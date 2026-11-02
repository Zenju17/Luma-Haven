from django.conf import settings
from django.core.management.base import BaseCommand
from core.media_storage import VARIANT_WIDTHS, get_or_create_variant, parse_variant_name, variant_name
from core.models import MediaFile


class Command(BaseCommand):
    help = 'Pre-render responsive WebP variants for database-stored images (they are otherwise made on first request)'

    def handle(self, *args, **options):
        if not settings.DATABASE_MEDIA:
            self.stdout.write('DATABASE_MEDIA is off; nothing to do.')
            return
        created = 0
        for name in MediaFile.objects.values_list('name', flat=True).iterator():
            if parse_variant_name(name):
                continue
            for width in VARIANT_WIDTHS:
                target = variant_name(name, width)
                if not MediaFile.objects.filter(pk=target).exists() and get_or_create_variant(target):
                    created += 1
        self.stdout.write(f'Created {created} variant(s).')
