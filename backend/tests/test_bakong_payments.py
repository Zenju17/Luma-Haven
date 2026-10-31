import hashlib
from datetime import timedelta
import pytest
from django.core.checks import run_checks
from django.utils import timezone
from psycopg.types.range import Range
from core import services
from core.decision_support import evaluate_decision_support_alerts
from core.models import (Allocation, Payment, PaymentAttempt, PaymentEvent, PaymentException, Hotel,
                         Reservation, Room, RoomType, User)
from core.payments import bakong, service
from core.payments.base import ProviderError, QRSession

JSON = 'application/json'


class FakeBakong:
    """Stands in for the Bakong API: tests never touch the network."""
    def __init__(self):
        self.paid, self.down, self.created = set(), False, []

    def create_qr(self, *, amount_minor, currency, bill_number):
        if currency != 'USD':
            raise ProviderError('Hotel currency does not match the configured Bakong currency')
        qr = f'FAKEQR|{amount_minor}|{currency}|{bill_number}|{len(self.created)}'
        self.created.append(qr)
        return QRSession(qr=qr, md5=hashlib.md5(qr.encode()).hexdigest(), tran_id=bill_number)

    def check_status(self, md5):
        if self.down:
            raise ProviderError('Bakong unavailable')
        return 'PAID' if md5 in self.paid else 'UNPAID'


@pytest.fixture
def fake(monkeypatch, settings):
    settings.PAYMENT_PROVIDER = 'bakong'
    provider = FakeBakong()
    monkeypatch.setattr(bakong, 'create_qr', provider.create_qr)
    monkeypatch.setattr(bakong, 'check_status', provider.check_status)
    return provider


@pytest.fixture
def room(db):
    hotel = Hotel.objects.create(name='Test Hotel', tax_percent=0)
    kind = RoomType.objects.create(hotel=hotel, name='Twin', nightly_rate_minor=10000)
    return Room.objects.create(hotel=hotel, type=kind, number='1')


def make_booking(client, room, name='Sok'):
    start = services.hotel_today(room.hotel) + timedelta(days=5)
    quote = services.create_quote(room, start, start + timedelta(days=2), 2)
    reservation = services.reserve(quote, name, f'{name.lower()}@example.com')
    session = client.session
    session['guest_reservation'] = reservation.pk
    session.save()
    return reservation


def open_session(client, reservation):
    response = client.post(f'/api/v1/reservations/{reservation.pk}/payment-sessions', {}, content_type=JSON)
    assert response.status_code == 201, response.content
    return response.json()


def poll(client, attempt_id):
    return client.get(f'/api/v1/payment-sessions/{attempt_id}')


def test_session_creates_qr_from_server_balance_and_extends_hold(client, room, fake):
    reservation = make_booking(client, room)
    before = reservation.hold_expires_at
    data = open_session(client, reservation)
    assert data['provider'] == 'bakong' and data['simulated'] is False and data['qr'].startswith('FAKEQR|20000|USD|')
    attempt = PaymentAttempt.objects.get(pk=data['id'])
    assert attempt.amount_minor == 20000 and attempt.provider_md5 and attempt.expires_at > timezone.now()
    reservation.refresh_from_db()
    assert reservation.hold_expires_at > before
    assert Allocation.objects.get(reservation=reservation).expires_at == reservation.hold_expires_at


def test_second_request_reuses_live_attempt_and_is_rate_limited(client, room, fake):
    reservation = make_booking(client, room)
    first = open_session(client, reservation)
    assert open_session(client, reservation)['id'] == first['id']
    assert len(fake.created) == 1
    # Force new sessions by expiring each, until the per-window cap is reached.
    for _ in range(service.MAX_ATTEMPTS_PER_WINDOW):
        PaymentAttempt.objects.filter(status='PENDING').update(expires_at=timezone.now() - timedelta(seconds=1))
        response = client.post(f'/api/v1/reservations/{reservation.pk}/payment-sessions', {}, content_type=JSON)
        if response.status_code == 400:
            break
    assert response.status_code == 400 and 'Too many' in response.json()[0]


def test_unpaid_poll_stays_pending_and_paid_poll_settles_once(client, room, fake):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    assert poll(client, data['id']).json()['status'] == 'PENDING'
    reservation.refresh_from_db()
    assert reservation.status == 'HOLD'

    fake.paid.add(PaymentAttempt.objects.get(pk=data['id']).provider_md5)
    PaymentAttempt.objects.update(last_checked_at=None)
    body = poll(client, data['id']).json()
    assert body['status'] == 'SUCCESS' and 'qr' not in body  # QR is not re-exposed once settled
    reservation.refresh_from_db()
    assert reservation.status == 'CONFIRMED'
    for _ in range(3):  # duplicate polls and sweeps are harmless
        PaymentAttempt.objects.update(last_checked_at=None)
        poll(client, data['id'])
        service.sweep()
    assert Payment.objects.count() == 1 and PaymentEvent.objects.filter(event_id__startswith='bakong:').count() == 1


def test_poll_is_booking_scoped(client, room, fake):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    from django.test import Client
    stranger = Client()
    assert poll(stranger, data['id']).status_code == 403
    assert poll(client, '00000000-0000-0000-0000-000000000000').status_code == 404


def test_poll_throttles_provider_calls(client, room, fake, monkeypatch):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    calls = []
    monkeypatch.setattr(bakong, 'check_status', lambda md5: calls.append(md5) or 'UNPAID')
    poll(client, data['id'])
    poll(client, data['id'])
    poll(client, data['id'])
    assert len(calls) == 1  # min interval between provider calls


def test_provider_outage_keeps_attempt_pending(client, room, fake):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    fake.down = True
    assert poll(client, data['id']).json()['status'] == 'PENDING'
    fake.down = False
    assert service.sweep()['checked'] == 1


def test_expired_attempt_then_late_payment_confirms_when_room_free(client, room, fake):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    attempt = PaymentAttempt.objects.get(pk=data['id'])
    PaymentAttempt.objects.filter(pk=attempt.pk).update(expires_at=timezone.now() - timedelta(minutes=1), last_checked_at=None)
    assert poll(client, data['id']).json()['status'] == 'EXPIRED'
    # Guest pays the old QR anyway; the sweeper still watches expired attempts.
    fake.paid.add(attempt.provider_md5)
    PaymentAttempt.objects.update(last_checked_at=None)
    assert service.sweep()['settled'] == 1
    reservation.refresh_from_db()
    assert reservation.status == 'CONFIRMED'


def test_late_payment_after_room_was_taken_becomes_exception(client, room, fake):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    attempt = PaymentAttempt.objects.get(pk=data['id'])
    PaymentAttempt.objects.filter(pk=attempt.pk).update(expires_at=timezone.now() - timedelta(minutes=1), last_checked_at=None)
    Allocation.objects.filter(reservation=reservation).update(active=False, expires_at=timezone.now() - timedelta(minutes=5))
    Reservation.objects.filter(pk=reservation.pk).update(status='EXPIRED')
    Allocation.objects.create(room=room, period=Range(reservation.arrival, reservation.departure, '[)'), kind='MAINTENANCE')
    fake.paid.add(attempt.provider_md5)
    service.sweep()
    attempt.refresh_from_db()
    assert attempt.status == 'EXCEPTION' and PaymentException.objects.filter(attempt=attempt).exists()
    assert not Payment.objects.exists()


def test_currency_mismatch_is_rejected_without_creating_qr(client, room, fake):
    room.hotel.currency = 'KHR'
    room.hotel.save()
    reservation = make_booking(client, room)
    response = client.post(f'/api/v1/reservations/{reservation.pk}/payment-sessions', {}, content_type=JSON)
    assert response.status_code == 400 and not fake.created


def test_development_provider_is_unchanged(client, room, settings):
    settings.PAYMENT_PROVIDER = 'development'
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    assert data['simulated'] is True and 'qr' not in data
    assert poll(client, data['id']).json()['provider'] == 'development'
    assert client.get(f"/api/v1/reservations/{reservation.pk}").json()['payment_provider'] == 'development'


def test_reconciliation_report_shows_channel_mix_and_funnel(client, room, fake):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    fake.paid.add(PaymentAttempt.objects.get(pk=data['id']).provider_md5)
    poll(client, data['id'])
    User.objects.create_user(username='acct', password='test-only', role='ACCOUNTANT')
    assert client.post('/api/v1/auth/login', {'username': 'acct', 'password': 'test-only'}, content_type=JSON, HTTP_X_PORTAL='staff').status_code == 200
    body = client.get('/api/v1/staff/reports/cash-reconciliation').json()
    assert body['channel_mix']['bakong'] == {'count': 1, 'amount_minor': 20000}
    assert body['attempt_funnel']['bakong']['SUCCESS'] == 1 and body['attempt_funnel']['bakong']['abandon_rate_percent'] == 0
    csv = client.get('/api/v1/staff/reports/cash-reconciliation?export=csv').content
    assert b'Channel: bakong' in csv


def test_decision_support_flags_unreconciled_khqr(client, room, fake):
    reservation = make_booking(client, room)
    data = open_session(client, reservation)
    assert 'unreconciled_khqr_attempts' not in {a['id'] for a in evaluate_decision_support_alerts()}
    PaymentAttempt.objects.filter(pk=data['id']).update(expires_at=timezone.now() - timedelta(hours=1))
    assert 'unreconciled_khqr_attempts' in {a['id'] for a in evaluate_decision_support_alerts()}


def test_system_check_requires_bakong_configuration(settings):
    settings.PAYMENT_PROVIDER = 'bakong'
    settings.BAKONG_TOKEN = ''
    ids = {e.id for e in run_checks() if e.id and e.id.startswith('payments.')}
    assert 'payments.E003' in ids
    settings.BAKONG_TOKEN, settings.BAKONG_ACCOUNT_ID = 'x', 'hotel@bank'
    assert not [e for e in run_checks() if e.id and e.id.startswith('payments.')]
    settings.PAYMENT_PROVIDER = 'stripe'
    assert 'payments.E002' in {e.id for e in run_checks()}


def test_real_sdk_generates_local_qr_with_exact_amount(settings):
    """Exercises the real bakong-khqr package offline (no network: a non-relay token builds the QR locally)."""
    settings.BAKONG_TOKEN, settings.BAKONG_ACCOUNT_ID = 'offline-test-token', 'luma_haven@abaa'
    qr = bakong.create_qr(amount_minor=12345, currency='USD', bill_number='REF-abc123')
    assert '5406123.45' in qr.qr and 'luma_haven@abaa' in qr.qr and len(qr.md5) == 32
    assert qr.md5 == hashlib.md5(qr.qr.encode()).hexdigest()
    with pytest.raises(ProviderError):
        bakong.create_qr(amount_minor=100, currency='KHR', bill_number='X')
    with pytest.raises(ProviderError):
        bakong.create_qr(amount_minor=0, currency='USD', bill_number='X')
