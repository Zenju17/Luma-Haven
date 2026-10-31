import secrets
import csv
import hashlib
from datetime import date, datetime, time, timedelta
from io import StringIO
from PIL import Image
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.db import IntegrityError, models, transaction
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import api_view, throttle_classes
from . import throttling
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from . import legal, services, staff_passwords
from .payments import service as payment_service
from .payments.base import ProviderError  # noqa: F401
from .decision_support import evaluate_decision_support_alerts
from .models import (Allocation, Audit, ConsentRecord, DataSubjectRequest, LegalDocument, Folio, FolioEntry, Hotel, HousekeepingTask,
                     OTP, Outbox, Payment, ROLES, PaymentAttempt, PaymentException, Quote, Refund,
                     Reservation, Room, RoomType, ServiceRequest, Stay, MaintenanceTicket, User,
                     VisualAsset)

ADMIN_PORTAL_ROLES = ('ADMIN', 'DEVELOPER', 'CONTENT_EDITOR')

def staff(request, *roles):
    if request.portal not in ('staff', 'admin') or not request.user.is_authenticated or request.user.role not in roles:
        raise PermissionDenied('Staff permission required')

def booking(request, pk):
    obj = Reservation.objects.select_related('guest', 'room__type', 'folio').filter(pk=pk).first()
    if not obj:
        raise ValidationError('Reservation not found')
    if request.portal in ('staff', 'admin') and request.user.is_authenticated and request.user.role in ('ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT'):
        return obj
    if request.session.get('guest_reservation') == obj.pk:
        return obj
    raise PermissionDenied('Verify booking access first')

def detail(obj):
    folio = obj.folio
    stay = Stay.objects.filter(reservation=obj).first()
    return {'id': obj.pk, 'reference': obj.reference, 'status': obj.status, 'arrival': obj.arrival,
            'departure': obj.departure, 'room': obj.room.number, 'room_type': obj.room.type.name,
            'guest_name': obj.guest.full_name, 'verified': obj.verified, 'currency': folio.currency,
            'hotel_today': services.hotel_today(obj.room.hotel), 'hotel_timezone': obj.room.hotel.timezone,
            'balance_minor': services.balance(folio), 'folio_version': folio.version, 'payment_provider': settings.PAYMENT_PROVIDER,
            'entries': list(folio.entries.values('category', 'description', 'amount_minor', 'service_date')),
            'stay_id': stay.pk if stay else None, 'checked_in_at': stay.checked_in_at if stay else None,
            'checked_out_at': stay.checked_out_at if stay else None,
            'requests': list(ServiceRequest.objects.filter(stay=stay).values('id', 'type', 'description', 'status')) if stay else []}

def ready(request):
    """Readiness probe for load balancers and uptime monitors: 200 only when the database answers."""
    try:
        User.objects.exists()
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ready'})

@api_view(['GET'])
def csrf(request):
    return Response({'csrfToken': get_token(request)})

@api_view(['POST'])
@throttle_classes([throttling.LoginThrottle])
def staff_login(request):
    if request.portal not in ('staff', 'admin'):
        raise PermissionDenied('Sign in through the staff or administrator portal')
    throttling.check_lockout(str(request.data.get('username', '')), request.portal)
    user = authenticate(request, username=request.data.get('username', ''), password=request.data.get('password', ''))
    if not user or not user.is_active:
        Audit.objects.create(actor=str(request.data.get('username', ''))[:120], action='LOGIN_FAILED', target=request.portal)
        raise ValidationError('Invalid credentials')
    if request.portal == 'admin' and user.role not in ADMIN_PORTAL_ROLES:
        raise PermissionDenied('Administrator account required')
    login(request, user)
    return Response({'username': user.username, 'role': user.role})

@api_view(['POST'])
def staff_logout(request):
    if request.portal not in ('staff', 'admin'):
        raise PermissionDenied('Use your staff or administrator session to sign out')
    logout(request)
    return Response({'ok': True})

@api_view(['GET'])
def me(request):
    if request.portal == 'guest':
        return Response({'guest_reservation': request.session.get('guest_reservation')})
    if not request.user.is_authenticated:
        return Response({})
    pending = legal.pending_staff_documents(request.user, request.query_params.get('lang', 'en') if request.query_params.get('lang') in legal.LANGUAGES else 'en')
    return Response({'username': request.user.username, 'role': request.user.role,
                     'pending_agreements': [{'id': d.pk, 'kind': d.kind, 'version': d.version, 'title': d.title} for d in pending]})

@api_view(['GET'])
def rooms(request):
    is_staff = request.user.is_authenticated and request.portal in ('staff', 'admin')
    if not is_staff:
        # Public catalog for guests: no internal operations, cleaning, or occupancy data exposed
        return Response([
            {
                'id': r.pk,
                'number': r.number,
                'type': r.type.name,
                'description': r.type.description,
                'amenities': r.type.amenities,
                'capacity': r.type.capacity,
                'rate_minor': r.type.nightly_rate_minor,
                'currency': r.hotel.currency,
            }
            for r in Room.objects.filter(in_service=True).select_related('type', 'hotel').order_by('number')
        ])

    is_housekeeping = request.user.role == 'HOUSEKEEPING'
    occupied_ids = set(Stay.objects.filter(checked_out_at__isnull=True).values_list('reservation__room_id', flat=True))

    result = []
    for r in Room.objects.select_related('type', 'hotel').all().order_by('number'):
        base = {
            'id': r.pk,
            'number': r.number,
            'type': r.type.name,
            'cleaning': r.cleaning,
            'in_service': r.in_service,
            'occupied': r.pk in occupied_ids,
        }
        if not is_housekeeping:
            base.update({
                'description': r.type.description,
                'amenities': r.type.amenities,
                'capacity': r.type.capacity,
                'rate_minor': r.type.nightly_rate_minor,
                'currency': r.hotel.currency,
            })
        result.append(base)
    return Response(result)

@api_view(['GET'])
def availability(request):
    try:
        arrival, departure = date.fromisoformat(request.query_params['arrival']), date.fromisoformat(request.query_params['departure'])
        occupants = int(request.query_params.get('occupants', '1'))
    except (KeyError, ValueError):
        raise ValidationError('Valid arrival, departure, and occupants required')
    if arrival >= departure or occupants < 1 or not Hotel.objects.exists() or arrival < services.hotel_today(Hotel.objects.first()):
        raise ValidationError('Invalid dates or occupancy')
    return Response([{'id': r.pk, 'number': r.number, 'type': r.type.name, 'rate_minor': r.type.nightly_rate_minor,
                      'currency': r.hotel.currency, 'capacity': r.type.capacity} for r in services.available(arrival, departure, occupants)])

def _require_bookings_open():
    from . import flags
    if flags.is_enabled('bookings_paused'):
        raise ValidationError('Online bookings are temporarily paused. Please try again later or contact the hotel.')

@api_view(['POST'])
@throttle_classes([throttling.BookingThrottle])
def quotes(request):
    _require_bookings_open()
    try:
        room = Room.objects.select_related('type', 'hotel').get(pk=request.data['room_id'])
        quote = services.create_quote(room, date.fromisoformat(request.data['arrival']), date.fromisoformat(request.data['departure']), int(request.data.get('occupants', 1)))
    except (Room.DoesNotExist, KeyError, ValueError) as exc:
        raise ValidationError(str(exc))
    return Response({'id': quote.pk, 'room_amount_minor': quote.room_amount_minor, 'tax_minor': quote.tax_minor,
                     'total_minor': quote.total, 'currency': quote.currency, 'expires_at': quote.expires_at})

@api_view(['POST'])
@throttle_classes([throttling.BookingThrottle])
def reservations(request):
    _require_bookings_open()
    try:
        docs = legal.validate_consent(request.data.get('consent_document_ids'), legal.BOOKING_KINDS)
    except ValueError as exc:
        raise ValidationError(str(exc))
    try:
        with transaction.atomic():
            quote = Quote.objects.select_related('room__type', 'room__hotel').get(pk=request.data['quote_id'])
            name, email = request.data['name'].strip(), request.data['email'].strip()
            if not name or not email or '@' not in email:
                raise ValueError('Name and email required')
            reservation = services.reserve(quote, name, email)
            legal.record_consent(docs, guest=reservation.guest, method='BOOKING',
                                 ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT'))
    except (KeyError, ValueError, Quote.DoesNotExist, IntegrityError) as exc:
        raise ValidationError('Quote expired, invalid, or room no longer available') from exc
    request.session['guest_reservation'] = reservation.pk
    request.session.set_expiry(3600)
    return Response({'id': reservation.pk, 'reference': reservation.reference, 'status': reservation.status,
                     'hold_expires_at': reservation.hold_expires_at}, status=201)

@api_view(['GET'])
def reservation(request, pk):
    return Response(detail(booking(request, pk)))

def _attempt_payload(attempt, include_qr=True):
    data = {'id': attempt.pk, 'provider': attempt.provider, 'status': attempt.status, 'amount_minor': attempt.amount_minor,
            'currency': attempt.currency, 'reservation_id': attempt.reservation_id, 'expires_at': attempt.expires_at,
            'simulated': attempt.provider == 'development', 'checkout_url': f'/checkout/{attempt.pk}'}
    if include_qr and attempt.provider == 'bakong' and attempt.status == 'PENDING':
        data['qr'] = attempt.provider_qr  # shown only while payable; never logged
    return data

@api_view(['POST'])
def payment_session(request, pk):
    obj = booking(request, pk)
    if obj.status not in ('HOLD', 'EXPIRED', 'CHECKED_IN', 'CONFIRMED'):
        raise ValidationError('Booking is not payable')
    amount = services.balance(obj.folio)
    if amount <= 0:
        raise ValidationError('Nothing outstanding')
    try:
        attempt = payment_service.create_session(obj, amount, obj.folio.currency)
    except payment_service.SessionError as exc:
        raise ValidationError(str(exc))
    return Response(_attempt_payload(attempt), status=201)

@api_view(['GET'])
@throttle_classes([throttling.PollThrottle])
def payment_session_status(request, pk):
    """Booking-scoped status. The browser never reports payment; the server asks the provider."""
    attempt = PaymentAttempt.objects.filter(pk=pk).first()
    if not attempt:
        raise NotFound('Payment session not found')
    booking(request, attempt.reservation_id)  # guest session or staff only
    if attempt.provider != 'development':
        attempt = payment_service.refresh_attempt(attempt.pk)
    return Response(_attempt_payload(attempt))

@api_view(['GET', 'POST'])
def development_checkout(request, pk):
    if settings.ENV != 'development' or __import__('os').getenv('PAYMENT_PROVIDER', 'development') != 'development':
        raise PermissionDenied()
    attempt = PaymentAttempt.objects.select_related('reservation__guest').get(pk=pk)
    if request.method == 'GET':
        return Response({'amount_minor': attempt.amount_minor, 'currency': attempt.currency, 'status': attempt.status, 'reservation_id': attempt.reservation_id, 'simulated': True})
    outcome = request.data.get('outcome')
    if outcome not in ('SUCCESS', 'FAILED', 'PENDING'):
        raise ValidationError('Invalid outcome')
    # This endpoint is a local provider emulator; it produces a provider event on the backend.
    # Never accept event IDs or amounts from a browser as evidence of settlement.
    event = services.process_event(pk, outcome, secrets.token_hex(20))
    return Response({'status': event.status, 'simulated': True})

@api_view(['POST'])
@throttle_classes([throttling.OtpThrottle])
def request_otp(request):
    reference = str(request.data.get('reference', '')).upper()
    email = str(request.data.get('email', '')).strip().lower()
    obj = Reservation.objects.filter(reference=reference, guest__email__iexact=email).first()
    if obj and obj.status in ('CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT'):
        recent = OTP.objects.filter(reservation=obj, issued_at__gt=timezone.now() - timedelta(minutes=1)).exists()
        if not recent:
            code = f'{secrets.randbelow(1000000):06d}'
            OTP.objects.create(reservation=obj, digest=services.otp_digest(code), expires_at=timezone.now() + timedelta(minutes=5))
            send_mail('Luma Haven verification code', f'Your verification code is {code}. It expires in 5 minutes.', 'noreply@localhost', [obj.guest.email])
    return Response({'message': 'If the details match, a verification message has been sent.'})

@api_view(['POST'])
@throttle_classes([throttling.OtpThrottle])
def verify_otp(request):
    obj = Reservation.objects.filter(reference=str(request.data.get('reference', '')).upper(), guest__email__iexact=str(request.data.get('email', '')).strip()).first()
    if not obj:
        raise ValidationError('Invalid or expired code')
    with transaction.atomic():
        otp = OTP.objects.select_for_update().filter(reservation=obj, consumed=False).order_by('-issued_at').first()
        if not otp or otp.expires_at <= timezone.now() or otp.attempts >= 5:
            raise ValidationError('Invalid or expired code')
        otp.attempts += 1
        correct = secrets.compare_digest(otp.digest, services.otp_digest(str(request.data.get('code', ''))))
        if correct:
            otp.consumed = True
            obj.verified = True
            obj.save(update_fields=['verified'])
            request.session['guest_reservation'] = obj.pk
            request.session.set_expiry(3600)
        otp.save(update_fields=['attempts', 'consumed'])
    if not correct:
        raise ValidationError('Invalid or expired code')
    return Response(detail(obj))

@api_view(['POST'])
def check_in(request, pk):
    obj = booking(request, pk)
    try:
        services.check_in(obj, request.user if request.user.is_authenticated else None)
    except ValueError as exc:
        raise ValidationError(str(exc))
    return Response(detail(obj.__class__.objects.get(pk=pk)))

@api_view(['POST'])
def check_out(request, pk):
    obj = booking(request, pk)
    try:
        services.check_out(obj, int(request.data['folio_version']))
    except (ValueError, KeyError, Stay.DoesNotExist) as exc:
        raise ValidationError(str(exc))
    return Response(detail(obj.__class__.objects.get(pk=pk)))

@api_view(['POST'])
def service_requests(request, pk):
    obj = booking(request, pk)
    stay = Stay.objects.filter(reservation=obj, checked_out_at__isnull=True).first()
    if not stay:
        raise ValidationError('Active stay required')
    kind = str(request.data.get('type', '')).strip()[:40]
    description = str(request.data.get('description', '')).strip()[:1000]
    if not kind or not description:
        raise ValidationError('Type and description required')
    item = ServiceRequest.objects.create(stay=stay, type=kind, description=description)
    return Response({'id': item.pk, 'status': item.status}, status=201)

@api_view(['GET'])
def dashboard(request):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING', 'ACCOUNTANT')
    occupied = Stay.objects.filter(checked_out_at__isnull=True).values('reservation__room_id')
    rooms = Room.objects.all()
    data = {'total_rooms': rooms.count(), 'occupied': occupied.count(),
            'vacant_ready': rooms.filter(cleaning='READY', in_service=True).exclude(id__in=occupied).count(),
            'vacant_dirty': rooms.filter(cleaning='DIRTY').exclude(id__in=occupied).count(),
            'out_of_service': rooms.filter(in_service=False).count(),
            'arrivals': Reservation.objects.filter(arrival=services.hotel_today(Hotel.objects.first()), status='CONFIRMED').count() if Hotel.objects.exists() else 0,
            'departures': Reservation.objects.filter(departure=services.hotel_today(Hotel.objects.first()), status='CHECKED_IN').count() if Hotel.objects.exists() else 0,
            'requests': ServiceRequest.objects.exclude(status='COMPLETED').count(),
            'housekeeping': HousekeepingTask.objects.exclude(status='READY').count()}
    if request.user.role != 'HOUSEKEEPING':
        data['outstanding_minor'] = sum(max(0, services.balance(f)) for f in Folio.objects.filter(closed=False))
    return Response(data)

@api_view(['GET'])
def staff_reservations(request):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT')
    return Response([detail(r) for r in Reservation.objects.select_related('guest', 'room__type', 'folio').order_by('-created_at')[:100]])

@api_view(['GET', 'POST'])
def admin_staff(request):
    staff(request, 'ADMIN')
    if request.method == 'POST':
        username = str(request.data.get('username', '')).strip()
        password = request.data.get('password', '')
        role = str(request.data.get('role', 'RECEPTION')).upper()
        if not username:
            raise ValidationError({'username': 'Username is required.'})
        if User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'A staff member with this username already exists.'})
        if len(password) < 8 or len(password) > 12:
            raise ValidationError({'password': 'Password must be between 8 and 12 characters.'})
        if role not in ROLES:
            raise ValidationError({'role': 'Invalid role.'})
        user = User.objects.create_user(username=username, password=password, role=role, is_staff=True)
        try:
            from . import staff_passwords
            staff_passwords.save_credential_to_file(username, password)
        except Exception:
            pass
        Audit.objects.create(actor=request.user.username, action='STAFF_ACCOUNT_CREATED', target=f'{username} ({role})')
        return Response({'id': user.pk, 'username': user.username, 'role': user.role, 'is_active': user.is_active}, status=201)
    return Response(list(User.objects.order_by('username').values('id', 'username', 'role', 'is_active', 'date_joined')))

@api_view(['PATCH', 'POST'])
def admin_update_staff(request, pk):
    staff(request, 'ADMIN')
    target_user = User.objects.filter(pk=pk).first()
    if not target_user:
        raise NotFound('Staff account not found')
    if 'is_active' in request.data:
        new_status = bool(request.data['is_active'])
        if target_user.pk == request.user.pk and not new_status:
            raise ValidationError({'is_active': 'Administrators cannot deactivate their own account.'})
        target_user.is_active = new_status
        Audit.objects.create(actor=request.user.username, action='STAFF_STATUS_UPDATED', target=f'{target_user.username}:{"active" if new_status else "inactive"}')
    if 'role' in request.data:
        new_role = str(request.data['role']).upper()
        if new_role not in ROLES:
            raise ValidationError({'role': 'Invalid role.'})
        if target_user.pk == request.user.pk and new_role != target_user.role:
            raise ValidationError({'role': 'Administrators cannot alter their own role.'})
        old_role = target_user.role
        target_user.role = new_role
        Audit.objects.create(actor=request.user.username, action='STAFF_ROLE_CHANGED', target=f'{target_user.username}:{old_role}->{new_role}')
    target_user.save()
    return Response({'id': target_user.pk, 'username': target_user.username, 'role': target_user.role, 'is_active': target_user.is_active})

@api_view(['POST'])
def admin_change_password(request, pk):
    staff(request, 'ADMIN')
    if request.portal != 'admin':
        raise PermissionDenied('Use the administrator portal to change staff passwords')
    password = request.data.get('new_password')
    if password != request.data.get('confirm_password'):
        raise ValidationError({'confirm_password': 'Passwords do not match.'})
    try:
        staff_passwords.change_password(request.user, pk, password)
    except User.DoesNotExist as exc:
        raise NotFound('Staff account not found') from exc
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response({'status': 'updated'})

@api_view(['GET'])
def admin_audit(request):
    staff(request, 'ADMIN')
    return Response(list(Audit.objects.order_by('-timestamp', '-pk').values('id', 'actor', 'action', 'target', 'timestamp')[:100]))

@api_view(['GET', 'POST', 'PUT'])
def admin_hotel(request):
    staff(request, 'ADMIN')
    hotel = Hotel.objects.first()
    if request.method in ('POST', 'PUT'):
        if not hotel:
            hotel = Hotel.objects.create(name='Luma Haven')
        name = str(request.data.get('name', hotel.name)).strip()[:120]
        email = str(request.data.get('email', hotel.email)).strip()
        phone = str(request.data.get('phone', hotel.phone)).strip()[:40]
        check_in_time = request.data.get('check_in_time', hotel.check_in_time)
        check_out_time = request.data.get('check_out_time', hotel.check_out_time)
        tax_percent = int(request.data.get('tax_percent', hotel.tax_percent))
        deposit_percent = int(request.data.get('deposit_percent', hotel.deposit_percent))
        if not (0 <= tax_percent <= 100):
            raise ValidationError({'tax_percent': 'Tax percent must be between 0 and 100.'})
        if not (0 <= deposit_percent <= 100):
            raise ValidationError({'deposit_percent': 'Deposit percent must be between 0 and 100.'})
        hotel.name = name
        hotel.email = email
        hotel.phone = phone
        hotel.check_in_time = check_in_time
        hotel.check_out_time = check_out_time
        hotel.tax_percent = tax_percent
        hotel.deposit_percent = deposit_percent
        hotel.save()
        Audit.objects.create(actor=request.user.username, action='HOTEL_SETTINGS_UPDATED', target=hotel.name)
        return Response({
            'id': hotel.id, 'name': hotel.name, 'email': hotel.email, 'phone': hotel.phone,
            'timezone': hotel.timezone, 'currency': hotel.currency,
            'check_in_time': str(hotel.check_in_time), 'check_out_time': str(hotel.check_out_time),
            'tax_percent': hotel.tax_percent, 'deposit_percent': hotel.deposit_percent
        })
    if hotel is None:
        raise ValidationError('Hotel settings have not been configured')
    return Response({
        'id': hotel.id, 'name': hotel.name, 'email': hotel.email, 'phone': hotel.phone,
        'timezone': hotel.timezone, 'currency': hotel.currency,
        'check_in_time': str(hotel.check_in_time), 'check_out_time': str(hotel.check_out_time),
        'tax_percent': hotel.tax_percent, 'deposit_percent': hotel.deposit_percent
    })

@api_view(['GET'])
def admin_health_diagnostics(request):
    staff(request, 'ADMIN')
    db_ok = True
    try:
        User.objects.count()
    except Exception:
        db_ok = False

    redis_ok = True
    try:
        from django.core.cache import cache
        cache.set('_diag_test', 1, 5)
        redis_ok = cache.get('_diag_test') == 1
    except Exception:
        redis_ok = False

    exceptions = list(PaymentException.objects.select_related('attempt__reservation').order_by('-created_at').values(
        'id', 'attempt_id', 'attempt__reservation__reference', 'reason', 'created_at'
    )[:20])

    failed_attempts = list(PaymentAttempt.objects.filter(status='FAILED').select_related('reservation').order_by('-created_at').values(
        'id', 'reservation__reference', 'amount_minor', 'currency', 'created_at'
    )[:20])

    pending_outbox = Outbox.objects.filter(delivered_at__isnull=True).count()

    return Response({
        'status': 'HEALTHY' if db_ok and redis_ok and len(exceptions) == 0 else 'WARNING',
        'services': {
            'database': {'status': 'ONLINE' if db_ok else 'OFFLINE'},
            'redis_cache': {'status': 'ONLINE' if redis_ok else 'DEGRADED'},
            'outbox_backlog_count': pending_outbox,
        },
        'unresolved_payment_exceptions': exceptions,
        'failed_payment_attempts': failed_attempts,
        'checked_at': timezone.now().isoformat(),
    })

@api_view(['GET'])
def tasks(request):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING')
    include_history = request.query_params.get('history') == 'true'
    qs = HousekeepingTask.objects.select_related('room', 'assignee')
    if include_history:
        qs = qs.filter(completed_at__isnull=False).order_by('-completed_at')[:50]
    else:
        if request.query_params.get('assignee') == 'me':
            qs = qs.filter(assignee=request.user)
        # Order by priority URGENT (1), HIGH (2), NORMAL (3)
        qs = qs.order_by(
            models.Case(
                models.When(priority='URGENT', then=models.Value(1)),
                models.When(priority='HIGH', then=models.Value(2)),
                default=models.Value(3),
                output_field=models.IntegerField(),
            ),
            '-created_at'
        )
    return Response([
        {
            'id': t.pk,
            'room__number': t.room.number,
            'status': t.status,
            'priority': getattr(t, 'priority', 'NORMAL'),
            'notes': t.notes,
            'assignee__username': t.assignee.username if t.assignee else None,
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'completed_at': t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in qs
    ])

@api_view(['POST'])
def transition_task(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING')
    with transaction.atomic():
        item = HousekeepingTask.objects.select_for_update().select_related('room').get(pk=pk)
        next_state = {'DIRTY': 'CLEANING', 'CLEANING': 'INSPECTION', 'INSPECTION': 'READY'}.get(item.status)
        if not next_state or request.data.get('status') != next_state:
            raise ValidationError('Invalid transition')
        if next_state == 'READY' and request.user.role == 'HOUSEKEEPING':
            raise PermissionDenied('Inspection requires reception or management')
        item.status = next_state
        item.room.cleaning = next_state
        if next_state == 'READY':
            item.completed_at = timezone.now()
        if 'notes' in request.data:
            item.notes = str(request.data.get('notes', ''))[:2000]
        if 'priority' in request.data and request.user.role in ('ADMIN', 'MANAGER', 'RECEPTION'):
            item.priority = str(request.data['priority']).upper()
        item.assignee = request.user
        item.room.save(update_fields=['cleaning'])
        item.save()
        Audit.objects.create(actor=request.user.username, action='HOUSEKEEPING_' + next_state, target=item.room.number)
    return Response({'status': item.status, 'priority': item.priority})

@api_view(['GET'])
def staff_requests(request):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    return Response(list(ServiceRequest.objects.values('id', 'stay__reservation__reference', 'type', 'description', 'status')))

@api_view(['POST'])
def finish_request(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    with transaction.atomic():
        item = ServiceRequest.objects.select_for_update().get(pk=pk)
        if item.status != 'COMPLETED':
            item.status = 'COMPLETED'
            item.completed_at = timezone.now()
            item.assignee = request.user
            item.save(update_fields=['status', 'completed_at', 'assignee'])
    return Response({'status': item.status})

@api_view(['POST'])
def cancel_reservation(request, pk):
    obj = booking(request, pk)
    with transaction.atomic():
        obj = Reservation.objects.select_for_update().get(pk=obj.pk)
        if obj.status == 'CANCELLED':
            return Response({'status': obj.status})
        if obj.status not in ('HOLD', 'CONFIRMED'):
            raise ValidationError('Cannot cancel this reservation')
        if Payment.objects.filter(attempt__reservation=obj).exists():
            raise ValidationError('Paid reservations require a reviewed refund; contact reception')
        Allocation.objects.filter(reservation=obj, active=True).update(active=False)
        obj.status = 'CANCELLED'
        obj.save(update_fields=['status'])
        Audit.objects.create(actor=request.user.username if request.user.is_authenticated else 'guest', action='CANCEL', target=obj.reference)
    return Response({'status': obj.status})

@api_view(['GET', 'POST'])
def maintenance(request):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING')
    if request.method == 'GET':
        return Response(list(MaintenanceTicket.objects.order_by('-created_at').values('id', 'room__number', 'description', 'priority', 'status', 'created_at')))
    try:
        room = Room.objects.get(pk=int(request.data['room_id']))
        today = services.hotel_today(room.hotel)
        start_str = request.data.get('arrival')
        end_str = request.data.get('departure')
        if start_str and end_str:
            start, end = date.fromisoformat(start_str), date.fromisoformat(end_str)
        else:
            start, end = today, today + timedelta(days=1)
        if start >= end:
            raise ValueError()
    except (KeyError, ValueError, Room.DoesNotExist):
        raise ValidationError('Valid room and dates required')
    description = str(request.data.get('description', '')).strip()[:2000]
    if not description:
        raise ValidationError('Description required')
    priority = str(request.data.get('priority', 'NORMAL')).upper()
    if priority not in ('NORMAL', 'HIGH', 'URGENT'):
        priority = 'NORMAL'
    from psycopg.types.range import Range
    try:
        with transaction.atomic():
            block = Allocation.objects.create(room=room, period=Range(start, end, '[)'), kind='MAINTENANCE')
            ticket = MaintenanceTicket.objects.create(room=room, description=description, priority=priority, allocation=block)
            if start <= services.hotel_today(room.hotel) < end:
                room.in_service = False
                room.save(update_fields=['in_service'])
            Audit.objects.create(actor=request.user.username, action='REPORT_MAINTENANCE', target=f'Room {room.number}:{priority}')
    except IntegrityError:
        raise ValidationError('Inventory conflict: resolve existing booking before blocking room')
    return Response({'id': ticket.pk, 'status': ticket.status, 'priority': ticket.priority}, status=201)

@api_view(['POST'])
def resolve_maintenance(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    with transaction.atomic():
        ticket = MaintenanceTicket.objects.select_for_update().select_related('room', 'allocation').get(pk=pk)
        if ticket.status == 'RESOLVED':
            return Response({'status': ticket.status})
        ticket.status = 'RESOLVED'
        now = timezone.now()
        ticket.resolved_at = now
        ticket.save(update_fields=['status', 'resolved_at'])
        if ticket.allocation:
            today = services.hotel_today(ticket.room.hotel)
            from psycopg.types.range import Range
            if today < ticket.allocation.period.upper:
                new_upper = max(ticket.allocation.period.lower, today)
                ticket.allocation.period = Range(ticket.allocation.period.lower, new_upper, '[)')
            ticket.allocation.active = False
            ticket.allocation.save(update_fields=['active', 'period'])
        ticket.room.in_service = True
        ticket.room.save(update_fields=['in_service'])
        Audit.objects.create(actor=request.user.username, action='MAINTENANCE_RESOLVED', target=ticket.room.number)
    return Response({'status': ticket.status})

def report_values(start, end):
    hotel = Hotel.objects.first()
    if not hotel:
        raise ValidationError('Hotel is not configured')
    if start >= end or (end - start).days > 366:
        raise ValidationError('Invalid period (maximum 366 days)')

    hotel_tz = ZoneInfo(hotel.timezone)
    today = services.hotel_today(hotel)
    days_count = (end - start).days

    from psycopg.types.range import Range
    maintenance_blocks = list(Allocation.objects.filter(kind='MAINTENANCE', period__overlap=Range(start, end, '[)')))
    total_rooms = Room.objects.count()

    sellable_room_nights = 0
    daily_blocked = {}
    for day_offset in range(days_count):
        d = start + timedelta(days=day_offset)
        blocked_room_ids = set()
        for block in maintenance_blocks:
            if block.period.lower <= d < block.period.upper:
                blocked_room_ids.add(block.room_id)
        daily_blocked[d] = len(blocked_room_ids)
        sellable_room_nights += max(0, total_rooms - len(blocked_room_ids))

    sold_room_nights = 0
    daily_sold = {start + timedelta(days=i): 0 for i in range(days_count)}

    stays = Stay.objects.select_related('reservation', 'reservation__room').filter(
        reservation__status__in=['CHECKED_IN', 'CHECKED_OUT']
    )

    valid_reservation_service_nights = set()
    for stay in stays:
        res = stay.reservation
        arr = res.arrival
        if res.status == 'CHECKED_OUT' and stay.checked_out_at:
            checkout_date = stay.checked_out_at.astimezone(hotel_tz).date()
            eff_dep = max(arr + timedelta(days=1), min(res.departure, checkout_date))
        else:
            eff_dep = res.departure

        curr = arr
        while curr < eff_dep:
            if start <= curr < end and curr <= today:
                valid_reservation_service_nights.add((res.id, curr))
                daily_sold[curr] = daily_sold.get(curr, 0) + 1
                sold_room_nights += 1
            curr += timedelta(days=1)

    room_entries = FolioEntry.objects.filter(
        category__in=['ROOM', 'ROOM_ADJUSTMENT'],
        service_date__gte=start,
        service_date__lt=end,
        service_date__lte=today,
        folio__reservation__status__in=['CHECKED_IN', 'CHECKED_OUT']
    ).select_related('folio__reservation')

    net_room_revenue = 0
    daily_revenue = {start + timedelta(days=i): 0 for i in range(days_count)}
    for entry in room_entries:
        if (entry.folio.reservation_id, entry.service_date) in valid_reservation_service_nights:
            net_room_revenue += entry.amount_minor
            if entry.service_date in daily_revenue:
                daily_revenue[entry.service_date] += entry.amount_minor

    beginning = timezone.make_aware(datetime.combine(start, time.min), hotel_tz)
    ending = timezone.make_aware(datetime.combine(end, time.min), hotel_tz)

    gross_cash = Payment.objects.filter(
        settled_at__gte=beginning, settled_at__lt=ending
    ).aggregate(v=Sum('amount_minor'))['v'] or 0

    refunded_cash = Refund.objects.filter(
        status='SETTLED', settled_at__gte=beginning, settled_at__lt=ending
    ).aggregate(v=Sum('amount_minor'))['v'] or 0

    net_cash = gross_cash - refunded_cash

    active_folios = Folio.objects.filter(
        closed=False, reservation__status__in=['CONFIRMED', 'CHECKED_IN']
    ).select_related('reservation')
    outstanding_balances = sum(max(0, services.balance(f)) for f in active_folios)

    cancellations = Reservation.objects.filter(
        status='CANCELLED',
        cancelled_at__gte=beginning,
        cancelled_at__lt=ending
    ).count()
    cancellations += Reservation.objects.filter(
        status='CANCELLED',
        cancelled_at__isnull=True,
        created_at__gte=beginning,
        created_at__lt=ending
    ).count()

    no_shows = Reservation.objects.filter(
        status='NO_SHOW',
        arrival__gte=start,
        arrival__lt=end
    ).count()

    total_cohort_bookings = Reservation.objects.filter(
        created_at__gte=beginning,
        created_at__lt=ending
    ).count()

    cancellation_rate = round(cancellations * 100 / total_cohort_bookings, 2) if total_cohort_bookings else None

    completed_tasks = HousekeepingTask.objects.filter(
        completed_at__gte=beginning,
        completed_at__lt=ending,
        stay__checked_out_at__isnull=False
    ).select_related('stay')

    turnaround_minutes_list = []
    for task in completed_tasks:
        if task.completed_at and task.stay.checked_out_at:
            delta = (task.completed_at - task.stay.checked_out_at).total_seconds() / 60
            if delta >= 0:
                turnaround_minutes_list.append(delta)

    avg_turnaround_minutes = round(sum(turnaround_minutes_list) / len(turnaround_minutes_list), 1) if turnaround_minutes_list else None

    occupancy_rate = round(sold_room_nights * 100 / sellable_room_nights, 2) if sellable_room_nights else None
    adr = round(net_room_revenue / sold_room_nights) if sold_room_nights else None
    revpar = round(net_room_revenue / sellable_room_nights) if sellable_room_nights else None

    return {
        'hotel': hotel.name,
        'timezone': hotel.timezone,
        'currency': hotel.currency,
        'start': str(start),
        'end_exclusive': str(end),
        'days': days_count,
        'generated_at': timezone.now().isoformat(),
        'total_rooms': total_rooms,
        'sellable_room_nights': sellable_room_nights,
        'sold_room_nights': sold_room_nights,
        'occupancy_rate_percent': occupancy_rate,
        'average_daily_rate_minor': adr,
        'revpar_minor': revpar,
        'net_room_revenue_minor': net_room_revenue,
        'settled_cash_minor': net_cash,
        'gross_cash_minor': gross_cash,
        'refunded_cash_minor': refunded_cash,
        'outstanding_balances_minor': outstanding_balances,
        'cancellations_count': cancellations,
        'no_shows_count': no_shows,
        'cancellation_rate_percent': cancellation_rate,
        'avg_housekeeping_turnaround_minutes': avg_turnaround_minutes,
        'daily_breakdown': [
            {
                'date': str(start + timedelta(days=i)),
                'sellable': max(0, total_rooms - daily_blocked.get(start + timedelta(days=i), 0)),
                'sold': daily_sold.get(start + timedelta(days=i), 0),
                'revenue_minor': daily_revenue.get(start + timedelta(days=i), 0),
            }
            for i in range(days_count)
        ]
    }

def sanitize_csv_cell(value):
    if value is None:
        return 'N/A'
    text = str(value)
    if text.startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + text
    return text

def build_csv_response(filename, headers, rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([sanitize_csv_cell(h) for h in headers])
    for row in rows:
        writer.writerow([sanitize_csv_cell(val) for val in row])
    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def get_room_type_performance(hotel, start, end):
    days_count = (end - start).days
    room_types = RoomType.objects.filter(hotel=hotel).order_by('name')
    from psycopg.types.range import Range

    maint_allocs = list(Allocation.objects.filter(
        kind='MAINTENANCE',
        room__hotel=hotel,
        period__overlap=Range(start, end, '[)')
    ).select_related('room'))

    stays = list(Stay.objects.filter(
        reservation__room__hotel=hotel,
        reservation__status__in=['CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT']
    ).select_related('reservation__room__type'))

    folio_entries = list(FolioEntry.objects.filter(
        category='ROOM',
        folio__reservation__room__hotel=hotel,
        service_date__gte=start,
        service_date__lt=end
    ).select_related('folio__reservation__room__type'))

    hotel_tz = ZoneInfo(hotel.timezone)
    result = []
    for rt in room_types:
        rooms_of_type = Room.objects.filter(type=rt)
        total_rooms = rooms_of_type.count()
        total_type_nights = total_rooms * days_count

        type_maint = [m for m in maint_allocs if m.room.type_id == rt.id]
        blocked = 0
        for i in range(days_count):
            d = start + timedelta(days=i)
            blocked += sum(1 for m in type_maint if m.period.lower <= d < m.period.upper)

        sellable = max(0, total_type_nights - blocked)

        sold = 0
        for i in range(days_count):
            d = start + timedelta(days=i)
            for stay in stays:
                if stay.reservation.room.type_id == rt.id:
                    check_in_d = timezone.localtime(stay.checked_in_at, hotel_tz).date() if stay.checked_in_at else stay.reservation.arrival
                    dep_d = timezone.localtime(stay.checked_out_at, hotel_tz).date() if stay.checked_out_at else stay.reservation.departure
                    if check_in_d <= d < dep_d:
                        sold += 1

        revenue = sum(e.amount_minor for e in folio_entries if e.folio.reservation.room.type_id == rt.id)
        occ = round(sold * 100 / sellable, 1) if sellable else None
        adr = round(revenue / sold) if sold else None

        result.append({
            'id': rt.id,
            'name': rt.name,
            'capacity': rt.capacity,
            'total_rooms': total_rooms,
            'nightly_rate_minor': rt.nightly_rate_minor,
            'sellable_room_nights': sellable,
            'sold_room_nights': sold,
            'occupancy_rate_percent': occ,
            'net_room_revenue_minor': revenue,
            'adr_minor': adr,
        })
    return result

@api_view(['GET'])
def manager_dashboard(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    hotel = Hotel.objects.first()
    if not hotel:
        raise ValidationError('Hotel not configured')
    today = services.hotel_today(hotel)
    try:
        start = date.fromisoformat(request.query_params.get('start', str(today)))
        end = date.fromisoformat(request.query_params.get('end', str(today + timedelta(days=1))))
    except (ValueError, TypeError):
        raise ValidationError('Valid start and end dates required (YYYY-MM-DD)')
    if start >= end:
        raise ValidationError('Start date must be before end date')

    kpis = report_values(start, end)
    room_types = get_room_type_performance(hotel, start, end)
    alerts = evaluate_decision_support_alerts(hotel, start, end)

    all_rooms = Room.objects.all()
    readiness = {
        'total': all_rooms.count(),
        'ready': all_rooms.filter(cleaning='READY', in_service=True).count(),
        'cleaning': all_rooms.filter(cleaning='CLEANING', in_service=True).count(),
        'inspection': all_rooms.filter(cleaning='INSPECTION', in_service=True).count(),
        'dirty': all_rooms.filter(cleaning='DIRTY', in_service=True).count(),
        'out_of_service': all_rooms.filter(in_service=False).count(),
    }

    today_arrivals_qs = Reservation.objects.filter(arrival=today)
    today_departures_qs = Reservation.objects.filter(departure=today)

    arrivals = {
        'total': today_arrivals_qs.exclude(status='CANCELLED').count(),
        'checked_in': today_arrivals_qs.filter(status='CHECKED_IN').count(),
        'pending': today_arrivals_qs.filter(status='CONFIRMED').count(),
    }
    departures = {
        'total': today_departures_qs.exclude(status='CANCELLED').count(),
        'checked_out': today_departures_qs.filter(status='CHECKED_OUT').count(),
        'pending': today_departures_qs.filter(status='CHECKED_IN').count(),
    }

    arriving_room_ids = today_arrivals_qs.filter(status='CONFIRMED').values_list('room_id', flat=True)
    unready_arrivals = list(Room.objects.filter(
        id__in=arriving_room_ids
    ).exclude(cleaning='READY', in_service=True).values('id', 'number', 'cleaning', 'in_service', 'type__name'))

    open_tickets = list(MaintenanceTicket.objects.filter(status='OPEN').values(
        'id', 'room__number', 'description', 'priority', 'status', 'created_at'
    ).order_by('-priority', '-created_at')[:10])

    open_requests = list(ServiceRequest.objects.exclude(status='COMPLETED').values(
        'id', 'stay__reservation__reference', 'stay__reservation__room__number', 'type', 'description', 'status', 'submitted_at'
    ).order_by('-submitted_at')[:10])

    pending_refunds = list(Refund.objects.filter(status='PENDING').values(
        'id', 'payment__attempt__reservation__reference', 'amount_minor', 'reason', 'status', 'requested_by__username', 'created_at'
    ).order_by('-created_at')[:10])

    return Response({
        'kpis': kpis,
        'trends': kpis.get('daily_breakdown', []),
        'room_types': room_types,
        'readiness': readiness,
        'operations': {
            'arrivals': arrivals,
            'departures': departures,
            'unready_arrivals_today': unready_arrivals,
            'open_maintenance': open_tickets,
            'open_requests': open_requests,
            'pending_refunds': pending_refunds,
            'payment_exceptions_count': PaymentException.objects.count(),
        },
        'alerts': alerts,
        'metadata': {
            'hotel': hotel.name,
            'timezone': hotel.timezone,
            'currency': hotel.currency,
            'start': str(start),
            'end': str(end),
            'generated_at': timezone.now().isoformat(),
        }
    })

@api_view(['POST'])
def staff_amend_reservation(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    res = Reservation.objects.filter(pk=pk).first()
    if not res:
        raise NotFound('Reservation not found')
    try:
        new_arrival = date.fromisoformat(request.data['arrival'])
        new_departure = date.fromisoformat(request.data['departure'])
        new_occupants = int(request.data.get('occupants', res.occupants))
    except (KeyError, ValueError, TypeError) as exc:
        raise ValidationError('Valid arrival, departure, and occupants required') from exc

    try:
        updated = services.amend_reservation(res, new_arrival, new_departure, new_occupants, actor_username=request.user.username)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response(detail(updated))

@api_view(['POST'])
def staff_reassign_room(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    res = Reservation.objects.filter(pk=pk).first()
    if not res:
        raise NotFound('Reservation not found')
    try:
        target_room = Room.objects.get(pk=int(request.data['room_id']))
    except (KeyError, ValueError, Room.DoesNotExist) as exc:
        raise ValidationError('Valid target room_id required') from exc

    try:
        updated = services.reassign_room(res, target_room, actor_username=request.user.username)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response(detail(updated))

@api_view(['POST'])
def staff_no_show(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    res = Reservation.objects.filter(pk=pk).first()
    if not res:
        raise NotFound('Reservation not found')
    try:
        updated = services.mark_no_show(res, actor_username=request.user.username)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response(detail(updated))

@api_view(['GET'])
def staff_refunds(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    status_filter = request.query_params.get('status')
    qs = Refund.objects.select_related(
        'payment__attempt__reservation__guest', 'requested_by', 'reviewed_by'
    ).order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter.upper())
    return Response([
        {
            'id': r.pk,
            'payment_id': r.payment_id,
            'reservation_reference': r.payment.attempt.reservation.reference,
            'guest_name': r.payment.attempt.reservation.guest.full_name,
            'amount_minor': r.amount_minor,
            'reason': r.reason,
            'status': r.status,
            'requested_by': r.requested_by.username if r.requested_by else None,
            'reviewed_by': r.reviewed_by.username if r.reviewed_by else None,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'settled_at': r.settled_at.isoformat() if r.settled_at else None,
        }
        for r in qs[:100]
    ])

@api_view(['POST'])
def staff_request_refund(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT')
    res = Reservation.objects.filter(pk=pk).first()
    if not res:
        raise NotFound('Reservation not found')
    payment = Payment.objects.filter(attempt__reservation=res).order_by('-settled_at').first()
    if not payment:
        raise ValidationError('No settled payment found for this reservation.')
    try:
        amount_minor = int(request.data['amount_minor'])
        reason = str(request.data.get('reason', '')).strip()[:200]
    except (KeyError, ValueError) as exc:
        raise ValidationError('Valid amount_minor and reason required') from exc
    if not reason:
        raise ValidationError('Refund reason is required.')

    try:
        refund = services.request_refund(payment, amount_minor, reason, request.user)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response({'id': refund.pk, 'status': refund.status, 'amount_minor': refund.amount_minor})

@api_view(['POST'])
def staff_approve_refund(request, pk):
    staff(request, 'ADMIN', 'MANAGER')
    refund = Refund.objects.filter(pk=pk).first()
    if not refund:
        raise NotFound('Refund not found')
    try:
        services.approve_refund(refund, request.user)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response({'id': refund.pk, 'status': refund.status})

@api_view(['POST'])
def staff_settle_refund(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    refund = Refund.objects.filter(pk=pk).first()
    if not refund:
        raise NotFound('Refund not found')
    if refund.status != 'APPROVED' and request.user.role == 'ACCOUNTANT':
        raise ValidationError('Only manager-approved refunds can be settled by an accountant.')
    if refund.requested_by_id == request.user.id and request.user.role != 'ADMIN':
        raise PermissionDenied('Segregation of duties: You cannot settle your own refund request.')
    try:
        services.settle_refund(refund, request.user)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response({'id': refund.pk, 'status': refund.status})

@api_view(['POST'])
def staff_reject_refund(request, pk):
    staff(request, 'ADMIN', 'MANAGER')
    refund = Refund.objects.filter(pk=pk).first()
    if not refund:
        raise NotFound('Refund not found')
    reason = str(request.data.get('reason', '')).strip()[:200]
    try:
        services.reject_refund(refund, request.user, rejection_reason=reason)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response({'id': refund.pk, 'status': refund.status})

@api_view(['GET'])
def accountant_payments(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    status_filter = request.query_params.get('status', 'all').lower()
    attempts = PaymentAttempt.objects.select_related('reservation__guest').order_by('-created_at')
    if status_filter != 'all':
        attempts = attempts.filter(status=status_filter.upper())

    attempts_list = list(attempts[:100])
    payments_by_attempt = {p.attempt_id: p for p in Payment.objects.filter(attempt__in=attempts_list)}
    exceptions_by_attempt = {e.attempt_id: e for e in PaymentException.objects.filter(attempt__in=attempts_list)}
    settled_refunds_by_payment = {}
    for r in Refund.objects.filter(status='SETTLED', payment__in=payments_by_attempt.values()):
        settled_refunds_by_payment.setdefault(r.payment_id, 0)
        settled_refunds_by_payment[r.payment_id] += r.amount_minor

    records = []
    for a in attempts_list:
        p = payments_by_attempt.get(a.id)
        e = exceptions_by_attempt.get(a.id)
        refunded_minor = settled_refunds_by_payment.get(p.id, 0) if p else 0
        records.append({
            'attempt_id': str(a.id),
            'reservation_reference': a.reservation.reference,
            'guest_name': a.reservation.guest.full_name,
            'amount_minor': a.amount_minor,
            'currency': a.currency,
            'status': a.status,
            'settled_at': p.settled_at.isoformat() if p else None,
            'refunded_minor': refunded_minor,
            'net_collected_minor': (p.amount_minor - refunded_minor) if p else 0,
            'exception_reason': e.reason if e else None,
            'created_at': a.created_at.isoformat(),
        })
    return Response(records)

@api_view(['GET'])
def accountant_reconciliation(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    reservations = Reservation.objects.select_related('guest', 'room', 'folio').order_by('-created_at')[:100]
    rows = []
    for r in reservations:
        folio = r.folio
        folio_charges = folio.entries.filter(amount_minor__gt=0).aggregate(s=Sum('amount_minor'))['s'] or 0
        folio_credits = abs(folio.entries.filter(amount_minor__lt=0).aggregate(s=Sum('amount_minor'))['s'] or 0)
        settled_payments = Payment.objects.filter(attempt__reservation=r).aggregate(s=Sum('amount_minor'))['s'] or 0
        settled_refunds = Refund.objects.filter(payment__attempt__reservation=r, status='SETTLED').aggregate(s=Sum('amount_minor'))['s'] or 0
        net_cash = settled_payments - settled_refunds
        current_balance = services.balance(folio)
        is_balanced = (current_balance == 0) and (r.status in ('CHECKED_OUT', 'CANCELLED', 'NO_SHOW') or net_cash >= folio_charges)
        rows.append({
            'reservation_id': r.pk,
            'reference': r.reference,
            'guest_name': r.guest.full_name,
            'room_number': r.room.number,
            'status': r.status,
            'folio_charges_minor': folio_charges,
            'folio_credits_minor': folio_credits,
            'net_cash_minor': net_cash,
            'balance_minor': current_balance,
            'is_balanced': is_balanced,
            'folio_closed': folio.closed,
            'folio_version': folio.version,
        })
    return Response(rows)

@api_view(['POST'])
def accountant_reconcile_folio(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    res = Reservation.objects.select_related('folio').filter(pk=pk).first()
    if not res:
        raise NotFound('Reservation not found')
    Audit.objects.create(actor=request.user.username, action='FOLIO_RECONCILED', target=f'{res.reference}:v{res.folio.version}')
    return Response({'ok': True, 'reference': res.reference, 'reconciled_by': request.user.username})

@api_view(['GET'])
def reception_diagnostics(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    res = Reservation.objects.select_related('guest', 'room', 'folio').filter(pk=pk).first()
    if not res:
        raise NotFound('Reservation not found')
    today = services.hotel_today(res.room.hotel)
    room = res.room
    stay = Stay.objects.filter(reservation=res).first()

    check_in_issues = []
    if res.status != 'CONFIRMED':
        check_in_issues.append(f'Status is {res.status}; only CONFIRMED bookings can check in.')
    if not res.verified:
        check_in_issues.append('Guest has not verified identity/email with OTP.')
    if today < res.arrival:
        check_in_issues.append(f'Scheduled arrival date is {res.arrival} (hotel date is {today}).')
    if today >= res.departure:
        check_in_issues.append(f'Scheduled departure date {res.departure} has already passed.')
    if room.cleaning != 'READY':
        check_in_issues.append(f'Room {room.number} is currently {room.cleaning} (must be READY).')
    if not room.in_service:
        check_in_issues.append(f'Room {room.number} is out of service.')
    bal = services.balance(res.folio)
    if bal > 0:
        check_in_issues.append(f'Outstanding balance of ${bal / 100:.2f} must be settled.')
    if Stay.objects.filter(reservation__room=room, checked_out_at__isnull=True).exclude(reservation=res).exists():
        check_in_issues.append(f'Room {room.number} is currently occupied by another guest.')

    check_out_issues = []
    if not stay or stay.checked_out_at:
        check_out_issues.append('Reservation has no active stay to check out.')
    if bal > 0:
        check_out_issues.append(f'Outstanding balance of ${bal / 100:.2f} must be paid.')

    return Response({
        'reservation_id': res.pk,
        'reference': res.reference,
        'guest_name': res.guest.full_name,
        'room_number': room.number,
        'can_check_in': len(check_in_issues) == 0 and not stay,
        'check_in_issues': check_in_issues,
        'can_check_out': len(check_out_issues) == 0 and bool(stay and not stay.checked_out_at),
        'check_out_issues': check_out_issues,
        'current_balance_minor': bal,
    })

@api_view(['POST'])
def staff_assign_task(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    task = HousekeepingTask.objects.select_related('room').filter(pk=pk).first()
    if not task:
        raise NotFound('Task not found')
    username = request.data.get('username')
    assignee = None
    if username:
        assignee = User.objects.filter(username=username).first()
        if not assignee:
            raise ValidationError(f'User {username} not found')
    services.assign_housekeeping_task(task, assignee, actor_username=request.user.username)
    return Response({'id': task.pk, 'assignee': assignee.username if assignee else None})

@api_view(['GET'])
def staff_rates(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    return Response([
        {
            'id': rt.pk,
            'name': rt.name,
            'description': rt.description,
            'capacity': rt.capacity,
            'nightly_rate_minor': rt.nightly_rate_minor,
            'total_rooms': rt.room_set.count(),
        }
        for rt in RoomType.objects.all().order_by('name')
    ])

@api_view(['POST'])
def staff_update_rate(request, pk):
    staff(request, 'ADMIN', 'MANAGER')
    room_type = RoomType.objects.filter(pk=pk).first()
    if not room_type:
        raise NotFound('Room type not found')
    try:
        new_rate = int(request.data['nightly_rate_minor'])
    except (KeyError, ValueError) as exc:
        raise ValidationError('Valid nightly_rate_minor required') from exc
    try:
        services.update_room_rate(room_type, new_rate, actor_username=request.user.username)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return Response({'id': room_type.pk, 'nightly_rate_minor': room_type.nightly_rate_minor})

@api_view(['GET'])
def report_daily_summary(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    hotel = Hotel.objects.first()
    today = services.hotel_today(hotel) if hotel else date.today()
    try:
        target_date = date.fromisoformat(request.query_params.get('date', str(today)))
    except ValueError:
        raise ValidationError('Invalid date (YYYY-MM-DD)')
    next_date = target_date + timedelta(days=1)
    values = report_values(target_date, next_date)
    if request.query_params.get('export') == 'csv':
        rows = [[k, v] for k, v in values.items() if not isinstance(v, list)]
        return build_csv_response(f'daily-summary-{target_date}.csv', ['Metric', 'Value'], rows)
    return Response(values)

@api_view(['GET'])
def report_revenue_occupancy(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    hotel = Hotel.objects.first()
    today = services.hotel_today(hotel) if hotel else date.today()
    try:
        start = date.fromisoformat(request.query_params.get('start', str(today - timedelta(days=6))))
        end = date.fromisoformat(request.query_params.get('end', str(today + timedelta(days=1))))
    except ValueError:
        raise ValidationError('Valid start and end dates required')
    if start >= end:
        raise ValidationError('Start date must be before end date')

    types_perf = get_room_type_performance(hotel, start, end)
    if request.query_params.get('export') == 'csv':
        headers = ['Room Type', 'Total Rooms', 'Sellable Nights', 'Sold Nights', 'Occupancy %', 'Net Revenue (Minor)', 'ADR (Minor)']
        rows = [
            [
                item['name'],
                item['total_rooms'],
                item['sellable_room_nights'],
                item['sold_room_nights'],
                item['occupancy_rate_percent'],
                item['net_room_revenue_minor'],
                item['adr_minor'],
            ]
            for item in types_perf
        ]
        return build_csv_response(f'revenue-occupancy-{start}-to-{end}.csv', headers, rows)
    return Response({'start': str(start), 'end': str(end), 'room_types': types_perf})

@api_view(['GET'])
def report_cash_reconciliation(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    hotel = Hotel.objects.first()
    today = services.hotel_today(hotel) if hotel else date.today()
    try:
        start = date.fromisoformat(request.query_params.get('start', str(today - timedelta(days=6))))
        end = date.fromisoformat(request.query_params.get('end', str(today + timedelta(days=1))))
    except ValueError:
        raise ValidationError('Valid start and end dates required')
    if start >= end:
        raise ValidationError('Start date must be before end date')

    hotel_tz = ZoneInfo(hotel.timezone) if hotel else ZoneInfo('UTC')
    beginning = timezone.make_aware(datetime.combine(start, time.min), hotel_tz)
    ending = timezone.make_aware(datetime.combine(end, time.min), hotel_tz)

    payments = list(Payment.objects.filter(
        settled_at__gte=beginning, settled_at__lt=ending
    ).select_related('attempt__reservation').order_by('settled_at'))

    refunds = list(Refund.objects.filter(
        status='SETTLED', settled_at__gte=beginning, settled_at__lt=ending
    ).select_related('payment__attempt__reservation', 'reviewed_by').order_by('settled_at'))

    gross_cash = sum(p.amount_minor for p in payments)
    refunded_cash = sum(r.amount_minor for r in refunds)
    net_cash = gross_cash - refunded_cash

    channel_mix = {}
    for p in payments:
        row = channel_mix.setdefault(p.attempt.provider, {'count': 0, 'amount_minor': 0})
        row['count'] += 1
        row['amount_minor'] += p.amount_minor
    attempts = PaymentAttempt.objects.filter(created_at__gte=beginning, created_at__lt=ending)
    attempt_funnel = {}
    for provider_name, status_name in attempts.values_list('provider', 'status'):
        row = attempt_funnel.setdefault(provider_name, {'created': 0, 'SUCCESS': 0, 'EXPIRED': 0, 'FAILED': 0, 'EXCEPTION': 0, 'PENDING': 0})
        row['created'] += 1
        row[status_name] = row.get(status_name, 0) + 1
    for row in attempt_funnel.values():
        row['abandon_rate_percent'] = round((row['EXPIRED'] + row['FAILED']) * 100 / row['created'], 1) if row['created'] else 0
    payment_exceptions = list(PaymentException.objects.filter(created_at__gte=beginning, created_at__lt=ending).values(
        'id', 'attempt__reservation__reference', 'reason', 'created_at'))

    if request.query_params.get('export') == 'csv':
        headers = ['Type', 'Record ID', 'Reservation Ref', 'Amount Minor', 'Reason / Channel', 'Settled At']
        rows = []
        for p in payments:
            rows.append(['PAYMENT', p.id, p.attempt.reservation.reference, p.amount_minor, f'Channel: {p.attempt.provider}', p.settled_at.isoformat()])
        for r in refunds:
            rows.append(['REFUND', r.id, r.payment.attempt.reservation.reference, -r.amount_minor, r.reason, r.settled_at.isoformat()])
        rows.append(['TOTAL_GROSS', '', '', gross_cash, '', ''])
        rows.append(['TOTAL_REFUNDED', '', '', -refunded_cash, '', ''])
        rows.append(['NET_CASH', '', '', net_cash, '', ''])
        return build_csv_response(f'cash-reconciliation-{start}-to-{end}.csv', headers, rows)

    return Response({
        'start': str(start),
        'end': str(end),
        'gross_cash_minor': gross_cash,
        'refunded_cash_minor': refunded_cash,
        'net_cash_minor': net_cash,
        'payments_count': len(payments),
        'refunds_count': len(refunds),
        'channel_mix': channel_mix,
        'attempt_funnel': attempt_funnel,
        'payment_exceptions': payment_exceptions,
        'payments': [
            {'id': p.id, 'reference': p.attempt.reservation.reference, 'amount_minor': p.amount_minor, 'channel': p.attempt.provider, 'settled_at': p.settled_at.isoformat()}
            for p in payments
        ],
        'refunds': [
            {'id': r.id, 'reference': r.payment.attempt.reservation.reference, 'amount_minor': r.amount_minor, 'reason': r.reason, 'settled_at': r.settled_at.isoformat()}
            for r in refunds
        ],
    })

@api_view(['GET'])
def report_housekeeping_turnaround(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    hotel = Hotel.objects.first()
    today = services.hotel_today(hotel) if hotel else date.today()
    try:
        start = date.fromisoformat(request.query_params.get('start', str(today - timedelta(days=6))))
        end = date.fromisoformat(request.query_params.get('end', str(today + timedelta(days=1))))
    except ValueError:
        raise ValidationError('Valid start and end dates required')
    if start >= end:
        raise ValidationError('Start date must be before end date')

    hotel_tz = ZoneInfo(hotel.timezone) if hotel else ZoneInfo('UTC')
    beginning = timezone.make_aware(datetime.combine(start, time.min), hotel_tz)
    ending = timezone.make_aware(datetime.combine(end, time.min), hotel_tz)

    completed_tasks = list(HousekeepingTask.objects.filter(
        completed_at__gte=beginning,
        completed_at__lt=ending,
        stay__checked_out_at__isnull=False
    ).select_related('stay', 'room', 'assignee'))

    task_rows = []
    durations = []
    for t in completed_tasks:
        delta = (t.completed_at - t.stay.checked_out_at).total_seconds() / 60
        if delta >= 0:
            durations.append(delta)
            task_rows.append({
                'task_id': t.pk,
                'room_number': t.room.number,
                'assignee': t.assignee.username if t.assignee else 'Unassigned',
                'checked_out_at': t.stay.checked_out_at.isoformat(),
                'completed_at': t.completed_at.isoformat(),
                'turnaround_minutes': round(delta, 1),
            })

    avg_minutes = round(sum(durations) / len(durations), 1) if durations else None

    if request.query_params.get('export') == 'csv':
        headers = ['Task ID', 'Room Number', 'Assignee', 'Checked Out At', 'Cleaned At', 'Turnaround (Minutes)']
        rows = [[r['task_id'], r['room_number'], r['assignee'], r['checked_out_at'], r['completed_at'], r['turnaround_minutes']] for r in task_rows]
        rows.append(['AVERAGE', '', '', '', '', avg_minutes or 'N/A'])
        return build_csv_response(f'housekeeping-turnaround-{start}-to-{end}.csv', headers, rows)

    return Response({
        'start': str(start),
        'end': str(end),
        'tasks_count': len(task_rows),
        'avg_turnaround_minutes': avg_minutes,
        'tasks': task_rows,
    })

@api_view(['GET'])
def report_accounts_receivable(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    hotel = Hotel.objects.first()
    today = services.hotel_today(hotel) if hotel else date.today()

    active_folios = Folio.objects.filter(
        closed=False,
        reservation__status__in=['CONFIRMED', 'CHECKED_IN']
    ).select_related('reservation__guest', 'reservation__room')

    records = []
    buckets = {'current_0_7': 0, 'overdue_8_14': 0, 'overdue_15_30': 0, 'overdue_30_plus': 0}

    for f in active_folios:
        b = services.balance(f)
        if b > 0:
            res = f.reservation
            days_since_arrival = max(0, (today - res.arrival).days)
            if days_since_arrival <= 7:
                bucket_key = 'current_0_7'
            elif days_since_arrival <= 14:
                bucket_key = 'overdue_8_14'
            elif days_since_arrival <= 30:
                bucket_key = 'overdue_15_30'
            else:
                bucket_key = 'overdue_30_plus'

            buckets[bucket_key] += b
            records.append({
                'reservation_reference': res.reference,
                'guest_name': res.guest.full_name,
                'room_number': res.room.number,
                'arrival': str(res.arrival),
                'departure': str(res.departure),
                'status': res.status,
                'balance_minor': b,
                'aging_bucket': bucket_key,
                'days_active': days_since_arrival,
            })

    total_outstanding = sum(r['balance_minor'] for r in records)

    if request.query_params.get('export') == 'csv':
        headers = ['Reservation Ref', 'Guest Name', 'Room', 'Arrival', 'Departure', 'Status', 'Aging Bucket', 'Days', 'Balance Minor']
        rows = [
            [r['reservation_reference'], r['guest_name'], r['room_number'], r['arrival'], r['departure'], r['status'], r['aging_bucket'], r['days_active'], r['balance_minor']]
            for r in records
        ]
        rows.append(['TOTAL OUTSTANDING', '', '', '', '', '', '', '', total_outstanding])
        return build_csv_response(f'accounts-receivable-{today}.csv', headers, rows)

    return Response({
        'hotel_today': str(today),
        'total_outstanding_minor': total_outstanding,
        'buckets': buckets,
        'records_count': len(records),
        'records': records,
    })

@api_view(['GET'])
def report(request):
    staff(request, 'ADMIN', 'MANAGER', 'ACCOUNTANT')
    try:
        today = services.hotel_today(Hotel.objects.first())
        start = date.fromisoformat(request.query_params.get('start', str(today)))
        end = date.fromisoformat(request.query_params.get('end', str(today + timedelta(days=1))))
    except (ValueError, AttributeError):
        raise ValidationError('Invalid period')
    values = report_values(start, end)
    if request.query_params.get('export') == 'csv':
        rows = [[k, v] for k, v in values.items() if not isinstance(v, list)]
        return build_csv_response('hotel-report.csv', ['metric', 'value'], rows)
    return Response(values)


def serialize_visual_asset(asset):
    return {
        'id': asset.id,
        'title': asset.title,
        'caption': asset.caption,
        'alt_text': asset.alt_text,
        'category': asset.category,
        'room_type_id': asset.room_type_id,
        'room_type_name': asset.room_type.name if asset.room_type else None,
        'image_url': asset.image.url if asset.image else '',
        'source_type': asset.source_type,
        'facility_claim': asset.facility_claim,
        'display_order': asset.display_order,
        'is_active': asset.is_active,
        'width': asset.width,
        'height': asset.height,
        'file_size_bytes': asset.file_size_bytes,
        'original_filename': asset.original_filename,
        'updated_at': asset.updated_at.isoformat() if asset.updated_at else None,
    }


@api_view(['GET'])
def visual_assets(request):
    category = request.query_params.get('category')
    room_type_id = request.query_params.get('room_type_id')

    qs = VisualAsset.objects.filter(is_active=True).select_related('room_type')
    if category:
        qs = qs.filter(category=category.upper())
    if room_type_id:
        qs = qs.filter(room_type_id=room_type_id)

    assets = list(qs.order_by('category', 'display_order', '-created_at'))
    serialized = [serialize_visual_asset(a) for a in assets]

    hero_asset = next((a for a in serialized if a['category'] == 'HERO'), None)
    logo_asset = next((a for a in serialized if a['category'] == 'BRANDING'), None)
    gallery_assets = [a for a in serialized if a['category'] == 'GALLERY']
    features_assets = [a for a in serialized if a['category'] == 'EXPERIENCE']

    room_types_map = {}
    for a in serialized:
        if a['category'] == 'ROOM_TYPE' and a['room_type_id']:
            room_types_map.setdefault(a['room_type_id'], []).append(a)

    return Response({
        'items': serialized,
        'hero': hero_asset,
        'logo': logo_asset,
        'gallery': gallery_assets,
        'features': features_assets,
        'room_types': room_types_map,
    })


@api_view(['GET', 'POST'])
def staff_visual_assets(request):
    staff(request, 'ADMIN', 'MANAGER')

    if request.method == 'GET':
        category = request.query_params.get('category')
        qs = VisualAsset.objects.all().select_related('room_type')
        if category:
            qs = qs.filter(category=category.upper())
        assets = [serialize_visual_asset(a) for a in qs.order_by('category', 'display_order', '-created_at')]
        return Response(assets)

    elif request.method == 'POST':
        image_file = request.FILES.get('image')
        if not image_file:
            raise ValidationError('An image file is required.')

        if image_file.size > 10 * 1024 * 1024:
            raise ValidationError('Image file size cannot exceed 10 MB.')

        try:
            with Image.open(image_file) as img:
                width, height = img.size
                img.verify()
        except Exception:
            raise ValidationError('Invalid or corrupted image file.')

        image_file.seek(0)
        hasher = hashlib.sha256()
        for chunk in image_file.chunks():
            hasher.update(chunk)
        content_hash = hasher.hexdigest()

        hotel = Hotel.objects.first()
        category = request.data.get('category', 'OTHER').upper()
        room_type_id = request.data.get('room_type_id')
        room_type = RoomType.objects.filter(pk=room_type_id).first() if room_type_id else None

        asset = VisualAsset.objects.create(
            hotel=hotel,
            category=category,
            room_type=room_type,
            image=image_file,
            title=request.data.get('title', image_file.name),
            caption=request.data.get('caption', ''),
            alt_text=request.data.get('alt_text', f"Luma Haven {category}"),
            display_order=int(request.data.get('display_order', 1)),
            is_active=str(request.data.get('is_active', 'true')).lower() in ('true', '1'),
            source_type=request.data.get('source_type', 'CONCEPT'),
            facility_claim=request.data.get('facility_claim', ''),
            original_filename=image_file.name,
            content_hash=content_hash,
            file_size_bytes=image_file.size,
            width=width,
            height=height,
        )
        return Response(serialize_visual_asset(asset), status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
def staff_visual_asset_detail(request, pk):
    staff(request, 'ADMIN', 'MANAGER')
    asset = VisualAsset.objects.select_related('room_type').filter(pk=pk).first()
    if not asset:
        raise NotFound('Visual asset not found.')

    if request.method == 'GET':
        return Response(serialize_visual_asset(asset))

    elif request.method == 'PATCH':
        if 'title' in request.data:
            asset.title = request.data['title']
        if 'caption' in request.data:
            asset.caption = request.data['caption']
        if 'alt_text' in request.data:
            asset.alt_text = request.data['alt_text']
        if 'category' in request.data:
            asset.category = request.data['category'].upper()
        if 'display_order' in request.data:
            try:
                asset.display_order = int(request.data['display_order'])
            except (ValueError, TypeError):
                pass
        if 'is_active' in request.data:
            asset.is_active = str(request.data['is_active']).lower() in ('true', '1')
        if 'source_type' in request.data:
            asset.source_type = request.data['source_type']
        if 'facility_claim' in request.data:
            asset.facility_claim = request.data['facility_claim']
        if 'room_type_id' in request.data:
            rt_id = request.data['room_type_id']
            asset.room_type = RoomType.objects.filter(pk=rt_id).first() if rt_id else None

        replacement_image = request.FILES.get('image')
        if replacement_image:
            if replacement_image.size > 10 * 1024 * 1024:
                raise ValidationError('Image file size cannot exceed 10 MB.')
            try:
                with Image.open(replacement_image) as img:
                    width, height = img.size
                    img.verify()
            except Exception:
                raise ValidationError('Invalid or corrupted image file.')
            replacement_image.seek(0)
            hasher = hashlib.sha256()
            for chunk in replacement_image.chunks():
                hasher.update(chunk)
            asset.content_hash = hasher.hexdigest()
            asset.width = width
            asset.height = height
            asset.file_size_bytes = replacement_image.size
            asset.original_filename = replacement_image.name
            asset.image = replacement_image

        asset.save()
        return Response(serialize_visual_asset(asset))

    elif request.method == 'DELETE':
        asset.delete()
        return Response({'deleted': True, 'id': pk})



# ---- Legal documents, consent and data-subject rights (P1) ----

def _lang(request):
    lang = request.query_params.get('lang', 'en')
    return lang if lang in legal.LANGUAGES else 'en'

def _legal_public(doc, body=False):
    data = {'id': doc.pk, 'kind': doc.kind, 'language': doc.language, 'version': doc.version,
            'title': doc.title, 'effective_at': doc.effective_at}
    if body:
        data['body_markdown'] = doc.body_markdown
    return data

@api_view(['GET'])
def legal_documents(request):
    docs = legal.current_documents(_lang(request))
    return Response([_legal_public(d) for d in docs.values()])

@api_view(['GET'])
def legal_document(request, kind):
    doc = legal.current_documents(_lang(request), [kind.upper()]).get(kind.upper())
    if not doc:
        raise NotFound('Document not found')
    return Response(_legal_public(doc, body=True))

@api_view(['POST'])
def accept_agreement(request):
    """Staff acceptance of the current acceptable-use agreement."""
    if request.portal not in ('staff', 'admin') or not request.user.is_authenticated:
        raise PermissionDenied('Staff permission required')
    try:
        docs = legal.validate_consent(request.data.get('consent_document_ids'), ('STAFF_AGREEMENT',))
    except ValueError as exc:
        raise ValidationError(str(exc))
    docs = [d for d in docs if d.kind == 'STAFF_AGREEMENT']
    legal.record_consent(docs, user=request.user, method='STAFF_LOGIN',
                         ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT'))
    return Response({'accepted': [d.pk for d in docs]}, status=201)

def _verified_guest_booking(request, pk):
    obj = booking(request, pk)
    if request.portal == 'guest' and not obj.verified:
        raise PermissionDenied('Verify your booking with the emailed code first')
    return obj

@api_view(['POST'])
@throttle_classes([throttling.PrivacyThrottle])
def guest_data_request(request, pk):
    obj = _verified_guest_booking(request, pk)
    type_ = str(request.data.get('type', '')).upper()
    if type_ not in ('ACCESS', 'EXPORT', 'RECTIFY', 'DELETE'):
        raise ValidationError('Unknown request type')
    req = legal.open_request(obj.guest, type_, str(request.data.get('note', '')))
    return Response({'id': req.pk, 'type': req.type, 'status': req.status, 'due_at': req.due_at}, status=201)

@api_view(['GET'])
def guest_data_export(request, pk):
    obj = _verified_guest_booking(request, pk)
    Audit.objects.create(actor=f'guest:{obj.guest.pk}', action='DATA_EXPORTED', target=f'guest:{obj.guest.pk}')
    return Response(legal.export_guest_data(obj.guest))

def _request_row(r):
    return {'id': r.pk, 'type': r.type, 'status': r.status, 'guest_id': r.guest_id, 'guest_name': r.guest.full_name,
            'guest_email': r.guest.email, 'note': r.note, 'resolution': r.resolution, 'requested_at': r.requested_at,
            'due_at': r.due_at, 'overdue': r.status == 'OPEN' and r.due_at < timezone.now(),
            'handled_by': r.handled_by, 'handled_at': r.handled_at}

@api_view(['GET'])
def admin_data_requests(request):
    staff(request, 'ADMIN')
    qs = DataSubjectRequest.objects.select_related('guest').order_by('status', 'due_at')[:200]
    return Response([_request_row(r) for r in qs])

@api_view(['POST'])
def admin_resolve_data_request(request, pk):
    staff(request, 'ADMIN')
    req = DataSubjectRequest.objects.select_related('guest').filter(pk=pk).first()
    if not req:
        raise NotFound('Request not found')
    try:
        req = legal.resolve_request(req, str(request.data.get('decision', '')), request.user.username, str(request.data.get('resolution', '')))
    except ValueError as exc:
        raise ValidationError(str(exc))
    return Response(_request_row(req))

@api_view(['GET', 'POST'])
def admin_legal(request):
    staff(request, 'ADMIN')
    if request.method == 'POST':
        kind, lang = str(request.data.get('kind', '')).upper(), request.data.get('language')
        title, body = str(request.data.get('title', '')).strip(), str(request.data.get('body_markdown', '')).strip()
        if kind not in dict(LegalDocument._meta.get_field('kind').choices) or lang not in legal.LANGUAGES or not title or not body:
            raise ValidationError('kind, language, title and body_markdown are required')
        doc = legal.new_draft(kind, lang, title, body, request.user.username)
        Audit.objects.create(actor=request.user.username, action='LEGAL_DRAFT_CREATED', target=f'{kind}/{lang}/v{doc.version}')
        return Response(dict(_legal_public(doc, body=True), status=doc.status), status=201)
    rows = LegalDocument.objects.order_by('kind', 'language', '-version')
    consents = dict(ConsentRecord.objects.values_list('document_id').annotate(n=models.Count('pk')))
    return Response([dict(_legal_public(d), status=d.status, created_by=d.created_by, consent_count=consents.get(d.pk, 0)) for d in rows])

@api_view(['GET', 'PATCH'])
def admin_legal_detail(request, pk):
    staff(request, 'ADMIN')
    doc = LegalDocument.objects.filter(pk=pk).first()
    if not doc:
        raise NotFound('Document not found')
    if request.method == 'PATCH':
        if doc.status != 'DRAFT':
            raise ValidationError('Published documents are immutable; create a new version')
        doc.title = str(request.data.get('title', doc.title)).strip() or doc.title
        doc.body_markdown = str(request.data.get('body_markdown', doc.body_markdown))
        doc.save()
    return Response(dict(_legal_public(doc, body=True), status=doc.status))

@api_view(['POST'])
def admin_legal_publish(request, pk):
    staff(request, 'ADMIN')
    doc = LegalDocument.objects.filter(pk=pk).first()
    if not doc:
        raise NotFound('Document not found')
    try:
        doc = legal.publish(doc, request.user.username)
    except ValueError as exc:
        raise ValidationError(str(exc))
    return Response(dict(_legal_public(doc, body=True), status=doc.status))

urlpatterns = [
    path('legal/documents', legal_documents), path('legal/documents/<str:kind>', legal_document),
    path('auth/accept-agreement', accept_agreement),
    path('reservations/<int:pk>/data-requests', guest_data_request), path('reservations/<int:pk>/data-export', guest_data_export),
    path('admin/data-requests', admin_data_requests), path('admin/data-requests/<int:pk>/resolve', admin_resolve_data_request),
    path('admin/legal', admin_legal), path('admin/legal/<int:pk>', admin_legal_detail), path('admin/legal/<int:pk>/publish', admin_legal_publish),
    path('health', lambda r: JsonResponse({'status': 'ok'})), path('ready', ready),
    path('auth/csrf', csrf), path('auth/login', staff_login), path('auth/logout', staff_logout), path('auth/me', me),
    path('rooms', rooms), path('availability', availability), path('quotes', quotes),
    path('visual-assets', visual_assets),
    path('staff/visual-assets', staff_visual_assets),
    path('staff/visual-assets/<int:pk>', staff_visual_asset_detail),
    path('admin/visual-assets', staff_visual_assets),
    path('admin/visual-assets/<int:pk>', staff_visual_asset_detail),
    path('reservations', reservations), path('reservations/<int:pk>', reservation),
    path('reservations/<int:pk>/payment-sessions', payment_session),
    path('payment-sessions/<uuid:pk>', payment_session_status),
    path('development/checkout/<uuid:pk>', development_checkout),
    path('guest-access/request-otp', request_otp), path('guest-access/verify-otp', verify_otp),
    path('reservations/<int:pk>/check-in', check_in), path('reservations/<int:pk>/check-out', check_out),
    path('reservations/<int:pk>/service-requests', service_requests),
    path('dashboard/summary', dashboard), path('staff/reservations', staff_reservations),
    path('admin/staff', admin_staff), path('admin/staff/<int:pk>', admin_update_staff),
    path('admin/staff/<int:pk>/password', admin_change_password),
    path('admin/audit', admin_audit), path('admin/hotel', admin_hotel),
    path('admin/health-diagnostics', admin_health_diagnostics),
    path('housekeeping/tasks', tasks), path('housekeeping/tasks/<int:pk>/transition', transition_task),
    path('housekeeping/tasks/<int:pk>/assign', staff_assign_task),
    path('staff/service-requests', staff_requests), path('staff/service-requests/<int:pk>/complete', finish_request),
    path('reservations/<int:pk>/cancel', cancel_reservation),
    path('staff/reservations/<int:pk>/amend', staff_amend_reservation),
    path('staff/reservations/<int:pk>/reassign', staff_reassign_room),
    path('staff/reservations/<int:pk>/no-show', staff_no_show),
    path('staff/reservations/<int:pk>/diagnostics', reception_diagnostics),
    path('staff/reservations/<int:pk>/request-refund', staff_request_refund),
    path('staff/refunds', staff_refunds),
    path('staff/refunds/<int:pk>/approve', staff_approve_refund),
    path('staff/refunds/<int:pk>/settle', staff_settle_refund),
    path('staff/refunds/<int:pk>/reject', staff_reject_refund),
    path('accountant/payments', accountant_payments),
    path('accountant/reconciliation', accountant_reconciliation),
    path('accountant/folios/<int:pk>/reconcile', accountant_reconcile_folio),
    path('staff/rates', staff_rates),
    path('staff/rates/<int:pk>', staff_update_rate),
    path('maintenance/tickets', maintenance), path('maintenance/tickets/<int:pk>/resolve', resolve_maintenance),
    path('reports/summary', report), path('staff/reports/summary', report), path('admin/reports/summary', report),
    path('manager/dashboard', manager_dashboard), path('staff/manager/dashboard', manager_dashboard), path('admin/manager/dashboard', manager_dashboard),
    path('reports/daily-summary', report_daily_summary), path('admin/reports/daily-summary', report_daily_summary), path('staff/reports/daily-summary', report_daily_summary),
    path('reports/revenue-occupancy', report_revenue_occupancy), path('admin/reports/revenue-occupancy', report_revenue_occupancy), path('staff/reports/revenue-occupancy', report_revenue_occupancy),
    path('reports/cash-reconciliation', report_cash_reconciliation), path('admin/reports/cash-reconciliation', report_cash_reconciliation), path('staff/reports/cash-reconciliation', report_cash_reconciliation),
    path('reports/housekeeping-turnaround', report_housekeeping_turnaround), path('admin/reports/housekeeping-turnaround', report_housekeeping_turnaround), path('staff/reports/housekeeping-turnaround', report_housekeeping_turnaround),
    path('reports/accounts-receivable', report_accounts_receivable), path('admin/reports/accounts-receivable', report_accounts_receivable), path('staff/reports/accounts-receivable', report_accounts_receivable),
]

# Admin CMS and Developer Console endpoints live in views_console.py (imported last: it uses staff() above).
from .views_console import urlpatterns as _console_urlpatterns  # noqa: E402
urlpatterns += _console_urlpatterns

