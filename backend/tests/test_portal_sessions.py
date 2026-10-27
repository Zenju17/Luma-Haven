import pytest
from core.models import User


def sign_in(client, portal, username):
    return client.post('/api/v1/auth/login', {'username': username, 'password': 'test-only'},
                       content_type='application/json', HTTP_X_PORTAL=portal)


@pytest.mark.django_db
def test_admin_staff_and_guest_sessions_are_independent(client):
    User.objects.create_user(username='admin-demo', password='test-only', role='ADMIN')
    User.objects.create_user(username='reception-demo', password='test-only', role='RECEPTION')
    guest = client.session
    guest['guest_reservation'] = 77
    guest.save()
    assert client.get('/api/v1/auth/me').json() == {'guest_reservation': 77}

    assert sign_in(client, 'guest', 'admin-demo').status_code == 403
    assert sign_in(client, 'admin', 'admin-demo').status_code == 200
    assert client.cookies['admin_sessionid']['httponly']
    assert client.cookies['admin_sessionid']['path'] == '/api/v1/'
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='admin').json()['username'] == 'admin-demo'
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json() == {}
    assert client.get('/api/v1/admin/staff').status_code == 200
    assert client.get('/api/v1/staff/reservations').status_code == 403

    assert sign_in(client, 'staff', 'reception-demo').status_code == 200
    assert client.cookies['staff_sessionid']['httponly']
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json()['username'] == 'reception-demo'
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='admin').json()['username'] == 'admin-demo'
    assert client.get('/api/v1/auth/me').json() == {'guest_reservation': 77}
    assert client.get('/api/v1/admin/staff').status_code == 200

    assert client.post('/api/v1/auth/logout', {}, content_type='application/json', HTTP_X_PORTAL='staff').status_code == 200
    assert client.cookies['staff_sessionid'].value == ''  # TestClient retains expired Set-Cookie morsels.
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json() == {}
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='admin').json()['username'] == 'admin-demo'
    assert client.get('/api/v1/auth/me').json() == {'guest_reservation': 77}

    # The same administrator may deliberately sign in to the staff workspace,
    # without the two cookies becoming interchangeable.
    assert sign_in(client, 'staff', 'admin-demo').status_code == 200
    assert client.get('/api/v1/staff/reservations').status_code == 200
    assert client.post('/api/v1/auth/logout', {}, content_type='application/json', HTTP_X_PORTAL='admin').status_code == 200
    assert client.get('/api/v1/admin/staff').status_code == 403
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json()['username'] == 'admin-demo'
    assert client.get('/api/v1/auth/me').json() == {'guest_reservation': 77}
