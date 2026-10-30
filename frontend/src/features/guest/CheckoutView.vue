<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import { money } from '../../types'

interface Checkout { amount_minor: number; currency: string; status: string; reservation_id: number }
const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id))
const checkout = useQuery({
  queryKey: computed(() => ['checkout', id.value]),
  queryFn: () => api<Checkout>(`/development/checkout/${id.value}`),
})
const error = ref('')
const pending = ref(false)

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
</script>

<template>
  <SiteLayout>
    <div class="card payment-panel p-8 max-w-lg mx-auto animate-[slideUp_0.4s_cubic-bezier(0.16,1,0.3,1)_both]">
      <span class="badge">Simulated payment · development only</span>
      <h1 class="text-3xl mt-4 text-[var(--brand-text)]">Simulated checkout</h1>
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
        <div class="flex flex-wrap gap-3 mt-8">
          <button class="btn" :disabled="pending" @click="simulate('SUCCESS')">Simulate success</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('FAILED')">Simulate failure</button>
          <button class="btn-secondary" :disabled="pending" @click="simulate('PENDING')">Simulate pending</button>
        </div>
        <RouterLink to="/verify" class="block mt-6 text-sm text-[var(--muted)] hover:text-[var(--ink)] underline">Verify booking after payment</RouterLink>
      </template>
    </div>
  </SiteLayout>
</template>
