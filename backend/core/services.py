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
                     Quote, Refund, Reservation, Room, Stay)

def hotel_today(hotel):
    return timezone.localtime(timezone.now(), ZoneInfo(hotel.timezone)).date()

def balance(folio):
    charges = folio.entries.aggregate(total=Sum('amount_minor'))['total'] or 0
    paid = Payment.objects.filter(attempt__reservation=folio.reservation).aggregate(total=Sum('amount_minor'))['total'] or 0
    refunded = Refund.objects.filter(payment__attempt__reservation=folio.reservation, status='SETTLED').aggregate(total=Sum('amount_minor'))['total'] or 0
    return charges - (paid - refunded)

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

    # Early checkout: if checking out before scheduled departure, shorten active allocation so room is sellable
    today = hotel_today(room.hotel)
    if today < reservation.departure:
        alloc = Allocation.objects.filter(reservation=reservation, active=True).first()
        if alloc:
            new_departure = max(reservation.arrival + timedelta(days=1), today)
            if new_departure < reservation.departure:
                alloc.period = Range(reservation.arrival, new_departure, '[)')
                alloc.save(update_fields=['period'])

    return stay

@transaction.atomic
def amend_reservation(reservation, new_arrival, new_departure, new_occupants, actor_username='staff'):
    reservation = Reservation.objects.select_for_update().select_related('room__hotel', 'room__type').get(pk=reservation.pk)
    if reservation.status not in ('CONFIRMED', 'HOLD'):
        raise ValueError(f'Cannot amend reservation in {reservation.status} status.')
    hotel = reservation.room.hotel
    today = hotel_today(hotel)
    if new_arrival >= new_departure:
        raise ValueError('Arrival date must precede departure date.')
    if new_arrival < today:
        raise ValueError(f'New arrival date cannot be in the past ({today}).')
    if new_occupants < 1 or new_occupants > reservation.room.type.capacity:
        raise ValueError(f'Occupancy must be between 1 and {reservation.room.type.capacity}.')

    # Check that room is available on the new dates (excluding current reservation)
    conflict = Allocation.objects.filter(
        active=True,
        room=reservation.room,
        period__overlap=Range(new_arrival, new_departure, '[)')
    ).exclude(reservation=reservation).exists()
    if conflict:
        raise ValueError(f'Room {reservation.room.number} is not available from {new_arrival} to {new_departure}.')

    alloc = Allocation.objects.select_for_update().filter(reservation=reservation, active=True).first()
    if alloc:
        alloc.period = Range(new_arrival, new_departure, '[)')
        alloc.save(update_fields=['period'])

    old_arrival, old_departure = reservation.arrival, reservation.departure
    reservation.arrival = new_arrival
    reservation.departure = new_departure
    reservation.occupants = new_occupants
    reservation.save(update_fields=['arrival', 'departure', 'occupants'])

    # Folio entries are immutable; calculate room charge delta and record as ADJUSTMENT
    folio = reservation.folio
    old_room_total = folio.entries.filter(category='ROOM').aggregate(v=Sum('amount_minor'))['v'] or 0
    new_nights = (new_departure - new_arrival).days
    new_room_total = new_nights * reservation.room.type.nightly_rate_minor
    room_delta = new_room_total - old_room_total
    if room_delta != 0:
        FolioEntry.objects.create(
            folio=folio,
            category='ADJUSTMENT',
            description=f'Amendment adjustment: {new_arrival} to {new_departure} ({new_nights} nights)',
            amount_minor=room_delta,
            service_date=new_arrival
        )

    if hotel.tax_percent > 0:
        old_tax = folio.entries.filter(category='TAX').aggregate(v=Sum('amount_minor'))['v'] or 0
        new_tax = (new_room_total * hotel.tax_percent + 50) // 100
        tax_delta = new_tax - old_tax
        if tax_delta != 0:
            FolioEntry.objects.create(
                folio=folio,
                category='TAX',
                description='Tax adjustment for amendment',
                amount_minor=tax_delta,
                service_date=new_arrival
            )

    Audit.objects.create(
        actor=actor_username,
        action='AMEND_RESERVATION',
        target=f'{reservation.reference}:{old_arrival}/{old_departure}->{new_arrival}/{new_departure}'
    )
    return reservation

@transaction.atomic
def reassign_room(reservation, new_room, actor_username='staff'):
    reservation = Reservation.objects.select_for_update().select_related('room__hotel', 'room__type').get(pk=reservation.pk)
    if reservation.status not in ('CONFIRMED', 'CHECKED_IN'):
        raise ValueError(f'Cannot reassign room for reservation in {reservation.status} status.')
    if new_room.pk == reservation.room_id:
        return reservation
    if not new_room.in_service:
        raise ValueError(f'Room {new_room.number} is currently out of service.')
    if new_room.type.capacity < reservation.occupants:
        raise ValueError(f'Room {new_room.number} capacity ({new_room.type.capacity}) is less than guests ({reservation.occupants}).')

    conflict = Allocation.objects.filter(
        active=True,
        room=new_room,
        period__overlap=Range(reservation.arrival, reservation.departure, '[)')
    ).exists()
    if conflict:
        raise ValueError(f'Room {new_room.number} is not available for {reservation.arrival} to {reservation.departure}.')

    alloc = Allocation.objects.select_for_update().filter(reservation=reservation, active=True).first()
    if alloc:
        alloc.room = new_room
        alloc.save(update_fields=['room'])

    old_room_number = reservation.room.number
    old_rate = reservation.room.type.nightly_rate_minor
    new_rate = new_room.type.nightly_rate_minor
    nights = (reservation.departure - reservation.arrival).days

    if old_rate != new_rate:
        rate_diff = (new_rate - old_rate) * nights
        FolioEntry.objects.create(
            folio=reservation.folio,
            category='ADJUSTMENT',
            description=f'Room reassignment: {old_room_number} to {new_room.number} ({new_room.type.name})',
            amount_minor=rate_diff,
            service_date=hotel_today(new_room.hotel)
        )

    reservation.room = new_room
    reservation.save(update_fields=['room'])

    Audit.objects.create(
        actor=actor_username,
        action='REASSIGN_ROOM',
        target=f'{reservation.reference}:{old_room_number}->{new_room.number}'
    )
    return reservation

@transaction.atomic
def mark_no_show(reservation, actor_username='staff'):
    reservation = Reservation.objects.select_for_update().select_related('room__hotel').get(pk=reservation.pk)
    if reservation.status != 'CONFIRMED':
        raise ValueError(f'Only confirmed reservations can be marked no-show (current: {reservation.status}).')
    today = hotel_today(reservation.room.hotel)
    if today < reservation.arrival:
        raise ValueError(f'Cannot mark no-show before the scheduled arrival date ({reservation.arrival}).')

    Allocation.objects.filter(reservation=reservation, active=True).update(active=False)
    reservation.status = 'NO_SHOW'
    reservation.cancelled_at = timezone.now()
    reservation.cancellation_reason = 'Guest did not arrive (No-Show)'
    reservation.save(update_fields=['status', 'cancelled_at', 'cancellation_reason'])

    Audit.objects.create(actor=actor_username, action='MARK_NO_SHOW', target=reservation.reference)
    return reservation

@transaction.atomic
def request_refund(payment, amount_minor, reason, requested_by_user):
    if amount_minor <= 0:
        raise ValueError('Refund amount must be positive.')
    prior_settled = Refund.objects.filter(payment=payment, status='SETTLED').aggregate(v=Sum('amount_minor'))['v'] or 0
    prior_pending = Refund.objects.filter(payment=payment, status__in=['PENDING', 'APPROVED']).aggregate(v=Sum('amount_minor'))['v'] or 0
    available_refundable = payment.amount_minor - (prior_settled + prior_pending)
    if amount_minor > available_refundable:
        raise ValueError(f'Requested refund ({amount_minor}) exceeds available refundable amount ({available_refundable}).')

    refund = Refund.objects.create(
        payment=payment,
        amount_minor=amount_minor,
        reason=reason,
        status='PENDING',
        requested_by=requested_by_user
    )
    Audit.objects.create(
        actor=requested_by_user.username,
        action='REQUEST_REFUND',
        target=f'{payment.attempt.reservation.reference}:{amount_minor}'
    )
    return refund

@transaction.atomic
def approve_refund(refund, reviewer_user):
    refund = Refund.objects.select_for_update().get(pk=refund.pk)
    if refund.status != 'PENDING':
        raise ValueError(f'Only pending refunds can be approved (current: {refund.status}).')
    refund.status = 'APPROVED'
    refund.reviewed_by = reviewer_user
    refund.save(update_fields=['status', 'reviewed_by'])
    Audit.objects.create(actor=reviewer_user.username, action='APPROVE_REFUND', target=f'Refund#{refund.pk}:{refund.amount_minor}')
    return refund

@transaction.atomic
def settle_refund(refund, reviewer_user):
    refund = Refund.objects.select_for_update().get(pk=refund.pk)
    if refund.status not in ('PENDING', 'APPROVED'):
        raise ValueError(f'Refund in {refund.status} status cannot be settled.')
    refund.status = 'SETTLED'
    refund.settled_at = timezone.now()
    if not refund.reviewed_by:
        refund.reviewed_by = reviewer_user
    refund.save(update_fields=['status', 'settled_at', 'reviewed_by'])

    reservation = refund.payment.attempt.reservation
    FolioEntry.objects.create(
        folio=reservation.folio,
        category='REFUND',
        description=f'Refund settled: {refund.reason}',
        amount_minor=-refund.amount_minor,
        service_date=hotel_today(reservation.room.hotel)
    )

    Audit.objects.create(actor=reviewer_user.username, action='SETTLE_REFUND', target=f'Refund#{refund.pk}:{refund.amount_minor}')
    return refund

@transaction.atomic
def reject_refund(refund, reviewer_user, rejection_reason=''):
    refund = Refund.objects.select_for_update().get(pk=refund.pk)
    if refund.status not in ('PENDING', 'APPROVED'):
        raise ValueError(f'Cannot reject refund in {refund.status} status.')
    refund.status = 'REJECTED'
    refund.reviewed_by = reviewer_user
    if rejection_reason:
        refund.reason = f'{refund.reason} [Rejected: {rejection_reason}]'
    refund.save(update_fields=['status', 'reviewed_by', 'reason'])
    Audit.objects.create(actor=reviewer_user.username, action='REJECT_REFUND', target=f'Refund#{refund.pk}:{refund.amount_minor}')
    return refund

@transaction.atomic
def assign_housekeeping_task(task, assignee_user, actor_username='staff'):
    task.assignee = assignee_user
    task.save(update_fields=['assignee'])
    Audit.objects.create(
        actor=actor_username,
        action='ASSIGN_HOUSEKEEPING',
        target=f'Room {task.room.number}->{assignee_user.username if assignee_user else "Unassigned"}'
    )
    return task

@transaction.atomic
def update_room_rate(room_type, new_rate_minor, actor_username='staff'):
    if new_rate_minor <= 0:
        raise ValueError('Nightly rate must be positive.')
    old_rate = room_type.nightly_rate_minor
    room_type.nightly_rate_minor = new_rate_minor
    room_type.save(update_fields=['nightly_rate_minor'])
    Audit.objects.create(
        actor=actor_username,
        action='UPDATE_ROOM_RATE',
        target=f'{room_type.name}:{old_rate}->{new_rate_minor}'
    )
    return room_type

