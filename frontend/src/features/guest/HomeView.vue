<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import { money, type Quote, type Room } from '../../types'

const router = useRouter()
const arrival = ref('')
const departure = ref('')
const occupants = ref(2)
const searched = ref(false)
const selected = ref<Room | null>(null)
const quote = ref<Quote | null>(null)
const name = ref('')
const email = ref('')
const error = ref('')
const saving = ref(false)

const rooms = useQuery({ queryKey: ['rooms'], queryFn: () => api<Room[]>('/rooms') })
const availability = useQuery({
  queryKey: computed(() => ['availability', arrival.value, departure.value, occupants.value]),
  queryFn: () => api<Room[]>(`/availability?arrival=${encodeURIComponent(arrival.value)}&departure=${encodeURIComponent(departure.value)}&occupants=${occupants.value}`),
  enabled: searched,
})
const displayRooms = computed(() => searched.value ? availability.data.value : rooms.data.value)

async function search() {
  error.value = ''
  if (!arrival.value || !departure.value || arrival.value >= departure.value) {
    error.value = 'Choose an arrival date before your departure date.'
    return
  }
  searched.value = true
  const result = await availability.refetch()
  if (result.error) error.value = String(result.error)
}

async function selectRoom(room: Room) {
  error.value = ''
  try {
    quote.value = await api<Quote>('/quotes', {
      room_id: room.id, arrival: arrival.value, departure: departure.value, occupants: occupants.value,
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
      quote_id: quote.value.id, name: name.value, email: email.value,
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
    <!-- Hero Section -->
    <section class="hero-panel">
      <div class="hero-copy">
        <h1 class="leading-[1.1]">A room to come back to.</h1>
        <p class="mt-5 text-base sm:text-lg">Choose your dates, see the exact price, and settle in. We'll take care of the details that make a stay feel easy.</p>
      </div>
      <div class="hero-keycard" aria-hidden="true">
        <span class="hero-keycard-monogram">LH</span>
        <span class="hero-keycard-caption">Your place to pause.</span>
      </div>
    </section>

    <!-- Booking Search Form -->
    <form class="booking-search" @submit.prevent="search">
      <label>
        <span class="label">Arrival</span>
        <input v-model="arrival" class="field cursor-pointer" type="date" required />
      </label>
      <label>
        <span class="label">Departure</span>
        <input v-model="departure" class="field cursor-pointer" type="date" required />
      </label>
      <label>
        <span class="label">Guests</span>
        <select v-model.number="occupants" class="field cursor-pointer" required aria-label="Guests">
          <option :value="1">1 Guest</option>
          <option :value="2">2 Guests</option>
          <option :value="3">3 Guests</option>
          <option :value="4">4 Guests</option>
          <option :value="5">5 Guests</option>
          <option :value="6">6 Guests</option>
          <option :value="7">7 Guests</option>
          <option :value="8">8 Guests</option>
        </select>
      </label>
      <button class="btn w-full" type="submit">Search rooms</button>
    </form>
    <Notice :message="error || (searched && availability.error.value ? String(availability.error.value) : '')" />

    <!-- Rooms Heading -->
    <div class="rooms-heading mt-16 flex items-end justify-between gap-5">
      <div>
        <h2 class="text-3xl text-[var(--brand-text)]">Rooms to settle into</h2>
        <p class="text-sm text-[var(--muted)] mt-1">Real availability for the dates you choose.</p>
      </div>
      <span class="text-xs sm:text-sm text-[var(--muted)] font-medium">Rates in USD · per night</span>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="rooms.isPending.value || (searched && availability.isFetching.value)" class="mt-6 space-y-4" role="status">
      <p class="text-sm text-[var(--muted)]">Searching availability…</p>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-4">
        <div v-for="i in 3" :key="i" class="card h-72 skeleton opacity-65"></div>
      </div>
    </div>

    <!-- Empty State -->
    <p v-if="searched && displayRooms?.length === 0 && !availability.isFetching.value" class="card p-8 mt-6 text-center text-[var(--muted)]">
      No rooms available for those dates. Try another stay.
    </p>

    <!-- Room Cards Grid -->
    <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
      <article v-for="room in displayRooms" :key="room.id" class="room-card card">
        <!-- Room Key Art Fallback or Photo -->
        <div class="room-key" aria-hidden="true">
          <span class="room-key-number">{{ room.number }}</span>
          <span class="room-key-aside">Luma Haven<br />Room key</span>
        </div>

        <!-- Room Details Body -->
        <div class="room-card-body">
          <div class="flex items-center justify-between gap-2">
            <span class="badge">Room {{ room.number }} · Up to {{ room.capacity }} {{ room.capacity === 1 ? 'guest' : 'guests' }}</span>
          </div>

          <h3 class="text-2xl mt-4 text-[var(--brand-text)]">{{ room.type }}</h3>
          <p class="text-[var(--muted)] text-sm mt-2 line-clamp-2">
            {{ room.description || 'A restful retreat, made for your next getaway.' }}
          </p>

          <p v-if="room.amenities?.length" class="amenity-list mt-4">
            {{ room.amenities.join(' · ') }}
          </p>

          <div class="room-card-footer">
            <div v-if="room.rate_minor !== undefined" class="flex flex-col">
              <span class="text-xs text-[var(--muted)]">From</span>
              <span class="font-bold text-xl text-[var(--brand-text)]">
                {{ money(room.rate_minor) }}
                <span class="font-normal text-xs text-[var(--muted)]">/ night</span>
              </span>
            </div>
            <button v-if="searched" class="btn-secondary" type="button" @click="selectRoom(room)">
              View quote
            </button>
          </div>
        </div>
      </article>
    </div>

    <!-- Hold Room / Quote Modal Dialog -->
    <Transition name="modal">
      <div v-if="selected && quote" class="modal-backdrop" role="dialog" aria-modal="true" aria-label="Review your reservation" @click.self="selected = null">
        <form class="card p-8 w-full max-w-lg shadow-2xl relative" @submit.prevent="reserve">
          <button
            class="absolute top-6 right-6 text-xl p-1 text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
            type="button"
            aria-label="Close"
            @click="selected = null"
          >
            ✕
          </button>
          <span class="badge">Your stay · Room {{ selected.number }}</span>
          <h2 class="text-3xl mt-3 text-[var(--brand-text)]">Almost there.</h2>
          <p class="mt-3 text-sm text-[var(--muted)]">{{ arrival }} to {{ departure }} · {{ occupants }} guest(s)</p>

          <div class="border-y border-[var(--line)] my-6 py-4 space-y-2 text-sm">
            <p class="flex justify-between"><span>Room charge</span><span>{{ money(quote.room_amount_minor) }}</span></p>
            <p class="flex justify-between"><span>Estimated tax</span><span>{{ money(quote.tax_minor) }}</span></p>
            <p class="flex justify-between font-bold text-base pt-2 border-t border-[var(--line)]">
              <span>Server-calculated total</span>
              <span class="text-[var(--brass)]">{{ money(quote.total_minor) }}</span>
            </p>
          </div>

          <label class="label">Full name<input v-model="name" class="field mt-1.5 normal-case" required /></label>
          <label class="label mt-4">Email for verification<input v-model="email" class="field mt-1.5 normal-case" type="email" required /></label>
          <Notice :message="error" />
          <button class="btn w-full mt-6" :disabled="saving || !name || !email">Hold this room</button>
        </form>
      </div>
    </Transition>
  </SiteLayout>
</template>
