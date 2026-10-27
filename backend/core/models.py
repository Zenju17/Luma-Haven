import uuid
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models
from django.db.models import Q, F
from django.utils import timezone

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=[(x, x) for x in ['ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING', 'ACCOUNTANT']], default='RECEPTION')

class Organization(models.Model):
    name = models.CharField(max_length=120)


class Hotel(models.Model):
    # Nullable until an operator has mapped and validated existing properties.
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT)

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    timezone = models.CharField(max_length=64, default='Asia/Phnom_Penh')
    currency = models.CharField(max_length=3, default='USD')
    check_in_time = models.TimeField(default='14:00')
    check_out_time = models.TimeField(default='12:00')
    tax_percent = models.PositiveSmallIntegerField(default=0)
    deposit_percent = models.PositiveSmallIntegerField(default=100)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(tax_percent__lte=100), name='hotel_tax_percent_lte_100'),
            models.CheckConstraint(condition=Q(deposit_percent__lte=100), name='hotel_deposit_percent_lte_100'),
        ]


class OrganizationMembership(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    role = models.CharField(max_length=40)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['organization', 'user'], name='unique_org_member')]


class PropertyMembership(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    role = models.CharField(max_length=40)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['hotel', 'user'], name='unique_property_member')]


class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.PROTECT)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    capacity = models.PositiveSmallIntegerField(default=2)
    amenities = models.JSONField(default=list)
    nightly_rate_minor = models.PositiveIntegerField()

class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.PROTECT)
    type = models.ForeignKey(RoomType, on_delete=models.PROTECT)
    number = models.CharField(max_length=12)
    cleaning = models.CharField(max_length=24, default='READY', choices=[(x, x) for x in ['DIRTY', 'CLEANING', 'INSPECTION', 'READY']])
    in_service = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['hotel', 'number'], name='unique_hotel_room')]

class Guest(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)

class Quote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    arrival = models.DateField()
    departure = models.DateField()
    occupants = models.PositiveSmallIntegerField()
    room_amount_minor = models.PositiveIntegerField()
    tax_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    expires_at = models.DateTimeField()

    @property
    def total(self):
        return self.room_amount_minor + self.tax_minor

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(departure__gt=F('arrival')), name='quote_valid_dates'),
            models.CheckConstraint(condition=Q(occupants__gt=0), name='quote_positive_occupants'),
        ]


class Reservation(models.Model):
    reference = models.CharField(max_length=18, unique=True)
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    arrival = models.DateField()
    departure = models.DateField()
    occupants = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, default='HOLD')
    hold_expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(departure__gt=F('arrival')), name='reservation_valid_dates'),
            models.CheckConstraint(condition=Q(occupants__gt=0), name='reservation_positive_occupants'),
        ]


class Allocation(models.Model):
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    reservation = models.ForeignKey(Reservation, null=True, blank=True, on_delete=models.PROTECT)
    period = DateRangeField()
    kind = models.CharField(max_length=20, default='HOLD')
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [ExclusionConstraint(name='no_active_room_overlap', expressions=[('room', RangeOperators.EQUAL), ('period', RangeOperators.OVERLAPS)], condition=Q(active=True)), models.CheckConstraint(condition=Q(reservation__isnull=False) | Q(kind='MAINTENANCE'), name='allocation_has_owner')]

class Folio(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.PROTECT)
    currency = models.CharField(max_length=3)
    version = models.PositiveIntegerField(default=1)
    closed = models.BooleanField(default=False)

class FolioEntry(models.Model):
    folio = models.ForeignKey(Folio, related_name='entries', on_delete=models.PROTECT)
    category = models.CharField(max_length=40)
    description = models.CharField(max_length=200)
    amount_minor = models.IntegerField()
    service_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)

class PaymentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(default=timezone.now)

class PaymentEvent(models.Model):
    event_id = models.CharField(max_length=100, unique=True)
    attempt = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=20)
    processed_at = models.DateTimeField(default=timezone.now)

class Payment(models.Model):
    attempt = models.OneToOneField(PaymentAttempt, on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
    settled_at = models.DateTimeField(default=timezone.now)

class PaymentException(models.Model):
    attempt = models.OneToOneField(PaymentAttempt, on_delete=models.PROTECT)
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now)

class OTP(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)
    issued_at = models.DateTimeField(default=timezone.now)

class Stay(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.PROTECT)
    checked_in_at = models.DateTimeField(default=timezone.now)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    actor = models.ForeignKey(User, null=True, on_delete=models.PROTECT)

class HousekeepingTask(models.Model):
    stay = models.OneToOneField(Stay, null=True, blank=True, on_delete=models.PROTECT)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    status = models.CharField(max_length=24, default='DIRTY')
    assignee = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

class ServiceRequest(models.Model):
    stay = models.ForeignKey(Stay, on_delete=models.PROTECT)
    type = models.CharField(max_length=40)
    description = models.TextField()
    status = models.CharField(max_length=20, default='SUBMITTED')
    assignee = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    submitted_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

class MaintenanceTicket(models.Model):
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    description = models.TextField()
    priority = models.CharField(max_length=12, default='NORMAL')
    status = models.CharField(max_length=20, default='OPEN')
    assignee = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    allocation = models.OneToOneField(Allocation, null=True, blank=True, on_delete=models.PROTECT)

class Audit(models.Model):
    actor = models.CharField(max_length=120)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=80)
    timestamp = models.DateTimeField(default=timezone.now)

class Outbox(models.Model):
    kind = models.CharField(max_length=60)
    target = models.CharField(max_length=80)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
