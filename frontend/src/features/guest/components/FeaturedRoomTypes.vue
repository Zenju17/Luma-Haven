<script setup lang="ts">
import { responsiveSrcset } from '../../../utils/responsiveImage'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import { money, type PublicVisualAssetsResponse, type Room } from '../../../types'
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

// Cheapest first, like a rate board at reception.
const rooms = computed(() => [...displayRooms.value].sort((a, b) => a.rateMinor - b.rateMinor))
const activeId = ref<string | null>(null)
const active = computed(() => rooms.value.find(r => r.id === activeId.value) ?? rooms.value[0])

function sleeps(room: { capacity: number; beds: string }) {
  const people = room.capacity === 1 ? 'Sleeps 1' : `Sleeps ${room.capacity}`
  return room.beds ? `${people}, ${room.beds}` : people
}

function choose(room: { name: string; capacity: number }) {
  router.push({ path: '/rooms', query: { type: room.name, occupants: String(Math.min(room.capacity, 2)) } })
}
</script>

<template>
  <section id="rooms" class="rc" aria-labelledby="rooms-heading">
    <div class="rc-head">
      <h2 id="rooms-heading">Rooms and rates</h2>
      <p>Starting prices per night. The exact total, with tax, comes before you pay.</p>
    </div>

    <p v-if="inventory.isPending.value" class="rc-msg">Loading rooms…</p>
    <p v-else-if="inventory.error.value" class="rc-msg">Rooms couldn't be loaded. Refresh the page to try again.</p>
    <div v-else class="rc-body">
      <ol class="rc-list">
        <li v-for="room in rooms" :key="room.id">
          <button
            type="button"
            class="rc-row"
            :aria-current="active?.id === room.id ? 'true' : undefined"
            @mouseenter="activeId = room.id"
            @focus="activeId = room.id"
            @click="choose(room)"
          >
            <img :src="room.photo" :srcset="room.photoSrcset" sizes="96px" alt="" width="96" height="72" loading="lazy" class="rc-thumb" />
            <span class="rc-name">{{ room.name }}</span>
            <span class="rc-sleeps">{{ sleeps(room) }}</span>
            <span class="rc-price">{{ money(room.rateMinor) }}</span>
          </button>
        </li>
      </ol>
      <figure v-if="active" class="rc-photo" aria-hidden="true">
        <img :key="active.id" :src="active.photo" :srcset="active.photoSrcset" sizes="40vw" :alt="active.photoAlt" width="800" height="600" />
        <figcaption>{{ active.summary }}</figcaption>
      </figure>
    </div>
    <RouterLink to="/rooms" class="rc-all">Compare rooms for your dates</RouterLink>
  </section>
</template>

<style scoped>
.rc { padding: 4rem 0; border-top: 1px solid var(--rule); }
.rc-head { display: grid; gap: .5rem; margin-bottom: 2rem; }
.rc-head h2 { font-size: clamp(2.4375rem, 5vw, 3.8125rem); color: var(--river); }
.rc-head p, .rc-msg { color: var(--silt); }
.rc-body { display: grid; gap: 2rem; }
.rc-list { display: grid; border-top: 1px solid var(--river); }
.rc-row {
  width: 100%; display: grid; grid-template-columns: 72px minmax(0, 1fr) auto; grid-template-areas: "thumb name price" "thumb sleeps price";
  column-gap: 1rem; align-items: center; padding: .9rem 0; text-align: left; border-bottom: 1px solid var(--rule);
}
.rc-thumb { grid-area: thumb; width: 72px; height: 54px; object-fit: cover; border-radius: 8px; background: var(--sunk); }
.rc-name { grid-area: name; font: 400 1.5625rem/1.1 var(--font-display); color: var(--river); }
.rc-sleeps { grid-area: sleeps; font-size: .875rem; color: var(--silt); }
.rc-price { grid-area: price; font: 500 1.5625rem/1 var(--font-display); color: var(--laterite); font-variant-numeric: lining-nums; }
.rc-row:hover .rc-name, .rc-row[aria-current="true"] .rc-name { text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 5px; }
.rc-photo { display: none; margin: 0; }
.rc-all { display: inline-flex; align-items: center; min-height: 44px; margin-top: 1.25rem; color: var(--river); font-weight: 600; text-decoration: underline; }

/* Desktop: the photo beside the list follows the row you point at or tab to. */
@media (min-width: 1000px) {
  .rc-body { grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: 4rem; align-items: start; }
  .rc-thumb { display: none; }
  .rc-row { grid-template-columns: minmax(0, 1fr) 15rem 6rem; grid-template-areas: "name sleeps price"; padding: 1.1rem 0; }
  .rc-name { font-size: 1.9375rem; }
  .rc-price { text-align: right; }
  .rc-photo { display: block; position: sticky; top: 6rem; }
  .rc-photo img { width: 100%; aspect-ratio: 4 / 5; object-fit: cover; border-radius: var(--radius-photo); background: var(--sunk); }
  .rc-photo figcaption { margin-top: .75rem; color: var(--silt); font-size: .9375rem; max-width: 46ch; }
}
@media (min-width: 1000px) and (prefers-reduced-motion: no-preference) {
  .rc-photo img { animation: rc-in 220ms ease both; }
}
@keyframes rc-in { from { opacity: .4; } to { opacity: 1; } }
</style>
