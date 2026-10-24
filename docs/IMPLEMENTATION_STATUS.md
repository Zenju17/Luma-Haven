# Implementation status · 24 October 2026

## Completed

- Feature branch, Django/DRF/Vite/React/Tailwind foundation and Compose configuration.
- Hotel, rooms, server quotes, short-lived holds, half-open PostgreSQL inventory exclusion, payment attempts and locally simulated settlement events, expired-hold release and late-payment conflict exceptions.
- Session login, role gates on staff operations, guest booking isolation, OTP email verification, transactional stay transitions, service requests, dirty-room checkout and inspection workflow.
- Basic staff summary, reservations, room board and task/requests screens; guest search, reserve, pay, verify, stay and checkout screens. Backend cancellation of unpaid bookings, maintenance blocks with explicit conflict errors, and summary KPI/CSV endpoints.
- OpenAPI schema endpoint, Django checks and frontend build.
- Supabase PostgreSQL is the development database again; Compose runs Redis and application services only. Rootless Podman-compatible image references and SELinux shared bind mount labels are configured.

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

## Known limitations

- This is an **incomplete working checkpoint**, not the complete README specification or a production-ready system.
- Compose services, database migration, seed command and browser journeys have not been exercised in this environment. Verify with the commands in README on a host with Docker.
- Docker is unavailable; Podman is installed, but no Compose provider was installed. A Podman Compose attempt built application images but could not start containers because short-name image resolution required an interactive prompt. Image names have since been qualified; Supabase connection, migrations and seeding still require a real `DATABASE_URL` in the ignored `.env`.
- Missing: amendments, paid cancellation/refunds, no-show, complete maintenance conflict resolution, historical reporting accuracy, PDF, detailed audit and monitoring, robust idempotency keys, identity review, provider-signed webhooks, secure guest token exchange, operational overrides, real provider integrations, login/OTP abuse protection, and Playwright scenarios.
- No real payment, SMS, identity-verification or door-lock integration. Backend outbox is stored but notifications and retry processing are not connected.
- The development checkout is an emulator and is not a real authenticated payment provider webhook.

## Next concrete steps

1. Set the Supabase session pooler URI in the existing ignored `.env`, start with Podman Compose or Docker Compose, migrate and seed synthetic data. Run integration tests only against an isolated PostgreSQL test server, then fix any runtime issues.
2. Add strict payment provider signatures, durable retry handling, refund locking and idempotency across browser commands.
3. Add guest token scope and identity review, maintenance block resolution, reservation amendments and cancellation.
4. Build server-calculated KPI reports, exports, access matrix tests and Playwright end-to-end tests.
