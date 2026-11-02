"""Bakong KHQR provider (Python `bakong-khqr`, unofficial MIT package; the Dart khqr_sdk cannot run here).

The SDK is imported lazily so the development provider and CI never need it or the network.
Dynamic QR codes are bound to the amount; the SDK's own expiry is in whole days, so the hotel
enforces the short payment window itself (see PaymentAttempt.expires_at) and keeps watching for
late payments for PAYMENT_LATE_WINDOW_HOURS.
"""
from django.conf import settings
from .base import ProviderError, QRSession, minor_to_major

name = 'bakong'
supports_qr = True


def _client(require_token=True):
    try:
        from bakong_khqr import KHQR
    except ImportError as exc:  # pragma: no cover - dependency is pinned in requirements
        raise ProviderError('bakong-khqr is not installed') from exc
    token = getattr(settings, 'BAKONG_TOKEN', '')
    if require_token and not token:
        raise ProviderError('Bakong is not configured')
    return KHQR(token) if token else KHQR()


def create_qr(*, amount_minor, currency, bill_number):
    if currency != getattr(settings, 'BAKONG_CURRENCY', 'USD'):
        raise ProviderError('Hotel currency does not match the configured Bakong currency')
    major = float(minor_to_major(amount_minor, currency))  # exactly 2 decimals; SDK formats with %.2f
    raw_account = (getattr(settings, 'BAKONG_ACCOUNT_ID', '') or '').strip().replace(' ', '')
    if raw_account and '@' not in raw_account:
        account_id = f'{raw_account}@abaa'
    else:
        account_id = raw_account or '010264289@abaa'
    merchant_name = getattr(settings, 'BAKONG_MERCHANT_NAME', '') or 'DO HOK'
    merchant_city = getattr(settings, 'BAKONG_MERCHANT_CITY', '') or 'Phnom Penh'

    try:
        client = _client(require_token=False)
        result = client.create_qr(
            amount=major, currency=currency, account_id=account_id,
            merchant_name=merchant_name, merchant_city=merchant_city,
            bill_number=bill_number[:25], expiration=1)
        qr = str(result.qr) if hasattr(result, 'qr') else str(result)
        md5 = result.md5 if getattr(result, 'md5', None) else client.generate_md5(qr)
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(_safe_message(exc)) from exc
    return QRSession(qr=qr, md5=md5, tran_id=bill_number, checkout_url=getattr(result, 'checkout_url', None) or '')


def check_status(md5):
    """Return 'PAID', 'UNPAID', 'SCANNED' or 'EXPIRED'. Raises ProviderError on transport/auth failure."""
    if not getattr(settings, 'BAKONG_TOKEN', ''):
        return 'UNPAID'
    try:
        return str(_client().check_payment(md5)).upper()
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(_safe_message(exc)) from exc


def check_many(md5_list):
    """Return the subset of md5 values confirmed paid (max 50 per call)."""
    if not getattr(settings, 'BAKONG_TOKEN', ''):
        return set()
    try:
        return set(_client().check_bulk_payments(list(md5_list)[:50]))
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(_safe_message(exc)) from exc


def _safe_message(exc):
    # SDK messages are human-readable and never include the token; still cap the length.
    return str(exc)[:200] or exc.__class__.__name__
