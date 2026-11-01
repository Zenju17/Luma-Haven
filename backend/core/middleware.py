import uuid
import time
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date
from django.views.csrf import csrf_failure as django_csrf_failure

def csrf_failure(request, reason=''):
    if request.path.startswith('/api/v1/'):
        return JsonResponse({'detail': 'CSRF verification failed. Refresh and retry.'}, status=403)
    return django_csrf_failure(request, reason=reason)


class PortalSessionMiddleware(SessionMiddleware):
    """Use distinct server-side Django sessions for guest, staff and admin.

    The header only selects a cookie jar. It is never proof of authorization:
    AuthenticationMiddleware and each endpoint still check the session user.
    """

    def process_request(self, request):
        if request.path.startswith('/api/v1/admin/'):
            portal = 'admin'
        elif request.path.startswith(('/api/v1/staff/', '/api/v1/manager/', '/api/v1/reports/', '/api/v1/housekeeping/', '/api/v1/accountant/', '/api/v1/maintenance/')):
            portal = 'staff'
        else:
            portal = request.headers.get('X-Portal', 'guest')
            if portal not in ('guest', 'staff', 'admin'):
                portal = 'guest'
        request.portal = portal
        request.portal_cookie_name = {
            'guest': settings.SESSION_COOKIE_NAME,
            'staff': 'staff_sessionid',
            'admin': 'admin_sessionid',
        }[portal]
        request.session = self.SessionStore(request.COOKIES.get(request.portal_cookie_name))

    def process_response(self, request, response):
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response
        cookie_name = request.portal_cookie_name
        path = settings.SESSION_COOKIE_PATH if request.portal == 'guest' else '/api/v1/'
        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(cookie_name, path=path, domain=settings.SESSION_COOKIE_DOMAIN,
                                   samesite=settings.SESSION_COOKIE_SAMESITE)
            patch_vary_headers(response, ('Cookie',))
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty and response.status_code < 500:
                if request.session.get_expire_at_browser_close():
                    max_age = expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires = http_date(time.time() + max_age)
                try:
                    request.session.save()
                except UpdateError:
                    raise SessionInterrupted('The portal session was deleted before this request completed.')
                response.set_cookie(cookie_name, request.session.session_key, max_age=max_age,
                                    expires=expires, domain=settings.SESSION_COOKIE_DOMAIN, path=path,
                                    secure=settings.SESSION_COOKIE_SECURE or None,
                                    httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                                    samesite=settings.SESSION_COOKIE_SAMESITE)
        return response

class StrictCSRFMiddleware(CsrfViewMiddleware):
    """Enforce CSRF for anonymous API writes as well as authenticated sessions."""
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.path.startswith('/api/v1/'):
            return super().process_view(request, lambda *args, **kwargs: None, (), {})
        return None

class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        from .logs import request_id_var
        token = request_id_var.set(request.request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response['X-Request-ID'] = request.request_id
        return response


def scrub(text):
    """Shared with logging: see core.logs.scrub_text."""
    from .logs import scrub_text
    return scrub_text(text)[:300]


class ErrorCaptureMiddleware:
    """Store a scrubbed record of unhandled exceptions for the Developer Console."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        try:
            from .models import ErrorEvent
            ErrorEvent.objects.create(
                request_id=getattr(request, 'request_id', '')[:40], method=request.method[:8],
                path=request.path[:200], exc_type=exception.__class__.__name__[:120], message=scrub(exception))
        except Exception:  # never mask the original error
            pass
        return None
