"""Durable payment polling on Vercel, with no continuously running worker."""
from datetime import timedelta
from asgiref.sync import async_to_sync
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from vercel.queue import send
from ..models import Outbox, PaymentAttempt

TOPIC = 'hotel-payment-status'


def start_monitoring(attempt):
    if not settings.PAYMENT_QUEUE_ENABLED:
        if settings.ENV == 'production':
            raise RuntimeError('Payment background monitoring must be configured')
        return
    with transaction.atomic():
        PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
        event = Outbox.objects.filter(kind='PAYMENT_POLL', target=str(attempt.pk)).first()
        if event is None:
            event = Outbox.objects.create(kind='PAYMENT_POLL', target=str(attempt.pk))
    if event.delivered_at:
        return
    async_to_sync(send)(TOPIC, {'attempt_id': str(attempt.pk), 'step': 0},
                        delay=30, retention=timedelta(days=2),
                        idempotency_key=f'payment:{attempt.pk}:0')
    Outbox.objects.filter(pk=event.pk, delivered_at__isnull=True).update(delivered_at=timezone.now())


def poll_once(attempt_id):
    from django.db import close_old_connections
    from .service import refresh_attempt
    from ..models import PaymentAttempt
    from ..services import release_expired
    try:
        attempt = PaymentAttempt.objects.filter(pk=attempt_id, provider='bakong').first()
        if not attempt or attempt.status not in ('PENDING', 'EXPIRED'):
            return None
        age = timezone.now() - attempt.created_at
        if age >= timedelta(hours=settings.PAYMENT_LATE_WINDOW_HOURS):
            release_expired()
            return None
        result = refresh_attempt(attempt.pk)
        release_expired()
        if result.status not in ('PENDING', 'EXPIRED'):
            return None
        return 30 if age < timedelta(minutes=15) else 300 if age < timedelta(hours=1) else 1800
    finally:
        close_old_connections()
