from django.test import Client


def test_api_csrf_rejection_is_json_without_session():
    client = Client(enforce_csrf_checks=True)
    response = client.post('/api/v1/auth/logout', data='{}', content_type='application/json')
    assert response.status_code == 403
    assert response['Content-Type'].startswith('application/json')
    assert response.json()['detail'] == 'CSRF verification failed. Refresh and retry.'
