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

@shared_task
def archive_daily_mis_snapshot():
    """Scheduled task to calculate and archive daily hotel management KPIs."""
    from datetime import timedelta
    from .models import Hotel, Audit
    from .services import hotel_today
    from .views import report_values

    hotel = Hotel.objects.first()
    if not hotel:
        return {'status': 'no_hotel'}
    today = hotel_today(hotel)
    yesterday = today - timedelta(days=1)
    values = report_values(yesterday, today)

    Audit.objects.create(
        actor='celery_beat',
        action='MIS_DAILY_SNAPSHOT',
        target=f'{yesterday}:occ={values.get("occupancy_rate_percent")}%:rev={values.get("net_room_revenue_minor")}:cash={values.get("settled_cash_minor")}'
    )
    return {'status': 'archived', 'date': str(yesterday), 'kpis': values}

