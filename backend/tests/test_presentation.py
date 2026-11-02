from datetime import timedelta
from io import BytesIO
import pytest
from PIL import Image
from django.core.files.base import ContentFile
from django.test import Client
from core import services
from core.media_storage import DatabaseMediaStorage
from core.models import Audit, FeatureFlag, Hotel, MediaFile, PaymentAttempt, Room, RoomType
from core.payments.factory import active_provider_name


@pytest.fixture
def presentation_booking(db, settings):
    settings.PRESENTATION_DEMO = True
    hotel = Hotel.objects.create(name='Presentation Hotel')
    kind = RoomType.objects.create(hotel=hotel, name='Twin', nightly_rate_minor=10000)
    room = Room.objects.create(hotel=hotel, type=kind, number='1')
    arrival = services.hotel_today(hotel)
    reservation = services.reserve(services.create_quote(room, arrival, arrival + timedelta(days=1), 1),
                                   'Fictional Presenter', 'presenter@example.test')
    attempt = PaymentAttempt.objects.create(reservation=reservation, amount_minor=services.balance(reservation.folio),
                                            currency='USD', provider='development')
    return reservation, attempt


def owner_client(reservation):
    client = Client(enforce_csrf_checks=True)
    session = client.session
    session['guest_reservation'] = reservation.pk
    session.save()
    return client


def post(client, path, data=None):
    token = client.get('/api/v1/auth/csrf').json()['csrfToken']
    return client.post(path, data or {}, content_type='application/json', HTTP_X_CSRFTOKEN=token)


def test_demo_verification_requires_owner_payment_and_csrf(presentation_booking, settings):
    reservation, attempt = presentation_booking
    path = f'/api/v1/reservations/{reservation.pk}/demo-verify'
    client = owner_client(reservation)
    assert client.post(path).status_code == 403
    assert post(Client(enforce_csrf_checks=True), path).status_code == 403
    assert post(client, path).status_code == 400  # no payment yet
    assert post(client, f'/api/v1/development/checkout/{attempt.pk}', {'outcome': 'SUCCESS'}).status_code == 200
    assert post(client, path).json()['verified'] is True
    assert post(client, path).status_code == 200
    assert Audit.objects.filter(action='DEMO_VERIFICATION').count() == 1
    assert post(client, f'/api/v1/reservations/{reservation.pk}/check-in').json()['status'] == 'CHECKED_IN'
    settings.PRESENTATION_DEMO = False
    assert post(client, path).status_code == 404


def test_demo_cannot_settle_another_guests_payment(presentation_booking):
    _, attempt = presentation_booking
    assert post(Client(enforce_csrf_checks=True), f'/api/v1/development/checkout/{attempt.pk}',
                {'outcome': 'SUCCESS'}).status_code == 403
    attempt.refresh_from_db()
    assert attempt.status == 'PENDING'


def test_demo_forces_simulation_and_production_rejects_stored_demo_flag(db, settings):
    FeatureFlag.objects.create(key='bank_payments', enabled=True)
    settings.PRESENTATION_DEMO = True
    assert active_provider_name() == 'development'
    settings.PRESENTATION_DEMO = False
    settings.ENV = 'production'
    settings.PAYMENT_PROVIDER = 'bakong'
    FeatureFlag.objects.filter(key='bank_payments').update(enabled=False)
    assert active_provider_name() == 'bakong'


def test_database_images_survive_storage_instances_and_are_served_safely(db, settings):
    settings.DATABASE_MEDIA = True
    settings.MEDIA_URL = '/api/v1/media/'
    image = BytesIO()
    Image.new('RGB', (8, 8)).save(image, format='PNG')
    storage = DatabaseMediaStorage()
    # Content type is determined by image bytes, never the user-controlled filename.
    name = storage.save('visual_assets/presentation.html', ContentFile(image.getvalue()))
    restored = DatabaseMediaStorage()
    assert restored.open(name).read() == image.getvalue()
    assert restored.size(name) == len(image.getvalue())
    response = Client().get(restored.url(name))
    assert response.status_code == 200
    assert response['Content-Type'] == 'image/png'
    assert response['X-Content-Type-Options'] == 'nosniff'
    assert response['Cache-Control'] == 'public, max-age=3600'
    restored.delete(name)
    assert Client().get(restored.url(name)).status_code == 404
    assert not MediaFile.objects.exists()


def test_database_image_limit_is_enforced_before_storage(db, settings):
    settings.MAX_IMAGE_UPLOAD_BYTES = 10
    with pytest.raises(ValueError, match='3 MB'):
        DatabaseMediaStorage().save('large.png', ContentFile(b'x' * 11))
    assert not MediaFile.objects.exists()


def test_responsive_variants_are_rendered_on_demand_and_bounded(db, settings):
    from core.media_storage import delete_variants
    settings.DATABASE_MEDIA = True
    settings.MEDIA_URL = '/api/v1/media/'
    image = BytesIO()
    Image.new('RGB', (2400, 1600), 'teal').save(image, format='JPEG')
    name = DatabaseMediaStorage().save('visual_assets/wide.jpg', ContentFile(image.getvalue()))
    client = Client()

    response = client.get(f'/api/v1/media/{name}.w640.webp')
    assert response.status_code == 200
    assert response['Content-Type'] == 'image/webp'
    with Image.open(BytesIO(response.content)) as variant:
        assert variant.size == (640, 427)
    assert MediaFile.objects.filter(pk=f'{name}.w640.webp').exists()  # cached after first render
    assert client.get(f'/api/v1/media/{name}.w640.webp').content == response.content

    # Only whitelisted widths of existing originals can be generated.
    assert client.get(f'/api/v1/media/{name}.w999.webp').status_code == 404
    assert client.get('/api/v1/media/visual_assets/missing.jpg.w640.webp').status_code == 404

    delete_variants(name)
    assert list(MediaFile.objects.values_list('name', flat=True)) == [name]


def test_variants_never_upscale_small_images(db, settings):
    from core.media_storage import render_variant
    image = BytesIO()
    Image.new('RGBA', (300, 200)).save(image, format='PNG')
    with Image.open(BytesIO(render_variant(image.getvalue(), 1280))) as variant:
        assert variant.size == (300, 200)
        assert variant.mode == 'RGBA'
