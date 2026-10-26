<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api, money } from '../lib/api'
import type { Booking } from '../types'
import Notice from '../components/Notice.vue'
import RequestForm from '../components/RequestForm.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id))

const data = ref<Booking | null>(null)
const isLoading = ref(true)
const error = ref<string | null>(null)
const msg = ref('')

async function load() {
  data.value = await api<Booking>(`/reservations/${id.value}`)
}

onMounted(async () => {
  try {
    await load()
  } catch (e) {
    error.value = String(e)
  } finally {
    isLoading.value = false
  }
})

async function act(fn: () => Promise<unknown>) {
  try {
    await fn()
    msg.value = 'Updated successfully'
    await load()
  } catch (e) {
    msg.value = String(e)
  }
}

async function startPayment() {
  await act(async () => {
    const session = await api<{ checkout_url: string }>(
      `/reservations/${id.value}/payment-sessions`,
      {},
    )
    router.push(session.checkout_url)
  })
}

function checkIn() {
  return act(() => api(`/reservations/${id.value}/check-in`, {}))
}

function checkOut() {
  return act(() =>
    api(`/reservations/${id.value}/check-out`, { folio_version: data.value?.folio_version }),
  )
}

function printReceipt() {
  window.print()
}
</script>

<template>
  <p v-if="isLoading">Loading your stay…</p>
  <Notice v-else-if="error" :error="error" />
  <div v-else-if="data" class="max-w-3xl mx-auto">
    <p class="label">Your reservation</p>
    <h1 class="text-4xl">Welcome, {{ data.guest_name }}.</h1>
    <p class="mt-3 text-[#6d8075]">
      Booking {{ data.reference }} · <span class="badge">{{ data.status.replace('_', ' ') }}</span>
    </p>

    <div class="grid md:grid-cols-2 gap-5 mt-8">
      <div class="card p-6">
        <span class="label">Your room</span>
        <h2 class="text-2xl">{{ data.room_type }} · {{ data.room }}</h2>
        <p class="mt-3">{{ data.arrival }} → {{ data.departure }}</p>
        <p class="mt-3 text-sm text-[#6d8075]">
          Please collect your physical key at reception. QR entry is for booking verification only.
        </p>
      </div>
      <div class="card p-6">
        <span class="label">Folio · {{ data.currency }}</span>
        <h2 class="text-2xl">Balance {{ money(data.balance_minor) }}</h2>
        <p v-for="(entry, i) in data.entries" :key="i" class="flex justify-between mt-2 text-sm">
          <span>{{ entry.description }} · {{ entry.service_date }}</span>
          <span>{{ money(entry.amount_minor) }}</span>
        </p>
        <button v-if="data.balance_minor > 0" class="btn mt-5" @click="startPayment">
          Pay balance (simulation) →
        </button>
      </div>
    </div>

    <div v-if="data.status === 'CONFIRMED'" class="card p-6 mt-5">
      <h2 class="text-2xl">Ready to arrive?</h2>
      <p class="text-sm text-[#6d8075] mt-2">Verify your email before check-in.</p>
      <RouterLink class="btn inline-block mt-4" to="/verify">Verify booking →</RouterLink>
      <button
        v-if="data.verified"
        class="btn-secondary ml-3"
        @click="checkIn"
      >
        Check in
      </button>
    </div>

    <div v-if="data.status === 'CHECKED_IN'" class="card p-6 mt-5">
      <h2 class="text-2xl">Enjoy your stay</h2>
      <p class="mt-2">Need anything? Let us know.</p>
      <RequestForm :id="id" @done="load" />
      <p v-for="request in data.requests" :key="request.id" class="border-t mt-3 pt-3">
        {{ request.type }}: {{ request.description }}
        <span class="badge">{{ request.status }}</span>
      </p>
      <button
        :disabled="data.balance_minor > 0"
        class="btn mt-6"
        @click="checkOut"
      >
        Check out →
      </button>
      <p v-if="data.balance_minor > 0" class="text-sm mt-2">
        Settle your balance before checkout.
      </p>
    </div>

    <div v-if="data.status === 'CHECKED_OUT'" class="card p-8 mt-5">
      <h2 class="text-2xl">Thank you for staying with us.</h2>
      <p class="mt-2">Your receipt is shown above. We hope to welcome you back.</p>
      <button class="btn-secondary mt-4" @click="printReceipt">Print receipt</button>
    </div>

    <p role="status" class="mt-4">{{ msg }}</p>
  </div>
</template>
