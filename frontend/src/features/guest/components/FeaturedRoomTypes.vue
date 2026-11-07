<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../../utils/responsiveImage'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import { money, type PublicVisualAssetsResponse, type Room } from '../../../types'
import StayRow from '../../../components/StayRow.vue'
import FactChip from '../../../components/FactChip.vue'
import { roomCatalogFor, roomPhotoFor } from '../../../data/roomCatalog'

const router = useRouter()

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})
const inventory = useQuery({ queryKey: ['rooms'], queryFn: () => api<Room[]>('/rooms') })

// Live inventory is the source of truth; the static catalogue only adds
// photos/copy, and uploaded visual assets override the photo.
const displayRooms = computed(() => {
  const uploaded = Object.values(visualAssets.data.value?.room_types || {}).flat()
  const groups = new Map<string, Room[]>()
  for (const room of inventory.data.value || []) {
    groups.set(room.type, [...(groups.get(room.type) || []), room])
  }
  return [...groups].map(([type, group]) => {
    const first = group[0]!
    const meta = roomCatalogFor(type)
    const asset = uploaded.find(a => a.room_type_name?.toLowerCase() === type.toLowerCase())
    const fallback = roomPhotoFor(type)
    return {
      id: type,
      name: type,
      capacity: first.capacity,
      beds: meta?.beds ?? '',
      bedKind: meta?.bedKind,
      summary: first.description || meta?.summary || '',
      rateMinor: Math.min(...group.map(r => r.rate_minor ?? 0)),
      photo: asset?.image_url ?? fallback.src,
      photoSrcset: responsiveSrcset(asset?.image_url ?? fallback.src, asset?.width),
      photoAlt: asset?.alt_text || fallback.alt,
    }
  })
})

const rooms = computed(() => displayRooms.value.slice(0, 3))

function choose(room: { name: string; capacity: number }) {
  router.push({ path: '/rooms', query: { type: room.name, occupants: String(Math.min(room.capacity, 2)) } })
}
</script>

<template>
  <section id="rooms" class="py-14 sm:py-20" aria-labelledby="rooms-heading">
    <div class="rt-head">
      <h2 id="rooms-heading">Choose your room</h2>
      <p>Prices are a starting guide per night. You'll see the exact total, with tax, before you pay anything.</p>
    </div>

    <p v-if="inventory.isPending.value" class="text-[var(--muted)]">Loading rooms…</p>
    <p v-else-if="inventory.error.value" class="text-[var(--muted)]">Rooms couldn't be loaded. Please refresh.</p>
    <div v-else class="rt-rows">
      <StayRow v-for="room in rooms" :key="room.id" :title="room.name">
        <template #photo>
          <img :src="room.photo" :srcset="room.photoSrcset" :sizes="SIZES.card" :alt="room.photoAlt" width="800" height="600" loading="lazy" class="rt-img" />
        </template>
        <template #facts>
          <FactChip v-if="room.beds">{{ room.beds }}</FactChip>
          <FactChip>Sleeps {{ room.capacity }}</FactChip>
        </template>
        <p>{{ room.summary }}</p>
        <template #price>
          <div>
            <span class="rt-from">From</span>
            <p class="rt-price">{{ money(room.rateMinor) }} <span>/ night</span></p>
          </div>
        </template>
        <template #action>
          <button type="button" class="btn-secondary rt-btn" @click="choose(room)">Check {{ room.name }}</button>
        </template>
      </StayRow>
    </div>
    <RouterLink to="/rooms" class="rt-all">See all rooms</RouterLink>
  </section>
</template>

<style scoped>
.rt-head { max-width: 60ch; margin-bottom: 1.5rem; display: grid; gap: .5rem; }
.rt-head h2 { font-size: 2.4375rem; color: var(--river); }
.rt-head p { color: var(--silt); }
.rt-rows { display: grid; gap: 1rem; }
.rt-img { width: 100%; height: 100%; object-fit: cover; }
.rt-from { color: var(--silt); font-size: .8125rem; }
.rt-price { color: var(--laterite); font-size: 1.5625rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.rt-price span { color: var(--silt); font-size: .8125rem; font-weight: 400; }
.rt-btn { width: 100%; min-height: 44px; border-radius: var(--radius-pill) !important; }
.rt-all { display: inline-flex; align-items: center; min-height: 44px; margin-top: 1rem; color: var(--river); font-weight: 600; text-decoration: underline; }
</style>
