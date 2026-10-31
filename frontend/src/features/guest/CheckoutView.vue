<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import QrcodeVue from 'qrcode.vue'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import { money } from '../../types'

interface Session {
  id: string; provider: 'development' | 'bakong'; status: string; amount_minor: number; currency: string
  reservation_id: number; expires_at: string | null; qr?: string; checkout_url: string
}
const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id))
const terminal = ['SUCCESS', 'EXPIRED', 'FAILED', 'EXCEPTION']
// The server asks Bakong; the browser only re-reads our own API. Stop polling once the attempt is settled.
const checkout = useQuery({
  queryKey: computed(() => ['checkout', id.value]),
  queryFn: () => api<Session>(`/payment-sessions/${id.value}`),
  refetchInterval: query => {
    const data = query.state.data
    return data && data.provider === 'bakong' && !terminal.includes(data.status) ? 4000 : false
  },
})
const error = ref('')
const pending = ref(false)
const now = ref(Date.now())
const timer = setInterval(() => { now.value = Date.now() }, 1000)
onBeforeUnmount(() => clearInterval(timer))

const secondsLeft = computed(() => {
  const expires = checkout.data.value?.expires_at
  return expires ? Math.max(0, Math.floor((new Date(expires).getTime() - now.value) / 1000)) : 0
})
const countdown = computed(() => `${Math.floor(secondsLeft.value / 60)}:${String(secondsLeft.value % 60).padStart(2, '0')}`)

watch(() => checkout.data.value?.status, status => {
  if (status === 'SUCCESS' && checkout.data.value) void router.push(`/booking/${checkout.data.value.reservation_id}`)
})

async function simulate(outcome: 'SUCCESS' | 'FAILED' | 'PENDING') {
  pending.value = true
  error.value = ''
  try {
    const result = await api<{ status: string }>(`/development/checkout/${id.value}`, { outcome })
    if (outcome === 'SUCCESS' && result.status === 'SUCCESS' && checkout.data.value) {
      await router.push(`/booking/${checkout.data.value.reservation_id}`)
    } else {
      await checkout.refetch()
    }
  } catch (caught) {
    error.value = String(caught)
  } finally {
    pending.value = false
  }
}

async function newQr() {
  if (!checkout.data.value) return
  pending.value = true
  error.value = ''
  try {
    const next = await api<Session>(`/reservations/${checkout.data.value.reservation_id}/payment-sessions`, {})
    await router.push(next.checkout_url)
  } catch (caught) {
    error.value = String(caught)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <SiteLayout>
    <div class="card payment-panel p-8 max-w-lg mx-auto animate-[slideUp_0.4s_cubic-bezier(0.16,1,0.3,1)_both]">
      <div class="flex items-center gap-2.5 mb-3">
        <img src="/images/luma-haven/branding/logo.png" alt="Luma Haven Logo" class="w-7 h-7 object-contain" />
        <span v-if="checkout.data.value?.provider === 'bakong'" class="badge">Bakong KHQR</span>
        <span v-else class="badge">Simulated payment · development only</span>
      </div>
      <h1 class="text-3xl text-[var(--brand-text)]">{{ checkout.data.value?.provider === 'bakong' ? 'Pay with Bakong' : 'Simulated checkout' }}</h1>
      <div v-if="checkout.isPending.value" class="mt-6 space-y-4" role="status">
        <p>Loading payment session…</p>
        <div class="skeleton h-8 w-48 rounded-md"></div>
        <div class="skeleton h-12 w-full rounded-md mt-4"></div>
      </div>
      <Notice v-else-if="checkout.error.value" :message="String(checkout.error.value)" />
      <template v-else-if="checkout.data.value">
        <p class="mt-4">Amount: <strong>{{ money(checkout.data.value.amount_minor) }} {{ checkout.data.value.currency }}</strong></p>
        <p class="mt-2 text-[var(--muted)]">Status: <span class="font-semibold text-[var(--ink)]">{{ checkout.data.value.status }}</span></p>
        <Notice :message="error" />

        <template v-if="checkout.data.value.provider === 'bakong'">
          <div v-if="checkout.data.value.status === 'PENDING' && checkout.data.value.qr" class="mt-6 flex flex-col items-center gap-3">
            <div class="bg-white p-4 rounded-xl">
              <QrcodeVue :value="checkout.data.value.qr" :size="240" level="M" render-as="svg" />
            </div>
            <p class="text-sm text-[var(--muted)]">Scan with any Cambodian banking app that supports KHQR.</p>
            <p class="font-mono text-lg" role="timer" aria-live="off">Expires in {{ countdown }}</p>
            <p class="text-xs text-[var(--muted)]" role="status">Waiting for payment confirmation… this page updates automatically.</p>
          </div>
          <div v-else-if="checkout.data.value.status === 'EXPIRED' || checkout.data.value.status === 'FAILED'" class="mt-6">
            <p class="text-sm">This QR code is no longer valid. Do not pay it. If you already paid, the hotel will confirm your booking automatically or contact you.</p>
            <button class="btn mt-4" :disabled="pending" @click="newQr">Create a new QR code</button>
          </div>
          <p v-else-if="checkout.data.value.status === 'EXCEPTION'" class="mt-6 text-sm">We received your payment but need to review it. The hotel will contact you shortly.</p>
        </template>

        <div v-else class="flex flex-wrap gap-3 mt-8">
          <button class="btn" :disabled="pending" @click="simulate('SUCCESS')">Simulate success</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('FAILED')">Simulate failure</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('PENDING')">Simulate pending</button>
        </div>
        <RouterLink to="/verify" class="block mt-6 text-sm text-[var(--muted)] hover:text-[var(--ink)] underline">Verify booking after payment</RouterLink>
      </template>
    </div>
  </SiteLayout>
</template>
