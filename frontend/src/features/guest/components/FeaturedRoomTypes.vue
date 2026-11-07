<script setup lang="ts">
import { responsiveSrcset } from '../../../utils/responsiveImage'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import { money, type PublicVisualAssetsResponse, type Room } from '../../../types'
import { roomCatalogFor, roomPhotoFor, type BedKind } from '../../../data/roomCatalog'

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
      count: group.length,
      summary: first.description || meta?.summary || '',
      highlights: (first.amenities?.length ? first.amenities : meta?.highlights ?? []).slice(0, 3),
      rateMinor: Math.min(...group.map(r => r.rate_minor ?? 0)),
      photo: asset?.image_url ?? fallback.src,
      photoSrcset: responsiveSrcset(asset?.image_url ?? fallback.src, asset?.width),
      photoAlt: asset?.alt_text || fallback.alt,
    }
  }).sort((a, b) => a.rateMinor - b.rateMinor)
})

const tabs: { key: BedKind | 'All'; label: string }[] = [
  { key: 'All', label: 'All rooms' },
  { key: 'Queen', label: 'Queen' },
  { key: 'King', label: 'King' },
  { key: 'Twin', label: 'Twin' },
  { key: 'Family', label: 'Family' },
]
const tab = ref<BedKind | 'All'>('All')
const rooms = computed(() => {
  const list = tab.value === 'All' ? displayRooms.value : displayRooms.value.filter(r => r.bedKind === tab.value)
  return list.slice(0, 4)
})
const hiddenCount = computed(() => {
  const all = tab.value === 'All' ? displayRooms.value.length : displayRooms.value.filter(r => r.bedKind === tab.value).length
  return Math.max(0, all - rooms.value.length)
})

function choose(room: { name: string; capacity: number }) {
  router.push({ path: '/rooms', query: { type: room.name, occupants: String(Math.min(room.capacity, 2)) } })
}
</script>

<template>
  <section id="rooms" class="acc" aria-labelledby="rooms-heading">
    <h2 id="rooms-heading" class="acc-title">Rooms and rates</h2>
    <p class="acc-sub">Starting prices per night, cheapest first. The exact total, with tax, comes before you pay.</p>

    <div class="acc-tabs" role="tablist" aria-label="Filter rooms by bed type">
      <button
        v-for="t in tabs"
        :key="t.key"
        type="button"
        role="tab"
        :aria-selected="tab === t.key"
        class="acc-tab"
        @click="tab = t.key"
      >{{ t.label }}</button>
    </div>

    <p v-if="inventory.isPending.value" class="acc-msg">Loading rooms…</p>
    <p v-else-if="inventory.error.value" class="acc-msg">Rooms couldn't be loaded. Refresh the page to try again.</p>
    <p v-else-if="!rooms.length" class="acc-msg">No rooms with this bed type right now. Try another tab.</p>
    <div v-else class="acc-list">
      <article v-for="room in rooms" :key="room.id" class="acc-row">
        <img :src="room.photo" :srcset="room.photoSrcset" sizes="(min-width: 1000px) 22vw, 100vw" :alt="room.photoAlt" width="800" height="600" loading="lazy" class="acc-img" />
        <div class="acc-about">
          <h3>{{ room.name }}</h3>
          <p>{{ room.summary }}</p>
        </div>
        <div class="acc-box">
          <p class="acc-price">{{ money(room.rateMinor) }}<span> / night</span></p>
          <p class="acc-tax">Before tax</p>
          <dl class="acc-facts">
            <div v-if="room.beds"><dt>Beds</dt><dd>{{ room.beds }}</dd></div>
            <div><dt>Sleeps</dt><dd>{{ room.capacity }}</dd></div>
            <div><dt>Rooms of this type</dt><dd>{{ room.count }}</dd></div>
          </dl>
        </div>
        <div class="acc-box acc-box--act">
          <ul class="acc-hl">
            <li v-for="h in room.highlights" :key="h">{{ h }}</li>
          </ul>
          <button type="button" class="acc-book" @click="choose(room)">Book {{ room.name }}</button>
        </div>
      </article>
    </div>
    <RouterLink v-if="hiddenCount" to="/rooms" class="acc-more">See {{ hiddenCount }} more {{ hiddenCount === 1 ? 'room type' : 'room types' }}</RouterLink>
  </section>
</template>

<style scoped>
.acc { padding: 3rem 0 4rem; }
.acc-title { text-align: center; font-size: clamp(2.6rem, 7vw, 5rem); color: var(--ink); }
.acc-sub { margin: .75rem auto 0; text-align: center; color: var(--silt); }
.acc-tabs { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(max-content, 1fr); gap: .25rem; margin: 2rem 0 1rem; padding: .35rem; background: var(--paper); border-radius: var(--radius-pill); overflow-x: auto; }
.acc-tab { min-height: 44px; padding: 0 1rem; border-radius: var(--radius-pill); font-size: .875rem; font-weight: 600; color: var(--silt); }
.acc-tab[aria-selected="true"] { background: var(--palm-leaf); color: var(--ink); }
.acc-msg { text-align: center; color: var(--silt); padding: 2rem 0; }
.acc-list { display: grid; gap: 1rem; }
.acc-row { display: grid; gap: 1rem; padding: 1rem; background: var(--paper); border-radius: var(--radius-panel); }
.acc-img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: var(--radius-photo); background: var(--sunk); }
.acc-about { display: grid; align-content: start; gap: .5rem; padding: .25rem; }
.acc-about h3 { font-size: 1.5rem; color: var(--ink); }
.acc-about p { font-size: .9375rem; color: var(--silt); }
.acc-box { display: grid; align-content: start; gap: .25rem; padding: 1.1rem; border-radius: var(--radius-photo); background: var(--palm-leaf); }
.acc-price { font-size: 1.75rem; font-weight: 700; letter-spacing: -.02em; color: var(--ink); font-variant-numeric: tabular-nums; }
.acc-price span { font-size: .9375rem; font-weight: 500; color: var(--silt); }
.acc-tax { font-size: .75rem; color: var(--silt); }
.acc-facts { margin-top: .9rem; display: grid; gap: .45rem; font-size: .8125rem; }
.acc-facts div { display: flex; justify-content: space-between; gap: 1rem; }
.acc-facts dt { color: var(--silt); }
.acc-facts dd { font-weight: 600; color: var(--ink); text-align: right; }
.acc-box--act { align-content: space-between; gap: 1rem; }
.acc-hl { display: grid; gap: .5rem; font-size: .875rem; color: var(--ink); }
.acc-hl li { display: flex; gap: .5rem; align-items: baseline; }
.acc-hl li::before { content: ''; flex: none; width: 6px; height: 6px; border-radius: 50%; background: var(--river); transform: translateY(-2px); }
.acc-book { min-height: 48px; width: 100%; border-radius: var(--radius-pill); background: var(--river); color: var(--on-river); font-weight: 600; font-size: .9375rem; }
.acc-book:hover { background: var(--river-hover); }
.acc-more { display: flex; justify-content: center; align-items: center; min-height: 44px; margin-top: 1.25rem; color: var(--river); font-weight: 600; text-decoration: underline; text-underline-offset: 4px; }

@media (min-width: 700px) {
  .acc-row { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
}
@media (min-width: 1100px) {
  .acc-row { grid-template-columns: 15rem minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr); align-items: stretch; }
  .acc-img { height: 100%; aspect-ratio: auto; min-height: 12rem; }
}
</style>
