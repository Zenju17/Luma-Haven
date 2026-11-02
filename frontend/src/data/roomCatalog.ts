// Guest-facing room catalogue. Names must match RoomType.name in the backend
// (seed_demo.py) — photos are resolved by slugified name via roomPhotoFor().

export type BedKind = 'King' | 'Queen' | 'Twin' | 'Family'

export interface RoomCatalogEntry {
  slug: string
  name: string
  beds: string
  bedKind: BedKind
  capacity: number
  fromRate: number // display hint only (USD); the server quote is authoritative
  summary: string
  highlights: string[]
  photo: string
  photoAlt: string
}

const photo = (slug: string) => `/images/luma-haven/rooms/${slug}/main.jpg`

export const ROOM_CATALOG: RoomCatalogEntry[] = [
  {
    slug: 'classic-queen', name: 'Classic Queen', beds: '1 queen bed', bedKind: 'Queen', capacity: 2, fromRate: 65,
    summary: 'A calm, compact room with a tall window and a reading chair. Good for a short city stay.',
    highlights: ['Tall window', 'Reading chair', 'Rain shower'],
    photo: photo('classic-queen'), photoAlt: 'Queen bed with dark headboard beside a tall window with sheer curtains',
  },
  {
    slug: 'city-twin', name: 'City Twin', beds: '2 single beds', bedKind: 'Twin', capacity: 2, fromRate: 72,
    summary: 'Two single beds and a window over the treetops. Easy for friends or colleagues.',
    highlights: ['Two single beds', 'Window view', 'Armchair'],
    photo: photo('city-twin'), photoAlt: 'Two single beds with warm wall lights and a window looking onto green trees',
  },
  {
    slug: 'city-king', name: 'City King', beds: '1 king bed', bedKind: 'King', capacity: 2, fromRate: 80,
    summary: 'A king bed and a long sofa by full-height sheer curtains. Room to stretch out after a busy day.',
    highlights: ['King bed', 'Window sofa', 'Soft wall lighting'],
    photo: photo('city-king'), photoAlt: 'King bed with a blue throw beside an armchair and full-height sheer curtains',
  },
  {
    slug: 'garden-king', name: 'Garden King', beds: '1 king bed', bedKind: 'King', capacity: 2, fromRate: 85,
    summary: 'Warm oak walls, paper lanterns and a corner sofa. Our quietest king room.',
    highlights: ['King bed', 'Oak-panelled walls', 'Coffee corner'],
    photo: photo('garden-king'), photoAlt: 'King bed against an oak-slat wall beside floor-to-ceiling windows onto a garden',
  },
  {
    slug: 'double-queen', name: 'Double Queen', beds: '2 queen beds', bedKind: 'Queen', capacity: 4, fromRate: 95,
    summary: 'Two queen beds, a work desk and a TV. Fits a small family or four friends.',
    highlights: ['Two queen beds', 'Work desk', 'Smart TV'],
    photo: photo('double-queen'), photoAlt: 'Two large beds with teal cushions beside warm curtains and a window seat',
  },
  {
    slug: 'triple-room', name: 'Triple Room', beds: '3 single beds', bedKind: 'Twin', capacity: 3, fromRate: 105,
    summary: 'Three single beds in a row, so nobody shares. Popular with groups and families with teens.',
    highlights: ['Three single beds', 'Desk', 'Blackout curtains'],
    photo: photo('triple-room'), photoAlt: 'Three single beds side by side with a desk and floor lamp',
  },
  {
    slug: 'family-suite', name: 'Family Suite', beds: '1 king + 1 single bed', bedKind: 'Family', capacity: 4, fromRate: 155,
    summary: 'A king bed plus a single for a child, with a long bench and desk space.',
    highlights: ['King + single bed', 'Extra floor space', 'Desk'],
    photo: photo('family-suite'), photoAlt: 'King bed and a separate single bed with a bench at the foot of the king',
  },
  {
    slug: 'connecting-family', name: 'Connecting Family Rooms', beds: '2 rooms, 2 queen beds each', bedKind: 'Family', capacity: 6, fromRate: 190,
    summary: 'Two rooms joined by a private door. Each side has its own beds and bathroom.',
    highlights: ['Two private rooms', 'Connecting door', 'Two bathrooms'],
    photo: photo('connecting-family'), photoAlt: 'View through open connecting doors into a second bright bedroom',
  },
  {
    slug: 'signature-suite', name: 'Signature Suite', beds: '1 king bed', bedKind: 'King', capacity: 2, fromRate: 210,
    summary: 'A separate lounge with armchairs and sofa, divided from the bedroom by a walnut screen.',
    highlights: ['Separate lounge', 'King bed', 'Walnut divider'],
    photo: photo('signature-suite'), photoAlt: 'Suite lounge with leather armchairs, a round black coffee table and a double-height ceiling',
  },
  {
    slug: 'riverfront-suite', name: 'Riverfront Suite', beds: '1 king bed', bedKind: 'King', capacity: 2, fromRate: 240,
    summary: 'Our largest room: floor-to-ceiling windows over the river, a curved sofa and a walk-through dressing room.',
    highlights: ['River-facing windows', 'Curved lounge', 'Dressing room'],
    photo: photo('riverfront-suite'), photoAlt: 'Large suite with king bed, curved leather sofa and floor-to-ceiling windows over a river',
  },
]

export const FALLBACK_ROOM_PHOTO = '/images/luma-haven/rooms/deluxe/main.jpg'

export function slugifyRoomName(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

export function roomCatalogFor(name: string): RoomCatalogEntry | undefined {
  const slug = slugifyRoomName(name)
  return ROOM_CATALOG.find((r) => r.slug === slug || slugifyRoomName(r.name) === slug)
}

export function roomPhotoFor(name: string): { src: string; alt: string } {
  const entry = roomCatalogFor(name)
  return entry ? { src: entry.photo, alt: entry.photoAlt } : { src: FALLBACK_ROOM_PHOTO, alt: `${name} room` }
}
