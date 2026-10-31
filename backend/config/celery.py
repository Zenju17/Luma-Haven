import os
from celery import Celery
from celery.signals import task_postrun, task_prerun

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('hims')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@task_prerun.connect
@task_postrun.connect
def close_db_connections(**kwargs):
    from django.db import close_old_connections
    close_old_connections()
