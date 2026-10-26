# Hotel Information Management System (HIMS)

> **Implementation checkpoint (October 2026):** This repository now includes an initial full-stack vertical slice, but the remainder of this document is the **target specification**, not a list of implemented features. See [implementation status](docs/IMPLEMENTATION_STATUS.md), [permissions](docs/PERMISSIONS.md), and [decisions](docs/DECISIONS.md). Do not use this checkpoint for real payments or production guest data.

## Run the current checkpoint

Prerequisites: a Supabase PostgreSQL project and Docker Compose, or Fedora's rootless Podman plus `uv` for Compose. Compose starts Redis, the Django app, workers and the frontend; **it does not start a local database**. Local addresses: guest UI at `http://localhost:5173/`, staff/admin login at `http://localhost:5173/staff`, API at `http://localhost:8000/api/v1/`, interactive OpenAPI at `http://localhost:8000/api/docs/`. Visiting the backend root `http://localhost:8000/` redirects to the staff login; the staff interface itself is served by Vite on port 5173, not by Django.

From the Supabase dashboard, open **Connect → Session pooler** and copy its connection URI (port `5432`). Replace the password with your database password, percent-encoding reserved characters, then add `?sslmode=require` (or `&sslmode=require` if the URI already has query parameters). Use the exact pooler host given by Supabase; its username has the form `postgres.<project-ref>`. A direct connection also works when your machine has IPv6. Port `6543` (transaction pooler) is unsupported. A GitHub connection to Supabase does **not** populate the backend's database credentials: configure `DATABASE_URL` yourself in the ignored `.env` file. Never put the database password in `VITE_*` variables or commit it.

Keep the Supabase Data API disabled, as you have done: Django tables in `public` are not protected by Supabase RLS policies. The first migration enables `btree_gist` for safe room allocations; if extension creation fails, enable **btree_gist** under Supabase **Database → Extensions** and retry migration. Use synthetic seed data only.

Keep `DJANGO_DEBUG=false` in `.env` when using a remote database: Django's detailed error page can expose a `DATABASE_URL` from request metadata. If a database URI appears in an error report, rotate that database password and recreate the backend and worker containers after updating `.env`.

```bash
# If .env already exists, keep it; otherwise copy .env.example to .env.
# Edit .env: set DATABASE_URL to the Supabase URI and set unique Django secrets.
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
docker compose logs backend  # read local console verification messages
```

`seed_demo` prints a random password for **newly created** staff users (admin, manager, reception, housekeeping, accountant). Set `SEED_PASSWORD` in your private `.env` to choose a local password before the first seed. Re-running the command does not change existing passwords. Seed data is synthetic. No reusable credentials are committed.

**Demo:** Open the guest UI, search dates starting today or later, select a vacant room, review the server quote, enter a fictional guest name and email, and hold the room. Use **Pay balance (simulation)**, choose **Simulate success**, then verify with the booking reference and email. Read the six-digit code in `docker compose logs backend` (never in an API response). For self check-in choose today's arrival date and room 101 or 201; room 102 is dirty, 103 is occupied and 202 is out of service. Check in, submit a request, inspect your folio and check out. Sign in to `/staff` as reception to complete requests and inspect a housekeeping task (housekeeping can mark cleaning and awaiting inspection but cannot approve readiness). The generic QR on the verification page opens the same link; physical keys are collected from reception.

**Fedora without Docker:** Podman is available, but requires a Compose provider. With `uv` installed, run `uvx --from podman-compose podman-compose up --build -d`, then use `uvx --from podman-compose podman-compose exec backend python manage.py migrate` and `uvx --from podman-compose podman-compose exec backend python manage.py seed_demo`. For logs, use `uvx --from podman-compose podman-compose logs backend`; stop with `uvx --from podman-compose podman-compose down` (without `-v`). Alternatively install Docker Engine with Compose. Do not run both stacks simultaneously on the same ports.

**Verification:** Django's PostgreSQL integration tests create a `test_*` database. **Do not run them against the project's main Supabase connection**; use a separate disposable PostgreSQL test server with database-creation permission. These checks do not create a test database:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python -m pytest -c pytest.ini tests/test_database_settings.py -q
docker compose exec frontend npm run build
docker compose down
```

With a separate PostgreSQL test server configured as `DATABASE_URL` in the test container, run `python -m pytest -c pytest.ini tests -q` there. `docker compose down` stops the app containers; it does not delete your Supabase database.

`.env.example` lists configuration keys. Never commit `.env` or expose the database URI to the frontend. `APP_ENV=production` rejects `PAYMENT_PROVIDER=development`; a real provider is not yet implemented. Review your Supabase project's backup and retention settings. For a separate manual backup use `pg_dump` with the project's **direct** database connection from a host that supports IPv6 (or the IPv4 add-on), and verify restoration into a disposable database. Production requires HTTPS, private infrastructure, secret management, backups and restore drills, monitoring, and a configured real provider. See the status document for known missing features and the specification below for intended behavior.

**Database choice:** Supabase PostgreSQL is the development default. The backend uses ordinary PostgreSQL through Django, not the Supabase JavaScript client or Supabase Auth. Connecting your Supabase project to GitHub does not automatically apply Django migrations or seed data.

A full-stack Management Information System for managing hotel reservations, room availability, guest information, QR self check-in, online payments, self check-out, housekeeping, and management reporting.

> **Specification status:** The sections below describe the intended complete system. Compare each requirement with [the tracked implementation status](docs/IMPLEMENTATION_STATUS.md) before relying on it.

---

## Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Project Objectives](#2-project-objectives)
- [3. Technology Stack](#3-technology-stack)
- [4. User Roles](#4-user-roles)
- [5. Main Features](#5-main-features)
- [6. Guest Workflows](#6-guest-workflows)
- [7. Business Rules](#7-business-rules)
- [8. System Architecture](#8-system-architecture)
- [9. Database Design](#9-database-design)
- [10. API Design](#10-api-design)
- [11. Frontend Pages](#11-frontend-pages)
- [12. Management Dashboard](#12-management-dashboard)
- [13. Security Requirements](#13-security-requirements)
- [14. Proposed Project Structure](#14-proposed-project-structure)
- [15. Development Setup](#15-development-setup)
- [16. Testing Requirements](#16-testing-requirements)
- [17. Development Roadmap](#17-development-roadmap)
- [18. Future Improvements](#18-future-improvements)
- [19. Contribution Guidelines](#19-contribution-guidelines)
- [20. License](#20-license)

---

## 1. Project Overview

The Hotel Information Management System centralizes hotel operations into one platform.

Guests can search for rooms, make reservations, pay online, verify their booking through a QR-based entry flow, check in, request services, review their bills, and check out.

Hotel staff can manage room inventory, reservations, guest verification, payments, housekeeping, maintenance, and service requests.

Managers can monitor hotel performance through dashboards and reports generated from operational records.

### Problems Addressed

- Duplicate or overlapping room bookings.
- Inaccurate room availability.
- Missing guest information.
- Unrecorded check-in and check-out times.
- Disconnected booking and payment records.
- Delayed housekeeping updates.
- Difficulty preparing management reports.
- Limited accountability for sensitive changes.

### Initial Scope

The first version targets:

- One hotel.
- One configured settlement currency.
- One room per reservation, with multiple registered occupants.
- A responsive guest portal.
- A staff management dashboard.
- A payment provider sandbox.
- Reception assistance for exceptions and physical key collection.

Multi-property operations, group bookings, booking-channel synchronization, and smart locks are future extensions.

---

## 2. Project Objectives

1. Centralize hotel information in a consistent database.
2. Prevent overlapping room allocations.
3. Support secure guest self-service.
4. Record accurate scheduled and actual stay information.
5. Track payments, refunds, charges, and outstanding balances.
6. Coordinate housekeeping and maintenance.
7. Provide reliable information for management decisions.
8. Maintain role-based access and an audit trail.
9. Support recovery through backups and tested restoration.
10. Reduce repetitive administrative work.

### Why This Is an MIS Project

The system converts daily operational transactions into management information.

| Operational Data | Management Information |
|---|---|
| Room reservations | Booking demand and future occupancy |
| Actual guest stays | Occupancy and stay-duration reports |
| Charges and payments | Revenue, cash collections, and unpaid balances |
| Housekeeping tasks | Cleaning turnaround and room readiness |
| Service requests | Response times and service performance |
| Cancellations | Cancellation patterns and lost demand |

---

## 3. Technology Stack

The following technologies are proposed project choices. Dependency versions should be selected, tested, and locked during implementation.

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Vue 3 + TypeScript | Guest portal and staff dashboard |
| Frontend tooling | Vite | Development server and frontend builds |
| Styling | Tailwind CSS | Responsive interface styling |
| Backend | Python + Django | Business logic and administration |
| API | Django REST Framework | REST endpoints and authorization |
| Database | PostgreSQL | Persistent data and transaction integrity |
| Background jobs | Celery | Notifications and scheduled processing |
| Message broker/cache | Redis | Background task coordination and caching |
| Authentication | Secure server-managed sessions | Staff and restricted guest authentication |
| Payments | Hosted checkout through a provider adapter | Online payment integration |
| File storage | Private S3-compatible storage | Restricted documents and exports |
| API documentation | OpenAPI | API contracts and documentation |
| Local environment | Docker Compose | Reproducible development services |
| Testing | Pytest and Playwright | Backend and browser workflow tests |
| Version control | Git | Source history and collaboration |

### Architectural Approach

Use a modular monolith for the first version:

- One backend application.
- One primary database.
- Separate modules for each business domain.
- Background workers for asynchronous tasks.
- Provider adapters for external integrations.

---

## 4. User Roles

Authorization must be enforced by the backend, including access to individual records.

| Role | Main Permissions |
|---|---|
| Administrator | Manage staff accounts, roles, system settings, and integration configuration |
| Hotel Manager | Manage rates, policies, reports, approvals, and authorized overrides |
| Receptionist | Manage reservations, verify guests, assign rooms, and assist check-in/out |
| Housekeeping Staff | View assigned cleaning tasks and update cleaning progress |
| Accountant | Review payments, reconcile transactions, and execute approved refunds |
| Guest | Access their own booking, payments, stay, requests, and checkout |

### Permission Rules

- Guests cannot access another guest’s booking.
- Housekeeping staff cannot access payment details or identity documents.
- Receptionists cannot modify staff permissions.
- Refunds require the configured approval process.
- Managers cannot silently rewrite settled financial history.
- Sensitive overrides require a reason and an audit record.

---

## 5. Main Features

### 5.1 Hotel Configuration

Manage:

- Hotel name and contact details.
- Hotel timezone.
- Settlement currency.
- Standard check-in and check-out times.
- Taxes and fees.
- Deposit requirements.
- Cancellation and refund policies.
- No-show policy.
- Guest verification requirements.

### 5.2 Room Management

Maintain:

- Room numbers.
- Room types.
- Capacity.
- Amenities.
- Photos and descriptions.
- Rate plans.
- Cleaning status.
- Service condition.
- Maintenance blocks.

Room information must distinguish:

| Dimension | Example Values |
|---|---|
| Current occupancy | Vacant, occupied |
| Housekeeping | Dirty, cleaning, awaiting inspection, ready |
| Service condition | In service, out of service |
| Availability for selected dates | Free, held, reserved, blocked |

A vacant room may still be dirty or reserved for an upcoming arrival.

### 5.3 Reservation Management

Support:

- Availability search by dates and occupancy.
- Server-calculated price quotes.
- Temporary inventory holds.
- Booking confirmation.
- Reservation amendments.
- Cancellation.
- No-show handling.
- Room assignment.
- Booking history.
- Reservation-source tracking.

Reservation prices must retain the rate, tax, and policy details agreed at booking time.

### 5.4 Guest Information Management

Store authorized information such as:

- Full name.
- Contact details.
- Registered occupants.
- Stay history.
- Verification status.
- Consent records.
- Special requests.

Identity documents, when required, must use restricted storage and a configured retention policy.

### 5.5 QR Self Check-In

Support two entry methods:

1. A generic lobby QR code that opens the verification page.
2. A private booking link or QR token with restricted scope.

The guest must complete the configured verification process before accessing the booking or completing check-in.

A scanned QR code alone must not grant room access.

### 5.6 Online Payments

Support:

- Deposits.
- Full payment.
- Remaining balance settlement.
- Payment status tracking.
- Receipts.
- Partial and full refunds.
- Reconciliation.
- Failed and pending payment handling.

Payments must use server-calculated amounts.

Only verified backend confirmation from the provider can establish successful payment.

### 5.7 Check-In Management

Before check-in, validate:

- Reservation status.
- Arrival policy.
- Guest verification.
- Required payment or approved guarantee.
- Room readiness.
- Actual room occupancy.

On successful check-in:

- Create the stay record.
- Record the actual check-in timestamp.
- Start the room occupancy interval.
- Update reservation status.
- Record the actor and audit event.

### 5.8 Self Check-Out

Allow guests to:

- Review an itemized folio.
- See outstanding charges.
- Settle the remaining balance.
- Confirm departure.
- Receive a receipt.

Successful checkout must:

- Record the actual check-out timestamp.
- End room occupancy.
- Close the stay.
- Close the folio under the configured settlement policy.
- Mark the room dirty.
- Trigger a housekeeping task.

### 5.9 Housekeeping

Support:

- Cleaning task assignment.
- Cleaning progress.
- Inspection.
- Room readiness.
- Completion timestamps.
- Overdue task monitoring.

A room becomes ready only after the required cleaning and inspection steps.

### 5.10 Maintenance

Support:

- Maintenance tickets.
- Priority levels.
- Assigned staff.
- Date-bounded room blocks.
- Repair status.
- Resolution history.

A maintenance block that conflicts with an existing reservation must trigger a resolution or reassignment workflow.

### 5.11 Guest Service Requests

Examples:

- Additional towels.
- Cleaning.
- Maintenance assistance.
- Extra amenities.
- Reception assistance.

Suggested request states:

```text
SUBMITTED → ASSIGNED → IN_PROGRESS → COMPLETED
```

Cancellation should be available where appropriate.

### 5.12 Reports and Audit Logs

Provide:

- Operational reports.
- Financial reports.
- Occupancy reports.
- Housekeeping reports.
- Authorized CSV/PDF exports.
- Sensitive-change history.

---

## 6. Guest Workflows

### 6.1 Booking and Payment

1. Guest selects arrival date, departure date, and occupancy.
2. Backend checks available inventory.
3. Guest selects a room type.
4. Backend generates an itemized, expiring quote.
5. Guest submits booking information.
6. Backend creates a temporary room allocation.
7. Guest opens hosted payment checkout.
8. Provider sends a payment event to the backend.
9. Backend verifies and records the event.
10. Reservation is confirmed when its conditions are satisfied.
11. Guest receives confirmation and portal access instructions.

If payment succeeds after the room hold expires, the system must safely reallocate inventory or start a payment exception/refund process.

### 6.2 QR Self Check-In

1. Guest scans a QR code.
2. Guest verifies their booking and contact.
3. Guest confirms required information.
4. Identity verification is completed where required.
5. Backend checks payment, arrival policy, and room readiness.
6. Backend completes check-in transactionally.
7. Guest receives room details and key collection instructions.

Without a smart-lock or key-dispenser integration, reception provides the physical key.

### 6.3 During the Stay

The guest can:

- View stay information.
- Submit service requests.
- Review the current folio.
- Contact reception.
- Prepare for checkout.

### 6.4 Self Check-Out

1. Guest requests the final folio.
2. Backend calculates the current balance.
3. Guest pays any outstanding amount.
4. Backend verifies settlement.
5. Guest submits the checkout request.
6. Backend rechecks the folio under a transaction.
7. Backend records departure and ends occupancy.
8. Room becomes dirty.
9. Housekeeping receives a task.
10. Guest receives confirmation and receipt.

If a new charge changes the balance during checkout, the system must request settlement of the updated balance.

---

## 7. Business Rules

### Reservation States

```text
HOLD → CONFIRMED → CHECKED_IN → CHECKED_OUT
```

Alternative transitions:

```text
HOLD → EXPIRED
HOLD → CANCELLED
CONFIRMED → CANCELLED
CONFIRMED → NO_SHOW
```

Payment status must remain separate from reservation status.

### Date and Availability Rules

- Arrival date must be earlier than departure date.
- Model reservation dates as `[arrival, departure)`.
- Adjacent bookings are allowed.
- Room capacity cannot be exceeded.
- Active room allocations cannot overlap.
- Availability checks alone are insufficient: the database must prevent conflicting writes.
- Expired holds must be explicitly released.
- Stay extensions must pass new availability checks.

### Check-In and Check-Out Rules

- Only eligible reservations may check in.
- Dirty, out-of-service, or occupied rooms cannot receive a new check-in.
- One reservation can have at most one active stay.
- One room can have at most one active occupancy interval.
- Checkout ends occupancy but does not make the room ready.
- Overrides require permission, reason, and audit history.

### Timestamp Rules

Store separately:

- Scheduled arrival date.
- Scheduled departure date.
- Actual check-in timestamp.
- Actual check-out timestamp.
- Hotel business date where applicable.

Actual timestamps must be generated by the backend, stored as timezone-aware UTC values, and displayed in the hotel timezone.

### Financial Rules

- Use integer minor units and explicit currency for money.
- Never use binary floating-point values for financial calculations.
- Do not combine different currencies into one total.
- Pending payments do not reduce the settled balance.
- Refunds cannot exceed the refundable settled amount.
- Financial corrections use adjustment or reversal records.
- Preserve original rate and tax snapshots.

### Retry and Concurrency Rules

Use idempotency keys for important commands such as:

- Creating reservations.
- Initiating payments.
- Checking in.
- Checking out.
- Creating charges.
- Submitting refunds.

Repeated requests must not create duplicate financial or operational effects.

---

## 8. System Architecture

```mermaid
flowchart TD
    Guest[Guest Portal] --> API[Django REST API]
    Staff[Staff Dashboard] --> API
    API --> DB[(PostgreSQL)]
    API --> Provider[Payment Provider]
    Provider --> Webhook[Verified Payment Webhook]
    Webhook --> API
    API --> Storage[Private File Storage]
    API --> Outbox[Transactional Outbox]
    Outbox --> Worker[Background Workers]
    Worker --> Notification[Email or SMS Provider]
```

### Responsibilities

**Frontend**

- Displays forms and information.
- Guides guest and staff workflows.
- Provides immediate usability feedback.
- Handles pending and failure states.

**Backend**

- Enforces authorization.
- Validates inputs.
- Calculates prices and balances.
- Controls state transitions.
- Coordinates database transactions.
- Verifies external events.

**Database**

- Stores authoritative records.
- Enforces relationships and constraints.
- Prevents overlapping allocations.
- Preserves financial and operational history.

**Workers**

- Send notifications.
- Expire holds.
- Process outbox events.
- Reconcile payments.
- Generate exports.
- Run retention tasks.

Redis must not be the sole source of room availability or payment truth.

---

## 9. Database Design

### Core Entities

| Entity | Important Fields |
|---|---|
| Hotel | name, timezone, currency, check-in/out policies |
| User | name, email, password hash, active status |
| StaffMembership | user, hotel, role |
| RoomType | name, capacity, amenities |
| Room | number, room type, cleaning status, service status |
| RatePlan | room type, price rules, tax policy |
| Guest | name, verified contact, consent |
| Reservation | reference, guest, dates, status, quote snapshot |
| ReservationGuest | reservation, guest, occupant type |
| InventoryAllocation | room, date range, kind, active, expiry |
| Stay | reservation, check-in timestamp, check-out timestamp |
| RoomOccupancy | stay, room, start timestamp, end timestamp |
| IdentityVerification | guest, status, reviewer, private file reference |
| Folio | reservation, currency, status, version |
| FolioEntry | category, amount, service date, adjustment reference |
| PaymentAttempt | expected amount, provider session, status |
| Payment | provider transaction, settled amount, currency |
| PaymentAllocation | payment, folio, applied amount |
| Refund | payment, amount, approval, provider status |
| WebhookEvent | provider, event ID, processing status |
| GuestAccessToken | token hash, scope, expiry, consumed timestamp |
| HousekeepingTask | room, assignee, status, timestamps |
| MaintenanceTicket | room, priority, status |
| ServiceRequest | stay, type, status, assignee |
| AuditLog | actor, action, entity, redacted change, timestamp |
| IdempotencyRecord | scope, key, request hash, result reference |
| OutboxEvent | event type, entity, payload, published timestamp |

### Relationships

```mermaid
erDiagram
    HOTEL ||--o{ ROOM : contains
    ROOM_TYPE ||--o{ ROOM : groups
    ROOM ||--o{ INVENTORY_ALLOCATION : allocates
    RESERVATION ||--o{ INVENTORY_ALLOCATION : reserves
    GUEST ||--o{ RESERVATION_GUEST : joins
    RESERVATION ||--o{ RESERVATION_GUEST : registers
    RESERVATION ||--o| STAY : becomes
    STAY ||--o{ ROOM_OCCUPANCY : records
    ROOM ||--o{ ROOM_OCCUPANCY : hosts
    RESERVATION ||--|| FOLIO : owns
    FOLIO ||--o{ FOLIO_ENTRY : contains
    FOLIO ||--o{ PAYMENT_ALLOCATION : receives
    PAYMENT ||--o{ PAYMENT_ALLOCATION : funds
    PAYMENT ||--o{ REFUND : returns
```

### Required Database Controls

- Unique room numbers within a hotel.
- Unique public booking references.
- Unique provider transaction identifiers.
- Unique provider webhook event identifiers.
- Foreign-key constraints.
- Valid date ranges.
- Positive payment and refund amounts.
- Exclusion constraints for overlapping active room allocations.
- Partial unique constraints for active stays and room occupancy.
- Protected financial references.
- Indexes for dates, status, room availability, payment settlement, and audit searches.

Aggregate financial limits, such as total refunds, must be checked transactionally under appropriate locks.

---

## 10. API Design

### Base Path

```text
/api/v1/
```

These endpoints are proposed contracts.

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/login` | Staff login |
| POST | `/auth/logout` | End session |
| GET | `/auth/me` | Current identity and permissions |

### Availability and Reservations

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/availability` | Search available rooms |
| POST | `/quotes` | Calculate booking quote |
| POST | `/reservations` | Create temporary booking hold |
| GET | `/reservations/{id}` | View authorized booking |
| POST | `/reservations/{id}/amend` | Change dates or allocation |
| POST | `/reservations/{id}/cancel` | Cancel under policy |

### Guest Verification and Stays

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/guest-access/request-otp` | Request verification code |
| POST | `/guest-access/verify-otp` | Verify code and establish guest session |
| POST | `/guest-access/exchange-token` | Exchange restricted booking token |
| POST | `/reservations/{id}/identity-submissions` | Submit required verification evidence |
| POST | `/identity-submissions/{id}/review` | Staff verification decision |
| POST | `/reservations/{id}/check-in` | Complete check-in |
| GET | `/stays/{id}/folio` | View itemized bill |
| POST | `/stays/{id}/check-out` | Complete checkout |

### Payments

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/reservations/{id}/payment-sessions` | Create hosted checkout session |
| GET | `/reservations/{id}/payments` | View authorized payment status |
| POST | `/webhooks/payments/{provider}` | Receive verified provider event |
| POST | `/folios/{id}/entries` | Create authorized charge or adjustment |
| POST | `/refunds` | Request refund |
| POST | `/refunds/{id}/approve` | Approve refund |
| POST | `/refunds/{id}/submit` | Submit approved refund |

### Operations and Reporting

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/rooms` | List or create rooms |
| PATCH | `/rooms/{id}` | Edit authorized room details |
| GET/POST | `/housekeeping/tasks` | Manage cleaning tasks |
| POST | `/housekeeping/tasks/{id}/transition` | Change task state |
| GET/POST | `/maintenance/tickets` | Manage maintenance |
| GET/POST | `/service-requests` | View or create authorized requests |
| PATCH | `/service-requests/{id}` | Update request assignment/status |
| GET | `/dashboard/summary` | Dashboard metrics |
| GET | `/reports/occupancy` | Occupancy report |
| GET | `/reports/revenue` | Revenue report |
| POST | `/reports/exports` | Generate authorized export |
| GET | `/audit-logs` | Restricted audit search |

### Example Reservation Request

```http
POST /api/v1/reservations
Content-Type: application/json
Idempotency-Key: 3daa5c87-79b5-4cb7-a695-8bfe9b3de10c
```

```json
{
  "quote_id": "6bafc7f4-24ec-4ef9-bcc0-65bc8abafab1",
  "guest": {
    "full_name": "Example Guest",
    "email": "guest@example.com"
  },
  "occupants": [
    {
      "full_name": "Example Guest",
      "type": "ADULT"
    }
  ],
  "terms_version": "hotel-terms-v1"
}
```

The backend obtains dates, price, and currency from the valid quote rather than trusting client-submitted totals.

### Error Format

```json
{
  "error": {
    "code": "OUTSTANDING_BALANCE",
    "message": "Settle the remaining balance before check-out.",
    "details": {
      "amount_minor": 1500,
      "currency": "USD"
    },
    "request_id": "req-example-001"
  }
}
```

### Payment Webhook Requirements

- Verify the raw-body signature.
- Apply provider replay controls.
- Match merchant, booking, amount, and currency.
- Persist the event durably.
- Deduplicate by provider and event ID.
- Keep failed processing retryable.
- Handle out-of-order delivery.
- Prevent older events from downgrading settled payments.
- Reconcile missed or unmatched events.

---

## 11. Frontend Pages

### Guest Pages

- Room catalog.
- Availability results.
- Room details.
- Reservation form.
- Payment checkout.
- Payment status.
- Booking verification.
- Guest booking overview.
- Identity submission.
- Self check-in.
- Stay information.
- Service requests.
- Itemized folio.
- Self check-out.
- Receipt.

### Staff Pages

- Staff login.
- Today’s operations.
- Reservation calendar.
- Reservation list and details.
- Arrivals and departures.
- Guest verification queue.
- Room assignment.
- Assisted check-in/out.
- Room status board.
- Housekeeping tasks.
- Inspection queue.
- Maintenance tickets.
- Service requests.

### Management Pages

- KPI dashboard.
- Occupancy reports.
- Revenue reports.
- Payments and reconciliation.
- Outstanding balances.
- Refund approvals.
- Rate plans.
- Staff and permissions.
- Hotel settings.
- Audit logs.

### Interface Requirements

- Mobile-friendly guest workflows.
- Accessible forms and keyboard navigation.
- Status labels that do not depend only on color.
- Clear date, timezone, and currency labels.
- Visible payment pending states.
- Helpful error recovery.
- Dashboard refresh timestamps.

---

## 12. Management Dashboard

### Operational Summary

Display:

- Total rooms.
- Currently occupied rooms.
- Vacant and ready rooms.
- Vacant and dirty rooms.
- Out-of-service rooms.
- Today’s scheduled arrivals and departures.
- Actual check-ins and check-outs.
- Pending guest verification.
- Outstanding balances.
- Overdue housekeeping and service tasks.

Current occupancy must come from actual occupancy records.

### KPI Definitions

| KPI | Definition |
|---|---|
| Sellable room-nights | Total room-nights minus out-of-service room-nights |
| Occupancy rate | Sold room-nights ÷ sellable room-nights × 100 |
| Average Daily Rate | Net room revenue ÷ sold room-nights |
| Revenue per Available Room | Net room revenue ÷ sellable room-nights |
| Cash collected | Settled payments minus completed refunds in the period |
| Housekeeping turnaround | Room-ready timestamp minus actual checkout timestamp |
| Cancellation rate | Cancelled bookings divided by bookings in a defined creation cohort |

Use consistent policies for complimentary rooms, taxes, adjustments, and room-night classification.

Return “N/A” when a denominator is zero.

### Revenue and Cash

Revenue and cash collections are separate:

- Room revenue is reported by the configured service/recognition date.
- Cash collections are reported by payment settlement date.
- Refunds and folio credits must be handled without double-counting.

### Report Metadata

Every report should show:

- Hotel.
- Reporting period.
- Timezone.
- Currency.
- Applied filters.
- Generation timestamp.
- Relevant calculation definitions.

---

## 13. Security Requirements

### Authentication and Authorization

- Use secure, HttpOnly session cookies.
- Protect state-changing requests against CSRF.
- Apply role and object-level permissions.
- Support privileged staff MFA.
- Expire and revoke sessions appropriately.
- Rate-limit login, OTP, booking lookup, and payment initiation.

### QR and Guest Access

- Use high-entropy tokens.
- Store token hashes.
- Restrict scope and lifetime.
- Support revocation and single-use behavior where required.
- Avoid personal information in QR payloads.
- Redact tokens from logs.
- Prevent booking enumeration.

### Sensitive Documents

- Use private storage.
- Validate file types and sizes.
- Quarantine uploads for malware checks.
- Require authorization for downloads.
- Use short-lived download links.
- Apply configured retention and deletion policies.

### Payments

- Use hosted payment pages.
- Do not store card numbers or security codes.
- Store secrets only on the backend.
- Verify provider events.
- Audit refunds, adjustments, discounts, and overrides.

### Data Integrity and Recovery

- Validate inputs on the backend.
- Enforce database constraints.
- Use transactions for critical changes.
- Preserve financial history.
- Back up the database and private files.
- Test restoration.
- Redact sensitive information from logs.

Applicable guest-registration, identity, tax, and privacy requirements must be confirmed for the hotel’s jurisdiction before production use.

---

## 14. Proposed Project Structure

The following is the target implementation structure:

```text
hotel-information-management-system/
├── backend/
│   ├── config/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── hotels/
│   │   ├── rooms/
│   │   ├── guests/
│   │   ├── reservations/
│   │   ├── stays/
│   │   ├── billing/
│   │   ├── payments/
│   │   ├── housekeeping/
│   │   ├── maintenance/
│   │   ├── service_requests/
│   │   ├── reports/
│   │   └── audit/
│   ├── tests/
│   ├── manage.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── layouts/
│   │   ├── services/
│   │   └── types/
│   ├── tests/
│   └── package.json
├── docs/
│   ├── openapi.yaml
│   └── decisions/
├── infra/
│   └── docker/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .env.example
├── .gitignore
├── compose.yaml
├── CONTRIBUTING.md
└── README.md
```

---

## 15. Development Setup

> These are planned setup instructions. They become executable after the application scaffold, Compose services, dependency files, migrations, and seed command are implemented.

### Prerequisites

- Git.
- Docker with Docker Compose.
- A payment provider sandbox account for integration testing.
- Optional email/SMS sandbox credentials.

### Clone

Replace the placeholder with your repository address:

```bash
git clone https://github.com/YOUR_USERNAME/hotel-information-management-system.git
cd hotel-information-management-system
```

### Configure Environment

```bash
cp .env.example .env
```

Example configuration:

```env
APP_ENV=development

DJANGO_DEBUG=true
DJANGO_SECRET_KEY=replace-with-generated-secret
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
REDIS_URL=redis://redis:6379/0

HOTEL_TIMEZONE=Asia/Phnom_Penh
HOTEL_CURRENCY=USD
HOTEL_CHECK_IN_TIME=14:00
HOTEL_CHECK_OUT_TIME=12:00

RESERVATION_HOLD_MINUTES=15
GUEST_TOKEN_TTL_MINUTES=30
OTP_TTL_MINUTES=5

PAYMENT_MODE=sandbox
PAYMENT_PROVIDER=select-provider
PAYMENT_API_SECRET=replace-with-sandbox-secret
PAYMENT_WEBHOOK_SECRET=replace-with-sandbox-webhook-secret

PRIVATE_STORAGE_BUCKET=replace-private-bucket
NOTIFICATION_MODE=console

VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Environment variables require explicit implementation and validation.

Never commit `.env`. Frontend `VITE_*` values are public and must not contain secrets.

### Planned Startup Commands

```bash
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_demo
```

### Planned Local Addresses

| Service | Address |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/v1/ |
| API documentation | http://localhost:8000/api/docs/ |

### Demo Data

Use fictional data covering:

- Several room types.
- Ready, dirty, occupied, and maintenance rooms.
- Future reservations.
- An active stay.
- A settled sandbox payment.
- An unpaid folio.
- Housekeeping and service tasks.

Do not include production credentials or real guest documents.

---

## 16. Testing Requirements

### Backend Tests

Cover:

- Validation.
- Permissions.
- Reservation transitions.
- Allocation constraints.
- Pricing and rounding.
- Folio balances.
- Payment verification.
- Refund limits.
- Check-in/out guards.
- Reporting calculations.

### Concurrency and Integration Tests

| Scenario | Expected Outcome |
|---|---|
| Two guests reserve the same room/date range | Only one allocation succeeds |
| Adjacent bookings | Both accepted; readiness still required at arrival |
| Late payment after hold expiry | Safe reallocation or payment exception |
| Duplicate provider event | One financial effect |
| Invalid event signature | No settled payment |
| Failure event arrives after success | Settled payment remains settled |
| Guest requests another booking | Access denied |
| Replayed token | No unauthorized session |
| Check-in to dirty room | Rejected |
| Duplicate checkout request | One departure transition |
| New charge during checkout | Updated settlement required |
| Notification fails after checkout | Checkout remains complete; notification retries |
| Concurrent excessive refunds | Excess amount rejected |
| Local midnight boundary | Correct hotel dates and report totals |
| Zero reporting denominator | N/A rather than calculation error |

Run allocation and concurrency tests against PostgreSQL.

### End-to-End Acceptance

The MVP is complete when:

1. A guest can book and pay in sandbox.
2. The guest can verify and check in.
3. Staff can assist guests through an alternative workflow.
4. The guest can submit a service request.
5. Charges and payments appear correctly in the folio.
6. The guest can settle and check out.
7. Checkout triggers housekeeping.
8. Inspection returns the room to ready status.
9. Reports match the underlying records.
10. Authorization, reconciliation, and recovery checks pass.

---

## 17. Development Roadmap

| Milestone | Deliverables | Exit Condition |
|---|---|---|
| M1: Foundation | Scaffold, configuration, authentication, roles, room catalog | Controlled staff access and master data |
| M2: Booking | Quotes, availability, holds, allocations, cancellations | Conflicting bookings prevented |
| M3: Payments | Folios, sandbox checkout, verified events, refunds | Financial records reconcile |
| M4: Self-Service | QR entry, verification, check-in, checkout | Complete guest stay workflow |
| M5: Operations | Housekeeping, inspection, maintenance, requests | Consistent physical room lifecycle |
| M6: MIS and Delivery | Dashboards, reports, exports, testing, deployment | Acceptance criteria demonstrated |

A milestone requires working backend rules, permissions, failure handling, and validation—not only completed screens.

### Production Preparation

Before launch:

- Confirm hotel policies and jurisdiction requirements.
- Complete merchant onboarding.
- Configure production secrets and HTTPS.
- Review migrations and deployment procedures.
- Test backups and restoration.
- Monitor payment failures and webhook backlogs.
- Provide reception procedures for outages.
- Document support and incident responsibilities.

---

## 18. Future Improvements

- Smart-lock or key-dispenser integration.
- Multi-property management.
- Group and multi-room bookings.
- External booking-channel synchronization.
- Restaurant and POS integration.
- Dynamic pricing.
- Loyalty programs.
- Multi-language interfaces.
- Additional payment methods and currencies.
- Demand forecasting.
- Mobile staff applications.
- Automated guest messaging.

---

## 19. Contribution Guidelines

1. Create an issue describing the problem or requirement.
2. Create a short-lived feature branch.
3. Implement validation, authorization, and failure handling.
4. Add meaningful tests.
5. Update documentation and API contracts.
6. Submit a pull request with validation evidence.

Suggested branch names:

```text
feat/reservations
feat/qr-check-in
feat/payments
feat/housekeeping
feat/dashboard
fix/checkout-balance
```

Example commit messages:

```text
feat(reservations): prevent overlapping room allocations
feat(payments): process verified events idempotently
feat(stays): add guarded self checkout
fix(housekeeping): prevent duplicate checkout tasks
docs(reports): define occupancy calculations
```

Never commit:

- Production secrets.
- Real identity documents.
- Guest personal information.
- Card information.
- Unredacted production payment payloads.

---

## 20. License

No license has been selected.

Confirm project ownership and add an appropriate license before public distribution or accepting external contributions.
