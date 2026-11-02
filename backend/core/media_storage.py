"""Durable, size-limited image storage for the small university demonstration."""
import re
from io import BytesIO
from urllib.parse import quote
from PIL import Image, ImageOps
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


# Responsive variants: "<original>.w<width>.webp" is a downscaled WebP of <original>.
# They are created on first request (see views.presentation_media), so existing
# images gain variants without a backfill, and only these widths can be requested.
VARIANT_WIDTHS = (640, 1280)
_VARIANT_RE = re.compile(r'^(?P<original>.+)\.w(?P<width>\d+)\.webp$')


def parse_variant_name(name):
    """Return (original_name, width) for an allowed variant name, else None."""
    match = _VARIANT_RE.match(name)
    if not match or int(match['width']) not in VARIANT_WIDTHS:
        return None
    return match['original'], int(match['width'])


def variant_name(original, width):
    return f'{original}.w{width}.webp'


def render_variant(data, width):
    """Downscale image bytes to at most `width` px wide (never upscales) as WebP."""
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source)
        has_alpha = image.mode in ('RGBA', 'LA') or 'transparency' in image.info
        image = image.convert('RGBA' if has_alpha else 'RGB')
        image.thumbnail((width, width * 10), Image.LANCZOS)
        out = BytesIO()
        image.save(out, format='WEBP', quality=80, method=4)
    return out.getvalue()


def get_or_create_variant(name):
    """Return the MediaFile for an allowed variant name, rendering it if needed, else None."""
    from django.db import IntegrityError, transaction
    from .models import MediaFile
    parsed = parse_variant_name(name)
    if parsed is None:
        return None
    existing = MediaFile.objects.filter(pk=name).first()
    if existing is not None:
        return existing
    original = MediaFile.objects.filter(pk=parsed[0]).first()
    if original is None:
        return None
    content = render_variant(bytes(original.content), parsed[1])
    try:
        with transaction.atomic():
            return MediaFile.objects.create(name=name, content=content, content_type='image/webp')
    except IntegrityError:  # a concurrent request rendered it first
        return MediaFile.objects.get(pk=name)


def delete_variants(original):
    """Remove generated variants of a database-stored image (no-op for other storages)."""
    from .models import MediaFile
    if original:
        MediaFile.objects.filter(name__in=[variant_name(original, w) for w in VARIANT_WIDTHS]).delete()
