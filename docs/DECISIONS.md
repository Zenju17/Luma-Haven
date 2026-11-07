# Implementation decisions

- **Public hosting follow-up (2 Nov 2026):** the user explicitly requested public
  Production rather than Preview. Deploy the committed app to Vercel Production,
  attach a stable `.vercel.app` domain, disable Vercel sign-in protection, and keep
  application roles/authentication. Hide the presentation banner. Production hosting
  does not constitute real payment/email activation: the existing simulated runtime
  remains explicit until provider credentials and integration verification are available.

- **University hosting (2 Nov 2026):** Vercel Services (beta) keeps the Vue frontend
  and Django API on one origin. Explicit `APP_ENV=demo` retains hosted HTTPS/security
  settings while forcing simulated payments. Verification may be simulated only
  for a paid booking owned by the current guest browser session, with a distinct
  audit event; production and the normal OTP flow do not gain that shortcut. Small
  hotel images use bounded database storage to avoid ephemeral disks and extra paid
  services; use object storage for production scale. No persistent Celery daemons
  run on Hobby: live reports and request-time hold release support the presentation,
  while scheduled tasks remain an explicit limitation. See [VERCEL_DEMO.md](VERCEL_DEMO.md).

- The initial property is a single hotel in `Asia/Phnom_Penh`, billing in USD minor units. The hotel row stores configurable contact details, tax, deposit percentage and arrival/departure times. Policy enforcement beyond full settlement is still pending.
- One room is selected per booking. PostgreSQL `daterange` allocations are half-open and an exclusion constraint is the final arbiter of inventory collisions. A `btree_gist` extension is installed in the initial migration.
- Booking immediately creates a short-lived guest browser session to access its hold and simulated checkout. Subsequent access from another browser requires email OTP; the OTP is hashed and sent to the console email backend. A confirmed booking must be verified before check-in.
- The simulated checkout creates backend payment events and can produce pending, failed, and successful results. It is deliberately unavailable outside development. A real payment provider interface, authenticated webhooks, refunds and reconciliation are **not implemented**.
- Key handover is at reception. The QR is a generic link to the verification page and never grants physical room access.
- PostgreSQL is required for migrations and tests; SQLite does not support the exclusion constraint. The user now has a Supabase project; its PostgreSQL session pooler is the development database, while Compose starts Redis and application services. The backend and Celery containers use the same server-side `DATABASE_URL` with TLS. Transaction pooling is rejected. The frontend never connects to the database directly.
- The Supabase Data API remains disabled before Django migrations: Django owns access checks, and its `public` tables do not have Supabase RLS policies. Supabase's GitHub connection does not configure Django's database credentials.
- On Fedora, rootless Podman is installed but Docker and a Compose provider are absent. `uvx --from podman-compose podman-compose` provides a no-sudo Compose path. Fully qualified container image names prevent Podman's interactive short-name prompt; `:z` bind mount labels allow sharing backend source among the server and workers under SELinux.
- The backend currently uses one `core` Django module as an early vertical slice. Domain splitting can follow stable API boundaries; empty apps have not been generated.
- **Payments:** the intended real provider is **Bakong KHQR** (Cambodia), not Stripe. The linked `mrrhak/khqr_sdk` is Flutter/Dart and cannot run in this Django/Vue stack; the planned backend path is the Python `bakong-khqr` package behind a provider adapter. The current simulator is unchanged. See [PAYMENTS.md](PAYMENTS.md) before implementing.
- The frontend was migrated from React to Vue 3 with TypeScript, Vue Router, TanStack Vue Query, Vite and Tailwind. The existing Django/DRF REST API, PostgreSQL integrity constraints, Celery/Redis workers, and simulated payment rules remain authoritative. Routes and browser acceptance workflows are preserved.
- Guest, operational staff and administrator entry points are separate Vue routes (`/`, `/staff`, `/admin`). The guest UI does not link to privileged routes; backend role checks on `/api/v1/admin/*` remain the security boundary. The admin portal displays backend-backed settings, staff and audit records, plus partial reports and CSV exports. Staff and hotel settings remain read-only apart from development-only, audited password changes for other staff accounts.
- A development-only administrator password change mirrors the new credential in a Git- and Docker-ignored local `0600` file in addition to storing its Django hash in PostgreSQL. File writes are serialized with an OS lock, use atomic replacement and attempt compensation if the DB commit fails. The file is a temporary credential handover aid, not a production password vault; the owner should transfer credentials to a password manager and delete it.
- Staff and administrator sessions are independent Django session-store records in distinct HttpOnly cookies, while guest booking access retains the original guest session cookie. A portal header only selects the cookie for shared API routes; role and object permissions are always enforced on the backend. Old staff logins under the former shared cookie require a one-time login in the new portal.
- Frontend visual direction (using the project's `frontend-design` skill): mineral deep teal `#163d3a`, mist `#f2f7f5`, sea glass `#dce9e5`, line `#cfddd8`, restrained brass `#b59462`, and ink `#213835`; Fraunces is reserved for guest headlines and hotel identity, DM Sans for interface text and dense operations. The guest layout is **hotel key card → date search → room-number key tiles**, while staff/admin use a narrow identity rail alongside a readable ledger. This replaced the earlier repeated rounded-card/star motif with one recognizable hotel-specific element; operational data and controls remain server-backed. Mobile layouts stack the search and make room cards full-width, with visible keyboard focus and reduced-motion support.
- **Legal & data protection (P1):** Cambodia has no comprehensive data-protection law in force, so policies follow GDPR-style principles. Published legal versions are immutable; changes are new versions that force re-consent. Consent proofs are append-only and store only salted hashes of IP/user agent. Financial records are never deleted: erasure means anonymising the guest profile (blocked while a reservation is HOLD/CONFIRMED/CHECKED_IN). Retention: accounting 10 y, guest profile 3 y after last stay, ID details ≤1 y (not yet captured by the system), OTP/quotes 24 h, audit 7 y; periods are settings. Consent enforcement is fail-open only if no published document of a required kind exists. The staff agreement gate is enforced in the UI and recorded server-side; API endpoints are not blocked on it. Seed texts are templates marked as requiring legal review.
- **KHQR payments (P2):** backend uses the Python `bakong-khqr` package behind a provider adapter chosen by `PAYMENT_PROVIDER`; the SDK is imported lazily so CI never needs the network. Settlement is only by server-side `check_payment(md5)`, deduplicated by `PaymentEvent.event_id = bakong:{md5}`; amount and currency are re-validated by `process_event`. Because QR expiry in the SDK is day-granular, the app enforces a 15-minute window and keeps watching expired attempts for 24 h so a late payment is never silently lost. Only USD is enabled. Refunds stay manual (two-person workflow) until a provider refund API is confirmed.
- **Admin console (P3):** one `/admin` portal with role-filtered navigation instead of separate apps; the server is the boundary (`staff()` checks per endpoint, all under `/api/v1/admin/` so the admin session cookie is used). Developers see operational data but never guest PII; administrators have read-only developer views so the owner can see system state without being able to change flags. CMS keeps a draft copy and a published copy on the same row, so editing never changes the live site until an administrator publishes; revisions allow restore. CMS text is Markdown rendered by an escaping renderer (no raw HTML is ever stored or rendered). Error and job records store only scrubbed text (no query strings, emails or long tokens) and are purged after 90/30 days. The outbox view is read-only because no delivery adapter exists yet. Failed sign-ins are recorded as `LOGIN_FAILED` audit rows; rate limiting is planned for P4.
- **Infrastructure (P4):** one Docker host with Caddy as the only public service (automatic TLS, CSP and security headers, static Vue build); managed PostgreSQL stays external. Rate limits and lockout are on by default only in production so demos and E2E runs are not throttled; counters use Redis so all workers agree; `X-Forwarded-For` is trusted only for the configured proxy count. Inline theme script moved to `/theme-init.js` so CSP can forbid inline scripts. Django's `/admin/` is not exposed (`/admin` is the Vue portal). Backups are logical dumps with a checksum plus a monthly restore drill; the provider's point-in-time recovery and an off-host copy are required additions, not replacements. Sentry is optional and strips cookies, bodies, headers, users and emails. `create_admin` takes the password from a prompt or environment, never from argv.
- **Review fixes (1 Nov 2026):** login lockout is keyed on username **and** client IP across portals (`LOGIN_FAILED` target is `portal|ip`), so a remote attacker cannot lock out the real owner; consent IP hashes use the proxy-aware client IP; Bakong QR creation runs outside the reservation row lock; the sweeper polls never-checked attempts first; developers cannot sign out administrators; staff-agreement acceptance must match the exact document; CMS/flag/revoke writes are atomic; one PII scrubber.
- **Payment mode switch (1 Nov 2026):** demo vs bank is a runtime choice stored in the `bank_payments` FeatureFlag row (hidden from the generic flag list), changed only by developers through a validated endpoint; env `PAYMENT_PROVIDER` is the fallback. The simulator endpoint now checks the attempt's own provider instead of the global setting.
- **Guest redesign (2 Nov 2026):** supersedes the teal/brass visual direction above. Exactly three brand colours: **Mekong Teal `#0e4a4c`** (structure, primary buttons), **Saffron `#eba742`** (the single main action per screen, with dark teal text for contrast) and **Celadon `#e4ede6`** (page background). Cream + terracotta was rejected because the `frontend-design` skill flags it as a generic-AI tell. Type: Young Serif (headings), Figtree (UI), Kantumruy Pro as Khmer fallback. Room photos are owner-supplied, labelled "Representative photo", and resolved on the frontend by slugified `RoomType.name` (`data/roomCatalog.ts`) with an uploaded visual asset taking priority; no DB image field yet. Unverified marketing claims (breakfast included, "best rate") were removed from the search card.

## 2026-11-02 — Bakong failures recorded as ErrorEvent rows

Bakong `create_qr`, status-poll and Developer Console connectivity failures (rate limit, 403, network) are now stored as `ErrorEvent` rows (`method=PAY`, `path=payments/bakong/<stage>/<attempt>`), so they appear in the Developer Console error list instead of only in Vercel logs. Identical failures within 5 minutes are collapsed to avoid flooding from 30 s polling. Messages come from `ProviderError` (capped at 300 chars, no token). No model change, so no migration. The new test (`test_bakong_failures_are_recorded_once_for_the_developer_console`) was not run: the disposable Postgres on :55432 was unavailable (no podman/docker here).

## 2026-11-02 — High-resolution stock images and a low-resolution warning

Some guest images looked blurry because their source files were small (the lounge image
was 328×175; several room photos were 540–863px wide). Lightboxes on HiDPI and phone
screens need about 2400px. The owner has no property photos, so five images were replaced
with Unsplash-licensed stock at 2400px (see IMAGE_CREDITS.md), with alt text rewritten to
match. The media manager now warns when an upload, or an existing asset, has a long edge
under 1600px. Responsive variants were then added without a schema change. Their names follow a
convention (`<original>.w<width>.webp`), and the database media endpoint renders them
on first request. This backfills existing uploads with no production migration or
batch job. Only the widths 640 and 1280 are allowed, so the endpoint cannot be used to
generate arbitrary sizes. Static photos ship pre-rendered variants plus a width
manifest.

## 2026-11-07 — "Mekong at dusk" redesign tokens, and teal kept in dark mode

The site-wide redesign (`docs/REDESIGN_PLAN_V2.md`, phases 1–9) replaced the teal, saffron and celadon
palette with river teal `#123C3F`, a laterite accent `#9A4A2C`, a palm-leaf background `#EEE8D9`, paper
`#FBF9F3`, silt `#5E6B66` and lotus `#E9C9C0`. Type is Libre Caslon Condensed for display and Hanken
Grotesk for text, with Kantumruy Pro as the Khmer fallback. Glass, blur, gradient washes and resting shadows were removed;
the only shadow is `--shadow-float`, used on floating elements. Phase 9 removed every legacy alias
(`--muted`, `--brass`, `--glass-*`, `--btn-*`, …). The final set is about 30 tokens in `frontend/src/style.css`.
During phases 1–8 the dark theme set `--river` to cream so the aliases worked. In phase 9 it went back
to a lifted teal (`#8CC3C4`), and body text moved to a separate `--ink` token, so `--river` means teal in
both themes. Hard-coded Tailwind palette classes in staff screens (emerald, rose, amber, sky, slate, …)
were mapped to `--status-*`, `--ink`, `--silt`, `--sunk` and `--rule`. The printable receipt is
the exception: it keeps fixed colours because it is a paper document.

## 2026-11-07: Landing page rebuilt around a sentence search and a rate card

Most gallery and facility images have advert-style captions baked into the pixels ("Lobby, a
warm welcome awaits"). The landing page showed them in a full-width carousel, which made it look
generated whatever the CSS did. The landing page now uses only clean images. The pool and
restaurant are cropped above their captions (`public/images/luma-haven/clean/`). The carousel
(`HotelGallery.vue`) was removed, and the Gallery page still shows admin-uploaded assets. The page is now:
a hero with an oversized headline, a Khmer line, and the booking search written as a sentence
("Arriving … leaving … with 2 guests."); a rate card listing every room type, cheapest first, with a
photo that follows the row under the pointer; three clean photos, labelled as design visualisations;
the stay laid out by its real times (14:00, 22:00, 12:00) instead of numbered steps; and the location map.
The e2e labels ("Arrival", "Departure", "Guests", "Search rooms") and the hero heading are unchanged.
The Khmer line (សម្រាកក្បែរមាត់ទន្លេ នៅភ្នំពេញ) should be checked by a native speaker.

