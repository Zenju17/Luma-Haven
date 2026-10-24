import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
ENV = os.getenv('APP_ENV', 'development')
if ENV == 'production' and os.getenv('PAYMENT_PROVIDER', 'development') == 'development':
    raise RuntimeError('Development payment provider is forbidden in production')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-only-insecure-secret')
if ENV == 'production' and (len(SECRET_KEY) < 32 or SECRET_KEY == 'local-only-insecure-secret'):
    raise RuntimeError('Set a strong DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true' and ENV != 'production'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.postgres', 'rest_framework', 'drf_spectacular', 'corsheaders', 'core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'core.middleware.StrictCSRFMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'core.middleware.RequestIDMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = []
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': dj_database_url.config(default='postgresql://hims:hims@localhost:5432/hims', conn_max_age=60)}
AUTH_USER_MODEL = 'core.User'
USE_TZ = True
TIME_ZONE = 'Asia/Phnom_Penh'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'], 'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'}
SPECTACULAR_SETTINGS = {'TITLE': 'Luma Haven API', 'VERSION': '1.0.0'}
CORS_ALLOWED_ORIGINS = ['http://localhost:5173']
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = ['http://localhost:5173']
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = ENV == 'production'
CSRF_COOKIE_SECURE = ENV == 'production'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BEAT_SCHEDULE = {'expire-holds': {'task': 'core.tasks.expire_holds', 'schedule': 60.0}}
