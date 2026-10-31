export interface HotelImageRecord {
  id: string
  category: 'branding' | 'hero' | 'gallery' | 'rooms' | 'facilities' | 'views' | 'dining'
  roomType?: 'deluxe' | 'premier' | 'suite'
  section?: string
  src: string
  alt: string
  caption: string
  locationTag: string
  width: number
  height: number
  isPlaceholder: boolean
  isDemo: boolean
  facilityClaim?: string
}

export const HOTEL_IMAGES: HotelImageRecord[] = [
  // --- BRANDING ---
  {
    id: 'brand-logo',
    category: 'branding',
    src: '/images/luma-haven/branding/logo.png',
    alt: 'Luma Haven Hotel official brand emblem logo',
    caption: 'Official Luma Haven brand emblem and typography.',
    locationTag: 'Brand Identity',
    width: 1263,
    height: 1245,
    isPlaceholder: false,
    isDemo: false,
    facilityClaim: 'Official Logo',
  },
  {
    id: 'brand-logo-concept',
    category: 'branding',
    src: '/images/luma-haven/branding/logo_concept.jpg',
    alt: 'Luma Haven Hotel arched gold emblem with stylized leaf on cream background',
    caption: 'A brighter stay, a calmer you. Architectural concept seal.',
    locationTag: 'Heritage Seal',
    width: 1184,
    height: 1600,
    isPlaceholder: false,
    isDemo: true,
  },

  // --- HERO ---
  {
    id: 'hero-exterior',
    category: 'hero',
    src: '/images/luma-haven/hero/hotel_exterior_concept.jpg',
    alt: 'Evening concept visualization of modern glass facade of Luma Haven boutique hotel with warm lighting',
    caption: 'Discover the welcoming elegance of Luma-Haven.',
    locationTag: 'Hotel Exterior Facade',
    width: 2560,
    height: 1753,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Architectural exterior',
  },

  // --- GALLERY ---
  {
    id: 'gallery-lobby',
    category: 'gallery',
    section: 'lobby',
    src: '/images/luma-haven/gallery/lobby.jpg',
    alt: 'Concept visualization of hotel lobby lounge with comfortable seating and ambient lighting',
    caption: 'A warm welcome awaits every guest.',
    locationTag: 'Ground Floor · Lobby & Reception',
    width: 1600,
    height: 1214,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Reception Lounge',
  },
  {
    id: 'gallery-guest-lounge',
    category: 'gallery',
    section: 'lounge',
    src: '/images/luma-haven/gallery/guest_lounge.jpg',
    alt: 'Concept visualization of quiet hotel library lounge with bookshelves and deep armchairs',
    caption: 'A peaceful space to unwind.',
    locationTag: 'Mezzanine · Guest Lounge & Library',
    width: 1600,
    height: 1247,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Guest Lounge',
  },
  {
    id: 'gallery-city-view',
    category: 'views',
    section: 'views',
    src: '/images/luma-haven/gallery/city_view.jpg',
    alt: 'Concept view of sunset over city skyline from boutique hotel terrace',
    caption: 'Experience beautiful skyline views.',
    locationTag: 'East Wing · City View Terrace',
    width: 1600,
    height: 1158,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Terrace View',
  },
  {
    id: 'gallery-restaurant',
    category: 'dining',
    section: 'restaurant',
    src: '/images/luma-haven/gallery/restaurant.jpg',
    alt: 'Concept visualization of elegant hotel dining room with warm ambient pendant lights',
    caption: 'Enjoy memorable dining moments.',
    locationTag: 'Ground Floor · Courtyard Restaurant',
    width: 1600,
    height: 1128,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Facility Unconfirmed (Restaurant)',
  },
  {
    id: 'gallery-rooftop-pool',
    category: 'facilities',
    section: 'pool',
    src: '/images/luma-haven/gallery/rooftop_pool.jpg',
    alt: 'Concept visualization of boutique hotel rooftop swimming pool illuminated at dusk',
    caption: 'Relax above the city.',
    locationTag: 'Level 4 · Rooftop Pool & Deck',
    width: 1600,
    height: 1128,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Facility Unconfirmed (Rooftop Pool)',
  },
  {
    id: 'gallery-fitness-center',
    category: 'facilities',
    section: 'gym',
    src: '/images/luma-haven/gallery/fitness_center.jpg',
    alt: 'Concept visualization of modern hotel fitness center with cardio equipment and natural light',
    caption: 'Stay active throughout your stay.',
    locationTag: 'Wellness Wing · Fitness Center',
    width: 1600,
    height: 1158,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Facility Unconfirmed (Fitness Center)',
  },

  // --- FACILITIES & EXPERIENCES ---
  {
    id: 'facility-pool',
    category: 'facilities',
    section: 'pool',
    src: '/images/luma-haven/facilities/pool.jpg',
    alt: 'Rooftop pool deck concept with loungers, sun umbrella, and tranquil water reflection',
    caption: 'Canopied loungers and tranquil waters designed for unhurried midday pause.',
    locationTag: 'Rooftop Pool Terrace',
    width: 1600,
    height: 1055,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Facility Unconfirmed (Pool)',
  },
  {
    id: 'facility-dining',
    category: 'dining',
    section: 'dining',
    src: '/images/luma-haven/facilities/dining.jpg',
    alt: 'Atmospheric hotel dining concept showing table set with fresh breakfast and coffee',
    caption: 'Seasonal Cambodian fare and local roast coffee in an intimate courtyard setting.',
    locationTag: 'Hotel Bistro & Dining',
    width: 1600,
    height: 973,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Facility Unconfirmed (Dining)',
  },
  {
    id: 'facility-gym',
    category: 'facilities',
    section: 'gym',
    src: '/images/luma-haven/facilities/gym.jpg',
    alt: 'Boutique hotel gym concept with timber accents and wellness equipment',
    caption: 'Dedicated equipment for morning stretching, light cardio, and restorative exercise.',
    locationTag: 'Wellness Center',
    width: 1600,
    height: 1012,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Facility Unconfirmed (Gym)',
  },
  {
    id: 'facility-details',
    category: 'facilities',
    section: 'details',
    src: '/images/luma-haven/facilities/details.jpg',
    alt: 'Organic guest bath amenities, fresh rolled towel, and wooden tray',
    caption: 'Organic botanical toiletries, waffle robes, and hand-milled soaps on solid timber trays.',
    locationTag: 'Guest Room Amenities',
    width: 1600,
    height: 1160,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Premium Bath Amenities',
  },
  {
    id: 'facility-lounge',
    category: 'facilities',
    section: 'lounge',
    src: '/images/luma-haven/facilities/lounge.jpg',
    alt: 'Concept visualization of quiet hotel library lounge with bookshelves and deep armchairs',
    caption: 'A peaceful sanctuary for reading, reflection, and quiet conversation.',
    locationTag: 'Mezzanine · Guest Lounge',
    width: 1600,
    height: 853,
    isPlaceholder: false,
    isDemo: true,
    facilityClaim: 'Guest Lounge',
  },

  // --- ROOMS: SUITE ---
  {
    id: 'suite-main',
    category: 'rooms',
    roomType: 'suite',
    section: 'main',
    src: '/images/luma-haven/rooms/suite/main.jpg',
    alt: 'Spacious master suite concept showing king bed and arched passage to adjoining living lounge',
    caption: 'Generous multi-room sanctuary featuring a king bed and arched living lounge.',
    locationTag: 'Family Suite — Main Bedroom & Lounge',
    width: 2560,
    height: 1295,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'suite-bedroom',
    category: 'rooms',
    roomType: 'suite',
    section: 'bedroom',
    src: '/images/luma-haven/rooms/suite/bedroom.jpg',
    alt: 'Master bedroom alcove in family suite with organic cotton linens and brass wall sconce',
    caption: 'King-sized luxury bed with organic percale linens and acoustic soundproofing.',
    locationTag: 'Family Suite — Master Bedroom',
    width: 1600,
    height: 1413,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'suite-living',
    category: 'rooms',
    roomType: 'suite',
    section: 'living',
    src: '/images/luma-haven/rooms/suite/living.jpg',
    alt: 'Living lounge in family suite with daybed sofa, dining table, and botanical prints',
    caption: 'Curved architectural alcove with comfortable daybeds, dining table, and reading corner.',
    locationTag: 'Family Suite — Arched Living Room',
    width: 1600,
    height: 1514,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'suite-bathroom',
    category: 'rooms',
    roomType: 'suite',
    section: 'bathroom',
    src: '/images/luma-haven/rooms/suite/bathroom.jpg',
    alt: 'Ensuite luxury bathroom in family suite with soaking tub, stone vanity, and brass fixtures',
    caption: 'Double vanity, deep soaking tub, and brass rain shower fixture.',
    locationTag: 'Family Suite — Ensuite Bathroom',
    width: 1600,
    height: 1437,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'suite-view',
    category: 'rooms',
    roomType: 'suite',
    section: 'view',
    src: '/images/luma-haven/rooms/suite/view.jpg',
    alt: 'Panoramic terrace view from family suite looking over hotel gardens and neighborhood rooftops',
    caption: 'Private shaded terrace overlooking Phnom Penh skyline and interior garden courtyards.',
    locationTag: 'Family Suite — Balcony City View',
    width: 1600,
    height: 1437,
    isPlaceholder: false,
    isDemo: true,
  },

  // --- ROOMS: DELUXE ---
  {
    id: 'deluxe-main',
    category: 'rooms',
    roomType: 'deluxe',
    section: 'main',
    src: '/images/luma-haven/rooms/deluxe/main.jpg',
    alt: 'Deluxe concept room with king bed, timber flooring, and large window with sheer drapes',
    caption: 'Contemporary boutique sanctuary with plush king bed and warm accent lighting.',
    locationTag: 'Deluxe Room — Main Bedroom',
    width: 2560,
    height: 1243,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'deluxe-bedroom',
    category: 'rooms',
    roomType: 'deluxe',
    section: 'bedroom',
    src: '/images/luma-haven/rooms/deluxe/bedroom.jpg',
    alt: 'Detail of deluxe room bed with upholstered headboard and soft neutral cushions',
    caption: 'Plush pillows, tailored fabric headboard, and bedside reading sconces.',
    locationTag: 'Deluxe Room — King Bed',
    width: 1600,
    height: 1357,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'deluxe-bathroom',
    category: 'rooms',
    roomType: 'deluxe',
    section: 'bathroom',
    src: '/images/luma-haven/rooms/deluxe/bathroom.jpg',
    alt: 'Deluxe room bathroom with walk-in rain shower, textured tiles, and illuminated mirror',
    caption: 'Subtle veined stone finishes, frameless glass shower, and illuminated mirror.',
    locationTag: 'Deluxe Room — Marble Bathroom',
    width: 1585,
    height: 1600,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'deluxe-work-desk',
    category: 'rooms',
    roomType: 'deluxe',
    section: 'work_desk',
    src: '/images/luma-haven/rooms/deluxe/work_desk.jpg',
    alt: 'Dedicated oak writing desk in deluxe room with lamp and notepad',
    caption: 'Solid timber workstation with ergonomic chair, power outlets, and fiber Wi-Fi.',
    locationTag: 'Deluxe Room — Dedicated Work Desk',
    width: 1600,
    height: 1379,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'deluxe-amenities',
    category: 'rooms',
    roomType: 'deluxe',
    section: 'amenities',
    src: '/images/luma-haven/rooms/deluxe/amenities.jpg',
    alt: 'Open wardrobe detail in deluxe room with brass hangers, safe, and luggage rack',
    caption: 'Open wardrobe storage, brass luggage rack, and in-room safety deposit box.',
    locationTag: 'Deluxe Room — Wardrobe & Amenities',
    width: 1600,
    height: 1285,
    isPlaceholder: false,
    isDemo: true,
  },

  // --- ROOMS: PREMIER ---
  {
    id: 'premier-main',
    category: 'rooms',
    roomType: 'premier',
    section: 'main',
    src: '/images/luma-haven/rooms/premier/main.jpg',
    alt: 'Premier concept room with king bed, hardwood finishes, and integrated reading lights',
    caption: 'Elevated boutique retreat with panoramic windows and rich textural timber finishes.',
    locationTag: 'Premier Room — Main Bedroom',
    width: 2560,
    height: 1298,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'premier-bedroom',
    category: 'rooms',
    roomType: 'premier',
    section: 'bedroom',
    src: '/images/luma-haven/rooms/premier/bedroom.jpg',
    alt: 'Premier room bed dressing detail with layered linen throws and headboard lighting',
    caption: 'Custom upholstered bedframe, blackout linen drapes, and ambient bedside controls.',
    locationTag: 'Premier Room — King Bedding',
    width: 1600,
    height: 1346,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'premier-bathroom',
    category: 'rooms',
    roomType: 'premier',
    section: 'bathroom',
    src: '/images/luma-haven/rooms/premier/bathroom.jpg',
    alt: 'Premier room ensuite bathroom with dual sink vanity and rainfall shower head',
    caption: 'Freestanding bath, rainfall shower, and custom stone basin with brass tapware.',
    locationTag: 'Premier Room — Luxury Bathroom',
    width: 1600,
    height: 1585,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'premier-seating',
    category: 'rooms',
    roomType: 'premier',
    section: 'seating',
    src: '/images/luma-haven/rooms/premier/seating.jpg',
    alt: 'Window seating banquette in premier room with view toward hotel courtyard gardens',
    caption: 'Cozy cushioned banquette beneath picture windows for afternoon reading and morning coffee.',
    locationTag: 'Premier Room — Window Seating Lounge',
    width: 1600,
    height: 1357,
    isPlaceholder: false,
    isDemo: true,
  },
  {
    id: 'premier-minibar',
    category: 'rooms',
    roomType: 'premier',
    section: 'minibar',
    src: '/images/luma-haven/rooms/premier/minibar.jpg',
    alt: 'Bespoke minibar cabinet in premier room with kettle, glasses, and curated tea selection',
    caption: 'Handcrafted drinks cabinet with artisanal teas, French press, and chilled refreshments.',
    locationTag: 'Premier Room — Curated In-Room Minibar',
    width: 1600,
    height: 1600,
    isPlaceholder: false,
    isDemo: true,
  },
]

// Placeholders mapping
export const PLACEHOLDERS = {
  room: '/images/luma-haven/placeholders/room-placeholder.svg',
  hotel: '/images/luma-haven/placeholders/hotel-placeholder.svg',
  facility: '/images/luma-haven/placeholders/facility-placeholder.svg',
}

// Helpers
export function getHeroImage(): HotelImageRecord {
  return HOTEL_IMAGES.find(img => img.id === 'hero-exterior') || HOTEL_IMAGES[0]
}

export function getLogoImage(): HotelImageRecord {
  return HOTEL_IMAGES.find(img => img.id === 'brand-logo') || HOTEL_IMAGES[0]
}

export function getLogoConceptImage(): HotelImageRecord {
  return HOTEL_IMAGES.find(img => img.id === 'brand-logo-concept') || HOTEL_IMAGES[0]
}

export function getGalleryCarouselImages(): HotelImageRecord[] {
  const order = [
    'gallery-lobby',
    'gallery-rooftop-pool',
    'gallery-restaurant',
    'gallery-fitness-center',
    'gallery-guest-lounge',
    'gallery-city-view',
  ]
  return order.map(id => HOTEL_IMAGES.find(img => img.id === id)).filter(Boolean) as HotelImageRecord[]
}

export function getFacilitiesImages(): HotelImageRecord[] {
  return [
    'facility-pool',
    'facility-dining',
    'facility-gym',
    'facility-lounge',
    'facility-details',
  ].map(id => HOTEL_IMAGES.find(img => img.id === id)).filter(Boolean) as HotelImageRecord[]
}

export function getRoomTourImages(roomType: 'deluxe' | 'premier' | 'suite'): HotelImageRecord[] {
  return HOTEL_IMAGES.filter(img => img.category === 'rooms' && img.roomType === roomType)
}

export function getImagesByCategory(cat: string): HotelImageRecord[] {
  if (cat === 'all') return HOTEL_IMAGES
  if (cat === 'hotel') return HOTEL_IMAGES.filter(img => ['hero', 'gallery', 'views'].includes(img.category))
  if (cat === 'rooms') return HOTEL_IMAGES.filter(img => img.category === 'rooms')
  if (cat === 'dining') return HOTEL_IMAGES.filter(img => img.category === 'dining')
  if (cat === 'facilities') return HOTEL_IMAGES.filter(img => img.category === 'facilities')
  if (cat === 'views') return HOTEL_IMAGES.filter(img => img.category === 'views')
  return HOTEL_IMAGES.filter(img => img.category === cat)
}
