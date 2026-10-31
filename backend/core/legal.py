"""Legal documents, consent capture, data-subject requests and retention (domain rules for P1)."""
import hashlib
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from .models import (Audit, ConsentRecord, DataSubjectRequest, FolioEntry, Guest, LegalDocument,
                     OTP, Payment, Quote, Refund, Reservation, ServiceRequest)

BOOKING_KINDS = ('TERMS', 'PRIVACY', 'CANCELLATION')
LANGUAGES = ('en', 'km')
REQUEST_DUE_DAYS = 30


def hash_value(value):
    return hashlib.sha256(f'{settings.SECRET_KEY}:{value or ""}'.encode()).hexdigest()


def current_documents(language='en', kinds=None):
    """Latest published version per kind; falls back to English when a translation is missing."""
    result = {}
    qs = LegalDocument.objects.filter(status='PUBLISHED')
    for kind in (kinds or [k for k, _ in LegalDocument._meta.get_field('kind').choices]):
        doc = (qs.filter(kind=kind, language=language).order_by('-version').first()
               or qs.filter(kind=kind, language='en').order_by('-version').first())
        if doc:
            result[kind] = doc
    return result


def is_current(doc):
    latest = LegalDocument.objects.filter(status='PUBLISHED', kind=doc.kind, language=doc.language).aggregate(v=Max('version'))['v']
    return doc.status == 'PUBLISHED' and doc.version == latest


def validate_consent(document_ids, required_kinds):
    """Return the accepted documents, or raise ValueError when a required current version is missing."""
    try:
        ids = {int(x) for x in (document_ids or [])}
    except (TypeError, ValueError):
        raise ValueError('Invalid consent payload')
    docs = list(LegalDocument.objects.filter(pk__in=ids))
    if len(docs) != len(ids):
        raise ValueError('Unknown legal document')
    accepted = {}
    for doc in docs:
        if not is_current(doc):
            raise ValueError('A legal document has a newer version; reload and accept again')
        accepted[doc.kind] = doc
    missing = [k for k in required_kinds if k not in accepted
               and current_documents('en', [k]).get(k) is not None]
    if missing:
        raise ValueError('You must accept: ' + ', '.join(missing))
    return docs


def record_consent(docs, *, guest=None, user=None, method='BOOKING', ip=None, user_agent=None):
    for doc in docs:
        ConsentRecord.objects.create(document=doc, guest=guest, user=user, method=method,
                                     ip_hash=hash_value(ip), user_agent_hash=hash_value(user_agent))


def pending_staff_documents(user, language='en'):
    docs = current_documents(language, ['STAFF_AGREEMENT'])
    doc = docs.get('STAFF_AGREEMENT')
    if not doc:
        return []
    accepted = ConsentRecord.objects.filter(user=user, document__kind='STAFF_AGREEMENT', document__version=doc.version).exists()
    return [] if accepted else [doc]


@transaction.atomic
def publish(doc, actor):
    if doc.status == 'PUBLISHED':
        raise ValueError('Already published')
    latest = LegalDocument.objects.filter(kind=doc.kind, language=doc.language, status='PUBLISHED').aggregate(v=Max('version'))['v'] or 0
    if doc.version <= latest:
        doc.version = latest + 1
    doc.status = 'PUBLISHED'
    doc.effective_at = timezone.now()
    doc.save()
    Audit.objects.create(actor=actor, action='LEGAL_PUBLISHED', target=f'{doc.kind}/{doc.language}/v{doc.version}')
    return doc


def new_draft(kind, language, title, body, actor):
    version = (LegalDocument.objects.filter(kind=kind, language=language).aggregate(v=Max('version'))['v'] or 0) + 1
    return LegalDocument.objects.create(kind=kind, language=language, version=version, title=title,
                                        body_markdown=body, created_by=actor)


def seed_templates(actor='system'):
    """Idempotently publish starter templates for kinds/languages that have no published version."""
    from .legal_templates import NOTICE_EN, NOTICE_KM, TEMPLATES
    created = 0
    for kind, langs in TEMPLATES.items():
        for lang, (title, body) in langs.items():
            if LegalDocument.objects.filter(kind=kind, language=lang).exists():
                continue
            notice = NOTICE_EN if lang == 'en' else NOTICE_KM
            LegalDocument.objects.create(kind=kind, language=lang, version=1, title=title, body_markdown=notice + body,
                                         status='PUBLISHED', effective_at=timezone.now(), created_by=actor)
            created += 1
    return created


# ---- data-subject rights -------------------------------------------------

def export_guest_data(guest):
    reservations = Reservation.objects.filter(guest=guest).select_related('room__type', 'folio')
    return {
        'exported_at': timezone.now().isoformat(),
        'guest': {'full_name': guest.full_name, 'email': guest.email, 'phone': guest.phone,
                  'anonymized_at': guest.anonymized_at.isoformat() if guest.anonymized_at else None},
        'reservations': [{
            'reference': r.reference, 'status': r.status, 'arrival': r.arrival.isoformat(),
            'departure': r.departure.isoformat(), 'room_type': r.room.type.name, 'occupants': r.occupants,
            'currency': r.folio.currency,
            'folio_entries': list(FolioEntry.objects.filter(folio=r.folio).values('category', 'description', 'amount_minor', 'service_date')),
            'payments': list(Payment.objects.filter(attempt__reservation=r).values('amount_minor', 'settled_at')),
            'refunds': list(Refund.objects.filter(payment__attempt__reservation=r).values('amount_minor', 'status', 'created_at')),
            'service_requests': list(ServiceRequest.objects.filter(stay__reservation=r).values('type', 'description', 'status')),
        } for r in reservations],
        'consents': list(ConsentRecord.objects.filter(guest=guest).values('document__kind', 'document__language', 'document__version', 'method', 'accepted_at')),
        'data_requests': list(DataSubjectRequest.objects.filter(guest=guest).values('type', 'status', 'requested_at', 'due_at')),
    }


def anonymization_blockers(guest):
    """Reasons a guest cannot be anonymised right now."""
    blockers = []
    live = Reservation.objects.filter(guest=guest, status__in=['HOLD', 'CONFIRMED', 'CHECKED_IN'])
    if live.exists():
        blockers.append('Guest has an active or upcoming reservation')
    return blockers


@transaction.atomic
def anonymize_guest(guest, actor='system'):
    guest = Guest.objects.select_for_update().get(pk=guest.pk)
    if guest.anonymized_at:
        return False
    blockers = anonymization_blockers(guest)
    if blockers:
        raise ValueError('; '.join(blockers))
    guest.full_name = 'Anonymized guest'
    guest.email = f'anonymized+{guest.pk}@invalid.local'
    guest.phone = ''
    guest.anonymized_at = timezone.now()
    guest.save(update_fields=['full_name', 'email', 'phone', 'anonymized_at'])
    OTP.objects.filter(reservation__guest=guest).delete()
    Audit.objects.create(actor=actor, action='GUEST_ANONYMIZED', target=f'guest:{guest.pk}')
    return True


def open_request(guest, type_, note=''):
    existing = DataSubjectRequest.objects.filter(guest=guest, type=type_, status='OPEN').first()
    if existing:
        return existing
    now = timezone.now()
    req = DataSubjectRequest.objects.create(guest=guest, type=type_, note=note[:500], due_at=now + timedelta(days=REQUEST_DUE_DAYS))
    Audit.objects.create(actor=f'guest:{guest.pk}', action='DATA_REQUEST_OPENED', target=f'{type_}:{req.pk}')
    return req


@transaction.atomic
def resolve_request(req, decision, actor, resolution=''):
    req = DataSubjectRequest.objects.select_for_update().get(pk=req.pk)
    if req.status != 'OPEN':
        raise ValueError('Request already handled')
    if decision == 'reject':
        if not resolution.strip():
            raise ValueError('A reason is required to reject a request')
        req.status = 'REJECTED'
    elif decision == 'complete':
        if req.type == 'DELETE':
            anonymize_guest(req.guest, actor)
        req.status = 'COMPLETED'
    else:
        raise ValueError('Unknown decision')
    req.resolution, req.handled_by, req.handled_at = resolution[:500], actor, timezone.now()
    req.save()
    Audit.objects.create(actor=actor, action='DATA_REQUEST_' + req.status, target=f'{req.type}:{req.pk}')
    return req


# ---- retention -----------------------------------------------------------

def run_retention(now=None):
    now = now or timezone.now()
    guest_cutoff = (now - timedelta(days=365 * settings.RETENTION_GUEST_YEARS)).date()
    cutoff = now - timedelta(hours=settings.RETENTION_SHORT_LIVED_HOURS)
    otp_deleted = OTP.objects.filter(issued_at__lt=cutoff).delete()[0]
    quote_deleted = Quote.objects.filter(expires_at__lt=cutoff).delete()[0]
    anonymized = 0
    candidates = (Guest.objects.filter(anonymized_at__isnull=True)
                  .exclude(reservation__departure__gte=guest_cutoff)
                  .exclude(reservation__status__in=['HOLD', 'CONFIRMED', 'CHECKED_IN']).distinct())
    for guest in candidates:
        if Reservation.objects.filter(guest=guest).exists():
            try:
                anonymized += int(anonymize_guest(guest, 'retention'))
            except ValueError:
                continue
    from .models import ErrorEvent, JobRun
    JobRun.objects.filter(started_at__lt=now - timedelta(days=30)).delete()
    ErrorEvent.objects.filter(created_at__lt=now - timedelta(days=90)).delete()
    result = {'otp_deleted': otp_deleted, 'quotes_deleted': quote_deleted, 'guests_anonymized': anonymized}
    Audit.objects.create(actor='retention', action='RETENTION_RUN',
                         target=f'otp={otp_deleted}:quotes={quote_deleted}:guests={anonymized}')
    return result
