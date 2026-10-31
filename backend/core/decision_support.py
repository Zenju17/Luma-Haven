"""Decision Support System (DSS) rules engine for Luma Haven Management Information System."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.db.models import Count, Q
from django.utils import timezone

from . import services
from .models import (
    Hotel, HousekeepingTask, MaintenanceTicket, PaymentAttempt, PaymentException,
    Reservation, Room, ServiceRequest
)


def evaluate_decision_support_alerts(hotel=None, period_start=None, period_end=None):
    """Evaluate server-side transparent business rules to generate actionable manager alerts.
    
    Each alert strictly adheres to the 4-part MIS decision structure:
    1. What happened (clear description of event/state)
    2. Which records or date range produced it (traceability)
    3. Why it matters (business/operational impact)
    4. An appropriate action the manager can take (prescriptive decision support)
    """
    if not hotel:
        hotel = Hotel.objects.first()
    if not hotel:
        return []

    hotel_tz = ZoneInfo(hotel.timezone)
    today = services.hotel_today(hotel)
    now = timezone.now()
    alerts = []

    # -------------------------------------------------------------
    # Rule 1: Low Forward Occupancy for Upcoming 7 Days (< 50% target)
    # -------------------------------------------------------------
    forward_start = today
    forward_end = today + timedelta(days=7)
    total_rooms = Room.objects.count()
    if total_rooms > 0:
        forward_days = 7
        total_forward_sellable = total_rooms * forward_days
        # Subtract maintenance blocks in the next 7 days
        from psycopg.types.range import Range
        from .models import Allocation
        forward_maint = Allocation.objects.filter(
            kind='MAINTENANCE',
            period__overlap=Range(forward_start, forward_end, '[)')
        )
        blocked_count = 0
        for offset in range(forward_days):
            d = forward_start + timedelta(days=offset)
            blocked_count += sum(1 for m in forward_maint if m.period.lower <= d < m.period.upper)
        forward_sellable = max(0, total_forward_sellable - blocked_count)

        # Count forward sold room-nights
        forward_res = Reservation.objects.filter(
            status__in=['CONFIRMED', 'CHECKED_IN'],
            arrival__lt=forward_end,
            departure__gt=forward_start
        )
        forward_sold = 0
        for res in forward_res:
            curr = max(res.arrival, forward_start)
            end_limit = min(res.departure, forward_end)
            while curr < end_limit:
                forward_sold += 1
                curr += timedelta(days=1)

        forward_occ = round(forward_sold * 100 / forward_sellable, 1) if forward_sellable else 0
        if forward_occ < 50.0:
            severity = 'URGENT' if forward_occ < 25.0 else 'WARNING'
            alerts.append({
                'id': 'low_occupancy_upcoming',
                'severity': severity,
                'category': 'REVENUE_OPTIMIZATION',
                'title': f'Low Forward Occupancy ({forward_occ}%) for Next 7 Days',
                'what_happened': f'Forward occupancy from {forward_start} to {forward_end} is {forward_occ}%, with only {forward_sold} of {forward_sellable} available room-nights booked.',
                'records_involved': f'{forward_sold} booked vs {forward_sellable} sellable room-nights ({forward_sellable - forward_sold} vacant nights across {forward_days} days)',
                'why_it_matters': 'Unoccupied room inventory perishes daily without producing revenue, reducing hotel RevPAR and profitability.',
                'recommended_action': 'Review room-type pricing, activate promotional discounts for target dates, or open inventory to OTA partner channels.'
            })

    # -------------------------------------------------------------
    # Rule 2: Reservations Awaiting Payment (arriving soon with balance)
    # -------------------------------------------------------------
    arrival_window = today + timedelta(days=3)
    unpaid_reservations = []
    active_unpaid = Reservation.objects.filter(
        status='CONFIRMED',
        arrival__gte=today,
        arrival__lte=arrival_window
    ).select_related('guest', 'room', 'folio')
    for res in active_unpaid:
        b = services.balance(res.folio)
        if b > 0:
            unpaid_reservations.append((res, b))

    if unpaid_reservations:
        total_unpaid = sum(b for _, b in unpaid_reservations)
        refs = [r.reference for r, _ in unpaid_reservations[:5]]
        records_str = f"{len(unpaid_reservations)} bookings: " + ", ".join(refs)
        if len(unpaid_reservations) > 5:
            records_str += f" (+{len(unpaid_reservations) - 5} more)"
        alerts.append({
            'id': 'unpaid_upcoming_reservations',
            'severity': 'WARNING',
            'category': 'FINANCIAL_CONTROL',
            'title': f'{len(unpaid_reservations)} Upcoming Booking(s) Awaiting Payment',
            'what_happened': f'{len(unpaid_reservations)} confirmed reservation(s) arriving within 3 days still have unpaid balances totaling ${total_unpaid / 100:.2f}.',
            'records_involved': records_str,
            'why_it_matters': 'Unsecured arrivals increase risk of last-minute no-shows, delayed check-in processing, and unpaid revenue leakage.',
            'recommended_action': 'Contact guests via email with payment session links to settle deposits prior to arrival date.'
        })

    # -------------------------------------------------------------
    # Rule 3: Payment Exceptions Requiring Investigation
    # -------------------------------------------------------------
    exceptions = list(PaymentException.objects.select_related('attempt__reservation').order_by('-created_at')[:10])
    if exceptions:
        count = len(exceptions)
        details = [f"Ref {e.attempt.reservation.reference}: {e.reason}" for e in exceptions[:3]]
        records_str = "; ".join(details)
        if count > 3:
            records_str += f" (+{count - 3} more)"
        alerts.append({
            'id': 'unresolved_payment_exceptions',
            'severity': 'URGENT',
            'category': 'PAYMENT_INTEGRITY',
            'title': f'{count} Payment Exception(s) Requiring Investigation',
            'what_happened': f'{count} payment attempt(s) encountered reconciliation or inventory conflict exceptions.',
            'records_involved': records_str,
            'why_it_matters': 'Guest payments may be in dispute, ledger records are unmatched, or room allocations failed due to late settlement.',
            'recommended_action': 'Inspect payment attempt logs, reconcile funds with the payment gateway, and initiate a reviewed refund or room reassignment.'
        })

    # -------------------------------------------------------------
    # Rule 4: Overdue Room Cleaning Before Today\'s Arrival
    # -------------------------------------------------------------
    today_arrivals = Reservation.objects.filter(
        arrival=today,
        status='CONFIRMED'
    ).select_related('room', 'guest')
    unready = [res for res in today_arrivals if res.room.cleaning != 'READY' or not res.room.in_service]
    if unready:
        count = len(unready)
        unready_details = [f"Room {r.room.number} ({r.room.cleaning}, Guest: {r.guest.full_name})" for r in unready[:4]]
        records_str = ", ".join(unready_details)
        if count > 4:
            records_str += f" (+{count - 4} more)"
        alerts.append({
            'id': 'unready_arrival_rooms',
            'severity': 'URGENT',
            'category': 'ROOM_OPERATIONS',
            'title': f'{count} Arrival Room(s) Not Ready for Check-in',
            'what_happened': f'{count} room(s) assigned to guests arriving today have not completed housekeeping inspection or are out of service.',
            'records_involved': records_str,
            'why_it_matters': 'Arriving guests cannot complete self check-in or access their accommodations upon arrival, causing immediate service friction.',
            'recommended_action': 'Prioritize housekeeping staff to these assigned rooms and expedite front-desk inspection immediately.'
        })

    # -------------------------------------------------------------
    # Rule 5: Rooms with Repeated Maintenance Issues (last 30 days)
    # -------------------------------------------------------------
    thirty_days_ago = now - timedelta(days=30)
    repeat_maintenance = (
        MaintenanceTicket.objects.filter(created_at__gte=thirty_days_ago)
        .values('room__number')
        .annotate(ticket_count=Count('id'))
        .filter(ticket_count__gte=2)
        .order_by('-ticket_count')
    )
    if repeat_maintenance.exists():
        room_list = [f"Room {item['room__number']} ({item['ticket_count']} tickets)" for item in repeat_maintenance]
        alerts.append({
            'id': 'recurring_maintenance_rooms',
            'severity': 'WARNING',
            'category': 'FACILITY_MAINTENANCE',
            'title': f'{len(room_list)} Room(s) with Recurring Maintenance Issues',
            'what_happened': f'{len(room_list)} room(s) logged 2 or more maintenance tickets in the last 30 days.',
            'records_involved': ", ".join(room_list),
            'why_it_matters': 'Chronic hardware or plumbing failures disrupt guest comfort, increase maintenance labor, and risk room downtime.',
            'recommended_action': 'Schedule a comprehensive engineering inspection of recurring equipment or replace aging components during maintenance blocks.'
        })

    # -------------------------------------------------------------
    # Rule 6: Unresolved Guest Service Requests (> 30 minutes)
    # -------------------------------------------------------------
    thirty_mins_ago = now - timedelta(minutes=30)
    overdue_requests = list(ServiceRequest.objects.filter(
        status='SUBMITTED',
        submitted_at__lte=thirty_mins_ago
    ).select_related('stay__reservation__room', 'stay__reservation__guest')[:8])
    if overdue_requests:
        count = len(overdue_requests)
        req_details = [
            f"Room {sr.stay.reservation.room.number}: {sr.type} ({int((now - sr.submitted_at).total_seconds() / 60)}m ago)"
            for sr in overdue_requests[:4]
        ]
        records_str = ", ".join(req_details)
        if count > 4:
            records_str += f" (+{count - 4} more)"
        alerts.append({
            'id': 'overdue_service_requests',
            'severity': 'WARNING',
            'category': 'GUEST_SERVICES',
            'title': f'{count} Guest Service Request(s) Pending > 30 Mins',
            'what_happened': f'{count} in-house guest request(s) remain unassigned or uncompleted after more than 30 minutes.',
            'records_involved': records_str,
            'why_it_matters': 'Delayed guest amenity fulfillment breaches hospitality service level agreements (SLAs) and reduces guest review scores.',
            'recommended_action': 'Dispatch floor runners or front-desk personnel to fulfill these pending items immediately.'
        })

    # -------------------------------------------------------------
    # Rule 7: Elevated Cancellation Rate (> 20% baseline)
    # -------------------------------------------------------------
    check_start = period_start or (today - timedelta(days=30))
    check_end = period_end or (today + timedelta(days=1))
    start_dt = timezone.make_aware(datetime.combine(check_start, time.min), hotel_tz) if isinstance(check_start, date) else check_start
    end_dt = timezone.make_aware(datetime.combine(check_end, time.min), hotel_tz) if isinstance(check_end, date) else check_end

    cohort_bookings = Reservation.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt).count()
    if cohort_bookings >= 5: # Statistically meaningful sample
        cohort_cancelled = Reservation.objects.filter(
            created_at__gte=start_dt, created_at__lt=end_dt, status='CANCELLED'
        ).count()
        canc_rate = round(cohort_cancelled * 100 / cohort_bookings, 1)
        if canc_rate > 20.0:
            alerts.append({
                'id': 'high_cancellation_rate',
                'severity': 'INFO',
                'category': 'PORTFOLIO_PERFORMANCE',
                'title': f'Elevated Period Cancellation Rate ({canc_rate}% vs 20% Baseline)',
                'what_happened': f'{cohort_cancelled} out of {cohort_bookings} reservations booked in this period were cancelled ({canc_rate}%).',
                'records_involved': f'{cohort_cancelled} cancelled / {cohort_bookings} total bookings ({check_start} to {check_end})',
                'why_it_matters': 'High cancellation velocity destabilizes occupancy forecasting, disrupts housekeeping staffing plans, and inflates booking acquisition costs.',
                'recommended_action': 'Analyze cancellation reasons, consider tightening cancellation policies for peak periods, or introduce non-refundable rate plans with pricing incentives.'
            })

    # -------------------------------------------------------------
    # Rule 8: KHQR attempts the sweeper has not reconciled (provider outage / worker stalled)
    # -------------------------------------------------------------
    stale = PaymentAttempt.objects.filter(provider='bakong', status='PENDING', expires_at__lt=now - timedelta(minutes=30))
    if stale.exists():
        count = stale.count()
        alerts.append({
            'id': 'unreconciled_khqr_attempts',
            'severity': 'CRITICAL',
            'category': 'PAYMENT_RECONCILIATION',
            'title': f'{count} KHQR Payment Attempt(s) Not Reconciled',
            'what_happened': f'{count} Bakong payment attempt(s) passed their expiry more than 30 minutes ago but are still PENDING.',
            'records_involved': ", ".join(f'attempt {str(a.pk)[:8]}' for a in stale[:10]),
            'why_it_matters': 'Guests may have paid without the booking being confirmed, or the payment worker or Bakong connection is down.',
            'recommended_action': 'Check the Celery worker/beat and Bakong connectivity, then verify the listed payments in the bank portal before releasing rooms.'
        })

    # -------------------------------------------------------------
    # Rule 9: High KHQR abandonment (>50% over 7 days, minimum 5 attempts)
    # -------------------------------------------------------------
    week = PaymentAttempt.objects.filter(provider='bakong', created_at__gte=now - timedelta(days=7)).exclude(status='PENDING')
    week_total = week.count()
    if week_total >= 5:
        lost = week.filter(status__in=['EXPIRED', 'FAILED']).count()
        if lost * 100 / week_total > 50:
            alerts.append({
                'id': 'high_khqr_abandonment',
                'severity': 'WARNING',
                'category': 'PAYMENT_CONVERSION',
                'title': f'High KHQR Abandonment ({round(lost * 100 / week_total)}%)',
                'what_happened': f'{lost} of {week_total} KHQR attempts in the last 7 days expired or failed.',
                'records_involved': f'{lost} expired/failed / {week_total} attempts (last 7 days)',
                'why_it_matters': 'Guests who cannot complete payment lose their hold and the hotel loses revenue.',
                'recommended_action': 'Review the QR window and checkout flow, test scanning with common banking apps, and consider a longer payment window.'
            })

    return alerts
