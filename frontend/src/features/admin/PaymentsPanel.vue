<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { RouterLink } from 'vue-router'
import Notice from '../../components/Notice.vue'
import { adminApi } from '../../services/api'
import { money } from '../../types'

interface Funnel { created: number; SUCCESS: number; EXPIRED: number; FAILED: number; EXCEPTION: number; PENDING: number; abandon_rate_percent: number }
interface Recon {
  gross_cash_minor: number; refunded_cash_minor: number; net_cash_minor: number; payments_count: number; refunds_count: number
  channel_mix: Record<string, { count: number; amount_minor: number }>
  attempt_funnel: Record<string, Funnel>
  payment_exceptions: { id: number; attempt__reservation__reference: string; reason: string; created_at: string }[]
}
const day = (offset = 0) => { const d = new Date(); d.setDate(d.getDate() + offset); return d.toISOString().slice(0, 10) }
const start = ref(day(-6))
const end = ref(day(1))
const report = useQuery({
  queryKey: computed(() => ['admin', 'recon', start.value, end.value]),
  queryFn: () => adminApi<Recon>(`/admin/reports/cash-reconciliation?start=${start.value}&end=${end.value}`),
})
const csv = computed(() => `/api/v1/admin/reports/cash-reconciliation?start=${start.value}&end=${end.value}&export=csv`)
</script>

<template>
  <section aria-label="Payments and reconciliation" class="space-y-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <h2 class="text-2xl">Payments &amp; reconciliation</h2>
      <div class="flex flex-wrap items-end gap-3">
        <label class="label">From<input v-model="start" type="date" class="field mt-1" /></label>
        <label class="label">To (exclusive)<input v-model="end" type="date" class="field mt-1" /></label>
        <a class="btn-secondary" :href="csv">Export CSV</a>
        <RouterLink class="btn-secondary" :to="{ path: '/staff', query: { tab: 'refunds' } }">Refund approvals</RouterLink>
      </div>
    </div>
    <p v-if="report.isPending.value" role="status">Loading…</p>
    <Notice :message="report.error.value ? String(report.error.value) : ''" />
    <template v-if="report.data.value">
      <div class="grid sm:grid-cols-3 gap-4">
        <div class="card p-4"><p class="label">Gross cash</p><p class="text-2xl">{{ money(report.data.value.gross_cash_minor) }}</p><p class="text-xs text-[var(--silt)]">{{ report.data.value.payments_count }} payments</p></div>
        <div class="card p-4"><p class="label">Refunded</p><p class="text-2xl">{{ money(report.data.value.refunded_cash_minor) }}</p><p class="text-xs text-[var(--silt)]">{{ report.data.value.refunds_count }} refunds</p></div>
        <div class="card p-4"><p class="label">Net cash</p><p class="text-2xl">{{ money(report.data.value.net_cash_minor) }}</p></div>
      </div>
      <div class="card overflow-auto">
        <table class="data-table w-full text-left text-sm">
          <caption class="text-left p-3 font-semibold">Payment channels</caption>
          <thead><tr><th>Channel</th><th>Payments</th><th>Amount</th><th>Attempts</th><th>Paid</th><th>Expired</th><th>Failed</th><th>Exception</th><th>Abandon</th></tr></thead>
          <tbody>
            <tr v-for="(f, channel) in report.data.value.attempt_funnel" :key="channel">
              <td>{{ channel }}</td>
              <td>{{ report.data.value.channel_mix[channel]?.count ?? 0 }}</td>
              <td>{{ money(report.data.value.channel_mix[channel]?.amount_minor ?? 0) }}</td>
              <td>{{ f.created }}</td><td>{{ f.SUCCESS }}</td><td>{{ f.EXPIRED }}</td><td>{{ f.FAILED }}</td><td>{{ f.EXCEPTION }}</td><td>{{ f.abandon_rate_percent }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card overflow-auto">
        <table class="data-table w-full text-left text-sm">
          <caption class="text-left p-3 font-semibold">Payment exceptions needing review</caption>
          <thead><tr><th>Booking</th><th>Reason</th><th>Raised</th></tr></thead>
          <tbody>
            <tr v-for="e in report.data.value.payment_exceptions" :key="e.id"><td>{{ e.attempt__reservation__reference }}</td><td>{{ e.reason }}</td><td>{{ e.created_at.slice(0, 16).replace('T', ' ') }}</td></tr>
            <tr v-if="report.data.value.payment_exceptions.length === 0"><td colspan="3" class="text-[var(--silt)]">None in this period.</td></tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>
