"""Rate limiting for abuse-prone endpoints (production default; dev/E2E stay unthrottled).

Counters live in Django's cache (Redis in production so every gunicorn worker shares them).
The client IP honours X-Forwarded-For only for the configured number of trusted proxies.
"""
import re
from django.conf import settings
from rest_framework.exceptions import Throttled
from rest_framework.throttling import SimpleRateThrottle

LOCKOUT_FAILURES = 5
LOCKOUT_MINUTES = 15


def client_ip(request):
    """Real client address: the Nth-from-last X-Forwarded-For entry when N proxies are trusted."""
    proxies = settings.TRUSTED_PROXY_COUNT
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if proxies and forwarded:
        parts = [p.strip() for p in forwarded.split(',') if p.strip()]
        if len(parts) >= proxies:
            return parts[-proxies]
    return request.META.get('REMOTE_ADDR', '')


class IPScopeThrottle(SimpleRateThrottle):
    scope = ''

    def get_rate(self):
        return settings.THROTTLE_RATES.get(self.scope)

    def allow_request(self, request, view):
        if not settings.THROTTLE_ENABLED:
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        return f'throttle_{self.scope}_{re.sub(r"[^0-9a-fA-F:.]", "", client_ip(request)) or "unknown"}'


class LoginThrottle(IPScopeThrottle):
    scope = 'login'


class OtpThrottle(IPScopeThrottle):
    scope = 'otp'


class BookingThrottle(IPScopeThrottle):
    scope = 'booking'


class PrivacyThrottle(IPScopeThrottle):
    scope = 'privacy'


class PollThrottle(IPScopeThrottle):
    scope = 'poll'


def check_lockout(username, portal):
    """Per-account lockout after repeated failed sign-ins (uses the LOGIN_FAILED audit rows)."""
    if not settings.THROTTLE_ENABLED or not username:
        return
    from datetime import timedelta
    from django.utils import timezone
    from .models import Audit
    since = timezone.now() - timedelta(minutes=LOCKOUT_MINUTES)
    failures = Audit.objects.filter(actor=username[:120], action='LOGIN_FAILED', target=portal, timestamp__gte=since).count()
    if failures >= LOCKOUT_FAILURES:
        raise Throttled(wait=LOCKOUT_MINUTES * 60, detail='Too many failed sign-in attempts. Try again in 15 minutes.')
