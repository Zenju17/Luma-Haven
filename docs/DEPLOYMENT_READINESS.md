# Deployment readiness review — 2 November 2026

**Follow-up:** the university-demo changes and deployment are documented in
[VERCEL_DEMO.md](VERCEL_DEMO.md). The assessment below records the original project
state before those changes; production limitations still apply.

Reviewed commit: `7db03b0`. Scope: repository deployment architecture, production settings,
frontend build, backend checks, automated journeys, and current Vercel documentation.
This is a readiness assessment, not a production release or a complete security audit.

## Verdict

**Not ready to deploy the complete application to Vercel Hobby as currently configured.**
The Vue build is viable, but routing, email delivery, upload storage, scheduling, and
environment configuration need work. A personal university demonstration can use Hobby;
real hotel business use requires a plan that permits commercial use.

Vercel now supports Django, Celery adapters, Services, and Daemons. The issue is not a
blanket lack of Python or worker support: this repository currently targets Docker
Compose and has no Vercel configuration or verified Vercel deployment.

## Findings, ordered by release impact

| Priority | Finding and evidence | Required action |
| --- | --- | --- |
| Blocker | `frontend/src/services/api.ts` uses `/api/v1`; `frontend/vite.config.ts` proxies `/api` and `/media` only in the development server. No Vercel routing configuration exists. | Route `/api/*` to Django and `/media/*` to durable storage before the SPA fallback. Support direct navigation to `/staff`, `/admin`, `/booking/*`, and other history routes. |
| Blocker | `backend/config/settings.py:93–97` selects console email in production. `core/views.py:266` sends OTPs from `noreply@localhost`. | Configure and test real email delivery and a verified sender. Environment variables alone will not change the hard-coded backend. |
| Blocker | `MEDIA_ROOT` is local disk; `VisualAsset.image` uses Django's default storage. Production Compose relies on a shared media volume. | Use durable object storage with a Django storage adapter if hosting Django on Vercel. Migrate existing media and URLs; do not use temporary disk for persistent uploads. |
| Blocker | Upload endpoints accept 10 MiB images (`core/views.py:1615,1693`); Vercel Functions accept at most 4.5 MB per request, including multipart overhead. | Reduce the application limit below the platform limit, or implement authorized direct uploads to object storage. |
| Blocker | Celery Beat schedules payment polling every 30 seconds and hold expiry every 60 seconds (`settings.py:112–117`). Hobby Cron runs each job at most daily. | Keep a suitable external scheduler/worker, or redesign task execution with Vercel primitives and prove all required intervals. Existing Redis/Celery configuration is not a Vercel queue adapter. |
| Blocker for sustained free hosting | Daemons are available on Hobby, but their current quota is 420 GB-hours/month. One 1 GiB daemon running for 30 days needs about 720 GB-hours; separate worker and beat instances need more. Redis and backups are additional dependencies. | Do not assume continuously running daemons will remain available all month for free. Select a task design or host that fits the intended uptime and budget. |
| Blocker for a public simulated demo | `settings.py:9–10` refuses production with the development payment provider. Development mode also changes cookie security and throttling defaults. | Define an explicit secure demo environment with synthetic data and clearly simulated payments. Do not simply weaken production guards or use the development defaults on a public site. |
| Blocker for real money | Bakong has no recorded real-provider verification. Refund settlement remains manual; provider refunds/reconciliation are incomplete. | Verify QR creation, payment, duplicates, expiry, late payments, refunds, and provider connectivity from the actual deployment. Repository documentation reports Cambodian egress restrictions for official NBC tokens; confirm this with the chosen provider/token before choosing a region. |
| High | `core/payments/factory.py:19–25` lets a persisted `bank_payments=False` override `PAYMENT_PROVIDER=bakong`, even in production. | Enforce allowed providers in the factory and cover environment transitions. A mocked ORM reproduction returned `environment=production configured=bakong effective=development`. This can strand checkout on an emulator that production disables; it does not establish that fake settlement is possible in production. |
| High | Cross-origin frontend/backend deployment would retain `SameSite=Lax` cookies, and settings do not add `X-Portal` to CORS allowed headers. | Prefer a same-origin API route. If using cross-origin requests, explicitly validate CORS preflights, session and CSRF cookies, browser third-party-cookie behavior, and all three portal sessions. |
| High | Production Compose backup files and `/backups/last_backup.json` assume a host volume. Vercel does not run the Compose stack. | Configure independent database and media backups, monitoring, and a restore drill. Confirm the managed database's actual backup entitlement. |
| High | CI permits production image build failures (`.github/workflows/ci.yml:89`) and dependency audit failures (`:61`). | Make release-critical build checks mandatory after verifying them. A green workflow currently does not prove the production images built. |
| Medium | Production `check --deploy` emits numerous drf-spectacular schema warnings: missing serializer inference and operation-ID collisions. | Complete API schema annotations; distinguish schema warnings from runtime failures. |
| Medium | `core/tasks.py:11–14` deliberately leaves outbox events pending because no delivery adapter exists. | Implement delivery/retries for any promised asynchronous notifications; monitor queue age. |

## Practical deployment paths

### Personal university demo

The least disruptive first step is Vercel for the Vue frontend, with same-origin
rewrites to a separately hosted Django API. Keep PostgreSQL on a separate demo database,
provide durable uploads, real OTP email, and an explicit secure simulated-payment mode.
Keep Celery/Redis/Beat on a host that can run them, or deliberately redesign and test
the demo's scheduling. Backend hosting and related services have their own costs/limits;
Vercel Hobby does not make the entire system free.

Frontend project settings would be Root Directory `frontend`, framework Vite,
Build Command `npm run build`, and Output Directory `dist`. API/media rewrites must
precede the SPA fallback. Caddy currently supplies security headers and CSP; preserve
the intended headers in the replacement hosting configuration.

An all-Vercel variant needs Services routing for frontend and Django plus a deliberate
queue/scheduler design. It is an implementation project, not just setting environment
variables or uploading `compose.prod.yaml`.

### Real hotel operation

Hobby is restricted to personal, non-commercial use. Use an eligible paid plan or
another suitable host, close the payment/email/storage findings, rehearse migrations
and rollback against a separate staging database, and test the actual HTTPS origin.
The existing Compose topology may require less application change, but its images,
runtime health, backups, and restore path still need verification.

## Verification

- Frontend production build (includes Vue TypeScript check): passed.
- E2E TypeScript check: passed.
- Django `check`: passed.
- `makemigrations --check --dry-run`: passed with access to disposable PostgreSQL;
  no changes detected.
- Production `check --deploy` using synthetic configuration: completed with schema
  warnings; this does not verify real credentials, network access, or deployed HTTPS.
- Backup and restore shell scripts: syntax checks passed.
- Playwright browser journeys: **4 passed** (1.2 minutes), covering the guest/staff
  workflow, portal separation, manager MIS, and CMS publishing.
- Full backend run: **109 passed, 1 failed** in 143.96 seconds. The failing test was
  `test_real_sdk_generates_local_qr_with_exact_amount`: the local virtual environment
  lacked `bakong-khqr`, already declared in both requirements files. Installed the
  declared `bakong-khqr==0.6.5`; the complete Bakong test file then passed **14/14**,
  including that failure. The full suite was not repeated after installation.
- Python dependency metadata: `uv pip check` passed. This checks installed-package
  compatibility, not security advisories or exact lockfile parity.

Tests use only disposable PostgreSQL on `127.0.0.1:55432`. Supabase data and credentials
were not used. Local Python is 3.14 and Node is 24; CI targets Python 3.13 and Node 22,
so a successful local run does not replace the pinned-runtime CI checks.

Not verified: a real Vercel build/deployment, production container builds, a fresh
dependency vulnerability audit, provider email delivery, real Bakong settlement,
production restore, load/concurrency limits, or deployed mobile/light/dark behavior.

## Current official platform references

Checked 2 November 2026; beta features and quotas can change.

- [Hobby eligibility](https://vercel.com/docs/plans/hobby)
- [Django deployment and Services](https://vercel.com/docs/frameworks/full-stack/django)
- [Vite SPA routing](https://vercel.com/docs/frameworks/frontend/vite)
- [Celery integration](https://vercel.com/docs/frameworks/backend/celery)
- [Daemons availability](https://vercel.com/docs/daemons)
- [Daemon quotas and ephemeral storage](https://vercel.com/docs/daemons/limits)
- [Cron frequency limits](https://vercel.com/docs/cron-jobs/usage-and-pricing)
- [Function request limits](https://vercel.com/docs/functions/limitations)
