<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import MyDataPanel from './components/MyDataPanel.vue'
import PrintableReceipt from './components/PrintableReceipt.vue'
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
    message.value = 'Your stay details are up to date.'
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
    <!-- Screen View (Hidden when printing) -->
    <div class="screen-only print:hidden">
      <div v-if="booking.isPending.value" role="status" class="max-w-3xl mx-auto space-y-4">
        <p>Loading your stay…</p>
        <div class="skeleton h-10 w-72 rounded-xl"></div>
        <div class="skeleton h-5 w-48 rounded-lg mt-2"></div>
        <div class="grid md:grid-cols-2 gap-5 mt-8">
          <div class="card h-48 skeleton opacity-60"></div>
          <div class="card h-48 skeleton opacity-60"></div>
        </div>
      </div>
      <Notice v-else-if="booking.error.value" :message="String(booking.error.value)" />
      <div v-else-if="booking.data.value" class="max-w-3xl mx-auto">
        <div class="flex items-center gap-2.5 mb-2">
          <img src="/images/luma-haven/branding/logo.png" alt="Luma Haven Logo" class="w-7 h-7 object-contain" />
          <p class="label mb-0">Your reservation</p>
        </div>
        <h1 class="text-4xl text-[var(--brand-text)]">Welcome, {{ booking.data.value.guest_name }}.</h1>
        <p class="mt-3 text-[var(--muted)]">Booking {{ booking.data.value.reference }} · <span class="badge">{{ booking.data.value.status.replaceAll('_', ' ') }}</span></p>
        <div class="grid md:grid-cols-2 gap-5 mt-8">
          <div class="card stay-room p-6">
            <span class="label">Your room</span>
            <h2 class="text-2xl text-[var(--brand-text)]">{{ booking.data.value.room_type }} · {{ booking.data.value.room }}</h2>
            <p class="mt-3">{{ booking.data.value.arrival }} → {{ booking.data.value.departure }}</p>
            <p class="mt-3 text-sm text-[var(--muted)]">Please collect your physical key at reception. QR entry is for booking verification only.</p>
          </div>
          <div class="card folio-sheet p-6">
            <div class="flex items-center justify-between">
              <span class="label mb-0">Folio · {{ booking.data.value.currency }}</span>
              <button
                type="button"
                class="text-xs text-[var(--muted)] hover:text-[var(--brand-text)] underline cursor-pointer flex items-center gap-1"
                @click="printReceipt"
              >
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                <span>Print receipt</span>
              </button>
            </div>
            <h2 class="text-2xl mt-2">Balance {{ money(booking.data.value.balance_minor) }}</h2>
            <p v-for="(entry, index) in booking.data.value.entries" :key="index" class="flex justify-between mt-2 text-sm">
              <span>{{ entry.description }} · {{ entry.service_date }}</span><span>{{ money(entry.amount_minor) }}</span>
            </p>
            <button v-if="booking.data.value.balance_minor > 0" class="btn mt-5" :disabled="busy" @click="pay">{{ booking.data.value.payment_provider === 'bakong' ? 'Pay with Bakong' : 'Pay balance (simulation)' }}</button>
          </div>
        </div>

        <div v-if="booking.data.value.status === 'CONFIRMED'" class="card stay-action p-6 mt-5">
          <h2 class="text-2xl">Ready to arrive?</h2>
          <p class="text-sm text-[var(--muted)] mt-2">{{ booking.data.value.presentation_demo ? 'University demo: simulate verification for the booking created in this browser.' : 'Verify by email or in person at reception before check-in.' }}</p>
          <button v-if="booking.data.value.presentation_demo && !booking.data.value.verified" class="btn mt-4" :disabled="busy" @click="act(() => api(`/reservations/${id}/demo-verify`, {}))">Verify demo booking</button>
          <RouterLink v-else-if="!booking.data.value.presentation_demo" class="btn inline-flex mt-4" to="/verify">Verify booking</RouterLink>
          <button v-if="eligibleToday" class="btn-secondary ml-3" :disabled="busy" @click="act(() => api(`/reservations/${id}/check-in`, {}))">Check in</button>
          <p v-else-if="booking.data.value.verified && booking.data.value.hotel_today < booking.data.value.arrival" class="text-sm mt-4 text-[var(--muted)]">Check-in opens on {{ booking.data.value.arrival }} ({{ booking.data.value.hotel_timezone }}).</p>
          <p v-else-if="booking.data.value.verified && booking.data.value.hotel_today >= booking.data.value.departure" class="text-sm mt-4 text-[var(--muted)]">Your arrival window has passed. Please contact reception.</p>
        </div>

        <div v-if="booking.data.value.status === 'CHECKED_IN'" class="card stay-action p-6 mt-5">
          <h2 class="text-2xl">Enjoy your stay</h2>
          <p class="mt-2 text-[var(--muted)]">Need anything? Let us know.</p>
          <form class="flex flex-col gap-3 mt-4" @submit.prevent="sendRequest">
            <select v-model="requestType" class="field" aria-label="Service type">
              <option>Towels</option><option>Cleaning</option><option>Maintenance</option><option>Reception</option>
            </select>
            <input v-model="description" class="field" placeholder="How can we help?" aria-label="How can we help?" required />
            <button class="btn-secondary">Send request</button>
            <Notice :message="requestError" />
          </form>
          <p v-for="request in booking.data.value.requests" :key="request.id" class="border-t border-[var(--line)] mt-3 pt-3 flex items-center justify-between">
            <span>{{ request.type }}: {{ request.description }}</span> <span class="badge">{{ request.status }}</span>
          </p>
          <button class="btn mt-6" :disabled="busy || booking.data.value.balance_minor > 0" @click="act(() => api(`/reservations/${id}/check-out`, { folio_version: booking.data.value?.folio_version }))">Check out</button>
          <p v-if="booking.data.value.balance_minor > 0" class="text-sm mt-2 text-[var(--muted)]">Settle your balance before checkout.</p>
        </div>

        <div v-if="booking.data.value.status === 'CHECKED_OUT'" class="card receipt-panel p-8 mt-5">
          <h2 class="text-2xl">Thank you for staying with us.</h2>
          <p class="mt-2 text-[var(--muted)]">Your stay is complete and all folio records are settled. Click below to print or save your official guest folio receipt.</p>
          <button class="btn mt-5 flex items-center gap-2 cursor-pointer" @click="printReceipt">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            <span>Print official receipt</span>
          </button>
        </div>
        <MyDataPanel :booking-id="id" :verified="booking.data.value.verified" />
        <Notice :message="message" :status="!failed" />
      </div>
    </div>

    <!-- Official Printable Guest Folio Receipt (Shown ONLY when printing) -->
    <PrintableReceipt v-if="booking.data.value" :booking="booking.data.value" />
  </SiteLayout>
</template>

