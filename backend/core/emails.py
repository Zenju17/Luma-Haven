"""Centralized email services for Luma Haven: OTP verification and booking confirmations.

Supports SMTP (Gmail, standard TLS/SSL) with elegant HTML + plaintext templates.
Safe fallback in development/offline modes.
"""
import logging
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

log = logging.getLogger(__name__)


def _send_templated_email(subject: str, to_email: str, text_content: str, html_content: str) -> bool:
    """Send a multipart HTML + text email safely without throwing unhandled exceptions."""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'noreply@lumahaven.com'
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)
        log.info('Sent email "%s" to %s', subject, to_email)
        return True
    except Exception as exc:
        log.warning('Failed sending email "%s" to %s: %s', subject, to_email, exc)
        return False


def build_otp_email_content(guest_email: str, guest_name: str, reference: str, code: str):
    """Build subject, plain text and HTML content for an OTP verification email."""
    subject = f'Luma Haven · Verification Code: {code}'
    safe_name = escape(guest_name or 'Valued Guest')
    safe_ref = escape(reference)
    safe_code = escape(code)

    text_content = f"""Luma Haven Verification Code

Hello {guest_name or 'Valued Guest'},

Your verification code for reservation {reference} is:

    {code}

This code expires in 5 minutes.

If you did not request this verification code, please ignore this email or contact hotel reception.

Luma Haven Boutique Hotel
Phnom Penh, Cambodia
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Luma Haven Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f6f3ee; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #1a2a26;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f6f3ee; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 540px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e3ded6; box-shadow: 0 4px 16px rgba(12, 43, 38, 0.04); overflow: hidden;">
          <tr>
            <td style="background-color: #0c2b26; padding: 32px 36px; text-align: center;">
              <span style="display: inline-block; width: 44px; height: 44px; line-height: 44px; border-radius: 50%; background-color: #1a423b; color: #f3ede2; font-family: Georgia, serif; font-size: 18px; font-weight: bold; border: 1px solid #35534c;">LH</span>
              <h1 style="margin: 12px 0 0 0; color: #f3ede2; font-family: Georgia, serif; font-size: 22px; font-weight: normal; letter-spacing: 0.5px;">Luma Haven</h1>
              <p style="margin: 4px 0 0 0; color: #9ab4ac; font-size: 12px; letter-spacing: 1px; text-transform: uppercase;">Boutique Hotel · Phnom Penh</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 36px 36px 24px 36px;">
              <p style="margin: 0 0 16px 0; font-size: 15px; color: #435b54;">Hello {safe_name},</p>
              <p style="margin: 0 0 24px 0; font-size: 15px; line-height: 1.5; color: #1a2a26;">
                Use the verification code below to access your reservation details for booking <strong>{safe_ref}</strong>:
              </p>
              
              <div style="background-color: #f0f6f4; border: 1px solid #cbdad4; border-radius: 12px; padding: 24px; text-align: center; margin: 28px 0;">
                <span style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #0c2b26; display: inline-block; padding-left: 8px;">
                  {safe_code}
                </span>
                <p style="margin: 10px 0 0 0; font-size: 13px; color: #536b66;">
                  Expires in <strong>5 minutes</strong>
                </p>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 13px; color: #698176; line-height: 1.5;">
                For your security, never share this verification code with anyone. Luma Haven staff will never ask for your code.
              </p>
              <p style="margin: 0; font-size: 13px; color: #698176; line-height: 1.5;">
                If you did not request this code, no action is needed.
              </p>
            </td>
          </tr>
          <tr>
            <td style="background-color: #faf8f5; padding: 20px 36px; border-top: 1px solid #f0ebe4; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #7f948e;">
                Luma Haven Hotel · Phnom Penh, Cambodia<br>
                A peaceful retreat for mindful hospitality.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return subject, text_content, html_content


def send_otp_email(guest_email: str, guest_name: str, reference: str, code: str) -> bool:
    """Send a 6-digit OTP verification email for guest portal access."""
    subject, text_content, html_content = build_otp_email_content(guest_email, guest_name, reference, code)
    return _send_templated_email(subject, guest_email, text_content, html_content)


def send_booking_confirmation_email(reservation) -> bool:
    """Send a booking confirmation email with reference, dates, room details, and stay link."""
    guest = reservation.guest
    room = reservation.room
    room_type = room.type
    hotel = room.hotel

    nights = (reservation.departure - reservation.arrival).days
    total_minor = sum(entry.amount_minor for entry in reservation.folio.entries.all()) if hasattr(reservation, 'folio') else 0
    total_dollars = f"${total_minor / 100:.2f}" if total_minor else "Calculated at checkout"

    frontend_origin = getattr(settings, 'FRONTEND_ORIGIN', 'http://localhost:5173').rstrip('/')
    booking_url = f"{frontend_origin}/booking/{reservation.pk}"
    verify_url = f"{frontend_origin}/verify"

    subject = f"Luma Haven Reservation Confirmation · {reservation.reference}"

    safe_name = escape(guest.full_name)
    safe_ref = escape(reservation.reference)
    safe_room_name = escape(room_type.name)
    safe_room_num = escape(room.number)

    text_content = f"""Luma Haven — Reservation Confirmation

Dear {guest.full_name},

Thank you for choosing Luma Haven. Your reservation has been successfully created.

Reservation Reference: {reservation.reference}
Status: {reservation.status}

Stay Details:
- Room: {room_type.name} (Room {room.number})
- Arrival: {reservation.arrival} (Check-in from {hotel.check_in_time})
- Departure: {reservation.departure} (Check-out by {hotel.check_out_time})
- Duration: {nights} night(s)
- Occupants: {reservation.occupants} guest(s)
- Total Amount: {total_dollars} {hotel.currency}

Manage your stay and complete payment:
{booking_url}

Verify your booking anytime:
{verify_url}

Hotel Information:
{hotel.name}
Timezone: {hotel.timezone}
Phnom Penh, Cambodia

We look forward to welcoming you.
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Luma Haven Reservation Confirmation</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f6f3ee; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #1a2a26;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f6f3ee; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e3ded6; box-shadow: 0 4px 16px rgba(12, 43, 38, 0.04); overflow: hidden;">
          <tr>
            <td style="background-color: #0c2b26; padding: 32px 36px; text-align: center;">
              <span style="display: inline-block; width: 44px; height: 44px; line-height: 44px; border-radius: 50%; background-color: #1a423b; color: #f3ede2; font-family: Georgia, serif; font-size: 18px; font-weight: bold; border: 1px solid #35534c;">LH</span>
              <h1 style="margin: 12px 0 0 0; color: #f3ede2; font-family: Georgia, serif; font-size: 24px; font-weight: normal; letter-spacing: 0.5px;">Reservation Confirmation</h1>
              <p style="margin: 4px 0 0 0; color: #9ab4ac; font-size: 12px; letter-spacing: 1px; text-transform: uppercase;">Luma Haven Boutique Hotel</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 36px 36px 20px 36px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; color: #1a2a26;">
                Dear <strong>{safe_name}</strong>,
              </p>
              <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #435b54;">
                Thank you for reserving your stay with us. We have received your booking and look forward to welcoming you to our sanctuary in Phnom Penh.
              </p>

              <div style="background-color: #faf8f5; border: 1px solid #ede7df; border-radius: 12px; padding: 24px; margin-bottom: 28px;">
                <table width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px;">
                  <tr>
                    <td style="padding: 6px 0; color: #698176; width: 40%;">Reservation Reference</td>
                    <td style="padding: 6px 0; color: #0c2b26; font-weight: bold; font-family: monospace; font-size: 16px;">{safe_ref}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #698176;">Room Type</td>
                    <td style="padding: 6px 0; color: #1a2a26; font-weight: 500;">{safe_room_name} (Room {safe_room_num})</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #698176;">Check-in Date</td>
                    <td style="padding: 6px 0; color: #1a2a26;">{reservation.arrival} <span style="color: #7f948e; font-size: 12px;">(from {hotel.check_in_time})</span></td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #698176;">Check-out Date</td>
                    <td style="padding: 6px 0; color: #1a2a26;">{reservation.departure} <span style="color: #7f948e; font-size: 12px;">(by {hotel.check_out_time})</span></td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #698176;">Length of Stay</td>
                    <td style="padding: 6px 0; color: #1a2a26;">{nights} night(s) · {reservation.occupants} guest(s)</td>
                  </tr>
                  <tr>
                    <td style="padding: 12px 0 6px 0; color: #0c2b26; font-weight: bold; border-top: 1px solid #e3ded6;">Total Amount</td>
                    <td style="padding: 12px 0 6px 0; color: #0c2b26; font-weight: bold; font-size: 16px; border-top: 1px solid #e3ded6;">{total_dollars} {hotel.currency}</td>
                  </tr>
                </table>
              </div>

              <div style="text-align: center; margin: 32px 0 20px 0;">
                <a href="{booking_url}" style="display: inline-block; background-color: #0c2b26; color: #f3ede2; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 14px; letter-spacing: 0.3px;">
                  View & Manage Your Reservation →
                </a>
              </div>

              <p style="margin: 20px 0 0 0; text-align: center; font-size: 12px; color: #7f948e;">
                You can also verify your stay anytime at <a href="{verify_url}" style="color: #0c2b26; text-decoration: underline;">{verify_url}</a> using your email and reference code.
              </p>
            </td>
          </tr>
          <tr>
            <td style="background-color: #faf8f5; padding: 24px 36px; border-top: 1px solid #f0ebe4; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #7f948e; line-height: 1.5;">
                <strong>{hotel.name}</strong> · Phnom Penh, Cambodia<br>
                For questions, special requests, or airport transfers, please contact our front desk.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return _send_templated_email(subject, guest.email, text_content, html_content)


def send_payment_confirmed_email(reservation, payment_amount_minor: int) -> bool:
    """Send payment confirmation receipt after payment completes."""
    guest = reservation.guest
    room = reservation.room
    hotel = room.hotel

    paid_dollars = f"${payment_amount_minor / 100:.2f}"
    frontend_origin = getattr(settings, 'FRONTEND_ORIGIN', 'http://localhost:5173').rstrip('/')
    booking_url = f"{frontend_origin}/booking/{reservation.pk}"

    subject = f"Payment Confirmed · Luma Haven Reservation {reservation.reference}"
    safe_name = escape(guest.full_name)
    safe_ref = escape(reservation.reference)

    text_content = f"""Luma Haven — Payment Confirmed

Dear {guest.full_name},

We have received your payment of {paid_dollars} {hotel.currency} for reservation {reservation.reference}.
Your booking is now CONFIRMED.

Room: {room.type.name} (Room {room.number})
Arrival: {reservation.arrival}
Departure: {reservation.departure}

View your reservation:
{booking_url}

Thank you,
Luma Haven Boutique Hotel
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Payment Confirmed</title></head>
<body style="margin: 0; padding: 0; background-color: #f6f3ee; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table role="presentation" width="100%" style="background-color: #f6f3ee; padding: 40px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width: 540px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e3ded6; overflow: hidden;">
        <tr>
          <td style="background-color: #0c2b26; padding: 28px 36px; text-align: center; color: #f3ede2;">
            <h1 style="margin: 0; font-family: Georgia, serif; font-size: 22px;">Payment Confirmed ✓</h1>
            <p style="margin: 4px 0 0 0; color: #9ab4ac; font-size: 13px;">Reservation {safe_ref}</p>
          </td>
        </tr>
        <tr>
          <td style="padding: 32px 36px;">
            <p style="margin: 0 0 16px 0; font-size: 15px;">Dear <strong>{safe_name}</strong>,</p>
            <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.5; color: #435b54;">
              We have successfully received your payment of <strong>{paid_dollars} {hotel.currency}</strong>. Your stay is fully confirmed and your room is reserved.
            </p>
            <div style="text-align: center; margin: 28px 0;">
              <a href="{booking_url}" style="background-color: #0c2b26; color: #f3ede2; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px;">
                View Booking Details →
              </a>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""
    return _send_templated_email(subject, guest.email, text_content, html_content)
