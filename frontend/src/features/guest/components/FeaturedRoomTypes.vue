<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import type { PublicVisualAssetsResponse } from '../../../types'
import RoomSpacesModal from './RoomSpacesModal.vue'

const router = useRouter()

interface RoomCategory {
  id: string
  name: string
  tagline: string
  capacity: number
  startingRate: number
  image: string
  imageAlt: string
  description: string
  amenities: string[]
}

const roomCategories: RoomCategory[] = [
  {
    id: 'garden-king',
    name: 'Garden King',
    tagline: 'Courtyard retreat with lush garden views',
    capacity: 2,
    startingRate: 85,
    image: '/images/rooms/garden-king.svg',
    imageAlt: 'Garden King room featuring king-sized bed, warm wood headboard, and private garden terrace doors',
    description: 'A serene sanctuary featuring floor-to-ceiling French doors opening toward our tranquil interior courtyard greenery.',
    amenities: ['1 King Bed', 'Courtyard View', 'Physical Brass Key', 'Rain Shower', 'Organic Tea Bar', 'Quiet AC'],
  },
  {
    id: 'city-twin',
    name: 'City Twin',
    tagline: 'Morning light & acoustic soundproofing',
    capacity: 2,
    startingRate: 72,
    image: '/images/rooms/city-twin.svg',
    imageAlt: 'City Twin room with two comfortable twin beds, morning city window light, and handcrafted oak work desk',
    description: 'Crisp morning sunlight, premium acoustic privacy, and a dedicated oak desk for mindful remote work or quiet rest.',
    amenities: ['2 Twin Beds', 'Sunrise Orientation', 'Solid Oak Desk', 'Soundproofing', 'High-Speed Wi-Fi', 'Brass Key'],
  },
  {
    id: 'family-suite',
    name: 'Family Suite',
    tagline: 'Spacious arched living alcove for four',
    capacity: 4,
    startingRate: 155,
    image: '/images/rooms/family-suite.svg',
    imageAlt: 'Family Suite featuring master bedroom archway, adjoining living lounge with daybeds, and botanical prints',
    description: 'Generous multi-room sanctuary with an arched living lounge, dining alcove, and ample space for up to four guests.',
    amenities: ['Master King + 2 Daybeds', 'Lounge Alcove', 'Double Vanity Bath', 'Courtyard Facing', 'Dining Table', 'Brass Key'],
  },
]

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})

const displayCategories = computed(() => {
  const rtMap = visualAssets.data.value?.room_types || {}
  const allRtAssets = Object.values(rtMap).flat()

  return roomCategories.map(cat => {
    const match = allRtAssets.find(a =>
      a.room_type_name?.toLowerCase() === cat.name.toLowerCase()
    )
    if (match) {
      return {
        ...cat,
        image: match.image_url,
        imageAlt: match.alt_text || cat.imageAlt,
        isConcept: match.source_type === 'CONCEPT',
      }
    }
    return {
      ...cat,
      isConcept: false,
    }
  })
})

function checkRoomAvailability(category: RoomCategory) {
  router.push({
    path: '/rooms',
    query: {
      type: category.name,
      occupants: String(category.capacity),
    },
  })
}

// Room Spaces Modal
const modalRoomName = ref<string | null>(null)

const modalAssets = computed(() => {
  if (!modalRoomName.value) return []
  const items = visualAssets.data.value?.items || []
  const n = modalRoomName.value.toLowerCase()
  if (n.includes('suite')) return items.filter(a => a.original_filename?.startsWith('rooms/suite/'))
  if (n.includes('deluxe')) return items.filter(a => a.original_filename?.startsWith('rooms/deluxe/'))
  if (n.includes('premier')) return items.filter(a => a.original_filename?.startsWith('rooms/premier/'))
  return []
})

function openSpacesModal(name: string) {
  modalRoomName.value = name
}

function closeSpacesModal() {
  modalRoomName.value = null
}

function handleBookFromModal(name: string) {
  closeSpacesModal()
  router.push({ path: '/rooms', query: { type: name } })
}
</script>

<template>
  <section id="rooms" class="py-16 sm:py-24 border-t border-[var(--line)]" aria-labelledby="rooms-heading">
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-12 sm:mb-16">
      <div class="max-w-2xl space-y-2">
        <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">
          Featured Accommodations
        </span>
        <h2 id="rooms-heading" class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
          Rooms to settle into<span class="text-[var(--brass)]">.</span>
        </h2>
        <p class="text-sm sm:text-base text-[var(--muted)] pt-1">
          Each room category is intentionally designed with acoustic isolation, tactile natural materials, and authentic physical brass keys.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <RouterLink
          to="/spaces"
          class="btn-secondary text-sm font-semibold px-4 py-2.5 inline-flex items-center gap-2"
        >
          Explore all spaces
        </RouterLink>
        <RouterLink
          to="/rooms"
          class="btn text-sm font-semibold px-5 py-2.5 inline-flex items-center gap-2"
        >
          View availability
          <span aria-hidden="true">→</span>
        </RouterLink>
      </div>
    </div>

    <!-- 3 Category Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      <article
        v-for="cat in displayCategories"
        :key="cat.id"
        class="card group overflow-hidden border border-[var(--glass-border)] bg-[var(--surface-raised)] hover:border-[var(--brass)]/50 transition-all duration-300 flex flex-col rounded-2xl shadow-md hover:shadow-xl"
      >
        <!-- Room Visual Image with aspect ratio -->
        <div class="relative aspect-[16/10] overflow-hidden bg-[var(--deep)] border-b border-[var(--glass-border)]">
          <img
            :src="cat.image"
            :alt="cat.imageAlt"
            class="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
            width="800"
            height="500"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-[var(--deep)]/50 to-transparent pointer-events-none" />

          <!-- Category Badge -->
          <div class="absolute top-4 left-4">
            <span class="px-3 py-1 rounded-full text-xs font-semibold bg-[var(--deep)]/85 text-[var(--mist)] border border-[var(--glass-border)] shadow-sm">
              Up to {{ cat.capacity }} {{ cat.capacity === 1 ? 'Guest' : 'Guests' }}
            </span>
          </div>

          <!-- Concept Badge -->
          <div v-if="cat.isConcept" class="absolute top-4 right-4">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-black/60 text-[#d9b87f] border border-[#d9b87f]/30 backdrop-blur-md shadow-sm">
              Design Concept
            </span>
          </div>

          <!-- Price Tag Overlay -->
          <div class="absolute bottom-4 right-4 bg-[var(--surface-raised)]/95 backdrop-blur-md px-3.5 py-1.5 rounded-xl border border-[var(--glass-border)] text-right shadow-sm">
            <span class="text-[10px] uppercase font-semibold text-[var(--muted)] block tracking-wider">From</span>
            <span class="serif text-lg font-bold text-[var(--brand-text)]">
              ${{ cat.startingRate }}
              <span class="text-xs font-normal text-[var(--muted)]">/ night</span>
            </span>
          </div>
        </div>

        <!-- Room Body -->
        <div class="p-6 sm:p-7 flex flex-col grow justify-between space-y-5">
          <div class="space-y-3">
            <h3 class="serif text-2xl font-medium text-[var(--brand-text)] group-hover:text-[var(--brass)] transition-colors">
              {{ cat.name }}
            </h3>
            <p class="text-xs text-[var(--brass)] font-medium">
              {{ cat.tagline }}
            </p>
            <p class="text-sm text-[var(--muted)] leading-relaxed">
              {{ cat.description }}
            </p>

            <!-- Verified Amenities -->
            <div class="pt-3 border-t border-[var(--line)]">
              <span class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)] block mb-2">
                Included Highlights
              </span>
              <ul class="flex flex-wrap gap-1.5 text-xs text-[var(--brand-text)]">
                <li
                  v-for="amenity in cat.amenities"
                  :key="amenity"
                  class="px-2.5 py-1 rounded-md bg-[var(--surface-muted)] text-[var(--muted)] text-[11px] font-medium"
                >
                  {{ amenity }}
                </li>
              </ul>
            </div>
          </div>

          <!-- Bottom Actions -->
          <div class="pt-4 border-t border-[var(--line)] space-y-2">
            <!-- Explore Room Spaces Button for Suite -->
            <button
              v-if="cat.id === 'family-suite'"
              type="button"
              class="btn-secondary w-full py-2 text-xs font-semibold flex items-center justify-center gap-1.5 hover:border-[var(--brass)] transition-colors"
              @click="openSpacesModal(cat.name)"
            >
              <svg class="w-3.5 h-3.5 text-[var(--brass)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>View 5 Suite Spaces (Bedroom, Living, Balcony)</span>
            </button>

            <button
              type="button"
              class="btn w-full py-2.5 text-sm font-semibold flex items-center justify-center gap-2 group-hover:bg-[var(--btn-primary-hover)] transition-colors"
              @click="checkRoomAvailability(cat)"
            >
              <span>Check availability for {{ cat.name }}</span>
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </article>
    </div>

    <!-- Design Concept Room Spaces Banner -->
    <div class="mt-12 p-6 rounded-2xl bg-[var(--surface-raised)] border border-[var(--glass-border)] flex flex-col sm:flex-row sm:items-center justify-between gap-5 shadow-sm">
      <div class="space-y-1">
        <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">Design Concept Previews</span>
        <h3 class="serif text-xl font-medium text-[var(--brand-text)]">
          Explore Deluxe Room &amp; Premier Room concept spaces
        </h3>
        <p class="text-xs sm:text-sm text-[var(--muted)]">
          Review 10 concept photos including marble bathrooms, dedicated work desks, and in-room minibars.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="btn-secondary px-4 py-2 rounded-xl text-xs font-semibold"
          @click="openSpacesModal('Deluxe Room')"
        >
          Deluxe Spaces (5)
        </button>
        <button
          type="button"
          class="btn-secondary px-4 py-2 rounded-xl text-xs font-semibold"
          @click="openSpacesModal('Premier Room')"
        >
          Premier Spaces (5)
        </button>
        <RouterLink
          to="/spaces"
          class="btn px-4 py-2 rounded-xl text-xs font-semibold"
        >
          All 28 Spaces &rarr;
        </RouterLink>
      </div>
    </div>

    <!-- Room Spaces Modal -->
    <RoomSpacesModal
      :show="Boolean(modalRoomName)"
      :room-name="modalRoomName || ''"
      :assets="modalAssets"
      @close="closeSpacesModal"
      @book="handleBookFromModal"
    />
  </section>
</template>
