"""Record Celery task outcomes for the Developer Console."""
import time
from celery.signals import task_failure, task_postrun, task_prerun

_started = {}


@task_prerun.connect
def _start(task_id=None, **kwargs):
    _started[task_id] = time.monotonic()


@task_postrun.connect
def _finish(task_id=None, task=None, state=None, **kwargs):
    began = _started.pop(task_id, None)
    if state == 'FAILURE':
        return  # task_failure records it with the error
    _record(task, task_id, 'SUCCESS', began, '')


@task_failure.connect
def _failed(task_id=None, exception=None, sender=None, **kwargs):
    _record(sender, task_id, 'FAILURE', _started.get(task_id), f'{exception.__class__.__name__}: {str(exception)[:200]}')


def _record(task, task_id, status, began, error):
    try:
        from .models import JobRun
        elapsed = int((time.monotonic() - began) * 1000) if began else 0
        JobRun.objects.create(task=getattr(task, 'name', str(task))[:120], task_id=str(task_id or '')[:60],
                              status=status, duration_ms=min(elapsed, 2**31 - 1), error=error[:300])
    except Exception:  # monitoring must never break a task
        pass
