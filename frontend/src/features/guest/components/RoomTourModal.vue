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
  <Transition name="lb-fade">
    <div v-if="show" class="lb-scrim" role="dialog" aria-modal="true" :aria-label="`${roomDetails.name} Virtual Room Tour`" @click.self="emit('close')">
      <div class="lb-panel">
        <div class="lb-head">
          <div>
            <h2 class="lb-title">{{ roomDetails.name }}</h2>
            <p class="lb-sub">{{ roomDetails.tagline }}</p>
          </div>
          <div class="lb-actions">
            <button type="button" class="btn" @click="handleBookNow">Book this room from ${{ dbRoom?.rate_minor ? (dbRoom.rate_minor / 100).toFixed(0) : roomDetails.basePrice }}/night</button>
            <button type="button" class="lb-close" aria-label="Close tour" @click="emit('close')"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
          </div>
        </div>

        <div class="tour-grid">
          <div>
            <div class="lb-stage" @touchstart="handleTouchStart" @touchend="handleTouchEnd">
              <img v-if="activeImage" :src="activeImage.src" :srcset="responsiveSrcset(activeImage.src)" :sizes="SIZES.lightbox" :alt="activeImage.alt" :class="['tour-img', isZoomed ? 'tour-img--zoom' : '']" @click="toggleZoom" />
              <div class="lb-chips">
                <span class="lb-chip">{{ roomDetails.roomSize }}</span>
                <span class="lb-chip">{{ roomDetails.bedConfig }}</span>
                <span class="lb-chip">Up to {{ roomDetails.capacity }} guests</span>
                <span v-if="activeImage?.isDemo" class="lb-chip">Design concept</span>
              </div>
              <button v-if="images.length > 1" type="button" class="lb-nav lb-nav--prev" aria-label="Previous space" @click="prev"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" /></svg></button>
              <button v-if="images.length > 1" type="button" class="lb-nav lb-nav--next" aria-label="Next space" @click="next"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" /></svg></button>
            </div>
            <p class="lb-caption tour-cap"><strong>{{ activeImage?.locationTag }}</strong> {{ activeImage?.caption }}</p>
            <div class="lb-thumbs">
              <button v-for="(img, idx) in images" :key="img.id" type="button" class="lb-thumb" :aria-current="activeIndex === idx" :aria-label="img.locationTag" @click="selectSection(idx)">
                <img :src="img.src" :srcset="responsiveSrcset(img.src)" :sizes="SIZES.thumb" :alt="img.alt" />
              </button>
            </div>
          </div>

          <div class="tour-side">
            <p>{{ roomDetails.description }}</p>
            <h3>What's included</h3>
            <ul>
              <li v-for="(amenity, aIdx) in roomDetails.amenities" :key="aIdx">{{ amenity }}</li>
            </ul>
            <p class="tour-times">Check-in from 14:00. Check-out by 12:00.</p>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.tour-grid { display: grid; gap: 1.25rem; }
.tour-img { cursor: zoom-in; transition: transform var(--duration-normal) ease; }
.tour-img--zoom { transform: scale(1.25); cursor: zoom-out; }
.tour-cap { margin: .6rem 0; font-size: .9375rem; }
.tour-side { display: grid; gap: .75rem; align-content: start; color: var(--silt); }
.tour-side h3 { font-size: 1.5625rem; color: var(--river); }
.tour-side ul { display: grid; gap: .35rem; list-style: disc inside; font-size: .9375rem; color: var(--river); }
.tour-times { padding-top: .75rem; border-top: 1px solid var(--rule); font-size: .875rem; }
@media (min-width: 1000px) { .tour-grid { grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr); } }
@media (prefers-reduced-motion: reduce) { .tour-img { transition: none; } }
</style>
