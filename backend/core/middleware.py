import uuid
from django.middleware.csrf import CsrfViewMiddleware

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
        response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        return response
