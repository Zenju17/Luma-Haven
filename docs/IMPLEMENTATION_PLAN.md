# Implementation plan — approved direction (31 Oct 2026)

Supersedes the open questions in `ROADMAP_PLAN.md` §7. Owner decisions:

| # | Decision |
|---|---|
| 1 | KHQR via Python `bakong-khqr` (backend). `mrrhak/khqr_sdk` only for a future Flutter app |
| 2 | Owner has a Bakong API token. It stays in `.env` only and is never committed or pasted |
| 3 | Merge `main` into `feat/hotel-management-system`, then PR to `main` |
| 4 | Legal text in English + Khmer, Markdown CMS editor |
| 5 | Retention follows real-world hotel practice (policy below) |
| 6 | License: **proprietary, all rights reserved** (recommended for a company system; can be changed later) |
| 7 | Full admin dashboard: a **Company Admin** area and a **Developer Console** |

Each phase ends with the AGENTS.md definition of done: tests on disposable Postgres `:55432`, `check`, `makemigrations --check`, `typecheck`, `build`, and doc updates. There is one PR per phase.

---

## Phase 0 — Branch merge (≈0.5 day)

Divergence: `main` has 3 commits not on `feat`:
- `bb67682`: the old PR #1 merge.
- `336815f`: the React→Vue migration. It is superseded, because `feat` already has a newer Vue layout in `features/`.
- `3915fba`: the Organization/membership model, integrity tests and `docs/DATABASE_*`.

**Conflict:** both branches have a migration `0002_*`.

Steps:
1. Back up the Supabase DB first. Then check which migrations are applied in it (`showmigrations core`). If main's `0002_organization...` was ever applied there, record it and plan a `--fake` step.
2. `git checkout feat/hotel-management-system && git merge main`.
   - Frontend conflicts: **keep `feat`** (drop `src/views/`, `src/lib/api.ts`, `src/main.ts` changes from main; keep `features/`, `services/api.ts`).
   - `package.json` / `package-lock.json`: keep `feat`, then run `npm install` to regenerate the lockfile.
   - `models.py` / `tasks.py`: keep both (add `Organization`, `OrganizationMembership` and the constraints from main).
   - Migrations: delete main's `0002_organization...` and regenerate it as `0005_organization...` on top of `0004_visualasset`.
   - Docs: keep `docs/DATABASE_*` and link them from `INDEX.md`.
3. Organization stays a **single-hotel placeholder**: seed one org, link the `Hotel`, and make no tenancy claims.
4. Run the full test suite, the 3 E2E journeys, `check` and `makemigrations --check`. Then open a PR `feat → main`.

---

## Phase 1 — Legal, consent and data protection (≈4 days)

### Retention policy (real-world hotel practice; confirm with accountant/lawyer)
| Data | Keep | Then |
|---|---|---|
| Folios, payments, refunds, invoices | 10 years (tax/accounting records) | Archive, never delete |
| Guest profile (name, email, phone) | 3 years after last stay | Anonymize; financial rows keep a pseudonymous ID |
| ID / passport details (if captured) | Only for the stay + police registration, max 1 year | Purge |
| Marketing consent | Until withdrawn | Stop use immediately |
| OTPs, quotes, expired holds | 24 hours | Hard delete |
| Audit log | 7 years | Archive |
| Server logs (no PII) | 90 days | Rotate |
| Data-subject requests | Answer within 30 days | Keep the request record 3 years |

All periods are settings (`RETENTION_*`). Admins can view them but only developers can change them.

### Backend
- Models: `LegalDocument` (kind, language `en|km`, version, body_markdown, status, effective_at), `ConsentRecord` (append-only; holds hashed IP/UA), `DataSubjectRequest`.
- Services: `accept_documents()`, `require_current_consent()` (called inside `create_booking`), `export_guest_data()`, `anonymize_guest()`.
- Celery beat `run_retention()` runs nightly. It writes counts to `Audit`.
- API: `GET /legal/<kind>?lang=`, `POST /consents`, `POST /me/data-requests`, admin `GET/PATCH /admin/data-requests`.
- Seed: EN+KM templates for terms, privacy, cancellation, cookies, payment terms and staff agreement. Each is marked "template — requires legal review".

### Frontend
- `features/legal/LegalPage.vue` at `/legal/:kind` with an EN/ខ្មែរ toggle and footer links.
- A required consent checkbox in the booking flow.
- "My data" on `/booking/:id`.
- Staff first-login agreement gate.

### Tests
- Booking without current consent → 400.
- A new version forces re-consent.
- Export is scoped to that guest.
- Anonymize keeps folio totals.
- The retention task respects each period.

---

## Phase 2 — Bakong KHQR payments (≈4 days)

Follows `docs/PAYMENTS.md` exactly. Summary of tasks:
1. `bakong-khqr==0.6.5` added to requirements and lockfile.
2. Env: `PAYMENT_PROVIDER`, `BAKONG_TOKEN`, `BAKONG_ACCOUNT_ID`, `BAKONG_MERCHANT_NAME`, `BAKONG_MERCHANT_CITY`, `BAKONG_CURRENCY`, plus a startup check.
3. `core/payments/{base,development,bakong,factory}.py`.
4. Migration: `PaymentAttempt` gets `provider`, `provider_qr`, `provider_md5`, `provider_tran_id`, `expires_at`.
5. `POST /reservations/<id>/payment-sessions` (the amount comes from the folio on the server) and `GET /payment-sessions/<uuid>`. The server calls `check_payment(md5)` and settles idempotently with `bakong:{md5}`.
6. Celery `sweep_payment_attempts` every 30 s: polls pending attempts, expires old ones and releases holds.
7. `CheckoutView.vue`: QR card (`qrcode.vue`), amount, countdown, polling, redirect. The simulator stays only when `PAYMENT_PROVIDER=development`.
8. MIS: channel mix, QR abandon rate, and an exceptions line in `cash-reconciliation`. New Decision Support rule: "unreconciled KHQR payments".
9. Throttles on session creation and polling.
10. Tests with `FakeBakongProvider`, never the network. Then a manual sandbox checklist using a $0.01 payment.

---

## Phase 3 — Full admin dashboard: Company Admin + Developer Console (≈6 days)

### Roles
Add `DEVELOPER` and `CONTENT_EDITOR` to `User.role` (migration).
- `ADMIN` is the company owner/GM.
- `DEVELOPER` is technical staff. They get the system console but **no** guest PII views by default.
- Update `docs/PERMISSIONS.md` and the server-side role checks.

### Layout
`/admin` becomes a sidebar layout (`layouts/AdminLayout.vue`) with grouped sections. Sections are hidden by role, and the server also enforces access.

**Company Admin (`ADMIN`, some sections for `MANAGER`/`CONTENT_EDITOR`)**
| Section | Contents |
|---|---|
| Overview | KPIs from the manager dashboard, today's arrivals/departures, payments today, alerts |
| Hotel settings | Name, address, contacts, currency, timezone, check-in/out times, taxes/fees, policies |
| Rooms & rates | Room types, rooms, rate plans, out-of-order (reuses the staff endpoints) |
| Staff & roles | Roster, invite, deactivate, role change, password reset, last login |
| Content (CMS) | Pages, homepage blocks, room marketing copy, media library, announcements; draft → publish, revisions |
| Legal | Legal docs EN/KM, versions, publish, consent stats |
| Privacy | Data-subject request queue with SLA timer, export/anonymize actions |
| Payments | KHQR attempts, settlements, exceptions, reconciliation; refund approvals |
| Reports | The five MIS reports + compliance report, CSV export |
| Audit | Searchable audit history with filters and export |

**Developer Console (`DEVELOPER`, `ADMIN` read-only)**
| Section | Contents |
|---|---|
| System health | DB, Redis, Celery worker/beat heartbeat, migration state, version/commit |
| Jobs | Celery task runs, failures, and a retry button for safe tasks |
| Outbox | Pending/failed outbox messages, retry, dead-letter |
| Payment provider | Active provider, Bakong connectivity check (no secrets shown), recent poll latency/errors |
| Feature flags | `FeatureFlag(key, enabled, description)`, e.g. `khqr_enabled`, `telegram_enabled`, `maintenance_mode` |
| Config view | Effective non-secret settings and retention periods. Secrets show only "set/unset" |
| Error log | Recent server exceptions with PII scrubbed (`ErrorEvent` model or Sentry link) |
| Security | Failed logins, throttled requests, active sessions, forced logout |

### Backend
- `FeatureFlag`, `CmsPage`, `CmsBlock`, `CmsRevision`, `ErrorEvent`, `JobRun` models (one migration).
- Admin endpoints under `/api/v1/admin/...` and `/api/v1/dev/...`, each role-checked, CSRF-protected and audited.
- Markdown is rendered server-side with sanitization (`markdown` + `bleach`/`nh3`); raw HTML is never stored.
- Public read-only `GET /cms/pages/<slug>` and `GET /cms/blocks`, cached.

### Frontend
- `features/admin/{overview,settings,rooms,staff,cms,legal,privacy,payments,reports,audit}/`.
- `features/dev/{health,jobs,outbox,provider,flags,config,errors,security}/`.
- Shared components: `DataTable`, `MarkdownEditor` (textarea + live preview), `StatusBadge`, `ConfirmDialog`.
- Light/dark and mobile tested. The guest site reads CMS content with the current hard-coded copy as fallback.

### Tests
- A role matrix covering every admin/dev endpoint.
- The CMS publish flow and the revision restore.
- Secrets are never present in dev config responses.
- An E2E journey: admin edits a page and publishes it, and the guest sees it.

---

## Phase 4 — IT infrastructure and production readiness (≈3 days)

- `docs/INFRASTRUCTURE.md`: topology diagram (proxy+TLS → Gunicorn → Postgres/Redis; Celery worker+beat; static Vue), environments, secrets handling.
- `.env.example`, a production compose file, Caddy config, container healthchecks.
- Security headers/CSP, DRF throttles on login/OTP/payment, `pip-audit` + `npm audit` in CI.
- Backups: a daily `pg_dump` plus a monthly restore drill script, with the last backup time shown in the Developer Console.
- Monitoring: structured logs, Sentry with PII scrubbing, an uptime check.
- `docs/SECURITY.md`, an incident and data-breach runbook, `CONTRIBUTING.md`, a proprietary `LICENSE`.
- `docs/PROJECT_SPEC.md` covering the 20-section outline, linking to the existing docs.

---

## Phase 5 — Future: Telegram bot (not scheduled)

- A separate `bot/` service (aiogram) using the API with a service account, behind the `telegram_enabled` flag.
- Features: availability, booking confirmation/reminders, KHQR QR sent in chat (same Phase 2 adapter), OTP channel.
- Account linking via a one-time code with consent, plus a privacy-policy update.
- Webhook secret token, plus rate limits.

---

## Order and estimate

`P0 merge → P1 legal → P2 KHQR → P3 admin/dev dashboard → P4 infra` ≈ **17–18 working days**. P1 and P2 are independent after P0 and can swap order if payments are more urgent.

## Before starting

- Back up the Supabase DB (needed for the P0 migration check).
- Add the Bakong token to `.env` yourself. Do not paste it into chat.
- Confirm the license choice (proprietary) or name another.
