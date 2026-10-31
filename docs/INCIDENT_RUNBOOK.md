# Incident and data-breach runbook

For anyone on call. Stay calm, record times, change one thing at a time. Contacts (fill in before launch): technical owner ____, hotel general manager ____, database provider support ____, bank/NBC Bakong contact ____, lawyer ____.

## First 30 minutes (any incident)

1. **Assess**: what is affected (site down, wrong data, payments, suspected intrusion)? Check Admin → Developer console → System health, Errors, Jobs, Security.
2. **Contain** if people or money are at risk:
   - Pause new bookings: Developer console → Feature flags → `bookings_paused` ON.
   - Suspected stolen account: Security → *Sign out everywhere* for that user, then deactivate it (Admin → Staff accounts) and reset the password.
   - Suspected leaked secret: rotate it now (below).
3. **Preserve evidence**: note times; do not delete logs, audit rows or the database. Copy relevant `docker compose logs` output and request IDs (`X-Request-ID`) into the incident log.
4. **Tell the owner** and open an incident log (what, when, who, actions, decisions).

## Playbooks

**Site down / 503 on `/api/v1/ready`** — `docker compose -f compose.prod.yaml ps` and `logs backend`. Database unreachable → check provider status and `DATABASE_URL`; Redis down → restart `redis`. Recent deploy → redeploy the previous commit. Data corrupted by a bad migration → restore from backup (see [INFRASTRUCTURE.md](INFRASTRUCTURE.md)), record the data gap.

**Payment problems** — Decision Support shows "KHQR payments not reconciled"/"Payment exceptions". Check Developer console → Payment provider (credentials set? connectivity test) and Jobs (is the sweeper running?). Unmatched money: compare with the bank statement per booking reference, confirm bookings manually, and use the two-person refund workflow for any refund. Bakong unreachable → bookings stay `PENDING`; the sweeper retries and late payments are picked up for 24 h.

**Leaked secret** — rotate, then redeploy:
- *Database password*: change in the provider dashboard, update `.env.production`, restart all services.
- *`DJANGO_SECRET_KEY`*: change and restart (all sessions are invalidated; OTP hashes and consent IP hashes change too).
- *`BAKONG_TOKEN`*: renew via NBC, update, restart; review recent payments for anomalies.
- Find how it leaked (log, screenshot, repo history) and remove it; assume it was read.

**Suspected intrusion** — contain (above), rotate all secrets, review `Audit` for unexpected actions (staff changes, refunds, hotel settings, CMS/legal publishes, flag changes), review failed/active sessions, redeploy from a clean checkout, and restore data from before the intrusion if integrity is in doubt.

**Mistaken CMS/legal publish** — CMS: restore a revision and republish (or unpublish). Legal: publish a corrected new version (published versions cannot be edited; guests re-accept).

## Personal-data breach procedure

Treat any unauthorised access, loss or exposure of guest or staff personal data as a breach until shown otherwise. Cambodia has no comprehensive breach-notification law in force yet; the hotel follows GDPR-style practice and must confirm duties with its lawyer.

1. **Contain** (above) and note the discovery time.
2. **Scope** within 24 h: which data (names, emails, phones, stay history, payment references; no card numbers are stored), how many people, which period, whether it was read/copied/altered. Use `Audit`, logs, and the `data-export` audit entries.
3. **Assess risk** to the people affected (identity theft, fraud, safety). Low risk: record and fix. Real risk: continue.
4. **Notify without undue delay, target 72 hours from discovery**: the hotel owner/management, affected guests (plain language: what happened, what data, what we did, what they should do, contact), and any authority or business partner your lawyer or contracts require (e.g. the bank for payment-related data).
5. **Remediate**: close the hole, rotate secrets, force password resets, strengthen controls.
6. **Record**: keep the incident log, decisions and notifications for at least 7 years.
7. **Review** within a week (below).

Guest notice template: *"On [date] we discovered that [what happened]. The information involved was [data]. It did not include [card details / passwords]. We have [actions]. You may wish to [advice]. Contact [name, email, phone] with questions."*

## After every incident

Blameless review within a week: timeline, root cause, what detected it, what slowed us down, concrete follow-ups with owners. Update this runbook, [SECURITY.md](SECURITY.md) and tests so it cannot recur silently.

## Routine checks

- Daily: Developer console health is green (database, Celery, backup).
- Weekly: failed sign-ins, errors, dependency audit.
- Monthly: restore drill; review unreconciled payments.
- Quarterly: staff access review; test this runbook with a tabletop exercise.
