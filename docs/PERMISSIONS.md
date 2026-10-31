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
| Change another staff account password (development only) | Yes | No | No | No | No | No |

The guest site at `/` has no staff/admin navigation. `/staff` is the operational staff workspace, and `/admin` is an administrator-only console backed by `/api/v1/admin/staff`, `/api/v1/admin/audit`, and `/api/v1/admin/hotel`. Non-admin requests to these API endpoints receive HTTP 403 even when the private URL is entered directly. Administrator credentials can also be used to **separately sign in** to the staff workspace, without reusing or ending the administrator session.

`POST /api/v1/admin/staff/{id}/password` is permitted only to an administrator signed in via the admin portal, and cannot change that administrator's own password. In development it updates the target's hashed Django password and an ignored owner-only local credentials file, then writes a password-free audit entry. The endpoint is unavailable outside development. Existing sessions for the changed user are invalidated by Django's session authentication hash.

Guest, staff and administrator sessions are stored by Django under **different HttpOnly cookies** (`sessionid`, `staff_sessionid`, `admin_sessionid`). An `X-Portal` request header selects the appropriate cookie for shared API routes; `/api/v1/admin/*` and `/api/v1/staff/*` always select their corresponding cookie regardless of that header. The header grants no permissions. Staff and administrator cookies are scoped to `/api/v1/`, and logging out deletes only that portal's cookie and server-side session. An old staff login held in a guest `sessionid` no longer confers staff permissions.

An initial reservation creates a short-lived restricted guest session allowing its creator to view and pay **that booking**. After the session expires, email OTP verification is required to re-enter. Completion of check-in additionally requires a verified booking. These rules are enforced in `backend/core/views.py` and `backend/core/services.py`; further scope hardening remains in the implementation status.


## Admin console roles (P3)

Two roles were added for the `/admin` portal. Both sign in through the admin portal only; the server checks the role on every endpoint under `/api/v1/admin/`.

| Operation | Administrator | Content editor | Developer |
|---|---|---|---|
| Company dashboard, staff, hotel settings, audit, reports, media | Yes | No | No |
| Legal documents, privacy-request queue, payments reconciliation | Yes | No | No |
| CMS: create/edit page and banner **drafts**, restore revisions | Yes | Yes | No |
| CMS: **publish / unpublish** pages and banners | Yes | No | No |
| Developer console: health, jobs, outbox, provider status, config, errors, security (read) | Yes (read-only) | No | Yes |
| Developer console: toggle feature flags, test Bakong connectivity, sign a user out everywhere | No | No | Yes |
| Guest PII (reservations, data exports, privacy requests) | Yes | No | **No** |

Public read-only endpoints: `GET /api/v1/cms/pages/<slug>?lang=` and `GET /api/v1/cms/blocks?lang=` serve only the **published** copy. The `bookings_paused` feature flag makes the quote and booking endpoints return 400 while a maintenance window is active. The developer config endpoint reports secrets only as set/unset.
