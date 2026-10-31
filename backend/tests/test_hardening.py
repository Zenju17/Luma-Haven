import json
import logging
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
import pytest
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.utils import timezone
from core import logs, throttling
from core.models import User

JSON = 'application/json'
BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def fresh_cache():
    cache.clear()
    yield
    cache.clear()


def login(client, username, password, portal='staff', ip='10.0.0.1'):
    return client.post('/api/v1/auth/login', {'username': username, 'password': password}, content_type=JSON,
                       HTTP_X_PORTAL=portal, REMOTE_ADDR=ip)


# ---------------------------------------------------------------- rate limiting

def test_account_lockout_after_repeated_failures(db, settings):
    settings.THROTTLE_ENABLED = True
    User.objects.create_user(username='reception', password='right-pass-1', role='RECEPTION')
    User.objects.create_user(username='other', password='right-pass-2', role='RECEPTION')
    client = Client()
    for _ in range(throttling.LOCKOUT_FAILURES):
        assert login(client, 'reception', 'wrong').status_code == 400
    locked = login(client, 'reception', 'right-pass-1')                 # correct password is refused while locked
    assert locked.status_code == 429
    assert login(Client(), 'other', 'right-pass-2', ip='10.0.0.2').status_code == 200   # other accounts unaffected


def test_lockout_disabled_outside_production_defaults(db, settings):
    settings.THROTTLE_ENABLED = False
    User.objects.create_user(username='reception', password='right-pass-1', role='RECEPTION')
    for _ in range(throttling.LOCKOUT_FAILURES + 2):
        login(Client(), 'reception', 'wrong')
    assert login(Client(), 'reception', 'right-pass-1').status_code == 200


def test_ip_rate_limit_applies_per_client_and_can_be_disabled(db, settings):
    settings.THROTTLE_ENABLED = True
    settings.THROTTLE_RATES = {**settings.THROTTLE_RATES, 'booking': '2/min'}
    client = Client()
    codes = [client.post('/api/v1/quotes', {}, content_type=JSON, REMOTE_ADDR='10.1.1.1').status_code for _ in range(3)]
    assert codes[:2] == [400, 400] and codes[2] == 429
    assert client.post('/api/v1/quotes', {}, content_type=JSON, REMOTE_ADDR='10.1.1.2').status_code == 400   # different IP
    settings.THROTTLE_ENABLED = False
    assert client.post('/api/v1/quotes', {}, content_type=JSON, REMOTE_ADDR='10.1.1.1').status_code == 400


def test_client_ip_trusts_only_configured_proxies(settings):
    factory = RequestFactory()
    spoofed = factory.get('/', HTTP_X_FORWARDED_FOR='6.6.6.6, 5.5.5.5', REMOTE_ADDR='172.18.0.5')
    settings.TRUSTED_PROXY_COUNT = 1
    assert throttling.client_ip(spoofed) == '5.5.5.5'            # entry appended by our proxy, not the forged one
    settings.TRUSTED_PROXY_COUNT = 0
    assert throttling.client_ip(spoofed) == '172.18.0.5'          # no proxy configured: header ignored


# ---------------------------------------------------------------- probes and backups

def test_ready_probe_reports_database_state(db, monkeypatch):
    client = Client()
    assert client.get('/api/v1/ready').json() == {'status': 'ready'}
    assert client.get('/api/v1/health').json() == {'status': 'ok'}

    class Broken:
        class objects:
            @staticmethod
            def exists():
                raise RuntimeError('db down')
    monkeypatch.setattr('core.views.User', Broken)
    assert client.get('/api/v1/ready').status_code == 503


def test_backup_status_in_developer_health(db, settings, tmp_path):
    User.objects.create_user(username='dev', password='test-only', role='DEVELOPER')
    client = Client()
    assert client.post('/api/v1/auth/login', {'username': 'dev', 'password': 'test-only'}, content_type=JSON, HTTP_X_PORTAL='admin').status_code == 200
    marker = tmp_path / 'last_backup.json'
    settings.BACKUP_STATUS_FILE = str(marker)
    assert client.get('/api/v1/admin/dev/health').json()['backup']['configured'] is False

    now = timezone.now()
    marker.write_text(json.dumps({'ok': True, 'finished_at': now.isoformat(), 'size_bytes': 1234}))
    (tmp_path / 'last_restore_drill.json').write_text(json.dumps({'ok': True, 'at': now.isoformat(), 'core_tables': 30}))
    backup = client.get('/api/v1/admin/dev/health').json()['backup']
    assert backup['ok'] is True and backup['size_bytes'] == 1234 and backup['last_restore_drill']['core_tables'] == 30

    marker.write_text(json.dumps({'ok': True, 'finished_at': (now - timedelta(hours=30)).isoformat(), 'size_bytes': 1}))
    assert client.get('/api/v1/admin/dev/health').json()['backup']['ok'] is False     # older than 26 h
    marker.write_text(json.dumps({'ok': False, 'finished_at': now.isoformat(), 'size_bytes': 0}))
    assert client.get('/api/v1/admin/dev/health').json()['backup']['ok'] is False     # last run failed


# ---------------------------------------------------------------- logging and error reporting (no DB)

def test_json_logs_are_structured_and_scrubbed():
    record = logging.LogRecord('core.test', logging.ERROR, __file__, 1, 'failed for %s token %s', ('sok@example.com', 'A' * 40), None)
    logs.RequestIdFilter().filter(record)
    out = json.loads(logs.JsonFormatter().format(record))
    assert out['level'] == 'ERROR' and out['logger'] == 'core.test'
    assert 'sok@example.com' not in out['message'] and 'AAAA' not in out['message'] and '[email]' in out['message']
    token = logs.request_id_var.set('req-123')
    try:
        logs.RequestIdFilter().filter(record)
        assert json.loads(logs.JsonFormatter().format(record))['request_id'] == 'req-123'
    finally:
        logs.request_id_var.reset(token)


def test_sentry_events_lose_cookies_bodies_users_and_pii():
    event = {'request': {'cookies': 'sessionid=abc', 'data': {'email': 'a@b.co'}, 'headers': {'Authorization': 'x'}, 'query_string': 'e=a@b.co', 'url': '/api/v1/x'},
             'user': {'email': 'a@b.co'}, 'message': 'error for a@b.co',
             'exception': {'values': [{'value': 'bad token ' + 'Z' * 30 + ' for a@b.co'}]}}
    clean = logs._scrub_event(event, {})
    assert clean['request'] == {'url': '/api/v1/x'} and 'user' not in clean
    assert 'a@b.co' not in json.dumps(clean) and 'ZZZZ' not in json.dumps(clean)


# ---------------------------------------------------------------- production configuration (subprocess, no DB)

PROD_ENV = {
    'APP_ENV': 'production', 'DJANGO_SECRET_KEY': 'Zq8vN3tR7yLp2WxD9mKc4HsB6jFgA1eUo5iT0nVbXaYrE_-+=Qw3Er5Ty7Ui9Op1', 'DATABASE_URL': 'postgresql://u:p@127.0.0.1:5432/x',
    'PAYMENT_PROVIDER': 'bakong', 'BAKONG_TOKEN': 't', 'BAKONG_ACCOUNT_ID': 'a@b',
    'DJANGO_ALLOWED_HOSTS': 'hotel.example.com,127.0.0.1', 'FRONTEND_ORIGIN': 'https://hotel.example.com',
    'REDIS_URL': 'redis://redis:6379/0',
}


def run_python(code, **overrides):
    env = {'PATH': os.environ.get('PATH', ''), **PROD_ENV, **overrides}
    env = {k: v for k, v in env.items() if v is not None}
    return subprocess.run([sys.executable, '-c', code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60)


def test_production_settings_are_hardened():
    code = ('import json, config.settings as s; print(json.dumps({"ssl": s.SECURE_SSL_REDIRECT, "hsts": s.SECURE_HSTS_SECONDS, '
            '"sess": s.SESSION_COOKIE_SECURE, "csrf": s.CSRF_COOKIE_SECURE, "xfo": s.X_FRAME_OPTIONS, "nosniff": s.SECURE_CONTENT_TYPE_NOSNIFF, '
            '"throttle": s.THROTTLE_ENABLED, "proxies": s.TRUSTED_PROXY_COUNT, "debug": s.DEBUG, '
            '"cache": s.CACHES["default"]["BACKEND"], "broker": s.CELERY_BROKER_URL, "proxy_hdr": s.SECURE_PROXY_SSL_HEADER, '
            '"clickjack": "django.middleware.clickjacking.XFrameOptionsMiddleware" in s.MIDDLEWARE}))')
    result = run_python(code)
    assert result.returncode == 0, result.stderr
    s = json.loads(result.stdout.strip().splitlines()[-1])
    assert s['ssl'] is True and s['hsts'] >= 31536000 and s['sess'] and s['csrf'] and s['xfo'] == 'DENY' and s['nosniff']
    assert s['throttle'] is True and s['proxies'] == 1 and s['debug'] is False and s['clickjack']
    assert s['cache'].endswith('RedisCache') and s['broker'] == 'redis://redis:6379/0'
    assert s['proxy_hdr'] == ['HTTP_X_FORWARDED_PROTO', 'https'] or s['proxy_hdr'] == ('HTTP_X_FORWARDED_PROTO', 'https')


@pytest.mark.parametrize('override', [
    {'DJANGO_ALLOWED_HOSTS': None},                       # missing hosts
    {'DJANGO_ALLOWED_HOSTS': '*'},                        # wildcard
    {'FRONTEND_ORIGIN': 'http://hotel.example.com'},      # not https
    {'DJANGO_SECRET_KEY': 'short'},                       # weak key
    {'PAYMENT_PROVIDER': 'development'},                  # emulator in production
])
def test_production_refuses_unsafe_configuration(override):
    result = run_python('import config.settings', **override)
    assert result.returncode != 0 and 'RuntimeError' in result.stderr


def test_django_deploy_check_has_no_security_warnings():
    env = {'PATH': os.environ.get('PATH', ''), **PROD_ENV}
    result = subprocess.run([sys.executable, 'manage.py', 'check', '--deploy'], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    assert 'security.W' not in result.stderr + result.stdout


def test_create_admin_command_validates_password(db, monkeypatch):
    from django.core.management import call_command
    from django.core.management.base import CommandError
    monkeypatch.setenv('LUMA_ADMIN_PASSWORD', '12345678')
    with pytest.raises(CommandError):
        call_command('create_admin', username='owner')                  # too common / numeric
    monkeypatch.setenv('LUMA_ADMIN_PASSWORD', 'Tr0ub4dor&3xyz')
    call_command('create_admin', username='owner')
    user = User.objects.get(username='owner')
    assert user.role == 'ADMIN' and user.check_password('Tr0ub4dor&3xyz') and user.is_staff
    with pytest.raises(CommandError):
        call_command('create_admin', username='owner')                  # duplicate
