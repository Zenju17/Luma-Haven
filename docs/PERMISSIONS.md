# Current backend access matrix

| Operation | Administrator | Manager | Reception | Housekeeping | Accountant | Verified booking guest |
|---|---|---|---|---|---|---|
| Public room search and quotes | Yes | Yes | Yes | Yes | Yes | Yes |
| View reservation and folio | Yes | Yes | Yes | No | Yes | Own booking only |
| Booking payment session | Yes | Yes | Yes | No | Yes | Own booking only |
| Booking check-in/out and requests | Yes | Yes | Yes | No | Yes | Own booking only |
| Staff reservation list | Yes | Yes | Yes | No | Yes | No |
| Operational summary | Yes | Yes | Yes | Redacted financials | Yes | No |
| Cleaning tasks and transitions | Yes | Yes | Yes | Except inspection approval | No | No |
| Maintenance creation and resolution | Yes | Yes | Yes | No | No | No |
| Reports and CSV | Yes | Yes | No | No | Yes | No |
| Complete guest requests | Yes | Yes | Yes | No | No | No |
| Admin staff roster, audit history and hotel settings (read-only) | Yes | No | No | No | No | No |

The guest site at `/` has no staff/admin navigation. `/staff` is the operational staff workspace, and `/admin` is an administrator-only console backed by `/api/v1/admin/staff`, `/api/v1/admin/audit`, and `/api/v1/admin/hotel`. Non-admin requests to these API endpoints receive HTTP 403 even when the private URL is entered directly. Administrator credentials can also be used to **separately sign in** to the staff workspace, without reusing or ending the administrator session.

Guest, staff and administrator sessions are stored by Django under **different HttpOnly cookies** (`sessionid`, `staff_sessionid`, `admin_sessionid`). An `X-Portal` request header selects the appropriate cookie for shared API routes; `/api/v1/admin/*` and `/api/v1/staff/*` always select their corresponding cookie regardless of that header. The header grants no permissions. Staff and administrator cookies are scoped to `/api/v1/`, and logging out deletes only that portal's cookie and server-side session. An old staff login held in a guest `sessionid` no longer confers staff permissions.

An initial reservation creates a short-lived restricted guest session allowing its creator to view and pay **that booking**. After the session expires, email OTP verification is required to re-enter. Completion of check-in additionally requires a verified booking. These rules are enforced in `backend/core/views.py` and `backend/core/services.py`; further scope hardening remains in the implementation status.
