"""Copy existing hotel image files into the presentation's durable database storage."""
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from core.media_storage import DatabaseMediaStorage
from core.models import VisualAsset


class Command(BaseCommand):
    help = 'Import referenced local visual assets into database media storage without changing their names'

    def handle(self, *args, **options):
        storage = DatabaseMediaStorage()
        imported = missing = 0
        for name in VisualAsset.objects.exclude(image='').values_list('image', flat=True).distinct():
            if storage.exists(name):
                continue
            source = (settings.MEDIA_ROOT / name).resolve()
            if not source.is_relative_to(settings.MEDIA_ROOT.resolve()):
                raise CommandError('Invalid image path')
            if not source.is_file():
                missing += 1
                continue
            storage.save(name, ContentFile(source.read_bytes()))
            imported += 1
        self.stdout.write(f'Imported {imported} images; {missing} referenced files missing locally.')
        if missing:
            raise CommandError('Some referenced images are missing; restore them before deploying.')
