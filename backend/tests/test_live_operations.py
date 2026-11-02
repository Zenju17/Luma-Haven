import asyncio
from datetime import timedelta
from smtplib import SMTPException
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from django.core import mail
from django.core.cache.backends.db import DatabaseCache
from django.test import Client
from django.utils import timezone
from core import services
from core.models import Allocation, Audit, Hotel, OTP, Outbox, Payment, PaymentAttempt, Room, RoomType, Stay, User
from core.payments import background, service, bakong
from core.payments.base import QRSession

pytestmark = pytest.mark.django_db(transaction=True)
JSON = 'application/json'


@pytest.fixture
def booking():
    hotel = Hotel.objects.create(name='Test Hotel')
    kind = RoomType.objects.create(hotel=hotel, name='Twin', nightly_rate_minor=10000)
    room = Room.objects.create(hotel=hotel, type=kind, number='1')
    today = services.hotel_today(hotel)
    return services.reserve(services.create_quote(room, today, today + timedelta(days=1), 1),
                            'Test Guest', 'guest@example.test')


def confirm(booking):
    attempt = PaymentAttempt.objects.create(reservation=booking, amount_minor=services.balance(booking.folio), currency='USD')
    services.process_event(attempt.pk, 'SUCCESS', f'test-{attempt.pk}')
    booking.refresh_from_db()
    return attempt


def staff_client(role):
    user = User.objects.create_user(username=role.lower(), password='Test-only-password', role=role)
    client = Client(HTTP_X_PORTAL='staff')
    client.force_login(user)
    client.cookies['staff_sessionid'] = client.cookies['sessionid'].value
    return client


def test_monitoring_publication_is_retryable_and_deduplicated(booking, settings, monkeypatch):
    settings.PAYMENT_QUEUE_ENABLED = True
    attempt = PaymentAttempt.objects.create(reservation=booking, amount_minor=10000, currency='USD', provider='bakong')
    publish = AsyncMock(side_effect=[RuntimeError('temporary transport failure'), 'message-1'])
    monkeypatch.setattr(background, 'send', publish)
    with pytest.raises(RuntimeError):
        background.start_monitoring(attempt)
    event = Outbox.objects.get(kind='PAYMENT_POLL')
    assert event.delivered_at is None
    background.start_monitoring(attempt)
    background.start_monitoring(attempt)
    event.refresh_from_db()
    assert event.delivered_at is not None and publish.call_count == 2
    assert publish.call_args_list[0].kwargs['idempotency_key'] == publish.call_args_list[1].kwargs['idempotency_key']


def test_qr_is_not_returned_until_background_monitoring_is_accepted(booking, settings, monkeypatch):
    settings.PAYMENT_PROVIDER = 'bakong'
    settings.PAYMENT_QUEUE_ENABLED = True
    create = lambda **kwargs: QRSession(qr='TEST_QR', md5='a' * 32)
    monkeypatch.setattr(bakong, 'create_qr', create)
    publish = AsyncMock(side_effect=RuntimeError('queue unavailable'))
    monkeypatch.setattr(background, 'send', publish)
    with pytest.raises(service.SessionError, match='monitoring is unavailable'):
        service.create_session(booking, 10000, 'USD')
    assert PaymentAttempt.objects.count() == 1
    publish.side_effect = None
    publish.return_value = 'message-1'
    attempt = service.create_session(booking, 10000, 'USD')
    assert attempt.provider_qr == 'TEST_QR'
    assert PaymentAttempt.objects.count() == 1  # reuses the existing QR after a transport retry


def test_background_poller_settles_once_and_stops(booking, monkeypatch):
    attempt = PaymentAttempt.objects.create(reservation=booking, amount_minor=10000, currency='USD', provider='bakong', provider_md5='b' * 32)
    monkeypatch.setattr(bakong, 'check_status', lambda md5: 'PAID')
    assert background.poll_once(attempt.pk) is None
    assert background.poll_once(attempt.pk) is None
    assert Payment.objects.filter(attempt=attempt).count() == 1
    booking.refresh_from_db()
    assert booking.status == 'CONFIRMED'


def test_background_poller_backs_off_and_stops_outside_late_window(booking, monkeypatch):
    attempt = PaymentAttempt.objects.create(reservation=booking, amount_minor=10000, currency='USD', provider='bakong', provider_md5='c' * 32)
    monkeypatch.setattr(bakong, 'check_status', lambda md5: 'UNPAID')
    assert background.poll_once(attempt.pk) == 30
    PaymentAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now() - timedelta(minutes=30))
    assert background.poll_once(attempt.pk) == 300
    PaymentAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now() - timedelta(hours=2))
    assert background.poll_once(attempt.pk) == 1800
    PaymentAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now() - timedelta(hours=25))
    assert background.poll_once(attempt.pk) is None


def test_private_queue_subscriber_requeues_with_a_stable_step_key(monkeypatch):
    import queue_worker
    monkeypatch.setattr(queue_worker, 'poll_once', lambda attempt_id: 30)
    publish = AsyncMock(return_value='message-2')
    monkeypatch.setattr(queue_worker, 'send', publish)
    attempt_id = '99dc6691-54fe-4688-b49a-0719e84aa3de'
    asyncio.run(queue_worker.poll_payment(SimpleNamespace(payload={'attempt_id': attempt_id, 'step': 3})))
    assert publish.call_args.kwargs['delay'] == 30
    assert publish.call_args.kwargs['idempotency_key'] == f'payment:{attempt_id}:4'
    monkeypatch.setattr(queue_worker, 'poll_once', lambda attempt_id: None)
    asyncio.run(queue_worker.poll_payment(SimpleNamespace(payload={'attempt_id': attempt_id, 'step': 4})))
    assert publish.call_count == 1


def test_otp_delivery_uses_configured_sender_and_does_not_return_code(booking, settings):
    confirm(booking)
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.DEFAULT_FROM_EMAIL = 'reception@example.test'
    settings.HOSTED_ENVIRONMENT = settings.EMAIL_DELIVERY_CONFIGURED = True
    response = Client().post('/api/v1/guest-access/request-otp',
                             {'reference': booking.reference, 'email': booking.guest.email}, content_type=JSON)
    assert response.status_code == 200 and set(response.json()) == {'message'}
    assert mail.outbox[-1].from_email == 'reception@example.test'
    assert OTP.objects.filter(reservation=booking).count() == 1


def test_failed_or_unconfigured_email_does_not_create_unusable_otp(booking, settings, monkeypatch):
    confirm(booking)
    settings.HOSTED_ENVIRONMENT = True
    settings.EMAIL_DELIVERY_CONFIGURED = False
    data = {'reference': booking.reference, 'email': booking.guest.email}
    assert Client().post('/api/v1/guest-access/request-otp', data, content_type=JSON).status_code == 503
    assert not OTP.objects.exists()
    settings.EMAIL_DELIVERY_CONFIGURED = True
    monkeypatch.setattr('core.views.send_mail', lambda *args, **kwargs: (_ for _ in ()).throw(SMTPException('failed')))
    assert Client().post('/api/v1/guest-access/request-otp', data, content_type=JSON).status_code == 503
    assert not OTP.objects.exists()


def test_only_reception_and_admin_can_record_an_explicit_identity_check(booking):
    confirm(booking)
    path = f'/api/v1/staff/reservations/{booking.pk}/verify'
    assert Client().post(path, {'identity_checked': True}, content_type=JSON).status_code == 403
    assert staff_client('MANAGER').post(path, {'identity_checked': True}, content_type=JSON).status_code == 403
    reception = staff_client('RECEPTION')
    assert reception.post(path, {}, content_type=JSON).status_code == 400
    assert reception.post(path, {'identity_checked': 'true'}, content_type=JSON).status_code == 400
    assert reception.post(path, {'identity_checked': True}, content_type=JSON).json()['verified'] is True
    assert reception.post(path, {'identity_checked': True}, content_type=JSON).status_code == 200
    assert Audit.objects.filter(action='GUEST_VERIFIED_IN_PERSON', actor='reception').count() == 1


def test_database_cache_is_shared_and_daily_jobs_require_a_secret(settings, monkeypatch):
    first, second = DatabaseCache('core_runtime_cache', {}), DatabaseCache('core_runtime_cache', {})
    first.set('shared-throttle-counter', 2)
    assert second.get('shared-throttle-counter') == 2
    settings.CRON_SECRET = 'test-only-cron-secret'
    settings.ENV = 'production'
    calls = []
    monkeypatch.setattr('core.tasks.run_retention.run', lambda: calls.append('retention'))
    monkeypatch.setattr('core.tasks.archive_daily_mis_snapshot.run', lambda: calls.append('snapshot'))
    path = '/api/v1/system/daily-maintenance'
    assert Client().get(path).status_code == 403
    assert Client().get(path, HTTP_AUTHORIZATION='Bearer wrong').status_code == 403
    assert Client().get(path, HTTP_AUTHORIZATION='Bearer test-only-cron-secret').status_code == 200
    assert calls == ['retention', 'snapshot']


def test_an_overdue_open_stay_is_not_sold_even_after_its_allocation_ends(booking):
    confirm(booking)
    today = services.hotel_today(booking.room.hotel)
    booking.arrival, booking.departure = today - timedelta(days=2), today - timedelta(days=1)
    booking.status = 'CHECKED_IN'
    booking.save(update_fields=['arrival', 'departure', 'status'])
    Allocation.objects.filter(reservation=booking).update(active=False)
    Stay.objects.create(reservation=booking)
    assert not services.available(today, today + timedelta(days=1), 1).filter(pk=booking.room_id).exists()
    with pytest.raises(ValueError, match='unavailable'):
        services.create_quote(booking.room, today, today + timedelta(days=1), 1)
    booking.folio.refresh_from_db()
    services.check_out(booking, booking.folio.version)
    assert services.available(today, today + timedelta(days=1), 1).filter(pk=booking.room_id).exists()


def test_reserving_rechecks_a_room_removed_from_service_after_quoting(booking):
    # The fixture's current hold is released solely in this isolated test database.
    Allocation.objects.filter(reservation=booking).update(active=False)
    today = services.hotel_today(booking.room.hotel)
    quote = services.create_quote(booking.room, today, today + timedelta(days=1), 1)
    Room.objects.filter(pk=booking.room_id).update(in_service=False)
    with pytest.raises(ValueError, match='no longer available'):
        services.reserve(quote, 'Another Test Guest', 'another@example.test')


def test_accounting_cannot_change_stays_and_reception_checkout_is_audited(booking):
    confirm(booking)
    booking.verified = True
    booking.save(update_fields=['verified'])
    accountant = staff_client('ACCOUNTANT')
    assert accountant.post(f'/api/v1/reservations/{booking.pk}/check-in', {}, content_type=JSON).status_code == 403
    reception = staff_client('RECEPTION')
    assert reception.post(f'/api/v1/reservations/{booking.pk}/check-in', {}, content_type=JSON).status_code == 200
    booking.folio.refresh_from_db()
    payload = {'folio_version': booking.folio.version}
    path = f'/api/v1/reservations/{booking.pk}/check-out'
    assert accountant.post(path, payload, content_type=JSON).status_code == 403
    assert reception.post(path, payload, content_type=JSON).json()['status'] == 'CHECKED_OUT'
    assert Audit.objects.filter(actor='reception', action='CHECK_OUT').exists()


def test_live_booking_does_not_accept_holds_without_payment_configuration(settings):
    settings.ENV = 'production'
    settings.PAYMENT_PROVIDER = 'bakong'
    settings.BAKONG_TOKEN = ''
    settings.PAYMENT_QUEUE_ENABLED = True
    response = Client().post('/api/v1/quotes', {}, content_type=JSON)
    assert response.status_code == 503
    assert 'Online booking is temporarily unavailable' in response.json()['detail']
