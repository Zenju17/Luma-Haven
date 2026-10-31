from django.utils import timezone
from .models import FeatureFlag

DEFAULT_FLAGS = {
    'bookings_paused': ('Pause new guest bookings (maintenance window).', False),
    'telegram_enabled': ('Telegram bot channel (future feature).', False),
}


def is_enabled(key):
    return FeatureFlag.objects.filter(key=key, enabled=True).exists()


def set_flag(key, enabled, actor):
    flag, _ = FeatureFlag.objects.get_or_create(key=key)
    flag.enabled, flag.updated_by, flag.updated_at = bool(enabled), actor, timezone.now()
    flag.save()
    return flag
