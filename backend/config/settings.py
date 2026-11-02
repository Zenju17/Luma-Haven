import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

def _load_env_file(path: Path):
    if not path.is_file():
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                os.environ.setdefault(k, v)
    except Exception:
        pass

if os.environ.get('APP_ENV') != 'production':
    _load_env_file(BASE_DIR.parent / '.env')
    _load_env_file(BASE_DIR / '.env')


STAFF_CREDENTIALS_FILE = Path(os.getenv('STAFF_CREDENTIALS_FILE', str(BASE_DIR / '.private-staff-passwords')))
ENV = os.getenv('APP_ENV', 'development')
PRESENTATION_DEMO = ENV == 'demo'
HOSTED_ENVIRONMENT = ENV in ('production', 'demo')
if PRESENTATION_DEMO and os.getenv('PAYMENT_PROVIDER', 'development') != 'development':
    raise RuntimeError('Presentation demos must use simulated payments')
if ENV == 'production' and os.getenv('PAYMENT_PROVIDER', 'development') == 'development':
    raise RuntimeError('Development payment provider is forbidden in production')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-only-insecure-secret')
if HOSTED_ENVIRONMENT and (len(SECRET_KEY) < 32 or SECRET_KEY == 'local-only-insecure-secret'):
    raise RuntimeError('Set a strong DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true' and not HOSTED_ENVIRONMENT
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
# Vercel generates a distinct hostname for each preview. Trust only this deployment's hosts.
VERCEL_HOSTS = [os.environ[key] for key in ('VERCEL_URL', 'VERCEL_BRANCH_URL', 'VERCEL_PROJECT_PRODUCTION_URL')
                if os.getenv('VERCEL') and os.getenv(key)]
ALLOWED_HOSTS += VERCEL_HOSTS
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.postgres',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'core',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'core.middleware.PortalSessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'core.middleware.StrictCSRFMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.RequestIDMiddleware',
    'core.middleware.ErrorCaptureMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DATABASE_MEDIA = os.getenv('DATABASE_MEDIA', 'false').lower() == 'true'
MAX_IMAGE_UPLOAD_BYTES = 3 * 1024 * 1024 if DATABASE_MEDIA else 10 * 1024 * 1024
if DATABASE_MEDIA:
    # Small presentation assets remain durable without a paid disk/object-storage service.
    MEDIA_URL = '/api/v1/media/'
    STORAGES = {
        'default': {'BACKEND': 'core.media_storage.DatabaseMediaStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
WSGI_APPLICATION = 'config.wsgi.application'
database_url = os.getenv('DATABASE_URL', '')
if not database_url or any(placeholder in database_url for placeholder in ('PROJECT_REF', 'YOUR_ENCODED_PASSWORD', 'YOUR_POOLER_HOST')):
    raise RuntimeError('Set DATABASE_URL to a PostgreSQL connection string in .env')
parsed_database = urlsplit(database_url)
if parsed_database.scheme not in ('postgres', 'postgresql'):
    raise RuntimeError('DATABASE_URL must be a PostgreSQL connection string')
if parsed_database.hostname and (parsed_database.hostname.endswith('.supabase.co') or parsed_database.hostname.endswith('.pooler.supabase.com')):
    if parse_qs(parsed_database.query).get('sslmode', [''])[0] not in ('require', 'verify-ca', 'verify-full'):
        raise RuntimeError('Supabase DATABASE_URL must include sslmode=require (or stricter)')
    if parsed_database.port == 6543:
        raise RuntimeError('Use the direct or session-mode port 5432; transaction pooling is not supported here')
DATABASES = {'default': dj_database_url.parse(database_url, conn_max_age=int(os.getenv('DATABASE_CONN_MAX_AGE', '0')))}
AUTH_USER_MODEL = 'core.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
USE_TZ = True
TIME_ZONE = 'Asia/Phnom_Penh'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'], 'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'}
SPECTACULAR_SETTINGS = {'TITLE': 'Luma Haven API', 'VERSION': '1.0.0'}
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([FRONTEND_ORIGIN] + ['https://' + host for host in VERCEL_HOSTS]))
CSRF_FAILURE_VIEW = 'core.middleware.csrf_failure'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = HOSTED_ENVIRONMENT
CSRF_COOKIE_SECURE = HOSTED_ENVIRONMENT
_gmail_user = (os.getenv('GMAIL_USER') or os.getenv('EMAIL_HOST_USER') or '').strip()
_gmail_pass = (os.getenv('GMAIL_APP_PASSWORD') or os.getenv('EMAIL_HOST_PASSWORD') or '').replace(' ', '').strip()
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
if not EMAIL_HOST and (_gmail_user or _gmail_pass):
    EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = _gmail_user
EMAIL_HOST_PASSWORD = _gmail_pass
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true'
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'false' if EMAIL_USE_SSL else 'true').lower() == 'true'
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL') or EMAIL_HOST_USER or 'noreply@lumahaven.com'
EMAIL_DELIVERY_CONFIGURED = bool(EMAIL_HOST and (EMAIL_HOST_USER or not HOSTED_ENVIRONMENT))
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
elif ENV == 'development' and os.getenv('NOTIFICATION_MODE') == 'file':
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = os.environ['EMAIL_FILE_PATH']
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Payments. PAYMENT_PROVIDER=development keeps the emulator; bakong enables KHQR (secrets only via env, never VITE_*).
PAYMENT_PROVIDER = os.getenv('PAYMENT_PROVIDER', 'development')
PAYMENT_QUEUE_ENABLED = os.getenv('PAYMENT_QUEUE_ENABLED', 'false').lower() == 'true'
CRON_SECRET = os.getenv('CRON_SECRET', '')
PAYMENT_ATTEMPT_MINUTES = int(os.getenv('PAYMENT_ATTEMPT_MINUTES', '15'))
PAYMENT_LATE_WINDOW_HOURS = int(os.getenv('PAYMENT_LATE_WINDOW_HOURS', '24'))
BAKONG_TOKEN = os.getenv('BAKONG_TOKEN', '')
BAKONG_ACCOUNT_ID = os.getenv('BAKONG_ACCOUNT_ID', '')
BAKONG_MERCHANT_NAME = os.getenv('BAKONG_MERCHANT_NAME', 'Luma Haven')
BAKONG_MERCHANT_CITY = os.getenv('BAKONG_MERCHANT_CITY', 'Phnom Penh')
BAKONG_CURRENCY = os.getenv('BAKONG_CURRENCY', 'USD')
# Dynamic KHQR scan amount for room bookings (default: 1 minor unit = $0.01 USD for test payments; 0 during test suite)
_default_scan = '0' if ('pytest' in sys.modules or any('test' in a for a in sys.argv)) else '1'
BAKONG_SCAN_AMOUNT_MINOR = int(os.getenv('BAKONG_SCAN_AMOUNT_MINOR', _default_scan))

# Data retention (see docs/IMPLEMENTATION_PLAN.md). Accounting records are never deleted.
RETENTION_GUEST_YEARS = int(os.getenv('RETENTION_GUEST_YEARS', '3'))
RETENTION_SHORT_LIVED_HOURS = int(os.getenv('RETENTION_SHORT_LIVED_HOURS', '24'))

CELERY_BEAT_SCHEDULE = {
    'sweep-payment-attempts': {'task': 'core.tasks.sweep_payment_attempts', 'schedule': 30.0},
    'run-retention': {'task': 'core.tasks.run_retention', 'schedule': 86400.0},
    'expire-holds': {'task': 'core.tasks.expire_holds', 'schedule': 60.0},
    'archive-daily-mis-snapshot': {'task': 'core.tasks.archive_daily_mis_snapshot', 'schedule': 3600.0},
}

# ---- Infrastructure (P4) ---------------------------------------------------------------------
APP_VERSION = os.getenv('APP_VERSION', 'dev')
REDIS_URL = os.getenv('REDIS_URL', '')
# Celery previously had no broker configured; it now follows REDIS_URL unless overridden.
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL') or REDIS_URL or 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND') or None
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
if 'pytest' in sys.modules or any('test' in a for a in sys.argv):
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
elif REDIS_URL:
    # Shared by every gunicorn worker so rate limits and health probes agree.
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': REDIS_URL}}
elif ENV == 'production':
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                         'LOCATION': 'core_runtime_cache', 'OPTIONS': {'MAX_ENTRIES': 10000}}}


# Rate limiting is on by default in production only, so local demos and E2E runs are not throttled.
THROTTLE_ENABLED = os.getenv('THROTTLE_ENABLED', 'true' if HOSTED_ENVIRONMENT else 'false').lower() == 'true'
THROTTLE_RATES = {'login': '20/min', 'otp': '10/min', 'booking': '30/min', 'privacy': '10/hour', 'poll': '120/min'}
# Number of reverse proxies in front of Django (Caddy = 1). Never trust X-Forwarded-For beyond this.
TRUSTED_PROXY_COUNT = int(os.getenv('TRUSTED_PROXY_COUNT', '1' if HOSTED_ENVIRONMENT else '0'))
# Marker file written by scripts/backup_db.sh; shown (read-only) in the Developer Console.
BACKUP_STATUS_FILE = os.getenv('BACKUP_STATUS_FILE', '/backups/last_backup.json')

if HOSTED_ENVIRONMENT:
    if not os.getenv('DJANGO_ALLOWED_HOSTS') or '*' in ALLOWED_HOSTS:
        raise RuntimeError('Set DJANGO_ALLOWED_HOSTS to the real hostnames (no wildcard) in production')
    if not FRONTEND_ORIGIN.startswith('https://'):
        raise RuntimeError('FRONTEND_ORIGIN must be an https:// origin in production')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # set by Caddy; Django is never exposed directly
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'true').lower() == 'true'
    SECURE_REDIRECT_EXEMPT = [r'^api/v1/(health|ready)$']  # probes run over plain HTTP inside the network
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False  # opt in deliberately once every subdomain is HTTPS
    SILENCED_SYSTEM_CHECKS = ['security.W021']  # the preload decision above is deliberate
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    CSRF_COOKIE_HTTPONLY = False  # the SPA reads the token from /auth/csrf, but keep the cookie Secure
    SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', str(60 * 60 * 12)))

# ---- Logging and error reporting ------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {'request_id': {'()': 'core.logs.RequestIdFilter'}},
    'formatters': {
        'json': {'()': 'core.logs.JsonFormatter'},
        'plain': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'},
    },
    'handlers': {'console': {'class': 'logging.StreamHandler', 'filters': ['request_id'],
                             'formatter': 'json' if HOSTED_ENVIRONMENT else 'plain'}},
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
}

SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    from core.logs import init_sentry
    init_sentry(SENTRY_DSN, ENV, APP_VERSION)
