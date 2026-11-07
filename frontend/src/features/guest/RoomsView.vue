<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../utils/responsiveImage'
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import FilterPill from '../../components/FilterPill.vue'
import SegmentedNumber from '../../components/SegmentedNumber.vue'
import RangeSlider from '../../components/RangeSlider.vue'
import FactChip from '../../components/FactChip.vue'
import StayRow from '../../components/StayRow.vue'
import DetailPanel from '../../components/DetailPanel.vue'
import CardStrip from '../../components/CardStrip.vue'
import AvailabilitySearch from './components/AvailabilitySearch.vue'
import RoomSpacesModal from './components/RoomSpacesModal.vue'
import ConsentCheck from '../legal/ConsentCheck.vue'
import { api } from '../../services/api'
import { hotelToday, followingDay } from '../../services/hotelDates'
import { roomCatalogFor, roomPhotoFor, type BedKind } from '../../data/roomCatalog'
import { money, type PublicVisualAssetsResponse, type Quote, type Room } from '../../types'

const route = useRoute()
const router = useRouter()

const arrival = ref((route.query.arrival as string) || '')
const departure = ref((route.query.departure as string) || '')
const occupants = ref(Number(route.query.occupants) || 2)
const typeFilter = ref((route.query.type as string) || '')

const selected = ref<Room | null>(null)
const quote = ref<Quote | null>(null)
const name = ref('')
const email = ref('')
const accepted = ref(false)
const consentIds = ref<number[]>([])
const error = ref('')
const saving = ref(false)

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})

function getRoomTypeAsset(typeName: string) {
  const rtMap = visualAssets.data.value?.room_types || {}
  const allRtAssets = Object.values(rtMap).flat()
  return allRtAssets.find(a => a.room_type_name?.toLowerCase() === typeName.toLowerCase())
}

// Room Spaces Modal
const modalRoomName = ref<string | null>(null)

function getRoomSpaces(typeName: string) {
  const items = visualAssets.data.value?.items || []
  const n = typeName.toLowerCase()
  if (n.includes('suite')) return items.filter(a => a.original_filename?.startsWith('rooms/suite/'))
  if (n.includes('deluxe')) return items.filter(a => a.original_filename?.startsWith('rooms/deluxe/'))
  if (n.includes('premier')) return items.filter(a => a.original_filename?.startsWith('rooms/premier/'))
  return []
}

const modalAssets = computed(() => {
  if (!modalRoomName.value) return []
  return getRoomSpaces(modalRoomName.value)
})

function openSpacesModal(typeName: string) {
  modalRoomName.value = typeName
}

function closeSpacesModal() {
  modalRoomName.value = null
}

// All rooms query (baseline fallback)
const rooms = useQuery({
  queryKey: ['rooms'],
  queryFn: () => api<Room[]>('/rooms'),
})


// Date-specific availability query
const hasDates = computed(() => Boolean(arrival.value && departure.value && arrival.value < departure.value))

const availability = useQuery({
  queryKey: computed(() => ['availability', arrival.value, departure.value, occupants.value]),
  queryFn: () =>
    api<Room[]>(
      `/availability?arrival=${encodeURIComponent(arrival.value)}&departure=${encodeURIComponent(
        departure.value
      )}&occupants=${occupants.value}`
    ),
  enabled: hasDates,
})

const searchError = computed(() => hasDates.value ? availability.error.value : rooms.error.value)
const searching = computed(() => hasDates.value ? availability.isPending.value : rooms.isPending.value)

function setTypeFilter(type: string) {
  typeFilter.value = type
  void router.replace({ query: { ...route.query, type: type || undefined } })
}

function retrySearch() {
  void (hasDates.value ? availability.refetch() : rooms.refetch())
}

watch([arrival, departure, occupants], () => {
  previewId.value = null
  selected.value = null
  quote.value = null
})

const bedFilter = ref<BedKind | ''>('')
const bedChips: { label: string; value: BedKind | '' }[] = [
  { label: 'All rooms', value: '' },
  { label: 'King bed', value: 'King' },
  { label: 'Queen bed', value: 'Queen' },
  { label: 'Single beds', value: 'Twin' },
  { label: 'Family', value: 'Family' },
]

function cardPhoto(typeName: string) {
  const uploaded = getRoomTypeAsset(typeName)
  const photo = uploaded ? { src: uploaded.image_url, alt: uploaded.alt_text } : roomPhotoFor(typeName)
  return { ...photo, srcset: responsiveSrcset(photo.src, uploaded?.width) }
}

// Rail filters (client-side only; dates and guests still go through the availability query)
const bedCount = ref<number | null>(null)
const budget = ref<number | null>(null) // minor units; null = no limit
const amenityFilter = ref<string[]>([])
const sort = ref<'recommended' | 'low' | 'high'>('recommended')
const filtersOpen = ref(false)
const previewId = ref<number | null>(null)

const sourceRooms = computed(() => (hasDates.value ? availability.data.value : rooms.data.value) ?? [])

function bedsIn(typeName: string) {
  const text = roomCatalogFor(typeName)?.beds ?? ''
  const nums = [...text.matchAll(/(\d+)\s/g)].map((m) => Number(m[1]))
  return nums.reduce((a, b) => a + b, 0) || null
}

const rateBounds = computed(() => {
  const rates = sourceRooms.value.map((r) => r.rate_minor).filter((n): n is number => typeof n === 'number')
  if (!rates.length) return null
  return { min: Math.floor(Math.min(...rates) / 500) * 500, max: Math.ceil(Math.max(...rates) / 500) * 500 }
})
const budgetValue = computed(() => budget.value ?? rateBounds.value?.max ?? 0)
const budgetActive = computed(() => budget.value !== null && rateBounds.value !== null && budget.value < rateBounds.value.max)

const amenityOptions = computed(() => {
  const counts = new Map<string, number>()
  for (const r of sourceRooms.value) for (const a of r.amenities ?? []) counts.set(a, (counts.get(a) ?? 0) + 1)
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([a]) => a)
})

const displayRooms = computed(() => {
  const list = sourceRooms.value.filter((r) => {
    if (typeFilter.value && !r.type.toLowerCase().includes(typeFilter.value.toLowerCase())) return false
    if (bedFilter.value && roomCatalogFor(r.type)?.bedKind !== bedFilter.value) return false
    if (bedCount.value !== null) {
      const n = bedsIn(r.type)
      if (n === null || (bedCount.value >= 3 ? n < 3 : n !== bedCount.value)) return false
    }
    if (budgetActive.value && (r.rate_minor ?? 0) > budget.value!) return false
    if (amenityFilter.value.some((a) => !(r.amenities ?? []).includes(a))) return false
    return true
  })
  if (sort.value === 'low') return [...list].sort((a, b) => (a.rate_minor ?? 0) - (b.rate_minor ?? 0))
  if (sort.value === 'high') return [...list].sort((a, b) => (b.rate_minor ?? 0) - (a.rate_minor ?? 0))
  return list
})

const activeFilterCount = computed(() =>
  Number(Boolean(typeFilter.value)) + Number(Boolean(bedFilter.value)) + Number(bedCount.value !== null) +
  Number(budgetActive.value) + amenityFilter.value.length)

function clearFilters() {
  setTypeFilter('')
  bedFilter.value = ''
  bedCount.value = null
  budget.value = null
  amenityFilter.value = []
}
function toggleAmenity(a: string) {
  amenityFilter.value = amenityFilter.value.includes(a) ? amenityFilter.value.filter((x) => x !== a) : [...amenityFilter.value, a]
}

const previewRoom = computed(() => displayRooms.value.find((r) => r.id === previewId.value) ?? null)
const stripItems = computed(() => displayRooms.value.map((r) => ({
  id: r.id,
  title: `Room ${r.number}`,
  price: r.rate_minor !== undefined ? money(r.rate_minor) : undefined,
})))
function roomById(id: string | number) { return displayRooms.value.find((r) => r.id === id) }
function leftOfType(typeName: string) {
  return sourceRooms.value.filter((r) => r.type === typeName).length
}

// Sync query params when route changes
watch(
  () => route.query,
  (q) => {
    arrival.value = (q.arrival as string) || ''
    departure.value = (q.departure as string) || ''
    occupants.value = Number(q.occupants) || 2
    typeFilter.value = (q.type as string) || ''
  }
)

function onSearch(params: { arrival: string; departure: string; occupants: number }) {
  arrival.value = params.arrival
  departure.value = params.departure
  occupants.value = params.occupants
  error.value = ''
  router.replace({
    query: {
      ...route.query,
      arrival: params.arrival,
      departure: params.departure,
      occupants: String(params.occupants),
    },
  })
}

async function selectRoom(room: Room) {
  error.value = ''
  if (!arrival.value || !departure.value) {
    error.value = 'Please select stay dates first to generate an accurate quote.'
    return
  }
  try {
    quote.value = await api<Quote>('/quotes', {
      room_id: room.id,
      arrival: arrival.value,
      departure: departure.value,
      occupants: occupants.value,
    })
    selected.value = room
  } catch (caught) {
    error.value = String(caught)
  }
}

async function reserve() {
  if (!quote.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const result = await api<{ id: number }>('/reservations', {
      quote_id: quote.value.id,
      name: name.value,
      email: email.value,
      consent_document_ids: consentIds.value,
    })
    await router.push(`/booking/${result.id}`)
  } catch (caught) {
    error.value = String(caught)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <SiteLayout>
    <div class="rooms-page py-6 sm:py-10">
      <div class="rooms-head">
        <h1 class="rooms-title">Find your room</h1>
        <p>Pick your dates and number of guests. We only show rooms that are free for your whole stay.</p>
      </div>

      <Notice v-if="!selected" :message="error" />

      <div class="rooms-layout" :class="{ 'rooms-layout--panel': previewRoom }">
        <!-- Filter rail -->
        <button type="button" class="filters-toggle" :aria-expanded="filtersOpen" @click="filtersOpen = true">
          Filters{{ activeFilterCount ? ` (${activeFilterCount})` : '' }}
        </button>
        <div v-if="filtersOpen" class="rail-scrim" @click="filtersOpen = false" />
        <aside class="rail" :class="{ 'rail--open': filtersOpen }" aria-label="Room filters">
          <div class="rail__sheet-head">
            <strong>Filters</strong>
            <button type="button" class="rail__done" @click="filtersOpen = false">Show {{ displayRooms.length }} rooms</button>
          </div>

          <AvailabilitySearch
            stacked
            :initial-arrival="arrival"
            :initial-departure="departure"
            :initial-occupants="occupants"
            :navigate-on-submit="false"
            @search="onSearch"
          />

          <div class="rail__group">
            <span class="rail__label">Beds</span>
            <SegmentedNumber v-model="bedCount" label="Number of beds" :options="[1, 2, 3]" :plus-from="3" />
          </div>
          <div v-if="rateBounds" class="rail__group">
            <RangeSlider
              :model-value="budgetValue"
              :min="rateBounds.min"
              :max="rateBounds.max"
              :step="500"
              label="Budget per night"
              :format="money"
              @update:model-value="budget = $event"
            />
          </div>
          <fieldset v-if="amenityOptions.length" class="rail__group">
            <legend class="rail__label">Amenities</legend>
            <label v-for="a in amenityOptions" :key="a" class="rail__check">
              <input type="checkbox" :checked="amenityFilter.includes(a)" @change="toggleAmenity(a)" />
              <span>{{ a }}</span>
            </label>
          </fieldset>
        </aside>

        <!-- Stay rows -->
        <section class="rooms-list" aria-label="Rooms">
          <div class="pills">
            <FilterPill v-if="typeFilter" active @click="setTypeFilter('')" @remove="setTypeFilter('')">Type: {{ typeFilter }}</FilterPill>
            <FilterPill
              v-for="chip in bedChips.filter((c) => c.value)"
              :key="chip.value"
              :active="bedFilter === chip.value"
              @click="bedFilter = bedFilter === chip.value ? '' : chip.value"
              @remove="bedFilter = ''"
            >{{ chip.label }}</FilterPill>
            <FilterPill v-if="budgetActive" active @click="budget = null" @remove="budget = null">Up to {{ money(budget!) }}</FilterPill>
            <FilterPill v-for="a in amenityFilter" :key="a" active @click="toggleAmenity(a)" @remove="toggleAmenity(a)">{{ a }}</FilterPill>
            <button v-if="activeFilterCount" type="button" class="pills__clear" @click="clearFilters">Clear filters</button>
            <label class="sort">
              <span>Sort</span>
              <select v-model="sort">
                <option value="recommended">Recommended</option>
                <option value="low">Price, low to high</option>
                <option value="high">Price, high to low</option>
              </select>
            </label>
          </div>

          <p class="rooms-sub">
            <template v-if="hasDates">{{ displayRooms.length }} rooms free from {{ arrival }} to {{ departure }} for {{ occupants }} {{ occupants === 1 ? 'guest' : 'guests' }}.</template>
            <template v-else>Standard nightly rates shown. Choose dates for exact prices.</template>
          </p>

          <div v-if="searching" class="space-y-4 py-4" role="status">
            <p class="rooms-sub">Searching available rooms…</p>
            <div v-for="i in 3" :key="i" class="skeleton h-48" style="border-radius: var(--radius-panel)" />
          </div>

          <div v-else-if="searchError" class="empty">
            <Notice :message="`We couldn't load room availability. ${String(searchError)}`" />
            <button type="button" class="btn-secondary" @click="retrySearch">Try again</button>
          </div>

          <div v-else-if="displayRooms.length === 0" class="empty">
            <p class="empty__title">
              {{ typeFilter ? `No ${typeFilter} rooms match this search.` : 'No rooms are available for these dates and guest count.' }}
            </p>
            <p>Try different dates or fewer guests, or loosen a filter.</p>
            <button v-if="typeFilter" type="button" class="btn-secondary" @click="setTypeFilter('')">Show all room types</button>
            <button v-else-if="activeFilterCount" type="button" class="btn-secondary" @click="clearFilters">Clear filters</button>
          </div>

          <div v-else class="rows">
            <StayRow v-for="room in displayRooms" :key="room.id" :title="room.type" :selected="room.id === previewId">
              <template #photo>
                <img
                  :src="cardPhoto(room.type).src"
                  :srcset="cardPhoto(room.type).srcset"
                  :sizes="SIZES.card"
                  :alt="cardPhoto(room.type).alt"
                  width="800"
                  height="600"
                  class="row-photo"
                  loading="lazy"
                />
              </template>
              <template #more>
                <button type="button" class="more-pill" @click="previewId = room.id">More details</button>
              </template>
              <template #facts>
                <FactChip v-if="roomCatalogFor(room.type)">{{ roomCatalogFor(room.type)!.beds }}</FactChip>
                <FactChip>Sleeps {{ room.capacity }}</FactChip>
                <FactChip>Room {{ room.number }}</FactChip>
              </template>
              <p v-if="room.amenities?.length" class="row-amenities">{{ room.amenities.slice(0, 4).join(', ') }}</p>
              <p v-if="hasDates" class="row-left">{{ leftOfType(room.type) }} of this type free for your dates</p>
              <p class="row-note">Representative photo. Free cancellation terms are shown before you pay.</p>
              <button
                v-if="getRoomSpaces(room.type).length > 0"
                type="button"
                class="row-link"
                @click="openSpacesModal(room.type)"
              >Explore {{ getRoomSpaces(room.type).length }} room spaces and photos</button>
              <template #price>
                <div v-if="room.rate_minor !== undefined">
                  <span class="price-from">From</span>
                  <p class="price-fig">{{ money(room.rate_minor) }} <span>/ night</span></p>
                </div>
              </template>
              <template #action>
                <button v-if="hasDates" class="btn-cta select-btn" type="button" @click="selectRoom(room)">See price</button>
                <button v-else class="btn-secondary select-btn" type="button" @click="onSearch({ arrival: hotelToday(), departure: followingDay(hotelToday()), occupants })">Pick dates</button>
              </template>
            </StayRow>
          </div>
        </section>

        <!-- Docked detail panel -->
        <DetailPanel :open="Boolean(previewRoom)" :label="previewRoom ? `${previewRoom.type} details` : 'Room details'" @close="previewId = null">
          <template v-if="previewRoom">
            <div class="dp-photo">
              <img :src="cardPhoto(previewRoom.type).src" :srcset="cardPhoto(previewRoom.type).srcset" :sizes="SIZES.card" :alt="cardPhoto(previewRoom.type).alt" width="800" height="600" />
            </div>
            <h2 class="dp-title">{{ previewRoom.type }}</h2>
            <div class="dp-chips">
              <FactChip v-if="roomCatalogFor(previewRoom.type)">{{ roomCatalogFor(previewRoom.type)!.beds }}</FactChip>
              <FactChip>Sleeps {{ previewRoom.capacity }}</FactChip>
              <FactChip>Room {{ previewRoom.number }}</FactChip>
            </div>
            <p class="dp-text">{{ roomCatalogFor(previewRoom.type)?.summary || previewRoom.description || 'A restful room for your stay in Phnom Penh.' }}</p>
            <ul v-if="previewRoom.amenities?.length" class="dp-list">
              <li v-for="a in previewRoom.amenities" :key="a">{{ a }}</li>
            </ul>
            <div class="dp-book">
              <p v-if="previewRoom.rate_minor !== undefined" class="price-fig">{{ money(previewRoom.rate_minor) }} <span>/ night</span></p>
              <button v-if="hasDates" type="button" class="btn-cta select-btn" @click="selectRoom(previewRoom)">Book room</button>
              <button v-else type="button" class="btn-secondary select-btn" @click="onSearch({ arrival: hotelToday(), departure: followingDay(hotelToday()), occupants })">Pick dates</button>
            </div>
            <h3 class="dp-sub">Other rooms</h3>
            <CardStrip :items="stripItems" :selected-id="previewId" label="Other rooms" @select="(id) => (previewId = roomById(id)?.id ?? null)">
              <template #photo="{ item }">
                <img v-if="roomById(item.id)" :src="cardPhoto(roomById(item.id)!.type).src" :alt="cardPhoto(roomById(item.id)!.type).alt" width="140" height="105" loading="lazy" class="strip-img" />
              </template>
            </CardStrip>
          </template>
        </DetailPanel>
      </div>

      <!-- Hold Room / Quote Modal Dialog -->
      <Transition name="modal">
        <div
          v-if="selected && quote"
          class="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="Review your reservation"
          @click.self="selected = null"
        >
          <form class="quote-card relative" @submit.prevent="reserve">
            <button class="quote-close" type="button" aria-label="Close" @click="selected = null">✕</button>
            <p class="quote-meta">Room {{ selected.number }}, {{ selected.type }}</p>
            <h2 class="quote-title">Almost there.</h2>
            <p class="quote-meta">{{ arrival }} to {{ departure }}, {{ occupants }} {{ occupants === 1 ? 'guest' : 'guests' }}</p>

            <div class="quote-lines">
              <p><span>Room charge</span><span>{{ money(quote.room_amount_minor) }}</span></p>
              <p><span>Estimated tax</span><span>{{ money(quote.tax_minor) }}</span></p>
              <p class="quote-total">
                <span>Server-calculated total</span>
                <span>{{ money(quote.total_minor) }}</span>
              </p>
            </div>

            <label class="quote-label">
              Full name
              <input v-model="name" class="field mt-1.5 w-full" required />
            </label>
            <label class="quote-label mt-4">
              Email for verification
              <input v-model="email" class="field mt-1.5 w-full" type="email" required />
            </label>
            <ConsentCheck v-model:accepted="accepted" v-model:document-ids="consentIds" />
            <Notice :message="error" class="mt-4" />
            <button class="btn w-full mt-6 py-3 font-semibold text-base" :disabled="saving || !name || !email || !accepted">
              Hold this room
            </button>
          </form>
        </div>
      </Transition>
      <RoomSpacesModal
        :show="Boolean(modalRoomName)"
        :room-name="modalRoomName || ''"
        :assets="modalAssets"
        @close="closeSpacesModal"
      />
    </div>
  </SiteLayout>
</template>

<style scoped>
.rooms-head { margin-bottom: 1.5rem; display: grid; gap: .5rem; }
.rooms-title { font-size: 3.0625rem; color: var(--river); }
.rooms-head p, .rooms-sub { color: var(--silt); }
.rooms-sub { margin: .75rem 0 1rem; font-size: .9375rem; }

.rooms-layout { display: grid; grid-template-columns: 1fr; gap: 1.5rem; align-items: start; }
.filters-toggle { justify-self: start; min-height: 44px; padding: 0 1.25rem; border-radius: var(--radius-pill); background: var(--river); color: var(--palm-leaf); font: 600 .9375rem var(--font-text); }
.rail { display: none; }
.rail--open { display: grid; position: fixed; inset: auto 0 0 0; z-index: 45; max-height: 85vh; overflow-y: auto; gap: 1.25rem; padding: 1.25rem; background: var(--paper); border-radius: var(--radius-panel) var(--radius-panel) 0 0; box-shadow: var(--shadow-float); }
.rail-scrim { position: fixed; inset: 0; z-index: 44; background: var(--scrim); }
.rail__sheet-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; color: var(--river); }
.rail__done { min-height: 44px; padding: 0 1.1rem; border-radius: var(--radius-pill); background: var(--river); color: var(--palm-leaf); font-weight: 600; }
.rail__group { display: grid; gap: .5rem; border: 0; padding: 0; margin: 0; }
.rail__label { color: var(--river); font-weight: 500; font-size: .875rem; }
.rail__check { display: flex; align-items: center; gap: .6rem; min-height: 44px; color: var(--river); font-size: .9375rem; }
.rail__check input { width: 20px; height: 20px; accent-color: var(--laterite); }

.pills { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; }
.pills__clear { min-height: 44px; padding: 0 .5rem; color: var(--silt); text-decoration: underline; font-size: .875rem; }
.sort { margin-left: auto; display: inline-flex; align-items: center; gap: .5rem; color: var(--silt); font-size: .875rem; }
.sort select { min-height: 44px; border: 1.5px solid var(--rule); border-radius: var(--radius-pill); padding: 0 1rem; background: var(--palm-leaf); color: var(--river); font: 500 .875rem var(--font-text); }

.rows { display: grid; gap: 1rem; }
.row-photo { width: 100%; height: 100%; object-fit: cover; }
.more-pill { min-height: 36px; padding: 0 .9rem; border-radius: var(--radius-pill); background: var(--paper); color: var(--river); font: 600 .8125rem var(--font-text); }
.row-amenities { color: var(--river); font-size: .9375rem; }
.row-left { color: var(--river); font-size: .875rem; font-weight: 500; }
.row-note { color: var(--silt); font-size: .8125rem; }
.row-link { justify-self: start; min-height: 44px; color: var(--laterite); font-size: .875rem; font-weight: 500; text-decoration: underline; text-underline-offset: 4px; }
.price-from { color: var(--silt); font-size: .8125rem; }
.price-fig { color: var(--laterite); font-size: 1.5625rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.price-fig span { color: var(--silt); font-size: .8125rem; font-weight: 400; }
.select-btn { width: 100%; min-height: 44px; border-radius: var(--radius-pill) !important; }

.empty { display: grid; gap: .75rem; justify-items: start; padding: 2rem; border-radius: var(--radius-panel); background: var(--paper); color: var(--silt); }
.empty__title { font: 400 1.5625rem/1.2 var(--font-display); color: var(--river); }

.dp-photo { aspect-ratio: 4 / 3; border-radius: var(--radius-photo); overflow: hidden; margin-top: 2.75rem; }
.dp-photo img { width: 100%; height: 100%; object-fit: cover; }
.dp-title { font-size: 2.4375rem; color: var(--river); margin: 1rem 0 .5rem; }
.dp-chips { display: flex; flex-wrap: wrap; gap: .5rem; }
.dp-text { margin: 1rem 0; color: var(--river); }
.dp-list { display: flex; flex-wrap: wrap; gap: .25rem 1rem; color: var(--silt); font-size: .875rem; list-style: disc inside; }
.dp-book { display: grid; gap: .75rem; margin: 1.25rem 0; padding: 1rem 0; border-block: 1px solid var(--rule); }
.dp-sub { font-size: 1.5625rem; color: var(--river); margin-bottom: .5rem; }
.strip-img { width: 100%; height: 100%; object-fit: cover; }

.quote-card { width: 100%; max-width: 32rem; padding: 2rem; background: var(--paper); border-radius: var(--radius-panel); box-shadow: var(--shadow-float); max-height: 92vh; overflow-y: auto; }
.quote-close { position: absolute; top: .75rem; right: .75rem; width: 44px; height: 44px; color: var(--silt); }
.quote-title { font-size: 2.4375rem; color: var(--river); margin: .25rem 0; }
.quote-meta { color: var(--silt); font-size: .9375rem; }
.quote-lines { margin: 1.25rem 0; padding: 1rem 0; border-block: 1px solid var(--rule); display: grid; gap: .5rem; font-size: .9375rem; font-variant-numeric: tabular-nums; }
.quote-lines p { display: flex; justify-content: space-between; gap: 1rem; }
.quote-total { padding-top: .5rem; border-top: 1px solid var(--rule); font-weight: 600; }
.quote-total span:last-child { color: var(--laterite); font-size: 1.25rem; }
.quote-label { display: block; color: var(--river); font-size: .875rem; font-weight: 500; }

@media (min-width: 1100px) {
  .filters-toggle, .rail__sheet-head, .rail-scrim { display: none; }
  .rooms-layout { grid-template-columns: 260px minmax(0, 1fr); }
  .rooms-layout--panel { grid-template-columns: 260px minmax(0, 1fr) 400px; }
  .rail { display: grid; position: sticky; top: 88px; gap: 1.25rem; align-content: start; }
}
</style>
