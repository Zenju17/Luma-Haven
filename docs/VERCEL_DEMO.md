# Public app deployment on Vercel

**Public production URL:** https://luma-haven-zenju17.vercel.app
(also https://luma-haven-delta.vercel.app).
Vercel reports **READY**, 2 November 2026. Production deployment:
`dpl_6ZTf4wvGpPra1gskD8bQonSSJrwz`, built from Git commit
`557bd48e426ed2fb2fef7818347a67f745700377`; project `luma-haven` in `zenju17`.
Hosting target is explicitly `production`; Vercel sign-in protection is disabled.
Build completed in approximately 50 seconds. Readiness here is Vercel's build state;
browser journeys were verified locally, not against the deployed URL.

The presentation uses Vercel Services (beta): Vite serves the Vue frontend and
Django handles `/api/*` on the same origin. The frontend's own rewrite supports
direct navigation to every SPA route. Singapore (`sin1`) keeps the API near Supabase.

## Runtime configuration

The user requested a normal public production deployment after the initial preview.
Production variables are now configured independently, with a new production signing
key. Preview configuration remains separate. The hosting environment is Production;
the runtime's simulated payment/verification behavior remains until real payment
and email providers are configured. Changing the hosting target does not enable them.

| Variable | Value |
| --- | --- |
| `APP_ENV` | `demo` |
| `DJANGO_DEBUG` | `false` |
| `PAYMENT_PROVIDER` | `development` |
| `DATABASE_MEDIA` | `true` |
| `DATABASE_CONN_MAX_AGE` | `0` |
| `VITE_PRESENTATION_DEMO` | `false` in Production: hides the presentation banner |
| `DJANGO_ALLOWED_HOSTS` | Explicit project hostname; Vercel deployment hostnames are added from system variables |
| `FRONTEND_ORIGIN` | `https://luma-haven-zenju17.vercel.app`; exact Vercel deployment origins are also trusted for CSRF |
| `DATABASE_URL` | Existing Supabase demo database; Secret |
| `DJANGO_SECRET_KEY` | Independent randomly generated deployment key; Secret |
| `REDIS_URL` | Empty for this serverless demonstration |

`APP_ENV=demo` retains HTTPS redirects, Secure/HttpOnly sessions, CSRF, hostname
validation, roles, and throttling. It forces simulated payments regardless of old
database flags. Production still forbids the emulator. Secrets never enter `VITE_*`.
The `.vercelignore` excludes local secrets, credentials, media, backups and traces.
Deployments do not automatically run migrations or seed data.
`django.contrib.staticfiles` is enabled so Vercel's automatic `collectstatic` runs;
the local dry-run also passed.

## Presentation journey

1. Open `/`, choose today and tomorrow, and reserve an available room with fictional details.
2. Choose **Pay balance (simulation)** and **Simulate success**.
3. On the booking page choose **Verify demo booking**. This deliberately simulates
   verification, only after payment and only in the browser session that created
   the booking. It never reveals an OTP or grants access to another booking.
4. Check in, request a service, complete it through `/staff`, then check out.
5. Complete housekeeping inspection in `/staff` and show live MIS in `/manager`.

Existing staff/admin credentials still apply. Find them in the ignored private
credential file; do not publish them or include them in slides. Portal sessions
remain separate. `/verify` retains the OTP flow; hosted email delivery is not
configured, so use the labelled booking-page shortcut for the presentation.

## Images and database preparation

`DatabaseMediaStorage` stores bounded image bytes in `core_mediafile` and serves
`/api/v1/media/<name>`. This gives the small presentation durable uploads without
another paid service. Uploads are limited to 3 MiB, below Vercel's 4.5 MB request
limit with room for multipart overhead. MIME types come from decoded images.
This is a small-demo storage choice, not the production media architecture.

On 2 November 2026, before deploying:

- Saved a private custom-format database dump in ignored `backups/`.
- Verified tables, fields and eight constraints for the legacy organization migration;
  recorded its renamed `0005` entry while retaining the legacy history row.
- Applied migrations `0006` through `0009` and imported all 29 referenced images with
  `python backend/manage.py import_presentation_media`.
- Did not reset/reseed the hotel or change existing account passwords.

The import command skips existing files and refuses missing referenced images.

## Limits

- Celery/Beat are not deployed. Holds are also released during availability, quote
  and reservation operations; dashboards/reports calculate live. Nightly snapshots,
  scheduled retention and background bank polling do not run.
- Payments and demo verification are simulated. Use fictional details and no real money.
- Without Redis, throttle counters are per process; database-backed login lockout still applies.
- Vercel sign-in protection was disabled at the user's request on 2 November 2026.
  Anyone with the deployment link can open the university demo; application-level
  staff/admin authentication, role checks, and CSRF remain in place.
- The preparation backup is local, not a scheduled production backup service.
- The current Production deployment uses the Git source at the commit above.
  The repository is connected to Vercel. Future production releases must use the
  intended production branch or an explicitly targeted Production deployment.

## Verification

All tests used disposable PostgreSQL on `127.0.0.1:55432`, never Supabase:
116 backend tests passed, plus four presentation-mode Playwright journeys, Vue
typecheck, E2E typecheck, build, Django check and migration consistency.

Run the browser journeys with `E2E_PRESENTATION_DEMO=true` and the documented
`E2E_DATABASE_URL`. The local HTTP harness overrides only the presentation interaction;
separate backend tests verify hosted HTTPS security and exact preview hostnames.
