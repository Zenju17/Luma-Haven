# Luma Haven — Frontend Redesign Plan

Status: proposed (2026-11-07). Follows on from `docs/REDESIGN_PLAN.md` (2026-11-02, room photography + first guest redesign, already implemented). Applies the `frontend-design` skill
(`.claude/skills/frontend-design/SKILL.md`). Whoever implements this (Sonnet,
DeepSeek, a person) should read that skill file first, then this plan, then
work phase by phase. **Do not change backend code, API calls, query keys, or
business logic.** This is a visual and layout pass only.

---

## 1. Brief

- **Subject:** Luma Haven, one boutique hotel in Cambodia (Khmer + English, USD/KHR,
  KHQR payments). There is one property, not a marketplace. Never design it as a listing site.
- **Audiences:** (a) guests browsing and booking on phones, (b) staff (reception,
  housekeeping, accountant, manager, admin) working on desktops all day.
- **Primary jobs:** guests choose a room and dates, then pay. Staff see today's
  rooms and act fast.
- **Why redesign:** the current site reads as generated: glass cards everywhere,
  one radius and one shadow on every card, a saffron CTA plus teal, eyebrow labels,
  and the same fade-up on each section.

## 2. What we take from each reference

| Reference | Take | Leave |
|---|---|---|
| **Estates (map + detail panel)** | Dark filled filter pills with an inline ✕ for active filters, and outlined pills for inactive ones. A detail panel docked beside the browse area. A horizontal strip of compact room cards under the detail, where the selected card gets a 2px ink outline instead of a shadow. Photo dots carousel. | A full map as the main browse surface: we have one hotel, not listings. |
| **Atlanta (Choose your stay)** | A condensed serif display for room names and page titles. One long pill search bar ("Check in → Check out", guests, Search). **Horizontal stay rows** (photo / facts / a thin vertical rule / price and Select). A "More details" pill sitting on the photo. Plain-language policy notes beside the price. | The newsletter bar and the decorative wave lines. |
| **Hotel dashboard (Room View)** | Staff room detail: a big photo with fact chips laid over it (size, bed, floor), a thumbnail strip, an occupancy calendar with booked days marked, and a right-hand column list ("Rooms", "Advance booking") with chevron rows. A thin icon rail as the staff sidebar. | The generic grey dashboard chrome and the orange logo. |
| **Property map (filters)** | A left filter column with **segmented number buttons** (beds 1·2·3·4·5+), a budget range slider, and an amenity checklist. A map with photo-popover pins. | The purple accent. |

**The synthesis:** the guest **Rooms** page becomes the hero of the redesign: a
filter rail (Ref 4) + Atlanta-style stay rows (Ref 2) + an Estates-style docked
detail panel with a card strip (Ref 1). The staff **room detail** follows Ref 3.
The map idea survives in exactly one place: the **Location** section, as a drawn
neighbourhood map of the hotel's surroundings with price-pill-style pins for
nearby places (Royal Palace & Riverside, National Museum, airport).

## 3. Design tokens

### Colour: "Mekong at dusk" (replaces teal + saffron + celadon)

Avoid cream with terracotta and black with acid green. The palette comes from river
water, laterite stone and palm-leaf manuscripts.

| Token | Hex | Role |
|---|---|---|
| `--river` | `#123C3F` | Primary ink and primary buttons. Deep river teal; keeps brand continuity. |
| `--laterite` | `#9A4A2C` | One accent only: selected states, the price figure, active filter pills on guest pages. Never used for large fills. |
| `--palm-leaf` | `#EEE8D9` | Page background. A dry palm-manuscript tone, greener and greyer than "AI cream". |
| `--paper` | `#FBF9F3` | Raised surfaces (stay rows, panels). |
| `--silt` | `#5E6B66` | Secondary text and hairlines (as `color-mix(in oklab, var(--silt) 30%, transparent)` for rules). |
| `--lotus` | `#E9C9C0` | Rare highlight: booked days on calendars, the "selected" calendar range. |

Status colours for staff (keep the semantic ones already in use): available
`#2F6B4F`, occupied `#123C3F`, dirty `#B07A1E`, out of order `#8A2E2E`.

Dark mode: background `#0F1E1F`, surface `#172A2B`, text `#E9E4D6`,
laterite lifted to `#C9714C`. Keep the existing `.dark` class strategy
(`@custom-variant dark` in `src/style.css`).

### Type

- **Display:** `Libre Caslon Condensed` (Google Fonts), weights 400 and 500. Used for page
  titles, room names, and the hotel wordmark. Set it large and tight:
  `letter-spacing: -0.01em; line-height: 1.02`. This is the Atlanta move, and it is
  the one place the redesign is bold.
- **Text/UI:** `Hanken Grotesk` 400/500/600, replacing Figtree.
- **Khmer:** keep `Kantumruy Pro` as the fallback in both stacks.
- **Scale** (1.25 ratio, 16px base): 12.8 / 14 / 16 / 20 / 25 / 31 / 39 / 49 / 61px.
  Body line-height 1.55. Max line length 68ch.
- **Rules:** sentence case everywhere. No all-caps eyebrows, no monospace labels,
  no single highlighted word in headlines, and no `→` appended to buttons (the Atlanta
  search's check-in → check-out arrow is fine because it means "to").

### Shape and depth

- Radii carry hierarchy: **pills 999px** (filters, search, chips, buttons),
  **14px** for photos, **20px** for stay rows and panels, and 0 for the staff tables.
- No glass or backdrop blur. No gradient washes. Shadows only on floating
  things (popovers, the docked panel on mobile): `0 12px 32px rgb(18 60 63 / .14)`.
  Resting cards get no shadow; they sit on `--paper` against `--palm-leaf`.
- Selected = a 2px `--river` outline (Ref 1), not a lift or glow.

### Motion

One orchestrated moment: on the Home page, the hero photo un-crops (clip-path
inset 6% → 0) and the title settles once on load. Everything else moves only
in response to an action: the panel slides in on room select, the filter pill
appears on apply, and calendar range fills. Respect `prefers-reduced-motion`.

## 4. Page layouts

### 4.1 Site header (`src/layouts/SiteLayout.vue`)
```
[Luma Haven]        Rooms  Spaces  Gallery  Location      [EN|ខ្មែរ] [◐] [Book a room]
```
The wordmark is set in the display serif, not shown as an icon. The active link gets a 2px underline
offset by 6px (Ref 1). Mobile: the wordmark and a "Menu" text button open a full-height sheet.

### 4.2 Home (`HomeView.vue`, `HeroSection.vue`, `AvailabilitySearch.vue`)
```
┌───────────────────────────────────────────────────────────┐
│ Luma Haven (61px serif, left)                             │
│ A quiet room near the riverside in Phnom Penh. (20px, 1 line)      │
│ ┌─────────────────────────── full-bleed photo, 14px r ─┐ │
│ │                                                       │ │
│ └───────────────────────────────────────────────────────┘ │
│  ( Check in → Check out | 2 adults ⌄ |  Search rooms )   │ ← Atlanta pill bar, overlapping photo bottom edge by 50%
└───────────────────────────────────────────────────────────┘
 Room types: 3 horizontal stay rows (same component as Rooms)
 Location: drawn neighbourhood map + pins (see 4.6)
 Stay steps: only if real sequence (arrive, check in, stay, check out) → numbers allowed here
```
Left-aligned throughout. Remove the keycard monogram, the glass hero card, and the
`ExperienceSection` icon grid (replace it with two photo-and-sentence pairs, or delete it).

### 4.3 Rooms: the centrepiece (`RoomsView.vue`)
Desktop ≥1100px:
```
┌ filters 260px ─┐┌ stay rows (fluid) ───────────────┐┌ detail 400px (on select) ┐
│ Dates          ││ [Type: Deluxe ✕][≤$120 ✕] Sort ⌄││ photo, dots, 4.8 chip      │
│ Guests  1 2 3 4││ ┌photo┐ Deluxe King   │ from    ││ Deluxe King (39px serif)   │
│ Beds    1 2 3+ ││ │more │ 🛏2 👤3 28m² │ $95/nt  ││ bed · bath · size icons     │
│ Budget ──●──── ││ └─────┘ amenities x4  │[Select] ││ description 3 lines + more │
│ ☐ Balcony      ││         policy note   │         ││ $95 / night   [Book room]  │
│ ☐ Bathtub      ││ ───────────────────────────────  ││ ─ other rooms strip ─────  │
│ [Apply]        ││ next row…                         ││ [card][card*][card] →      │
└────────────────┘└──────────────────────────────────┘└────────────────────────────┘
```
- The filter rail is from Ref 4: segmented buttons, range slider, checklist. Active filters
  are mirrored as dark `--river` pills with ✕ above the list (Ref 1). On mobile the rail becomes a
  "Filters (2)" pill that opens a bottom sheet.
- Each stay row is from Ref 2: the thin vertical rule before the price column, with the price in `--laterite`.
  Show live availability ("3 left for these dates") as plain text, with no badge.
- The detail panel is from Ref 1. It docks right on desktop and becomes a full sheet on mobile. Its card strip
  scrolls horizontally with snap; the selected card gets a 2px outline.
- Keep every existing data hook, query and emit. Only markup and CSS change.

### 4.4 Booking / Checkout / Verify
A two-column layout: form left (max 560px), and a sticky "Your stay" summary card right
(photo thumb, room name in serif, dates, nights, total in `--laterite`).
KHQR: the QR sits on `--paper` with a 14px radius, the amount in large serif above it, and
"Waiting for payment…" as live text with no spinner gimmick. Errors say what happened
and what to do.

### 4.5 Gallery / Spaces
A masonry of photos with 14px radius and captions below in 14px `--silt`. RoomTourModal and
RoomSpacesModal reuse the Ref 3 layout: a big photo, fact chips laid over the top-right, and a
thumbnail strip at the bottom-left.

### 4.6 Location (`LocationSection.vue`)
An inline SVG neighbourhood map in two tones (`--palm-leaf` land, a `--river` 15% river
band) with white pill pins in the Ref 1 price-pill style: "Royal Palace & Riverside", "National Museum of Cambodia",
"Phnom Penh International Airport · 35 min drive" (names and times as already in `LocationSection.vue`). The hotel pin is a filled `--river` dot.
No map library and no tiles.

### 4.7 Staff portal (`PortalLayout.vue`, all `features/{reception,housekeeping,manager,accountant,admin}`)
```
┌rail┐┌ Today, 7 Nov ─────────────── search ─ [◐] [avatar] ┐
│ ⌂  ││                                                    │
│ 🛏 ││  content                                            │
│ ✓  ││                                                    │
│ $  ││                                                    │
│ ⚙  ││                                                    │
└────┘└────────────────────────────────────────────────────┘
```
- Replaces the current wide brand rail in `PortalLayout.vue` (logo, tagline, theme toggle). Keep `ThemeToggle` and the mobile header. A 64px icon rail with labels shown as tooltips, plus a visible text label for the active item (Ref 3).
- Staff use **Hanken Grotesk only**; the serif appears only in the page title.
- Tables: zero radius, 1px hairlines, 44px rows, tabular numbers, status as a coloured
  dot plus a word (never colour alone).
- Room detail (reception/admin) is Ref 3: a photo with overlaid chips (size, bed, floor), a month
  calendar with booked nights in `--lotus` and arrival/departure ends in `--laterite`,
  and a right column of chevron rows (Bed, Bathroom, Accessibility…) and upcoming bookings.
- The Manager dashboard shows the numbers people act on (arrivals, departures, dirty rooms,
  unpaid folios) as plain rows with counts. **No "big number + gradient" KPI tiles.**

## 5. Implementation phases

Do them in order. Each phase ends with:
`npm --prefix frontend run typecheck && npm --prefix frontend run build`,
and a visual check at 375px, 768px and 1440px in both light and dark.

1. **Tokens and fonts.** Rewrite the `:root` and `.dark` token blocks in `src/style.css`.
   Load Libre Caslon Condensed and Hanken Grotesk (keep Kantumruy Pro) in `index.html`.
   Keep the old token *names* as aliases to the new values for now, so nothing breaks.
   Delete the glass utilities and generic fade-up animations.
2. **Primitives** in `src/components/`: `PillButton`, `FilterPill` (active/inactive, ✕),
   `SegmentedNumber`, `RangeSlider`, `FactChip`, `StayRow`, `DetailPanel`, `CardStrip`,
   `MonthCalendar`. Use plain Vue + CSS with no new dependencies.
3. **Site header and footer** (`SiteLayout.vue`).
4. **Rooms page** (4.3). This is the most visible change, so do it before Home.
5. **Home** (4.2), including AvailabilitySearch as the pill bar, and **Location** (4.6).
6. **Booking / Checkout / Verify / PrintableReceipt screen styles** (4.4). Do not touch print CSS
   unless it breaks.
7. **Gallery / Spaces / modals** (4.5).
8. **Staff portal shell and tables** (4.7), then each workspace one at a time.
9. **Cleanup.** Remove the alias tokens and unused CSS from `style.css` (it is about 1,200 lines now and should
   end well under half that), and run the Playwright e2e suite (`npm run test:e2e`) if it is set up.

## 6. Guardrails for the implementer

- Keep route paths and emitted events. The e2e suite (`frontend/tests/workflow.spec.ts`) selects by role and accessible name (e.g. dialog "Staff agreement", button "Accept and continue", textbox "Username"), so keep those labels and roles exactly.
- Language is `useLanguage()` (`en` | `km`, `src/composables/useLanguage.ts`); it currently drives the footer, legal pages and consent. Keep it and test one page in `km`.
- Money display stays as it is formatted today (integer minor units → formatter); do not
  reformat currency logic.
- Accessibility floor: visible `:focus-visible` ring (2px `--laterite`, 2px offset),
  4.5:1 text contrast, 44px touch targets, and reduced motion.
- Before calling a phase done, compare it against the "AI tells" list in the skill
  (eyebrows, middle-dot meta strings, identical cards, `→` buttons, cream+clay).
  If the result looks like that list, revise it.
- Commit per phase on `feat/hotel-management-system`. Don't merge or rebase with `main`.
- After finishing: update `docs/IMPLEMENTATION_STATUS.md`, `docs/HANDOVER.md`, and add
  a `docs/DECISIONS.md` entry for the palette and type change.
