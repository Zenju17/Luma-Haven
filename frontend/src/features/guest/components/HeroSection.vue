<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import type { PublicVisualAssetsResponse } from '../../../types'

const emit = defineEmits<{
  (e: 'focusSearch'): void
}>()

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})
const heroAsset = computed(() => visualAssets.data.value?.hero ?? null)

function scrollToSearch() {
  emit('focusSearch')
  const el = document.getElementById('search')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
    const arrivalInput = el.querySelector('input')
    if (arrivalInput) arrivalInput.focus()
  }
}
</script>

<template>
  <section class="relative pt-6 sm:pt-10 pb-16 overflow-hidden" aria-labelledby="hero-heading">
    <div class="grid lg:grid-cols-12 gap-8 lg:gap-12 items-center">
      <!-- Left Copy Column (7 cols) -->
      <div class="lg:col-span-7 space-y-6 sm:space-y-8">
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--glass-border)] bg-[var(--surface-muted)] text-[var(--brass)] text-xs font-semibold tracking-wider uppercase">
          <span class="w-1.5 h-1.5 rounded-full bg-[var(--brass)] animate-pulse" />
          Boutique Sanctuary · Phnom Penh
        </div>

        <div class="space-y-4">
          <h1 id="hero-heading" class="serif text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tight text-[var(--brand-text)] leading-[1.12]">
            Welcome to Luma-Haven<span class="text-[var(--brass)]">.</span>
          </h1>
          <p class="serif text-lg sm:text-xl text-[var(--brass)] italic font-normal">
            &ldquo;Where comfort meets a brighter stay.&rdquo;
          </p>
          <p class="text-base sm:text-lg text-[var(--muted)] leading-relaxed max-w-xl font-normal">
            A boutique sanctuary of quiet comfort and unhurried hospitality in Phnom Penh. Choose your dates, see verified pricing with physical brass keys waiting at reception, and settle in.
          </p>
        </div>

        <!-- Call to Actions -->
        <div class="flex flex-wrap items-center gap-4 pt-2">
          <button
            type="button"
            class="btn px-7 py-3.5 text-base font-semibold shadow-md hover:shadow-lg transition-all"
            @click="scrollToSearch"
          >
            Check availability
          </button>
          <RouterLink
            to="/rooms"
            class="btn-secondary px-6 py-3.5 text-base font-semibold transition-all inline-flex items-center gap-2"
          >
            Explore our rooms
            <span aria-hidden="true">→</span>
          </RouterLink>
          <RouterLink
            to="/spaces"
            class="text-xs sm:text-sm font-medium text-[var(--brass)] hover:underline inline-flex items-center gap-1.5 w-full sm:w-auto pt-1 sm:pt-0"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Review all 28 hotel spaces &amp; architecture →
          </RouterLink>
        </div>

        <!-- Subtle Highlights -->
        <div class="pt-4 border-t border-[var(--line)] grid grid-cols-3 gap-4 text-left">
          <div>
            <p class="serif text-xl sm:text-2xl font-semibold text-[var(--brand-text)]">14:00</p>
            <p class="text-xs text-[var(--muted)] mt-0.5">Check-in welcome</p>
          </div>
          <div>
            <p class="serif text-xl sm:text-2xl font-semibold text-[var(--brand-text)]">Solid Brass</p>
            <p class="text-xs text-[var(--muted)] mt-0.5">Physical room keys</p>
          </div>
          <div>
            <p class="serif text-xl sm:text-2xl font-semibold text-[var(--brand-text)]">Quiet Hours</p>
            <p class="text-xs text-[var(--muted)] mt-0.5">22:00 – 07:00</p>
          </div>
        </div>
      </div>

      <!-- Right Visual Column (5 cols) -->
      <div class="lg:col-span-5 relative">
        <div class="relative rounded-2xl overflow-hidden border border-[var(--glass-border)] shadow-xl aspect-[4/3] sm:aspect-[5/4] lg:aspect-[4/5] bg-[var(--deep)]">
          <img
            :src="heroAsset ? heroAsset.image_url : '/images/hero-luma-haven.svg'"
            :alt="heroAsset ? heroAsset.alt_text : 'Interior of Luma Haven boutique hotel with courtyard arch and ambient evening lighting'"
            class="w-full h-full object-cover object-center transform transition-transform duration-700 hover:scale-[1.02]"
            width="800"
            height="1000"
            loading="eager"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-[var(--deep)]/60 via-transparent to-transparent pointer-events-none" />

          <!-- Design Concept Badge -->
          <div
            v-if="heroAsset?.source_type === 'CONCEPT'"
            class="absolute top-4 right-4 px-2.5 py-1 rounded-full text-[11px] font-medium tracking-wide bg-black/60 backdrop-blur-md text-[#d9b87f] border border-[#d9b87f]/30"
          >
            Design Concept
          </div>

          <!-- Floating Monogram Badge -->
          <RouterLink
            to="/spaces"
            class="absolute bottom-5 left-5 right-5 p-4 rounded-xl backdrop-blur-md bg-white/10 dark:bg-black/25 border border-white/20 text-white flex items-center justify-between hover:bg-white/15 dark:hover:bg-black/35 transition-colors group"
          >
            <div>
              <p class="text-[11px] font-semibold text-[#d9b87f] uppercase tracking-wider">Location: Hotel Exterior Facade</p>
              <p class="serif text-base font-semibold tracking-wide text-[#fdf4dc]">{{ heroAsset?.title || 'Luma Haven' }}</p>
              <p class="text-xs text-stone-200 group-hover:underline">Explore all spaces &rarr;</p>
            </div>
            <div class="w-10 h-10 rounded-full border border-[#d9b87f]/60 bg-[#0c2b26]/80 flex items-center justify-center text-[#d9b87f] serif font-semibold text-sm">
              LH
            </div>
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>
