"""Durable, size-limited image storage for the small university demonstration."""
from io import BytesIO
from urllib.parse import quote
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseMediaStorage(Storage):
    def _open(self, name, mode='rb'):
        from .models import MediaFile
        try:
            obj = MediaFile.objects.get(pk=name)
        except MediaFile.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        return ContentFile(bytes(obj.content), name=name)

    def _save(self, name, content):
        from .models import MediaFile
        data = content.read(settings.MAX_IMAGE_UPLOAD_BYTES + 1)
        if len(data) > settings.MAX_IMAGE_UPLOAD_BYTES:
            raise ValueError('Presentation images must be 3 MB or smaller.')
        with Image.open(BytesIO(data)) as image:
            content_type = Image.MIME[image.format]
            image.verify()
        MediaFile.objects.create(name=name, content=data, content_type=content_type)
        return name

    def exists(self, name):
        from .models import MediaFile
        return MediaFile.objects.filter(pk=name).exists()

    def delete(self, name):
        from .models import MediaFile
        MediaFile.objects.filter(pk=name).delete()

    def size(self, name):
        from .models import MediaFile
        from django.db.models.functions import Length
        return MediaFile.objects.annotate(length=Length('content')).values_list('length', flat=True).get(pk=name)

    def url(self, name):
        return settings.MEDIA_URL + quote(name, safe='/')
