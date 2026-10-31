from datetime import timedelta
import pytest
from django.utils import timezone
from core import legal, services
from core.models import (ConsentRecord, DataSubjectRequest, Folio, Guest, Hotel, LegalDocument, OTP,
                         Quote, Reservation, Room, RoomType, User)

JSON = 'application/json'


@pytest.fixture
def docs(db):
    LegalDocument.objects.all().delete()
    legal.seed_templates()
    return legal.current_documents('en')


@pytest.fixture
def room(db):
    hotel = Hotel.objects.create(name='Test Hotel', tax_percent=10)
    kind = RoomType.objects.create(hotel=hotel, name='Twin', nightly_rate_minor=10000)
    return Room.objects.create(hotel=hotel, type=kind, number='1')


def quote_for(room):
    start = services.hotel_today(room.hotel) + timedelta(days=5)
    return services.create_quote(room, start, start + timedelta(days=2), 2)


def login(client, portal, role):
    User.objects.create_user(username=f'{role}-u', password='test-only', role=role)
    assert client.post('/api/v1/auth/login', {'username': f'{role}-u', 'password': 'test-only'},
                       content_type=JSON, HTTP_X_PORTAL=portal).status_code == 200


def book(client, room, ids):
    return client.post('/api/v1/reservations', {'quote_id': str(quote_for(room).pk), 'name': 'Sok', 'email': 'sok@example.com',
                                                'consent_document_ids': ids}, content_type=JSON)


def required_ids(docs):
    return [docs[k].pk for k in legal.BOOKING_KINDS]


def test_templates_seed_en_and_km_for_every_kind(docs):
    for lang in ('en', 'km'):
        assert set(legal.current_documents(lang)) == {'TERMS', 'PRIVACY', 'CANCELLATION', 'COOKIES', 'PAYMENT', 'STAFF_AGREEMENT'}
    assert legal.current_documents('km')['PRIVACY'].language == 'km'
    assert legal.seed_templates() == 0  # idempotent


def test_public_legal_api_serves_language_with_fallback(client, docs):
    body = client.get('/api/v1/legal/documents/privacy?lang=km').json()
    assert body['language'] == 'km' and body['body_markdown']
    assert client.get('/api/v1/legal/documents/privacy?lang=fr').json()['language'] == 'en'
    assert client.get('/api/v1/legal/documents/nope').status_code == 404


def test_booking_requires_current_consent_and_records_it(client, room, docs):
    assert book(client, room, []).status_code == 400
    assert book(client, room, [docs['TERMS'].pk]).status_code == 400  # privacy + cancellation missing
    assert Reservation.objects.count() == 0
    response = book(client, room, required_ids(docs))
    assert response.status_code == 201
    guest = Reservation.objects.get().guest
    assert ConsentRecord.objects.filter(guest=guest).count() == 3
    assert ConsentRecord.objects.filter(guest=guest).first().ip_hash not in ('', '127.0.0.1')


def test_new_version_forces_reconsent(client, room, docs):
    old_ids = required_ids(docs)
    draft = legal.new_draft('TERMS', 'en', 'Terms v2', 'new text', 'admin')
    legal.publish(draft, 'admin')
    assert draft.version == 2
    assert book(client, room, old_ids).status_code == 400
    fresh = legal.current_documents('en')
    assert book(client, room, required_ids(fresh)).status_code == 201


def test_published_documents_and_consents_are_immutable(docs):
    doc = docs['TERMS']
    doc.body_markdown = 'tampered'
    with pytest.raises(ValueError):
        doc.save()
    with pytest.raises(ValueError):
        doc.delete()
    guest = Guest.objects.create(full_name='A', email='a@example.com')
    legal.record_consent([doc], guest=guest)
    record = ConsentRecord.objects.get()
    with pytest.raises(ValueError):
        record.save()
    with pytest.raises(ValueError):
        record.delete()


def test_admin_legal_api_is_admin_only_and_publishes(client, docs):
    assert client.get('/api/v1/admin/legal').status_code == 403
    login(client, 'staff', 'MANAGER')
    assert client.get('/api/v1/admin/legal').status_code == 403
    client.post('/api/v1/auth/logout', {}, content_type=JSON, HTTP_X_PORTAL='staff')
    login(client, 'admin', 'ADMIN')
    created = client.post('/api/v1/admin/legal', {'kind': 'terms', 'language': 'en', 'title': 'T', 'body_markdown': 'x'}, content_type=JSON)
    assert created.status_code == 201
    pk = created.json()['id']
    assert client.patch(f'/api/v1/admin/legal/{pk}', {'body_markdown': 'edited'}, content_type=JSON).status_code == 200
    assert client.post(f'/api/v1/admin/legal/{pk}/publish', {}, content_type=JSON).json()['status'] == 'PUBLISHED'
    assert client.patch(f'/api/v1/admin/legal/{pk}', {'body_markdown': 'again'}, content_type=JSON).status_code == 400
    assert legal.current_documents('en')['TERMS'].pk == pk


def test_staff_agreement_flag_and_acceptance(client, docs):
    login(client, 'staff', 'RECEPTION')
    me = client.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json()
    assert [d['kind'] for d in me['pending_agreements']] == ['STAFF_AGREEMENT']
    ids = [me['pending_agreements'][0]['id']]
    assert client.post('/api/v1/auth/accept-agreement', {'consent_document_ids': ids}, content_type=JSON, HTTP_X_PORTAL='staff').status_code == 201
    assert client.get('/api/v1/auth/me', HTTP_X_PORTAL='staff').json()['pending_agreements'] == []


def verified_reservation(client, room, docs):
    response = book(client, room, required_ids(docs))
    reservation = Reservation.objects.get(pk=response.json()['id'])
    return reservation


def test_guest_export_requires_verification_and_is_scoped(client, room, docs):
    reservation = verified_reservation(client, room, docs)
    other = Guest.objects.create(full_name='Other', email='other@example.com')
    url = f'/api/v1/reservations/{reservation.pk}/data-export'
    assert client.get(url).status_code == 403  # booking session exists but is not verified
    reservation.verified = True
    reservation.save()
    data = client.get(url).json()
    assert data['guest']['email'] == 'sok@example.com'
    assert len(data['reservations']) == 1 and 'other@example.com' not in str(data)
    assert other.pk != reservation.guest_id


def test_delete_request_flow_anonymizes_but_keeps_folio(client, room, docs):
    reservation = verified_reservation(client, room, docs)
    reservation.verified = True
    reservation.save()
    created = client.post(f'/api/v1/reservations/{reservation.pk}/data-requests', {'type': 'delete'}, content_type=JSON)
    assert created.status_code == 201
    req_id = created.json()['id']
    # idempotent while open
    assert client.post(f'/api/v1/reservations/{reservation.pk}/data-requests', {'type': 'delete'}, content_type=JSON).json()['id'] == req_id

    login(client, 'admin', 'ADMIN')
    # active reservation blocks anonymisation
    assert client.post(f'/api/v1/admin/data-requests/{req_id}/resolve', {'decision': 'complete'}, content_type=JSON).status_code == 400
    reservation.status = 'CHECKED_OUT'
    reservation.save()
    total_before = sum(e.amount_minor for e in Folio.objects.get(reservation=reservation).entries.all())
    done = client.post(f'/api/v1/admin/data-requests/{req_id}/resolve', {'decision': 'complete'}, content_type=JSON)
    assert done.status_code == 200 and done.json()['status'] == 'COMPLETED'
    guest = Guest.objects.get(pk=reservation.guest_id)
    assert guest.full_name == 'Anonymized guest' and guest.email.endswith('@invalid.local') and guest.anonymized_at
    assert sum(e.amount_minor for e in Folio.objects.get(reservation=reservation).entries.all()) == total_before
    assert client.post(f'/api/v1/admin/data-requests/{req_id}/resolve', {'decision': 'reject', 'resolution': 'x'}, content_type=JSON).status_code == 400


def test_reject_requires_reason(docs, db):
    guest = Guest.objects.create(full_name='A', email='a@example.com')
    req = legal.open_request(guest, 'EXPORT')
    with pytest.raises(ValueError):
        legal.resolve_request(req, 'reject', 'admin', '')
    assert legal.resolve_request(req, 'reject', 'admin', 'identity not verified').status == 'REJECTED'


def test_retention_respects_each_period(room, docs):
    now = timezone.now()
    old_day = (now - timedelta(days=365 * 4)).date()
    recent_day = (now - timedelta(days=30)).date()

    def stay(name, departure, status):
        guest = Guest.objects.create(full_name=name, email=f'{name}@example.com')
        res = Reservation.objects.create(reference=name.upper(), guest=guest, room=room, arrival=departure - timedelta(days=1),
                                         departure=departure, occupants=1, status=status, hold_expires_at=now)
        Folio.objects.create(reservation=res, currency='USD')
        return guest, res

    old_guest, old_res = stay('old', old_day, 'CHECKED_OUT')
    recent_guest, recent_res = stay('recent', recent_day, 'CHECKED_OUT')
    live_guest, _ = stay('live', old_day, 'CONFIRMED')
    stale_otp = OTP.objects.create(reservation=recent_res, digest='x', expires_at=now, issued_at=now - timedelta(hours=30))
    fresh_otp = OTP.objects.create(reservation=recent_res, digest='y', expires_at=now, issued_at=now)
    stale_quote = quote_for(room)
    Quote.objects.filter(pk=stale_quote.pk).update(expires_at=now - timedelta(hours=30))

    result = legal.run_retention(now)

    assert result['guests_anonymized'] == 1
    assert Guest.objects.get(pk=old_guest.pk).anonymized_at
    assert not Guest.objects.get(pk=recent_guest.pk).anonymized_at
    assert not Guest.objects.get(pk=live_guest.pk).anonymized_at
    assert not OTP.objects.filter(pk=stale_otp.pk).exists()
    assert OTP.objects.filter(pk=fresh_otp.pk).exists()
    assert not Quote.objects.filter(pk=stale_quote.pk).exists()
    assert Reservation.objects.filter(pk=old_res.pk).exists()  # accounting rows are never deleted
