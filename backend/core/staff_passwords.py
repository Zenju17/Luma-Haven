"""Development-only synchronization of admin-changed passwords and private credentials."""

import fcntl
import os
import stat
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from .models import Audit, User


def _read_credentials(path: Path) -> bytes | None:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('The private credentials file must be a regular owner-only file.')
        contents = handle.read(65537)
        if len(contents) > 65536:
            raise ValueError('The private credentials file is too large to update safely.')
        return contents


def _replace_credentials(path: Path, contents: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f'{path.name}.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def change_password(actor: User, staff_id: int, password: str) -> str:
    """Change another staff member's password, mirroring it in a 0600 file.

    Both mutations occur while holding the file lock and the database row lock.
    If the database commit fails after the file replacement, restore the old
    file before releasing the lock.
    """
    if settings.ENV != 'development':
        raise ValueError('Local credential-file changes are available only in development.')
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError('Choose a password between 12 and 128 characters.')
    if any(ord(character) < 32 or ord(character) == 127 or character in ('\u2028', '\u2029') for character in password):
        raise ValueError('Passwords cannot contain control characters.')

    path = Path(settings.STAFF_CREDENTIALS_FILE)
    if not path.is_absolute():
        raise ValueError('Configure an absolute private credentials file path.')
    lock_path = path.with_name(path.name + '.lock')
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except OSError as exc:
        raise ValueError('The private credentials file is unavailable.') from exc
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        original = _read_credentials(path)
        try:
            entries = dict(line.split('\t', 1) for line in (original or b'').decode('utf-8').splitlines())
        except (ValueError, UnicodeError) as exc:
            raise ValueError('The private credentials file has an invalid format.') from exc

        replaced = False
        try:
            with transaction.atomic():
                target = User.objects.select_for_update().get(pk=staff_id)
                if target.pk == actor.pk:
                    raise ValueError('Use the password-change command for your own account.')
                if target.check_password(password):
                    raise ValueError('The new password must differ from the current password.')
                try:
                    validate_password(password, target)
                except DjangoValidationError as exc:
                    raise ValueError('The new password does not meet the configured requirements.') from exc
                entries[target.username] = password
                updated = ''.join(f'{username}\t{secret}\n' for username, secret in entries.items()).encode('utf-8')
                if len(updated) > 65536:
                    raise ValueError('The private credentials file is too large to update safely.')
                target.set_password(password)
                target.save(update_fields=['password'])
                Audit.objects.create(actor=actor.username, action='STAFF_PASSWORD_CHANGED', target=target.username)
                _replace_credentials(path, updated)
                replaced = True
        except Exception:
            if replaced:
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    _replace_credentials(path, original)
            raise
        return target.username
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
