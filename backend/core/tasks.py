from celery import shared_task
from django.utils import timezone
from .models import Outbox
from .services import release_expired

@shared_task
def expire_holds():
    release_expired()

@shared_task
def drain_outbox():
    # No delivery adapter is configured. Keep events pending until one exists.
    # Marking them delivered here would silently discard notifications.
    return 0
