# Luma Haven — Management Information System (MIS) Demonstration

## Executive Summary

Luma Haven is an enterprise-grade luxury boutique hospitality Management Information System (MIS). It bridges hotel front-desk operations, housekeeping, guest self-service, and executive management.

The central thesis of the system is the closed-loop MIS cycle:

$$\text{Hotel Transaction} \longrightarrow \text{Validated Database Record} \longrightarrow \text{Accurate Management Information} \longrightarrow \text{Management Decision}$$

This document demonstrates how operational transactions in Luma Haven are captured under strict relational constraints, aggregated into accurate management indicators without statistical distortions, surfaced through executive dashboards and decision-support alerts, and resolved through auditable workflows.

---

## 1. System Scope, Users & Architectural Boundaries

### Single-Hotel Architectural Boundary
Luma Haven is purposefully scoped and explicitly modeled as a **single luxury boutique property** (`Hotel` singleton with `time_zone = 'Asia/Phnom_Penh'`). It avoids misleading "chain/multi-property" placeholders. All operational dates, night-audit cutoffs, revenue attribution dates, and occupancy calculations are anchored to this explicit hotel timezone rather than ambiguous server UTC offsets.

### User Roles & Segregation of Duties
| Role | Portal Route | Primary Responsibilities | Data Governance & Permissions |
|---|---|---|---|
| **Guest** | `/`, `/booking/:id`, `/verify` | Search, quote, reserve, self-check-in, service requests, folios, self-checkout | Public catalog access only; zero visibility into cleaning status, maintenance blocks, or other guests' folios. Verified via HMAC/OTP. |
| **Receptionist** | `/staff` | Check-in/out, room reassignments, amendments, no-shows, initial refund requests, room board inspection | Full operational visibility of today's movements, service requests, and room allocations. Read-only on rates. Cannot approve or settle refunds. |
| **Housekeeping** | `/staff` | Room cleaning lifecycle (`DIRTY` $\rightarrow$ `CLEANING` $\rightarrow$ `INSPECTION`), cleaner task assignments | Operational room board and assigned task queue. Cannot inspect own cleaning (requires manager/reception inspection). No access to financial folios. |
| **Accountant** | `/staff`, `/reports/*` | Financial reconciliation, accounts receivable, settled cash, ledger auditing | Read-only operational records, full financial report access, export capabilities. No room status modification permissions. |
| **General Manager** | `/manager`, `/staff` | Operational oversight, Decision Support alerts, rate management, cleaner dispatch, refund approvals | Executive dashboard, pricing adjustments, operational overrides, refund sign-off. |
| **Administrator** | `/admin` | Staff identity & roster management, hotel settings, audit logs, raw data export, server maintenance | Master administrative control, credential synchronization, high-level governance. |

---

## 2. The Core MIS Loop: From Transaction to Decision

```mermaid
flowchart TD
    subgraph T["1. Transaction Layer"]
        T1["Guest Books Room / Checks Out Early"]
        T2["Staff Reports Maintenance Ticket"]
        T3["Guest Requests Refund for Cancellation"]
    end

    subgraph D["2. Validated Persistence Layer"]
        D1["PostgreSQL Exclusion Constraints (btree_gist)"]
        D2["select_for_update() Row Locks"]
        D3["Double-entry Folio & Payment Settlement"]
    end

    subgraph I["3. Management Information Layer"]
        I1["8 Core Real-Time KPIs (ADR, RevPAR, Occupancy)"]
        I2["Daily Trend Curves & Room-Type Profitability"]
        I3["Scheduled Snapshot & Sanitized CSV Reports"]
    end

    subgraph M["4. Decision Support & Action Layer"]
        M1["Attention Needed Alerts (4-Part Context)"]
        M2["Two-Person Refund Approval & Settlement"]
        M3["Dynamic Rate Adjustment & Cleaner Dispatch"]
    end

    T1 --> D1
    T2 --> D1
    T3 --> D3
    D1 --> I1
    D2 --> I1
    D3 --> I2
    I1 --> M1
    I2 --> M1
    I3 --> M2
    M1 --> M3
    M2 --> D3
    M3 --> T1
```

---

## 3. Core Operational Metrics & KPIs: Precision Definitions

Every metric in Luma Haven is computed directly on PostgreSQL using validated database records. Denominators are strictly guarded against zero-division anomalies.

### Metric 1: Sellable Room-Nights
- **Definition:** Total available physical room-inventory nights across the period minus room-nights blocked by out-of-service maintenance tickets.
- **Formula:**
  $$\text{Sellable Nights} = (\text{Total Active Rooms} \times \text{Days in Period}) - \sum_{\text{tickets}} \text{Overlap Nights}$$
- **Edge Case Handling:** Rooms blocked for maintenance are completely excluded from the sellable inventory denominator, preventing false revPAR deflation.

### Metric 2: Sold Room-Nights
- **Definition:** The count of distinct room-date nights occupied by confirmed, checked-in, or checked-out reservations.
- **Formula:**
  $$\text{Sold Nights} = \sum_{\text{stays}} \text{Overlap Nights with Period}$$
- **Edge Case Handling:**
  - *Early Checkouts:* When a guest checks out early, the allocation interval in `Reservation` is updated to reflect the actual departure date. Unused future nights immediately return to available inventory and are not counted as sold.
  - *No-Shows & Cancellations:* Never counted as sold room-nights.

### Metric 3: Occupancy Rate (%)
- **Definition:** The percentage of sellable room-nights that were actively occupied by staying guests.
- **Formula:**
  $$\text{Occupancy} = \begin{cases} \left(\frac{\text{Sold Room-Nights}}{\text{Sellable Room-Nights}}\right) \times 100 & \text{if Sellable Nights} > 0 \\ \text{N/A} & \text{if Sellable Nights} = 0 \end{cases}$$
- **Edge Case Handling:** Returns `N/A` rather than 0% or crashing if all rooms are out of service.

### Metric 4: Average Daily Rate (ADR)
- **Definition:** Average room rental revenue earned per paid sold room-night.
- **Formula:**
  $$\text{ADR} = \begin{cases} \frac{\text{Net Room Revenue on Service Dates}}{\text{Sold Room-Nights}} & \text{if Sold Nights} > 0 \\ \text{N/A} & \text{if Sold Nights} = 0 \end{cases}$$
- **Edge Case Handling:** Computed strictly on sold room-nights. Unsold capacity does not dilute ADR.

### Metric 5: Revenue Per Available Room (RevPAR)
- **Definition:** Total room revenue divided by total sellable room-nights.
- **Formula:**
  $$\text{RevPAR} = \text{ADR} \times \text{Occupancy Rate} = \frac{\text{Net Room Revenue}}{\text{Sellable Room-Nights}}$$
- **Edge Case Handling:** Accurately reflects both occupancy and pricing performance across available inventory.

### Metric 6: Service-Date Net Room Revenue
- **Definition:** Room charge revenue attributed to the night the service was consumed, rather than the lump-sum booking deposit date.
- **Formula:**
  $$\text{Service-Date Revenue} = \sum_{r \in \text{Reservations}} \left( \frac{\text{Total Room Charge}}{\text{Stay Nights}} \times \text{Overlapping Nights} \right)$$
- **Accounting Principle:** Accrual accounting; matches revenue to room-night occupancy.

### Metric 7: Net Settled Cash Collected
- **Definition:** Actual cash inflow collected via settled payment transactions within the selected calendar window, minus any cash refunds settled in the same period.
- **Formula:**
  $$\text{Net Cash} = \sum \text{Settled Payments} - \sum \text{Settled Refunds}$$
- **Timezone Precision:** Filtered by `created_at` timestamp in hotel local time (`Asia/Phnom_Penh`).

### Metric 8: Outstanding Balances (Folio Accounts Receivable)
- **Definition:** Unpaid charges remaining on active or completed reservations where folio charges exceed settled payments.
- **Formula:**
  $$\text{Folio Balance} = \sum \text{Folio Charges} - \sum \text{Folio Credits} - \sum \text{Settled Payments}$$
- **Risk Mitigation:** Highlighted prominently on the manager dashboard and reception departure queue to prevent uncollected checkouts.

### Metric 9: Housekeeping Turnaround Time
- **Definition:** Average elapsed duration in minutes from room checkout (`DIRTY` task creation) until room is approved as `READY` by housekeeping and inspection.
- **Formula:**
  $$\text{Turnaround} = \frac{1}{N} \sum_{i=1}^N \left( t_{\text{ready}} - t_{\text{created}} \right)$$

---

## 4. Decision Support System: The 7 Transparent Business Rules

The Luma Haven Decision Support engine evaluates all operational records against seven transparent rules on every request. Alerts are returned with an actionable 4-part structure:
1. **What Happened:** Concise, factual description of the anomaly or condition.
2. **Records Involved:** Exact room numbers, reservation references, or transaction IDs.
3. **Why It Matters:** Business consequence (revenue loss, guest dissatisfaction, audit vulnerability).
4. **Recommended Action:** Concrete operational step to resolve the situation.

| Rule Name | Severity | Condition Evaluated | Impact & Action |
|---|---|---|---|
| **High Unpaid Balances on Departure** | `URGENT` | Reservations with departure today or earlier having balance $> \$0.00$. | Prevents guest walkout without settling charges. Recommends front desk collect payment prior to key return. |
| **Pending Refund Requests** | `WARNING` | Refund requests in `SUBMITTED` state requiring manager review. | Maintains regulatory compliance and guest goodwill. Recommends manager review and approve or reject. |
| **Maintenance-Blocked Room Bottlenecks** | `WARNING` | Active maintenance tickets on rooms with upcoming check-ins in the next 48 hours. | Avoids room shortage at check-in. Recommends prioritizing engineering or executing proactive room reassignment under lock. |
| **Housekeeping Turnaround Degradation** | `WARNING` | Dirty rooms awaiting cleaning for $> 120$ minutes while arrival count $> 0$. | Prevents arrival delays. Recommends reallocating housekeeping staff to priority rooms. |
| **Low Occupancy Pricing Opportunity** | `INFO` | Occupancy for upcoming 7-day period $< 40\%$. | RevPAR underperformance. Recommends promotional rate reduction or corporate package release. |
| **Stale Unverified Bookings** | `INFO` | Unpaid holds within 30 minutes of expiration or unverified confirmed bookings. | Free up inventory for walk-ins or prompt guest communication. |
| **Unassigned Housekeeping Tasks** | `WARNING` | Dirty or cleaning rooms with no staff member assigned. | Eliminates accountability gaps. Recommends manager assign cleaner. |

---

## 5. Enterprise Workflows & Operational Controls

### Two-Person Refund Review & Segregation of Duties
To eliminate cash leakage and fraud, refunds enforce strict separation:
1. **Initiation:** Receptionist or guest creates a refund request with an auditable reason (`SUBMITTED`).
2. **Approval:** A Manager or Administrator reviews the request and either approves (`APPROVED`) or rejects (`REJECTED`) it.
3. **Settlement:** Once approved, the refund is executed (`SETTLED`). The backend creates an auditable `Folio` credit entry, adjusting the reservation balance and cash reconciliation ledger under database transaction locks.

### Safe Reservation Amendments & Reassignments Under Lock
All date modifications, occupancy updates, and room transfers use PostgreSQL row-level locks:
- `select_for_update()` locks target room and reservation rows.
- The `Reservation` table's PostgreSQL exclusion constraint (`EXCLUDE USING gist (room_id WITH =, stay WITH &&)`) guarantees no overlapping bookings can ever be persisted, preventing double-bookings even under extreme concurrent requests.

### Data Governance & Public Security
- **Public API Isolation:** The guest-facing `/rooms` endpoint returns strictly public catalog data (`id`, `number`, `type`, `capacity`, `description`, `amenities`, `rate_minor`). Operational fields (`cleaning`, `in_service`, `occupied`) are completely suppressed.
- **CSV Formula Injection Sanitization:** All CSV exports sanitize text cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` by prefixing a single quote (`'`), neutralizing spreadsheet formula execution attacks.

---

## 6. Scheduled MIS Reports & Background Tasks

Luma Haven provides five authorized reports accessible to Managers, Accountants, and Administrators:
1. **Daily Operational Summary (`/reports/daily-summary`):** Complete overview of arrivals, departures, stayovers, sold/sellable rooms, and cash flow.
2. **Revenue & Occupancy Analysis (`/reports/revenue-occupancy`):** Detailed breakdown of ADR, RevPAR, and room-type utilization across date ranges.
3. **Cash Reconciliation Ledger (`/reports/cash-reconciliation`):** Audit of all payments, payment methods, and settled refunds.
4. **Housekeeping Turnaround Report (`/reports/housekeeping-turnaround`):** Turnaround velocity and room cleaning efficiency.
5. **Accounts Receivable Aging (`/reports/accounts-receivable`):** Unpaid balances grouped by reservation aging and check-out status.

All reports support 1-click **CSV Export** with cell sanitization.

### Celery Beat Daily Snapshot Task
The background task `archive_daily_mis_snapshot` runs automatically via Celery Beat every night at 23:59 hotel time. It computes and archives daily KPI snapshots into persistent storage for historical reporting and trend analysis.

---

## 7. Verification Evidence & Test Execution

### Automated Pytest Suite (37/37 Passed)
Executed inside the container environment against isolated PostgreSQL:
```bash
podman exec luma-haven_backend_1 pytest --reuse-db
```
- **Password Governance:** 2 tests covering safe hashing, credential rotation, and permission checks.
- **Portal & Session Isolation:** 2 tests verifying separate HttpOnly cookies (`sessionid`, `staff_sessionid`, `admin_sessionid`).
- **Core Operations:** 18 tests covering bookings, allocations, half-open date intervals, check-in/out, and inspection transitions.
- **MIS Metrics & Workflows (`test_mis_reports.py`):** 15 tests verifying:
  - Exact ADR, RevPAR, and occupancy formulas
  - Zero-denominator handling (`N/A`)
  - Maintenance ticket exclusion from sellable room-nights
  - Early checkout inventory restoration
  - Refund approval & folio balance adjustment
  - 7 Decision Support rules
  - CSV formula injection sanitization
  - Role-based permissions on report endpoints

### Automated Playwright E2E Tests (3/3 Passed)
Executed against isolated PostgreSQL test database:
```bash
env E2E_DATABASE_URL=postgresql://hims_test:local-integration-only@127.0.0.1:55432/postgres npm --prefix frontend run test:e2e
```
1. **Guest Journey (18.0s):** Booking search $\rightarrow$ server quote $\rightarrow$ reservation hold $\rightarrow$ simulated payment $\rightarrow$ OTP verification $\rightarrow$ self check-in $\rightarrow$ service request submission $\rightarrow$ staff fulfillment $\rightarrow$ checkout $\rightarrow$ housekeeping room transition (`DIRTY` $\rightarrow$ `CLEANING` $\rightarrow$ `INSPECTION` $\rightarrow$ `READY`).
2. **Role & Session Isolation (12.3s):** Verified public catalog cannot access staff endpoints; simultaneous staff and admin logins with independent session state; staff password rotation via admin console with audit trail.
3. **MIS Manager Journey (2.9s):** Manager login $\rightarrow$ Executive dashboard load $\rightarrow$ Date range filtering $\rightarrow$ 8 KPI cards verified with formulas $\rightarrow$ Decision Support "Attention Needed" alerts $\rightarrow$ Room type comparison breakdown $\rightarrow$ Report CSV download and verification.
