# Roadmap plan — draft for owner review

**Status:** proposal (31 Oct 2026). Nothing in this file has been implemented yet. It builds on `docs/HANDOVER.md` and `docs/PAYMENTS.md`.

Phases are ordered by dependency: **P0** must land before real guests use the system.

| Phase | Theme | Why first |
|---|---|---|
| P0 | Legal pages + consent + data-rights (§2) | Required before collecting real guest data or real payments |
| P1 | Bakong KHQR payments (§4) | Replaces the emulator; main business gap |
| P2 | Admin CMS (§3) | Lets the hotel edit content/legal text without deploys |
| P3 | IT infrastructure hardening (§5) | Production readiness: rate limits, backups, monitoring |
| P4 | Telegram bot payment/notifications (§6) | Future feature, reuses P1 adapter |

---

## 1. Project requirement framing: MIS + IT infrastructure

The project must show both of these:

- **MIS loop** (already in place): transaction → validated record → KPIs/reports → decision support. New features have to feed this loop:
  - KHQR adds **payment channel mix**, **QR expiry/abandon rate** and **reconciliation exceptions** to the manager dashboard and the `cash-reconciliation` report.
  - Consent/CMS add a **compliance report**: consent counts by version, open data-subject requests, and overdue requests (SLA).
  - Telegram adds **channel attribution** (web vs Telegram bookings).
- **IT infrastructure:** a documented deployment topology, security controls, backup/DR, monitoring and an incident runbook (§5). New doc: `docs/INFRASTRUCTURE.md`.

### Mapping to the requested 20-section project spec

Rather than growing `README.md`, put a short spec at `docs/PROJECT_SPEC.md` that **links** to existing docs. That saves tokens and avoids duplicated text.

| # | Section | Source |
|---|---|---|
| 1–2 | Overview, objectives | new, short (in PROJECT_SPEC) |
| 3 | Technology stack | AGENTS.md table |
| 4 | User roles | PERMISSIONS.md (+ new `content_editor`, `dpo` roles) |
| 5–6 | Main features, guest workflows | IMPLEMENTATION_STATUS.md, DEMO.md |
| 7 | Business rules | AGENTS.md "Architecture rules" + DECISIONS.md |
| 8 | System architecture | new INFRASTRUCTURE.md diagram |
| 9 | Database design | models.py → generated ERD (`docs/ERD.md`, Mermaid) |
| 10 | API design | `/api/schema/` (drf-spectacular), with an endpoint list summary |
| 11 | Frontend pages | AGENTS.md routes + new legal/CMS routes |
| 12 | Management dashboard | MIS_DEMONSTRATION.md |
| 13 | Security requirements | new SECURITY.md (merge AGENTS rules + §5 + PAYMENTS security) |
| 14 | Project structure | AGENTS.md repo map |
| 15 | Development setup | AGENTS.md "Run it" |
| 16 | Testing | TESTING.md |
| 17 | Roadmap | this file |
| 18 | Future improvements | §6 + HANDOVER gaps |
| 19 | Contribution guidelines | new CONTRIBUTING.md (branching, DoD from AGENTS.md) |
| 20 | License | **owner decision** (proprietary vs MIT) |

---

## 2. P0 — Terms, agreements, privacy policy and user-data handling

Cambodia does not yet have a comprehensive data-protection law in force. A draft Personal Data Protection Law exists, and the e-Commerce Law (2019) and Consumer Protection Law (2019) apply now. Write the policies to GDPR-style principles so they still hold when the PDP law lands. **A local lawyer must review the final text**; the repo ships templates only.

### Documents (versioned, bilingual EN / Khmer)
1. **Terms & Conditions** (website use, booking contract).
2. **Booking & Cancellation Policy** (deposits, no-show, refunds, check-in/out times, ID requirement).
3. **Privacy Policy**: what data is collected (name, email, phone, passport/ID if collected, stay history, payment refs; **no card data**), purpose, legal basis, retention, processors (Supabase, email provider, Bakong/bank, Telegram later), cross-border transfer (Supabase Singapore), rights, and contact.
4. **Cookie notice**: only strictly necessary session/CSRF cookies today, so a banner is informational. Add a consent toggle if analytics are added.
5. **Staff Acceptable Use & Confidentiality Agreement**, accepted at first staff login.
6. **Payment terms**: KHQR, the currency, and what happens on QR expiry or a late payment.

### Backend
- `LegalDocument(kind, version, language, title, body_markdown, effective_at, published, created_by)`. It is immutable once published; a new version replaces it.
- `ConsentRecord(subject_type guest|staff, subject_id, document FK, accepted_at, ip_hash, user_agent_hash, method)`. It is append-only and audited.
- Booking creation **requires** acceptance of the current T&C + privacy versions. The service rejects it if the accepted IDs are missing or stale.
- `DataSubjectRequest(guest, type access|export|rectify|delete, status, due_at, handled_by)` + a service:
  - **Export:** JSON/CSV of the guest's records.
  - **Delete:** anonymize PII (keep financial records for the statutory retention period). Never hard-delete folios.
- **Retention:** a Celery beat task anonymizes guests with no activity for N years (setting) and purges expired OTPs and quotes.
- API: `GET /api/v1/legal/<kind>?lang=`, `POST /api/v1/consents`, `POST /api/v1/me/data-requests`.

### Frontend
- Routes `/legal/terms`, `/legal/privacy`, `/legal/cancellation`, `/legal/cookies`, with footer links on the guest site.
- A required checkbox on booking (links open in a modal), storing the accepted versions.
- "My data" panel on `/booking/:id`: request export/deletion.
- Staff: first-login agreement gate.

### Tests
Booking without consent → 400. A new version requires re-consent. The export contains only that guest's data. Delete anonymizes PII but leaves folio totals intact.

---

## 3. P2 — Admin panel CMS

Goal: hotel staff edit public content and legal text **without a code deploy**, inside the existing `/admin` Vue portal. The Django admin stays for superusers only.

### Scope
| Content | Model | Notes |
|---|---|---|
| Pages (About, Contact, FAQ) | `CmsPage(slug, title, body_markdown, status draft/published, seo_title, seo_description, published_at)` | Markdown, sanitized on render (no raw HTML) |
| Homepage sections / banners | `CmsBlock(key, position, content JSON, status)` | Hero, highlights, promos |
| Room-type marketing | extend `RoomType` (description, amenities JSON) | Pricing stays in rates, not CMS |
| Media | existing `VisualAsset` + `MediaAssetManager.vue` | Reuse; add alt-text required |
| Legal docs | `LegalDocument` from §2 | Publish = new version |
| Announcements / promotions | `CmsBlock` with date window | |
| Bilingual | `language` field per item (en/km) | Fallback to en |

### Workflow and controls
- Roles: new `content_editor` (draft) and `admin` (publish). Publishing a legal doc needs the admin role; optionally a second approver, mirroring the refund two-person rule.
- Every save/publish/unpublish is written to `Audit`; there is a revision history with restore.
- Preview via a signed preview token; public API serves `published` only.
- Public API is read-only and cached (`GET /api/v1/cms/pages/<slug>`, `/cms/blocks`). Admin CRUD lives under `/api/v1/admin/cms/...` with CSRF and role checks.

### Frontend
- `features/admin/cms/`: `CmsPagesList.vue`, `CmsPageEditor.vue` (markdown + live preview), `CmsBlocksEditor.vue`, `LegalDocsEditor.vue`, all as tabs in `AdminView.vue`.
- Guest pages read CMS content with fallback to the current hard-coded copy in `frontend/src/data/`.

### MIS tie-in
The admin dashboard shows content freshness, the pending drafts, and the legal versions in force.

---

## 4. P1 — Bakong KHQR payments

The detailed design already exists in **`docs/PAYMENTS.md`**. This section only adds the delivery plan.

**SDK decision (needs your confirmation):** `mrrhak/khqr_sdk` is a **Flutter/Dart** package. It cannot run inside Django or Vue. Options:
- **A (recommended):** the backend uses the Python `bakong-khqr` package (same KHQR/EMVCo spec). `khqr_sdk` is used later only if you build a Flutter mobile/staff app.
- **B:** a small Dart microservice wrapping `khqr_sdk`. This adds infrastructure and is not recommended.

### Steps
1. Prerequisites (owner): a Bakong merchant account/token from NBC or a bank, the merchant account ID, and a sandbox.
2. `core/payments/` adapter (`base`, `development`, `bakong`, `factory`), selected by `PAYMENT_PROVIDER`.
3. Migration: `PaymentAttempt` provider fields (`provider`, `provider_qr`, `provider_md5`, `expires_at`, …).
4. Endpoints: create a payment session (server computes the amount from the folio) and poll its status. Settlement is server-side only, idempotent via `bakong:{md5}`.
5. Celery task: sweep pending attempts (backup to browser polling), expire them, and release holds.
6. `CheckoutView.vue`: QR via `qrcode.vue`, amount, countdown, status polling, success redirect.
7. Reconciliation: daily report attempt ↔ Bakong status, with exceptions shown in `cash-reconciliation` and Decision Support.
8. Tests with a fake provider (no network in CI), plus a manual sandbox checklist.
9. Refunds stay a manual bank process recorded via the existing two-person workflow.

---

## 5. P3 — IT infrastructure hardening

| Area | Plan |
|---|---|
| Topology | Reverse proxy (Caddy/Nginx, TLS) → Gunicorn backend; built static Vue; Celery worker + beat; Redis; managed Postgres. Document with a diagram in `docs/INFRASTRUCTURE.md` |
| Environments | dev (local/Supabase dev), staging, prod. Separate DBs and secrets, plus `.env.example` |
| Security | Rate limiting on login/OTP/payment endpoints (django-ratelimit or DRF throttles), security headers/CSP, `DEBUG=false`, secret rotation, dependency audit (`pip-audit`, `npm audit`) in CI |
| Data | Daily automated backups + restore test; PITR on managed Postgres; retention task from §2 |
| Reliability | Durable Outbox delivery with retries/backoff; health/readiness endpoints already exist, so wire them to the container healthchecks |
| Monitoring | Structured logs (no PII/secrets), Sentry (PII scrubbing on), uptime check, Celery queue depth |
| Ops docs | Incident runbook, data-breach procedure (links to the privacy policy), access review for staff accounts |

---

## 6. P4 (future) — Telegram bot

- Bot (aiogram or python-telegram-bot) runs as a **separate service** calling the existing API with a service account. It holds no business logic of its own.
- Features: check availability, receive booking confirmation and a reminder, **pay by KHQR** (the bot sends the QR image from the P1 adapter; settlement is still via the server poll/sweeper), and an OTP/notifications channel as an alternative to email.
- Account linking: one-time link code from `/booking/:id` → bot. Store `telegram_chat_id` on Guest only with consent (privacy policy update).
- Webhook secured with the Telegram secret token, plus rate limiting.

---

## 7. Decisions needed from you

1. KHQR SDK route: **A (Python `bakong-khqr`)** or B (Dart service)?
2. Do you have a Bakong merchant token/sandbox yet?
3. Target branch: keep working on `feat/hotel-management-system`, or reconcile with `main` first?
4. Legal text languages: EN + Khmer? Who reviews legally?
5. Guest data retention period (e.g. 3 or 5 years after last stay)?
6. License for section 20?
7. Is the CMS editor Markdown (recommended, safe) or rich-text WYSIWYG?
