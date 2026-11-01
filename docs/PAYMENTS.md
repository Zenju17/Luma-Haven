# Bakong KHQR payments — integration plan

**Status: implemented (31 Oct 2026), not yet run against Bakong or a test database.** The adapter, migration `0007`, session/status endpoints, sweeper, checkout QR page and MIS additions exist; the unit tests use a fake provider and two tests exercise the real SDK offline. The development emulator remains the default (`PAYMENT_PROVIDER=development`). Set `PAYMENT_PROVIDER=bakong` plus the `BAKONG_*` variables in the ignored `.env` to enable KHQR.

**Demo vs bank mode:** `PAYMENT_PROVIDER` is only the default. A developer switches new payments between **Demo payment** (simulated checkout) and **Bank payment (Bakong KHQR)** in Admin → Developer console → Payment provider (`POST /api/v1/admin/dev/payment-mode`, audited). Bank mode is refused until the `BAKONG_*` values are configured; demo mode is refused in production. Every attempt keeps the mode it was created with: demo attempts can only be simulated, bank attempts can only settle via Bakong, and the sweeper always runs, so bank payments started before a switch are still confirmed.

**Implementation notes (differences from the original design):**
- The SDK's QR expiry is in **whole days**, so the hotel enforces the 15-minute window itself (`PaymentAttempt.expires_at`). A QR can still be paid in the bank app after our window, so the Celery sweeper (`core.tasks.sweep_payment_attempts`, every 30 s) keeps polling `PENDING` and `EXPIRED` attempts for `PAYMENT_LATE_WINDOW_HOURS` (24) with back-off. A late payment goes through `process_event`: it confirms if the room is still free, otherwise it becomes a `PaymentException` needing a manual refund.
- Endpoints: `POST /reservations/<id>/payment-sessions` (reuses a live attempt, max 5 new per 10 min) and `GET /payment-sessions/<uuid>` (booking-scoped; server-side provider check, at most one provider call per 3 s per attempt). Payment never settles from browser input.
- A QR payment extends an unpaid hold up to the QR expiry (+2 min), only within the first hour of the booking.
- Only USD is supported (`payments.E004`); KHR is rejected until it has tests. `manage.py check` fails if `bakong` is selected without token/account/merchant settings, or if `development` is used with `APP_ENV=production`.
- Bakong's NBC API accepts requests **from Cambodian IP addresses only**: the production server (or an egress proxy) must run in Cambodia, or use a KHQR.dev `rbk_` token.
- MIS: cash-reconciliation report now returns `channel_mix`, `attempt_funnel` (with abandon rate) and `payment_exceptions`; Decision Support rules 8 (unreconciled KHQR attempts) and 9 (KHQR abandonment > 50 %).


> **SDK note.** The linked [`mrrhak/khqr_sdk`](https://github.com/mrrhak/khqr_sdk) is a **Flutter/Dart** package (`pubspec.yaml`, `KhqrSdk.generateMerchant(...)`, `KhqrCardWidget`). It cannot run in this Django/Python backend or the Vue frontend. Use the Python package [`bakong-khqr`](https://pypi.org/project/bakong-khqr/) (unofficial, MIT, Python 3.8+) for the backend, or build a separate Flutter client later. Both implement the same KHQR/EMVCo concepts.

## Method mapping

| Dart SDK (`khqr_sdk`) | Python (`bakong-khqr`) | Use in Luma Haven |
|---|---|---|
| `KhqrSdk.generateMerchant(MerchantInfo(...))` | `KHQR(token).create_qr(account_id=..., merchant_name=..., merchant_city=..., amount=..., currency=..., bill_number=..., expiration=...)` | Create the dynamic QR for a `PaymentAttempt` |
| `KhqrSdk.generateIndividual(IndividualInfo(...))` | `create_qr(...)` with individual merchant fields | Not used (hotel is a merchant) |
| `KhqrSdk.verify(qr)` / `decode(qr)` | `create_qr()` output is the QR string; validate structure yourself | Optional staff diagnostics |
| `KhqrSdk.generateDeepLink(url, qr, SourceInfo(...))` | `generate_deeplink(qr=..., appName=..., appIconUrl=..., appDeepLinkCallback=...)` | Optional “Open banking app” button |
| `KhqrSdk.checkBakongAccount(url, account)` | `check_payment(md5)` / `get_payment(md5)` | Server-side settlement check |
| `KhqrCardWidget` | `qr_image(qr, format="base64_uri")` or Vue `qrcode.vue` | Render the QR in the guest checkout page |

`bakong-khqr` also provides `generate_md5(qr)`, `check_bulk_payments([...])` and a smart polling helper (`check_payment(md5, start_time=...)` → `(status, next_delay)`). Supported states: `PAID`, `UNPAID` (official NBC), plus `SCANNED`/`EXPIRED` with a KHQR.dev `rbk...` token.

## Recommended architecture

Keep provider code behind an adapter so the emulator, tests and a future gateway do not leak into views.

```text
Vue CheckoutView
  → POST /api/v1/reservations/<id>/payment-sessions
      → PaymentProvider.create_attempt(reservation, amount)
      → PaymentAttempt(provider='bakong', qr=..., md5=..., tran_id=..., expires_at=...)
      ← { qr, md5, expires_at, simulated: false }
  → render QR with qrcode.vue; poll GET /api/v1/payment-sessions/<uuid>
      → provider.check_payment(md5)          # server → Bakong, never browser → Bakong
      → if PAID: services.process_event(attempt, 'SUCCESS', f'bakong:{md5}')
      ← { status: 'PENDING' | 'SUCCESS' | 'EXPIRED' | 'EXCEPTION' }
```

Proposed modules:

```text
backend/core/payments/
  base.py        PaymentProvider protocol: create_attempt(), check_status()
  development.py wraps the existing simulated flow
  bakong.py      lazy-imports bakong_khqr; reads settings/env
  factory.py     get_payment_provider() from PAYMENT_PROVIDER
```

Proposed model fields on `PaymentAttempt` (one migration): `provider`, `provider_qr`, `provider_md5`, `provider_tran_id`, `checkout_url`, `expires_at`. Keep `status` values aligned with existing logic (`PENDING`, `SUCCESS`, `FAILED`, `EXCEPTION`).

## Configuration

Never put these in `VITE_*` variables or commit them.

```env
PAYMENT_PROVIDER=bakong
BAKONG_TOKEN=...                 # NBC developer token, or rbk_... KHQR.dev token
BAKONG_ACCOUNT_ID=hotel@bank     # required for offline/official-token mode
BAKONG_MERCHANT_NAME=Luma Haven
BAKONG_MERCHANT_CITY=Phnom Penh
BAKONG_CURRENCY=USD              # must match Hotel.currency
```

Notes from the Python SDK README:

- With an `rbk...` token, `create_qr(amount=...)` resolves merchant/currency from the KHQR.dev store; only `amount` is required.
- With an official NBC token or no token (offline EMVCo generation), pass full merchant fields.
- The official Bakong API is restricted to Cambodia IPs; KHQR.dev is the global alternative. Confirm which one the hotel’s merchant account supports.
- The PyPI package is **not an official NBC release**; review it and confirm compliance before production.

## Amount and currency rules

- Luma Haven stores integer minor units (`amount_minor`, USD cents).
- KHQR expects major units (`10.00`). Convert with `Decimal(amount_minor) / 100` for USD; never float.
- KHR has no minor unit; if KHR is ever enabled, send whole riel and add explicit currency tests.
- Reject creation when `Hotel.currency != BAKONG_CURRENCY`.
- On settlement, re-check that the provider amount/currency and reservation folio balance still match. `services.process_event()` already marks mismatches as `PaymentException`.
- Use a stable `bill_number` (reservation reference + attempt id) to aid reconciliation.

## Security requirements

1. **Server is the source of truth.** A browser saying “paid” means nothing. Only `check_payment(md5)` returning `PAID`, or a verified provider callback, may settle.
2. **Do not accept `md5`, QR strings or amounts from the client** when polling; look them up from `PaymentAttempt`.
3. **Idempotency:** use `event_id = f'bakong:{md5}'`; `PaymentEvent.event_id` is unique, so repeated polls cannot double-settle.
4. **No secrets or raw QR payloads in logs**, screenshots, analytics or error reports. `DJANGO_DEBUG=false` remains mandatory for remote databases.
5. **Rate-limit** payment-session creation and status polling; reuse the SDK’s `next_delay` guidance instead of tight loops.
6. **Expiry:** dynamic QR must expire (for example 10–15 minutes, matching `RESERVATION_HOLD_MINUTES`). Reject expired attempts and release the hold through the existing task.
7. **Refunds** stay manual until the provider’s refund API is confirmed; the current two-person approval workflow records intent, not a real bank refund.
8. Keep Bakong credentials and callback URLs out of the repository; document rotation and incident response.

## Frontend changes

- Replace “Pay balance (simulation)” with “Pay with Bakong” when `provider == 'bakong'`.
- `CheckoutView.vue` renders `qr` with the existing `qrcode.vue` dependency and shows amount, currency, expiry countdown and status.
- Poll the backend endpoint (for example every 3–5 seconds), stop on `SUCCESS`/`EXPIRED`, and redirect to `/booking/:id` on success.
- Keep the simulator behind `PAYMENT_PROVIDER=development` so demos and Playwright remain deterministic.
- Deep link (`generate_deeplink`) is optional; if omitted, guests scan the QR with any banking app.

## Testing strategy (when implemented)

- Unit-test the adapter with a **fake provider**; never call Bakong in CI.
- Assert exact major-unit conversion, currency rejection, QR/MD5 persistence and `bakong:{md5}` idempotency.
- Test duplicate polls settle once, failed/expired attempts do not confirm the reservation, and a late payment hits the existing `PaymentException` path.
- Keep the current development E2E journey; add a Bakong checkout E2E only with a stub provider.
- A manual sandbox checklist should cover: QR renders, Bakong app scans it, status becomes `PAID`, booking becomes `CONFIRMED`, duplicate polls are harmless, expired QR is rejected.

## Implementation checklist

1. Add `bakong-khqr==0.6.5` to `backend/requirements.txt` and regenerate `requirements.lock`.
2. Add settings/env parsing and a startup check for the selected provider.
3. Add `payments/base.py`, `development.py`, `bakong.py`, `factory.py`.
4. Add the `PaymentAttempt` migration and update `payment_session` / add the status endpoint.
5. Update `CheckoutView.vue` and `BookingView.vue` labels; keep the simulator route dev-only.
6. Add tests, update `docs/IMPLEMENTATION_STATUS.md`, `docs/DECISIONS.md`, `docs/PERMISSIONS.md` if new roles are needed, and this file’s status line.
7. Only then set real credentials, test with a small amount, and document refund/reconciliation handling.

## References

- Dart SDK: <https://github.com/mrrhak/khqr_sdk> (MIT, unofficial)
- Python package: <https://github.com/bsthen/bakong-khqr> · <https://pypi.org/project/bakong-khqr/>
- KHQR specification: <https://bakong.nbc.gov.kh/en/download/KHQR/integration/KHQR%20SDK%20Document.pdf>
- Bakong developer portal: <https://bakong.nbc.gov.kh/>
