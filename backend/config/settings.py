import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
STAFF_CREDENTIALS_FILE = Path(os.getenv('STAFF_CREDENTIALS_FILE', str(BASE_DIR / '.private-staff-passwords')))
ENV = os.getenv('APP_ENV', 'development')
if ENV == 'production' and os.getenv('PAYMENT_PROVIDER', 'development') == 'development':
    raise RuntimeError('Development payment provider is forbidden in production')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-only-insecure-secret')
if ENV == 'production' and (len(SECRET_KEY) < 32 or SECRET_KEY == 'local-only-insecure-secret'):
    raise RuntimeError('Set a strong DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true' and ENV != 'production'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
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
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]
CSRF_FAILURE_VIEW = 'core.middleware.csrf_failure'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = ENV == 'production'
CSRF_COOKIE_SECURE = ENV == 'production'
if ENV == 'development' and os.getenv('NOTIFICATION_MODE') == 'file':
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = os.environ['EMAIL_FILE_PATH']
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Payments. PAYMENT_PROVIDER=development keeps the emulator; bakong enables KHQR (secrets only via env, never VITE_*).
PAYMENT_PROVIDER = os.getenv('PAYMENT_PROVIDER', 'development')
PAYMENT_ATTEMPT_MINUTES = int(os.getenv('PAYMENT_ATTEMPT_MINUTES', '15'))
PAYMENT_LATE_WINDOW_HOURS = int(os.getenv('PAYMENT_LATE_WINDOW_HOURS', '24'))
BAKONG_TOKEN = os.getenv('BAKONG_TOKEN', '')
BAKONG_ACCOUNT_ID = os.getenv('BAKONG_ACCOUNT_ID', '')
BAKONG_MERCHANT_NAME = os.getenv('BAKONG_MERCHANT_NAME', 'Luma Haven')
BAKONG_MERCHANT_CITY = os.getenv('BAKONG_MERCHANT_CITY', 'Phnom Penh')
BAKONG_CURRENCY = os.getenv('BAKONG_CURRENCY', 'USD')

# Data retention (see docs/IMPLEMENTATION_PLAN.md). Accounting records are never deleted.
RETENTION_GUEST_YEARS = int(os.getenv('RETENTION_GUEST_YEARS', '3'))
RETENTION_SHORT_LIVED_HOURS = int(os.getenv('RETENTION_SHORT_LIVED_HOURS', '24'))

CELERY_BEAT_SCHEDULE = {
    'sweep-payment-attempts': {'task': 'core.tasks.sweep_payment_attempts', 'schedule': 30.0},
    'run-retention': {'task': 'core.tasks.run_retention', 'schedule': 86400.0},
    'expire-holds': {'task': 'core.tasks.expire_holds', 'schedule': 60.0},
    'archive-daily-mis-snapshot': {'task': 'core.tasks.archive_daily_mis_snapshot', 'schedule': 3600.0},
}
