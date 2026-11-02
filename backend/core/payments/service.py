"""Payment-session orchestration: create attempts, poll the provider, settle idempotently, sweep."""
import logging
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from .. import services
from ..models import Allocation, Audit, PaymentAttempt, Reservation
from .base import ProviderError
from .factory import get_provider

log = logging.getLogger(__name__)
MIN_POLL_SECONDS = 3
MAX_ATTEMPTS_PER_WINDOW = 5  # new sessions per reservation per 10 minutes
HOLD_EXTENSION_CAP = timedelta(hours=1)  # a hold can be stretched for payment, never beyond this age


class SessionError(Exception):
    pass


def create_session(reservation, amount_minor, currency):
    """Create (or reuse) a payment attempt for the current server-computed balance.

    Three steps so the provider's network call never runs while the reservation row is locked:
    (1) lock, reuse/rate-limit, insert the attempt; (2) ask the provider for a QR; (3) attach it.
    """
    provider = get_provider()
    now = timezone.now()
    with transaction.atomic():
        locked = Reservation.objects.select_for_update().get(pk=reservation.pk)
        if not provider.supports_qr:
            return PaymentAttempt.objects.create(reservation=locked, amount_minor=amount_minor, currency=currency,
                                                 provider=provider.name)
        live = (PaymentAttempt.objects.filter(reservation=locked, provider=provider.name, status='PENDING',
                                              amount_minor=amount_minor, currency=currency, expires_at__gt=now)
                .exclude(provider_md5='').first())
        if not live and PaymentAttempt.objects.filter(reservation=locked, created_at__gte=now - timedelta(minutes=10)).count() >= MAX_ATTEMPTS_PER_WINDOW:
            raise SessionError('Too many payment attempts. Please wait a few minutes.')
        if not live:
            attempt = PaymentAttempt.objects.create(reservation=locked, amount_minor=amount_minor, currency=currency, provider=provider.name,
                                                    expires_at=now + timedelta(minutes=settings.PAYMENT_ATTEMPT_MINUTES))
            bill = f'{locked.reference}-{str(attempt.pk)[:6]}'
    if live:
        _ensure_monitoring(live)
        return live
    try:
        qr = provider.create_qr(amount_minor=amount_minor, currency=currency, bill_number=bill)
    except ProviderError as exc:
        log.warning('Bakong create_qr failed for reservation %s: %s', reservation.pk, exc)
        PaymentAttempt.objects.filter(pk=attempt.pk).update(status='FAILED')
        raise SessionError('Payment provider is unavailable. Please try again shortly.') from exc
    with transaction.atomic():
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
        attempt.provider_qr, attempt.provider_md5, attempt.provider_tran_id, attempt.checkout_url = qr.qr, qr.md5, qr.tran_id, qr.checkout_url
        attempt.save(update_fields=['provider_qr', 'provider_md5', 'provider_tran_id', 'checkout_url'])
        _extend_hold(Reservation.objects.select_for_update().get(pk=reservation.pk), attempt.expires_at)
    _ensure_monitoring(attempt)
    return attempt


def _ensure_monitoring(attempt):
    from .background import start_monitoring
    try:
        start_monitoring(attempt)
    except Exception as exc:
        log.warning('Unable to enqueue payment monitoring for attempt %s: %s', attempt.pk, exc)
        if getattr(settings, 'PAYMENT_QUEUE_ENABLED', False):
            raise SessionError('Payment monitoring is unavailable. Please retry before making a payment.')


def _extend_hold(reservation, until):
    """Keep the room held while a QR payment is in flight (bounded, so holds cannot be stretched forever)."""
    if reservation.status != 'HOLD' or timezone.now() - reservation.created_at > HOLD_EXTENSION_CAP:
        return
    target = until + timedelta(minutes=2)
    if target <= reservation.hold_expires_at:
        return
    reservation.hold_expires_at = target
    reservation.save(update_fields=['hold_expires_at'])
    Allocation.objects.filter(reservation=reservation, kind='HOLD', active=True).update(expires_at=target)


def refresh_attempt(attempt_id, *, force=False):
    """Ask the provider about one attempt and settle it if paid. Safe to call repeatedly."""
    now = timezone.now()
    with transaction.atomic():
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt_id)
        if attempt.status not in ('PENDING', 'EXPIRED') or not attempt.provider_md5:
            return attempt
        if not force and attempt.last_checked_at and (now - attempt.last_checked_at).total_seconds() < MIN_POLL_SECONDS:
            return attempt
        attempt.last_checked_at = now
        attempt.save(update_fields=['last_checked_at'])
    provider = get_provider(attempt.provider)
    try:
        status = provider.check_status(attempt.provider_md5)
    except ProviderError as exc:
        log.warning('Bakong status check failed for attempt %s: %s', attempt.pk, exc)
        return attempt  # transient: stay PENDING, the sweeper retries
    return _apply_status(attempt.pk, status)


def _apply_status(attempt_id, status):
    with transaction.atomic():
        if status == 'PAID':
            # process_event is idempotent on event_id and re-validates amount, currency and availability.
            attempt = services.process_event(attempt_id, 'SUCCESS', f'bakong:{PaymentAttempt.objects.get(pk=attempt_id).provider_md5}')
            if attempt.status == 'SUCCESS':
                Audit.objects.get_or_create(actor='bakong', action='PAYMENT_SETTLED', target=f'attempt:{str(attempt.pk)[:30]}')
            return attempt
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt_id)
        if attempt.status == 'PENDING' and (status == 'EXPIRED' or (attempt.expires_at and attempt.expires_at <= timezone.now())):
            attempt.status = 'EXPIRED'
            attempt.save(update_fields=['status'])
        return attempt


def _due(attempt, now):
    """Back off polling as an attempt ages: <15 min every cycle, <1 h every 5 min, then every 30 min."""
    age = now - attempt.created_at
    gap = timedelta(seconds=0) if age < timedelta(minutes=15) else timedelta(minutes=5) if age < timedelta(hours=1) else timedelta(minutes=30)
    return not attempt.last_checked_at or now - attempt.last_checked_at >= gap


def sweep(limit=50):
    """Poll unsettled provider attempts, including recently expired ones, to catch late payments."""
    now = timezone.now()
    window = now - timedelta(hours=settings.PAYMENT_LATE_WINDOW_HOURS)
    candidates = (PaymentAttempt.objects.filter(status__in=['PENDING', 'EXPIRED'], created_at__gte=window)
                  .exclude(provider_md5='').order_by(F('last_checked_at').asc(nulls_first=True), 'created_at')[:limit * 3])
    checked = settled = expired = 0
    for attempt in candidates:
        if checked >= limit:
            break
        if not _due(attempt, now):
            continue
        before = attempt.status
        result = refresh_attempt(attempt.pk, force=True)
        checked += 1
        settled += result.status == 'SUCCESS'
        expired += before == 'PENDING' and result.status == 'EXPIRED'
    return {'checked': checked, 'settled': settled, 'expired': expired}
