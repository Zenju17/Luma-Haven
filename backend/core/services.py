import hashlib
import hmac
import secrets
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from psycopg.types.range import Range
from .models import (Allocation, Audit, Folio, FolioEntry, Guest, Hotel, HousekeepingTask,
                     OTP, Outbox, Payment, PaymentAttempt, PaymentEvent, PaymentException,
                     Quote, Reservation, Room, Stay)

def hotel_today(hotel):
    return timezone.localtime(timezone.now(), ZoneInfo(hotel.timezone)).date()

def balance(folio):
    charges = folio.entries.aggregate(total=Sum('amount_minor'))['total'] or 0
    paid = Payment.objects.filter(attempt__reservation=folio.reservation).aggregate(total=Sum('amount_minor'))['total'] or 0
    return charges - paid

def release_expired():
    now = timezone.now()
    ids = list(Allocation.objects.filter(active=True, kind='HOLD', expires_at__lte=now).values_list('reservation_id', flat=True))
    Allocation.objects.filter(active=True, kind='HOLD', expires_at__lte=now).update(active=False)
    Reservation.objects.filter(id__in=ids, status='HOLD').update(status='EXPIRED')

def available(arrival, departure, occupants):
    release_expired()
    occupied = Allocation.objects.filter(active=True, period__overlap=Range(arrival, departure, '[)')).values('room_id')
    return Room.objects.filter(in_service=True, type__capacity__gte=occupants).exclude(id__in=occupied).select_related('type', 'hotel').order_by('number')

def create_quote(room, arrival, departure, occupants):
    if arrival >= departure or arrival < hotel_today(room.hotel) or occupants < 1 or occupants > room.type.capacity:
        raise ValueError('Invalid dates or occupancy')
    if not available(arrival, departure, occupants).filter(id=room.id).exists():
        raise ValueError('Room is unavailable')
    nights = (departure - arrival).days
    amount = nights * room.type.nightly_rate_minor
    return Quote.objects.create(room=room, arrival=arrival, departure=departure, occupants=occupants,
                                room_amount_minor=amount, tax_minor=(amount * room.hotel.tax_percent + 50) // 100,
                                currency=room.hotel.currency, expires_at=timezone.now() + timedelta(minutes=10))

@transaction.atomic
def reserve(quote, name, email):
    if quote.expires_at <= timezone.now():
        raise ValueError('Quote expired')
    release_expired()
    guest = Guest.objects.create(full_name=name, email=email)
    reservation = Reservation.objects.create(reference=secrets.token_hex(8).upper(), guest=guest,
        room=quote.room, arrival=quote.arrival, departure=quote.departure, occupants=quote.occupants,
        hold_expires_at=timezone.now() + timedelta(minutes=15))
    Allocation.objects.create(room=quote.room, reservation=reservation, period=Range(quote.arrival, quote.departure, '[)'),
                              expires_at=reservation.hold_expires_at)
    folio = Folio.objects.create(reservation=reservation, currency=quote.currency)
    nights = (quote.departure - quote.arrival).days
    base, extra = divmod(quote.room_amount_minor, nights)
    for day in range(nights):
        date = quote.arrival + timedelta(days=day)
        FolioEntry.objects.create(folio=folio, category='ROOM', description='Room night',
                                  amount_minor=base + (1 if day < extra else 0), service_date=date)
    if quote.tax_minor:
        FolioEntry.objects.create(folio=folio, category='TAX', description='Quoted tax', amount_minor=quote.tax_minor, service_date=quote.arrival)
    return reservation

@transaction.atomic
def process_event(attempt_id, outcome, event_id):
    attempt = PaymentAttempt.objects.select_for_update().select_related('reservation').get(pk=attempt_id)
    if PaymentEvent.objects.filter(event_id=event_id).exists():
        return attempt
    PaymentEvent.objects.create(attempt=attempt, outcome=outcome, event_id=event_id)
    if attempt.status == 'SUCCESS':
        return attempt
    if outcome == 'PENDING':
        return attempt
    if outcome == 'FAILED':
        attempt.status = 'FAILED'
    elif outcome == 'SUCCESS':
        reservation = Reservation.objects.select_for_update().get(pk=attempt.reservation_id)
        if attempt.currency != reservation.folio.currency or attempt.amount_minor != balance(reservation.folio):
            PaymentException.objects.get_or_create(attempt=attempt, defaults={'reason': 'Amount or currency mismatch'})
            attempt.status = 'EXCEPTION'
        else:
            if reservation.status in ('HOLD', 'EXPIRED'):
                release_expired()
                try:
                    # Database exclusion constraint arbitrates late payment against new allocations.
                    with transaction.atomic():
                        allocation = Allocation.objects.filter(reservation=reservation).first()
                        if allocation.active:
                            allocation.kind = 'CONFIRMED'
                            allocation.expires_at = None
                            allocation.save(update_fields=['kind', 'expires_at'])
                        else:
                            Allocation.objects.create(room=reservation.room, reservation=reservation,
                                period=Range(reservation.arrival, reservation.departure, '[)'), kind='CONFIRMED')
                except IntegrityError:
                    PaymentException.objects.get_or_create(attempt=attempt, defaults={'reason': 'Room no longer available; refund required'})
                    attempt.status = 'EXCEPTION'
                else:
                    reservation.status = 'CONFIRMED'
                    reservation.save(update_fields=['status'])
            if attempt.status != 'EXCEPTION':
                Payment.objects.get_or_create(attempt=attempt, defaults={'amount_minor': attempt.amount_minor})
                attempt.status = 'SUCCESS'
                Outbox.objects.create(kind='BOOKING_CONFIRMED', target=str(reservation.pk))
    attempt.save(update_fields=['status'])
    return attempt

def otp_digest(code):
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()

@transaction.atomic
def check_in(reservation, actor=None):
    reservation = Reservation.objects.select_for_update().select_related('room__hotel').get(pk=reservation.pk)
    existing = Stay.objects.filter(reservation=reservation).first()
    if existing:
        return existing
    room = Room.objects.select_for_update().get(pk=reservation.room_id)
    if reservation.status != 'CONFIRMED':
        raise ValueError('Only confirmed reservations can check in.')
    if not reservation.verified:
        raise ValueError('Verify your booking before check-in.')
    today = hotel_today(room.hotel)
    if today < reservation.arrival:
        raise ValueError(f'Check-in opens on {reservation.arrival} ({room.hotel.timezone}).')
    if today >= reservation.departure:
        raise ValueError('The booking departure date has passed. Contact reception.')
    if room.cleaning != 'READY' or not room.in_service:
        raise ValueError('The room is not ready or is out of service. Contact reception.')
    if balance(reservation.folio) > 0:
        raise ValueError('Settle the outstanding balance before check-in.')
    if Stay.objects.filter(reservation__room=room, checked_out_at__isnull=True).exists():
        raise ValueError('The room is occupied. Contact reception.')
    stay = Stay.objects.create(reservation=reservation, actor=actor)
    reservation.status = 'CHECKED_IN'
    reservation.save(update_fields=['status'])
    Audit.objects.create(actor=str(actor or 'verified guest'), action='CHECK_IN', target=reservation.reference)
    return stay

@transaction.atomic
def check_out(reservation, version):
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    stay = Stay.objects.select_for_update().get(reservation=reservation)
    if stay.checked_out_at:
        return stay
    folio = Folio.objects.select_for_update().get(reservation=reservation)
    if version != folio.version or balance(folio) > 0:
        raise ValueError('Folio changed or balance outstanding')
    stay.checked_out_at = timezone.now()
    stay.save(update_fields=['checked_out_at'])
    folio.closed = True
    folio.save(update_fields=['closed'])
    reservation.status = 'CHECKED_OUT'
    reservation.save(update_fields=['status'])
    room = Room.objects.select_for_update().get(pk=reservation.room_id)
    room.cleaning = 'DIRTY'
    room.save(update_fields=['cleaning'])
    HousekeepingTask.objects.get_or_create(stay=stay, defaults={'room': room})
    Audit.objects.create(actor='verified guest', action='CHECK_OUT', target=reservation.reference)
    Outbox.objects.create(kind='CHECK_OUT', target=str(reservation.pk))
    return stay
