import pytest
from core.models import Hotel, Room, RoomType, User, Audit, Reservation, Guest, Folio, Allocation
from psycopg.types.range import Range
from django.utils import timezone
from datetime import timedelta

JSON = 'application/json'


@pytest.fixture
def hotel(db):
    return Hotel.objects.create(name='Luma Haven Test', timezone='Asia/Phnom_Penh', currency='USD')


@pytest.fixture
def admin_client(client, db):
    admin = User.objects.create_user(username='superadmin', password='x-password-123', role='ADMIN', is_staff=True)
    res = client.post('/api/v1/auth/login', {'username': 'superadmin', 'password': 'x-password-123'},
                      content_type=JSON, HTTP_X_PORTAL='admin')
    assert res.status_code == 200
    return client


@pytest.fixture
def manager_client(client, db):
    mgr = User.objects.create_user(username='manager1', password='x-password-123', role='MANAGER', is_staff=True)
    session = client.session
    session['_auth_user_id'] = str(mgr.pk)
    session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
    session.save()
    client.cookies['sessionid'] = session.session_key
    client.cookies['staff_sessionid'] = session.session_key
    client.user = mgr
    return client


@pytest.fixture
def guest_client(client):
    return client


def test_admin_room_type_crud(admin_client, hotel):
    # 1. Create Room Type
    payload = {
        'name': 'Zen Suite',
        'description': 'A calm sanctuary with garden views.',
        'capacity': 3,
        'nightly_rate_minor': 18000,
        'amenities': ['King Bed', 'Rain Shower', 'Espresso Bar'],
    }
    create_res = admin_client.post('/api/v1/admin/room-types', payload, content_type=JSON)
    assert create_res.status_code == 201, create_res.content
    type_id = create_res.json()['id']
    assert create_res.json()['name'] == 'Zen Suite'
    assert create_res.json()['capacity'] == 3
    assert create_res.json()['nightly_rate_minor'] == 18000
    assert 'Rain Shower' in create_res.json()['amenities']

    # Audit check
    assert Audit.objects.filter(action='ROOM_TYPE_CREATED', target__contains='Zen Suite').exists()

    # 2. Read Room Types List & Detail
    list_res = admin_client.get('/api/v1/admin/room-types')
    assert list_res.status_code == 200
    assert any(rt['id'] == type_id for rt in list_res.json())

    detail_res = admin_client.get(f'/api/v1/admin/room-types/{type_id}')
    assert detail_res.status_code == 200
    assert detail_res.json()['name'] == 'Zen Suite'

    # 3. Update Room Type
    update_res = admin_client.patch(
        f'/api/v1/admin/room-types/{type_id}',
        {'name': 'Zen Master Suite', 'nightly_rate_minor': 22000, 'capacity': 4},
        content_type=JSON
    )
    assert update_res.status_code == 200
    assert update_res.json()['name'] == 'Zen Master Suite'
    assert update_res.json()['nightly_rate_minor'] == 22000
    assert update_res.json()['capacity'] == 4
    assert Audit.objects.filter(action='ROOM_TYPE_UPDATED', target__contains='Zen Master Suite').exists()

    # 4. Delete Room Type (when unassigned)
    del_res = admin_client.delete(f'/api/v1/admin/room-types/{type_id}')
    assert del_res.status_code == 200
    assert del_res.json()['deleted'] is True
    assert not RoomType.objects.filter(pk=type_id).exists()
    assert Audit.objects.filter(action='ROOM_TYPE_DELETED').exists()


def test_cannot_delete_room_type_with_assigned_rooms(admin_client, hotel):
    rt = RoomType.objects.create(hotel=hotel, name='Deluxe Twin', nightly_rate_minor=12000, capacity=2)
    Room.objects.create(hotel=hotel, type=rt, number='301')

    # Attempt delete
    del_res = admin_client.delete(f'/api/v1/admin/room-types/{rt.pk}')
    assert del_res.status_code == 400
    assert 'assigned' in del_res.json()[0].lower()
    assert RoomType.objects.filter(pk=rt.pk).exists()


def test_admin_room_crud(admin_client, hotel):
    rt = RoomType.objects.create(hotel=hotel, name='Villa Suite', nightly_rate_minor=25000, capacity=4)

    # 1. Create Room
    create_res = admin_client.post('/api/v1/admin/rooms', {
        'number': '501',
        'type_id': rt.pk,
        'in_service': True,
        'cleaning': 'READY'
    }, content_type=JSON)
    assert create_res.status_code == 201, create_res.content
    room_id = create_res.json()['id']
    assert create_res.json()['number'] == '501'
    assert create_res.json()['type_name'] == 'Villa Suite'
    assert Audit.objects.filter(action='ROOM_CREATED', target__contains='501').exists()

    # Duplicate number rejected
    dup_res = admin_client.post('/api/v1/admin/rooms', {
        'number': '501',
        'type_id': rt.pk
    }, content_type=JSON)
    assert dup_res.status_code == 400

    # 2. Read Rooms List
    list_res = admin_client.get('/api/v1/admin/rooms')
    assert list_res.status_code == 200
    assert any(r['number'] == '501' for r in list_res.json())

    # 3. Update Room (Change cleaning & in_service)
    update_res = admin_client.patch(f'/api/v1/admin/rooms/{room_id}', {
        'cleaning': 'INSPECTION',
        'in_service': False
    }, content_type=JSON)
    assert update_res.status_code == 200
    assert update_res.json()['cleaning'] == 'INSPECTION'
    assert update_res.json()['in_service'] is False
    assert Audit.objects.filter(action='ROOM_UPDATED', target__contains='501').exists()

    # 4. Delete Room
    del_res = admin_client.delete(f'/api/v1/admin/rooms/{room_id}')
    assert del_res.status_code == 200
    assert del_res.json()['deleted'] is True
    assert not Room.objects.filter(pk=room_id).exists()
    assert Audit.objects.filter(action='ROOM_DELETED', target__contains='501').exists()


def test_cannot_delete_room_with_active_allocation(admin_client, hotel):
    rt = RoomType.objects.create(hotel=hotel, name='Standard Queen', nightly_rate_minor=9000, capacity=2)
    room = Room.objects.create(hotel=hotel, type=rt, number='108')
    guest = Guest.objects.create(full_name='Alice Guest', email='alice@example.com')
    res = Reservation.objects.create(
        reference='TESTALLOC01', guest=guest, room=room,
        arrival=timezone.now().date(), departure=timezone.now().date() + timedelta(days=2),
        occupants=2, hold_expires_at=timezone.now() + timedelta(minutes=15)
    )
    Allocation.objects.create(
        room=room, reservation=res,
        period=Range(res.arrival, res.departure, '[)'),
        active=True
    )

    del_res = admin_client.delete(f'/api/v1/admin/rooms/{room.pk}')
    assert del_res.status_code == 400
    assert 'active' in del_res.json()[0].lower()
    assert Room.objects.filter(pk=room.pk).exists()


def test_guest_forbidden_from_admin_room_crud(guest_client, hotel):
    assert guest_client.get('/api/v1/admin/room-types').status_code in (401, 403)
    assert guest_client.post('/api/v1/admin/room-types', {}, content_type=JSON).status_code in (401, 403)
    assert guest_client.get('/api/v1/admin/rooms').status_code in (401, 403)
    assert guest_client.post('/api/v1/admin/rooms', {}, content_type=JSON).status_code in (401, 403)
