# Luma Haven — live demo guide

This is a walkthrough of the **implemented development workflow**, using fictional guests and **simulated payments**. Allow about 10–15 minutes. The hotel business date uses `Asia/Phnom_Penh`; select that date as arrival if you want to demonstrate check-in immediately. No real payment or physical-door unlocking occurs.

## 1. Start the application

Run these commands in the repository root on Fedora (fish or bash). Keep the existing, ignored `.env` configured with your Supabase **Session pooler** `DATABASE_URL` and `DJANGO_DEBUG=false`. Never paste or commit that URI.

```fish
uvx --from podman-compose podman-compose up --build -d
uvx --from podman-compose podman-compose exec backend python manage.py migrate
uvx --from podman-compose podman-compose ps
```

The migration command is safe to rerun; it applies only pending migrations. **Do not rerun `seed_demo` to recover a password**: it does not change passwords of existing users. On a new, empty development database only, create the fictional rooms and accounts once with:

```fish
uvx --from podman-compose podman-compose exec backend python manage.py seed_demo
```

| Page | Address |
|---|---|
| Guest booking and room search | <http://localhost:5173/> |
| Guest booking verification / lobby QR destination | <http://localhost:5173/verify> |
| Staff sign-in (reception, manager, housekeeping, accountant) | <http://localhost:5173/staff> |
| Administrator sign-in (`admin`) | <http://localhost:5173/admin> |
| Backend API documentation | <http://localhost:8000/api/docs/> |
| Backend health check | <http://localhost:8000/api/v1/health> |

The Django backend on port 8000 is an API; the separate Vue staff and admin portals are on port 5173 at `/staff` and `/admin`. The guest site's navigation does not link to either portal. A new booking's private page has a URL like `/booking/4`, but you must create that booking or verify access before opening it in a different browser session.

## 2. Staff test accounts

| Role | Username | Demonstration |
|---|---|---|
| Administrator | `admin` | Private admin console: operational metrics, staff roster, audit history, settings and reports |
| Manager | `manager` | Operational overview and final room inspection |
| Receptionist | `reception` | Complete guest requests and approve room inspection |
| Housekeeping | `housekeeping` | Advance cleaning to awaiting inspection; cannot approve ready status or see financial details |
| Accountant | `accountant` | Financial summary access; cannot manage cleaning tasks |

The initial seed generates one password for **newly created** accounts and prints it in the seed command's output. Passwords are intentionally **not stored in this guide**. If you have already seeded the project, use the passwords you subsequently assigned. To set a new one interactively, replace `USERNAME` with one of the names above:

```fish
uvx --from podman-compose podman-compose exec backend python manage.py changepassword USERNAME
```

Do not share passwords, OTPs or session cookies in screenshots or presentation slides. `/admin` is the application's Vue administrator console, **not** Django's built-in `/admin/`. The `admin` account signs in at `/admin`; other staff sign in at `/staff`.

**Tip:** guest, staff and admin now have independent HttpOnly sessions, so the three portals may be open in separate tabs of the same browser. You may still use a private window to keep presentation screenshots and credentials separate. Signing out of `/staff` does not sign out `/admin` or the verified guest session.

## 3. Prepare a repeatable demo

Before presenting, open `/staff` as `reception` and check the room board. Choose an **in-service, vacant, READY** room such as 101, 201 or an available suite. Room 103 may already host the seeded active stay; room 102 starts dirty; room 202 starts out of service. After previous demos, these states can differ, so use the **current board** rather than assuming a room is ready. Use only fictional names and an email address you control for the presentation; verification mail is written to backend logs rather than delivered to that mailbox.

For a single-room booking, pick **arrival = today's date in Asia/Phnom_Penh** and **departure = tomorrow**, with occupancy within the chosen room's capacity. A future-arrival booking can be paid and verified now but **cannot check in before its arrival date**. The quote expires after 10 minutes and a booking hold expires after 15 minutes; complete the booking promptly.

## 4. Present the full guest-to-staff journey

1. **Search and quote — guest window.** Visit `/`, enter the arrival/departure dates and number of guests, and click **Search rooms**. Select an available room and point out the room and tax amounts calculated by the backend. Enter fictional guest details and click **Hold this room**. Note the new **booking reference** shown on its booking page; it is different for each run.
2. **Payment — guest window.** Click **Pay balance (simulation)**. On the clearly labelled development checkout, choose **Simulate success**. Return to the booking page and show the **CONFIRMED** status and zero outstanding balance. This is a backend-processed simulation, **not a real card payment**.
3. **Verification and QR — guest window.** Visit `/verify` using **My stay** (or scan the generic QR on that page). Enter the booking reference and the same email used in step 1. Click **Send verification code**, then retrieve the code using the command in section 5 below. Enter the latest six-digit code; the app opens the private booking page. The generic QR only opens verification; a physical key is collected from reception.
4. **Check-in — guest window.** If arrival is today, the booking is verified and paid, and the room is ready, click **Check in**. Show the changed booking status and actual check-in timestamp. If the booking arrives on a future date, instead use a new booking arriving today; do not edit database dates to bypass inventory checks.
5. **Service request — guest window.** While checked in, select a service type (for example **Towels**), enter a distinctive fictional description such as “Demo presentation: extra towels” and click **Send request**. The request appears with status **SUBMITTED**; the distinctive description helps staff distinguish it from seeded requests.
6. **Staff response — private staff window.** Sign in at `/staff` as `reception` or `manager`. Find the guest request in **Guest requests** and click **Complete**. Refresh the guest booking page to show **COMPLETED**. You can also show the persisted reservation list and combined room board.
7. **Folio and checkout — guest window.** Review the itemized folio. If a balance is displayed, use the simulated checkout to settle it and return to the booking page. The current booking demo generally pays the entire room charge at step 2, so the balance will already be zero. Click **Check out** and show the confirmation/printable receipt. Checkout records the actual departure, marks the room **DIRTY** and creates a housekeeping task.
8. **Housekeeping and inspection — staff window.** On `/staff`, find the room's task. Use `housekeeping` to advance **DIRTY → CLEANING → INSPECTION** (sign out and back in when changing staff roles). Use `reception` or `manager` for the final **INSPECTION → READY** transition. Show the room board again: the room is **vacant, ready and in service**.

Optional: sign in as `admin` at `/admin` and use the **Staff accounts**, **Audit history**, **Settings** and **Reports** tabs. Set a period in Reports and download the CSV. These are backend-backed views; editing staff or hotel settings and complete financial reporting remain future work. `manager` or `accountant` may access the partial report API at `/api/v1/reports/summary?start=YYYY-MM-DD&end=YYYY-MM-DD` in their authenticated browser.

## 5. Find the one-time verification code in backend logs

**First click Send verification code in `/verify`.** Then, within five minutes, run:

```fish
podman logs --since 5m luma-haven_backend_1
```

Near the newest `Subject: Luma Haven verification code` message, find `Your verification code is ...`. If there are multiple messages, use the **most recent** code for the right fictional email. `uvx --from podman-compose podman-compose logs backend` also works, but includes older application logs and may be harder to scan. Codes expire after **5 minutes**; a new code is limited to once per **minute**. If no email message appears, check that `/verify` showed **“Check your verification message”** after you clicked Send and that the reference/email match a **confirmed or checked-in** booking. The public API never returns the code. Treat log output as private and do not paste it into chat or slides.

## 6. Stop safely

```fish
uvx --from podman-compose podman-compose down
```

This stops local app and Redis containers. **Supabase keeps the bookings and staff accounts**; the next start does not require reseeding. Do not add `-v` or delete the remote database. If the database password or `DJANGO_DEBUG` value changes in `.env`, recreate the backend, worker and beat containers so they receive the updated environment:

```fish
uvx --from podman-compose podman-compose up -d --force-recreate backend worker beat
```

This remains a development checkpoint, not a production system. See [implementation status](IMPLEMENTATION_STATUS.md) for unfinished features and tests.
