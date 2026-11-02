# Handover — current state

**Snapshot:** 31 October 2026
**Branch:** `feat/hotel-management-system`
**HEAD:** `aed34f4` — *feat: add StaySteps component for simplified guest stay process and MediaAssetManager for visual asset management*

Read [`AGENTS.md`](../AGENTS.md) first for stack, commands and invariants. This file answers: what works, what is fake, what is risky, and what to do next.

## University deployment update — 2 November 2026

Vercel preview deployment preparation now uses Services for Vue/Django, hardened
`APP_ENV=demo`, simulated payments/verification, and durable bounded database images
(migration `0009`). See [VERCEL_DEMO.md](VERCEL_DEMO.md) for the deployment result,
presentation steps and hosting limits. The Supabase demo DB was backed up, its legacy
organization migration reconciled after schema verification, and `0006`–`0009`
applied; 29 image files imported. Existing inventory and accounts were not reseeded.
All 116 backend tests and four presentation-mode browser journeys pass on disposable
PostgreSQL; frontend build/typechecks, Django check and migration consistency pass.
Older snapshots and next steps below predate this deployment work.
After the initial preview, the user requested a normal public production deployment.
It is **READY** at https://luma-haven-zenju17.vercel.app (also
https://luma-haven-delta.vercel.app), deployment `dpl_6ZTf4wvGpPra1gskD8bQonSSJrwz`,
from committed Git source `557bd48`. Production has its own signing key and environment
variables. Vercel protection is disabled and the presentation banner is off; staff/admin
authentication remains. Payments and verification still use the explicitly simulated
runtime configuration; this release does not enable real payment/email providers.
Staticfiles was enabled to fix the real Vercel `collectstatic` build.

## Production inventory seed — 2 November 2026

Production was missing 7 of the 10 guest-facing room types: they were in
`roomCatalog.ts` and `seed_demo.py` but never seeded, so they showed names without
availability. After a private dump (`backups/before-room-seed-20261102T124513Z.dump`),
`seed_demo` was run against the Supabase demo DB. It is idempotent, so no users,
reservations or maintenance blocks were added. Production now has 10 types and 17 rooms,
16 in service (202 is under maintenance). Open issue: room 103 holds a seeded demo stay
that was never checked out. Once that stay is past its departure date, `_available_rooms`
treats it as an overstay and blocks 103 on every date until staff check the guest out.

## Image sharpness — 2 November 2026

Replaced 5 low-resolution guest images with 2400px Unsplash stock (docs/IMAGE_CREDITS.md)
and added a low-resolution warning to the media manager. Production `VisualAsset` #29
("Guest Lounge Concept", EXPERIENCE) now points to `visual_assets/features/lounge-2400.jpg`.
The old 328px `MediaFile` row (`visual_assets/features/lounge.jpg`) is kept for rollback. `rooms/connecting-family/main.jpg` (712px) still
needs a replacement.

## Status at a glance

Luma Haven is a **working development/demo checkpoint**, not production software. The full guest-to-housekeeping journey and the MIS management loop run end to end against PostgreSQL, with simulated payments.

- **Backend:** Django/DRF, one `core` app, migrations `0001`–`0004`, Celery + Redis.
- **Frontend:** Vue 3 + TypeScript with separate guest, staff, manager and admin portals.
- **Database:** PostgreSQL 17 via `DATABASE_URL`. Development uses Supabase (Singapore `LumaHaven`, session pooler). `btree_gist` + GiST exclusion prevents overlapping active room allocations.
- **Test baseline:** last recorded green run on disposable PostgreSQL: 37 backend pytest tests and 3 Playwright journeys (31 Oct 2026). The suite now collects 44 backend test functions, so re-run before claiming green. CI runs the same checks.

## Implemented

- Guest search, server-side quotes, 10-minute quote expiry, 15-minute holds, booking creation, simulated payment, OTP verification, self check-in/out, folio view, service requests.
- Staff workspace: daily movements, reservation search/amend/reassign, no-show, room board, housekeeping lifecycle, service request completion, maintenance, rates, refund requests.
- Two-person refund workflow (request → approve → settle/reject) with folio adjustments.
- Manager dashboard: 8 KPIs (occupancy, ADR, RevPAR, revenue, cash, receivables, turnaround, cancellation), SVG trends, room-type profitability, 7-rule Decision Support alerts.
- Five authorized MIS reports with sanitized CSV export (`daily-summary`, `revenue-occupancy`, `cash-reconciliation`, `housekeeping-turnaround`, `accounts-receivable`) and a nightly Celery snapshot.
- Admin console: staff roster, development-only password rotation, hotel settings, audit history, health diagnostics.
- Independent guest/staff/admin HttpOnly sessions; strict CSRF on API writes; role gates and guest booking isolation.
- Visual asset management (`VisualAsset`, import command, media manager) and the room-key visual system.

- P1 legal/consent/data-rights (see IMPLEMENTATION_STATUS): code complete, tests passed 1 Nov 2026.

- P2 Bakong KHQR (see PAYMENTS.md): code complete behind `PAYMENT_PROVIDER=bakong`; tests passed 1 Nov 2026; **no real Bakong call yet**.

- P3 admin console (see IMPLEMENTATION_STATUS): code complete; tests passed 1 Nov 2026. Login to `/admin` now also accepts `DEVELOPER` and `CONTENT_EDITOR`.

- P4 infrastructure (see INFRASTRUCTURE.md): files committed; **never deployed or run on Docker**. Celery broker now follows `REDIS_URL` (it was unset before).

- Guest UI redesigned 2 Nov 2026 (see DECISIONS). Room photos are representative stock supplied by the owner, not photos of the real property. Booking/checkout pages only picked up the new tokens and were not restructured; the "3-step progress" idea in `docs/REDESIGN_PLAN.md` is still open.

## Deliberately simulated or missing

- **Payments are fake by default** (KHQR exists but is unverified against Bakong). `/api/v1/development/checkout/<uuid>` is an emulator that writes provider events. No real gateway, signed webhooks, provider refunds, reconciliation with a PSP, or card storage.
- **No real identity verification, SMS, or door-lock integration.** QR is a generic link to `/verify`; physical keys are collected at reception.
- **Single property only.** No enforced organization/property tenancy or RLS. Do not present it as multi-tenant.
- **No PDF export.** CSV only.
- Other gaps: durable outbox delivery/retries, comprehensive append-only audit, login/OTP rate limiting, provider idempotency, retention policies, Playwright coverage beyond the three core journeys.

## Branch status

`main` was merged into `feat/hotel-management-system` on 31 Oct 2026 (P0 of `docs/IMPLEMENTATION_PLAN.md`).

- Kept from `feat`: the whole frontend (`features/` layout, `services/api.ts`, `package.json`/lockfile). `main`'s older Vue files (`src/views`, `src/lib`, `src/router.ts`, `src/types.ts`, `src/App.vue`) were dropped.
- Kept from `main`: `Organization`, `OrganizationMembership`, `PropertyMembership`, DB check constraints, `test_integrity_constraints.py`, `docs/DATABASE_*`, and the non-discarding `drain_outbox`.
- Migration `main/0002_organization...` was renumbered to **`0005_organization_organizationmembership_and_more`** (depends on `0004_visualasset`). If any database already applied main's old `0002`, the `django_migrations` row must be reconciled before migrating. Check `showmigrations core` on Supabase first and back it up.
- **Not yet verified:** the merged backend test suite and Playwright E2E, because no disposable PostgreSQL was available when merging. Run them before opening the PR to `main`.
- `Organization` is still a single-hotel placeholder; no tenancy is enforced.

## Environment / infrastructure notes

- The real `.env` is ignored and points at Supabase. Never print it, commit it, or paste its URI into logs/screenshots.
- Compose starts Redis, backend, worker, beat and frontend — **no local database**.
- Automated tests must use the disposable PostgreSQL on `127.0.0.1:55432` (`hims-integration-postgres`), never the Supabase demo project. The Playwright suite refuses non-loopback hosts and non-55432 ports.
- Earlier incident: a database password appeared in a Django debug traceback. `DJANGO_DEBUG=false` is the default; rotate the password if it is ever exposed again.
- Development credentials live in ignored `backend/.private-staff-passwords` (mode `0600`) after rotation. Treat as secret.
- Local recovery artifacts from the Tokyo→Singapore database move live outside the repo (`~/luma-recovery/`); they are not part of normal development.

## Recent commits (newest first)

| Commit | Change |
|---|---|
| `aed34f4` | StaySteps guest component + visual MediaAssetManager |
| `afcedd3` | Operations deep-linking and tab sync across portals |
| `02175bd` | Reservation table/action-button redesign |
| `9cf1e74` | Fix manager dashboard 500 caused by Supabase pool exhaustion |
| `65a2040` | Light-mode contrast and Tailwind 4 dark-variant fixes |
| `469d62e` | Manager and reception workspaces |
| `c201afe` | Custom Django admin CSS/templates |

## Next concrete steps

1. Replace the payment emulator with Bakong KHQR, following [`PAYMENTS.md`](PAYMENTS.md): adapter, QR/polling endpoints, idempotent `bakong:{md5}` settlement, refund/reconciliation handling.
2. Add PDF rendering for period reports and delivery/retry for notifications (outbox → worker).
3. Harden security: rate limits on login/OTP/booking lookup, identity review, retention policy, complete audit coverage.
4. Resolve the `main` ↔ `feat` divergence deliberately (decide which database-foundation work to port).
5. If multi-property is pursued: enforce property ownership on every record, permission matrix via membership, and PostgreSQL RLS; then add cross-tenant tests.
6. Expand Playwright coverage (admin password rotation, refunds, maintenance, reports) and keep CI green.

## Resume checklist for a new session

1. `git status` and confirm the branch (`feat/hotel-management-system` unless told otherwise).
2. Read `AGENTS.md`; open only the specific doc or source file needed.
3. Check whether the disposable PostgreSQL is running (`pg_isready -h 127.0.0.1 -p 55432`); do not use Supabase for tests.
4. Reproduce the current failing behavior before changing code; keep changes inside `services.py`/`views.py` patterns.
5. Run the narrowest relevant test first, then the full backend suite and frontend typecheck/build.
6. Update `docs/IMPLEMENTATION_STATUS.md` and this handover when the resume point changes.
