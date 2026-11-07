<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import MyDataPanel from './components/MyDataPanel.vue'
import PrintableReceipt from './components/PrintableReceipt.vue'
import { api } from '../../services/api'
import { roomPhotoFor } from '../../data/roomCatalog'
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
const nights = computed(() => {
  const data = booking.data.value
  if (!data) return 0
  return Math.max(0, Math.round((Date.parse(data.departure) - Date.parse(data.arrival)) / 86_400_000))
})
const roomPhoto = computed(() => roomPhotoFor(booking.data.value?.room_type ?? ''))
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
    <div class="screen-only print:hidden">
      <div v-if="booking.isPending.value" role="status" class="bk-wrap">
        <p>Loading your stay…</p>
        <div class="skeleton h-10 w-72 mt-4" />
        <div class="skeleton h-48 w-full mt-6" />
      </div>
      <Notice v-else-if="booking.error.value" :message="String(booking.error.value)" />
      <div v-else-if="booking.data.value" class="bk-wrap bk-grid">
        <div class="bk-main">
          <h1 class="bk-title">Welcome, {{ booking.data.value.guest_name }}.</h1>
          <p class="bk-ref">Booking {{ booking.data.value.reference }} <span class="badge">{{ booking.data.value.status.replaceAll('_', ' ') }}</span></p>

          <section class="bk-panel" aria-label="Folio">
            <div class="bk-panel-head">
              <h2>Folio in {{ booking.data.value.currency }}</h2>
              <button type="button" class="bk-link" @click="printReceipt"><span>Print receipt</span></button>
            </div>
            <p class="bk-balance">Balance {{ money(booking.data.value.balance_minor) }}</p>
            <p v-for="(entry, index) in booking.data.value.entries" :key="index" class="bk-entry">
              <span>{{ entry.description }}, {{ entry.service_date }}</span><span>{{ money(entry.amount_minor) }}</span>
            </p>
            <button v-if="booking.data.value.balance_minor > 0" class="btn mt-5" :disabled="busy" @click="pay">{{ booking.data.value.payment_provider === 'bakong' ? 'Pay with Bakong' : 'Pay balance (simulation)' }}</button>
          </section>

          <section v-if="booking.data.value.status === 'CONFIRMED'" class="bk-panel">
            <h2>Ready to arrive?</h2>
            <p class="bk-muted">{{ booking.data.value.presentation_demo ? 'University demo: simulate verification for the booking created in this browser.' : 'Verify by email or in person at reception before check-in.' }}</p>
            <div class="bk-actions">
              <button v-if="booking.data.value.presentation_demo && !booking.data.value.verified" class="btn" :disabled="busy" @click="act(() => api(`/reservations/${id}/demo-verify`, {}))">Verify demo booking</button>
              <RouterLink v-else-if="!booking.data.value.presentation_demo" class="btn inline-flex" to="/verify">Verify booking</RouterLink>
              <button v-if="eligibleToday" class="btn-secondary" :disabled="busy" @click="act(() => api(`/reservations/${id}/check-in`, {}))">Check in</button>
            </div>
            <p v-if="!eligibleToday && booking.data.value.verified && booking.data.value.hotel_today < booking.data.value.arrival" class="bk-muted mt-4">Check-in opens on {{ booking.data.value.arrival }} ({{ booking.data.value.hotel_timezone }}).</p>
            <p v-else-if="!eligibleToday && booking.data.value.verified && booking.data.value.hotel_today >= booking.data.value.departure" class="bk-muted mt-4">Your arrival window has passed. Please contact reception.</p>
          </section>

          <section v-if="booking.data.value.status === 'CHECKED_IN'" class="bk-panel">
            <h2>Enjoy your stay</h2>
            <p class="bk-muted">Need anything? Let us know.</p>
            <form class="flex flex-col gap-3 mt-4" @submit.prevent="sendRequest">
              <select v-model="requestType" class="field" aria-label="Service type">
                <option>Towels</option><option>Cleaning</option><option>Maintenance</option><option>Reception</option>
              </select>
              <input v-model="description" class="field" placeholder="How can we help?" aria-label="How can we help?" required />
              <button class="btn-secondary">Send request</button>
              <Notice :message="requestError" />
            </form>
            <p v-for="request in booking.data.value.requests" :key="request.id" class="bk-entry bk-request">
              <span>{{ request.type }}: {{ request.description }}</span> <span class="badge">{{ request.status }}</span>
            </p>
            <button class="btn mt-6" :disabled="busy || booking.data.value.balance_minor > 0" @click="act(() => api(`/reservations/${id}/check-out`, { folio_version: booking.data.value?.folio_version }))">Check out</button>
            <p v-if="booking.data.value.balance_minor > 0" class="bk-muted mt-2">Settle your balance before checkout.</p>
          </section>

          <section v-if="booking.data.value.status === 'CHECKED_OUT'" class="bk-panel">
            <h2>Thank you for staying with us.</h2>
            <p class="bk-muted">Your stay is complete and all folio records are settled. Print or save your official guest folio receipt below.</p>
            <button class="btn mt-5" @click="printReceipt">Print official receipt</button>
          </section>

          <MyDataPanel :booking-id="id" :verified="booking.data.value.verified" />
          <Notice :message="message" :status="!failed" />
        </div>

        <aside class="bk-summary" aria-label="Your stay">
          <img :src="roomPhoto.src" :alt="roomPhoto.alt" width="400" height="300" class="bk-thumb" />
          <h2 class="bk-room">{{ booking.data.value.room_type }}</h2>
          <p class="bk-muted">Room {{ booking.data.value.room }}</p>
          <dl class="bk-facts">
            <div><dt>Arrive</dt><dd>{{ booking.data.value.arrival }}</dd></div>
            <div><dt>Depart</dt><dd>{{ booking.data.value.departure }}</dd></div>
            <div><dt>Nights</dt><dd>{{ nights }}</dd></div>
            <div><dt>Balance</dt><dd class="bk-total">{{ money(booking.data.value.balance_minor) }}</dd></div>
          </dl>
          <p class="bk-muted">Collect your room key at reception. The QR code is for booking verification only.</p>
        </aside>
      </div>
    </div>

    <PrintableReceipt v-if="booking.data.value" :booking="booking.data.value" />
  </SiteLayout>
</template>

<style scoped>
.bk-wrap { max-width: 64rem; margin: 0 auto; padding: 1.5rem 0 2rem; }
.bk-grid { display: grid; gap: 2rem; }
.bk-main { display: grid; gap: 1.25rem; align-content: start; max-width: 560px; }
.bk-title { font-size: 3.0625rem; color: var(--river); }
.bk-ref { color: var(--silt); }
.bk-panel { padding: 1.5rem; background: var(--paper); border-radius: var(--radius-panel); border: 1px solid var(--rule); }
.bk-panel h2 { font-size: 1.9375rem; color: var(--river); }
.bk-panel-head { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
.bk-link { min-height: 44px; display: inline-flex; align-items: center; color: var(--silt); text-decoration: underline; font-size: .875rem; }
.bk-balance { margin: .5rem 0; font: 400 1.9375rem/1.2 var(--font-display); color: var(--laterite); font-variant-numeric: tabular-nums; }
.bk-entry { display: flex; justify-content: space-between; gap: 1rem; padding: .6rem 0; border-top: 1px solid var(--rule); font-size: .9375rem; font-variant-numeric: tabular-nums; }
.bk-request { align-items: center; }
.bk-muted { color: var(--silt); font-size: .9375rem; margin-top: .5rem; }
.bk-actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1rem; }
.bk-summary { align-self: start; padding: 1rem; background: var(--paper); border-radius: var(--radius-panel); border: 1px solid var(--rule); display: grid; gap: .5rem; }
.bk-thumb { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: var(--radius-photo); }
.bk-room { font-size: 1.9375rem; color: var(--river); margin-top: .5rem; }
.bk-facts { display: grid; gap: .25rem; margin: .5rem 0; }
.bk-facts > div { display: flex; justify-content: space-between; padding: .5rem 0; border-top: 1px solid var(--rule); font-size: .9375rem; }
.bk-facts dt { color: var(--silt); }
.bk-total { color: var(--laterite); font-weight: 600; font-size: 1.25rem; font-variant-numeric: tabular-nums; }
@media (min-width: 900px) {
  .bk-grid { grid-template-columns: minmax(0, 560px) 340px; justify-content: space-between; }
  .bk-summary { position: sticky; top: 96px; }
}
</style>
