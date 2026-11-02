<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../utils/responsiveImage'
import { ref, computed } from 'vue'
import { PLACEHOLDERS } from '../data/hotelImages'

const props = withDefaults(
  defineProps<{
    src?: string
    alt?: string
    caption?: string
    aspectRatio?: string // e.g. '16/10', '4/3', '1/1', '16/9'
    placeholderLabel?: string
    placeholderType?: 'room' | 'hotel' | 'facility'
    loading?: 'lazy' | 'eager'
    objectFit?: 'cover' | 'contain' | 'fill'
    isDemo?: boolean
    facilityClaim?: string
    showBadge?: boolean
    width?: number
    sizes?: string
  }>(),
  {
    src: '',
    alt: 'Luma Haven Hotel image',
    caption: '',
    aspectRatio: '16/10',
    placeholderLabel: 'Photography Coming Soon',
    placeholderType: 'hotel',
    loading: 'lazy',
    objectFit: 'cover',
    isDemo: false,
    facilityClaim: '',
    showBadge: true,
    width: 0,
    sizes: SIZES.card,
  }
)

const hasError = ref(false)
const isLoaded = ref(false)

const effectiveSrc = computed(() => {
  if (hasError.value || !props.src) {
    return PLACEHOLDERS[props.placeholderType] || PLACEHOLDERS.hotel
  }
  return props.src
})

const effectiveSrcset = computed(() => (hasError.value ? undefined : responsiveSrcset(props.src, props.width)))

const aspectStyle = computed(() => ({
  aspectRatio: props.aspectRatio.includes('/') ? props.aspectRatio : '16/10',
}))

function onError() {
  hasError.value = true
}

function onLoad() {
  isLoaded.value = true
}
</script>

<template>
  <div class="hotel-image-wrapper relative overflow-hidden bg-[var(--deep)] rounded-xl" :style="aspectStyle">
    <!-- Image -->
    <img
      :src="effectiveSrc"
      :srcset="effectiveSrcset"
      :sizes="effectiveSrcset ? sizes : undefined"
      :alt="alt"
      :loading="loading"
      :class="[
        'w-full h-full transition-all duration-500',
        objectFit === 'contain' ? 'object-contain' : 'object-cover',
        !isLoaded && !hasError ? 'opacity-0' : 'opacity-100',
      ]"
      @error="onError"
      @load="onLoad"
    />

    <!-- Subtle gradient overlay -->
    <div class="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />

    <!-- Loading Skeleton Shimmer -->
    <div
      v-if="!isLoaded && !hasError"
      class="absolute inset-0 skeleton bg-[var(--surface-muted)] animate-pulse flex items-center justify-center text-[var(--muted)] text-xs"
    >
      <span class="font-mono text-[11px]">Loading...</span>
    </div>

    <!-- Error / Fallback Label if placeholder is shown -->
    <div
      v-if="hasError || !src"
      class="absolute bottom-3 inset-x-3 text-center pointer-events-none"
    >
      <span class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-black/75 backdrop-blur-md text-[#d9b87f] border border-[#d9b87f]/30 inline-block shadow-sm">
        {{ placeholderLabel }}
      </span>
    </div>

    <!-- Demo / Design Concept Badge -->
    <div
      v-else-if="showBadge && isDemo"
      class="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-medium tracking-wide bg-black/60 backdrop-blur-md text-[#d9b87f] border border-[#d9b87f]/30 shadow-sm pointer-events-none"
    >
      {{ facilityClaim ? `Concept · ${facilityClaim}` : 'Design Concept' }}
    </div>

    <!-- Optional Caption Slot or Overlay -->
    <div v-if="caption" class="sr-only">
      {{ caption }}
    </div>
  </div>
</template>
