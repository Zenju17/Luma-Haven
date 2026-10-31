# AGENTS.md — working agreement for Luma Haven

Luma Haven is a **single-property hotel Management Information System (MIS)**: Django/DRF + PostgreSQL backend, Vue 3 + TypeScript frontend, Celery/Redis workers. The product loop is: hotel transaction → validated database record → management information → management decision.

> **Read this file first.** It exists so agents do not need to load the 1,300-line `README.md`. Current state, risks and next steps are in [`docs/HANDOVER.md`](docs/HANDOVER.md); the full doc map is [`docs/INDEX.md`](docs/INDEX.md).

## Stack and entry points

| Area | Technology | Entry point |
|---|---|---|
| Backend | Python 3.13, Django, DRF, drf-spectacular | `backend/manage.py`, `backend/config/` |
| Domain logic | One Django app (`core`) | `backend/core/models.py`, `services.py`, `views.py` |
| Database | PostgreSQL 17 (Supabase in dev; `btree_gist`, GiST exclusion) | `DATABASE_URL` |
| Async | Celery worker + beat, Redis | `backend/config/celery.py`, `core/tasks.py` |
| Frontend | Vue 3, TypeScript, Vue Router, TanStack Query, Tailwind 4, Vite | `frontend/src/app/` |
| Tests | Pytest (backend), Playwright (E2E), GitHub Actions | `backend/tests/`, `frontend/tests/`, `.github/workflows/ci.yml` |

Frontend routes: `/` guest site, `/booking/:id`, `/checkout/:id`, `/verify`, `/staff`, `/manager`, `/admin`.
API prefix: `/api/v1/`; OpenAPI UI `/api/docs/`; schema `/api/schema/`; health `/api/v1/health`.

## Run it

Prereqs: a PostgreSQL `DATABASE_URL` (Supabase Session pooler, port 5432, `sslmode=require`) in the ignored `.env`, plus Docker Compose or rootless Podman + `uv`.

```bash
# Docker
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo   # empty DB only

# Fedora / Podman equivalent
uvx --from podman-compose podman-compose up --build -d
uvx --from podman-compose podman-compose exec backend python manage.py migrate

# Stop without deleting data
docker compose down        # never use -v against shared data
```

Local URLs: guest `http://localhost:5173/`, staff `http://localhost:5173/staff`, manager `http://localhost:5173/manager`, admin `http://localhost:5173/admin`, API `http://localhost:8000/api/v1/`.

## Verify changes

**Never run tests against the Supabase demo database.** Use a disposable PostgreSQL on `127.0.0.1:55432` (see [`docs/TESTING.md`](docs/TESTING.md)).

```bash
# Backend checks (needs DATABASE_URL)
.venv/bin/python backend/manage.py check
.venv/bin/python backend/manage.py makemigrations --check --dry-run
env DATABASE_URL=postgresql://hims_test:local-integration-only@127.0.0.1:55432/postgres \
  .venv/bin/python -m pytest -c backend/pytest.ini backend/tests -q

# Frontend checks
npm --prefix frontend run typecheck
npm --prefix frontend run typecheck:e2e
npm --prefix frontend run build

# Full browser journey (needs E2E_DATABASE_URL on port 55432)
cd frontend && env E2E_DATABASE_URL=... npm run test:e2e
```

Last recorded green run: **37 backend tests and 3 Playwright E2E tests** (31 Oct 2026). The backend suite now collects 44 test functions, so re-run it before claiming green; CI executes the same checks.

## Repository map

```text
backend/
  config/            settings, URLs, Celery, WSGI
  core/              models, services (domain rules), views (all endpoints),
                     decision_support, middleware, staff_passwords, tasks, admin
  tests/             pytest suite (workflow, MIS reports, roles, ports, admin, assets)
  templates/static/  lightly skinned Django admin
frontend/src/
  app/               App.vue, router.ts
  features/          guest, staff, reception, housekeeping, manager, accountant,
                     admin, media — one folder per portal/domain
  components/ layouts/ services/api.ts types/ data/
docs/                DEMO, TESTING, MIS_DEMONSTRATION, PERMISSIONS, DECISIONS, status
.github/workflows/   CI
compose.yaml         redis, backend, worker, beat, frontend (no local database)
```

## Architecture rules to preserve

- **Money** is integer minor units plus an explicit currency. Never use floats.
- **Dates** are half-open `[arrival, departure)`. Overlapping active allocations are blocked by the PostgreSQL GiST exclusion constraint `no_active_room_overlap`; application checks alone are not sufficient.
- **State transitions** for reservations, stays, folios, payments and housekeeping belong in `core/services.py` inside transactions; views validate and authorize, then call services.
- **Concurrency**: use `select_for_update()` for balance/refund/capacity changes. A folio `version` guards checkout against stale balances.
- **Sessions**: guest, staff and admin use separate HttpOnly cookies (`sessionid`, `staff_sessionid`, `admin_sessionid`). The `X-Portal` header selects a cookie jar, never authorization. Role checks still happen server-side.
- **CSRF**: every API write requires a CSRF token; the frontend refreshes it per write.
- **OTP**: six-digit codes are HMAC-hashed, expire in 5 minutes, and are never returned by the API (console/file email only).
- **Payments**: default is the **development emulator** (`/development/checkout/<uuid>`). Bakong KHQR is implemented behind `core/payments/` (`PAYMENT_PROVIDER=bakong`, see [`docs/PAYMENTS.md`](docs/PAYMENTS.md)) but is untested against the real Bakong API. No signed webhook, provider refunds or PSP reconciliation exist; settlement is server-side polling.
- **Single hotel**: `Hotel` is effectively a singleton (`Asia/Phnom_Penh`, USD). Multi-property isolation is not implemented; do not claim it is.
- **Test isolation**: pytest creates `test_*` databases and Playwright creates/drops `hims_e2e_*`; both must stay on the disposable local server.

## Conventions

- Backend: keep the `core` monolith consistent; put reusable rules in `services.py`, not in views. Add a migration for every model change (`makemigrations --check` must pass). Audit sensitive actions in the existing `Audit` model; queue side effects through `Outbox`.
- Frontend: Vue 3 Composition API with `<script setup lang="ts">`; typed API helpers in `services/api.ts`; feature folders mirror portals. Preserve existing URLs and role-gated routing. Load the project `.agents/skills/vue-*` skills for non-trivial Vue work.
- Styling: Tailwind 4 with the existing room-key visual system; test light/dark and mobile states.
- Never commit `.env`, `backend/.private-staff-passwords`, test traces, real guest data, card data, or database URIs. Seed data must remain synthetic.

## Definition of done

1. Backend logic includes validation, authorization, failure handling and a migration if needed.
2. Relevant backend tests (and an E2E journey for user-visible flows) pass on disposable PostgreSQL.
3. `manage.py check`, `makemigrations --check --dry-run`, `npm run typecheck` and `npm run build` pass.
4. Docs updated: `docs/IMPLEMENTATION_STATUS.md` for state, `docs/DECISIONS.md` for material choices, and `docs/HANDOVER.md` if the resume point changed.
