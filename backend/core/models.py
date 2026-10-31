import uuid
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models, transaction
from django.db.models import Q, F
from django.utils import timezone

ROLES = ['ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING', 'ACCOUNTANT', 'DEVELOPER', 'CONTENT_EDITOR']


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=[(x, x) for x in ROLES], default='RECEPTION')

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
    anonymized_at = models.DateTimeField(null=True, blank=True)

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
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True, default='')
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

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError('Folio entries are immutable; create an adjustment instead.')
        with transaction.atomic():
            folio = Folio.objects.select_for_update().get(pk=self.folio_id)
            if folio.closed:
                raise ValueError('Cannot charge a closed folio.')
            super().save(*args, **kwargs)
            Folio.objects.filter(pk=folio.pk).update(version=F('version') + 1)

    def delete(self, *args, **kwargs):
        raise ValueError('Folio entries are immutable; create an adjustment instead.')

class PaymentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(default=timezone.now)
    provider = models.CharField(max_length=20, default='development')
    provider_qr = models.TextField(blank=True, default='')
    provider_md5 = models.CharField(max_length=32, blank=True, default='', db_index=True)
    provider_tran_id = models.CharField(max_length=64, blank=True, default='')
    checkout_url = models.CharField(max_length=500, blank=True, default='')
    expires_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

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

class Refund(models.Model):
    payment = models.ForeignKey(Payment, related_name='refunds', on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
    reason = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default='PENDING', choices=[(x, x) for x in ['PENDING', 'APPROVED', 'REJECTED', 'SETTLED']])
    requested_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='requested_refunds')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_refunds')
    created_at = models.DateTimeField(default=timezone.now)
    settled_at = models.DateTimeField(null=True, blank=True)

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
    priority = models.CharField(max_length=12, default='NORMAL', choices=[(x, x) for x in ['NORMAL', 'HIGH', 'URGENT']])
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
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

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

class VisualAsset(models.Model):
    CATEGORY_CHOICES = [
        ('BRANDING', 'Branding & Logo'),
        ('HERO', 'Homepage Hero'),
        ('GALLERY', 'Homepage Gallery'),
        ('ROOM_TYPE', 'Room Type Gallery'),
        ('EXPERIENCE', 'Experience & Feature'),
        ('OTHER', 'Other / General'),
    ]
    SOURCE_CHOICES = [
        ('CONCEPT', 'AI Concept Visualization'),
        ('VERIFIED', 'Verified Hotel Photograph'),
        ('PLACEHOLDER', 'Graphic Placeholder'),
    ]

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='visual_assets')
    category = models.CharField(max_length=24, choices=CATEGORY_CHOICES, db_index=True)
    room_type = models.ForeignKey(RoomType, null=True, blank=True, on_delete=models.SET_NULL, related_name='visual_assets')
    image = models.ImageField(upload_to='visual_assets/%Y/%m/')
    title = models.CharField(max_length=120)
    caption = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=255)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='CONCEPT')
    facility_claim = models.CharField(max_length=80, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'display_order', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.category})"



LEGAL_KINDS = ['TERMS', 'PRIVACY', 'CANCELLATION', 'COOKIES', 'PAYMENT', 'STAFF_AGREEMENT']


class LegalDocument(models.Model):
    """Versioned legal text. A published version is immutable; publish a new version to change it."""
    kind = models.CharField(max_length=20, choices=[(x, x) for x in LEGAL_KINDS])
    language = models.CharField(max_length=2, choices=[('en', 'en'), ('km', 'km')])
    version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=160)
    body_markdown = models.TextField()
    status = models.CharField(max_length=12, default='DRAFT', choices=[(x, x) for x in ['DRAFT', 'PUBLISHED']])
    effective_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['kind', 'language', 'version'], name='unique_legal_version')]

    def save(self, *args, **kwargs):
        if self.pk and LegalDocument.objects.filter(pk=self.pk, status='PUBLISHED').exists():
            raise ValueError('Published legal documents are immutable; create a new version')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == 'PUBLISHED':
            raise ValueError('Published legal documents cannot be deleted')
        return super().delete(*args, **kwargs)


class ConsentRecord(models.Model):
    """Append-only proof that a guest or staff member accepted a document version."""
    document = models.ForeignKey(LegalDocument, on_delete=models.PROTECT)
    guest = models.ForeignKey(Guest, null=True, blank=True, on_delete=models.PROTECT)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    method = models.CharField(max_length=20, default='BOOKING')
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent_hash = models.CharField(max_length=64, blank=True)
    accepted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(guest__isnull=False) | Q(user__isnull=False), name='consent_has_subject')]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('Consent records are append-only')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Consent records are append-only')


class DataSubjectRequest(models.Model):
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT)
    type = models.CharField(max_length=12, choices=[(x, x) for x in ['ACCESS', 'EXPORT', 'RECTIFY', 'DELETE']])
    status = models.CharField(max_length=12, default='OPEN', choices=[(x, x) for x in ['OPEN', 'COMPLETED', 'REJECTED']])
    note = models.CharField(max_length=500, blank=True)
    resolution = models.CharField(max_length=500, blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField()
    handled_by = models.CharField(max_length=150, blank=True)
    handled_at = models.DateTimeField(null=True, blank=True)


class FeatureFlag(models.Model):
    key = models.SlugField(max_length=60, unique=True)
    enabled = models.BooleanField(default=False)
    description = models.CharField(max_length=200, blank=True)
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)


class CmsPage(models.Model):
    """Draft fields are edited freely; publishing copies them to the published_* fields served to guests."""
    slug = models.SlugField(max_length=60)
    language = models.CharField(max_length=2, choices=[('en', 'en'), ('km', 'km')], default='en')
    title = models.CharField(max_length=160)
    body_markdown = models.TextField(blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    is_published = models.BooleanField(default=False)
    published_title = models.CharField(max_length=160, blank=True)
    published_body = models.TextField(blank=True)
    published_seo_description = models.CharField(max_length=300, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['slug', 'language'], name='unique_cms_page')]


class CmsBlock(models.Model):
    """A small structured content slot such as an announcement banner (key + language)."""
    key = models.SlugField(max_length=60)
    language = models.CharField(max_length=2, choices=[('en', 'en'), ('km', 'km')], default='en')
    content = models.JSONField(default=dict)
    is_published = models.BooleanField(default=False)
    published_content = models.JSONField(default=dict)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['key', 'language'], name='unique_cms_block')]


class CmsRevision(models.Model):
    page = models.ForeignKey(CmsPage, related_name='revisions', on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    body_markdown = models.TextField(blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    action = models.CharField(max_length=12, default='SAVE', choices=[(x, x) for x in ['SAVE', 'PUBLISH', 'RESTORE']])
    saved_by = models.CharField(max_length=150, blank=True)
    saved_at = models.DateTimeField(default=timezone.now)


class JobRun(models.Model):
    task = models.CharField(max_length=120, db_index=True)
    task_id = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=10, choices=[(x, x) for x in ['SUCCESS', 'FAILURE']])
    started_at = models.DateTimeField(default=timezone.now)
    duration_ms = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=300, blank=True)


class ErrorEvent(models.Model):
    """Scrubbed server exception record (no query strings, bodies, emails or tokens)."""
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    request_id = models.CharField(max_length=40, blank=True)
    method = models.CharField(max_length=8, blank=True)
    path = models.CharField(max_length=200, blank=True)
    exc_type = models.CharField(max_length=120)
    message = models.CharField(max_length=300, blank=True)
