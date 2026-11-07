<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../../utils/responsiveImage'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import type { PublicVisualAssetsResponse, VisualAsset } from '../../../types'

const router = useRouter()

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})

interface SpaceItem {
  id: number
  asset: VisualAsset
  spaceName: string
  areaCategory: string
  floorLocation: string
  description: string
  isConcept: boolean
  facilityClaim: string
  roomTypeName?: string
}

function resolveSpaceMetadata(asset: VisualAsset): { spaceName: string; areaCategory: string; floorLocation: string; description: string } {
  const filename = asset.original_filename || ''

  if (filename === 'branding/logo.png') {
    return {
      spaceName: 'Official Brand Identity Logo',
      areaCategory: 'branding',
      floorLocation: 'Brand Identity',
      description: 'The official Luma Haven emblem mark, featuring crisp typography and transparent backdrop.',
    }
  }
  if (filename.includes('logo_concept')) {
    return {
      spaceName: 'Architectural Concept Seal',
      areaCategory: 'branding',
      floorLocation: 'Heritage Monogram',
      description: 'Gold-leaf arch and botanical seal concept representing unhurried hospitality.',
    }
  }
  if (filename.includes('hotel_exterior')) {
    return {
      spaceName: 'Hotel Exterior & Facade',
      areaCategory: 'grounds',
      floorLocation: 'Grounds & Street Entrance',
      description: 'Evening concept visualization of the modern glass facade with warm welcoming ambient illumination.',
    }
  }
  if (filename.includes('gallery/lobby')) {
    return {
      spaceName: 'Hotel Lobby & Reception',
      areaCategory: 'grounds',
      floorLocation: 'Ground Floor Atrium',
      description: 'Quiet arrival lounge with teak reception desk, warm lighting, and physical brass key collection.',
    }
  }
  if (filename.includes('gallery/guest_lounge')) {
    return {
      spaceName: 'Guest Lounge & Library',
      areaCategory: 'grounds',
      floorLocation: 'Mezzanine Floor',
      description: 'Restful salon with deep armchairs and afternoon natural light for reading and conversation.',
    }
  }
  if (filename.includes('features/lounge')) {
    return {
      spaceName: 'Mezzanine Library & Reading Lounge',
      areaCategory: 'grounds',
      floorLocation: 'Mezzanine Reading Sanctuary',
      description: 'A quiet sanctuary with literature and deep armchairs for mindful downtime.',
    }
  }
  if (filename.includes('gallery/city_view')) {
    return {
      spaceName: 'City Skyline Terrace View',
      areaCategory: 'grounds',
      floorLocation: 'East Wing Vista',
      description: 'Panoramic dusk outlook over Phnom Penh neighborhood rooftops and tranquil skyline.',
    }
  }
  if (filename.includes('gallery/restaurant')) {
    return {
      spaceName: 'Courtyard Restaurant',
      areaCategory: 'dining',
      floorLocation: 'Ground Floor Courtyard',
      description: 'Intimate dining bistro serving seasonal Cambodian fusion cuisine and local roast coffee.',
    }
  }
  if (filename.includes('features/dining')) {
    return {
      spaceName: 'Dining & Culinary Experience',
      areaCategory: 'dining',
      floorLocation: 'Hotel Bistro',
      description: 'A table set for unhurried breakfasts and quiet evening tasting menus.',
    }
  }
  if (filename.includes('gallery/rooftop_pool')) {
    return {
      spaceName: 'Rooftop Pool & Sun Deck',
      areaCategory: 'wellness',
      floorLocation: 'Level 4 Rooftop',
      description: 'Calm open-air lap pool and lounging deck overlooking the capital city lights.',
    }
  }
  if (filename.includes('features/pool')) {
    return {
      spaceName: 'Shaded Pool & Daybeds',
      areaCategory: 'wellness',
      floorLocation: 'Rooftop Pool Terrace',
      description: 'Canopied loungers and cool waters designed for mid-day respite and mindful swimming.',
    }
  }
  if (filename.includes('gallery/fitness_center')) {
    return {
      spaceName: 'Fitness Center & Gym',
      areaCategory: 'wellness',
      floorLocation: 'Wellness Floor',
      description: 'Sunlit conditioning studio with premium cardio equipment and free weights.',
    }
  }
  if (filename.includes('features/gym')) {
    return {
      spaceName: 'Movement & Wellness Studio',
      areaCategory: 'wellness',
      floorLocation: 'Wellness Center',
      description: 'Dedicated space for morning stretching, yoga, and mindful strength training.',
    }
  }
  if (filename.includes('features/details')) {
    return {
      spaceName: 'Thoughtful Guest Touches',
      areaCategory: 'details',
      floorLocation: 'Guest Rooms',
      description: 'Organic botanical toiletries, waffle robes, and hand-milled soaps on solid timber trays.',
    }
  }
  // Suite
  if (filename.includes('rooms/suite/main')) {
    return {
      spaceName: 'Family Suite — Main Space',
      areaCategory: 'suite',
      floorLocation: 'Level 3 Suite Wing',
      description: 'Spacious multi-room sanctuary featuring master sleeping quarters and an arched living lounge.',
    }
  }
  if (filename.includes('rooms/suite/bedroom')) {
    return {
      spaceName: 'Family Suite — Master Bedroom',
      areaCategory: 'suite',
      floorLocation: 'Level 3 Suite Wing',
      description: 'King-sized luxury bed with organic percale linens and acoustic soundproofing.',
    }
  }
  if (filename.includes('rooms/suite/living')) {
    return {
      spaceName: 'Family Suite — Arched Living Room',
      areaCategory: 'suite',
      floorLocation: 'Level 3 Suite Wing',
      description: 'Curved architectural alcove with comfortable daybeds, dining table, and reading corner.',
    }
  }
  if (filename.includes('rooms/suite/bathroom')) {
    return {
      spaceName: 'Family Suite — Ensuite Bathroom',
      areaCategory: 'suite',
      floorLocation: 'Level 3 Suite Wing',
      description: 'Double vanity, deep soaking tub, and brass rain shower fixture.',
    }
  }
  if (filename.includes('rooms/suite/view')) {
    return {
      spaceName: 'Family Suite — Balcony City View',
      areaCategory: 'suite',
      floorLocation: 'Level 3 Suite Wing',
      description: 'Private shaded terrace overlooking Phnom Penh skyline and interior garden courtyards.',
    }
  }
  // Deluxe
  if (filename.includes('rooms/deluxe/main')) {
    return {
      spaceName: 'Deluxe Room — Main Bedroom',
      areaCategory: 'deluxe',
      floorLocation: 'Level 2 Guest Wing',
      description: 'Contemporary boutique sanctuary with plush king bed, hardwood flooring, and warm accent lighting.',
    }
  }
  if (filename.includes('rooms/deluxe/bedroom')) {
    return {
      spaceName: 'Deluxe Room — King Bed',
      areaCategory: 'deluxe',
      floorLocation: 'Level 2 Guest Wing',
      description: 'Plush pillows, tailored fabric headboard, and bedside reading sconces.',
    }
  }
  if (filename.includes('rooms/deluxe/bathroom')) {
    return {
      spaceName: 'Deluxe Room — Marble Bathroom',
      areaCategory: 'deluxe',
      floorLocation: 'Level 2 Guest Wing',
      description: 'Subtle veined stone finishes, frameless glass shower, and illuminated mirror.',
    }
  }
  if (filename.includes('rooms/deluxe/work_desk')) {
    return {
      spaceName: 'Deluxe Room — Dedicated Work Desk',
      areaCategory: 'deluxe',
      floorLocation: 'Level 2 Guest Wing',
      description: 'Solid timber workstation with ergonomic chair, power outlets, and fiber Wi-Fi.',
    }
  }
  if (filename.includes('rooms/deluxe/amenities')) {
    return {
      spaceName: 'Deluxe Room — Wardrobe & Amenities',
      areaCategory: 'deluxe',
      floorLocation: 'Level 2 Guest Wing',
      description: 'Open wardrobe storage, brass luggage rack, and in-room safety deposit box.',
    }
  }
  // Premier
  if (filename.includes('rooms/premier/main')) {
    return {
      spaceName: 'Premier Room — Main Bedroom',
      areaCategory: 'premier',
      floorLocation: 'Level 3 Guest Wing',
      description: 'Elevated boutique retreat with panoramic windows and rich textural timber finishes.',
    }
  }
  if (filename.includes('rooms/premier/bedroom')) {
    return {
      spaceName: 'Premier Room — King Bedding',
      areaCategory: 'premier',
      floorLocation: 'Level 3 Guest Wing',
      description: 'Custom upholstered bedframe, blackout linen drapes, and ambient bedside controls.',
    }
  }
  if (filename.includes('rooms/premier/bathroom')) {
    return {
      spaceName: 'Premier Room — Luxury Bathroom',
      areaCategory: 'premier',
      floorLocation: 'Level 3 Guest Wing',
      description: 'Freestanding bath, rainfall shower, and custom stone basin with brass tapware.',
    }
  }
  if (filename.includes('rooms/premier/seating')) {
    return {
      spaceName: 'Premier Room — Window Seating Lounge',
      areaCategory: 'premier',
      floorLocation: 'Level 3 Guest Wing',
      description: 'Cozy cushioned banquette beneath picture windows for afternoon reading and morning coffee.',
    }
  }
  if (filename.includes('rooms/premier/minibar')) {
    return {
      spaceName: 'Premier Room — Curated In-Room Minibar',
      areaCategory: 'premier',
      floorLocation: 'Level 3 Guest Wing',
      description: 'Handcrafted drinks cabinet with artisanal teas, French press, and chilled refreshments.',
    }
  }

  // Fallback
  return {
    spaceName: asset.title || filename,
    areaCategory: 'other',
    floorLocation: 'Hotel Space',
    description: asset.caption || asset.alt_text,
  }
}

const allSpaces = computed<SpaceItem[]>(() => {
  const items = visualAssets.data.value?.items || []
  return items.map(asset => {
    const meta = resolveSpaceMetadata(asset)
    return {
      id: asset.id,
      asset,
      spaceName: meta.spaceName,
      areaCategory: meta.areaCategory,
      floorLocation: meta.floorLocation,
      description: meta.description,
      isConcept: asset.source_type === 'CONCEPT',
      facilityClaim: asset.facility_claim,
      roomTypeName: asset.room_type_name || (
        meta.areaCategory === 'suite' ? 'Family Suite' :
        meta.areaCategory === 'deluxe' ? 'Deluxe Room' :
        meta.areaCategory === 'premier' ? 'Premier Room' : undefined
      ),
    }
  })
})

const categories = [
  { id: 'all', label: 'All Spaces' },
  { id: 'grounds', label: 'Grounds & Lobby' },
  { id: 'wellness', label: 'Pool & Wellness' },
  { id: 'dining', label: 'Dining & Bistro' },
  { id: 'suite', label: 'Family Suite' },
  { id: 'deluxe', label: 'Deluxe Room' },
  { id: 'premier', label: 'Premier Room' },
  { id: 'details', label: 'In-Room Details' },
  { id: 'branding', label: 'Brand Identity' },
]

const activeCategory = ref('all')

const filteredSpaces = computed(() => {
  if (activeCategory.value === 'all') return allSpaces.value
  if (activeCategory.value === 'details') {
    return allSpaces.value.filter(s =>
      s.areaCategory === 'details' ||
      s.asset.original_filename?.includes('amenities') ||
      s.asset.original_filename?.includes('minibar') ||
      s.asset.original_filename?.includes('work_desk')
    )
  }
  return allSpaces.value.filter(s => s.areaCategory === activeCategory.value)
})

// Lightbox state
const lightboxIndex = ref<number | null>(null)
const activeLightboxItem = computed(() => {
  if (lightboxIndex.value === null) return null
  return filteredSpaces.value[lightboxIndex.value] || null
})

function openLightbox(index: number) {
  lightboxIndex.value = index
}

function closeLightbox() {
  lightboxIndex.value = null
}

function nextLightbox() {
  if (lightboxIndex.value === null) return
  const len = filteredSpaces.value.length
  lightboxIndex.value = (lightboxIndex.value + 1) % len
}

function prevLightbox() {
  if (lightboxIndex.value === null) return
  const len = filteredSpaces.value.length
  lightboxIndex.value = (lightboxIndex.value - 1 + len) % len
}

function handleKeydown(e: KeyboardEvent) {
  if (lightboxIndex.value === null) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowRight') nextLightbox()
  if (e.key === 'ArrowLeft') prevLightbox()
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

function handleBookRoom(roomType?: string) {
  closeLightbox()
  if (roomType) {
    router.push({ path: '/rooms', query: { type: roomType } })
  } else {
    router.push('/rooms')
  }
}
</script>

<template>
  <div class="spaces-explorer py-6">
    <div class="sx-filters" role="group" aria-label="Filter spaces">
      <button v-for="cat in categories" :key="cat.id" type="button" class="sx-filter" :aria-pressed="activeCategory === cat.id" @click="activeCategory = cat.id">{{ cat.label }}</button>
    </div>

    <p v-if="filteredSpaces.length === 0" class="sx-empty">No spaces in this group yet. Pick another from the list above.</p>

    <div class="sx-masonry">
      <figure v-for="(space, index) in filteredSpaces" :key="space.id" class="sx-item">
        <button type="button" class="sx-photo" :aria-label="`View ${space.spaceName} larger`" @click="openLightbox(index)">
          <img
            :src="space.asset.image_url"
            :srcset="responsiveSrcset(space.asset.image_url, space.asset.width)"
            :sizes="SIZES.card"
            :alt="space.asset.alt_text"
            :width="space.asset.width"
            :height="space.asset.height"
            loading="lazy"
          />
        </button>
        <figcaption>
          <strong>{{ space.spaceName }}</strong>
          <span>{{ space.floorLocation }}<template v-if="space.isConcept">. {{ space.facilityClaim ? `Concept: ${space.facilityClaim}` : 'Design concept' }}</template></span>
          <span>{{ space.description }}</span>
        </figcaption>
      </figure>
    </div>

    <Transition name="lb-fade">
      <div v-if="activeLightboxItem" class="lb-scrim" role="dialog" aria-modal="true" :aria-label="activeLightboxItem.spaceName" @click.self="closeLightbox">
        <div class="lb-panel">
          <div class="lb-head">
            <div>
              <h2 class="lb-title">{{ activeLightboxItem.spaceName }}</h2>
              <p class="lb-sub">{{ activeLightboxItem.floorLocation }}, {{ (lightboxIndex ?? 0) + 1 }} of {{ filteredSpaces.length }}</p>
            </div>
            <div class="lb-actions">
              <button v-if="activeLightboxItem.roomTypeName" type="button" class="btn" @click="handleBookRoom(activeLightboxItem.roomTypeName)">Book {{ activeLightboxItem.roomTypeName }}</button>
              <button type="button" class="lb-close" aria-label="Close photo" @click="closeLightbox"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
            </div>
          </div>
          <div class="lb-stage">
            <img :src="activeLightboxItem.asset.image_url" :srcset="responsiveSrcset(activeLightboxItem.asset.image_url, activeLightboxItem.asset.width)" :sizes="SIZES.lightbox" :alt="activeLightboxItem.asset.alt_text" />
            <div v-if="activeLightboxItem.isConcept" class="lb-chips"><span class="lb-chip">{{ activeLightboxItem.facilityClaim ? `Concept: ${activeLightboxItem.facilityClaim}` : 'Design concept' }}</span></div>
            <button v-if="filteredSpaces.length > 1" type="button" class="lb-nav lb-nav--prev" aria-label="Previous space photo" @click="prevLightbox"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" /></svg></button>
            <button v-if="filteredSpaces.length > 1" type="button" class="lb-nav lb-nav--next" aria-label="Next space photo" @click="nextLightbox"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" /></svg></button>
          </div>
          <p class="lb-caption">{{ activeLightboxItem.description }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.sx-filters { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: 1.5rem; }
.sx-filter { min-height: 44px; padding: 0 1rem; border-radius: var(--radius-pill); border: 1.5px solid var(--rule); color: var(--river); font: 500 .875rem var(--font-text); }
.sx-filter[aria-pressed="true"] { background: var(--river); border-color: var(--river); color: var(--palm-leaf); }
.sx-empty { padding: 2rem 0; color: var(--silt); }
.sx-masonry { columns: 1; column-gap: 1.25rem; }
.sx-item { break-inside: avoid; margin-bottom: 1.5rem; }
.sx-photo { display: block; width: 100%; border-radius: var(--radius-photo); overflow: hidden; background: var(--surface-muted); }
.sx-photo img { width: 100%; height: auto; display: block; }
.sx-item figcaption { display: grid; gap: .1rem; margin-top: .5rem; font-size: .875rem; color: var(--silt); }
.sx-item figcaption strong { color: var(--river); font-weight: 600; }
@media (min-width: 640px) { .sx-masonry { columns: 2; } }
@media (min-width: 1024px) { .sx-masonry { columns: 3; } }
</style>
