from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from . import bakong, development


def get_provider(name=None):
    name = name or settings.PAYMENT_PROVIDER
    if name == 'development':
        return development
    if name == 'bakong':
        return bakong
    raise ImproperlyConfigured(f'Unknown PAYMENT_PROVIDER {name!r}')
