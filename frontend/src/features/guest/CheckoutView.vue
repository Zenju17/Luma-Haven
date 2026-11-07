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
    <div class="card payment-panel p-8 max-w-lg mx-auto">
      <div class="flex items-center justify-between gap-2.5 mb-3">
        <div class="flex items-center gap-2.5">
          <img src="/images/luma-haven/branding/logo.png" alt="Luma Haven Logo" class="w-7 h-7 object-contain" />
          <span v-if="checkout.data.value?.provider === 'bakong'" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">
            <span class="w-2 h-2 rounded-full bg-rose-600 animate-pulse"></span>
            Bakong KHQR
          </span>
          <span v-else class="badge">Simulated payment · development only</span>
        </div>
        <span v-if="checkout.data.value?.status === 'PENDING'" class="text-xs font-mono text-[var(--muted)]">
          {{ countdown }}
        </span>
      </div>

      <h1 class="text-3xl text-[var(--brand-text)]">{{ checkout.data.value?.provider === 'bakong' ? 'Scan to Pay' : 'Simulated checkout' }}</h1>
      <p v-if="checkout.data.value?.provider === 'bakong'" class="text-xs text-[var(--muted)] mt-1">
        Pay in USD with any Cambodian banking app that supports the National Bank of Cambodia KHQR standard.
      </p>

      <div v-if="checkout.isPending.value" class="mt-6 space-y-4" role="status">
        <p>Loading payment session…</p>
        <div class="skeleton h-8 w-48 rounded-md"></div>
        <div class="skeleton h-12 w-full rounded-md mt-4"></div>
      </div>
      <Notice v-else-if="checkout.error.value" :message="String(checkout.error.value)" />
      <template v-else-if="checkout.data.value">
        <div class="mt-4 p-3 rounded-lg bg-[var(--surface-muted)] flex items-center justify-between">
          <span class="text-sm text-[var(--muted)]">Total payable</span>
          <span class="text-xl font-bold font-mono text-[var(--brand-text)]">
            {{ money(checkout.data.value.amount_minor) }} {{ checkout.data.value.currency }}
          </span>
        </div>
        <p class="mt-2 text-xs text-[var(--muted)]">Status: <span class="font-semibold text-[var(--ink)]">{{ checkout.data.value.status }}</span></p>
        <Notice :message="error" />

        <template v-if="checkout.data.value.provider === 'bakong'">
          <div v-if="checkout.data.value.status === 'PENDING' && checkout.data.value.qr" class="mt-6 flex flex-col items-center gap-3">
            <!-- KHQR Display Card -->
            <div class="relative bg-white p-5 rounded-2xl shadow-md border-2 border-rose-600/30 flex flex-col items-center">
              <div class="w-full flex items-center justify-between border-b pb-2 mb-3">
                <span class="text-[10px] font-bold text-rose-700 tracking-wider uppercase">KHQR Universal</span>
                <div class="text-right">
                  <span class="text-[10px] text-slate-500 font-mono block">Room total: {{ money(checkout.data.value.amount_minor) }} USD</span>
                  <span class="text-[11px] font-bold text-emerald-600 font-mono block">Scan-to-Pay: $0.01 USD</span>
                </div>
              </div>
              <QrcodeVue :value="checkout.data.value.qr" :size="230" level="M" render-as="svg" />
              <div class="mt-3 text-[11px] text-slate-600 font-medium tracking-wide">LUMA HAVEN BOUTIQUE HOTEL</div>
            </div>

            <!-- Scan amount callout badge -->
            <div class="w-full bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-xl p-3 text-center">
              <p class="text-xs font-medium text-emerald-800 dark:text-emerald-300">
                💡 <strong>Scan Test:</strong> Scan with ABA Mobile or Bakong to test paying <strong>$0.01 USD</strong>, or click below to simulate for free without real cash.
              </p>
            </div>

            <!-- Supported Banks pill -->
            <div class="w-full text-center mt-1">
              <p class="text-[11px] text-[var(--muted)]">
                Accepted by <strong>Bakong · ABA Mobile · ACLEDA · Wing · Canadia · Sathapana</strong> & 40+ members
              </p>
            </div>

            <!-- Action buttons -->
            <div class="w-full flex flex-col gap-2.5 mt-2">
              <button
                type="button"
                class="btn w-full flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-700 text-white font-semibold shadow hover:opacity-95"
                :disabled="pending"
                @click="simulate('SUCCESS')"
              >
                <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>{{ pending ? 'Confirming booking…' : '⚡ Simulate Payment (Confirm Free)' }}</span>
              </button>

              <button
                type="button"
                class="btn-secondary w-full flex items-center justify-center gap-2"
                :disabled="checking"
                @click="checkPaymentNow"
              >
                <svg v-if="checking" class="w-4 h-4 animate-spin shrink-0" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
                <span>{{ checking ? 'Checking status…' : "I've paid $0.01 in my bank app" }}</span>
              </button>

              <button
                type="button"
                class="btn-secondary w-full text-xs flex items-center justify-center gap-1.5 opacity-80"
                @click="copyQrString"
              >
                <span>{{ copied ? 'KHQR payload copied! ✓' : 'Copy KHQR payload' }}</span>
              </button>
            </div>

            <p class="text-[11px] text-[var(--muted)] mt-1" role="status">
              Auto-checking for payment confirmation every 4 seconds…
            </p>
          </div>
          <div v-else-if="checkout.data.value.status === 'EXPIRED' || checkout.data.value.status === 'FAILED'" class="mt-6">
            <p class="text-sm">This QR code has expired. If you have already paid, the hotel front desk will confirm your stay automatically.</p>
            <button class="btn mt-4 w-full" :disabled="pending" @click="newQr">Generate new KHQR</button>
          </div>
          <p v-else-if="checkout.data.value.status === 'EXCEPTION'" class="mt-6 text-sm">We received your payment and our reception team is reviewing it. Your booking is safe.</p>
        </template>

        <div v-else class="flex flex-wrap gap-3 mt-8">
          <button class="btn" :disabled="pending" @click="simulate('SUCCESS')">Simulate success</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('FAILED')">Simulate failure</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('PENDING')">Simulate pending</button>
        </div>
        <RouterLink to="/verify" class="block mt-6 text-sm text-[var(--muted)] hover:text-[var(--ink)] underline text-center">Verify booking or enter OTP</RouterLink>
      </template>
    </div>
  </SiteLayout>
</template>
