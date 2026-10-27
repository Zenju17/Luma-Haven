# Implementation status · 24 October 2026

## Completed

- Feature branch, Django/DRF/Vite/Vue 3/Tailwind foundation and Compose configuration.
- Hotel, rooms, server quotes, short-lived holds, half-open PostgreSQL inventory exclusion, payment attempts and locally simulated settlement events, expired-hold release and late-payment conflict exceptions.
- Session login, role gates on staff operations, guest booking isolation, OTP email verification, transactional stay transitions, service requests, dirty-room checkout and inspection workflow.
- Basic staff summary, reservations, room board and task/requests screens; guest search, reserve, pay, verify, stay and checkout screens. Backend cancellation of unpaid bookings, maintenance blocks with explicit conflict errors, and summary KPI/CSV endpoints.
- OpenAPI schema endpoint, Django checks and frontend build.
- Supabase PostgreSQL is the development database again; Compose runs Redis and application services only. Rootless Podman-compatible image references and SELinux shared bind mount labels are configured.
- A standalone start-to-finish presentation script is available in [DEMO.md](DEMO.md), including test account names, private OTP log retrieval, guest/staff browser separation and safe shutdown.
- Disposable PostgreSQL integration tests, a private file-based OTP adapter for local browser tests, Playwright coverage of the complete guest-to-housekeeping journey and a CI workflow are implemented. New folio entries increment folio versions under a row lock; checkout rejects a stale folio even when a later payment settles the new charge. Room board queries now refresh after housekeeping transitions.
- Vue 3 + TypeScript replaced the React UI while preserving guest search/booking/payment/verification/stay, staff operations, server queries and existing frontend URLs. Staff sessions are restored through `/auth/me` after a page refresh, and housekeeping actions refresh the room board.
- Separate staff (`/staff`) and administrator (`/admin`) Vue portals; the guest header links only to guest search and booking verification. Admin-only staff-roster, hotel-settings and audit GET endpoints plus period reports/CSV use persisted backend records. Administrator route and API access are tested independently of staff roles.
- Guest, staff and administrator now have separate server-managed HttpOnly session cookies. A user can keep an administrator login active while signing in to or out of `/staff`, including with another account; Vue sends an explicit portal selector on shared API calls. Legacy staff sessions in the previous shared cookie require re-login.

## Current work

Additional business rules, dedicated payment adapter boundaries, reporting, security hardening and integration verification.

## Tests actually executed

- `python backend/manage.py check` — passed.
- `python backend/manage.py makemigrations --check --dry-run` — no model changes detected; DB history check warns because PostgreSQL is unavailable.
- `npm run typecheck` and `npm run build` — passed.
- Backend pytest collected eight integration tests. Running the suite here produced eight setup errors because there is no PostgreSQL listener at `localhost:5432`; no test assertions ran.
- `npm run dev` started the Vite development server at `http://127.0.0.1:5173/`. A direct Django `runserver` attempt stopped during the migration check because PostgreSQL is not running; the full guest workflow has **not** been run.
- PostgreSQL pytest integration tests authored but **not executed**: no PostgreSQL server or Docker executable is installed here.
- Supabase configuration change: `manage.py check` passed with a dummy session-pooler URI; `makemigrations --check --dry-run` reported no changes (database history lookup warned because the dummy hostname cannot resolve); four database-configuration tests passed and eight DB-backed tests collected. Both Compose YAML files parsed. No remote Supabase connection or Compose execution was tested.
- Local PostgreSQL return: `manage.py check` passed with the local `db` URI; `makemigrations --check --dry-run` reported no changes (the Docker-only hostname `db` cannot resolve on this host); five database-settings tests passed. The local PostgreSQL Compose YAML and persistent volume configuration parsed, but Docker execution is unavailable here.
- Current Supabase switch: Podman Compose `config` parsed with no local DB service, Django `check` passed using a dummy Supabase session-pooler URI, five database-configuration tests passed, and frontend type checking/build passed. No live Supabase connection or migration was attempted because the real URI is not configured here.
- After user-supplied setup: Supabase migrations and synthetic seed completed; the Podman stack runs, and the public rooms API returns persisted seed inventory. Enabled Django's template engine to serve interactive Swagger UI: live GET `/api/docs/` and `/api/schema/` both returned HTTP 200. The database password appeared in a Django debug traceback supplied by the user; `DJANGO_DEBUG=false` is the example default now, and the user must rotate the exposed password and update their existing `.env`.
- Staff service-request completion: identified stale frontend CSRF token after Django staff login; the frontend now refreshes it for every state-changing request and handles non-JSON server responses. CSRF failures from API endpoints return JSON, and duplicate request completion preserves its original timestamp. Six database-free backend tests, frontend type checking/build, Django check, and a live anonymous 403 JSON CSRF response passed. Completion in an authenticated browser has not yet been re-tested by the user.
- Guest check-in: a confirmed, verified and paid booking was rejected because its persisted arrival is October 29 while the hotel date is October 24. The backend now reports each failed prerequisite explicitly (including arrival date/timezone), and the frontend renders DRF validation arrays instead of a generic 400. A PostgreSQL-dependent early-arrival regression test was added but not executed against the main Supabase database.
- Isolated test run (26 October 2026): all **17 backend tests passed** on a disposable local PostgreSQL 17 container; migration consistency and Django checks passed. Frontend application/e2e type checks and production build passed. **One Chromium Playwright test passed**, covering booking/payment/OTP/check-in/request/checkout/inspection and unauthorized access. A stale room-board cache found on the first browser run was fixed, then the complete journey passed. The test database and OTP mail files were cleaned up; the real Supabase demo project was not used for testing. GitHub Actions CI configuration was added but has not yet been executed on GitHub.
- Vue migration (27 October 2026): `vue-tsc` and the production Vite build passed; the same Chromium Playwright journey passed on isolated PostgreSQL, including staff session restoration after refresh. No main Supabase database was used for the browser test.
- Separate portals (27 October 2026): **18 backend tests passed** on disposable PostgreSQL; two Playwright tests passed (complete guest-to-housekeeping workflow and guest/staff/admin route isolation, real admin data and CSV); `vue-tsc`, Playwright type checking, migration consistency and frontend production build passed. No tests were run against the main Supabase project. CSV exports use `export=csv` because DRF reserves `format` for renderer negotiation.
- Independent portal sessions (27 October 2026): **19 backend tests passed** on disposable PostgreSQL, including cookie isolation and independent logouts; two Playwright tests passed, including simultaneous staff/admin sign-in, staff logout preserving admin login, admin logout preserving staff login, guest verification and the full operational journey. Frontend type checks, build and migration consistency passed. The main Supabase project was not used for these tests.

## Known limitations

- This is an **incomplete working checkpoint**, not the complete README specification or a production-ready system.
- The user's Supabase-backed Compose demo was started, migrated and seeded locally. Automated tests deliberately use a separate, disposable PostgreSQL server instead of the main project. Repeated demonstrations still need a ready room and a booking for today's hotel date.
- Missing: amendments, paid cancellation/refunds, no-show, complete maintenance conflict resolution, historical reporting accuracy, PDF, comprehensive audit and monitoring, admin edits to staff/hotel settings, robust idempotency keys, identity review, provider-signed webhooks, secure guest token exchange, operational overrides, real provider integrations and login/OTP abuse protection.
- No real payment, SMS, identity-verification or door-lock integration. Backend outbox is stored but notifications and retry processing are not connected.
- The development checkout is an emulator and is not a real authenticated payment provider webhook.

## Next concrete steps

1. Add login/OTP throttling and scoped short-lived guest access tokens; test replay and authorization across portals.
2. Complete payment event authenticity, durable retry handling, refund approvals and transactional limits before considering any real provider.
3. Implement reservation amendments, cancellation/no-show and maintenance conflict workflows using the existing PostgreSQL allocation constraints.
4. Expand reporting accuracy, admin account/settings editing, audit coverage and PDF export; run the new CI workflow on GitHub when the changes are pushed.
