# IT infrastructure

How Luma Haven runs in production, and what each piece is for. **Status:** designed and committed (31 Oct 2026); the production compose file and images have not yet been deployed or load-tested. Local development is unchanged (`compose.yaml`).

## Topology

```mermaid
flowchart LR
  G[Guests / staff browsers] -->|HTTPS 443| W
  subgraph Host["One Linux host (Docker Compose, compose.prod.yaml)"]
    W["web: Caddy<br/>TLS, headers, CSP, static Vue build, /media"]
    B["backend: gunicorn + Django/DRF<br/>(non-root, 3 workers)"]
    K["worker: Celery"]
    T["beat: Celery scheduler"]
    R[("redis<br/>broker + cache + rate-limit counters")]
    BK["backup: daily pg_dump"]
    V1[("media volume")]
    V2[("backups volume")]
  end
  W -->|/api/*| B
  B --> R
  K --> R
  T --> R
  B -->|SQL over TLS| DB[("Managed PostgreSQL 17<br/>(Supabase, Singapore)")]
  K --> DB
  BK --> DB
  B -.->|status check| BAK["Bakong API (Cambodian IPs only)"]
  K -.-> BAK
  B -.->|scrubbed errors| S["Sentry (optional)"]
  W --- V1
  B --- V1
  BK --- V2
  B -. read-only .- V2
```

- Only **Caddy** is exposed (ports 80/443). Django, Redis and the worker have no published ports.
- Django's own `/admin/` site is **not** proxied; `/admin` in the browser is the Vue admin portal.
- The database is external and managed. The app needs the `btree_gist` extension (GiST exclusion constraint) and PostgreSQL 17 (`pg_dump` in the backup image matches).

## Environments

| Environment | Purpose | Database | Payments | Notes |
|---|---|---|---|---|
| Local dev | day-to-day work | Supabase dev project | development emulator | `compose.yaml`, `APP_ENV=development`, throttling off |
| CI / disposable | tests | PostgreSQL on `127.0.0.1:55432` | fake provider | never the Supabase demo DB ([TESTING.md](TESTING.md)) |
| Staging (recommended) | rehearse releases and Bakong sandbox | **separate** project | Bakong with a test account | copy of production config, different secrets |
| Production | real guests | production project | `bakong` | `APP_ENV=production`; startup refuses unsafe settings |

Production refuses to start if: the secret key is weak, `DJANGO_ALLOWED_HOSTS` is missing or a wildcard, `FRONTEND_ORIGIN` is not `https://`, or the payment provider is `development`.

## Deploying

1. Provision a host with Docker, a DNS A record for the hostname, and ports 80/443 open. **The host (or an egress proxy) must have a Cambodian IP address** — the NBC Bakong API rejects other regions (see [PAYMENTS.md](PAYMENTS.md)).
2. `cp .env.production.example .env.production` and fill every value (generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Never commit the file.
3. `docker compose -f compose.prod.yaml --env-file .env.production up -d --build`
4. `docker compose -f compose.prod.yaml exec backend python manage.py migrate` (first deploy and every release with migrations).
5. Create the first administrator: `docker compose -f compose.prod.yaml exec backend python manage.py create_admin --username <name>` (prompts for the password; or set `LUMA_ADMIN_PASSWORD` for one non-interactive run). Do **not** run `seed_demo` in production.
6. Check: `https://<host>/api/v1/ready` returns `{"status":"ready"}`, then sign in to `/admin` → Developer console → System health (database, Celery, backup all green).

Release: pull, rebuild, `up -d`, run migrations. Roll back by redeploying the previous commit; restore the database from backup only if a migration damaged data.

## Secrets

| Secret | Where | Rotate |
|---|---|---|
| `DJANGO_SECRET_KEY` | `.env.production` | yearly or after exposure — signs out everyone |
| `DATABASE_URL` password | `.env.production` + provider dashboard | after any exposure (a past incident leaked it in a debug traceback; keep `DEBUG=false`) |
| `BAKONG_TOKEN` | `.env.production` | per NBC expiry/renewal and after exposure |
| `SENTRY_DSN` | `.env.production` | after exposure |

Secrets are only environment variables on the server. They are never in the repository, images (`.dockerignore`), `VITE_*` variables, logs, or the Developer Console (which shows only set/unset).

## Backups and recovery

- `backup` service runs `scripts/backup_db.sh` daily: custom-format `pg_dump` into the `backups` volume, SHA-256 file, 30-day retention (`BACKUP_KEEP_DAYS`), atomic `last_backup.json` marker. The Developer Console shows the marker; it turns red if the last good backup is older than 26 hours.
- **Also enable the database provider's own point-in-time recovery**; daily dumps alone mean up to 24 h of data loss. Copy the `backups` volume off the host regularly (object storage or another machine) — a dump on the same host does not survive losing the host. *This off-host copy is not automated yet.*
- **Restore drill, monthly:** start a disposable PostgreSQL ([TESTING.md](TESTING.md)) and run `DRILL_DATABASE_URL=postgresql://hims_test:...@127.0.0.1:55432/postgres scripts/restore_drill.sh`. It verifies the checksum, restores into a throwaway database, checks table and row counts, drops it, and writes `last_restore_drill.json` (shown in the console). The script refuses non-local servers and the production URL.
- Real restore: create a new empty database, `pg_restore --no-owner --dbname=<new> <dump>`, point `DATABASE_URL` at it, run `migrate`, start the stack. Record the time and the data gap in the incident log.

Targets (proposed, confirm with the owner): RPO 24 h (improves with PITR), RTO 4 h.

## Monitoring

| Signal | How |
|---|---|
| Uptime | external monitor (e.g. UptimeRobot) on `GET https://<host>/api/v1/ready` every minute; alert on 503/timeout |
| Liveness vs readiness | `/api/v1/health` = process is up; `/api/v1/ready` = database answers. Used by container health checks |
| Logs | JSON to stdout with a per-request `request_id` (also returned as `X-Request-ID`); emails and long tokens are scrubbed. Use `docker compose logs` or ship to your log service |
| Errors | `ErrorEvent` table in the Developer Console (90-day retention) and optional Sentry (`SENTRY_DSN`; cookies, bodies, headers, users, emails are stripped before sending) |
| Jobs | Celery task outcomes in the console (30-day retention); alert "KHQR attempts not reconciled" in Decision Support |
| Security | failed sign-ins and active sessions in the console; per-account lockout after 5 failures / 15 min |

## Capacity and limits

Sized for one hotel: 3 gunicorn workers, 2 Celery processes, a single host. Rate limits (per client IP, per minute unless stated): login 20, OTP 10, booking/quote 30, privacy requests 10/hour, payment polling 120. Upload limit 12 MB at the proxy. Scaling beyond one host would need shared media storage (object storage) and a managed Redis — not implemented.

## Known gaps

- Media uploads live in a local volume (single host).
- Backups are not copied off the host automatically; no alerting channel is wired (the console and uptime monitor are manual/external).
- Outbox delivery (email/SMS/Telegram) has no adapter; production needs a real `EMAIL_BACKEND` configuration before OTP emails reach guests.
- Images and compose file were validated by CI configuration only, not yet on a real server.
