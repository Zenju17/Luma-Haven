from datetime import date

import pytest
from django.db import IntegrityError, transaction

from core.models import Hotel, Guest, Reservation, Room, RoomType


@pytest.mark.django_db
def test_hotel_percentages_and_room_uniqueness():
    hotel = Hotel.objects.create(name='First')
    other = Hotel.objects.create(name='Second')
    kind = RoomType.objects.create(hotel=hotel, name='Standard', nightly_rate_minor=100)
    other_kind = RoomType.objects.create(hotel=other, name='Standard', nightly_rate_minor=100)
    Room.objects.create(hotel=hotel, type=kind, number='1')
    Room.objects.create(hotel=other, type=other_kind, number='1')
    with pytest.raises(IntegrityError), transaction.atomic():
        Room.objects.create(hotel=hotel, type=kind, number='1')
    for field in ('tax_percent', 'deposit_percent'):
        with pytest.raises(IntegrityError), transaction.atomic():
            Hotel.objects.filter(pk=hotel.pk).update(**{field: 101})


@pytest.mark.django_db
def test_reservation_dates_and_occupancy_are_enforced():
    hotel = Hotel.objects.create(name='Hotel')
    kind = RoomType.objects.create(hotel=hotel, name='Standard', nightly_rate_minor=100)
    room = Room.objects.create(hotel=hotel, type=kind, number='1')
    guest = Guest.objects.create(full_name='Guest', email='guest@example.test')
    from django.utils import timezone
    values = dict(reference='TEST', guest=guest, room=room, arrival=date(2026, 1, 1),
                  departure=date(2026, 1, 2), occupants=1, hold_expires_at=timezone.now())
    for invalid in ({'departure': date(2026, 1, 1)}, {'occupants': 0}):
        with pytest.raises(IntegrityError), transaction.atomic():
            Reservation.objects.create(**(values | invalid))
