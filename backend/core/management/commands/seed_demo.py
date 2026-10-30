import os
import secrets
from datetime import timedelta
from psycopg.types.range import Range
from django.core.management.base import BaseCommand
from django.utils import timezone
from core import services
from core.models import (Allocation, Hotel, RoomType, Room, User, HousekeepingTask,
                         Reservation, PaymentAttempt, ServiceRequest, MaintenanceTicket)

class Command(BaseCommand):
    help = 'Create idempotent synthetic local demonstration inventory and staff'

    def handle(self, *args, **kwargs):
        hotel, _ = Hotel.objects.get_or_create(name='Luma Haven', defaults={'email': 'hello@luma.local', 'phone': '+855 00 000 000'})
        for name, price, capacity, numbers in [('Garden King', 8500, 2, ['101', '102', '103']), ('City Twin', 7200, 2, ['201', '202']), ('Family Suite', 15500, 4, ['301', '302'])]:
            room_type, _ = RoomType.objects.get_or_create(hotel=hotel, name=name, defaults={'nightly_rate_minor': price, 'capacity': capacity, 'description': 'Thoughtful comfort for your stay.', 'amenities': ['Wi-Fi', 'Air conditioning']})
            for number in numbers:
                room, created = Room.objects.get_or_create(hotel=hotel, number=number, defaults={'type': room_type})
                if created and number == '102':
                    room.cleaning = 'DIRTY'
                    room.save(update_fields=['cleaning'])
                    HousekeepingTask.objects.create(room=room)
        password = os.getenv('SEED_PASSWORD') or secrets.token_urlsafe(18)
        for username, role in [('admin', 'ADMIN'), ('manager', 'MANAGER'), ('reception', 'RECEPTION'), ('housekeeping', 'HOUSEKEEPING'), ('accountant', 'ACCOUNTANT')]:
            user, created = User.objects.get_or_create(username=username, defaults={'role': role, 'is_staff': True})
            if created:
                user.set_password(password)
                user.save(update_fields=['password'])
            elif not user.is_staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
        today = services.hotel_today(hotel)
        if not MaintenanceTicket.objects.filter(room__hotel=hotel).exists():
            room = Room.objects.get(hotel=hotel, number='202')
            block = Allocation.objects.create(room=room, period=Range(today, today + timedelta(days=5), '[)'), kind='MAINTENANCE')
            MaintenanceTicket.objects.create(room=room, description='Synthetic air conditioning inspection', allocation=block)
            room.in_service = False
            room.save(update_fields=['in_service'])
        if not Reservation.objects.filter(guest__email='active.demo@localhost').exists():
            room = Room.objects.get(hotel=hotel, number='103')
            reservation = services.reserve(services.create_quote(room, today, today + timedelta(days=2), 1), 'Demo Active Guest', 'active.demo@localhost')
            amount = services.balance(reservation.folio)
            attempt = PaymentAttempt.objects.create(reservation=reservation, amount_minor=amount, currency='USD')
            services.process_event(attempt.id, 'SUCCESS', 'demo-active-payment')
            reservation.refresh_from_db()
            reservation.verified = True
            reservation.save(update_fields=['verified'])
            stay = services.check_in(reservation)
            ServiceRequest.objects.create(stay=stay, type='Towels', description='Please bring extra towels')
        if not Reservation.objects.filter(guest__email='future.demo@localhost').exists():
            room = Room.objects.get(hotel=hotel, number='101')
            reservation = services.reserve(services.create_quote(room, today + timedelta(days=3), today + timedelta(days=5), 2), 'Demo Future Guest', 'future.demo@localhost')
            attempt = PaymentAttempt.objects.create(reservation=reservation, amount_minor=services.balance(reservation.folio), currency='USD')
            services.process_event(attempt.id, 'SUCCESS', 'demo-future-payment')
        self.stdout.write(f'New account password (only for newly created users): {password}')
