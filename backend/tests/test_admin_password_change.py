import stat

import pytest
from django.core.management import call_command
from django.test import override_settings

from core.models import Audit, User


def sign_in(client, portal, username):
    return client.post('/api/v1/auth/login', {'username': username, 'password': 'original-test-only'},
                       content_type='application/json', HTTP_X_PORTAL=portal)


@pytest.mark.django_db
def test_admin_password_change_updates_database_private_file_and_audit(client, tmp_path):
    output = tmp_path / 'staff-credentials'
    admin = User.objects.create_user(username='admin', password='original-test-only', role='ADMIN')
    target = User.objects.create_user(username='reception', password='original-test-only', role='RECEPTION')
    other = User.objects.create_user(username='accountant', password='original-test-only', role='ACCOUNTANT')
    call_command('reset_staff_passwords', output=str(output))
    original = dict(line.split('\t', 1) for line in output.read_text().splitlines())
    new_password = 'ValidPass99!'
    url = f'/api/v1/admin/staff/{target.pk}/password'
    payload = {'new_password': new_password, 'confirm_password': new_password}

    with override_settings(STAFF_CREDENTIALS_FILE=output):
        assert client.post(url, payload, content_type='application/json').status_code == 403
        assert sign_in(client, 'staff', 'admin').status_code == 400  # The reset invalidated the original password.
        assert client.post('/api/v1/auth/login', {'username': 'admin', 'password': original['admin']},
            content_type='application/json', HTTP_X_PORTAL='staff').status_code == 200
        assert client.post(url, payload, content_type='application/json', HTTP_X_PORTAL='staff').status_code == 403
        assert client.post('/api/v1/auth/login', {'username': 'admin', 'password': original['admin']},
            content_type='application/json', HTTP_X_PORTAL='admin').status_code == 200
        assert client.post(f'/api/v1/admin/staff/{admin.pk}/password', payload,
            content_type='application/json').status_code == 400
        assert client.post(url, {'new_password': new_password, 'confirm_password': 'different'},
            content_type='application/json').status_code == 400
        assert client.post(url, {'new_password': 'short', 'confirm_password': 'short'},
            content_type='application/json').status_code == 400
        assert client.post(url, {'new_password': '1234567890', 'confirm_password': '1234567890'},
            content_type='application/json').status_code == 400

        response = client.post(url, payload, content_type='application/json')
        assert response.status_code == 200
        assert response.json() == {'status': 'updated'}
        assert new_password not in response.content.decode()
        target.refresh_from_db()
        assert target.check_password(new_password)
        assert not target.check_password(original['reception'])
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
        stored = dict(line.split('\t', 1) for line in output.read_text().splitlines())
        assert stored['reception'] == new_password
        assert stored['admin'] == original['admin']
        assert stored['accountant'] == original['accountant']
        assert Audit.objects.filter(actor='admin', action='STAFF_PASSWORD_CHANGED', target='reception').count() == 1
        assert not Audit.objects.filter(target__contains=new_password).exists()
        other.refresh_from_db()
        assert other.check_password(original['accountant'])


@pytest.mark.django_db
def test_missing_private_file_is_created_and_insecure_file_fails_closed(client, tmp_path):
    admin = User.objects.create_user(username='admin', password='original-test-only', role='ADMIN')
    target = User.objects.create_user(username='housekeeping', password='original-test-only', role='HOUSEKEEPING')
    output = tmp_path / 'staff-credentials'
    url = f'/api/v1/admin/staff/{target.pk}/password'
    with override_settings(STAFF_CREDENTIALS_FILE=output):
        assert sign_in(client, 'admin', admin.username).status_code == 200
        first = 'TestPass88!'
        assert client.post(url, {'new_password': first, 'confirm_password': first},
            content_type='application/json').status_code == 200
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
        assert output.read_text() == f'housekeeping\t{first}\n'

        output.chmod(0o644)
        second = 'TestPass99!'
        response = client.post(url, {'new_password': second, 'confirm_password': second},
            content_type='application/json')
        assert response.status_code == 400
        target.refresh_from_db()
        assert target.check_password(first)
        assert not target.check_password(second)
