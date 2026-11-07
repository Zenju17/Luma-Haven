<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../../utils/responsiveImage'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import type { PublicVisualAssetsResponse } from '../../../types'
import { getGalleryCarouselImages } from '../../../data/hotelImages'

interface DisplaySlide {
  id: string | number
  title: string
  location: string
  caption: string
  src: string
  alt: string
  isConcept: boolean
  facilityClaim: string
  width?: number
}

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})

// Canonical captions and location tags mapped by image slug
const canonicalGalleryConfig: Record<string, { title: string; location: string; caption: string }> = {
  lobby: {
    title: 'Hotel Lobby & Reception',
    location: 'Ground Floor · Lobby & Reception',
    caption: 'A warm welcome awaits every guest.',
  },
  rooftop_pool: {
    title: 'Rooftop Swimming Pool',
    location: 'Level 4 · Rooftop Pool & Deck',
    caption: 'Relax above the city.',
  },
  restaurant: {
    title: 'Courtyard Restaurant',
    location: 'Courtyard · Restaurant & Dining',
    caption: 'Enjoy memorable dining moments.',
  },
  fitness_center: {
    title: 'Modern Fitness Center',
    location: 'Wellness Wing · Fitness Center',
    caption: 'Stay active throughout your stay.',
  },
  guest_lounge: {
    title: 'Mezzanine Guest Lounge',
    location: 'Mezzanine · Guest Lounge',
    caption: 'A peaceful space to unwind.',
  },
  city_view: {
    title: 'East Wing City Views',
    location: 'East Wing · City View Terrace',
    caption: 'Experience beautiful skyline views.',
  },
}

const galleryOrder = ['lobby', 'rooftop_pool', 'restaurant', 'fitness_center', 'guest_lounge', 'city_view']

const displayPhotos = computed<DisplaySlide[]>(() => {
  const assets = visualAssets.data.value?.gallery

  if (assets && assets.length > 0) {
    // Sort and map API assets according to canonical galleryOrder
    const mapped = galleryOrder.map(key => {
      const match = assets.find(a => (a.original_filename || '').includes(key))
      const config = canonicalGalleryConfig[key]
      if (match) {
        return {
          id: match.id,
          title: config?.title || match.title,
          location: config?.location || 'Hotel Space',
          caption: config?.caption || match.caption || match.alt_text,
          src: match.image_url,
          width: match.width,
          alt: match.alt_text,
          isConcept: match.source_type === 'CONCEPT',
          facilityClaim: match.facility_claim,
        }
      }
      return null
    }).filter(Boolean) as DisplaySlide[]

    if (mapped.length > 0) return mapped
  }

  // Instant fallback to curated registry assets
  return getGalleryCarouselImages().map(img => {
    return {
      id: img.id,
      title: img.locationTag.split('·')[1]?.trim() || img.locationTag,
      location: img.locationTag,
      caption: img.caption,
      src: img.src,
      alt: img.alt,
      isConcept: img.isDemo,
      facilityClaim: img.facilityClaim || '',
    }
  })
})

const currentIndex = ref(0)
const touchStartX = ref(0)
const touchEndX = ref(0)
const showLightbox = ref(false)

const currentSlide = computed(() => displayPhotos.value[currentIndex.value] || null)

function prev() {
  const len = displayPhotos.value.length
  if (len === 0) return
  currentIndex.value = (currentIndex.value - 1 + len) % len
}

function next() {
  const len = displayPhotos.value.length
  if (len === 0) return
  currentIndex.value = (currentIndex.value + 1) % len
}

function goTo(index: number) {
  currentIndex.value = index
}

function openLightbox() {
  showLightbox.value = true
}

function closeLightbox() {
  showLightbox.value = false
}

// Touch swipe support
function handleTouchStart(e: TouchEvent) {
  touchStartX.value = e.touches[0].clientX
}

function handleTouchEnd(e: TouchEvent) {
  touchEndX.value = e.changedTouches[0].clientX
  const deltaX = touchEndX.value - touchStartX.value
  if (Math.abs(deltaX) > 40) {
    if (deltaX > 0) prev()
    else next()
  }
}

// Global keyboard navigation
function handleKeyDown(e: KeyboardEvent) {
  if (showLightbox.value) {
    if (e.key === 'Escape') closeLightbox()
    else if (e.key === 'ArrowLeft') prev()
    else if (e.key === 'ArrowRight') next()
    return
  }

  if (e.key === 'ArrowLeft') {
    prev()
  } else if (e.key === 'ArrowRight') {
    next()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <section id="gallery" class="py-16 sm:py-20 border-t border-[var(--rule)]" aria-labelledby="gallery-heading">
    <div class="hg-head">
      <div>
        <h2 id="gallery-heading">Around the hotel</h2>
        <p>The lobby, the rooftop pool, the courtyard restaurant and the places in between.</p>
      </div>
      <div class="hg-ctrl">
        <span class="hg-count">Photo {{ currentIndex + 1 }} of {{ displayPhotos.length }}</span>
        <button type="button" class="lb-close" aria-label="Previous photo" @click="prev"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" /></svg></button>
        <button type="button" class="lb-close" aria-label="Next photo" @click="next"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" /></svg></button>
      </div>
    </div>

    <div class="hg-stage" tabindex="0" role="region" aria-label="Hotel gallery carousel" @touchstart="handleTouchStart" @touchend="handleTouchEnd" @click="openLightbox">
      <TransitionGroup name="fade">
        <div v-for="(photo, index) in displayPhotos" v-show="index === currentIndex" :key="photo.id" class="hg-slide">
          <img :src="photo.src" :srcset="responsiveSrcset(photo.src, photo.width)" :sizes="SIZES.card" :alt="photo.alt" loading="lazy" width="1600" height="1128" />
          <span v-if="photo.facilityClaim || photo.isConcept" class="lb-chip hg-chip">{{ photo.facilityClaim ? `Design concept: ${photo.facilityClaim}` : 'Design concept' }}</span>
        </div>
      </TransitionGroup>
    </div>
    <div v-if="currentSlide" class="hg-cap">
      <h3>{{ currentSlide.caption }}</h3>
      <p>{{ currentSlide.location }}</p>
    </div>

    <div class="hg-dots" role="tablist" aria-label="Gallery slides">
      <button v-for="(photo, index) in displayPhotos" :key="photo.id" type="button" role="tab" :aria-selected="index === currentIndex" :aria-label="`Slide ${index + 1}: ${photo.title}`" class="hg-dot" @click.stop="goTo(index)" />
    </div>

    <div class="hg-links">
      <RouterLink to="/gallery" class="btn">View the full gallery</RouterLink>
      <RouterLink to="/spaces" class="btn-secondary">See all spaces</RouterLink>
    </div>

    <Transition name="lb-fade">
      <div v-if="showLightbox && currentSlide" class="lb-scrim" role="dialog" aria-modal="true" :aria-label="currentSlide.title" @click.self="closeLightbox">
        <div class="lb-panel">
          <div class="lb-head">
            <div>
              <h3 class="lb-title">{{ currentSlide.caption }}</h3>
              <p class="lb-sub">{{ currentSlide.location }}, {{ currentIndex + 1 }} of {{ displayPhotos.length }}</p>
            </div>
            <button type="button" class="lb-close" aria-label="Close" @click="closeLightbox"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
          </div>
          <div class="lb-stage">
            <img :src="currentSlide.src" :srcset="responsiveSrcset(currentSlide.src, currentSlide.width)" :sizes="SIZES.lightbox" :alt="currentSlide.alt" />
            <div v-if="currentSlide.isConcept" class="lb-chips"><span class="lb-chip">{{ currentSlide.facilityClaim || 'Design concept' }}</span></div>
            <button type="button" class="lb-nav lb-nav--prev" aria-label="Previous photo" @click.stop="prev"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" /></svg></button>
            <button type="button" class="lb-nav lb-nav--next" aria-label="Next photo" @click.stop="next"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" /></svg></button>
          </div>
          <RouterLink to="/gallery" class="hg-open" @click="closeLightbox">Open the full gallery</RouterLink>
        </div>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.hg-head { display: grid; gap: 1rem; margin-bottom: 1.5rem; }
.hg-head h2 { font-size: 2.4375rem; color: var(--river); }
.hg-head p { color: var(--silt); }
.hg-ctrl { display: flex; align-items: center; gap: .5rem; }
.hg-count { margin-right: auto; color: var(--silt); font-size: .875rem; font-variant-numeric: tabular-nums; }
.hg-stage { position: relative; aspect-ratio: 16 / 10; border-radius: var(--radius-photo); overflow: hidden; background: var(--sunk); cursor: zoom-in; }
.hg-slide { position: absolute; inset: 0; }
.hg-slide img { width: 100%; height: 100%; object-fit: cover; }
.hg-chip { position: absolute; top: .75rem; right: .75rem; }
.hg-cap { margin-top: .75rem; }
.hg-cap h3 { font-size: 1.9375rem; color: var(--river); }
.hg-cap p { color: var(--silt); font-size: .875rem; }
.hg-dots { display: flex; gap: .25rem; margin-top: .75rem; }
.hg-dot { width: 44px; height: 44px; position: relative; }
.hg-dot::after { content: ''; position: absolute; inset: 50% 8px auto; height: 3px; transform: translateY(-50%); border-radius: 2px; background: var(--rule); }
.hg-dot[aria-selected="true"]::after { background: var(--river); }
.hg-links { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1rem; }
.hg-open { color: var(--laterite); text-decoration: underline; min-height: 44px; display: inline-flex; align-items: center; }
@media (min-width: 800px) { .hg-head { grid-template-columns: 1fr auto; align-items: end; } }
</style>
