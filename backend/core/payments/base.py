"""Provider-neutral payment types. Views and services never import a provider SDK directly."""
from dataclasses import dataclass
from decimal import Decimal


class ProviderError(Exception):
    """A provider call failed (network, auth, configuration). Never carries secrets."""


@dataclass(frozen=True)
class QRSession:
    qr: str
    md5: str
    tran_id: str = ''
    checkout_url: str = ''


def minor_to_major(amount_minor: int, currency: str) -> Decimal:
    """USD cents -> dollars as an exact Decimal. KHR is not enabled until it has its own tests."""
    if currency != 'USD':
        raise ProviderError(f'Currency {currency} is not supported by the payment provider')
    if amount_minor <= 0:
        raise ProviderError('Amount must be positive')
    return Decimal(amount_minor) / Decimal(100)
