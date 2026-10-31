# CLAUDE.md

Luma Haven = single-property hotel **MIS** (Django/DRF + PostgreSQL 17, Vue 3 + TS, Celery/Redis).

## Token-saving read order (stop as soon as you have enough)

1. `AGENTS.md` — stack, commands, invariants, definition of done (authoritative).
2. `docs/HANDOVER.md` — what works, what is fake, risks, next steps.
3. `docs/IMPLEMENTATION_PLAN.md` — approved phased plan (start here for new work); `ROADMAP_PLAN.md` is background.
4. Topic docs only when needed: `docs/PAYMENTS.md`, `docs/PERMISSIONS.md`, `docs/TESTING.md`, `docs/DECISIONS.md`, `docs/INDEX.md`.

**Do not read `README.md` (≈1,300 lines) unless asked.** Prefer `grep -n` and ranged reads on
`backend/core/views.py` (≈1,700 lines) and `admin.py`; read `models.py` / `services.py` whole only when changing them.

## Hard rules (summary — details in AGENTS.md)

- Money = integer minor units + currency. Dates = half-open `[arrival, departure)`.
- State changes live in `core/services.py` inside transactions; views validate/authorize then call services.
- Every model change needs a migration (`makemigrations --check` must pass).
- Tests only on disposable Postgres `127.0.0.1:55432` — **never the Supabase DB**. Never print `.env`.
- Payments are an emulator until KHQR lands; Hotel is a singleton — don't claim multi-tenant.
- Branches `feat/hotel-management-system` and `main` have diverged — never merge/rebase without the owner.

## Quick commands

```bash
.venv/bin/python backend/manage.py check
env DATABASE_URL=postgresql://hims_test:local-integration-only@127.0.0.1:55432/postgres \
  .venv/bin/python -m pytest -c backend/pytest.ini backend/tests -q
npm --prefix frontend run typecheck && npm --prefix frontend run build
```

After finishing work, update `docs/IMPLEMENTATION_STATUS.md` and `docs/HANDOVER.md`, and add an entry to `docs/DECISIONS.md` for any material choice.
