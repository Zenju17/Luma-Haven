"""Payment provider selection.

PAYMENT_PROVIDER (env) is the default. A developer can switch between demo and bank payments at
runtime from the Developer Console; that choice is stored in the `bank_payments` row of FeatureFlag
and overrides the env default. Existing attempts always keep the provider they were created with.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from . import bakong, development

MODE_FLAG = 'bank_payments'
REQUIRED_BAKONG = ('BAKONG_TOKEN', 'BAKONG_ACCOUNT_ID', 'BAKONG_MERCHANT_NAME', 'BAKONG_MERCHANT_CITY')


def bakong_configured():
    return all(getattr(settings, name) for name in REQUIRED_BAKONG) and settings.BAKONG_CURRENCY == 'USD'


def active_provider_name():
    """'bakong' or 'development' for NEW payment sessions."""
    if settings.PRESENTATION_DEMO:
        return 'development'
    from ..models import FeatureFlag
    flag = FeatureFlag.objects.filter(key=MODE_FLAG).only('enabled').first()
    if flag is None:
        return settings.PAYMENT_PROVIDER
    if settings.ENV == 'production' and not flag.enabled:
        return settings.PAYMENT_PROVIDER
    return 'bakong' if flag.enabled else 'development'


def get_provider(name=None):
    name = name or active_provider_name()
    if name == 'development':
        return development
    if name == 'bakong':
        return bakong
    raise ImproperlyConfigured(f'Unknown PAYMENT_PROVIDER {name!r}')
