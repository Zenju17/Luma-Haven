# Project specification

Short map of the 20-section project outline. It links to the living documents instead of duplicating them, so it does not go stale. Status of every feature is in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and [HANDOVER.md](HANDOVER.md).

## 1. Project overview
Luma Haven is a **single-property hotel Management Information System (MIS)** for a boutique hotel in Phnom Penh. The loop it implements: *hotel transaction → validated database record → management information → management decision*.

## 2. Project objectives
- Take reliable online bookings with no double-booking and clear payment status.
- Run daily operations (arrivals, rooms, housekeeping, maintenance, requests) from one system.
- Give managers trustworthy KPIs, reports and prescriptive alerts ([MIS_DEMONSTRATION.md](MIS_DEMONSTRATION.md)).
- Handle guest data lawfully and transparently (consent, rights requests, retention).
- Provide an operable, secure IT infrastructure ([INFRASTRUCTURE.md](INFRASTRUCTURE.md)).

## 3. Technology stack
Django/DRF, PostgreSQL 17, Celery + Redis, Vue 3 + TypeScript + Tailwind 4 + TanStack Query, Caddy, Docker Compose, Bakong KHQR (Python `bakong-khqr`). Table in [AGENTS.md](../AGENTS.md).

## 4. User roles
Guest (booking-scoped, OTP), Reception, Housekeeping, Accountant, Manager, Administrator, Content editor, Developer. Matrix: [PERMISSIONS.md](PERMISSIONS.md).

## 5. Main features
Guest booking and self service; staff operations; refunds with two-person approval; manager dashboard and five MIS reports; legal documents and consent; Bakong KHQR payments; admin CMS; developer console. Detail: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

## 6. Guest workflows
Search → quote (10 min) → hold (15 min) → accept terms → pay (QR) → confirmation → OTP verify → check-in → service requests → checkout; plus "My data" export/correction/deletion. Walk-through: [DEMO.md](DEMO.md).

## 7. Business rules
Money in integer minor units; half-open `[arrival, departure)` stays; GiST exclusion for room overlap; state changes in transactions; folio version guards checkout; late payments handled without silent loss ([AGENTS.md](../AGENTS.md), [DECISIONS.md](DECISIONS.md), [PAYMENTS.md](PAYMENTS.md)).

## 8. System architecture
Topology diagram and environments: [INFRASTRUCTURE.md](INFRASTRUCTURE.md). Repository map: [AGENTS.md](../AGENTS.md).

## 9. Database design
Generated ERD: [ERD.md](ERD.md). Governance notes from the database workstream: [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md) and related `DATABASE_*.md` files.

## 10. API design
`/api/v1/`, session cookies + CSRF, JSON. Endpoint index: [API.md](API.md); live schema `/api/schema/`, Swagger UI `/api/docs/`.

## 11. Frontend pages
`/` guest site, `/rooms`, `/gallery`, `/spaces`, `/booking/:id`, `/checkout/:id`, `/verify`, `/legal/:kind`, `/p/:slug` (CMS), `/staff`, `/manager`, `/admin`.

## 12. Management dashboard
Manager Intelligence Dashboard (8 KPIs, trends, room-type profitability, Decision Support alerts incl. KHQR reconciliation) and the Payments reconciliation screen: [MIS_DEMONSTRATION.md](MIS_DEMONSTRATION.md).

## 13. Security requirements
[SECURITY.md](SECURITY.md) (controls, known gaps), [INCIDENT_RUNBOOK.md](INCIDENT_RUNBOOK.md), payment rules in [PAYMENTS.md](PAYMENTS.md).

## 14. Proposed project structure
Repository map in [AGENTS.md](../AGENTS.md); production files: `compose.prod.yaml`, `backend/Dockerfile.prod`, `deploy/web/`, `scripts/`.

## 15. Development setup
[AGENTS.md](../AGENTS.md) "Run it"; environment variables in `.env.example` (dev) and `.env.production.example` (production).

## 16. Testing requirements
[TESTING.md](TESTING.md): pytest on a disposable PostgreSQL, Playwright journeys, typechecks, CI workflow `.github/workflows/ci.yml`. Real-Bakong sandbox checklist in [PAYMENTS.md](PAYMENTS.md).

## 17. Development roadmap
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) (phases P0–P5) and [ROADMAP_PLAN.md](ROADMAP_PLAN.md) (background).

## 18. Future improvements
Telegram bot (separate service, reuses the payment adapter), outbox delivery adapters (email/SMS), MFA, off-host encrypted backups, PDF reports, provider refunds and webhooks, multi-property tenancy (not implemented), KHR currency.

## 19. Contribution guidelines
[CONTRIBUTING.md](../CONTRIBUTING.md).

## 20. License
Proprietary, all rights reserved: [LICENSE](../LICENSE). The owner should confirm the copyright holder's legal name.
