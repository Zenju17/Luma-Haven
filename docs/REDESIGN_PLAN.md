# Guest UI Redesign + Room Photography — Implementation Plan (for Sonnet)

> Written 2026-11-02. Executor: Claude Sonnet. Read `AGENTS.md` first, then this file.
> Scope: **guest-facing frontend** (`frontend/src/features/guest/**`, `layouts/SiteLayout.vue`,
> `components/**`, `style.css`) plus demo seed data. Staff portals only inherit the new tokens —
> do not restructure them.

## 0. Setup

1. Install the design skill the owner asked for:
   `npx skills add anthropics/skills --skill frontend-design`
   Then invoke `frontend-design` and follow it for every visual decision below.
2. Branch: stay on `feat/hotel-management-system` (never merge/rebase with `main`).
3. Start disposable test DB on `127.0.0.1:55432` only. Never touch Supabase. Never print `.env`.

## 1. Room photography (10 owner-supplied photos)

Source files (copy, don't move):
`/home/heng/.claude/uploads/a1172b4a-e897-473b-9902-eea1211efb69/`

Copy each into `frontend/public/images/luma-haven/rooms/<slug>/main.jpg`, convert to WebP
(keep the JPG as fallback), max width 1600px, and record real width/height.

| # | Source file | Slug | Room type name (seed) | Beds / cap | What the photo shows |
|---|---|---|---|---|---|
| 1 | `868524fe-image.jpg` | `riverfront-suite` | Riverfront Suite | 1 King · 2 | Corner suite, floor-to-ceiling river view, lounge |
| 2 | `0006907d-image.jpg` | `signature-suite` | Signature Suite | 1 King · 2 | Bedroom + lounge split by walnut divider |
| 3 | `5577f240-image.jpg` | `connecting-family` | Connecting Family Rooms | 2 Queen + 2 Queen · 6 | Two rooms joined by connecting doors |
| 4 | `34dafcc6-image.jpg` | `family-suite` | Family Suite | 1 King + 1 Single · 3–4 | King plus extra bed |
| 5 | `12ef12c4-image.jpg` | `triple-room` | Triple Room | 3 Single · 3 | Three single beds |
| 6 | `0de407d7-image.jpg` | `garden-king` | Garden King | 1 King · 2 | Warm oak timber, lounge sofa |
| 7 | `a6c178bc-image.jpg` | `city-king` | City King | 1 King · 2 | King, sofa nook, sheer city-view curtains |
| 8 | `464a92d5-image.jpg` | `double-queen` | Double Queen | 2 Queen · 4 | Two queens, desk, TV |
| 9 | `1f6341d5-image.jpg` | `city-twin` | City Twin | 2 Single · 2 | Twin beds, green view |
| 10 | `12237b5b-image.jpg` | `classic-queen` | Classic Queen | 1 Queen · 2 | Compact queen, tall window |

Implementation:

1. `frontend/src/data/hotelImages.ts`: widen `roomType` to the 10 slugs (keep old
   `deluxe|premier|suite` entries for the gallery, but stop using them for room cards).
   Add one `rooms` record per slug, `isDemo: true`, `isPlaceholder: false`, honest `alt` text
   describing the photo (no invented facilities — e.g. don't claim "river view" in copy for a
   room that isn't real; captions say "Representative photo").
2. Add `roomImageFor(roomTypeName: string): HotelImageRecord` — slugify the API name
   (`'Garden King' → 'garden-king'`), return the match, else a neutral fallback
   (`/images/luma-haven/rooms/deluxe/main.jpg`). Unit-test the slug + fallback.
3. Replace every room-type image lookup (`RoomsView.vue`, `FeaturedRoomTypes.vue`,
   `BookingView.vue`, `CheckoutView.vue`, `RoomTourModal.vue`, `RoomSpacesModal.vue`,
   reception room picker if it shows images) with `roomImageFor`. Delete the
   `public/images/rooms/*.svg` placeholders once nothing references them (`grep -rn "rooms/.*svg"`).
4. Use `<HotelImage>` with `loading="lazy"`, explicit width/height (no layout shift),
   `object-fit: cover`, 4:3 card ratio.
5. `backend/core/management/commands/seed_demo.py`: add the 7 new room types
   (idempotent `get_or_create`, money in integer minor units, sensible USD rates, e.g.
   Classic Queen 6500 … Riverfront Suite 24000) with 1–2 rooms each and real amenity lists.
   Existing 3 names must stay unchanged so existing data still maps. No model change →
   no migration; confirm with `makemigrations --check`.

## 2. Three-colour palette (replace the generic teal/brass)

Identity: "Mekong evening" — warm, local, not template-y. Exactly three brand colours;
everything else is derived tints/shades of them plus neutral ink.

| Role | Name | Hex | Use |
|---|---|---|---|
| Primary | **Mekong Teal** | `#0E4A4C` | Header, primary buttons, links, focus rings |
| Accent | **Saffron** (shipped; replaced Lotus Clay) | `#EBA742` | The ONE call to action per screen ("Book this room", "Search"), price highlights, selected states |
| Base | **Celadon** (shipped; replaced Rice Paper) | `#E4EDE6` | Page background, cards on dark, light-theme surfaces |

Rules:
- Define as `--brand-teal`, `--brand-clay`, `--brand-paper` on `:root` in `style.css`; map all
  existing semantic tokens (`--deep`, `--brass`, `--btn-primary-bg`, …) onto them so staff
  portals change automatically. Remove now-unused tokens.
- Text ink `#1C2526`, muted `#5B6567` (neutrals, not brand colours).
- Dark theme: background = teal shade `#0A2E30`, surfaces `#123B3D`, text = Rice Paper,
  clay stays the accent (lighten to `#E07A50` for contrast).
- Every text/background pair must pass WCAG AA (4.5:1 body, 3:1 large). Clay on paper for
  small text fails — use clay for buttons with white text (check ≥4.5:1, darken to `#B5552F`
  if needed) and teal for body links.
- Typography: one display serif for headings (e.g. "Fraunces"), keep "DM Sans" for UI.

## 3. Ease-of-use redesign (guest flow)

Goal: a first-time guest books in ≤3 screens without reading instructions.

1. **Home**: hero with photo #1, headline + one sticky availability bar
   (dates · guests · Search). Below: "Choose your room" grid (all 10 types), then trust strip
   (free cancellation policy, pay at hotel/KHQR-coming, location), then gallery.
   Cut decorative sections that don't help booking.
2. **Rooms list**: filter chips (Guests, Beds: King/Queen/Twin/Family, Price), each card =
   photo, name, bed icon + capacity icon, 3 key amenities, "from $X / night" in clay, one
   button. Sold-out cards greyed with "Try other dates".
3. **Room detail / booking**: big photo, plain-language facts list, price breakdown
   (nights × rate, taxes, total) always visible on desktop (sticky side) and as a bottom bar
   on mobile.
4. **Checkout**: progress indicator "1 Dates · 2 Your details · 3 Pay"; inline field
   validation with human messages; keep the payment-emulator banner honest (it's not real).
5. General: mobile-first (test 375px), tap targets ≥44px, visible focus, icons always paired
   with labels, Khmer/English toggle keeps working (`useLanguage`), empty/loading/error states
   on every API call, no hover-only information.
6. Avoid "generic AI" look: no purple gradients, no glassmorphism everywhere, no emoji
   icons, no centered-everything; use asymmetric photo-led layouts, real photography,
   restrained motion (one fade-up on scroll, respects `prefers-reduced-motion`).

## 4. Order of work (commit after each)

1. Palette tokens + fonts (`style.css`) → typecheck/build.
2. Room images + `roomImageFor` + seed → tests.
3. Home + Rooms list redesign.
4. Booking + Checkout redesign.
5. Polish pass: dark mode, a11y contrast check, mobile, Khmer strings.

Commits: no Claude attribution lines (owner rule).

## 5. Definition of done

```bash
.venv/bin/python backend/manage.py check
.venv/bin/python backend/manage.py makemigrations --check --dry-run
env DATABASE_URL=postgresql://hims_test:local-integration-only@127.0.0.1:55432/postgres \
  .venv/bin/python -m pytest -c backend/pytest.ini backend/tests -q
npm --prefix frontend run typecheck && npm --prefix frontend run build
```
- Update E2E selectors/headings that changed and run the E2E suite.
- Screenshot Home, Rooms, Booking, Checkout at 375px and 1440px, light + dark, and check them.
- Update `docs/IMPLEMENTATION_STATUS.md`, `docs/HANDOVER.md`; add a `docs/DECISIONS.md`
  entry for the palette and the slug-based room-image mapping (and why no DB image field yet:
  a `RoomType.cover_image` field via the existing media assets is the follow-up).
