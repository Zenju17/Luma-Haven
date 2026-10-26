<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, money } from '../lib/api'
import type { Quote, Room } from '../types'
import Notice from '../components/Notice.vue'

const router = useRouter()

const arrival = ref('')
const departure = ref('')
const occupants = ref(2)
const searched = ref(false)
const error = ref('')
const selected = ref<Room | null>(null)
const quote = ref<Quote | null>(null)
const name = ref('')
const email = ref('')

const rooms = ref<Room[] | null>(null)
const results = ref<Room[] | null>(null)
const isFetching = ref(false)

const displayedRooms = computed(() => (searched.value ? results.value : rooms.value) ?? [])

onMounted(async () => {
  try {
    rooms.value = await api<Room[]>('/rooms')
  } catch (e) {
    error.value = String(e)
  }
})

async function search() {
  error.value = ''
  searched.value = true
  isFetching.value = true
  try {
    results.value = await api<Room[]>(
      `/availability?arrival=${arrival.value}&departure=${departure.value}&occupants=${occupants.value}`,
    )
  } catch (e) {
    error.value = String(e)
  } finally {
    isFetching.value = false
  }
}

async function choose(room: Room) {
  error.value = ''
  try {
    quote.value = await api<Quote>('/quotes', {
      room_id: room.id,
      arrival: arrival.value,
      departure: departure.value,
      occupants: occupants.value,
    })
    selected.value = room
  } catch (e) {
    error.value = String(e)
  }
}

async function reserve() {
  try {
    const booking = await api<{ id: number }>('/reservations', {
      quote_id: quote.value?.id,
      name: name.value,
      email: email.value,
    })
    router.push(`/booking/${booking.id}`)
  } catch (e) {
    error.value = String(e)
  }
}

function closeModal() {
  selected.value = null
}
</script>

<template>
  <div class="rounded-[28px] bg-[#123e35] text-white p-8 md:p-16 relative overflow-hidden">
    <div
      class="absolute right-0 top-0 opacity-10 text-[220px] serif leading-none pointer-events-none"
    >
      ✳
    </div>
    <p class="text-[#d7b683] uppercase tracking-[.25em] text-xs font-bold mb-6">
      A more thoughtful way to stay
    </p>
    <h1 class="text-4xl md:text-6xl max-w-xl leading-tight">Your next chapter starts here.</h1>
    <p class="text-[#c0d7c9] mt-5 max-w-lg">
      Find the space that feels like yours. Simple booking, warm hospitality, and everything you
      need at your fingertips.
    </p>
  </div>

  <form
    class="card relative md:-mt-9 mx-auto max-w-5xl p-5 md:p-7 grid grid-cols-1 md:grid-cols-4 gap-4"
    @submit.prevent="search"
  >
    <label>
      <span class="label">Arrival</span>
      <input v-model="arrival" class="field" type="date" required />
    </label>
    <label>
      <span class="label">Departure</span>
      <input v-model="departure" class="field" type="date" required />
    </label>
    <label>
      <span class="label">Guests</span>
      <input v-model.number="occupants" class="field" type="number" min="1" max="8" />
    </label>
    <button class="btn mt-5" type="submit">Search rooms →</button>
  </form>

  <Notice :error="error" />

  <div class="mt-16 flex items-end justify-between">
    <div>
      <p class="label text-[#b68c55]">Stay your way</p>
      <h2 class="text-3xl">Rooms to settle into</h2>
    </div>
    <span class="text-sm text-[#75867c]">Rates in USD · per night</span>
  </div>

  <p v-if="isFetching" class="mt-6">Searching availability…</p>
  <p v-if="searched && results?.length === 0" class="card p-8 mt-6">
    No rooms available for those dates. Try another stay.
  </p>

  <div class="grid md:grid-cols-3 gap-6 mt-8">
    <article v-for="room in displayedRooms" :key="room.id" class="card overflow-hidden">
      <div class="h-40 bg-[#dae7da] flex items-center justify-center text-6xl text-[#6c9985]">✳</div>
      <div class="p-6">
        <span class="badge">Room {{ room.number }} · Up to {{ room.capacity }}</span>
        <h3 class="text-2xl mt-3">{{ room.type }}</h3>
        <p class="text-[#71857a] text-sm mt-2">
          A restful retreat, made for your next getaway.
        </p>
        <div class="flex justify-between items-center mt-6">
          <span class="font-bold text-lg">
            {{ money(room.rate_minor) }}
            <small class="font-normal text-[#7a887e]">/ night</small>
          </span>
          <button v-if="searched" class="btn-secondary" @click="choose(room)">Select →</button>
        </div>
      </div>
    </article>
  </div>

  <div
    v-if="selected && quote"
    class="fixed inset-0 z-10 bg-[#0c2b26aa] flex items-center justify-center p-4"
    @click.self="closeModal"
  >
    <div class="card p-8 w-full max-w-lg">
      <button class="float-right" aria-label="Close" @click="closeModal">✕</button>
      <p class="label">Your stay · Room {{ selected.number }}</p>
      <h2 class="text-3xl">Almost there.</h2>
      <p class="mt-4 text-[#698176]">
        {{ arrival }} to {{ departure }} · {{ occupants }} guest(s)
      </p>
      <div class="border-y my-6 py-4 space-y-2">
        <p class="flex justify-between">
          <span>Room</span><span>{{ money(quote.room_amount_minor) }}</span>
        </p>
        <p class="flex justify-between">
          <span>Tax</span><span>{{ money(quote.tax_minor) }}</span>
        </p>
        <p class="flex justify-between font-bold">
          <span>Server-calculated total</span><span>{{ money(quote.total_minor) }}</span>
        </p>
      </div>
      <label class="label">
        Full name
        <input v-model="name" class="field mt-2 normal-case" />
      </label>
      <label class="label mt-4">
        Email for verification
        <input v-model="email" class="field mt-2 normal-case" type="email" />
      </label>
      <Notice :error="error" />
      <button :disabled="!name || !email" class="btn w-full mt-6" @click="reserve">
        Hold this room →
      </button>
    </div>
  </div>
</template>
