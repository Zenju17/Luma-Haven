# Current backend access matrix

| Operation | Administrator | Manager | Reception | Housekeeping | Accountant | Verified booking guest |
|---|---|---|---|---|---|---|
| Public room search and quotes | Yes | Yes | Yes | Yes | Yes | Yes |
| View reservation and folio | Yes | Yes | Yes | No | Yes | Own booking only |
| Booking payment session | Yes | Yes | Yes | No | Yes | Own booking only |
| Booking check-in/out and requests | Yes | Yes | Yes | No | Yes | Own booking only |
| Staff reservation list | Yes | Yes | Yes | No | Yes | No |
| Operational summary | Yes | Yes | Yes | Redacted financials | Yes | No |
| Cleaning tasks and transitions | Yes | Yes | Yes | Except inspection approval | No | No |
| Maintenance creation and resolution | Yes | Yes | Yes | No | No | No |
| Reports and CSV | Yes | Yes | No | No | Yes | No |
| Complete guest requests | Yes | Yes | Yes | No | No | No |

An initial reservation creates a short-lived restricted guest session allowing its creator to view and pay **that booking**. After the session expires, email OTP verification is required to re-enter. Completion of check-in additionally requires a verified booking. These rules are enforced in `backend/core/views.py` and `backend/core/services.py`; further scope hardening remains in the implementation status.
