from django.conf import settings
from django.core.checks import Error, register


@register()
def payment_provider_configuration(app_configs, **kwargs):
    """Refuse to start with a half-configured payment provider."""
    provider = settings.PAYMENT_PROVIDER
    if provider == 'development':
        if settings.ENV == 'production':
            return [Error('PAYMENT_PROVIDER=development must not be used in production.', id='payments.E001')]
        return []
    if provider != 'bakong':
        return [Error(f'Unknown PAYMENT_PROVIDER {provider!r}.', id='payments.E002')]
    missing = [name for name in ('BAKONG_TOKEN', 'BAKONG_ACCOUNT_ID', 'BAKONG_MERCHANT_NAME', 'BAKONG_MERCHANT_CITY')
               if not getattr(settings, name)]
    errors = [Error(f'{name} is required when PAYMENT_PROVIDER=bakong.', id='payments.E003') for name in missing]
    if settings.BAKONG_CURRENCY != 'USD':
        errors.append(Error('Only BAKONG_CURRENCY=USD is supported until KHR has dedicated tests.', id='payments.E004'))
    return errors
