<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { VisualAsset } from '../../../types'

const props = defineProps<{
  show: boolean
  roomName: string
  assets: VisualAsset[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'book', roomName: string): void
}>()

const activeIndex = ref(0)

const activeAsset = computed(() => {
  if (!props.assets.length) return null
  return props.assets[activeIndex.value] || props.assets[0]
})

function selectAsset(index: number) {
  activeIndex.value = index
}

function next() {
  if (!props.assets.length) return
  activeIndex.value = (activeIndex.value + 1) % props.assets.length
}

function prev() {
  if (!props.assets.length) return
  activeIndex.value = (activeIndex.value - 1 + props.assets.length) % props.assets.length
}

function handleKeydown(e: KeyboardEvent) {
  if (!props.show) return
  if (e.key === 'Escape') emit('close')
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft') prev()
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

function getSpaceName(filename: string): string {
  const parts = filename.split('/')
  const base = parts[parts.length - 1].replace(/\.(jpg|jpeg|png|webp)$/i, '')
  const names: Record<string, string> = {
    main: 'Main Room Space',
    bedroom: 'Bedroom & Bedding',
    bathroom: 'Ensuite Bathroom',
    living: 'Arched Living Lounge',
    view: 'Balcony & City View',
    work_desk: 'Dedicated Work Desk',
    amenities: 'Wardrobe & Amenities',
    seating: 'Window Seating Lounge',
    minibar: 'Curated In-Room Minibar',
  }
  return names[base] || base.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
</script>

<template>
  <Transition name="fade">
    <div
      v-if="show"
      class="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      :aria-label="`${roomName} Spaces Gallery`"
      @click.self="emit('close')"
    >
      <div class="relative w-full max-w-5xl bg-[var(--surface-raised)] border border-[var(--glass-border)] rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh]">
        <!-- Header -->
        <div class="px-6 py-4 border-b border-[var(--line)] flex items-center justify-between gap-4 bg-[var(--surface-muted)]">
          <div class="space-y-0.5">
            <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">Room Spaces Tour</span>
            <h3 class="serif text-xl sm:text-2xl font-medium text-[var(--brand-text)] flex items-center gap-3">
              {{ roomName }}
              <span class="text-xs font-mono font-normal px-2.5 py-0.5 rounded-full bg-[var(--surface-overlay)] text-[var(--muted)] border border-[var(--glass-border)]">
                {{ activeIndex + 1 }} of {{ assets.length }} Spaces
              </span>
            </h3>
          </div>

          <div class="flex items-center gap-3">
            <button
              type="button"
              class="btn px-4 py-2 text-xs font-semibold rounded-lg"
              @click="emit('book', roomName)"
            >
              Book this room
            </button>
            <button
              type="button"
              class="p-2 rounded-lg text-[var(--muted)] hover:text-[var(--brand-text)] hover:bg-[var(--surface-overlay)] transition-colors"
              aria-label="Close modal"
              @click="emit('close')"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Main Display -->
        <div class="relative grow overflow-hidden bg-black flex items-center justify-center min-h-[320px] sm:min-h-[460px]">
          <template v-if="activeAsset">
            <img
              :src="activeAsset.image_url"
              :alt="activeAsset.alt_text"
              class="max-h-[65vh] w-auto max-w-full object-contain mx-auto transition-opacity duration-300"
            />

            <!-- Prev/Next buttons -->
            <button
              v-if="assets.length > 1"
              type="button"
              class="absolute left-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Previous space photo"
              @click="prev"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              v-if="assets.length > 1"
              type="button"
              class="absolute right-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center border border-white/20 transition-all shadow-lg"
              aria-label="Next space photo"
              @click="next"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>

            <!-- Location Overlay Badge -->
            <div class="absolute bottom-4 left-4 right-4 p-3.5 rounded-xl backdrop-blur-md bg-black/70 border border-white/15 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div class="space-y-0.5">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-[#d9b87f] uppercase tracking-wider">
                    Location: {{ getSpaceName(activeAsset.original_filename) }}
                  </span>
                  <span
                    v-if="activeAsset.source_type === 'CONCEPT'"
                    class="px-2 py-0.5 rounded text-[10px] font-medium bg-[#d9b87f]/20 text-[#d9b87f] border border-[#d9b87f]/40"
                  >
                    Design Concept
                  </span>
                </div>
                <p class="text-sm text-stone-200">
                  {{ activeAsset.caption || activeAsset.title }}
                </p>
              </div>
              <span class="text-[11px] font-mono text-stone-400 shrink-0">
                {{ activeAsset.width }}×{{ activeAsset.height }} px
              </span>
            </div>
          </template>
        </div>

        <!-- Thumbnails Strip -->
        <div v-if="assets.length > 1" class="p-3 bg-[var(--surface-muted)] border-t border-[var(--line)] overflow-x-auto flex items-center gap-2.5">
          <button
            v-for="(asset, idx) in assets"
            :key="asset.id"
            type="button"
            class="relative rounded-lg overflow-hidden shrink-0 w-20 h-14 border-2 transition-all focus:outline-none"
            :class="activeIndex === idx ? 'border-[var(--brass)] scale-105 shadow-md' : 'border-transparent opacity-65 hover:opacity-100'"
            @click="selectAsset(idx)"
          >
            <img :src="asset.image_url" :alt="asset.alt_text" class="w-full h-full object-cover" />
            <span class="absolute bottom-0 inset-x-0 bg-black/75 text-[9px] text-white text-center py-0.5 truncate px-1">
              {{ getSpaceName(asset.original_filename) }}
            </span>
          </button>
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
