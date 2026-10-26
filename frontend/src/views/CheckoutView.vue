<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api, money } from '../lib/api'
import type { CheckoutSession } from '../types'
import Notice from '../components/Notice.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id))

const data = ref<CheckoutSession | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await api<CheckoutSession>(`/development/checkout/${id.value}`)
  } catch (e) {
    error.value = String(e)
  }
})

async function pay(outcome: string) {
  try {
    const result = await api<{ status: string }>(`/development/checkout/${id.value}`, { outcome })
    if (data.value) data.value.status = result.status
    if (outcome === 'SUCCESS' && result.status === 'SUCCESS') {
      router.push(`/booking/${data.value?.reservation_id}`)
    }
  } catch (e) {
    error.value = String(e)
  }
}
</script>

<template>
  <div class="card p-8 max-w-lg mx-auto">
    <span class="badge">DEVELOPMENT SIMULATION · No real money moves</span>
    <h1 class="text-3xl mt-4">Simulated checkout</h1>
    <p class="mt-4">
      Amount:
      <strong>{{ data ? money(data.amount_minor) : '' }} {{ data?.currency }}</strong>
    </p>
    <p class="mt-2">Status: {{ data?.status }}</p>
    <Notice :error="error" />
    <div class="flex flex-wrap gap-3 mt-8">
      <button class="btn" @click="pay('SUCCESS')">Simulate success</button>
      <button class="btn-secondary" @click="pay('FAILED')">Simulate failure</button>
      <button class="btn-secondary" @click="pay('PENDING')">Simulate pending</button>
    </div>
    <RouterLink to="/verify" class="block mt-6 underline">
      Verify booking after payment →
    </RouterLink>
  </div>
</template>
