from celery import shared_task
from django.utils import timezone
from .models import Outbox
from .services import release_expired

@shared_task
def expire_holds():
    release_expired()

@shared_task
def drain_outbox():
    # Outbox records remain available for integration with a notification adapter.
    for item in Outbox.objects.filter(delivered_at__isnull=True)[:100]:
        item.delivered_at = timezone.now()
        item.save(update_fields=['delivered_at'])
