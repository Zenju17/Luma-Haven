<script setup lang="ts">
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
  <div class="spaces-explorer py-8 sm:py-12">
    <!-- Category Filter Tabs -->
    <div class="flex items-center gap-2 overflow-x-auto pb-4 mb-8 border-b border-[var(--line)] scrollbar-none">
      <button
        v-for="cat in categories"
        :key="cat.id"
        type="button"
        class="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold tracking-wide whitespace-nowrap transition-all flex items-center gap-2"
        :class="activeCategory === cat.id
          ? 'bg-[var(--brass)] text-[var(--deep)] shadow-sm'
          : 'bg-[var(--surface-raised)] border border-[var(--glass-border)] text-[var(--brand-text)] hover:border-[var(--brass)]/50'"
        @click="activeCategory = cat.id"
      >
        <span>{{ cat.label }}</span>
        <span
          class="text-[11px] font-mono px-1.5 py-0.2 rounded-full"
          :class="activeCategory === cat.id ? 'bg-black/15' : 'bg-[var(--surface-muted)] text-[var(--muted)]'"
        >
          {{
            cat.id === 'all'
              ? allSpaces.length
              : cat.id === 'details'
                ? allSpaces.filter(s => s.areaCategory === 'details' || s.asset.original_filename?.includes('amenities') || s.asset.original_filename?.includes('minibar') || s.asset.original_filename?.includes('work_desk')).length
                : allSpaces.filter(s => s.areaCategory === cat.id).length
          }}
        </span>
      </button>
    </div>

    <!-- Empty State -->
    <div v-if="filteredSpaces.length === 0" class="card p-12 text-center rounded-2xl border border-[var(--glass-border)]">
      <p class="text-base text-[var(--muted)]">No spaces discovered for this category.</p>
    </div>

    <!-- Responsive Spaces Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
      <article
        v-for="(space, index) in filteredSpaces"
        :key="space.id"
        class="card rounded-2xl overflow-hidden border border-[var(--glass-border)] bg-[var(--surface-raised)] hover:border-[var(--brass)]/60 transition-all shadow-sm hover:shadow-md flex flex-col group cursor-pointer"
        @click="openLightbox(index)"
      >
        <!-- Photo Container -->
        <div class="relative aspect-[16/11] overflow-hidden bg-[var(--deep)]">
          <img
            :src="space.asset.image_url"
            :alt="space.asset.alt_text"
            class="w-full h-full object-cover transform transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-70 group-hover:opacity-40 transition-opacity" />

          <!-- Location Badge (Derived from Filename) -->
          <div class="absolute top-3 left-3 px-2.5 py-1 rounded-md text-[11px] font-medium bg-black/60 backdrop-blur-md text-white border border-white/20">
            {{ space.floorLocation }}
          </div>

          <!-- Concept / Verified Badge -->
          <div class="absolute top-3 right-3">
            <span
              v-if="space.isConcept"
              class="px-2.5 py-1 rounded-md text-[10px] font-semibold tracking-wide bg-black/60 backdrop-blur-md text-[#d9b87f] border border-[#d9b87f]/40"
            >
              {{ space.facilityClaim ? `Concept · ${space.facilityClaim}` : 'Design Concept' }}
            </span>
            <span
              v-else
              class="px-2.5 py-1 rounded-md text-[10px] font-semibold tracking-wide bg-emerald-950/80 backdrop-blur-md text-emerald-300 border border-emerald-500/30"
            >
              Verified
            </span>
          </div>

          <!-- Bottom Dimensions & Filename Tag -->
          <div class="absolute bottom-2.5 right-3 text-[10px] font-mono text-stone-300 bg-black/40 px-2 py-0.5 rounded backdrop-blur-sm">
            {{ space.asset.width }}×{{ space.asset.height }}
          </div>
        </div>

        <!-- Body -->
        <div class="p-5 flex flex-col grow justify-between gap-4">
          <div class="space-y-1.5">
            <h3 class="serif text-xl font-medium text-[var(--brand-text)] group-hover:text-[var(--brass)] transition-colors">
              {{ space.spaceName }}
            </h3>
            <p class="text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
              {{ space.description }}
            </p>
          </div>

          <div class="pt-3 border-t border-[var(--line)] flex items-center justify-between text-xs">
            <span class="font-mono text-[var(--muted)] truncate max-w-[170px]" :title="space.asset.original_filename">
              {{ space.asset.original_filename }}
            </span>

            <span class="font-medium text-[var(--brass)] group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
              View photo →
            </span>
          </div>
        </div>
      </article>
    </div>

    <!-- Lightbox Modal -->
    <Transition name="fade">
      <div
        v-if="activeLightboxItem"
        class="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-3 sm:p-6"
        role="dialog"
        aria-modal="true"
        :aria-label="activeLightboxItem.spaceName"
        @click.self="closeLightbox"
      >
        <div class="relative w-full max-w-6xl bg-[var(--surface-raised)] border border-[var(--glass-border)] rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[94vh]">
          <!-- Lightbox Header -->
          <div class="px-5 py-3.5 border-b border-[var(--line)] bg-[var(--surface-muted)] flex items-center justify-between gap-4">
            <div class="space-y-0.5">
              <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
                Location: {{ activeLightboxItem.floorLocation }}
              </span>
              <h2 class="serif text-xl sm:text-2xl font-medium text-[var(--brand-text)] flex items-center gap-3">
                {{ activeLightboxItem.spaceName }}
                <span class="text-xs font-mono font-normal px-2.5 py-0.5 rounded-full bg-[var(--surface-overlay)] text-[var(--muted)] border border-[var(--glass-border)]">
                  {{ (lightboxIndex ?? 0) + 1 }} of {{ filteredSpaces.length }}
                </span>
              </h2>
            </div>

            <div class="flex items-center gap-3">
              <button
                v-if="activeLightboxItem.roomTypeName"
                type="button"
                class="btn px-4 py-2 text-xs font-semibold"
                @click="handleBookRoom(activeLightboxItem.roomTypeName)"
              >
                Book {{ activeLightboxItem.roomTypeName }}
              </button>
              <button
                type="button"
                class="p-2 rounded-lg text-[var(--muted)] hover:text-[var(--brand-text)] hover:bg-[var(--surface-overlay)] transition-colors"
                aria-label="Close photo"
                @click="closeLightbox"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Lightbox Image Viewport -->
          <div class="relative grow overflow-hidden bg-black flex items-center justify-center min-h-[360px] sm:min-h-[520px]">
            <img
              :src="activeLightboxItem.asset.image_url"
              :alt="activeLightboxItem.asset.alt_text"
              class="max-h-[70vh] w-auto max-w-full object-contain mx-auto"
            />

            <!-- Left / Right Nav -->
            <button
              v-if="filteredSpaces.length > 1"
              type="button"
              class="absolute left-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Previous space photo"
              @click="prevLightbox"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              v-if="filteredSpaces.length > 1"
              type="button"
              class="absolute right-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Next space photo"
              @click="nextLightbox"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>

            <!-- Bottom Info Overlay -->
            <div class="absolute bottom-4 left-4 right-4 p-4 rounded-xl backdrop-blur-md bg-black/75 border border-white/15 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-[#d9b87f] uppercase tracking-wider">
                    Defined Location: {{ activeLightboxItem.spaceName }}
                  </span>
                  <span
                    v-if="activeLightboxItem.isConcept"
                    class="px-2 py-0.5 rounded text-[10px] font-medium bg-[#d9b87f]/20 text-[#d9b87f] border border-[#d9b87f]/40"
                  >
                    {{ activeLightboxItem.facilityClaim ? `Concept · ${activeLightboxItem.facilityClaim}` : 'Design Concept' }}
                  </span>
                </div>
                <p class="text-sm text-stone-200">
                  {{ activeLightboxItem.description }}
                </p>
              </div>

              <div class="flex items-center gap-4 text-xs font-mono text-stone-400 shrink-0">
                <span>{{ activeLightboxItem.asset.width }}×{{ activeLightboxItem.asset.height }} px</span>
                <span>{{ Math.round((activeLightboxItem.asset.file_size_bytes || 0) / 1024) }} KB</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
