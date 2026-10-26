# Isolated workflow testing

**Do not run pytest or Playwright against the main Supabase demo project.** The backend tests create a temporary PostgreSQL database, and the browser suite creates and drops its own `hims_e2e_*` database. Both suites need a separate, disposable PostgreSQL server. The browser suite refuses non-loopback hosts, ports other than `55432`, or an admin database other than `postgres`.

## Start a disposable PostgreSQL server

With Podman installed (these commands work in fish and bash):

```sh
podman run --rm --name hims-integration-postgres \
  -e POSTGRES_USER=hims_test \
  -e POSTGRES_PASSWORD=local-integration-only \
  -e POSTGRES_DB=postgres \
  -p 127.0.0.1:55432:5432 -d docker.io/library/postgres:17-alpine
podman exec hims-integration-postgres pg_isready -U hims_test -d postgres
```

This **test-only** database is bound to localhost. It has no Supabase data or production credentials. The image may take a moment to download and initialize; wait for `pg_isready` to succeed before testing. If this image is unavailable, another PostgreSQL 17 server on the same local port with a role permitted to create databases works too.

## Run backend tests

Install locked dependencies in a local Python virtual environment if they are not installed yet:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r backend/requirements.lock
```

Run all backend tests (Django creates and drops a separate `test_postgres` database):

```sh
env DATABASE_URL=postgresql://hims_test:local-integration-only@127.0.0.1:55432/postgres \
  .venv/bin/python -m pytest -c backend/pytest.ini backend/tests -q
```

## Run the complete browser workflow

From the repository root, install the locked frontend dependencies and Playwright Chromium if needed:

```sh
npm ci --prefix frontend
npm --prefix frontend exec -- playwright install chromium
```

From `frontend/`:

```sh
env E2E_DATABASE_URL=postgresql://hims_test:local-integration-only@127.0.0.1:55432/postgres \
  npm run test:e2e
```

Playwright creates a randomly named database on that **local** server, runs migrations and an idempotent synthetic seed, then starts Django on port `8001` and Vite on `5174`. Verification emails use a private temporary file-based adapter; no OTP is exposed by the API. The browser test covers booking, simulated payment, OTP verification, guest ownership isolation, check-in, service requests, checkout, housekeeping transitions, staff role restrictions and final room readiness. On completion it drops the temporary database and removes temporary email files. Traces on failure remain in ignored `frontend/test-results/` and may contain temporary OTPs: do not publish them.

For the Vue 3 frontend production build, Vue SFC type check and Playwright test-code type check:

```sh
npm --prefix frontend run typecheck
npm --prefix frontend run typecheck:e2e
npm --prefix frontend run build
```

When finished, stop **only this disposable test database**:

```sh
podman stop hims-integration-postgres
```

The regular Supabase-backed demo application and its data are not touched by these tests. If you have not run the browser tests before, `npm --prefix frontend exec -- playwright install chromium` may prompt for missing Linux libraries; follow Playwright's dependency guidance for your distribution. In CI, the workflow provisions its own disposable PostgreSQL service.
