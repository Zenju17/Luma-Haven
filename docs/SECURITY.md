# Security

Single source for what protects the system, what does not yet, and how to report a problem. Architecture rules are in [AGENTS.md](../AGENTS.md); roles in [PERMISSIONS.md](PERMISSIONS.md); incident handling in [INCIDENT_RUNBOOK.md](INCIDENT_RUNBOOK.md).

## Controls in place

| Area | Control |
|---|---|
| Authentication | Django password hashing; separate guest / staff / admin sessions in distinct HttpOnly cookies; guests re-enter via 6-digit email OTP (HMAC-hashed, 5-minute expiry, attempt counter, never returned by the API) |
| Authorization | Server-side role checks on every endpoint; booking-scoped guest access; `X-Portal` only selects a cookie jar. Developers cannot read guest PII ([PERMISSIONS.md](PERMISSIONS.md)) |
| CSRF | Required on every API write, including anonymous ones |
| Brute force | Per-IP rate limits (login, OTP, booking, privacy, polling) and per-account lockout (5 failures / 15 min). Enabled by default in production, shared through Redis |
| Transport | HTTPS only via Caddy; HSTS (1 year), secure cookies, `SECURE_SSL_REDIRECT`, proxy header trusted only from the single configured hop |
| Browser hardening | CSP (`default-src 'self'`, no inline scripts, no framing), `X-Content-Type-Options`, `X-Frame-Options: DENY`, Referrer-Policy, Permissions-Policy; Markdown content is HTML-escaped before rendering |
| Data | Card data is never stored; PII minimised; consent records append-only; retention and anonymisation jobs ([DECISIONS.md](DECISIONS.md)); exports/deletions audited |
| Payments | Settlement only by server-side provider check, idempotent per payment, amount/currency re-validated; QR secrets never logged; refunds need two people |
| Integrity | PostgreSQL exclusion constraint prevents double-booking; check constraints on amounts and dates; `select_for_update` on balance changes |
| Secrets | Environment only; `.dockerignore` keeps `.env` and credential files out of images; console shows set/unset; startup refuses weak or missing production settings |
| Logging | Structured JSON, request IDs, emails and long tokens scrubbed; error and job records scrubbed and purged; sensitive actions in the `Audit` table |
| Supply chain | Lock file with pinned versions; CI runs `pip-audit` and `npm audit` (non-blocking, reviewed weekly) |
| Recovery | Daily backups with checksum, monthly restore drill, status visible to developers |

## Known gaps and risks (be honest in audits)

1. **No multi-factor authentication** for staff or admins. Password rules are 8–12 characters; consider raising the maximum and adding TOTP before go-live.
2. **Development-only credential tooling** (`backend/.private-staff-passwords`, admin password change that mirrors passwords to a local file) must stay disabled in production; the endpoint is development-only by design. Delete any such file from servers.
3. **Payments** have not been exercised against the real Bakong API; there is no webhook and no automated provider refund.
4. **CSP allows inline styles** (`style-src 'unsafe-inline'`) because the UI uses inline style bindings; scripts are strict.
5. **Staff agreement** is enforced in the UI and recorded server-side but does not block API calls.
6. **No WAF or DDoS protection** beyond rate limits; consider a CDN/WAF in front of Caddy.
7. **Backups** stay on the host unless copied off (see [INFRASTRUCTURE.md](INFRASTRUCTURE.md)); there is no encryption of dumps at rest beyond the volume.
8. **Single hotel**: no tenant isolation; do not host a second property on this deployment.
9. **No external penetration test** has been performed. Commission one (including the KHQR flow) before launch.
10. Legal texts are templates pending lawyer review.

## Operating practices

- Review staff accounts quarterly (Admin → Staff accounts): deactivate leavers, check roles against duties, confirm only named developers hold `DEVELOPER`.
- Review failed sign-ins and active sessions weekly (Developer console → Security); sign out unknown sessions.
- Review dependency audit output weekly; patch high/critical findings within 7 days.
- Rotate secrets on the schedule in [INFRASTRUCTURE.md](INFRASTRUCTURE.md); rotate immediately on suspicion.
- Never paste secrets, database URLs or guest data into tickets, chat, screenshots or AI tools.

## Reporting a vulnerability

Email the hotel's technical owner (contact to be set before launch in `.well-known/security.txt` and here). Include steps to reproduce; do not access other people's data. We acknowledge within 3 business days.
