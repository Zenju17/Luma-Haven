from django.contrib import admin
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from . import services
from .models import (
    Allocation, Audit, Folio, FolioEntry, Guest, Hotel, HousekeepingTask,
    MaintenanceTicket, OTP, Outbox, Payment, PaymentAttempt, PaymentEvent,
    PaymentException, Quote, Refund, Reservation, Room, RoomType, ServiceRequest, Stay, User
)


class LumaAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError("This account is inactive.", code="inactive")
        if not (
            user.is_staff
            or user.is_superuser
            or getattr(user, 'role', None) in ('ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT')
        ):
            raise ValidationError(
                "Please enter the credentials for an authorized staff or administrator account.",
                code="invalid_login",
            )


class LumaAdminSite(admin.AdminSite):
    site_header = "Luma Haven Hotel Management"
    site_title = "Luma Haven Admin"
    index_title = "Operations & Administration"
    index_template = "admin/index.html"
    login_form = LumaAdminAuthenticationForm

    def has_permission(self, request):
        return bool(
            request.user
            and request.user.is_active
            and (
                request.user.is_staff
                or request.user.is_superuser
                or getattr(request.user, 'role', None) in ('ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT')
            )
        )

    def index(self, request, extra_context=None):
        hotel = Hotel.objects.first()
        today = services.hotel_today(hotel) if hotel else timezone.now().date()

        total_rooms = Room.objects.count()
        occupied_rooms = Stay.objects.filter(checked_out_at__isnull=True).count()
        available_rooms = (
            Room.objects.filter(in_service=True, cleaning='READY')
            .exclude(allocation__active=True, allocation__period__contains=today)
            .distinct()
            .count()
        )
        today_arrivals = Reservation.objects.filter(arrival=today, status__in=['CONFIRMED', 'HOLD']).count()
        today_departures = Reservation.objects.filter(departure=today, status__in=['CHECKED_IN', 'CONFIRMED']).count()
        active_reservations = Reservation.objects.filter(status__in=['HOLD', 'CONFIRMED', 'CHECKED_IN']).count()
        pending_payments = PaymentAttempt.objects.filter(status='PENDING').count()
        settled_revenue_minor = Payment.objects.aggregate(total=Sum('amount_minor'))['total'] or 0
        settled_revenue = f"${settled_revenue_minor / 100:,.2f}"

        # Housekeeping metrics
        dirty_count = Room.objects.filter(cleaning='DIRTY').count()
        cleaning_count = Room.objects.filter(cleaning='CLEANING').count()
        inspection_count = Room.objects.filter(cleaning='INSPECTION').count()
        ready_count = Room.objects.filter(cleaning='READY').count()
        out_of_service_count = Room.objects.filter(in_service=False).count()

        # Recent activities
        recent_audits = Audit.objects.order_by('-timestamp')[:6]
        recent_reservations = Reservation.objects.select_related('guest', 'room', 'room__type').order_by('-created_at')[:6]

        context = {
            **(extra_context or {}),
            'hotel_name': hotel.name if hotel else 'Luma Haven',
            'hotel_timezone': hotel.timezone if hotel else 'Asia/Phnom_Penh',
            'business_date': today,
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'available_rooms': available_rooms,
            'today_arrivals': today_arrivals,
            'today_departures': today_departures,
            'active_reservations': active_reservations,
            'pending_payments': pending_payments,
            'settled_revenue': settled_revenue,
            'hk_ready': ready_count,
            'hk_dirty': dirty_count,
            'hk_cleaning': cleaning_count,
            'hk_inspection': inspection_count,
            'hk_out_of_service': out_of_service_count,
            'recent_audits': recent_audits,
            'recent_reservations': recent_reservations,
        }
        return super().index(request, extra_context=context)


luma_admin_site = LumaAdminSite(name='luma_admin')


# ─────────────────────────────────────────────
# Helper formatters
# ─────────────────────────────────────────────

def format_status_badge(status: str) -> str:
    color_map = {
        'READY': 'badge-success',
        'CONFIRMED': 'badge-success',
        'COMPLETED': 'badge-success',
        'SUCCESS': 'badge-success',
        'CHECKED_IN': 'badge-primary',
        'CLEANING': 'badge-warning',
        'INSPECTION': 'badge-warning',
        'PENDING': 'badge-warning',
        'SUBMITTED': 'badge-warning',
        'OPEN': 'badge-warning',
        'DIRTY': 'badge-danger',
        'FAILED': 'badge-danger',
        'EXPIRED': 'badge-muted',
        'HOLD': 'badge-info',
        'CHECKED_OUT': 'badge-muted',
    }
    css_class = color_map.get(status, 'badge-muted')
    label = status.replace('_', ' ')
    return format_html('<span class="status-pill {}">{}</span>', css_class, label)


# ─────────────────────────────────────────────
# Base ModelAdmin with Role-Based Permissions
# ─────────────────────────────────────────────

class LumaBaseAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return bool(
            request.user
            and request.user.is_active
            and (
                request.user.is_staff
                or request.user.is_superuser
                or getattr(request.user, 'role', None) in ('ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT')
            )
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        if not request.user or not request.user.is_active:
            return False
        role = getattr(request.user, 'role', None)
        return bool(request.user.is_superuser or role in ('ADMIN', 'MANAGER', 'RECEPTION'))

    def has_add_permission(self, request):
        if not request.user or not request.user.is_active:
            return False
        role = getattr(request.user, 'role', None)
        return bool(request.user.is_superuser or role in ('ADMIN', 'MANAGER', 'RECEPTION'))

    def has_delete_permission(self, request, obj=None):
        if not request.user or not request.user.is_active:
            return False
        return bool(request.user.is_superuser or getattr(request.user, 'role', None) == 'ADMIN')


class HotelAdmin(LumaBaseAdmin):
    list_display = ('name', 'timezone', 'currency', 'check_in_time', 'check_out_time', 'tax_percent', 'deposit_percent')


class RoomTypeAdmin(LumaBaseAdmin):
    list_display = ('name', 'capacity', 'rate_display', 'amenities_display')
    search_fields = ('name',)

    @admin.display(description='Nightly rate')
    def rate_display(self, obj):
        return f"${obj.nightly_rate_minor / 100:.2f}"

    @admin.display(description='Amenities')
    def amenities_display(self, obj):
        return ", ".join(obj.amenities) if obj.amenities else "—"


class RoomAdmin(LumaBaseAdmin):
    list_display = ('number', 'type', 'cleaning_badge', 'in_service_badge', 'capacity_display', 'rate_display')
    list_filter = ('cleaning', 'in_service', 'type')
    search_fields = ('number', 'type__name')
    ordering = ('number',)

    @admin.display(description='Cleaning Status')
    def cleaning_badge(self, obj):
        return format_status_badge(obj.cleaning)

    @admin.display(description='Service')
    def in_service_badge(self, obj):
        if obj.in_service:
            return format_html('<span class="status-pill badge-success">In Service</span>')
        return format_html('<span class="status-pill badge-danger">Out of Service</span>')

    @admin.display(description='Capacity')
    def capacity_display(self, obj):
        return f"{obj.type.capacity} guests"

    @admin.display(description='Nightly Rate')
    def rate_display(self, obj):
        return f"${obj.type.nightly_rate_minor / 100:.2f}"


class ReservationAdmin(LumaBaseAdmin):
    list_display = ('reference', 'guest_link', 'room_number', 'arrival', 'departure', 'occupants', 'status_badge', 'verified_badge', 'created_at')
    list_filter = ('status', 'verified', 'arrival', 'departure')
    search_fields = ('reference', 'guest__full_name', 'guest__email', 'room__number')
    readonly_fields = ('reference', 'created_at')
    ordering = ('-created_at',)

    @admin.display(description='Guest')
    def guest_link(self, obj):
        url = reverse('luma_admin:core_guest_change', args=[obj.guest.id])
        return format_html('<a href="{}" class="admin-link">{}</a>', url, obj.guest.full_name)

    @admin.display(description='Room')
    def room_number(self, obj):
        return f"Room {obj.room.number} ({obj.room.type.name})"

    @admin.display(description='Status')
    def status_badge(self, obj):
        return format_status_badge(obj.status)

    @admin.display(description='Verified')
    def verified_badge(self, obj):
        if obj.verified:
            return format_html('<span class="status-pill badge-success">Verified</span>')
        return format_html('<span class="status-pill badge-muted">Unverified</span>')


class GuestAdmin(LumaBaseAdmin):
    list_display = ('full_name', 'email', 'phone', 'reservations_count')
    search_fields = ('full_name', 'email', 'phone')

    @admin.display(description='Total Stays/Reservations')
    def reservations_count(self, obj):
        return obj.reservation_set.count()


class AllocationAdmin(LumaBaseAdmin):
    list_display = ('room', 'period', 'kind', 'active_badge', 'reservation_reference', 'expires_at')
    list_filter = ('kind', 'active')
    search_fields = ('room__number', 'reservation__reference')

    @admin.display(description='Active')
    def active_badge(self, obj):
        if obj.active:
            return format_html('<span class="status-pill badge-success">Active</span>')
        return format_html('<span class="status-pill badge-muted">Released</span>')

    @admin.display(description='Reservation')
    def reservation_reference(self, obj):
        if obj.reservation:
            url = reverse('luma_admin:core_reservation_change', args=[obj.reservation.id])
            return format_html('<a href="{}" class="admin-link">{}</a>', url, obj.reservation.reference)
        return "—"


class QuoteAdmin(LumaBaseAdmin):
    list_display = ('id_short', 'room', 'arrival', 'departure', 'occupants', 'total_display', 'expires_at')
    list_filter = ('arrival', 'departure')
    readonly_fields = ('id', 'room_amount_minor', 'tax_minor', 'total', 'expires_at')

    @admin.display(description='Quote ID')
    def id_short(self, obj):
        return str(obj.id)[:8]

    @admin.display(description='Total')
    def total_display(self, obj):
        return f"${obj.total / 100:.2f} {obj.currency}"


class FolioEntryInline(admin.TabularInline):
    model = FolioEntry
    extra = 0
    can_delete = False
    readonly_fields = ('category', 'description', 'amount_display', 'service_date', 'created_at')

    @admin.display(description='Amount')
    def amount_display(self, obj):
        return f"${obj.amount_minor / 100:.2f}"

    def has_add_permission(self, request, obj=None):
        return False


class FolioAdmin(LumaBaseAdmin):
    list_display = ('reservation_link', 'currency', 'version', 'closed_badge', 'balance_display')
    list_filter = ('closed',)
    search_fields = ('reservation__reference', 'reservation__guest__full_name')
    inlines = [FolioEntryInline]

    @admin.display(description='Reservation')
    def reservation_link(self, obj):
        url = reverse('luma_admin:core_reservation_change', args=[obj.reservation.id])
        return format_html('<a href="{}" class="admin-link">{} ({})</a>', url, obj.reservation.reference, obj.reservation.guest.full_name)

    @admin.display(description='Status')
    def closed_badge(self, obj):
        if obj.closed:
            return format_html('<span class="status-pill badge-muted">Closed</span>')
        return format_html('<span class="status-pill badge-success">Open</span>')

    @admin.display(description='Current Balance')
    def balance_display(self, obj):
        bal = services.balance(obj)
        return f"${bal / 100:.2f}"


class StayAdmin(LumaBaseAdmin):
    list_display = ('reservation_link', 'guest_name', 'room_number', 'checked_in_at', 'checked_out_at', 'stay_status')
    list_filter = ('checked_in_at', 'checked_out_at')
    search_fields = ('reservation__reference', 'reservation__guest__full_name', 'reservation__room__number')

    @admin.display(description='Reservation')
    def reservation_link(self, obj):
        url = reverse('luma_admin:core_reservation_change', args=[obj.reservation.id])
        return format_html('<a href="{}" class="admin-link">{}</a>', url, obj.reservation.reference)

    @admin.display(description='Guest')
    def guest_name(self, obj):
        return obj.reservation.guest.full_name

    @admin.display(description='Room')
    def room_number(self, obj):
        return f"Room {obj.reservation.room.number}"

    @admin.display(description='Status')
    def stay_status(self, obj):
        if obj.checked_out_at:
            return format_html('<span class="status-pill badge-muted">Checked Out</span>')
        return format_html('<span class="status-pill badge-success">Currently In-House</span>')


class HousekeepingTaskAdmin(LumaBaseAdmin):
    list_display = ('room_number', 'status_badge', 'assignee', 'notes_snippet', 'created_at', 'completed_at')
    list_filter = ('status', 'assignee')
    search_fields = ('room__number', 'notes')

    @admin.display(description='Room')
    def room_number(self, obj):
        return f"Room {obj.room.number}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        return format_status_badge(obj.status)

    @admin.display(description='Notes')
    def notes_snippet(self, obj):
        return (obj.notes[:40] + "…") if len(obj.notes) > 40 else (obj.notes or "—")


class ServiceRequestAdmin(LumaBaseAdmin):
    list_display = ('room_display', 'type', 'status_badge', 'description_snippet', 'assignee', 'submitted_at', 'completed_at')
    list_filter = ('type', 'status', 'submitted_at')
    search_fields = ('description', 'stay__reservation__guest__full_name')

    @admin.display(description='Room / Guest')
    def room_display(self, obj):
        return f"Room {obj.stay.reservation.room.number} · {obj.stay.reservation.guest.full_name}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        return format_status_badge(obj.status)

    @admin.display(description='Request')
    def description_snippet(self, obj):
        return (obj.description[:50] + "…") if len(obj.description) > 50 else obj.description


class MaintenanceTicketAdmin(LumaBaseAdmin):
    list_display = ('room_display', 'priority_badge', 'status_badge', 'description_snippet', 'assignee')
    list_filter = ('priority', 'status')
    search_fields = ('room__number', 'description')

    @admin.display(description='Room')
    def room_display(self, obj):
        return f"Room {obj.room.number}"

    @admin.display(description='Priority')
    def priority_badge(self, obj):
        color = 'badge-danger' if obj.priority == 'HIGH' else ('badge-warning' if obj.priority == 'MEDIUM' else 'badge-info')
        return format_html('<span class="status-pill {}">{}</span>', color, obj.priority)

    @admin.display(description='Status')
    def status_badge(self, obj):
        return format_status_badge(obj.status)

    @admin.display(description='Description')
    def description_snippet(self, obj):
        return (obj.description[:50] + "…") if len(obj.description) > 50 else obj.description


class PaymentAttemptAdmin(LumaBaseAdmin):
    list_display = ('id_short', 'reservation_link', 'amount_display', 'status_badge', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('reservation__reference',)

    @admin.display(description='Attempt ID')
    def id_short(self, obj):
        return str(obj.id)[:8]

    @admin.display(description='Reservation')
    def reservation_link(self, obj):
        url = reverse('luma_admin:core_reservation_change', args=[obj.reservation.id])
        return format_html('<a href="{}" class="admin-link">{}</a>', url, obj.reservation.reference)

    @admin.display(description='Amount')
    def amount_display(self, obj):
        return f"${obj.amount_minor / 100:.2f} {obj.currency}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        return format_status_badge(obj.status)


class PaymentAdmin(LumaBaseAdmin):
    list_display = ('id', 'reservation_reference', 'amount_display', 'settled_at')
    search_fields = ('attempt__reservation__reference',)

    @admin.display(description='Reservation')
    def reservation_reference(self, obj):
        res = obj.attempt.reservation
        url = reverse('luma_admin:core_reservation_change', args=[res.id])
        return format_html('<a href="{}" class="admin-link">{}</a>', url, res.reference)

    @admin.display(description='Amount Settled')
    def amount_display(self, obj):
        return f"${obj.amount_minor / 100:.2f}"


class UserAdmin(LumaBaseAdmin):
    list_display = ('username', 'email', 'role_badge', 'is_active_badge', 'is_staff', 'last_login')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')

    @admin.display(description='Role')
    def role_badge(self, obj):
        return format_html('<span class="status-pill badge-primary">{}</span>', obj.role)

    @admin.display(description='Active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="status-pill badge-success">Active</span>')
        return format_html('<span class="status-pill badge-danger">Inactive</span>')


class AuditAdmin(LumaBaseAdmin):
    list_display = ('timestamp', 'actor', 'action', 'target')
    list_filter = ('action',)
    search_fields = ('actor', 'action', 'target')
    ordering = ('-timestamp',)


class OTPAdmin(LumaBaseAdmin):
    list_display = ('reservation_link', 'attempts', 'consumed_badge', 'expires_at', 'issued_at')
    list_filter = ('consumed',)

    @admin.display(description='Reservation')
    def reservation_link(self, obj):
        return obj.reservation.reference

    @admin.display(description='Consumed')
    def consumed_badge(self, obj):
        if obj.consumed:
            return format_html('<span class="status-pill badge-muted">Consumed</span>')
        return format_html('<span class="status-pill badge-success">Valid</span>')


class RefundAdmin(LumaBaseAdmin):
    list_display = ('id', 'payment_info', 'amount_display', 'status_badge', 'requested_by', 'reviewed_by', 'created_at', 'settled_at')
    list_filter = ('status', 'created_at', 'settled_at')
    search_fields = ('reason', 'payment__attempt__reservation__reference')

    @admin.display(description='Payment')
    def payment_info(self, obj):
        return f"Payment #{obj.payment_id} ({obj.payment.attempt.reservation.reference})"

    @admin.display(description='Amount')
    def amount_display(self, obj):
        return f"${obj.amount_minor / 100:.2f}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        classes = {
            'SETTLED': 'badge-success',
            'APPROVED': 'badge-primary',
            'PENDING': 'badge-warning',
            'REJECTED': 'badge-danger',
        }
        badge_cls = classes.get(obj.status, 'badge-neutral')
        return format_html('<span class="status-pill {}">{}</span>', badge_cls, obj.status)


# Register all models with the custom Luma Haven Admin Site
luma_admin_site.register(Hotel, HotelAdmin)
luma_admin_site.register(RoomType, RoomTypeAdmin)
luma_admin_site.register(Room, RoomAdmin)
luma_admin_site.register(Reservation, ReservationAdmin)
luma_admin_site.register(Guest, GuestAdmin)
luma_admin_site.register(Allocation, AllocationAdmin)
luma_admin_site.register(Quote, QuoteAdmin)
luma_admin_site.register(Folio, FolioAdmin)
luma_admin_site.register(Stay, StayAdmin)
luma_admin_site.register(HousekeepingTask, HousekeepingTaskAdmin)
luma_admin_site.register(ServiceRequest, ServiceRequestAdmin)
luma_admin_site.register(MaintenanceTicket, MaintenanceTicketAdmin)
luma_admin_site.register(PaymentAttempt, PaymentAttemptAdmin)
luma_admin_site.register(Payment, PaymentAdmin)
luma_admin_site.register(Refund, RefundAdmin)
luma_admin_site.register(PaymentEvent)
luma_admin_site.register(PaymentException)
luma_admin_site.register(User, UserAdmin)
luma_admin_site.register(Audit, AuditAdmin)
luma_admin_site.register(OTP, OTPAdmin)
luma_admin_site.register(Outbox)
