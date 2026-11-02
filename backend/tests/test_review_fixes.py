"""Regression tests for the 1 Nov 2026 code-review findings."""
from datetime import timedelta
import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone
from core import legal, services, throttling
from core.models import ConsentRecord, Hotel, LegalDocument, PaymentAttempt, Room, RoomType, User
from core.payments import bakong, service
from core.payments.base import QRSession

JSON = 'application/json'


def login(c, u, p, portal='staff', ip='10.0.0.1'):
    return c.post('/api/v1/auth/login', {'username': u, 'password': p}, content_type=JSON, HTTP_X_PORTAL=portal, REMOTE_ADDR=ip)


def test_attacker_cannot_lock_out_owner_from_another_ip(db, settings):
    cache.clear()
    settings.THROTTLE_ENABLED = True
    User.objects.create_user(username='admin', password='right-pass-9', role='ADMIN')
    for i in range(throttling.LOCKOUT_FAILURES):
        login(Client(), 'admin', 'wrong', portal='admin' if i % 2 else 'staff', ip='6.6.6.6')   # alternating portals
    assert login(Client(), 'admin', 'right-pass-9', portal='admin', ip='6.6.6.6').status_code == 429  # attacker IP locked
    assert login(Client(), 'admin', 'right-pass-9', portal='admin', ip='10.0.0.9').status_code == 200  # owner elsewhere is fine
    cache.clear()


def test_consent_hash_uses_real_client_ip_behind_proxy(db, settings):
    settings.TRUSTED_PROXY_COUNT = 1
    LegalDocument.objects.all().delete()
    legal.seed_templates()
    hotel = Hotel.objects.create(name='H')
    room = Room.objects.create(hotel=hotel, type=RoomType.objects.create(hotel=hotel, name='T', nightly_rate_minor=1000), number='1')
    docs = legal.current_documents('en')
    ids = [docs[k].pk for k in legal.BOOKING_KINDS]
    for n, real in enumerate(('1.1.1.1', '2.2.2.2')):
        start = services.hotel_today(hotel) + timedelta(days=3 + 2 * n)
        q = services.create_quote(room, start, start + timedelta(days=1), 1)
        Client().post('/api/v1/reservations', {'quote_id': str(q.pk), 'name': 'A', 'email': 'a@example.com', 'consent_document_ids': ids},
                      content_type=JSON, REMOTE_ADDR='172.18.0.2', HTTP_X_FORWARDED_FOR=real)
    hashes = set(ConsentRecord.objects.values_list('ip_hash', flat=True))
    assert len(hashes) == 2 and legal.hash_value('172.18.0.2') not in hashes


def test_agreement_must_match_exact_document(db):
    LegalDocument.objects.all().delete()
    legal.seed_templates()
    user = User.objects.create_user(username='r', password='x-test-pass', role='RECEPTION')
    km = legal.current_documents('km')['STAFF_AGREEMENT']
    legal.record_consent([km], user=user)                          # accepted Khmer v1 only
    assert [d.language for d in legal.pending_staff_documents(user, 'en')] == ['en']
    assert legal.pending_staff_documents(user, 'km') == []


def test_sweep_checks_never_polled_attempts_first(db, monkeypatch, settings):
    settings.PAYMENT_PROVIDER = 'bakong'
    hotel = Hotel.objects.create(name='H')
    room = Room.objects.create(hotel=hotel, type=RoomType.objects.create(hotel=hotel, name='T', nightly_rate_minor=1000), number='1')
    start = services.hotel_today(hotel) + timedelta(days=4)
    res = services.reserve(services.create_quote(room, start, start + timedelta(days=1), 1), 'A', 'a@example.com')
    old = timezone.now() - timedelta(hours=2)
    for i in range(6):
        PaymentAttempt.objects.create(reservation=res, amount_minor=1, currency='USD', provider='bakong', provider_md5=f'{i:032d}',
                                      status='EXPIRED', expires_at=old, last_checked_at=old)
    fresh = PaymentAttempt.objects.create(reservation=res, amount_minor=1, currency='USD', provider='bakong', provider_md5='f' * 32,
                                          expires_at=timezone.now() + timedelta(minutes=10))
    seen = []
    monkeypatch.setattr(bakong, 'check_status', lambda md5: seen.append(md5) or 'UNPAID')
    service.sweep(limit=1)
    assert seen == ['f' * 32] and PaymentAttempt.objects.get(pk=fresh.pk).last_checked_at


def test_qr_is_created_outside_the_reservation_lock(db, monkeypatch, settings):
    settings.PAYMENT_PROVIDER = 'bakong'
    from django.db import connection
    hotel = Hotel.objects.create(name='H')
    room = Room.objects.create(hotel=hotel, type=RoomType.objects.create(hotel=hotel, name='T', nightly_rate_minor=1000), number='1')
    start = services.hotel_today(hotel) + timedelta(days=4)
    res = services.reserve(services.create_quote(room, start, start + timedelta(days=1), 1), 'A', 'a@example.com')
    depth = []

    def fake_qr(**kw):
        depth.append(len(connection.savepoint_ids))   # savepoints opened by create_session itself
        return QRSession(qr='Q', md5='a' * 32, tran_id=kw['bill_number'])
    monkeypatch.setattr(bakong, 'create_qr', fake_qr)
    attempt = service.create_session(res, 1000, 'USD')
    assert depth == [0] and attempt.provider_md5 == 'a' * 32


def test_developer_cannot_sign_out_admin(db):
    User.objects.create_user(username='dev', password='test-only', role='DEVELOPER')
    boss = User.objects.create_user(username='boss', password='test-only', role='ADMIN')
    c = Client()
    assert login(c, 'dev', 'test-only', portal='admin').status_code == 200
    assert c.post(f'/api/v1/admin/dev/security/revoke/{boss.pk}', {}, content_type=JSON).status_code == 403


def test_bakong_failures_are_recorded_once_for_the_developer_console(db, monkeypatch, settings):
    from core.models import ErrorEvent
    from core.payments.base import ProviderError
    settings.PAYMENT_PROVIDER = 'bakong'
    hotel = Hotel.objects.create(name='H')
    room = Room.objects.create(hotel=hotel, type=RoomType.objects.create(hotel=hotel, name='T', nightly_rate_minor=1000), number='1')
    start = services.hotel_today(hotel) + timedelta(days=4)
    res = services.reserve(services.create_quote(room, start, start + timedelta(days=1), 1), 'A', 'a@example.com')

    def boom(**kw):
        raise ProviderError('429 Too Many Requests')
    monkeypatch.setattr(bakong, 'create_qr', boom)
    with pytest.raises(service.SessionError):
        service.create_session(res, 1000, 'USD')
    event = ErrorEvent.objects.get()
    assert event.path.startswith('payments/bakong/create_qr') and '429' in event.message

    attempt = PaymentAttempt.objects.create(reservation=res, amount_minor=1, currency='USD', provider='bakong', provider_md5='b' * 32)

    def fail_status(md5):
        raise ProviderError('403 Forbidden')
    monkeypatch.setattr(bakong, 'check_status', fail_status)
    service.refresh_attempt(attempt.pk, force=True)
    service.refresh_attempt(attempt.pk, force=True)  # identical failure inside 5 min is collapsed
    assert ErrorEvent.objects.filter(path__startswith='payments/bakong/check_status').count() == 1
