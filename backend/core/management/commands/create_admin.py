"""Create the first administrator in a fresh (production) database without the demo seed.

    python manage.py create_admin --username owner      # prompts for the password
    LUMA_ADMIN_PASSWORD=... python manage.py create_admin --username owner   # non-interactive
"""
import getpass
import os
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from core.models import Audit, User


class Command(BaseCommand):
    help = 'Create an ADMIN user (the password is never passed as a command-line argument).'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    def handle(self, *args, **options):
        username = options['username'].strip()
        if not username or User.objects.filter(username=username).exists():
            raise CommandError('Username is empty or already exists.')
        password = os.getenv('LUMA_ADMIN_PASSWORD') or getpass.getpass('Password: ')
        if not os.getenv('LUMA_ADMIN_PASSWORD') and password != getpass.getpass('Repeat password: '):
            raise CommandError('Passwords do not match.')
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(' '.join(exc.messages))
        User.objects.create_user(username=username, password=password, role='ADMIN', is_staff=True)
        Audit.objects.create(actor='cli', action='ADMIN_CREATED', target=username[:80])
        self.stdout.write(self.style.SUCCESS(f'Administrator {username} created. Sign in at /admin and enable your own safeguards.'))
