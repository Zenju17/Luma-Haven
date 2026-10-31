import pytest
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from django.utils import timezone
from psycopg.types.range import Range

from core import services
from core.models import (
    Allocation, Folio, FolioEntry, Guest, Hotel, HousekeepingTask,
    MaintenanceTicket, Payment, PaymentAttempt, Refund, Reservation, Room, RoomType, Stay, User
)
from core.views import report_values


@pytest.fixture
def mis_hotel(db):
    hotel = Hotel.objects.create(name='MIS Grand Haven', timezone='Asia/Phnom_Penh', currency='USD')
    deluxe = RoomType.objects.create(hotel=hotel, name='Deluxe Suite', capacity=2, nightly_rate_minor=15000)
    suite = RoomType.objects.create(hotel=hotel, name='Executive Suite', capacity=4, nightly_rate_minor=30000)
    r101 = Room.objects.create(hotel=hotel, type=deluxe, number='101')
    r102 = Room.objects.create(hotel=hotel, type=deluxe, number='102')
    r201 = Room.objects.create(hotel=hotel, type=suite, number='201')
    return {'hotel': hotel, 'r101': r101, 'r102': r102, 'r201': r201}


@pytest.mark.django_db
def test_zero_denominator_returns_none(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    start = today + timedelta(days=10)
    end = today + timedelta(days=12)

    # All 3 rooms blocked by maintenance in this window
    for room in [mis_hotel['r101'], mis_hotel['r102'], mis_hotel['r201']]:
        Allocation.objects.create(room=room, period=Range(start, end, '[)'), kind='MAINTENANCE')

    result = report_values(start, end)
    assert result['sellable_room_nights'] == 0
    assert result['sold_room_nights'] == 0
    assert result['occupancy_rate_percent'] is None
    assert result['average_daily_rate_minor'] is None
    assert result['revpar_minor'] is None


@pytest.mark.django_db
def test_normal_stay_metrics_and_revenue_recognition(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    room = mis_hotel['r101']
    start = today - timedelta(days=3)
    end = today

    # Guest stayed 2 nights (3 days ago to yesterday)
    guest = Guest.objects.create(full_name='Test Visitor', email='visitor@example.com')
    res = Reservation.objects.create(
        reference='RES-MIS-01', guest=guest, room=room,
        arrival=start, departure=start + timedelta(days=2), occupants=2,
        status='CHECKED_OUT', hold_expires_at=timezone.now()
    )
    alloc = Allocation.objects.create(room=room, reservation=res, period=Range(start, start + timedelta(days=2), '[)'), kind='CONFIRMED')
    stay = Stay.objects.create(
        reservation=res,
        checked_in_at=timezone.now() - timedelta(days=3),
        checked_out_at=timezone.now() - timedelta(days=1)
    )
    folio = Folio.objects.create(reservation=res, currency='USD')
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Night 1', amount_minor=15000, service_date=start)
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Night 2', amount_minor=15000, service_date=start + timedelta(days=1))
    FolioEntry.objects.create(folio=folio, category='TAX', description='Tax', amount_minor=3000, service_date=start)

    # Payment settled on start date
    attempt = PaymentAttempt.objects.create(reservation=res, amount_minor=33000, currency='USD', status='SUCCESS')
    Payment.objects.create(attempt=attempt, amount_minor=33000, settled_at=stay.checked_in_at)

    result = report_values(start, end)
    # Total rooms = 3, days = 3 -> 3 * 3 = 9 sellable room nights
    assert result['sellable_room_nights'] == 9
    assert result['sold_room_nights'] == 2
    # Occupancy = 2 / 9 * 100 = 22.22%
    assert result['occupancy_rate_percent'] == 22.22
    # Net room revenue = 15000 + 15000 = 30000 (taxes excluded)
    assert result['net_room_revenue_minor'] == 30000
    # ADR = 30000 / 2 = 15000
    assert result['average_daily_rate_minor'] == 15000
    # RevPAR = 30000 / 9 = 3333
    assert result['revpar_minor'] == 3333
    assert result['settled_cash_minor'] == 33000


@pytest.mark.django_db
def test_early_checkout_preserves_accuracy(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    room = mis_hotel['r102']
    arrival = today - timedelta(days=4)
    scheduled_departure = today # 4 nights booked

    guest = Guest.objects.create(full_name='Early Leaver', email='early@example.com')
    res = Reservation.objects.create(
        reference='RES-EARLY-01', guest=guest, room=room,
        arrival=arrival, departure=scheduled_departure, occupants=2,
        status='CHECKED_IN', hold_expires_at=timezone.now()
    )
    alloc = Allocation.objects.create(room=room, reservation=res, period=Range(arrival, scheduled_departure, '[)'), kind='CONFIRMED')
    stay = Stay.objects.create(reservation=res, checked_in_at=timezone.now() - timedelta(days=4))
    folio = Folio.objects.create(reservation=res, currency='USD')
    for d in range(4):
        FolioEntry.objects.create(folio=folio, category='ROOM', description=f'Night {d+1}', amount_minor=15000, service_date=arrival + timedelta(days=d))

    # Early checkout performed on day 2 (arrival + 2 days)
    # Guest only stayed 2 nights (arrival and arrival + 1)
    early_checkout_time = timezone.now() - timedelta(days=2)
    stay.checked_out_at = early_checkout_time
    stay.save(update_fields=['checked_out_at'])
    res.status = 'CHECKED_OUT'
    res.save(update_fields=['status'])
    # Shorten allocation to 2 days
    alloc.period = Range(arrival, arrival + timedelta(days=2), '[)')
    alloc.save(update_fields=['period'])

    # Report over the 4-day period
    result = report_values(arrival, scheduled_departure)
    # Total rooms: 3. Period: 4 days. Total sellable: 12.
    assert result['sellable_room_nights'] == 12
    # Sold nights should only be 2, NOT 4!
    assert result['sold_room_nights'] == 2
    # Net room revenue should only be 30000 (2 nights * 15000), NOT 60000!
    assert result['net_room_revenue_minor'] == 30000
    assert result['average_daily_rate_minor'] == 15000


@pytest.mark.django_db
def test_historical_maintenance_preservation(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    room = mis_hotel['r201']
    past_start = today - timedelta(days=5)
    past_end = today - timedelta(days=2) # 3-day block

    # Ticket was resolved yesterday, so active is now False
    alloc = Allocation.objects.create(room=room, period=Range(past_start, past_end, '[)'), kind='MAINTENANCE', active=False)
    ticket = MaintenanceTicket.objects.create(
        room=room, description='Fixed AC unit', status='RESOLVED', allocation=alloc,
        created_at=timezone.now() - timedelta(days=6),
        resolved_at=timezone.now() - timedelta(days=2)
    )

    # When querying the past window, the resolved maintenance block MUST still be accounted for!
    result = report_values(past_start, past_end)
    # 3 rooms * 3 days = 9. Room 201 was blocked for all 3 days -> 9 - 3 = 6 sellable room nights.
    assert result['sellable_room_nights'] == 6


@pytest.mark.django_db
def test_refund_deduction_from_settled_cash(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    start = today - timedelta(days=2)
    end = today

    room = mis_hotel['r101']
    guest = Guest.objects.create(full_name='Refund Guest', email='refund@example.com')
    res = Reservation.objects.create(
        reference='RES-REFUND-01', guest=guest, room=room,
        arrival=start, departure=end, occupants=1,
        status='CANCELLED', hold_expires_at=timezone.now()
    )
    attempt = PaymentAttempt.objects.create(reservation=res, amount_minor=20000, currency='USD', status='SUCCESS')
    payment = Payment.objects.create(attempt=attempt, amount_minor=20000, settled_at=timezone.now() - timedelta(days=1))

    # A refund of 15000 was approved and settled
    Refund.objects.create(
        payment=payment, amount_minor=15000, reason='Guest cancelled within grace window',
        status='SETTLED', settled_at=payment.settled_at + timedelta(hours=2)
    )

    result = report_values(start, end)
    assert result['gross_cash_minor'] == 20000
    assert result['refunded_cash_minor'] == 15000
    assert result['settled_cash_minor'] == 5000 # 20000 - 15000
    assert result['sold_room_nights'] == 0 # Cancelled reservation has 0 sold nights


@pytest.mark.django_db
def test_manager_dashboard_and_permissions(client, mis_hotel):
    User.objects.create_user(username='mgr', password='Password123!', role='MANAGER')
    User.objects.create_user(username='hk', password='Password123!', role='HOUSEKEEPING')

    # Manager portal access
    login_res = client.post('/api/v1/auth/login', {'username': 'mgr', 'password': 'Password123!'},
                            content_type='application/json', HTTP_X_PORTAL='staff')
    assert login_res.status_code == 200

    response = client.get('/api/v1/manager/dashboard', HTTP_X_PORTAL='staff')
    assert response.status_code == 200
    data = response.json()
    assert 'kpis' in data
    assert 'room_types' in data
    assert 'readiness' in data
    assert 'operations' in data
    assert 'alerts' in data
    assert data['readiness']['total'] == 3

    # Housekeeper access must be denied
    client.post('/api/v1/auth/logout', {}, content_type='application/json', HTTP_X_PORTAL='staff')
    hk_res = client.post('/api/v1/auth/login', {'username': 'hk', 'password': 'Password123!'},
                         content_type='application/json', HTTP_X_PORTAL='staff')
    assert hk_res.status_code == 200
    denied = client.get('/api/v1/manager/dashboard', HTTP_X_PORTAL='staff')
    assert denied.status_code == 403


@pytest.mark.django_db
def test_decision_support_engine_structure(mis_hotel):
    from core.decision_support import evaluate_decision_support_alerts
    alerts = evaluate_decision_support_alerts(mis_hotel['hotel'])
    assert isinstance(alerts, list)
    for alert in alerts:
        assert 'id' in alert
        assert 'severity' in alert
        assert 'title' in alert
        assert 'what_happened' in alert
        assert 'records_involved' in alert
        assert 'why_it_matters' in alert
        assert 'recommended_action' in alert


@pytest.mark.django_db
def test_reservation_amendment_workflow(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    room = mis_hotel['r101']
    guest = Guest.objects.create(full_name='Amend Guest', email='amend@example.com')
    res = Reservation.objects.create(
        reference='RES-AMEND-01', guest=guest, room=room,
        arrival=today + timedelta(days=2), departure=today + timedelta(days=4), occupants=2,
        status='CONFIRMED', hold_expires_at=timezone.now()
    )
    alloc = Allocation.objects.create(room=room, reservation=res, period=Range(res.arrival, res.departure, '[)'), kind='CONFIRMED')
    folio = Folio.objects.create(reservation=res, currency='USD')
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Night 1', amount_minor=15000, service_date=res.arrival)
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Night 2', amount_minor=15000, service_date=res.arrival + timedelta(days=1))

    # Amend reservation: extend by 1 night (days 2 to 5 -> 3 nights total)
    new_dep = today + timedelta(days=5)
    updated = services.amend_reservation(res, res.arrival, new_dep, 2, actor_username='test_mgr')

    assert updated.departure == new_dep
    alloc.refresh_from_db()
    assert alloc.period.upper == new_dep

    # Folio should have an ADJUSTMENT entry for +15000 (3 nights * 15000 - 30000 = +15000)
    adj = folio.entries.filter(category='ADJUSTMENT').first()
    assert adj is not None
    assert adj.amount_minor == 15000


@pytest.mark.django_db
def test_room_reassignment_workflow(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    r101 = mis_hotel['r101'] # 15000/night
    r201 = mis_hotel['r201'] # 30000/night (Executive suite)

    guest = Guest.objects.create(full_name='Upgrade Guest', email='upgrade@example.com')
    res = Reservation.objects.create(
        reference='RES-REASSIGN-01', guest=guest, room=r101,
        arrival=today + timedelta(days=1), departure=today + timedelta(days=3), occupants=2,
        status='CONFIRMED', hold_expires_at=timezone.now()
    )
    alloc = Allocation.objects.create(room=r101, reservation=res, period=Range(res.arrival, res.departure, '[)'), kind='CONFIRMED')
    folio = Folio.objects.create(reservation=res, currency='USD')
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Night 1', amount_minor=15000, service_date=res.arrival)
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Night 2', amount_minor=15000, service_date=res.arrival + timedelta(days=1))

    # Reassign to suite
    updated = services.reassign_room(res, r201, actor_username='test_mgr')
    assert updated.room == r201
    alloc.refresh_from_db()
    assert alloc.room == r201

    # Folio should have rate adjustment: (30000 - 15000) * 2 nights = +30000
    adj = folio.entries.filter(category='ADJUSTMENT').first()
    assert adj is not None
    assert adj.amount_minor == 30000


@pytest.mark.django_db
def test_no_show_workflow(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    room = mis_hotel['r101']
    guest = Guest.objects.create(full_name='No Show Guest', email='noshow@example.com')
    res = Reservation.objects.create(
        reference='RES-NOSHOW-01', guest=guest, room=room,
        arrival=today, departure=today + timedelta(days=2), occupants=1,
        status='CONFIRMED', hold_expires_at=timezone.now()
    )
    alloc = Allocation.objects.create(room=room, reservation=res, period=Range(res.arrival, res.departure, '[)'), kind='CONFIRMED')

    updated = services.mark_no_show(res, actor_username='test_reception')
    assert updated.status == 'NO_SHOW'
    assert updated.cancelled_at is not None
    alloc.refresh_from_db()
    assert not alloc.active


@pytest.mark.django_db
def test_refund_workflow_lifecycle(mis_hotel):
    today = services.hotel_today(mis_hotel['hotel'])
    mgr = User.objects.create_user(username='refund_mgr', password='Password123!', role='MANAGER')
    room = mis_hotel['r101']
    guest = Guest.objects.create(full_name='Refund Lifecycle', email='rf@example.com')
    res = Reservation.objects.create(
        reference='RES-RF-01', guest=guest, room=room,
        arrival=today + timedelta(days=1), departure=today + timedelta(days=3), occupants=1,
        status='CONFIRMED', hold_expires_at=timezone.now()
    )
    folio = Folio.objects.create(reservation=res, currency='USD')
    FolioEntry.objects.create(folio=folio, category='ROOM', description='Room', amount_minor=30000, service_date=res.arrival)
    attempt = PaymentAttempt.objects.create(reservation=res, amount_minor=30000, currency='USD', status='SUCCESS')
    payment = Payment.objects.create(attempt=attempt, amount_minor=30000)

    # 1. Request refund
    refund = services.request_refund(payment, 10000, 'Guest requested cancellation', mgr)
    assert refund.status == 'PENDING'
    assert refund.amount_minor == 10000

    # 2. Approve refund
    approved = services.approve_refund(refund, mgr)
    assert approved.status == 'APPROVED'
    assert approved.reviewed_by == mgr

    # 3. Settle refund
    settled = services.settle_refund(approved, mgr)
    assert settled.status == 'SETTLED'
    assert settled.settled_at is not None

    # Verify folio entry added as credit (-10000)
    rf_entry = folio.entries.filter(category='REFUND').first()
    assert rf_entry is not None
    assert rf_entry.amount_minor == -10000
    # Net balance check: charges(30000) - (paid(30000) - refunded(10000)) + folio_refund(-10000) = 0 balance
    assert services.balance(folio) == 0


@pytest.mark.django_db
def test_housekeeping_task_assignment(mis_hotel):
    cleaner = User.objects.create_user(username='cleaner1', password='Password123!', role='HOUSEKEEPING')
    room = mis_hotel['r101']
    task = HousekeepingTask.objects.create(room=room, status='DIRTY')

    updated = services.assign_housekeeping_task(task, cleaner, actor_username='desk')
    assert updated.assignee == cleaner


@pytest.mark.django_db
def test_room_rate_update_and_audit(mis_hotel):
    deluxe = mis_hotel['r101'].type
    old_rate = deluxe.nightly_rate_minor
    updated = services.update_room_rate(deluxe, 18500, actor_username='admin_user')
    assert updated.nightly_rate_minor == 18500
    from core.models import Audit
    audit_entry = Audit.objects.filter(action='UPDATE_ROOM_RATE').first()
    assert audit_entry is not None
    assert f'{old_rate}->18500' in audit_entry.target


@pytest.mark.django_db
def test_scheduled_mis_reports_and_csv_sanitization(client, mis_hotel):
    User.objects.create_user(username='rep_mgr', password='Password123!', role='MANAGER')
    login_res = client.post('/api/v1/auth/login', {'username': 'rep_mgr', 'password': 'Password123!'},
                            content_type='application/json', HTTP_X_PORTAL='staff')
    assert login_res.status_code == 200

    # 1. Daily summary report
    res1 = client.get('/api/v1/reports/daily-summary', HTTP_X_PORTAL='staff')
    assert res1.status_code == 200

    # 2. Revenue & Occupancy report with CSV export
    res2 = client.get('/api/v1/reports/revenue-occupancy?export=csv', HTTP_X_PORTAL='staff')
    assert res2.status_code == 200
    assert res2['Content-Type'].startswith('text/csv')
    assert b'Room Type,Total Rooms,Sellable Nights' in res2.content

    # 3. Cash reconciliation report with CSV export
    res3 = client.get('/api/v1/reports/cash-reconciliation?export=csv', HTTP_X_PORTAL='staff')
    assert res3.status_code == 200
    assert res3['Content-Type'].startswith('text/csv')
    assert b'Type,Record ID,Reservation Ref' in res3.content

    # 4. Housekeeping turnaround report with CSV export
    res4 = client.get('/api/v1/reports/housekeeping-turnaround?export=csv', HTTP_X_PORTAL='staff')
    assert res4.status_code == 200
    assert res4['Content-Type'].startswith('text/csv')

    # 5. Accounts receivable aging report with CSV export
    res5 = client.get('/api/v1/reports/accounts-receivable?export=csv', HTTP_X_PORTAL='staff')
    assert res5.status_code == 200
    assert res5['Content-Type'].startswith('text/csv')


@pytest.mark.django_db
def test_public_rooms_catalog_stripped(client, mis_hotel):
    # Unauthenticated / guest client
    res = client.get('/api/v1/rooms')
    assert res.status_code == 200
    rooms = res.json()
    assert len(rooms) == 3
    for room in rooms:
        # Public catalog must not leak internal operations or cleaning statuses!
        assert 'cleaning' not in room
        assert 'in_service' not in room
        assert 'occupied' not in room
        assert 'number' in room
        assert 'rate_minor' in room

