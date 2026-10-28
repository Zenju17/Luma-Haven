import stat

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core.models import User


@pytest.mark.django_db
def test_reset_generates_distinct_private_staff_passwords(tmp_path):
    for username, role in [('admin', 'ADMIN'), ('reception', 'RECEPTION'), ('housekeeping', 'HOUSEKEEPING')]:
        User.objects.create_user(username=username, password='previous-test-only', role=role)

    output = tmp_path / 'private-staff-passwords'
    call_command('reset_staff_passwords', output=str(output))

    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    entries = dict(line.split('\t', 1) for line in output.read_text().splitlines())
    assert set(entries) == {'admin', 'reception', 'housekeeping'}
    assert len(set(entries.values())) == len(entries)
    for username, password in entries.items():
        user = User.objects.get(username=username)
        assert user.check_password(password)
        assert not user.check_password('previous-test-only')

    with pytest.raises(CommandError, match='already exists'):
        call_command('reset_staff_passwords', output=str(output))
    for username, password in entries.items():
        assert User.objects.get(username=username).check_password(password)
