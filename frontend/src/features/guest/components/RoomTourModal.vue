<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../../utils/responsiveImage'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getRoomTourImages, type HotelImageRecord } from '../../../data/hotelImages'
import type { Room } from '../../../types'

const router = useRouter()

const props = defineProps<{
  show: boolean
  roomTypeKey: 'deluxe' | 'premier' | 'suite'
  dbRoom?: Room | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'book', roomType: string): void
}>()

const activeIndex = ref(0)
const touchStartX = ref(0)
const touchEndX = ref(0)
const isZoomed = ref(false)

const roomDetails = computed(() => {
  const map = {
    suite: {
      key: 'suite' as const,
      name: 'Family Suite',
      dbMatch: 'Family Suite',
      tagline: 'Spacious multi-room sanctuary with arched living lounge',
      capacity: 4,
      bedConfig: '1 Master King Bed + 2 Twin Daybeds',
      roomSize: '68 m² / 732 sq ft',
      basePrice: 155,
      amenities: [
        'Master King Bed + 2 Daybeds',
        'Arched Living Lounge Alcove',
        'Double Vanity Stone Bathroom',
        'Deep Soaking Bathtub & Rain Shower',
        'Private Shaded Balcony & Courtyard Vista',
        'Dedicated Oak Dining Table',
        'Physical Handcrafted Brass Key',
        'High-Speed Fiber Wi-Fi',
      ],
      description: 'An expansive architectural sanctuary offering distinct living and sleeping chambers connected by gentle arches. Designed for families and discerning travelers who value unhurried space, restorative acoustics, and natural materials.',
    },
    deluxe: {
      key: 'deluxe' as const,
      name: 'Garden King (Deluxe Collection)',
      dbMatch: 'Garden King',
      tagline: 'Courtyard retreat with lush garden views & solid timber finishes',
      capacity: 2,
      bedConfig: '1 Plush King Bed',
      roomSize: '38 m² / 409 sq ft',
      basePrice: 85,
      amenities: [
        'Plush King-Sized Bed',
        'Courtyard Garden View',
        'Dedicated Hardwood Work Desk',
        'Marble Bathroom with Rain Shower',
        'Open Wardrobe & Brass Luggage Rack',
        'Hand-Stamped Physical Brass Key',
        'Acoustically Insulated Walls',
        'Organic Cotton Percale Linens',
      ],
      description: 'A serene sanctuary featuring floor-to-ceiling French doors opening toward our interior courtyard greenery. Balanced with an ergonomic writing desk and soothing ambient sconce lighting.',
    },
    premier: {
      key: 'premier' as const,
      name: 'City Twin / Premier Room',
      dbMatch: 'City Twin',
      tagline: 'Morning light, cushioned window banquette & acoustic privacy',
      capacity: 2,
      bedConfig: '2 Twin Beds or 1 King Bed',
      roomSize: '34 m² / 366 sq ft',
      basePrice: 72,
      amenities: [
        'Twin Bedding or King Conversion',
        'Window Banquette Seating Lounge',
        'Luxury Ensuite Stone Bathroom',
        'Artisanal Minibar & Tea Station',
        'Soundproof Double-Glazed Windows',
        'Physical Brass Key Collection',
        'Fiber Wi-Fi & Multiple Power Ports',
      ],
      description: 'Filled with gentle morning sunrise, acoustic soundproofing, and a custom window lounge for quiet tea and reading. Complete with a curated in-room refreshment cabinet.',
    },
  }

  return map[props.roomTypeKey] || map.suite
})

const images = computed<HotelImageRecord[]>(() => {
  return getRoomTourImages(props.roomTypeKey)
})

const activeImage = computed<HotelImageRecord>(() => {
  return images.value[activeIndex.value] || images.value[0]
})

function next() {
  if (!images.value.length) return
  activeIndex.value = (activeIndex.value + 1) % images.value.length
}

function prev() {
  if (!images.value.length) return
  activeIndex.value = (activeIndex.value - 1 + images.value.length) % images.value.length
}

function selectSection(idx: number) {
  activeIndex.value = idx
}

function toggleZoom() {
  isZoomed.value = !isZoomed.value
}

function handleTouchStart(e: TouchEvent) {
  touchStartX.value = e.touches[0].clientX
}

function handleTouchEnd(e: TouchEvent) {
  touchEndX.value = e.changedTouches[0].clientX
  const delta = touchEndX.value - touchStartX.value
  if (Math.abs(delta) > 40) {
    if (delta > 0) prev()
    else next()
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (!props.show) return
  if (e.key === 'Escape') {
    if (isZoomed.value) isZoomed.value = false
    else emit('close')
  }
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft') prev()
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

function handleBookNow() {
  emit('book', roomDetails.value.dbMatch)
  router.push({
    path: '/rooms',
    query: { type: roomDetails.value.dbMatch, occupants: String(roomDetails.value.capacity) },
  })
}
</script>

<template>
  <Transition name="fade">
    <div
      v-if="show"
      class="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      :aria-label="`${roomDetails.name} Virtual Room Tour`"
      @click.self="emit('close')"
    >
      <div class="relative w-full max-w-6xl bg-[var(--surface-raised)] border border-[var(--glass-border)] rounded-2xl overflow-hidden shadow-2xl flex flex-col my-auto max-h-[96vh]">
        <!-- Tour Header -->
        <div class="px-6 py-4 border-b border-[var(--line)] bg-[var(--surface-muted)] flex items-center justify-between gap-4 shrink-0">
          <div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">Virtual Room Tour</span>
              <span v-if="activeImage?.isDemo" class="px-2 py-0.5 rounded text-[10px] font-medium bg-[#d9b87f]/20 text-[#d9b87f] border border-[#d9b87f]/40">
                Design Concept
              </span>
            </div>
            <h2 class="serif text-xl sm:text-2xl font-medium text-[var(--brand-text)] flex items-center gap-3">
              {{ roomDetails.name }}
            </h2>
          </div>

          <div class="flex items-center gap-3">
            <button
              type="button"
              class="btn px-5 py-2 text-xs sm:text-sm font-semibold rounded-lg shadow-sm"
              @click="handleBookNow"
            >
              Book this room from ${{ dbRoom?.rate_minor ? (dbRoom.rate_minor / 100).toFixed(0) : roomDetails.basePrice }}/night
            </button>
            <button
              type="button"
              class="p-2 rounded-lg text-[var(--muted)] hover:text-[var(--brand-text)] hover:bg-[var(--surface-overlay)] transition-colors"
              aria-label="Close tour"
              @click="emit('close')"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Tour Content Area: Split View -->
        <div class="grid grid-cols-1 lg:grid-cols-12 grow overflow-y-auto">
          <!-- Left: Featured Photograph & Visual Tour (7 cols) -->
          <div
            class="lg:col-span-7 bg-black relative flex flex-col items-center justify-center min-h-[340px] sm:min-h-[460px] overflow-hidden select-none"
            @touchstart="handleTouchStart"
            @touchend="handleTouchEnd"
          >
            <!-- Large Image with Click-to-Zoom -->
            <img
              v-if="activeImage"
              :src="activeImage.src"
              :srcset="responsiveSrcset(activeImage.src)"
              :sizes="SIZES.lightbox"
              :alt="activeImage.alt"
              :class="[
                'max-h-[60vh] w-auto max-w-full object-contain mx-auto transition-transform duration-300 cursor-zoom-in',
                isZoomed ? 'scale-125 cursor-zoom-out' : 'scale-100',
              ]"
              @click="toggleZoom"
            />

            <!-- Prev / Next Controls -->
            <button
              v-if="images.length > 1"
              type="button"
              class="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Previous space"
              @click="prev"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              v-if="images.length > 1"
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Next space"
              @click="next"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>

            <!-- Bottom Floating Caption -->
            <div class="absolute bottom-3 left-3 right-3 p-3 rounded-xl backdrop-blur-md bg-black/75 border border-white/15 text-white flex items-center justify-between text-xs">
              <div>
                <p class="font-semibold text-[#d9b87f]">
                  {{ activeImage?.locationTag }}
                </p>
                <p class="text-stone-300 text-[11px] mt-0.5 line-clamp-1">
                  {{ activeImage?.caption }}
                </p>
              </div>
              <span class="text-[10px] font-mono text-stone-400 shrink-0">
                {{ activeIndex + 1 }} / {{ images.length }}
              </span>
            </div>
          </div>

          <!-- Right: Room Details, Amenities & Thumbnail Tour (5 cols) -->
          <div class="lg:col-span-5 p-6 sm:p-7 flex flex-col justify-between space-y-6 overflow-y-auto bg-[var(--surface-raised)]">
            <!-- Room Specs -->
            <div class="space-y-4">
              <div class="space-y-1">
                <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
                  Accommodation Profile
                </span>
                <p class="text-xs text-[var(--muted)]">
                  {{ roomDetails.tagline }}
                </p>
              </div>

              <!-- Quick Specs Grid -->
              <div class="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-[var(--surface-muted)] border border-[var(--glass-border)] text-xs">
                <div>
                  <span class="text-[var(--muted)] block">Capacity</span>
                  <span class="font-semibold text-[var(--brand-text)]">Up to {{ roomDetails.capacity }} Guests</span>
                </div>
                <div>
                  <span class="text-[var(--muted)] block">Bed Setup</span>
                  <span class="font-semibold text-[var(--brand-text)]">{{ roomDetails.bedConfig }}</span>
                </div>
                <div>
                  <span class="text-[var(--muted)] block">Room Area</span>
                  <span class="font-semibold text-[var(--brand-text)]">{{ roomDetails.roomSize }}</span>
                </div>
                <div>
                  <span class="text-[var(--muted)] block">Key Type</span>
                  <span class="font-semibold text-[var(--brand-text)]">Solid Brass Physical Key</span>
                </div>
                <div>
                  <span class="text-[var(--muted)] block">Check-in</span>
                  <span class="font-semibold text-[var(--brand-text)]">From 14:00</span>
                </div>
                <div>
                  <span class="text-[var(--muted)] block">Check-out</span>
                  <span class="font-semibold text-[var(--brand-text)]">Until 12:00 (Noon)</span>
                </div>
              </div>

              <!-- Room Description -->
              <p class="text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
                {{ roomDetails.description }}
              </p>

              <!-- Included Highlights -->
              <div class="space-y-2">
                <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted)] block">
                  Included Amenities
                </span>
                <ul class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-[var(--brand-text)]">
                  <li v-for="(amenity, aIdx) in roomDetails.amenities" :key="aIdx" class="flex items-center gap-2 text-[var(--muted)]">
                    <svg class="w-3.5 h-3.5 text-[var(--brass)] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
                    </svg>
                    <span class="truncate">{{ amenity }}</span>
                  </li>
                </ul>
              </div>
            </div>

            <!-- Tour Section Navigation Thumbnails -->
            <div class="pt-4 border-t border-[var(--line)] space-y-2">
              <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)] block">
                Tour Spaces ({{ images.length }} Views)
              </span>
              <div class="grid grid-cols-5 gap-2">
                <button
                  v-for="(img, idx) in images"
                  :key="img.id"
                  type="button"
                  class="relative aspect-[4/3] rounded-lg overflow-hidden border-2 transition-all focus:outline-none"
                  :class="activeIndex === idx ? 'border-[var(--brass)] scale-105 shadow-md' : 'border-transparent opacity-70 hover:opacity-100'"
                  :title="img.locationTag"
                  @click="selectSection(idx)"
                >
                  <img :src="img.src" :srcset="responsiveSrcset(img.src)" :sizes="SIZES.thumb" :alt="img.alt" class="w-full h-full object-cover" />
                  <span class="absolute bottom-0 inset-x-0 bg-black/80 text-[8px] text-white text-center py-0.5 truncate px-1">
                    {{ img.section || 'view' }}
                  </span>
                </button>
              </div>

              <!-- Book Now Action -->
              <div class="pt-3">
                <button
                  type="button"
                  class="btn w-full py-3 font-semibold text-sm flex items-center justify-center gap-2"
                  @click="handleBookNow"
                >
                  <span>Book this room now</span>
                  <span aria-hidden="true">&rarr;</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
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
