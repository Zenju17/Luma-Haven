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
    <section class="hero-panel">
      <div class="hero-copy">
        <h1>A room to come back to.</h1>
        <p class="mt-6">Choose your dates, see the exact price, and settle in. We'll take care of the details that make a stay feel easy.</p>
      </div>
      <div class="hero-keycard" aria-hidden="true">
        <span class="hero-keycard-monogram">LH</span>
        <span class="hero-keycard-caption">Your place to pause.</span>
      </div>
    </section>

    <form class="booking-search" @submit.prevent="search">
      <label><span class="label">Arrival</span><input v-model="arrival" class="field" type="date" required /></label>
      <label><span class="label">Departure</span><input v-model="departure" class="field" type="date" required /></label>
      <label><span class="label">Guests</span><input v-model.number="occupants" class="field" type="number" min="1" max="8" required /></label>
      <button class="btn" type="submit">Search rooms</button>
    </form>
    <Notice :message="error || (searched && availability.error.value ? String(availability.error.value) : '')" />

    <div class="rooms-heading mt-16 flex items-end justify-between gap-5">
      <div><h2 class="text-3xl">Rooms to settle into</h2><p class="text-sm text-[var(--muted)] mt-1">Real availability for the dates you choose.</p></div>
      <span class="text-sm text-[var(--muted)]">Rates in USD · per night</span>
    </div>

    <div v-if="rooms.isPending.value || (searched && availability.isFetching.value)" class="mt-6 space-y-4" role="status">
      <p>Searching availability…</p>
      <div class="grid md:grid-cols-3 gap-6 mt-4">
        <div v-for="i in 3" :key="i" class="card h-64 skeleton opacity-60"></div>
      </div>
    </div>

    <p v-if="searched && displayRooms?.length === 0 && !availability.isFetching.value" class="card p-8 mt-6">No rooms available for those dates. Try another stay.</p>
    
    <div class="grid md:grid-cols-3 gap-6 mt-8">
      <article v-for="room in displayRooms" :key="room.id" class="room-card card">
        <div class="room-key" aria-hidden="true">
          <span class="room-key-number">{{ room.number }}</span>
          <span class="room-key-aside">Luma Haven<br />Room key</span>
        </div>
        <div class="room-card-body">
          <span class="badge">Room {{ room.number }} · Up to {{ room.capacity }}</span>
          <h3 class="text-2xl mt-4">{{ room.type }}</h3>
          <p class="text-[var(--muted)] text-sm mt-2">{{ room.description || 'A restful retreat, made for your next getaway.' }}</p>
          <p v-if="room.amenities?.length" class="amenity-list mt-4">{{ room.amenities.join(' · ') }}</p>
          <div class="room-card-footer">
            <span v-if="room.rate_minor !== undefined" class="font-bold text-lg">{{ money(room.rate_minor) }} <small class="font-normal text-[var(--muted)]">/ night</small></span>
            <button v-if="searched" class="btn-secondary" type="button" @click="selectRoom(room)">View quote</button>
          </div>
        </div>
      </article>
    </div>

    <Transition name="modal">
      <div v-if="selected && quote" class="modal-backdrop" role="dialog" aria-modal="true" aria-label="Review your reservation" @click.self="selected = null">
        <form class="card p-8 w-full max-w-lg" @submit.prevent="reserve">
          <button class="float-right text-lg opacity-70 hover:opacity-100 transition-opacity" type="button" aria-label="Close" @click="selected = null">✕</button>
          <p class="label">Your stay · Room {{ selected.number }}</p>
          <h2 class="text-3xl">Almost there.</h2>
          <p class="mt-4 text-[var(--muted)]">{{ arrival }} to {{ departure }} · {{ occupants }} guest(s)</p>
          <div class="border-y border-[var(--line)] my-6 py-4 space-y-2">
            <p class="flex justify-between"><span>Room</span><span>{{ money(quote.room_amount_minor) }}</span></p>
            <p class="flex justify-between"><span>Tax</span><span>{{ money(quote.tax_minor) }}</span></p>
            <p class="flex justify-between font-bold"><span>Server-calculated total</span><span>{{ money(quote.total_minor) }}</span></p>
          </div>
          <label class="label">Full name<input v-model="name" class="field mt-2 normal-case" required /></label>
          <label class="label mt-4">Email for verification<input v-model="email" class="field mt-2 normal-case" type="email" required /></label>
          <Notice :message="error" />
          <button class="btn w-full mt-6" :disabled="saving || !name || !email">Hold this room</button>
        </form>
      </div>
    </Transition>
  </SiteLayout>
</template>
