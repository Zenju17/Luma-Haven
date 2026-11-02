<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../utils/responsiveImage'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import SiteLayout from '../../layouts/SiteLayout.vue'
import HotelImage from '../../components/HotelImage.vue'
import RoomTourModal from './components/RoomTourModal.vue'
import {
  HOTEL_IMAGES,
  getImagesByCategory,
  type HotelImageRecord,
} from '../../data/hotelImages'

const filters = [
  { id: 'all', label: 'All Photos' },
  { id: 'hotel', label: 'Hotel & Grounds' },
  { id: 'rooms', label: 'Rooms & Suites' },
  { id: 'dining', label: 'Dining' },
  { id: 'facilities', label: 'Facilities' },
  { id: 'views', label: 'Views' },
]

const activeFilter = ref('all')
const activeTourRoom = ref<'deluxe' | 'premier' | 'suite' | null>(null)

const displayedImages = computed<HotelImageRecord[]>(() => {
  return getImagesByCategory(activeFilter.value)
})

// Lightbox state
const lightboxIndex = ref<number | null>(null)
const activeLightbox = computed<HotelImageRecord | null>(() => {
  if (lightboxIndex.value === null) return null
  return displayedImages.value[lightboxIndex.value] || null
})

function openLightbox(index: number) {
  lightboxIndex.value = index
}

function closeLightbox() {
  lightboxIndex.value = null
}

function next() {
  if (lightboxIndex.value === null) return
  lightboxIndex.value = (lightboxIndex.value + 1) % displayedImages.value.length
}

function prev() {
  if (lightboxIndex.value === null) return
  const len = displayedImages.value.length
  lightboxIndex.value = (lightboxIndex.value - 1 + len) % len
}

function handleKeydown(e: KeyboardEvent) {
  if (lightboxIndex.value === null) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft') prev()
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

function openTour(roomKey: 'deluxe' | 'premier' | 'suite') {
  activeTourRoom.value = roomKey
}

function closeTour() {
  activeTourRoom.value = null
}
</script>

<template>
  <SiteLayout>
    <div class="gallery-page py-8 sm:py-12 space-y-10">
      <!-- Page Header -->
      <div class="max-w-3xl space-y-3">
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--glass-border)] bg-[var(--surface-muted)] text-[var(--brass)] text-xs font-semibold tracking-wider uppercase">
          <span class="w-1.5 h-1.5 rounded-full bg-[var(--brass)] animate-pulse" />
          Visual Archive · {{ HOTEL_IMAGES.length }} Hotel Locations
        </div>
        <h1 class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
          The Luma-Haven Gallery<span class="text-[var(--brass)]">.</span>
        </h1>
        <p class="text-sm sm:text-base text-[var(--muted)] leading-relaxed">
          Explore every corner of our boutique property, from peaceful courtyard guest rooms to shaded rooftop terraces and atmospheric dining lounges.
        </p>
      </div>

      <!-- Quick Room Tour Banners -->
      <div class="p-6 rounded-2xl bg-[var(--surface-raised)] border border-[var(--glass-border)] flex flex-col md:flex-row md:items-center justify-between gap-5 shadow-sm">
        <div class="space-y-1">
          <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">Virtual Room Collections</span>
          <h2 class="serif text-xl font-medium text-[var(--brand-text)]">
            Explore complete room tours by category
          </h2>
          <p class="text-xs sm:text-sm text-[var(--muted)]">
            Experience multi-angle photography of bedrooms, bathrooms, writing desks, and private balconies.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            class="btn-secondary px-4 py-2 rounded-xl text-xs font-semibold hover:border-[var(--brass)] transition-colors"
            @click="openTour('suite')"
          >
            Family Suite Tour (5)
          </button>
          <button
            type="button"
            class="btn-secondary px-4 py-2 rounded-xl text-xs font-semibold hover:border-[var(--brass)] transition-colors"
            @click="openTour('deluxe')"
          >
            Deluxe Room Tour (5)
          </button>
          <button
            type="button"
            class="btn-secondary px-4 py-2 rounded-xl text-xs font-semibold hover:border-[var(--brass)] transition-colors"
            @click="openTour('premier')"
          >
            Premier Room Tour (5)
          </button>
        </div>
      </div>

      <!-- Category Filter Tabs -->
      <div class="flex items-center gap-2 overflow-x-auto pb-3 border-b border-[var(--line)] scrollbar-none" role="tablist">
        <button
          v-for="filter in filters"
          :key="filter.id"
          type="button"
          role="tab"
          :aria-selected="activeFilter === filter.id"
          class="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold tracking-wide whitespace-nowrap transition-all flex items-center gap-2"
          :class="activeFilter === filter.id
            ? 'bg-[var(--brass)] text-[var(--deep)] shadow-sm'
            : 'bg-[var(--surface-raised)] border border-[var(--glass-border)] text-[var(--brand-text)] hover:border-[var(--brass)]/50'"
          @click="activeFilter = filter.id"
        >
          <span>{{ filter.label }}</span>
          <span
            class="text-[11px] font-mono px-1.5 py-0.2 rounded-full"
            :class="activeFilter === filter.id ? 'bg-black/15' : 'bg-[var(--surface-muted)] text-[var(--muted)]'"
          >
            {{ getImagesByCategory(filter.id).length }}
          </span>
        </button>
      </div>

      <!-- Empty State -->
      <div v-if="displayedImages.length === 0" class="card p-12 text-center rounded-2xl border border-[var(--glass-border)]">
        <p class="text-base text-[var(--muted)]">No images available for this filter.</p>
      </div>

      <!-- Responsive Photo Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
        <article
          v-for="(img, index) in displayedImages"
          :key="img.id"
          class="card group rounded-2xl overflow-hidden border border-[var(--glass-border)] bg-[var(--surface-raised)] hover:border-[var(--brass)]/60 transition-all shadow-sm hover:shadow-lg flex flex-col cursor-pointer"
          @click="openLightbox(index)"
        >
          <!-- HotelImage with Aspect Ratio -->
          <div class="relative overflow-hidden aspect-[16/11] bg-[var(--deep)]">
            <HotelImage
              :src="img.src"
              :alt="img.alt"
              aspect-ratio="16/11"
              :is-demo="img.isDemo"
              :facility-claim="img.facilityClaim"
              class="group-hover:scale-105 transition-transform duration-500"
            />

            <!-- Location Overlay -->
            <div class="absolute bottom-3 left-3 right-3 px-3 py-1.5 rounded-lg bg-black/70 backdrop-blur-md border border-white/15 text-white flex items-center justify-between text-xs">
              <span class="font-medium truncate mr-2">{{ img.locationTag }}</span>
              <span class="text-[10px] font-mono text-stone-300 shrink-0">{{ img.width }}×{{ img.height }}</span>
            </div>
          </div>

          <!-- Card Body -->
          <div class="p-5 flex flex-col grow justify-between space-y-3">
            <div class="space-y-1">
              <h3 class="serif text-lg font-medium text-[var(--brand-text)] group-hover:text-[var(--brass)] transition-colors">
                {{ img.locationTag }}
              </h3>
              <p class="text-xs text-[var(--muted)] leading-relaxed">
                {{ img.caption }}
              </p>
            </div>

            <div class="pt-2 border-t border-[var(--line)] flex items-center justify-between text-xs">
              <span class="capitalize text-[var(--muted)] font-mono text-[11px]">
                {{ img.category }}
              </span>
              <span class="text-[var(--brass)] font-semibold inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                Inspect image &rarr;
              </span>
            </div>
          </div>
        </article>
      </div>

      <!-- Lightbox Modal -->
      <Transition name="fade">
        <div
          v-if="activeLightbox"
          class="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-3 sm:p-6"
          role="dialog"
          aria-modal="true"
          :aria-label="activeLightbox.locationTag"
          @click.self="closeLightbox"
        >
          <div class="relative w-full max-w-5xl bg-[var(--surface-raised)] border border-[var(--glass-border)] rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[94vh]">
            <!-- Header -->
            <div class="px-5 py-3.5 border-b border-[var(--line)] bg-[var(--surface-muted)] flex items-center justify-between gap-4">
              <div class="space-y-0.5">
                <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
                  {{ activeLightbox.category }} · {{ activeLightbox.locationTag }}
                </span>
                <h3 class="serif text-xl sm:text-2xl font-medium text-[var(--brand-text)] flex items-center gap-3">
                  {{ activeLightbox.caption }}
                </h3>
              </div>

              <div class="flex items-center gap-3">
                <span class="text-xs font-mono px-2.5 py-1 rounded-full bg-[var(--surface-overlay)] text-[var(--muted)] border border-[var(--glass-border)]">
                  {{ (lightboxIndex ?? 0) + 1 }} of {{ displayedImages.length }}
                </span>
                <button
                  type="button"
                  class="p-2 rounded-lg text-[var(--muted)] hover:text-[var(--brand-text)] hover:bg-[var(--surface-overlay)] transition-colors"
                  aria-label="Close"
                  @click="closeLightbox"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Image Viewport -->
            <div class="relative grow overflow-hidden bg-black flex items-center justify-center min-h-[360px] sm:min-h-[500px]">
              <img
                :src="activeLightbox.src"
                :srcset="responsiveSrcset(activeLightbox.src)"
                :sizes="SIZES.lightbox"
                :alt="activeLightbox.alt"
                class="max-h-[68vh] w-auto max-w-full object-contain mx-auto"
              />

              <!-- Navigation Controls -->
              <button
                v-if="displayedImages.length > 1"
                type="button"
                class="absolute left-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
                aria-label="Previous image"
                @click="prev"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                v-if="displayedImages.length > 1"
                type="button"
                class="absolute right-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
                aria-label="Next image"
                @click="next"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            <!-- Footer Details -->
            <div class="p-4 bg-[var(--surface-muted)] border-t border-[var(--line)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div class="flex items-center gap-3">
                <span class="font-semibold text-[var(--brand-text)]">{{ activeLightbox.locationTag }}</span>
                <span v-if="activeLightbox.isDemo" class="px-2 py-0.5 rounded text-[10px] font-medium bg-[#d9b87f]/20 text-[#d9b87f] border border-[#d9b87f]/40">
                  {{ activeLightbox.facilityClaim || 'Design Concept' }}
                </span>
              </div>
              <div class="flex items-center gap-4 text-[var(--muted)] font-mono text-[11px]">
                <span>{{ activeLightbox.width }} × {{ activeLightbox.height }} px</span>
                <span>{{ activeLightbox.src }}</span>
              </div>
            </div>
          </div>
        </div>
      </Transition>

      <!-- Virtual Room Tour Modal -->
      <RoomTourModal
        :show="Boolean(activeTourRoom)"
        :room-type-key="activeTourRoom || 'suite'"
        @close="closeTour"
      />
    </div>
  </SiteLayout>
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
