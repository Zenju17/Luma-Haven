import pytest
from django.contrib.auth import get_user_model
from core.models import Audit, Hotel


@pytest.mark.django_db
def test_admin_endpoints_restrict_staff_and_guests(client):
    Hotel.objects.create(name='Fictional Hotel')
    Audit.objects.create(actor='system', action='ROOM_INSPECTED', target='101')
    User = get_user_model()
    admin = User.objects.create_user(username='administrator', password='test-only', role='ADMIN')
    staff = User.objects.create_user(username='frontdesk', password='test-only', role='RECEPTION')
    manager = User.objects.create_user(username='manager-test', password='test-only', role='MANAGER')
    endpoints = ['/api/v1/admin/staff', '/api/v1/admin/audit', '/api/v1/admin/hotel']

    for url in endpoints:
        assert client.get(url).status_code == 403
    for user in [staff, manager]:
        client.force_login(user)
        for url in endpoints:
            assert client.get(url).status_code == 403

    client.force_login(admin)
    for url in endpoints:
        assert client.get(url).status_code == 200
    team = client.get('/api/v1/admin/staff').json()
    assert any(member['username'] == admin.username for member in team)
    assert all('password' not in member and 'email' not in member for member in team)
    assert client.get('/api/v1/admin/audit').json()[0]['action'] == 'ROOM_INSPECTED'
    assert client.get('/api/v1/admin/hotel').json()['name'] == 'Fictional Hotel'
    csv = client.get('/api/v1/reports/summary?export=csv')
    assert csv.status_code == 200
    assert csv['Content-Type'].startswith('text/csv')
    assert b'net_room_revenue_minor' in csv.content
