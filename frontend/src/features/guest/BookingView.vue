<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import { money, type Booking } from '../../types'

const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id))
const booking = useQuery({ queryKey: computed(() => ['booking', id.value]), queryFn: () => api<Booking>(`/reservations/${id.value}`) })
const message = ref('')
const failed = ref(false)
const busy = ref(false)
const requestType = ref('Towels')
const description = ref('')
const requestError = ref('')
const printReceipt = () => window.print()
const eligibleToday = computed(() => {
  const data = booking.data.value
  return Boolean(data?.verified && data.hotel_today >= data.arrival && data.hotel_today < data.departure)
})

async function act(action: () => Promise<unknown>) {
  if (busy.value) return
  busy.value = true
  message.value = ''
  failed.value = false
  try {
    await action()
    await booking.refetch()
    message.value = 'Updated successfully'
  } catch (error) {
    failed.value = true
    message.value = String(error)
  } finally {
    busy.value = false
  }
}

async function pay() {
  if (busy.value) return
  busy.value = true
  message.value = ''
  try {
    const session = await api<{ checkout_url: string }>(`/reservations/${id.value}/payment-sessions`, {})
    await router.push(session.checkout_url)
  } catch (error) {
    failed.value = true
    message.value = String(error)
  } finally {
    busy.value = false
  }
}

async function sendRequest() {
  requestError.value = ''
  try {
    await api(`/reservations/${id.value}/service-requests`, { type: requestType.value, description: description.value })
    description.value = ''
    await booking.refetch()
  } catch (error) {
    requestError.value = String(error)
  }
}
</script>

<template>
  <SiteLayout>
    <div v-if="booking.isPending.value" role="status">Loading your stay…</div>
    <Notice v-else-if="booking.error.value" :message="String(booking.error.value)" />
    <div v-else-if="booking.data.value" class="max-w-3xl mx-auto">
      <p class="label">Your reservation</p>
      <h1 class="text-4xl">Welcome, {{ booking.data.value.guest_name }}.</h1>
      <p class="mt-3 text-[#6d8075]">Booking {{ booking.data.value.reference }} · <span class="badge">{{ booking.data.value.status.replaceAll('_', ' ') }}</span></p>
      <div class="grid md:grid-cols-2 gap-5 mt-8">
        <div class="card p-6">
          <span class="label">Your room</span>
          <h2 class="text-2xl">{{ booking.data.value.room_type }} · {{ booking.data.value.room }}</h2>
          <p class="mt-3">{{ booking.data.value.arrival }} → {{ booking.data.value.departure }}</p>
          <p class="mt-3 text-sm text-[#6d8075]">Please collect your physical key at reception. QR entry is for booking verification only.</p>
        </div>
        <div class="card p-6">
          <span class="label">Folio · {{ booking.data.value.currency }}</span>
          <h2 class="text-2xl">Balance {{ money(booking.data.value.balance_minor) }}</h2>
          <p v-for="(entry, index) in booking.data.value.entries" :key="index" class="flex justify-between mt-2 text-sm">
            <span>{{ entry.description }} · {{ entry.service_date }}</span><span>{{ money(entry.amount_minor) }}</span>
          </p>
          <button v-if="booking.data.value.balance_minor > 0" class="btn mt-5" :disabled="busy" @click="pay">Pay balance (simulation) →</button>
        </div>
      </div>

      <div v-if="booking.data.value.status === 'CONFIRMED'" class="card p-6 mt-5">
        <h2 class="text-2xl">Ready to arrive?</h2>
        <p class="text-sm text-[#6d8075] mt-2">Verify your email before check-in.</p>
        <RouterLink class="btn inline-block mt-4" to="/verify">Verify booking →</RouterLink>
        <button v-if="eligibleToday" class="btn-secondary ml-3" :disabled="busy" @click="act(() => api(`/reservations/${id}/check-in`, {}))">Check in</button>
        <p v-else-if="booking.data.value.verified && booking.data.value.hotel_today < booking.data.value.arrival" class="text-sm mt-4">Check-in opens on {{ booking.data.value.arrival }} ({{ booking.data.value.hotel_timezone }}).</p>
        <p v-else-if="booking.data.value.verified && booking.data.value.hotel_today >= booking.data.value.departure" class="text-sm mt-4">Your arrival window has passed. Please contact reception.</p>
      </div>

      <div v-if="booking.data.value.status === 'CHECKED_IN'" class="card p-6 mt-5">
        <h2 class="text-2xl">Enjoy your stay</h2>
        <p class="mt-2">Need anything? Let us know.</p>
        <form class="flex flex-col gap-3 mt-4" @submit.prevent="sendRequest">
          <select v-model="requestType" class="field" aria-label="Service type">
            <option>Towels</option><option>Cleaning</option><option>Maintenance</option><option>Reception</option>
          </select>
          <input v-model="description" class="field" placeholder="How can we help?" aria-label="How can we help?" required />
          <button class="btn-secondary">Send request</button>
          <Notice :message="requestError" />
        </form>
        <p v-for="request in booking.data.value.requests" :key="request.id" class="border-t mt-3 pt-3">
          {{ request.type }}: {{ request.description }} <span class="badge">{{ request.status }}</span>
        </p>
        <button class="btn mt-6" :disabled="busy || booking.data.value.balance_minor > 0" @click="act(() => api(`/reservations/${id}/check-out`, { folio_version: booking.data.value?.folio_version }))">Check out →</button>
        <p v-if="booking.data.value.balance_minor > 0" class="text-sm mt-2">Settle your balance before checkout.</p>
      </div>

      <div v-if="booking.data.value.status === 'CHECKED_OUT'" class="card p-8 mt-5">
        <h2 class="text-2xl">Thank you for staying with us.</h2>
        <p class="mt-2">Your receipt is shown above. We hope to welcome you back.</p>
        <button class="btn-secondary mt-4" @click="printReceipt">Print receipt</button>
      </div>
      <Notice :message="message" :status="!failed" />
    </div>
  </SiteLayout>
</template>
