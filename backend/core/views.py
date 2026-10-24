import secrets
import csv
from datetime import date, timedelta
from io import StringIO
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from . import services
from .models import (Allocation, Audit, Folio, FolioEntry, Hotel, HousekeepingTask,
                     OTP, Payment, PaymentAttempt, Quote, Reservation, Room, ServiceRequest, Stay, MaintenanceTicket)

def staff(request, *roles):
    if not request.user.is_authenticated or request.user.role not in roles:
        raise PermissionDenied('Staff permission required')

def booking(request, pk):
    obj = Reservation.objects.select_related('guest', 'room__type', 'folio').filter(pk=pk).first()
    if not obj:
        raise ValidationError('Reservation not found')
    if request.user.is_authenticated and request.user.role in ('ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT'):
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
            'balance_minor': services.balance(folio), 'folio_version': folio.version,
            'entries': list(folio.entries.values('category', 'description', 'amount_minor', 'service_date')),
            'stay_id': stay.pk if stay else None, 'checked_in_at': stay.checked_in_at if stay else None,
            'checked_out_at': stay.checked_out_at if stay else None,
            'requests': list(ServiceRequest.objects.filter(stay=stay).values('id', 'type', 'description', 'status')) if stay else []}

@api_view(['GET'])
def csrf(request):
    return Response({'csrfToken': get_token(request)})

@api_view(['POST'])
def staff_login(request):
    user = authenticate(request, username=request.data.get('username', ''), password=request.data.get('password', ''))
    if not user or not user.is_active:
        raise ValidationError('Invalid credentials')
    login(request, user)
    return Response({'username': user.username, 'role': user.role})

@api_view(['POST'])
def staff_logout(request):
    logout(request)
    return Response({'ok': True})

@api_view(['GET'])
def me(request):
    return Response({'username': request.user.username, 'role': request.user.role} if request.user.is_authenticated else {'guest_reservation': request.session.get('guest_reservation')})

@api_view(['GET'])
def rooms(request):
    staff_housekeeping = request.user.is_authenticated and request.user.role == 'HOUSEKEEPING'
    return Response([{'id': r.pk, 'number': r.number, 'type': r.type.name, 'description': r.type.description,
                      'amenities': r.type.amenities, 'capacity': r.type.capacity, 'rate_minor': r.type.nightly_rate_minor,
                      'currency': r.hotel.currency, 'cleaning': r.cleaning, 'in_service': r.in_service,
                      'occupied': Stay.objects.filter(reservation__room=r, checked_out_at__isnull=True).exists()}
                     if not staff_housekeeping else {'id': r.pk, 'number': r.number, 'type': r.type.name,
                      'cleaning': r.cleaning, 'in_service': r.in_service,
                      'occupied': Stay.objects.filter(reservation__room=r, checked_out_at__isnull=True).exists()}
                     for r in Room.objects.select_related('type', 'hotel').all().order_by('number')])

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

@api_view(['POST'])
def quotes(request):
    try:
        room = Room.objects.select_related('type', 'hotel').get(pk=request.data['room_id'])
        quote = services.create_quote(room, date.fromisoformat(request.data['arrival']), date.fromisoformat(request.data['departure']), int(request.data.get('occupants', 1)))
    except (Room.DoesNotExist, KeyError, ValueError) as exc:
        raise ValidationError(str(exc))
    return Response({'id': quote.pk, 'room_amount_minor': quote.room_amount_minor, 'tax_minor': quote.tax_minor,
                     'total_minor': quote.total, 'currency': quote.currency, 'expires_at': quote.expires_at})

@api_view(['POST'])
def reservations(request):
    try:
        quote = Quote.objects.select_related('room__type', 'room__hotel').get(pk=request.data['quote_id'])
        name, email = request.data['name'].strip(), request.data['email'].strip()
        if not name or not email or '@' not in email:
            raise ValueError('Name and email required')
        reservation = services.reserve(quote, name, email)
    except (KeyError, ValueError, Quote.DoesNotExist, IntegrityError) as exc:
        raise ValidationError('Quote expired, invalid, or room no longer available') from exc
    request.session['guest_reservation'] = reservation.pk
    request.session.set_expiry(3600)
    return Response({'id': reservation.pk, 'reference': reservation.reference, 'status': reservation.status,
                     'hold_expires_at': reservation.hold_expires_at}, status=201)

@api_view(['GET'])
def reservation(request, pk):
    return Response(detail(booking(request, pk)))

@api_view(['POST'])
def payment_session(request, pk):
    obj = booking(request, pk)
    if obj.status not in ('HOLD', 'EXPIRED', 'CHECKED_IN', 'CONFIRMED'):
        raise ValidationError('Booking is not payable')
    amount = services.balance(obj.folio)
    if amount <= 0:
        raise ValidationError('Nothing outstanding')
    attempt = PaymentAttempt.objects.create(reservation=obj, amount_minor=amount, currency=obj.folio.currency)
    return Response({'id': attempt.pk, 'amount_minor': amount, 'currency': attempt.currency,
                     'checkout_url': f'/checkout/{attempt.pk}', 'simulated': True}, status=201)

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

@api_view(['GET'])
def tasks(request):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING')
    return Response(list(HousekeepingTask.objects.values('id', 'room__number', 'status', 'notes', 'assignee__username')))

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
        item.notes = str(request.data.get('notes', ''))[:2000]
        item.assignee = request.user
        item.room.save(update_fields=['cleaning'])
        item.save()
        Audit.objects.create(actor=request.user.username, action='HOUSEKEEPING_' + next_state, target=item.room.number)
    return Response({'status': item.status})

@api_view(['GET'])
def staff_requests(request):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    return Response(list(ServiceRequest.objects.values('id', 'stay__reservation__reference', 'type', 'description', 'status')))

@api_view(['POST'])
def finish_request(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    item = ServiceRequest.objects.get(pk=pk)
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
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    if request.method == 'GET':
        return Response(list(MaintenanceTicket.objects.values('id', 'room__number', 'description', 'priority', 'status')))
    try:
        room = Room.objects.get(pk=int(request.data['room_id']))
        start, end = date.fromisoformat(request.data['arrival']), date.fromisoformat(request.data['departure'])
        if start >= end:
            raise ValueError()
    except (KeyError, ValueError, Room.DoesNotExist):
        raise ValidationError('Valid room and dates required')
    description = str(request.data.get('description', '')).strip()[:2000]
    if not description:
        raise ValidationError('Description required')
    from psycopg.types.range import Range
    try:
        with transaction.atomic():
            block = Allocation.objects.create(room=room, period=Range(start, end, '[)'), kind='MAINTENANCE')
            ticket = MaintenanceTicket.objects.create(room=room, description=description, allocation=block)
            if start <= services.hotel_today(room.hotel) < end:
                room.in_service = False
                room.save(update_fields=['in_service'])
    except IntegrityError:
        raise ValidationError('Inventory conflict: resolve existing booking before blocking room')
    return Response({'id': ticket.pk, 'status': ticket.status}, status=201)

@api_view(['POST'])
def resolve_maintenance(request, pk):
    staff(request, 'ADMIN', 'MANAGER', 'RECEPTION')
    with transaction.atomic():
        ticket = MaintenanceTicket.objects.select_for_update().select_related('room', 'allocation').get(pk=pk)
        if ticket.status == 'RESOLVED':
            return Response({'status': ticket.status})
        ticket.status = 'RESOLVED'
        ticket.save(update_fields=['status'])
        if ticket.allocation:
            ticket.allocation.active = False
            ticket.allocation.save(update_fields=['active'])
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
    # Service-date recognition; exclude taxes and unoccupied maintenance inventory.
    room_revenue = FolioEntry.objects.filter(category__in=['ROOM', 'ROOM_ADJUSTMENT'], service_date__gte=start, service_date__lt=end,
        service_date__lte=services.hotel_today(hotel), folio__reservation__status__in=['CHECKED_IN', 'CHECKED_OUT']).aggregate(v=Sum('amount_minor'))['v'] or 0
    sold = FolioEntry.objects.filter(category='ROOM', service_date__gte=start, service_date__lt=end,
        service_date__lte=services.hotel_today(hotel), folio__reservation__status__in=['CHECKED_IN', 'CHECKED_OUT']).count()
    days = (end - start).days
    blocked = 0
    for block in Allocation.objects.filter(kind='MAINTENANCE', active=True):
        blocked += max(0, (min(end, block.period.upper) - max(start, block.period.lower)).days)
    sellable = max(0, Room.objects.count() * days - blocked)
    beginning = timezone.make_aware(__import__('datetime').datetime.combine(start, __import__('datetime').time.min), ZoneInfo(hotel.timezone))
    ending = timezone.make_aware(__import__('datetime').datetime.combine(end, __import__('datetime').time.min), ZoneInfo(hotel.timezone))
    cash = Payment.objects.filter(settled_at__gte=beginning, settled_at__lt=ending).aggregate(v=Sum('amount_minor'))['v'] or 0
    return {'hotel': hotel.name, 'timezone': hotel.timezone, 'currency': hotel.currency, 'start': start, 'end_exclusive': end,
            'generated_at': timezone.now(), 'sold_room_nights': sold, 'sellable_room_nights': sellable,
            'occupancy_rate_percent': round(sold * 100 / sellable, 2) if sellable else None,
            'average_daily_rate_minor': round(room_revenue / sold) if sold else None,
            'revpar_minor': round(room_revenue / sellable) if sellable else None,
            'net_room_revenue_minor': room_revenue, 'settled_cash_minor': cash}

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
    if request.query_params.get('format') == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['metric', 'value'])
        for key, value in values.items():
            text = str(value if value is not None else 'N/A')
            if text.startswith(('=', '+', '-', '@', '\t', '\r')):
                text = "'" + text
            writer.writerow([key, text])
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="hotel-report.csv"'
        return response
    return Response(values)

urlpatterns = [
    path('health', lambda r: JsonResponse({'status': 'ok'})),
    path('auth/csrf', csrf), path('auth/login', staff_login), path('auth/logout', staff_logout), path('auth/me', me),
    path('rooms', rooms), path('availability', availability), path('quotes', quotes),
    path('reservations', reservations), path('reservations/<int:pk>', reservation),
    path('reservations/<int:pk>/payment-sessions', payment_session),
    path('development/checkout/<uuid:pk>', development_checkout),
    path('guest-access/request-otp', request_otp), path('guest-access/verify-otp', verify_otp),
    path('reservations/<int:pk>/check-in', check_in), path('reservations/<int:pk>/check-out', check_out),
    path('reservations/<int:pk>/service-requests', service_requests),
    path('dashboard/summary', dashboard), path('staff/reservations', staff_reservations),
    path('housekeeping/tasks', tasks), path('housekeeping/tasks/<int:pk>/transition', transition_task),
    path('staff/service-requests', staff_requests), path('staff/service-requests/<int:pk>/complete', finish_request),
    path('reservations/<int:pk>/cancel', cancel_reservation),
    path('maintenance/tickets', maintenance), path('maintenance/tickets/<int:pk>/resolve', resolve_maintenance),
    path('reports/summary', report),
]
