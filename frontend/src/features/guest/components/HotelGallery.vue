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
  <section id="gallery" class="py-16 sm:py-24 border-t border-[var(--line)]" aria-labelledby="gallery-heading">
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8 sm:mb-12">
      <div class="space-y-2">
        <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">
          Visual Atmosphere
        </span>
        <h2 id="gallery-heading" class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
          Moments around the hotel<span class="text-[var(--brass)]">.</span>
        </h2>
        <p class="text-sm sm:text-base text-[var(--muted)]">
          Explore the spaces where morning calm meets unhurried Cambodian hospitality.
        </p>
      </div>

      <!-- Controls & Slide Counter -->
      <div class="flex items-center gap-4">
        <span class="text-xs sm:text-sm font-medium text-[var(--muted)] font-mono">
          Photo {{ currentIndex + 1 }} of {{ displayPhotos.length }}
        </span>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="w-10 h-10 rounded-full border border-[var(--glass-border)] bg-[var(--surface-raised)] text-[var(--brand-text)] hover:border-[var(--brass)] hover:bg-[var(--surface-muted)] flex items-center justify-center transition-colors shadow-xs"
            aria-label="Previous photo"
            @click="prev"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            type="button"
            class="w-10 h-10 rounded-full border border-[var(--glass-border)] bg-[var(--surface-raised)] text-[var(--brand-text)] hover:border-[var(--brass)] hover:bg-[var(--surface-muted)] flex items-center justify-center transition-colors shadow-xs"
            aria-label="Next photo"
            @click="next"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Carousel Main Stage -->
    <div
      class="relative rounded-2xl overflow-hidden border border-[var(--glass-border)] bg-[var(--deep)] shadow-2xl focus:outline-none focus:ring-2 focus:ring-[var(--brass)] cursor-pointer group"
      tabindex="0"
      role="region"
      aria-label="Hotel gallery carousel"
      @touchstart="handleTouchStart"
      @touchend="handleTouchEnd"
      @click="openLightbox"
    >
      <!-- Slides Container -->
      <div class="relative w-full aspect-[16/10] sm:aspect-[16/9] overflow-hidden">
        <TransitionGroup name="fade">
          <div
            v-for="(photo, index) in displayPhotos"
            v-show="index === currentIndex"
            :key="photo.id"
            class="absolute inset-0 w-full h-full"
          >
            <img
              :src="photo.src"
              :srcset="responsiveSrcset(photo.src, photo.width)"
              :sizes="SIZES.card"
              :alt="photo.alt"
              class="w-full h-full object-cover object-center group-hover:scale-102 transition-transform duration-700"
              loading="lazy"
              width="1600"
              height="1128"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-[var(--deep)]/90 via-[var(--deep)]/25 to-transparent pointer-events-none" />

            <!-- Corner Disclaimer Badge -->
            <div
              v-if="photo.facilityClaim"
              class="absolute top-4 right-4 px-3 py-1 rounded-full text-[11px] font-medium tracking-wide bg-black/75 backdrop-blur-md text-amber-200 border border-amber-400/40 shadow-sm pointer-events-none"
            >
              Design Concept · {{ photo.facilityClaim }}
            </div>
            <div
              v-else-if="photo.isConcept"
              class="absolute top-4 right-4 px-3 py-1 rounded-full text-[11px] font-medium tracking-wide bg-black/70 backdrop-blur-md text-[#d9b87f] border border-[#d9b87f]/30 shadow-sm pointer-events-none"
            >
              Design Concept
            </div>

            <!-- Enlarge Icon Hint -->
            <div class="absolute top-4 left-4 px-3 py-1.5 rounded-xl bg-black/60 backdrop-blur-md border border-white/20 text-white text-xs font-medium flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <svg class="w-4 h-4 text-[var(--brass)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              </svg>
              <span>Click to enlarge photo</span>
            </div>

            <!-- Caption Overlay at Bottom -->
            <div class="absolute bottom-0 inset-x-0 p-6 sm:p-8 backdrop-blur-sm bg-black/40 border-t border-white/10 text-white flex flex-col sm:flex-row sm:items-end justify-between gap-4 pointer-events-none">
              <div class="space-y-1.5 max-w-2xl">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold uppercase tracking-wider text-[#d9b87f]">
                    {{ photo.location }}
                  </span>
                  <span
                    v-if="photo.facilityClaim"
                    class="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded bg-amber-900/60 text-amber-200 border border-amber-600/30"
                  >
                    Unverified
                  </span>
                </div>
                <h3 class="serif text-xl sm:text-2xl lg:text-3xl font-medium text-white">
                  {{ photo.caption }}
                </h3>
                <p class="text-xs sm:text-sm text-stone-300 leading-relaxed font-normal">
                  {{ photo.title }}
                </p>
              </div>

              <!-- Quick Jump Indicator on slide -->
              <span class="text-xs text-stone-300 font-mono hidden sm:inline-block">
                Press ← or → to navigate
              </span>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>

    <!-- Dot Indicators -->
    <div class="flex items-center justify-center gap-2 mt-6" role="tablist" aria-label="Gallery slides">
      <button
        v-for="(photo, index) in displayPhotos"
        :key="photo.id"
        type="button"
        role="tab"
        :aria-selected="index === currentIndex"
        :aria-label="`Slide ${index + 1}: ${photo.title}`"
        :class="[
          'h-2.5 rounded-full transition-all duration-300',
          index === currentIndex ? 'w-8 bg-[var(--brass)]' : 'w-2.5 bg-[var(--line)] hover:bg-[var(--muted)]',
        ]"
        @click.stop="goTo(index)"
      />
    </div>

    <!-- Gallery Exploration Actions -->
    <div class="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
      <RouterLink
        to="/gallery"
        class="btn px-6 py-3 rounded-xl font-semibold text-xs sm:text-sm inline-flex items-center gap-2 shadow-sm"
      >
        <svg class="w-4 h-4 text-[var(--brass)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        View Full Photo Gallery (29 Photos) &rarr;
      </RouterLink>

      <RouterLink
        to="/spaces"
        class="btn-secondary px-6 py-3 rounded-xl font-semibold text-xs sm:text-sm inline-flex items-center gap-2 hover:border-[var(--brass)] transition-all shadow-sm"
      >
        <svg class="w-4 h-4 text-[var(--brass)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
        Review Hotel Spaces &amp; Locations &rarr;
      </RouterLink>
    </div>

    <!-- Carousel Full-Screen Lightbox Modal -->
    <Transition name="fade">
      <div
        v-if="showLightbox && currentSlide"
        class="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-3 sm:p-6"
        role="dialog"
        aria-modal="true"
        :aria-label="currentSlide.title"
        @click.self="closeLightbox"
      >
        <div class="relative w-full max-w-5xl bg-[var(--surface-raised)] border border-[var(--glass-border)] rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[94vh]">
          <!-- Modal Header -->
          <div class="px-5 py-3.5 border-b border-[var(--line)] bg-[var(--surface-muted)] flex items-center justify-between gap-4">
            <div class="space-y-0.5">
              <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
                {{ currentSlide.location }}
              </span>
              <h3 class="serif text-xl sm:text-2xl font-medium text-[var(--brand-text)]">
                {{ currentSlide.caption }}
              </h3>
            </div>

            <div class="flex items-center gap-3">
              <span class="text-xs font-mono px-2.5 py-1 rounded-full bg-[var(--surface-overlay)] text-[var(--muted)] border border-[var(--glass-border)]">
                {{ currentIndex + 1 }} of {{ displayPhotos.length }}
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

          <!-- Modal Viewport -->
          <div class="relative grow overflow-hidden bg-black flex items-center justify-center min-h-[360px] sm:min-h-[500px]">
            <img
              :src="currentSlide.src"
              :srcset="responsiveSrcset(currentSlide.src, currentSlide.width)"
              :sizes="SIZES.lightbox"
              :alt="currentSlide.alt"
              class="max-h-[68vh] w-auto max-w-full object-contain mx-auto"
            />

            <!-- Left / Right Controls -->
            <button
              type="button"
              class="absolute left-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Previous photo"
              @click.stop="prev"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              type="button"
              class="absolute right-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Next photo"
              @click.stop="next"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          <!-- Modal Footer Details -->
          <div class="p-4 bg-[var(--surface-muted)] border-t border-[var(--line)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div class="flex items-center gap-3">
              <span class="font-semibold text-[var(--brand-text)]">{{ currentSlide.title }}</span>
              <span v-if="currentSlide.isConcept" class="px-2 py-0.5 rounded text-[10px] font-medium bg-[#d9b87f]/20 text-[#d9b87f] border border-[#d9b87f]/40">
                {{ currentSlide.facilityClaim || 'Design Concept' }}
              </span>
            </div>
            <div class="flex items-center gap-4 text-[var(--muted)] font-mono text-[11px]">
              <span>Press ESC to exit</span>
              <RouterLink to="/gallery" class="text-[var(--brass)] font-sans font-semibold hover:underline" @click="closeLightbox">
                Open full gallery &rarr;
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease-in-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
