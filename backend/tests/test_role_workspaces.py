import pytest
from datetime import date, timedelta
from psycopg.types.range import Range
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import (
    Allocation, Audit, Folio, FolioEntry, Guest, Hotel, HousekeepingTask,
    Payment, PaymentAttempt, PaymentException, Refund, Reservation, Room,
    RoomType, ServiceRequest, Stay
)
from core import services

User = get_user_model()


@pytest.fixture
def hotel_setup(db):
    hotel = Hotel.objects.create(
        name='Luma Haven Luxury Resort',
        timezone='Asia/Phnom_Penh',
        currency='USD',
        check_in_time='14:00',
        check_out_time='12:00',
        tax_percent=10,
        deposit_percent=100
    )
    deluxe = RoomType.objects.create(
        hotel=hotel,
        name='Deluxe Haven Suite',
        capacity=2,
        nightly_rate_minor=20000,
        amenities=['King Bed', 'Balcony', 'Ocean View']
    )
    suite = RoomType.objects.create(
        hotel=hotel,
        name='Executive Penthouse',
        capacity=4,
        nightly_rate_minor=45000,
        amenities=['Private Terrace', 'Jacuzzi', 'Butler Service']
    )
    r101 = Room.objects.create(hotel=hotel, type=deluxe, number='101', cleaning='READY', in_service=True)
    r102 = Room.objects.create(hotel=hotel, type=deluxe, number='102', cleaning='READY', in_service=True)
    r201 = Room.objects.create(hotel=hotel, type=suite, number='201', cleaning='READY', in_service=True)

    # 5 role users
    admin = User.objects.create_user(username='admin_user', password='Password123!', role='ADMIN', is_staff=True)
    manager = User.objects.create_user(username='manager_user', password='Password123!', role='MANAGER', is_staff=True)
    reception = User.objects.create_user(username='reception_user', password='Password123!', role='RECEPTION', is_staff=True)
    housekeeping = User.objects.create_user(username='housekeeping_user', password='Password123!', role='HOUSEKEEPING', is_staff=True)
    accountant = User.objects.create_user(username='accountant_user', password='Password123!', role='ACCOUNTANT', is_staff=True)

    return {
        'hotel': hotel, 'deluxe': deluxe, 'suite': suite,
        'r101': r101, 'r102': r102, 'r201': r201,
        'admin': admin, 'manager': manager, 'reception': reception,
        'housekeeping': housekeeping, 'accountant': accountant,
    }


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


# ==============================================================================
# 1. Role-Specific Workspace Permissions & Boundaries
# ==============================================================================

@pytest.mark.django_db
def test_admin_workspace_actions(client, hotel_setup):
    """Admin creates accounts, alters roles/status, updates hotel settings, views health diagnostics."""
    login_as(client, hotel_setup['admin'], portal='admin')

    # Create new staff account
    res = client.post('/api/v1/admin/staff', {
        'username': 'new_cleaner',
        'password': 'Passw0rd12!',
        'role': 'HOUSEKEEPING'
    }, content_type='application/json')
    assert res.status_code == 201
    created = res.json()
    assert created['username'] == 'new_cleaner'
    assert created['role'] == 'HOUSEKEEPING'
    assert User.objects.filter(username='new_cleaner').exists()

    # Alter role and status of new cleaner
    patch_res = client.patch(f"/api/v1/admin/staff/{created['id']}", {
        'role': 'RECEPTION',
        'is_active': False
    }, content_type='application/json')
    assert patch_res.status_code == 200
    assert patch_res.json()['role'] == 'RECEPTION'
    assert patch_res.json()['is_active'] is False

    # Admin cannot deactivate self
    self_res = client.patch(f"/api/v1/admin/staff/{hotel_setup['admin'].id}", {'is_active': False}, content_type='application/json')
    assert self_res.status_code == 400

    # Admin cannot change own role
    self_role = client.patch(f"/api/v1/admin/staff/{hotel_setup['admin'].id}", {'role': 'MANAGER'}, content_type='application/json')
    assert self_role.status_code == 400

    # Update hotel settings
    hotel_res = client.post('/api/v1/admin/hotel', {
        'name': 'Luma Haven Grand Resort',
        'tax_percent': 12,
        'deposit_percent': 100
    }, content_type='application/json')
    assert hotel_res.status_code == 200
    assert hotel_res.json()['name'] == 'Luma Haven Grand Resort'
    assert hotel_res.json()['tax_percent'] == 12

    # System Health Diagnostics
    diag_res = client.get('/api/v1/admin/health-diagnostics')
    assert diag_res.status_code == 200
    diag = diag_res.json()
    assert 'services' in diag
    assert diag['services']['database']['status'] == 'ONLINE'
    assert 'unresolved_payment_exceptions' in diag


@pytest.mark.django_db
def test_housekeeping_workspace_security_boundaries(client, hotel_setup):
    """Housekeeping has dedicated operational tools but zero financial or guest visibility."""
    login_as(client, hotel_setup['housekeeping'], portal='staff')

    # Housekeeping is forbidden from reservations, rates, refunds, reports, admin
    assert client.get('/api/v1/staff/reservations').status_code == 403
    assert client.get('/api/v1/staff/rates').status_code == 403
    assert client.get('/api/v1/staff/refunds').status_code == 403
    assert client.get('/api/v1/reports/daily-summary').status_code == 403
    assert client.get('/api/v1/accountant/payments').status_code == 403
    assert client.get('/api/v1/admin/staff').status_code == 403

    # Housekeeping can see tasks and reporting maintenance
    task = HousekeepingTask.objects.create(room=hotel_setup['r101'], status='DIRTY', priority='HIGH')
    tasks_res = client.get('/api/v1/housekeeping/tasks')
    assert tasks_res.status_code == 200
    assert any(t['id'] == task.id and t['priority'] == 'HIGH' for t in tasks_res.json())

    # Housekeeping can start cleaning
    step1 = client.post(f'/api/v1/housekeeping/tasks/{task.id}/transition', {'status': 'CLEANING'}, content_type='application/json')
    assert step1.status_code == 200
    assert step1.json()['status'] == 'CLEANING'

    # Housekeeping can request inspection with notes
    step2 = client.post(f'/api/v1/housekeeping/tasks/{task.id}/transition', {'status': 'INSPECTION', 'notes': 'Linen replaced, sanitized'}, content_type='application/json')
    assert step2.status_code == 200
    assert step2.json()['status'] == 'INSPECTION'

    # Housekeeping CANNOT approve room ready
    step3 = client.post(f'/api/v1/housekeeping/tasks/{task.id}/transition', {'status': 'READY'}, content_type='application/json')
    assert step3.status_code == 403  # Inspection requires reception or management

    # Housekeeping can report room maintenance problem
    maint_res = client.post('/api/v1/maintenance/tickets', {
        'room_id': hotel_setup['r102'].id,
        'description': 'Leaking air conditioner pipe',
        'priority': 'URGENT'
    }, content_type='application/json')
    assert maint_res.status_code == 201
    assert maint_res.json()['priority'] == 'URGENT'


@pytest.mark.django_db
def test_reception_and_manager_inspection_and_diagnostics(client, hotel_setup):
    """Receptionist inspects rooms, checks diagnostics, and cannot approve refunds."""
    r = hotel_setup['r101']
    task = HousekeepingTask.objects.create(room=r, status='INSPECTION')

    # Reception signs in
    login_as(client, hotel_setup['reception'], portal='staff')

    # Receptionist can inspect and mark room ready
    ready_res = client.post(f'/api/v1/housekeeping/tasks/{task.id}/transition', {'status': 'READY'}, content_type='application/json')
    assert ready_res.status_code == 200
    assert ready_res.json()['status'] == 'READY'
    r.refresh_from_db()
    assert r.cleaning == 'READY'

    # Reception cannot approve refunds
    guest = Guest.objects.create(full_name='Test Guest', email='test@example.com')
    today = services.hotel_today(hotel_setup['hotel'])
    res = Reservation.objects.create(
        reference='LH-DIAG-01', guest=guest, room=r,
        arrival=today + timedelta(days=2), departure=today + timedelta(days=3),
        occupants=1, status='CONFIRMED', hold_expires_at=timezone.now() + timedelta(hours=2)
    )
    Folio.objects.create(reservation=res, currency='USD')
    attempt = PaymentAttempt.objects.create(reservation=res, amount_minor=22000, currency='USD', status='SETTLED')
    payment = Payment.objects.create(attempt=attempt, amount_minor=22000)
    refund = Refund.objects.create(payment=payment, amount_minor=5000, reason='Guest requested reduction', requested_by=hotel_setup['reception'])

    # Receptionist cannot approve refund
    assert client.post(f'/api/v1/staff/refunds/{refund.id}/approve').status_code == 403

    # Receptionist can check diagnostics for check-in
    diag_res = client.get(f'/api/v1/staff/reservations/{res.id}/diagnostics')
    assert diag_res.status_code == 200
    diag = diag_res.json()
    assert diag['can_check_in'] is False
    assert any('arrival date' in str(issue).lower() for issue in diag['check_in_issues'])

    # Manager CAN approve refund
    login_as(client, hotel_setup['manager'], portal='staff')
    app_res = client.post(f'/api/v1/staff/refunds/{refund.id}/approve')
    assert app_res.status_code == 200
    refund.refresh_from_db()
    assert refund.status == 'APPROVED'


@pytest.mark.django_db
def test_accountant_workspace_segregation_of_duties(client, hotel_setup):
    """Accountant processes manager-approved refunds, reconciles folios, and cannot approve own refund."""
    r = hotel_setup['r101']
    guest = Guest.objects.create(full_name='Accounting Test', email='acct@example.com')
    today = services.hotel_today(hotel_setup['hotel'])
    res = Reservation.objects.create(
        reference='LH-ACCT-01', guest=guest, room=r,
        arrival=today, departure=today + timedelta(days=1),
        occupants=1, status='CONFIRMED', hold_expires_at=timezone.now() + timedelta(hours=2)
    )
    folio = Folio.objects.create(reservation=res, currency='USD')
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Deluxe Room', amount_minor=20000, service_date=today)
    attempt = PaymentAttempt.objects.create(reservation=res, amount_minor=20000, currency='USD', status='SETTLED')
    payment = Payment.objects.create(attempt=attempt, amount_minor=20000)

    # 1. Settle approved refund
    refund = Refund.objects.create(
        payment=payment, amount_minor=5000, reason='Approved goodwill refund',
        status='APPROVED', requested_by=hotel_setup['reception'], reviewed_by=hotel_setup['manager']
    )

    login_as(client, hotel_setup['accountant'], portal='staff')

    # Accountant sees payment transactions and reconciliation
    payments_res = client.get('/api/v1/accountant/payments')
    assert payments_res.status_code == 200
    assert any(p['reservation_reference'] == 'LH-ACCT-01' for p in payments_res.json())

    recon_res = client.get('/api/v1/accountant/reconciliation')
    assert recon_res.status_code == 200
    assert any(rec['reference'] == 'LH-ACCT-01' for rec in recon_res.json())

    # Accountant can settle manager-approved refund
    settle_res = client.post(f'/api/v1/staff/refunds/{refund.id}/settle')
    assert settle_res.status_code == 200
    refund.refresh_from_db()
    assert refund.status == 'SETTLED'

    # Accountant cannot settle unapproved refund
    unapproved = Refund.objects.create(
        payment=payment, amount_minor=2000, reason='Not yet reviewed',
        status='PENDING', requested_by=hotel_setup['reception']
    )
    fail_res = client.post(f'/api/v1/staff/refunds/{unapproved.id}/settle')
    assert fail_res.status_code == 400

    # Accountant cannot settle their own refund request (segregation of duties)
    self_requested = Refund.objects.create(
        payment=payment, amount_minor=1000, reason='Self refund',
        status='APPROVED', requested_by=hotel_setup['accountant'], reviewed_by=hotel_setup['manager']
    )
    self_settle_res = client.post(f'/api/v1/staff/refunds/{self_requested.id}/settle')
    assert self_settle_res.status_code == 403

    # Accountant can record folio reconciliation audit
    reconcile_res = client.post(f'/api/v1/accountant/folios/{res.id}/reconcile')
    assert reconcile_res.status_code == 200
    assert Audit.objects.filter(actor='accountant_user', action='FOLIO_RECONCILED').exists()


# ==============================================================================
# 2. Complete 10-Step Connected Cross-Role Workflow
# ==============================================================================

@pytest.mark.django_db
def test_ten_step_connected_cross_role_workflow(client, hotel_setup):
    """
    Connected 10-Step Workflow using persisted PostgreSQL records:
    1. Reception checks a verified guest in.
    2. Guest requests a service.
    3. Reception handles the request.
    4. Guest settles the final balance and checks out.
    5. Checkout marks the room dirty and creates one housekeeping task.
    6. Housekeeping cleans the room and requests inspection.
    7. Reception or manager inspects and marks it ready.
    8. Accountant reconciles the payment and audits folio.
    9. Manager sees the updated occupancy, revenue, and operational metrics.
    10. Admin reviews who performed the sensitive actions in the audit history.
    """
    hotel = hotel_setup['hotel']
    room = hotel_setup['r101']
    today = services.hotel_today(hotel)
    tomorrow = today + timedelta(days=1)

    # Setup Confirmed & Paid Booking
    guest = Guest.objects.create(full_name='Arthur Pendelton', email='arthur@example.test')
    res = Reservation.objects.create(
        reference='LH-FLOW-10',
        guest=guest,
        room=room,
        arrival=today,
        departure=tomorrow,
        occupants=1,
        status='CONFIRMED',
        verified=True,
        hold_expires_at=timezone.now() + timedelta(hours=4)
    )
    Allocation.objects.create(room=room, reservation=res, period=Range(today, tomorrow, '[)'), kind='CONFIRMED', active=True)
    folio = Folio.objects.create(reservation=res, currency='USD')
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Deluxe Night', amount_minor=20000, service_date=today)
    FolioEntry.objects.create(folio=folio, category='TAX', description='Room Tax', amount_minor=2000, service_date=today)
    attempt = PaymentAttempt.objects.create(reservation=res, amount_minor=22000, currency='USD', status='SETTLED')
    Payment.objects.create(attempt=attempt, amount_minor=22000)

    # STEP 1: Reception checks verified guest in
    login_as(client, hotel_setup['reception'], portal='staff')
    in_res = client.post(f'/api/v1/reservations/{res.id}/check-in', HTTP_X_PORTAL='staff')
    assert in_res.status_code == 200
    res.refresh_from_db()
    assert res.status == 'CHECKED_IN'
    stay = Stay.objects.get(reservation=res)
    assert stay.actor.username == 'reception_user'
    assert Audit.objects.filter(actor='reception_user', action='CHECK_IN').exists()

    # STEP 2: Guest requests a service
    client.post('/api/v1/auth/logout', HTTP_X_PORTAL='staff')
    # Guest session
    session = client.session
    session['guest_reservation'] = res.id
    session.save()
    req_res = client.post(f'/api/v1/reservations/{res.id}/service-requests', {
        'type': 'Extra Towels',
        'description': 'Two extra bath sheets please'
    }, content_type='application/json')
    assert req_res.status_code == 201
    service_req = ServiceRequest.objects.get(stay=stay)
    assert service_req.status == 'SUBMITTED'

    # STEP 3: Reception handles the request
    login_as(client, hotel_setup['reception'], portal='staff')
    comp_res = client.post(f'/api/v1/staff/service-requests/{service_req.id}/complete')
    assert comp_res.status_code == 200
    service_req.refresh_from_db()
    assert service_req.status == 'COMPLETED'
    assert service_req.assignee.username == 'reception_user'

    # STEP 4: Guest settles final balance and checks out
    # Folio balance is $0.00, check-out succeeds
    client.post('/api/v1/auth/logout', HTTP_X_PORTAL='staff')
    session = client.session
    session['guest_reservation'] = res.id
    session.save()
    folio.refresh_from_db()
    out_res = client.post(f'/api/v1/reservations/{res.id}/check-out', {
        'folio_version': folio.version
    }, content_type='application/json')
    assert out_res.status_code == 200
    res.refresh_from_db()
    assert res.status == 'CHECKED_OUT'

    # STEP 5: Checkout marks room dirty and creates one housekeeping task
    room.refresh_from_db()
    assert room.cleaning == 'DIRTY'
    hk_tasks = HousekeepingTask.objects.filter(room=room)
    assert hk_tasks.count() == 1
    hk_task = hk_tasks.first()
    assert hk_task.status == 'DIRTY'

    # Duplicate checkout cannot create duplicate task
    client.post(f'/api/v1/reservations/{res.id}/check-out', {'folio_version': folio.version}, content_type='application/json')
    assert HousekeepingTask.objects.filter(room=room).count() == 1

    # STEP 6: Housekeeping cleans the room and requests inspection
    login_as(client, hotel_setup['housekeeping'], portal='staff')
    start_clean = client.post(f'/api/v1/housekeeping/tasks/{hk_task.id}/transition', {'status': 'CLEANING'}, content_type='application/json')
    assert start_clean.status_code == 200
    req_insp = client.post(f'/api/v1/housekeeping/tasks/{hk_task.id}/transition', {'status': 'INSPECTION', 'notes': 'Deep clean complete'}, content_type='application/json')
    assert req_insp.status_code == 200
    hk_task.refresh_from_db()
    assert hk_task.status == 'INSPECTION'
    assert hk_task.notes == 'Deep clean complete'
    assert Audit.objects.filter(actor='housekeeping_user', action='HOUSEKEEPING_INSPECTION').exists()

    # STEP 7: Reception inspects and marks it ready
    login_as(client, hotel_setup['reception'], portal='staff')
    inspect_res = client.post(f'/api/v1/housekeeping/tasks/{hk_task.id}/transition', {'status': 'READY'}, content_type='application/json')
    assert inspect_res.status_code == 200
    room.refresh_from_db()
    assert room.cleaning == 'READY'
    assert Audit.objects.filter(actor='reception_user', action='HOUSEKEEPING_READY').exists()

    # STEP 8: Accountant reconciles the payment and audits folio
    login_as(client, hotel_setup['accountant'], portal='staff')
    recon_res = client.get('/api/v1/accountant/reconciliation')
    assert recon_res.status_code == 200
    flow_rec = next(r for r in recon_res.json() if r['reference'] == 'LH-FLOW-10')
    assert flow_rec['is_balanced'] is True
    assert flow_rec['balance_minor'] == 0
    audit_folio_res = client.post(f'/api/v1/accountant/folios/{res.id}/reconcile')
    assert audit_folio_res.status_code == 200
    assert Audit.objects.filter(actor='accountant_user', action='FOLIO_RECONCILED').exists()

    # STEP 9: Manager sees updated occupancy, revenue, and operational metrics
    login_as(client, hotel_setup['manager'], portal='staff')
    dash_res = client.get(f'/api/v1/manager/dashboard?start={today}&end={tomorrow}')
    assert dash_res.status_code == 200
    kpis = dash_res.json()['kpis']
    assert kpis['sold_room_nights'] >= 1
    assert kpis['settled_cash_minor'] >= 22000

    # STEP 10: Admin reviews who performed sensitive actions in the audit history
    login_as(client, hotel_setup['admin'], portal='admin')
    audit_res = client.get('/api/v1/admin/audit')
    assert audit_res.status_code == 200
    actions = [a['action'] for a in audit_res.json()]
    assert 'CHECK_IN' in actions
    assert 'CHECK_OUT' in actions
    assert 'HOUSEKEEPING_INSPECTION' in actions
    assert 'HOUSEKEEPING_READY' in actions
    assert 'FOLIO_RECONCILED' in actions
