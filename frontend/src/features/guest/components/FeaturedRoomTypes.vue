<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../../utils/responsiveImage'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import { money, type PublicVisualAssetsResponse, type Room } from '../../../types'
import { roomCatalogFor, roomPhotoFor, type BedKind } from '../../../data/roomCatalog'

const router = useRouter()

const filters: { label: string; value: BedKind | '' }[] = [
  { label: 'All', value: '' },
  { label: 'King', value: 'King' },
  { label: 'Queen', value: 'Queen' },
  { label: 'Single beds', value: 'Twin' },
  { label: 'Family', value: 'Family' },
]
const active = ref<BedKind | ''>('')

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

const rooms = computed(() =>
  active.value ? displayRooms.value.filter(r => r.bedKind === active.value) : displayRooms.value,
)

function choose(room: { name: string; capacity: number }) {
  router.push({ path: '/rooms', query: { type: room.name, occupants: String(Math.min(room.capacity, 2)) } })
}
</script>

<template>
  <section id="rooms" class="py-14 sm:py-20" aria-labelledby="rooms-heading">
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-5 mb-8">
      <div class="max-w-xl space-y-2">
        <h2 id="rooms-heading" class="serif text-3xl sm:text-4xl font-medium text-[var(--brand-text)]">
          Choose your room
        </h2>
        <p class="text-[var(--muted)]">
          Prices are a starting guide per night. You'll see the exact total, with tax, before you pay anything.
        </p>
      </div>
      <div class="filter-chips" role="group" aria-label="Filter rooms by bed type">
        <button
          v-for="f in filters"
          :key="f.value"
          type="button"
          class="chip"
          :aria-pressed="active === f.value"
          @click="active = f.value"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <p v-if="inventory.isPending.value" class="text-[var(--muted)]">Loading rooms…</p>
    <p v-else-if="inventory.error.value" class="text-[var(--muted)]">Rooms couldn't be loaded. Please refresh.</p>
    <ul v-else class="room-rail">
      <li v-for="room in rooms" :key="room.id">
        <article class="guest-room">
          <button type="button" class="guest-room-photo" :aria-label="`View ${room.name}`" @click="choose(room)">
            <img :src="room.photo" :srcset="room.photoSrcset" :sizes="SIZES.card" :alt="room.photoAlt" width="800" height="600" loading="lazy" />
          </button>
          <div class="guest-room-body">
            <div class="flex items-baseline justify-between gap-3">
              <h3 class="serif text-xl font-medium text-[var(--brand-text)]">{{ room.name }}</h3>
              <p class="price whitespace-nowrap">
                <span class="text-xs font-normal text-[var(--muted)]">from</span>
                {{ money(room.rateMinor) }}
              </p>
            </div>
            <ul class="room-facts">
              <li v-if="room.beds">{{ room.beds }}</li>
              <li>Sleeps {{ room.capacity }}</li>
            </ul>
            <p class="text-sm text-[var(--muted)] leading-relaxed">{{ room.summary }}</p>
            <button type="button" class="btn-secondary w-full mt-auto" @click="choose(room)">
              Check {{ room.name }}
            </button>
          </div>
        </article>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.room-rail {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 82%;
  gap: 1rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding-bottom: 0.75rem;
  margin: 0 -1rem;
  padding-inline: 1rem;
  scroll-padding-inline: 1rem;
}
.room-rail > li { scroll-snap-align: start; }
.guest-room {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--line);
  border-radius: 1rem;
  overflow: hidden;
}
.guest-room-photo {
  aspect-ratio: 4 / 3;
  overflow: hidden;
  display: block;
  width: 100%;
  background: var(--surface-muted);
}
.guest-room-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}
.guest-room-photo:hover img { transform: scale(1.03); }
.guest-room-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.125rem 1.125rem 1.25rem;
  flex: 1;
}

@media (min-width: 640px) {
  .room-rail { grid-auto-columns: 46%; }
}
@media (min-width: 1024px) {
  .room-rail {
    grid-auto-flow: row;
    grid-template-columns: repeat(3, 1fr);
    overflow: visible;
    margin: 0;
    padding-inline: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .guest-room-photo img { transition: none; }
}
</style>
