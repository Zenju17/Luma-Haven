<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../../utils/responsiveImage'
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
  <Transition name="lb-fade">
    <div v-if="show" class="lb-scrim" role="dialog" aria-modal="true" :aria-label="`${roomName} Spaces Gallery`" @click.self="emit('close')">
      <div class="lb-panel">
        <div class="lb-head">
          <div>
            <h3 class="lb-title">{{ roomName }}</h3>
            <p class="lb-sub">{{ activeIndex + 1 }} of {{ assets.length }} spaces</p>
          </div>
          <div class="lb-actions">
            <button type="button" class="btn" @click="emit('book', roomName)">Book this room</button>
            <button type="button" class="lb-close" aria-label="Close modal" @click="emit('close')"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
          </div>
        </div>

        <div class="lb-stage">
          <template v-if="activeAsset">
            <img :src="activeAsset.image_url" :srcset="responsiveSrcset(activeAsset.image_url, activeAsset.width)" :sizes="SIZES.lightbox" :alt="activeAsset.alt_text" />
            <div class="lb-chips">
              <span class="lb-chip">{{ getSpaceName(activeAsset.original_filename) }}</span>
              <span v-if="activeAsset.source_type === 'CONCEPT'" class="lb-chip">Design concept</span>
            </div>
            <button v-if="assets.length > 1" type="button" class="lb-nav lb-nav--prev" aria-label="Previous space photo" @click="prev"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7" /></svg></button>
            <button v-if="assets.length > 1" type="button" class="lb-nav lb-nav--next" aria-label="Next space photo" @click="next"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" /></svg></button>
          </template>
        </div>
        <p v-if="activeAsset" class="lb-caption">{{ activeAsset.caption || activeAsset.title }}</p>

        <div v-if="assets.length > 1" class="lb-thumbs">
          <button v-for="(asset, idx) in assets" :key="asset.id" type="button" class="lb-thumb" :aria-current="activeIndex === idx" :aria-label="getSpaceName(asset.original_filename)" @click="selectAsset(idx)">
            <img :src="asset.image_url" :srcset="responsiveSrcset(asset.image_url, asset.width)" :sizes="SIZES.thumb" :alt="asset.alt_text" />
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>
