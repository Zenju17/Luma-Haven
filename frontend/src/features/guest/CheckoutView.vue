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
  reservation_id: number; expires_at: string | null; qr?: string; checkout_url: string; scan_amount_minor?: number
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

const copied = ref(false)
const checking = ref(false)

async function copyQrString() {
  if (!checkout.data.value?.qr) return
  try {
    await navigator.clipboard.writeText(checkout.data.value.qr)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // fallback if clipboard unavailable
  }
}

async function checkPaymentNow() {
  checking.value = true
  error.value = ''
  try {
    const result = await checkout.refetch()
    if (result.data?.status === 'SUCCESS' && checkout.data.value) {
      await router.push(`/booking/${checkout.data.value.reservation_id}`)
    }
  } catch (caught) {
    error.value = String(caught)
  } finally {
    checking.value = false
  }
}

async function simulate(outcome: 'SUCCESS' | 'FAILED' | 'PENDING' = 'SUCCESS') {
  pending.value = true
  error.value = ''
  try {
    const url = checkout.data.value?.provider === 'development'
      ? `/development/checkout/${id.value}`
      : `/payment-sessions/${id.value}/simulate`
    const result = await api<{ status: string; reservation_id?: number }>(url, { outcome })
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
    <div class="co">
      <div class="co-head">
        <span v-if="checkout.data.value?.provider === 'bakong'" class="co-tag">Bakong KHQR</span>
        <span v-else class="badge">Simulated payment · development only</span>
        <span v-if="checkout.data.value?.status === 'PENDING'" class="co-time" aria-label="Time left">{{ countdown }}</span>
      </div>

      <h1 class="co-title">{{ checkout.data.value?.provider === 'bakong' ? 'Scan to Pay' : 'Simulated checkout' }}</h1>
      <p v-if="checkout.data.value?.provider === 'bakong'" class="co-muted">
        Pay in USD with any Cambodian banking app that supports the National Bank of Cambodia KHQR standard.
      </p>

      <div v-if="checkout.isPending.value" class="mt-6" role="status">
        <p>Loading payment session…</p>
        <div class="skeleton h-12 w-full mt-4" />
      </div>
      <Notice v-else-if="checkout.error.value" :message="String(checkout.error.value)" />
      <template v-else-if="checkout.data.value">
        <div class="co-amount">
          <span>Total payable</span>
          <strong>{{ money(checkout.data.value.amount_minor) }} {{ checkout.data.value.currency }}</strong>
        </div>
        <p class="co-muted">Status: <span class="co-status">{{ checkout.data.value.status }}</span></p>
        <Notice :message="error" />

        <template v-if="checkout.data.value.provider === 'bakong'">
          <div v-if="checkout.data.value.status === 'PENDING' && checkout.data.value.qr" class="co-pay">
            <div class="co-qr">
              <QrcodeVue :value="checkout.data.value.qr" :size="230" level="M" render-as="svg" />
              <p class="co-qr-name">Luma Haven</p>
              <p class="co-qr-note">Room total {{ money(checkout.data.value.amount_minor) }} USD. Scan-to-pay: $0.01 USD</p>
            </div>

            <p class="co-note">
              <strong>Scan test:</strong> scan with ABA Mobile or Bakong to pay <strong>$0.01 USD</strong>, or use the button below to simulate without real cash.
            </p>
            <p class="co-muted">Accepted by Bakong, ABA Mobile, ACLEDA, Wing, Canadia, Sathapana and 40+ members.</p>

            <div class="co-actions">
              <button type="button" class="btn" :disabled="pending" @click="simulate('SUCCESS')">
                {{ pending ? 'Confirming booking…' : 'Simulate payment (no charge)' }}
              </button>
              <button type="button" class="btn-secondary" :disabled="checking" @click="checkPaymentNow">
                {{ checking ? 'Checking status…' : "I've paid $0.01 in my bank app" }}
              </button>
              <button type="button" class="btn-secondary" @click="copyQrString">
                {{ copied ? 'KHQR payload copied' : 'Copy KHQR payload' }}
              </button>
            </div>

            <p class="co-live" role="status">Waiting for payment… We check every 4 seconds.</p>
          </div>
          <div v-else-if="checkout.data.value.status === 'EXPIRED' || checkout.data.value.status === 'FAILED'" class="mt-6">
            <p>This QR code has expired. If you have already paid, the hotel front desk will confirm your stay automatically.</p>
            <button class="btn mt-4 w-full" :disabled="pending" @click="newQr">Generate new KHQR</button>
          </div>
          <p v-else-if="checkout.data.value.status === 'EXCEPTION'" class="mt-6">We received your payment and our reception team is reviewing it. Your booking is safe.</p>
        </template>

        <div v-else class="co-actions co-actions--row">
          <button class="btn" :disabled="pending" @click="simulate('SUCCESS')">Simulate success</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('FAILED')">Simulate failure</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('PENDING')">Simulate pending</button>
        </div>
        <RouterLink to="/verify" class="co-verify">Verify booking or enter OTP</RouterLink>
      </template>
    </div>
  </SiteLayout>
</template>

<style scoped>
.co { max-width: 560px; margin: 1.5rem auto 2rem; padding: 1.5rem; background: var(--paper); border: 1px solid var(--rule); border-radius: var(--radius-panel); }
.co-head { display: flex; justify-content: space-between; align-items: center; gap: 1rem; min-height: 28px; }
.co-tag { font-weight: 600; color: var(--status-out); }
.co-time { font-variant-numeric: tabular-nums; color: var(--silt); }
.co-title { font-size: 2.4375rem; color: var(--river); margin-top: .5rem; }
.co-muted { color: var(--silt); font-size: .875rem; margin-top: .35rem; }
.co-status { color: var(--river); font-weight: 600; }
.co-amount { margin-top: 1.25rem; padding: 1rem 0; border-block: 1px solid var(--rule); display: grid; gap: .15rem; color: var(--silt); }
.co-amount strong { font: 400 3.0625rem/1 var(--font-display); color: var(--laterite); font-variant-numeric: tabular-nums; }
.co-pay { display: grid; gap: 1rem; margin-top: 1.25rem; justify-items: center; text-align: center; }
.co-qr { background: #fff; color: #1a1a1a; padding: 1.25rem; border-radius: var(--radius-photo); display: grid; justify-items: center; gap: .35rem; }
.co-qr-name { font-weight: 600; }
.co-qr-note { font-size: .8125rem; color: #555; }
.co-note { font-size: .9375rem; color: var(--river); text-align: left; }
.co-actions { display: grid; gap: .6rem; width: 100%; }
.co-actions--row { margin-top: 1.5rem; grid-auto-flow: row; }
.co-live { color: var(--silt); font-size: .875rem; }
.co-verify { display: flex; justify-content: center; align-items: center; min-height: 44px; margin-top: 1rem; color: var(--silt); text-decoration: underline; font-size: .875rem; }
@media (min-width: 640px) { .co-actions--row { grid-auto-flow: column; } }
</style>
