import os
import secrets
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import User


class Command(BaseCommand):
    help = 'Generate unique staff passwords and save them to an owner-only local file (development only)'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True, help='Absolute path to a new private file; existing files are never replaced')

    def handle(self, *args, **options):
        if settings.ENV != 'development':
            raise CommandError('Generated staff password reset is available only in development')

        output = Path(options['output'])
        if not output.is_absolute() or not output.parent.is_dir():
            raise CommandError('Provide an absolute path in an existing directory')

        users = list(User.objects.order_by('pk'))
        if not users:
            raise CommandError('No staff accounts found; seed the development project first')
        credentials = [(user, secrets.token_urlsafe(24)) for user in users]

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        try:
            fd = os.open(output, flags, 0o600)
        except FileExistsError as exc:
            raise CommandError('Private password file already exists; it will not be overwritten') from exc
        except OSError as exc:
            raise CommandError('Unable to create the private password file') from exc

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                for user, password in credentials:
                    handle.write(f'{user.username}\t{password}\n')
                handle.flush()
                os.fsync(handle.fileno())

            with transaction.atomic():
                for user, password in credentials:
                    user.set_password(password)
                    user.save(update_fields=['password'])
        except BaseException:
            output.unlink(missing_ok=True)
            raise

        self.stdout.write(self.style.SUCCESS(
            f'Changed {len(users)} staff passwords. Read the owner-only file at {output} locally; no passwords were printed.'
        ))
