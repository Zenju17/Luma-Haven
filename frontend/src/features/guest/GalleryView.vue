<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../utils/responsiveImage'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import SiteLayout from '../../layouts/SiteLayout.vue'
import HotelImage from '../../components/HotelImage.vue'
import RoomTourModal from './components/RoomTourModal.vue'
import {
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
    <div class="gallery-page py-8 sm:py-12">
      <div class="g-head">
        <h1 class="g-title">Gallery</h1>
        <p>Courtyard rooms, the rooftop terrace and the dining lounge. Tap a photo to see it larger.</p>
      </div>

      <div class="g-tours" role="group" aria-label="Room tours">
        <button type="button" class="g-tour" @click="openTour('suite')">Family Suite Tour (5)</button>
        <button type="button" class="g-tour" @click="openTour('deluxe')">Deluxe Room Tour (5)</button>
        <button type="button" class="g-tour" @click="openTour('premier')">Premier Room Tour (5)</button>
      </div>

      <div class="g-filters" role="tablist">
        <button
          v-for="filter in filters"
          :key="filter.id"
          type="button"
          role="tab"
          :aria-selected="activeFilter === filter.id"
          class="g-filter"
          @click="activeFilter = filter.id"
        >{{ filter.label }} ({{ getImagesByCategory(filter.id).length }})</button>
      </div>

      <p v-if="displayedImages.length === 0" class="g-empty">No photos in this group yet. Pick another from the list above.</p>

      <div class="g-masonry">
        <figure v-for="(img, index) in displayedImages" :key="img.id" class="g-item">
          <button type="button" class="g-photo" :aria-label="`View ${img.locationTag} larger`" @click="openLightbox(index)">
            <HotelImage
              :src="img.src"
              :alt="img.alt"
              :aspect-ratio="`${img.width}/${img.height}`"
              :is-demo="img.isDemo"
              :facility-claim="img.facilityClaim"
            />
          </button>
          <figcaption>
            <strong>{{ img.locationTag }}</strong>
            <span>{{ img.caption }}<template v-if="img.isDemo"> Design concept.</template></span>
          </figcaption>
        </figure>
      </div>

      <Transition name="lb-fade">
        <div v-if="activeLightbox" class="lb-scrim" role="dialog" aria-modal="true" :aria-label="activeLightbox.locationTag" @click.self="closeLightbox">
          <div class="lb-panel">
            <div class="lb-head">
              <div>
                <h2 class="lb-title">{{ activeLightbox.locationTag }}</h2>
                <p class="lb-sub">{{ (lightboxIndex ?? 0) + 1 }} of {{ displayedImages.length }}</p>
              </div>
              <button type="button" class="lb-close" aria-label="Close" @click="closeLightbox"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
            </div>
            <div class="lb-stage">
              <img :src="activeLightbox.src" :srcset="responsiveSrcset(activeLightbox.src)" :sizes="SIZES.lightbox" :alt="activeLightbox.alt" />
              <div v-if="activeLightbox.isDemo" class="lb-chips"><span class="lb-chip">{{ activeLightbox.facilityClaim || 'Design concept' }}</span></div>
              <button v-if="displayedImages.length > 1" type="button" class="lb-nav lb-nav--prev" aria-label="Previous image" @click="prev"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" /></svg></button>
              <button v-if="displayedImages.length > 1" type="button" class="lb-nav lb-nav--next" aria-label="Next image" @click="next"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" /></svg></button>
            </div>
            <p class="lb-caption">{{ activeLightbox.caption }}</p>
          </div>
        </div>
      </Transition>

      <RoomTourModal :show="Boolean(activeTourRoom)" :room-type-key="activeTourRoom || 'suite'" @close="closeTour" />
    </div>
  </SiteLayout>
</template>

<style scoped>
.g-head { display: grid; gap: .5rem; max-width: 60ch; margin-bottom: 1.5rem; }
.g-title { font-size: 3.0625rem; color: var(--river); }
.g-head p { color: var(--silt); }
.g-tours, .g-filters { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: 1rem; }
.g-tour, .g-filter { min-height: 44px; padding: 0 1rem; border-radius: var(--radius-pill); border: 1.5px solid var(--rule); color: var(--river); font: 500 .875rem var(--font-text); }
.g-tour { border-color: var(--river); }
.g-filter[aria-selected="true"] { background: var(--river); border-color: var(--river); color: var(--palm-leaf); }
.g-empty { padding: 2rem 0; color: var(--silt); }
.g-masonry { columns: 1; column-gap: 1.25rem; margin-top: 1.5rem; }
.g-item { break-inside: avoid; margin-bottom: 1.5rem; }
.g-photo { display: block; width: 100%; border-radius: var(--radius-photo); overflow: hidden; }
.g-item figcaption { display: grid; margin-top: .5rem; font-size: .875rem; color: var(--silt); }
.g-item figcaption strong { color: var(--river); font-weight: 600; }
@media (min-width: 640px) { .g-masonry { columns: 2; } }
@media (min-width: 1024px) { .g-masonry { columns: 3; } }
</style>
