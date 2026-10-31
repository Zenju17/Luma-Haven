"""Structured JSON logging with a per-request id, plus PII-scrubbed Sentry initialisation."""
import contextvars
import json
import logging
import re

request_id_var = contextvars.ContextVar('request_id', default='-')
_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_TOKEN = re.compile(r'[A-Za-z0-9_\-]{24,}')


def scrub_text(value):
    """Remove emails and long token-like strings. Applied to every log message and Sentry event."""
    return _TOKEN.sub('[token]', _EMAIL.sub('[email]', str(value)))


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {'time': self.formatTime(record, '%Y-%m-%dT%H:%M:%S%z'), 'level': record.levelname,
                   'logger': record.name, 'request_id': getattr(record, 'request_id', '-'),
                   'message': scrub_text(record.getMessage())}
        if record.exc_info:
            payload['exception'] = scrub_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def _scrub_event(event, hint):
    request = event.get('request') or {}
    for key in ('cookies', 'data', 'headers', 'query_string'):
        request.pop(key, None)  # never ship cookies, bodies, auth headers or query strings
    event.pop('user', None)
    for exc in (event.get('exception') or {}).get('values', []):
        if exc.get('value'):
            exc['value'] = scrub_text(exc['value'])
    if event.get('message'):
        event['message'] = scrub_text(event['message'])
    return event


def init_sentry(dsn, environment, release):
    try:
        import sentry_sdk
    except ImportError:  # optional dependency; logging still works
        logging.getLogger(__name__).warning('SENTRY_DSN is set but sentry-sdk is not installed')
        return
    sentry_sdk.init(dsn=dsn, environment=environment, release=release, send_default_pii=False,
                    traces_sample_rate=0.0, before_send=_scrub_event)
