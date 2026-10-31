import io
import json
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from core.models import Hotel, RoomType, User, VisualAsset


def create_dummy_png(width=100, height=100, color='blue'):
    buf = io.BytesIO()
    img = Image.new('RGB', (width, height), color=color)
    img.save(buf, format='PNG')
    return buf.getvalue()



@pytest.fixture
def hotel_setup(db):
    hotel = Hotel.objects.first()
    if not hotel:
        hotel = Hotel.objects.create(name='Luma Haven', timezone='Asia/Phnom_Penh', currency='USD')
    garden_king, _ = RoomType.objects.get_or_create(
        hotel=hotel, name='Garden King',
        defaults={'capacity': 2, 'nightly_rate_minor': 8500, 'amenities': ['Wi-Fi']}
    )
    city_twin, _ = RoomType.objects.get_or_create(
        hotel=hotel, name='City Twin',
        defaults={'capacity': 2, 'nightly_rate_minor': 7200, 'amenities': ['Wi-Fi']}
    )
    family_suite, _ = RoomType.objects.get_or_create(
        hotel=hotel, name='Family Suite',
        defaults={'capacity': 4, 'nightly_rate_minor': 15500, 'amenities': ['Wi-Fi']}
    )
    return hotel, garden_king, city_twin, family_suite


def login_as(client, user, portal='staff'):
    client.post('/api/v1/auth/logout', HTTP_X_PORTAL=portal)
    res = client.post(
        '/api/v1/auth/login',
        {'username': user.username, 'password': 'Password123!'},
        content_type='application/json',
        HTTP_X_PORTAL=portal
    )
    assert res.status_code == 200
    return res


@pytest.fixture
def users(db):
    admin_user = User.objects.create_user(username='admin_test', password='Password123!', role='ADMIN', is_staff=True)
    manager_user = User.objects.create_user(username='manager_test', password='Password123!', role='MANAGER', is_staff=True)
    reception_user = User.objects.create_user(username='reception_test', password='Password123!', role='RECEPTION', is_staff=True)
    return admin_user, manager_user, reception_user


@pytest.mark.django_db
def test_staff_visual_assets_permissions(client, hotel_setup, users):
    admin_user, manager_user, reception_user = users

    # 1. Anonymous user -> 403
    resp_anon = client.get('/api/v1/staff/visual-assets', HTTP_X_PORTAL='staff')
    assert resp_anon.status_code == 403

    # 2. Reception user -> 403
    login_as(client, reception_user, portal='staff')
    resp_reception = client.get('/api/v1/staff/visual-assets', HTTP_X_PORTAL='staff')
    assert resp_reception.status_code == 403

    # 3. Manager user -> 200
    login_as(client, manager_user, portal='staff')
    resp_manager = client.get('/api/v1/staff/visual-assets', HTTP_X_PORTAL='staff')
    assert resp_manager.status_code == 200

    # 4. Admin user -> 200 on admin route
    login_as(client, admin_user, portal='admin')
    resp_admin = client.get('/api/v1/admin/visual-assets', HTTP_X_PORTAL='admin')
    assert resp_admin.status_code == 200


@pytest.mark.django_db
def test_staff_visual_asset_crud(client, hotel_setup, users):
    hotel, garden_king, _, _ = hotel_setup
    admin_user, manager_user, _ = users
    login_as(client, manager_user, portal='staff')

    # Upload new asset via manager on staff route
    img_bytes = create_dummy_png(200, 150)
    file_upload = SimpleUploadedFile('new_gallery.png', img_bytes, content_type='image/png')

    post_resp = client.post(
        '/api/v1/staff/visual-assets',
        {
            'image': file_upload,
            'title': 'New Gallery Image',
            'caption': 'Original Caption',
            'alt_text': 'Original Alt',
            'category': 'GALLERY',
            'display_order': 5,
        },
        HTTP_X_PORTAL='staff'
    )
    assert post_resp.status_code == 201
    asset_id = post_resp.json()['id']

    # Update asset via PATCH (as admin on admin route)
    login_as(client, admin_user, portal='admin')
    patch_resp = client.patch(
        f'/api/v1/admin/visual-assets/{asset_id}',
        json.dumps({
            'caption': 'Updated Caption',
            'display_order': 2,
            'room_type_id': garden_king.id,
            'is_active': False
        }),
        content_type='application/json',
        HTTP_X_PORTAL='admin'
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data['caption'] == 'Updated Caption'
    assert data['display_order'] == 2
    assert data['room_type_id'] == garden_king.id
    assert data['is_active'] is False

    # Delete asset
    del_resp = client.delete(f'/api/v1/admin/visual-assets/{asset_id}', HTTP_X_PORTAL='admin')
    assert del_resp.status_code == 200
    assert not VisualAsset.objects.filter(pk=asset_id).exists()



@pytest.mark.django_db
def test_public_visual_assets_api(client, hotel_setup):
    hotel, garden_king, _, _ = hotel_setup

    active_asset = VisualAsset.objects.create(
        hotel=hotel,
        category='HERO',
        image='visual_assets/hero/exterior.png',
        title='Hotel Exterior',
        caption='Exterior at dusk',
        alt_text='Exterior view',
        is_active=True,
    )
    inactive_asset = VisualAsset.objects.create(
        hotel=hotel,
        category='GALLERY',
        image='visual_assets/gallery/pool.png',
        title='Pool Draft',
        caption='Pool concept',
        alt_text='Rooftop pool',
        is_active=False,
    )
    room_asset = VisualAsset.objects.create(
        hotel=hotel,
        category='ROOM_TYPE',
        room_type=garden_king,
        image='visual_assets/rooms/deluxe/main.png',
        title='Garden King Room',
        caption='King bed room',
        alt_text='Garden King bed',
        is_active=True,
    )

    resp = client.get('/api/v1/visual-assets')
    assert resp.status_code == 200
    data = resp.json()

    assert data['hero'] is not None
    assert data['hero']['id'] == active_asset.id
    assert not any(item['id'] == inactive_asset.id for item in data['items'])
    assert str(garden_king.id) in data['room_types'] or garden_king.id in data['room_types']


@pytest.mark.django_db
def test_import_visual_assets_dry_run(tmp_path, hotel_setup):
    hotel, garden_king, city_twin, family_suite = hotel_setup

    # Create dummy source assets structure in tmp_path
    hero_dir = tmp_path / 'hero'
    hero_dir.mkdir(parents=True)
    img_data = create_dummy_png(300, 200)
    (hero_dir / 'hotel_exterior_concept.png').write_bytes(img_data)

    initial_count = VisualAsset.objects.count()

    # Dry run should not create database objects
    call_command('import_visual_assets', source=str(tmp_path), dry_run=True)
    assert VisualAsset.objects.count() == initial_count

