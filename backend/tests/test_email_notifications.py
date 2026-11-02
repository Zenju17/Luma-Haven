import pytest
from django.core import mail
from datetime import timedelta
from django.utils import timezone
from core.models import Hotel, Room, RoomType, Reservation, Guest, Folio, FolioEntry
from core.emails import send_otp_email, send_booking_confirmation_email, send_payment_confirmed_email
from core import services

JSON = 'application/json'


@pytest.fixture
def sample_reservation(db):
    hotel = Hotel.objects.create(name='Luma Haven', timezone='Asia/Phnom_Penh', currency='USD', check_in_time='14:00', check_out_time='11:00')
    rt = RoomType.objects.create(hotel=hotel, name='Panoramic King', nightly_rate_minor=15000, capacity=2)
    room = Room.objects.create(hotel=hotel, type=rt, number='204')
    guest = Guest.objects.create(full_name='Elena Rostova', email='elena@example.com')
    res = Reservation.objects.create(
        reference='TESTREF1234',
        guest=guest,
        room=room,
        arrival=timezone.now().date() + timedelta(days=5),
        departure=timezone.now().date() + timedelta(days=8),
        occupants=2,
        hold_expires_at=timezone.now() + timedelta(minutes=15),
    )
    folio = Folio.objects.create(reservation=res, currency='USD')
    FolioEntry.objects.create(folio=folio, category='ROOM', description='3 Room Nights', amount_minor=45000, service_date=res.arrival)
    return res


def test_send_otp_email_structure():
    mail.outbox.clear()
    ok = send_otp_email('testguest@example.com', 'Alex Rivera', 'LH-TESTREF', '482910')
    assert ok is True
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ['testguest@example.com']
    assert '482910' in msg.subject
    assert '482910' in msg.body
    assert '5 minutes' in msg.body

    # Check HTML alternative
    html_alternatives = [c for c, m in msg.alternatives if m == 'text/html']
    assert len(html_alternatives) == 1
    assert '482910' in html_alternatives[0]
    assert 'LH-TESTREF' in html_alternatives[0]


def test_send_booking_confirmation_email(sample_reservation):
    mail.outbox.clear()
    ok = send_booking_confirmation_email(sample_reservation)
    assert ok is True
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == [sample_reservation.guest.email]
    assert sample_reservation.reference in msg.subject
    assert sample_reservation.reference in msg.body
    assert 'Panoramic King' in msg.body
    assert 'Room 204' in msg.body
    assert '$450.00' in msg.body
    assert '/booking/' in msg.body

    # Check HTML
    html_parts = [c for c, m in msg.alternatives if m == 'text/html']
    assert len(html_parts) == 1
    assert sample_reservation.guest.full_name in html_parts[0]
    assert sample_reservation.reference in html_parts[0]


def test_send_payment_confirmed_email(sample_reservation):
    mail.outbox.clear()
    ok = send_payment_confirmed_email(sample_reservation, 45000)
    assert ok is True
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert 'Payment Confirmed' in msg.subject
    assert '$450.00' in msg.body
    assert sample_reservation.reference in msg.body


def test_request_otp_dispatches_email(client, sample_reservation, monkeypatch):
    mail.outbox.clear()
    sample_reservation.status = 'CONFIRMED'
    sample_reservation.save(update_fields=['status'])

    res = client.post('/api/v1/guest-access/request-otp', {
        'reference': sample_reservation.reference,
        'email': sample_reservation.guest.email
    }, content_type=JSON)

    assert res.status_code == 200
    assert len(mail.outbox) == 1
    assert sample_reservation.reference in mail.outbox[0].body
