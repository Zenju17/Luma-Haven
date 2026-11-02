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
        inventory = [
            # name, rate (USD minor units), capacity, room numbers, description, amenities
            ('Garden King', 8500, 2, ['101', '102', '103'], 'Warm oak walls, paper lanterns and a corner sofa.', ['King bed', 'Wi-Fi', 'Air conditioning', 'Coffee corner']),
            ('City Twin', 7200, 2, ['201', '202'], 'Two single beds and a window over the treetops.', ['2 single beds', 'Wi-Fi', 'Air conditioning']),
            ('Family Suite', 15500, 4, ['301', '302'], 'A king bed plus a single bed, with extra floor space.', ['King + single bed', 'Wi-Fi', 'Air conditioning', 'Desk']),
            ('Classic Queen', 6500, 2, ['104', '105'], 'A calm, compact room with a tall window.', ['Queen bed', 'Wi-Fi', 'Air conditioning', 'Rain shower']),
            ('City King', 8000, 2, ['203', '204'], 'A king bed and a long sofa by full-height curtains.', ['King bed', 'Wi-Fi', 'Air conditioning', 'Sofa']),
            ('Double Queen', 9500, 4, ['205', '206'], 'Two queen beds, a work desk and a smart TV.', ['2 queen beds', 'Wi-Fi', 'Air conditioning', 'Smart TV']),
            ('Triple Room', 10500, 3, ['207'], 'Three single beds, so nobody has to share.', ['3 single beds', 'Wi-Fi', 'Air conditioning']),
            ('Connecting Family Rooms', 19000, 6, ['303'], 'Two rooms joined by a private connecting door.', ['2 rooms', '4 queen beds', '2 bathrooms', 'Wi-Fi']),
            ('Signature Suite', 21000, 2, ['401'], 'Separate lounge divided from the bedroom by a walnut screen.', ['King bed', 'Lounge', 'Wi-Fi', 'Air conditioning']),
            ('Riverfront Suite', 24000, 2, ['501'], 'Our largest room, with floor-to-ceiling river-facing windows.', ['King bed', 'River-facing windows', 'Dressing room', 'Wi-Fi']),
        ]
        for name, price, capacity, numbers, description, amenities in inventory:
            room_type, _ = RoomType.objects.get_or_create(hotel=hotel, name=name, defaults={'nightly_rate_minor': price, 'capacity': capacity, 'description': description, 'amenities': amenities})
            for number in numbers:
                room, created = Room.objects.get_or_create(hotel=hotel, number=number, defaults={'type': room_type})
                if created and number == '102':
                    room.cleaning = 'DIRTY'
                    room.save(update_fields=['cleaning'])
                    HousekeepingTask.objects.create(room=room)
        password = os.getenv('SEED_PASSWORD') or secrets.token_urlsafe(18)
        for username, role in [('admin', 'ADMIN'), ('manager', 'MANAGER'), ('reception', 'RECEPTION'), ('housekeeping', 'HOUSEKEEPING'), ('accountant', 'ACCOUNTANT'), ('developer', 'DEVELOPER'), ('editor', 'CONTENT_EDITOR')]:
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
