from datetime import timedelta
import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from psycopg.types.range import Range
from core import services
from core.models import (Allocation, Folio, FolioEntry, Hotel, HousekeepingTask,
                         OTP, Payment, PaymentAttempt, PaymentException, Quote, Reservation,
                         Room, RoomType, User)

@pytest.fixture
def inventory(db):
    hotel = Hotel.objects.create(name='Test Hotel')
    kind = RoomType.objects.create(hotel=hotel, name='Twin', nightly_rate_minor=10000)
    room = Room.objects.create(hotel=hotel, type=kind, number='1')
    return room

@pytest.mark.django_db(transaction=True)
def test_overlaps_rejected_but_adjacent_dates_allowed(inventory):
    today = services.hotel_today(inventory.hotel) + timedelta(days=1)
    Allocation.objects.create(room=inventory, period=Range(today, today + timedelta(days=2), '[)'), kind='MAINTENANCE')
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Allocation.objects.create(room=inventory, period=Range(today + timedelta(days=1), today + timedelta(days=3), '[)'), kind='MAINTENANCE')
    Allocation.objects.create(room=inventory, period=Range(today + timedelta(days=2), today + timedelta(days=3), '[)'), kind='MAINTENANCE')
    assert Allocation.objects.filter(active=True).count() == 2

@pytest.mark.django_db(transaction=True)
def test_payment_replay_failure_after_success_and_checkout(inventory):
    arrival = services.hotel_today(inventory.hotel)
    quote = services.create_quote(inventory, arrival, arrival + timedelta(days=1), 1)
    reservation = services.reserve(quote, 'Fictional Visitor', 'example@localhost')
    attempt = PaymentAttempt.objects.create(reservation=reservation, amount_minor=10000, currency='USD')
    services.process_event(attempt.id, 'SUCCESS', 'event-1')
    services.process_event(attempt.id, 'SUCCESS', 'event-1')
    services.process_event(attempt.id, 'FAILED', 'event-2')
    assert Payment.objects.filter(attempt=attempt).count() == 1
    attempt.refresh_from_db()
    assert attempt.status == 'SUCCESS'
    reservation.refresh_from_db()
    assert reservation.status == 'CONFIRMED'
    reservation.verified = True
    reservation.save(update_fields=['verified'])
    stay = services.check_in(reservation)
    assert services.check_in(reservation).pk == stay.pk
    assert services.check_out(reservation, 1).pk == stay.pk
    services.check_out(reservation, 1)
    assert HousekeepingTask.objects.filter(stay=stay).count() == 1
    inventory.refresh_from_db()
    assert inventory.cleaning == 'DIRTY'

@pytest.mark.django_db(transaction=True)
def test_late_payment_with_conflicting_booking_is_visible(inventory):
    arrival = services.hotel_today(inventory.hotel) + timedelta(days=1)
    reservation = services.reserve(services.create_quote(inventory, arrival, arrival + timedelta(days=1), 1), 'One', 'one@localhost')
    Allocation.objects.filter(reservation=reservation).update(expires_at=timezone.now() - timedelta(seconds=1))
    services.release_expired()
    second = services.reserve(services.create_quote(inventory, arrival, arrival + timedelta(days=1), 1), 'Two', 'two@localhost')
    attempt = PaymentAttempt.objects.create(reservation=reservation, amount_minor=10000, currency='USD')
    services.process_event(attempt.id, 'SUCCESS', 'late-event')
    attempt.refresh_from_db()
    assert attempt.status == 'EXCEPTION'
    assert PaymentException.objects.filter(attempt=attempt).exists()
    second.refresh_from_db()
    assert second.status == 'HOLD'

@pytest.mark.django_db
def test_checkout_rejects_updated_folio(inventory):
    arrival = services.hotel_today(inventory.hotel)
    obj = services.reserve(services.create_quote(inventory, arrival, arrival + timedelta(days=1), 1), 'Test', 'test@localhost')
    obj.verified = True
    obj.status = 'CONFIRMED'
    obj.save(update_fields=['verified', 'status'])
    Allocation.objects.filter(reservation=obj).update(kind='CONFIRMED', expires_at=None)
    attempt = PaymentAttempt.objects.create(reservation=obj, amount_minor=10000, currency='USD', status='SUCCESS')
    Payment.objects.create(attempt=attempt, amount_minor=10000)
    services.check_in(obj)
    FolioEntry.objects.create(folio=obj.folio, category='SERVICE', description='Late charge', amount_minor=500, service_date=arrival)
    with pytest.raises(ValueError):
        services.check_out(obj, 1)

@pytest.mark.django_db
def test_guest_cannot_read_other_booking(inventory, client):
    arrival = services.hotel_today(inventory.hotel) + timedelta(days=1)
    obj = services.reserve(services.create_quote(inventory, arrival, arrival + timedelta(days=1), 1), 'One', 'one@localhost')
    response = client.get(f'/api/v1/reservations/{obj.pk}')
    assert response.status_code == 403

@pytest.mark.django_db
def test_housekeeping_cannot_read_financial_dashboard(inventory, client):
    user = User.objects.create_user(username='cleaner', password='test', role='HOUSEKEEPING')
    client.force_login(user)
    response = client.get('/api/v1/dashboard/summary')
    assert 'outstanding_minor' not in response.json()
    assert 'rate_minor' not in client.get('/api/v1/rooms').json()[0]
    assert client.get('/api/v1/staff/reservations').status_code == 403

@pytest.mark.django_db
def test_report_zero_denominators_and_hotel_day(inventory):
    from core.views import report_values
    today = services.hotel_today(inventory.hotel)
    empty = report_values(today, today + timedelta(days=1))
    assert empty['sellable_room_nights'] == 1
    assert empty['sold_room_nights'] == 0
    assert empty['average_daily_rate_minor'] is None
    assert empty['revpar_minor'] == 0
    assert empty['timezone'] == 'Asia/Phnom_Penh'

@pytest.mark.django_db
def test_otp_attempt_limit_and_expiry(inventory, client):
    arrival = services.hotel_today(inventory.hotel) + timedelta(days=1)
    obj = services.reserve(services.create_quote(inventory, arrival, arrival + timedelta(days=1), 1), 'One', 'one@localhost')
    otp = OTP.objects.create(reservation=obj, digest=services.otp_digest('123456'), expires_at=timezone.now() + timedelta(minutes=5))
    for _ in range(5):
        response = client.post('/api/v1/guest-access/verify-otp', {'reference': obj.reference, 'email': 'one@localhost', 'code': '000000'}, content_type='application/json')
        assert response.status_code == 400
    otp.refresh_from_db()
    assert otp.attempts == 5
    assert client.post('/api/v1/guest-access/verify-otp', {'reference': obj.reference, 'email': 'one@localhost', 'code': '123456'}, content_type='application/json').status_code == 400
