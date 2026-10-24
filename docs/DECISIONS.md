# Implementation decisions

- The initial property is a single hotel in `Asia/Phnom_Penh`, billing in USD minor units. The hotel row stores configurable contact details, tax, deposit percentage and arrival/departure times. Policy enforcement beyond full settlement is still pending.
- One room is selected per booking. PostgreSQL `daterange` allocations are half-open and an exclusion constraint is the final arbiter of inventory collisions. A `btree_gist` extension is installed in the initial migration.
- Booking immediately creates a short-lived guest browser session to access its hold and simulated checkout. Subsequent access from another browser requires email OTP; the OTP is hashed and sent to the console email backend. A confirmed booking must be verified before check-in.
- The simulated checkout creates backend payment events and can produce pending, failed, and successful results. It is deliberately unavailable outside development. A real payment provider interface, authenticated webhooks, refunds and reconciliation are **not implemented**.
- Key handover is at reception. The QR is a generic link to the verification page and never grants physical room access.
- PostgreSQL is required for migrations and tests; SQLite does not support the exclusion constraint. There is no local PostgreSQL or Docker installation in the current execution environment.
- The backend currently uses one `core` Django module as an early vertical slice. Domain splitting can follow stable API boundaries; empty apps have not been generated.
