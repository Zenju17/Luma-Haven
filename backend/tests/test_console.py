from datetime import timedelta
import pytest
from django.test import Client, RequestFactory
from django.utils import timezone
from core import flags
from core.middleware import ErrorCaptureMiddleware
from core.models import Audit, CmsBlock, CmsPage, ErrorEvent, FeatureFlag, Hotel, JobRun, User
from core.payments import bakong

JSON = 'application/json'


def client_for(role, portal='admin'):
    c = Client()
    User.objects.create_user(username=f'{role.lower()}-u', password='test-only', role=role)
    response = c.post('/api/v1/auth/login', {'username': f'{role.lower()}-u', 'password': 'test-only'}, content_type=JSON, HTTP_X_PORTAL=portal)
    assert response.status_code == 200, response.content
    return c


@pytest.fixture
def admin(db):
    return client_for('ADMIN')


@pytest.fixture
def editor(db):
    return client_for('CONTENT_EDITOR')


@pytest.fixture
def dev(db):
    return client_for('DEVELOPER')


def post(c, url, data=None):
    return c.post(url, data or {}, content_type=JSON)


def patch(c, url, data):
    return c.patch(url, data, content_type=JSON)


# ---------------------------------------------------------------- roles

def test_role_matrix_for_console_endpoints(db):
    admin, editor, dev = client_for('ADMIN'), client_for('CONTENT_EDITOR'), client_for('DEVELOPER')
    anon = Client()
    dev_get = ['/api/v1/admin/dev/health', '/api/v1/admin/dev/jobs', '/api/v1/admin/dev/outbox', '/api/v1/admin/dev/payment-provider',
               '/api/v1/admin/dev/flags', '/api/v1/admin/dev/config', '/api/v1/admin/dev/errors', '/api/v1/admin/dev/security']
    cms_get = ['/api/v1/admin/cms/pages', '/api/v1/admin/cms/blocks']
    for url in dev_get + cms_get:
        assert anon.get(url).status_code == 403, url
    for url in dev_get:
        assert dev.get(url).status_code == 200, url
        assert admin.get(url).status_code == 200, url          # admin: read-only developer views
        assert editor.get(url).status_code == 403, url
    for url in cms_get:
        assert admin.get(url).status_code == 200 and editor.get(url).status_code == 200, url
        assert dev.get(url).status_code == 403, url
    # Developers never reach guest PII or company admin data.
    for url in ['/api/v1/admin/staff', '/api/v1/admin/data-requests', '/api/v1/admin/legal', '/api/v1/admin/hotel']:
        assert dev.get(url).status_code == 403 and editor.get(url).status_code == 403, url
    # Writes: only developers change flags; admin cannot.
    assert post(admin, '/api/v1/admin/dev/flags', {'key': 'x_flag'}).status_code == 403
    assert post(dev, '/api/v1/admin/dev/flags', {'key': 'x_flag'}).status_code == 201


def test_staff_portal_roles_cannot_use_admin_portal(db):
    User.objects.create_user(username='mgr', password='test-only', role='MANAGER')
    c = Client()
    assert c.post('/api/v1/auth/login', {'username': 'mgr', 'password': 'test-only'}, content_type=JSON, HTTP_X_PORTAL='admin').status_code == 403
    assert Client().get('/api/v1/admin/dev/health').status_code == 403


def test_admin_can_create_new_roles(admin):
    r = post(admin, '/api/v1/admin/staff', {'username': 'devperson', 'password': 'Passw0rd!x', 'role': 'DEVELOPER'})
    assert r.status_code == 201 and r.json()['role'] == 'DEVELOPER'
    assert post(admin, '/api/v1/admin/staff', {'username': 'bad', 'password': 'Passw0rd!x', 'role': 'ROOT'}).status_code == 400


# ---------------------------------------------------------------- CMS

def test_cms_page_lifecycle_editor_drafts_admin_publishes(admin, editor):
    created = post(editor, '/api/v1/admin/cms/pages', {'slug': 'about', 'language': 'en', 'title': 'About', 'body_markdown': 'Hello'})
    assert created.status_code == 201
    pk = created.json()['id']
    assert Client().get('/api/v1/cms/pages/about').status_code == 404          # drafts are never public
    assert post(editor, f'/api/v1/admin/cms/pages/{pk}/publish').status_code == 403
    assert post(admin, f'/api/v1/admin/cms/pages/{pk}/publish').json()['is_published'] is True
    assert Client().get('/api/v1/cms/pages/about').json()['body_markdown'] == 'Hello'

    edited = patch(editor, f'/api/v1/admin/cms/pages/{pk}', {'body_markdown': 'Hello v2'}).json()
    assert edited['has_unpublished_changes'] is True
    assert Client().get('/api/v1/cms/pages/about').json()['body_markdown'] == 'Hello'   # still the published copy
    post(admin, f'/api/v1/admin/cms/pages/{pk}/publish')
    assert Client().get('/api/v1/cms/pages/about').json()['body_markdown'] == 'Hello v2'

    revisions = admin.get(f'/api/v1/admin/cms/pages/{pk}').json()['revisions']
    first_save = [r for r in revisions if r['action'] == 'SAVE'][-1]
    restored = post(editor, f'/api/v1/admin/cms/pages/{pk}/restore', {'revision_id': first_save['id']}).json()
    assert restored['body_markdown'] == 'Hello' and restored['has_unpublished_changes'] is True
    assert post(editor, f'/api/v1/admin/cms/pages/{pk}/unpublish').status_code == 403
    post(admin, f'/api/v1/admin/cms/pages/{pk}/unpublish')
    assert Client().get('/api/v1/cms/pages/about').status_code == 404
    assert Audit.objects.filter(action='CMS_PAGE_PUBLISHED').count() == 2


def test_cms_page_validation_and_language_fallback(admin):
    assert post(admin, '/api/v1/admin/cms/pages', {'slug': 'Bad Slug', 'title': 'x'}).status_code == 400
    assert post(admin, '/api/v1/admin/cms/pages', {'slug': 'faq', 'language': 'fr', 'title': 'x'}).status_code == 400
    assert post(admin, '/api/v1/admin/cms/pages', {'slug': 'faq', 'title': ''}).status_code == 400
    en = post(admin, '/api/v1/admin/cms/pages', {'slug': 'faq', 'title': 'FAQ', 'body_markdown': 'english'}).json()
    assert post(admin, '/api/v1/admin/cms/pages', {'slug': 'faq', 'title': 'dup'}).status_code == 400
    post(admin, f"/api/v1/admin/cms/pages/{en['id']}/publish")
    assert Client().get('/api/v1/cms/pages/faq?lang=km').json()['language'] == 'en'     # falls back
    km = post(admin, '/api/v1/admin/cms/pages', {'slug': 'faq', 'language': 'km', 'title': 'សំណួរ', 'body_markdown': 'ខ្មែរ'}).json()
    post(admin, f"/api/v1/admin/cms/pages/{km['id']}/publish")
    assert Client().get('/api/v1/cms/pages/faq?lang=km').json()['body_markdown'] == 'ខ្មែរ'


def test_cms_blocks_validate_publish_and_respect_dates(admin, editor):
    bad = post(editor, '/api/v1/admin/cms/blocks', {'key': 'site.announcement', 'content': {'text': 'Hi', 'link': 'javascript:alert(1)'}})
    assert bad.status_code == 400
    assert post(editor, '/api/v1/admin/cms/blocks', {'key': 'site.announcement', 'content': {'text': 'x' * 501}}).status_code == 400
    ok = post(editor, '/api/v1/admin/cms/blocks', {'key': 'site.announcement', 'content': {'text': 'Pool closed Monday', 'link': '/rooms'}})
    assert ok.status_code == 201
    pk = ok.json()['id']
    assert Client().get('/api/v1/cms/blocks').json() == []
    assert post(editor, f'/api/v1/admin/cms/blocks/{pk}/publish').status_code == 403
    post(admin, f'/api/v1/admin/cms/blocks/{pk}/publish')
    assert Client().get('/api/v1/cms/blocks').json()[0]['content']['text'] == 'Pool closed Monday'
    CmsBlock.objects.filter(pk=pk).update(ends_at=timezone.now() - timedelta(minutes=1))
    assert Client().get('/api/v1/cms/blocks').json() == []                    # outside its window
    CmsBlock.objects.filter(pk=pk).update(ends_at=None, starts_at=timezone.now() + timedelta(days=1))
    assert Client().get('/api/v1/cms/blocks').json() == []                    # not started yet


# ---------------------------------------------------------------- developer console

def test_feature_flag_pauses_bookings_and_is_audited(dev):
    FeatureFlag.objects.get_or_create(key='bookings_paused')
    guest = Client()
    assert patch(dev, '/api/v1/admin/dev/flags/bookings_paused', {'enabled': True}).json()['enabled'] is True
    assert flags.is_enabled('bookings_paused')
    assert post(guest, '/api/v1/quotes', {'room_id': 1}).status_code == 400
    assert 'paused' in post(guest, '/api/v1/reservations', {'quote_id': 'x'}).json()[0]
    patch(dev, '/api/v1/admin/dev/flags/bookings_paused', {'enabled': False})
    assert not flags.is_enabled('bookings_paused')
    assert Audit.objects.filter(action='FLAG_CHANGED').count() == 2
    assert patch(dev, '/api/v1/admin/dev/flags/nope', {'enabled': True}).status_code == 404


def test_config_endpoint_never_returns_secret_values(dev, settings):
    settings.BAKONG_TOKEN = 'super-secret-bakong-token-123'
    settings.BAKONG_ACCOUNT_ID = 'hotel@private-bank'
    body = dev.get('/api/v1/admin/dev/config').content.decode()
    provider = dev.get('/api/v1/admin/dev/payment-provider').content.decode()
    for secret in (settings.BAKONG_TOKEN, settings.BAKONG_ACCOUNT_ID, settings.SECRET_KEY):
        assert secret not in body and secret not in provider
    assert dev.get('/api/v1/admin/dev/config').json()['secrets_configured']['BAKONG_TOKEN'] is True


def test_error_capture_scrubs_pii_and_tokens(dev):
    request = RequestFactory().post('/api/v1/reservations?email=sok@example.com')
    request.request_id = 'abc'
    ErrorCaptureMiddleware(lambda r: None).process_exception(
        request, ValueError('failed for sok@example.com using token ABCDEFGHIJKLMNOPQRSTUVWXYZ123456'))
    event = ErrorEvent.objects.get()
    assert event.path == '/api/v1/reservations' and 'sok@example.com' not in event.message and 'ABCDEFGHIJKL' not in event.message
    listed = dev.get('/api/v1/admin/dev/errors').json()
    assert listed[0]['exc_type'] == 'ValueError' and '[email]' in listed[0]['message']


def test_jobs_and_health_reflect_task_runs(dev):
    health = dev.get('/api/v1/admin/dev/health').json()
    assert health['database']['ok'] is True and health['celery']['healthy'] is False
    assert health['pending_migrations'] == 0 and 'secret' not in str(health).lower()
    JobRun.objects.create(task='core.tasks.expire_holds', status='SUCCESS', duration_ms=5)
    JobRun.objects.create(task='core.tasks.sweep_payment_attempts', status='FAILURE', error='ProviderError: down')
    assert dev.get('/api/v1/admin/dev/health').json()['celery']['healthy'] is True
    jobs = dev.get('/api/v1/admin/dev/jobs').json()
    assert {r['task']: r['failures'] for r in jobs['summary']}['core.tasks.sweep_payment_attempts'] == 1
    assert jobs['failures'][0]['error'] == 'ProviderError: down'


def test_failed_logins_are_listed_and_sessions_can_be_revoked(dev):
    bad = Client()
    for _ in range(2):
        assert bad.post('/api/v1/auth/login', {'username': 'ghost', 'password': 'x'}, content_type=JSON, HTTP_X_PORTAL='admin').status_code == 400
    sec = dev.get('/api/v1/admin/dev/security').json()
    assert sec['failed_logins_24h'][0] == {'username': 'ghost', 'portal': 'admin', 'count': 2}

    reception = client_for('RECEPTION', portal='staff')
    assert reception.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json()['username'] == 'reception-u'
    uid = User.objects.get(username='reception-u').pk
    assert any(s['user_id'] == uid for s in dev.get('/api/v1/admin/dev/security').json()['active_sessions'])
    assert post(dev, f'/api/v1/admin/dev/security/revoke/{uid}').json()['revoked'] >= 1
    assert reception.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json() == {}
    own = User.objects.get(username='developer-u').pk
    assert post(dev, f'/api/v1/admin/dev/security/revoke/{own}').status_code == 400


def test_provider_check_requires_bakong_and_developer(dev, admin, settings, monkeypatch):
    settings.BAKONG_TOKEN = ''
    assert post(dev, '/api/v1/admin/dev/payment-provider/check').status_code == 400      # bank not configured
    settings.PAYMENT_PROVIDER, settings.BAKONG_TOKEN, settings.BAKONG_ACCOUNT_ID = 'bakong', 't', 'hotel@bank'
    monkeypatch.setattr(bakong, 'check_status', lambda md5: 'UNPAID')
    assert post(admin, '/api/v1/admin/dev/payment-provider/check').status_code == 403
    body = post(dev, '/api/v1/admin/dev/payment-provider/check').json()
    assert body['ok'] is True and body['status'] == 'UNPAID'


def test_outbox_view_lists_pending(dev):
    from core.models import Outbox
    Outbox.objects.create(kind='BOOKING_CONFIRMED', target='1')
    body = dev.get('/api/v1/admin/dev/outbox').json()
    assert body['pending_count'] == 1 and body['pending'][0]['kind'] == 'BOOKING_CONFIRMED'


def test_payment_mode_switch_between_demo_and_bank(dev, admin, settings):
    from core.models import FeatureFlag
    from core.payments import factory
    settings.PAYMENT_PROVIDER = 'development'
    settings.BAKONG_TOKEN, settings.BAKONG_ACCOUNT_ID = '', ''
    url = '/api/v1/admin/dev/payment-mode'
    assert post(admin, url, {'mode': 'bank'}).status_code == 403                        # developers only
    assert post(dev, url, {'mode': 'bank'}).status_code == 400                          # credentials missing
    settings.BAKONG_TOKEN, settings.BAKONG_ACCOUNT_ID = 't', 'hotel@bank'
    assert post(dev, url, {'mode': 'bank'}).json()['provider'] == 'bakong'
    assert factory.active_provider_name() == 'bakong'
    assert dev.get('/api/v1/admin/dev/payment-provider').json()['provider'] == 'bakong'
    assert post(dev, url, {'mode': 'demo'}).json()['provider'] == 'development'
    assert Audit.objects.filter(action='PAYMENT_MODE_CHANGED').count() == 2
    # the mode is not exposed as a generic flag
    assert 'bank_payments' not in [f['key'] for f in dev.get('/api/v1/admin/dev/flags').json()]
    assert patch(dev, '/api/v1/admin/dev/flags/bank_payments', {'enabled': True}).status_code == 404
    assert FeatureFlag.objects.get(key='bank_payments').enabled is False
    settings.ENV = 'production'
    assert post(dev, url, {'mode': 'demo'}).status_code == 400                          # never demo in production


def test_bank_attempt_cannot_be_simulated(db):
    from datetime import timedelta
    from core import services
    from core.models import PaymentAttempt, Room, RoomType
    hotel = Hotel.objects.create(name='H')
    room = Room.objects.create(hotel=hotel, type=RoomType.objects.create(hotel=hotel, name='T', nightly_rate_minor=1000), number='1')
    start = services.hotel_today(hotel) + timedelta(days=4)
    res = services.reserve(services.create_quote(room, start, start + timedelta(days=1), 1), 'A', 'a@example.com')
    bank = PaymentAttempt.objects.create(reservation=res, amount_minor=1000, currency='USD', provider='bakong')
    assert Client().post(f'/api/v1/development/checkout/{bank.pk}', {'outcome': 'SUCCESS'}, content_type=JSON).status_code == 403
    demo = PaymentAttempt.objects.create(reservation=res, amount_minor=1000, currency='USD', provider='development')
    assert Client().post(f'/api/v1/development/checkout/{demo.pk}', {'outcome': 'SUCCESS'}, content_type=JSON).json()['status'] == 'SUCCESS'
