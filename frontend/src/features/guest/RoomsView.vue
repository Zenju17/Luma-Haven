<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import AvailabilitySearch from './components/AvailabilitySearch.vue'
import RoomSpacesModal from './components/RoomSpacesModal.vue'
import { api } from '../../services/api'
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

const displayRooms = computed(() => {
  const source = hasDates.value ? availability.data.value : rooms.data.value
  if (!source) return []
  if (!typeFilter.value) return source
  return source.filter((r) => r.type.toLowerCase().includes(typeFilter.value.toLowerCase()))
})

// Sync query params when route changes
watch(
  () => route.query,
  (q) => {
    if (q.arrival) arrival.value = q.arrival as string
    if (q.departure) departure.value = q.departure as string
    if (q.occupants) occupants.value = Number(q.occupants)
    if (q.type !== undefined) typeFilter.value = q.type as string
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
    <div class="py-6 sm:py-10 space-y-8">
      <!-- Page Header -->
      <div class="space-y-2">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--glass-border)] bg-[var(--surface-muted)] text-[var(--brass)] text-xs font-semibold tracking-wider uppercase">
          Luma Haven · Room Inventory
        </div>
        <h1 class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
          Rooms &amp; Availability<span class="text-[var(--brass)]">.</span>
        </h1>
        <p class="text-sm sm:text-base text-[var(--muted)] max-w-2xl">
          Enter your dates below to see verified available rooms, live rates, and instant quotes. Physical brass keys await at reception.
        </p>
      </div>

      <!-- Search Bar -->
      <AvailabilitySearch
        :initial-arrival="arrival"
        :initial-departure="departure"
        :initial-occupants="occupants"
        :navigate-on-submit="false"
        @search="onSearch"
      />

      <!-- Banner linking to Spaces Explorer -->
      <div class="mb-6 p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--glass-border)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs sm:text-sm shadow-sm">
        <span class="text-[var(--muted)]">
          Looking to review all hotel architecture, rooftop pool, and interior design concepts?
        </span>
        <RouterLink to="/spaces" class="font-semibold text-[var(--brass)] hover:underline inline-flex items-center gap-1 shrink-0">
          Review all 28 hotel locations &rarr;
        </RouterLink>
      </div>

      <!-- Filter status / Active dates notice -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--line)] pb-4 pt-2">
        <div>
          <h2 class="text-xl sm:text-2xl font-medium text-[var(--brand-text)] serif">
            {{ hasDates ? 'Available Rooms for Your Stay' : 'All Guest Rooms' }}
          </h2>
          <p class="text-xs sm:text-sm text-[var(--muted)]">
            <span v-if="hasDates">
              Showing availability for {{ arrival }} to {{ departure }} · {{ occupants }} guest(s)
            </span>
            <span v-else>
              Standard nightly rates shown. Choose dates above for exact pricing.
            </span>
          </p>
        </div>

        <!-- Room Type quick filters -->
        <div class="flex items-center gap-2 text-xs">
          <span class="text-[var(--muted)]">Filter:</span>
          <button
            type="button"
            :class="[
              'px-3 py-1 rounded-full font-medium transition-colors',
              typeFilter === '' ? 'bg-[var(--brass)] text-white' : 'bg-[var(--surface-muted)] text-[var(--muted)] hover:text-[var(--brand-text)]',
            ]"
            @click="typeFilter = ''"
          >
            All
          </button>
          <button
            type="button"
            :class="[
              'px-3 py-1 rounded-full font-medium transition-colors',
              typeFilter === 'Garden King' ? 'bg-[var(--brass)] text-white' : 'bg-[var(--surface-muted)] text-[var(--muted)] hover:text-[var(--brand-text)]',
            ]"
            @click="typeFilter = 'Garden King'"
          >
            Garden King
          </button>
          <button
            type="button"
            :class="[
              'px-3 py-1 rounded-full font-medium transition-colors',
              typeFilter === 'City Twin' ? 'bg-[var(--brass)] text-white' : 'bg-[var(--surface-muted)] text-[var(--muted)] hover:text-[var(--brand-text)]',
            ]"
            @click="typeFilter = 'City Twin'"
          >
            City Twin
          </button>
          <button
            type="button"
            :class="[
              'px-3 py-1 rounded-full font-medium transition-colors',
              typeFilter === 'Family Suite' ? 'bg-[var(--brass)] text-white' : 'bg-[var(--surface-muted)] text-[var(--muted)] hover:text-[var(--brand-text)]',
            ]"
            @click="typeFilter = 'Family Suite'"
          >
            Family Suite
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="rooms.isPending.value || (hasDates && availability.isFetching.value)" class="space-y-4 py-8" role="status">
        <p class="text-sm text-[var(--muted)]">Searching available rooms…</p>
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="i in 3" :key="i" class="card h-72 skeleton opacity-65 rounded-2xl" />
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-else-if="displayRooms.length === 0"
        class="card p-10 text-center space-y-3 rounded-2xl border border-[var(--glass-border)]"
      >
        <p class="serif text-xl font-medium text-[var(--brand-text)]">
          No rooms found matching your criteria.
        </p>
        <p class="text-sm text-[var(--muted)] max-w-md mx-auto">
          Try selecting different dates or resetting the room type filter. Our reception team is also available at hello@luma.local.
        </p>
      </div>

      <!-- Room Cards Grid -->
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <article
          v-for="room in displayRooms"
          :key="room.id"
          class="room-card card flex flex-col justify-between rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)] shadow-sm hover:shadow-lg transition-all"
        >
          <!-- Room Image Thumbnail (if assigned) -->
          <div v-if="getRoomTypeAsset(room.type)" class="relative aspect-[16/10] overflow-hidden rounded-t-2xl bg-[var(--deep)] border-b border-[var(--glass-border)]">
            <img
              :src="getRoomTypeAsset(room.type)!.image_url"
              :alt="getRoomTypeAsset(room.type)!.alt_text"
              class="w-full h-full object-cover object-center"
              loading="lazy"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-[var(--deep)]/40 to-transparent pointer-events-none" />
            <div
              v-if="getRoomTypeAsset(room.type)!.source_type === 'CONCEPT'"
              class="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-medium tracking-wide bg-black/60 text-[#d9b87f] border border-[#d9b87f]/30 backdrop-blur-md"
            >
              Design Concept
            </div>
          </div>
          <!-- Room Key Graphic Badge (fallback if no photo assigned) -->
          <div v-else class="room-key" aria-hidden="true">
            <span class="room-key-number">{{ room.number }}</span>
            <span class="room-key-aside">Luma Haven<br />Physical key</span>
          </div>


          <div class="room-card-body p-6 flex flex-col grow justify-between space-y-4">
            <div class="space-y-2">
              <div class="flex items-center justify-between gap-2">
                <span class="badge">
                  Room {{ room.number }} · Up to {{ room.capacity }} {{ room.capacity === 1 ? 'guest' : 'guests' }}
                </span>
              </div>

              <h3 class="text-2xl font-medium text-[var(--brand-text)] serif">
                {{ room.type }}
              </h3>

              <p class="text-[var(--muted)] text-sm line-clamp-2">
                {{ room.description || 'A restful retreat, made for your next getaway in Phnom Penh.' }}
              </p>

              <p v-if="room.amenities?.length" class="amenity-list text-xs text-[var(--muted)] pt-2 border-t border-[var(--line)]">
                {{ room.amenities.join(' · ') }}
              </p>

              <!-- Explore Room Spaces button (if assets exist) -->
              <button
                v-if="getRoomSpaces(room.type).length > 0"
                type="button"
                class="text-xs text-[var(--brass)] hover:underline inline-flex items-center gap-1.5 font-medium pt-2 transition-colors"
                @click="openSpacesModal(room.type)"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>Explore {{ getRoomSpaces(room.type).length }} room spaces &amp; photos &rarr;</span>
              </button>
            </div>

            <!-- Card Footer: Rate & Action -->
            <div class="room-card-footer pt-4 border-t border-[var(--line)] flex items-center justify-between gap-4">
              <div v-if="room.rate_minor !== undefined" class="flex flex-col">
                <span class="text-xs text-[var(--muted)]">From</span>
                <span class="font-bold text-xl text-[var(--brand-text)]">
                  {{ money(room.rate_minor) }}
                  <span class="font-normal text-xs text-[var(--muted)]">/ night</span>
                </span>
              </div>

              <!-- View Quote Button: active when dates exist -->
              <button
                v-if="hasDates"
                class="btn-secondary text-sm font-semibold px-4 py-2"
                type="button"
                @click="selectRoom(room)"
              >
                View quote
              </button>
              <button
                v-else
                class="btn-secondary text-xs font-semibold px-3 py-2"
                type="button"
                @click="onSearch({ arrival: new Date().toISOString().split('T')[0], departure: new Date(Date.now() + 86400000).toISOString().split('T')[0], occupants })"
              >
                Select dates
              </button>
            </div>
          </div>
        </article>
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
          <form class="card p-8 w-full max-w-lg shadow-2xl relative rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)]" @submit.prevent="reserve">
            <button
              class="absolute top-6 right-6 text-xl p-1 text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
              type="button"
              aria-label="Close"
              @click="selected = null"
            >
              ✕
            </button>
            <span class="badge">Your stay · Room {{ selected.number }} ({{ selected.type }})</span>
            <h2 class="text-3xl mt-3 text-[var(--brand-text)] serif">Almost there.</h2>
            <p class="mt-2 text-sm text-[var(--muted)]">
              {{ arrival }} to {{ departure }} · {{ occupants }} guest(s)
            </p>

            <div class="border-y border-[var(--line)] my-6 py-4 space-y-2 text-sm">
              <p class="flex justify-between"><span>Room charge</span><span>{{ money(quote.room_amount_minor) }}</span></p>
              <p class="flex justify-between"><span>Estimated tax</span><span>{{ money(quote.tax_minor) }}</span></p>
              <p class="flex justify-between font-bold text-base pt-2 border-t border-[var(--line)]">
                <span>Server-calculated total</span>
                <span class="text-[var(--brass)]">{{ money(quote.total_minor) }}</span>
              </p>
            </div>

            <label class="label block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-1">
              Full name
              <input v-model="name" class="field mt-1.5 normal-case w-full" required />
            </label>
            <label class="label block text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mt-4 mb-1">
              Email for verification
              <input v-model="email" class="field mt-1.5 normal-case w-full" type="email" required />
            </label>
            <Notice :message="error" class="mt-4" />
            <button class="btn w-full mt-6 py-3 font-semibold text-base shadow-md" :disabled="saving || !name || !email">
              Hold this room
            </button>
          </form>
        </div>
      </Transition>
      <!-- Room Spaces Modal -->
      <RoomSpacesModal
        :show="Boolean(modalRoomName)"
        :room-name="modalRoomName || ''"
        :assets="modalAssets"
        @close="closeSpacesModal"
      />
    </div>
  </SiteLayout>
</template>
