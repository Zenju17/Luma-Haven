<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { staffApi, queryClient } from '../../services/api'
import {
  money,
  type AccountantPayment,
  type ReconciliationItem,
  type RefundRecord
} from '../../types'

const props = defineProps<{
  userRole: string
  username: string
}>()

const busy = ref(false)
const error = ref('')
const successNotice = ref('')
const activeTab = ref<'reconciliation' | 'ledger' | 'refunds'>('reconciliation')

// Payment Ledger Filter
const paymentStatus = ref<'ALL' | 'SETTLED' | 'PENDING' | 'FAILED' | 'EXCEPTION'>('ALL')

// Data Queries
const reconciliation = useQuery({
  queryKey: ['accountant-reconciliation'],
  queryFn: () => staffApi<ReconciliationItem[]>('/accountant/reconciliation'),
})

const payments = useQuery({
  queryKey: computed(() => ['accountant-payments', paymentStatus.value]),
  queryFn: () => staffApi<AccountantPayment[]>(`/accountant/payments?status=${paymentStatus.value}`),
})

const refunds = useQuery({
  queryKey: ['accountant-refunds'],
  queryFn: () => staffApi<RefundRecord[]>('/staff/refunds'),
})

const approvedRefunds = computed(() => {
  return (refunds.data.value || []).filter(r => r.status === 'APPROVED')
})

const unbalancedFolios = computed(() => {
  return (reconciliation.data.value || []).filter(r => !r.is_balanced)
})

async function reconcileFolio(reservationId: number, refCode: string) {
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/accountant/folios/${reservationId}/reconcile`, {})
    successNotice.value = `Folio for ${refCode} reconciled and logged to audit trail.`
    await queryClient.invalidateQueries({ queryKey: ['accountant-reconciliation'] })
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

async function settleRefund(refundId: number) {
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/staff/refunds/${refundId}/settle`, {})
    successNotice.value = `Refund settled successfully and recorded to financial ledger.`
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['accountant-refunds'] }),
      queryClient.invalidateQueries({ queryKey: ['accountant-reconciliation'] }),
      queryClient.invalidateQueries({ queryKey: ['accountant-payments'] })
    ])
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-8">
    <Notice :message="error || (reconciliation.error.value ? String(reconciliation.error.value) : '')" />
    <div v-if="successNotice" class="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-sm flex items-center justify-between">
      <span>{{ successNotice }}</span>
      <button class="text-xs font-semibold uppercase hover:underline ml-4" @click="successNotice = ''">Dismiss</button>
    </div>

    <!-- Summary KPI Strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-5">
        <span class="label text-[10px]">Unbalanced Folios</span>
        <p class="text-xl font-serif mt-1" :class="unbalancedFolios.length ? 'text-amber-500 font-bold' : ''">
          {{ unbalancedFolios.length }}
        </p>
        <span class="text-xs text-[var(--muted)]">Require ledger balance</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Approved Refunds</span>
        <p class="text-xl font-serif mt-1" :class="approvedRefunds.length ? 'text-blue-500 font-bold' : ''">
          {{ approvedRefunds.length }}
        </p>
        <span class="text-xs text-[var(--muted)]">Ready for settlement</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Segregation of Duties</span>
        <p class="text-xs font-medium mt-2 text-emerald-600 dark:text-emerald-400">Enforced</p>
        <span class="text-[10px] text-[var(--muted)]">No self-approval or manual charge invention</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Payment Audit Status</span>
        <p class="text-xs font-medium mt-2 text-emerald-600 dark:text-emerald-400">Gateway Synchronized</p>
        <span class="text-[10px] text-[var(--muted)]">Settlement matching active</span>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex items-center gap-2 border-b border-[var(--line)] pb-4">
      <button
        class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
        :class="activeTab === 'reconciliation' ? 'bg-[var(--accent)] text-white' : 'btn-secondary'"
        @click="activeTab = 'reconciliation'"
      >
        Folio Reconciliation
      </button>
      <button
        class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
        :class="activeTab === 'ledger' ? 'bg-[var(--accent)] text-white' : 'btn-secondary'"
        @click="activeTab = 'ledger'"
      >
        Payments Audit Ledger
      </button>
      <button
        class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
        :class="activeTab === 'refunds' ? 'bg-[var(--accent)] text-white' : 'btn-secondary'"
        @click="activeTab = 'refunds'"
      >
        Approved Refunds Settlement ({{ approvedRefunds.length }})
      </button>
    </div>

    <!-- TAB 1: Folio Reconciliation -->
    <section v-if="activeTab === 'reconciliation'" class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-serif">Folio Reconciliation & Financial Audit</h2>
          <p class="text-xs text-[var(--muted)] mt-1">Cross-check ledger entries, settled transactions, and calculate outstanding variance.</p>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-[var(--line)] text-[var(--muted)]">
              <th class="py-3 px-2">Reference</th>
              <th class="py-3 px-2">Guest</th>
              <th class="py-3 px-2">Stay Dates</th>
              <th class="py-3 px-2 text-right">Charges</th>
              <th class="py-3 px-2 text-right">Settled</th>
              <th class="py-3 px-2 text-right">Refunds</th>
              <th class="py-3 px-2 text-right">Balance</th>
              <th class="py-3 px-2 text-center">Status</th>
              <th class="py-3 px-2 text-right">Audit Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--line)]">
            <tr v-for="item in reconciliation.data.value || []" :key="item.reservation_id" class="hover:bg-[var(--card)]/80">
              <td class="py-3 px-2 font-mono font-bold">{{ item.reference }}</td>
              <td class="py-3 px-2">{{ item.guest_name }}</td>
              <td class="py-3 px-2 text-[var(--muted)]">{{ item.arrival }} → {{ item.departure }}</td>
              <td class="py-3 px-2 text-right font-mono">{{ money(item.charges_minor) }}</td>
              <td class="py-3 px-2 text-right font-mono text-emerald-600">{{ money(item.settled_minor) }}</td>
              <td class="py-3 px-2 text-right font-mono text-rose-500">{{ money(item.refunds_minor) }}</td>
              <td class="py-3 px-2 text-right font-mono font-bold" :class="item.balance_minor === 0 ? 'text-emerald-600' : 'text-rose-500'">
                {{ money(item.balance_minor) }}
              </td>
              <td class="py-3 px-2 text-center">
                <span
                  class="badge text-[10px]"
                  :class="item.is_balanced ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30' : 'bg-rose-500/10 text-rose-500 border-rose-500/30'"
                >
                  {{ item.is_balanced ? 'Balanced' : 'Discrepancy' }}
                </span>
              </td>
              <td class="py-3 px-2 text-right">
                <button
                  class="btn-secondary text-[11px] py-1 px-3"
                  :disabled="busy || !item.is_balanced"
                  @click="reconcileFolio(item.reservation_id, item.reference)"
                >
                  Audit Folio ✓
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- TAB 2: Payments Audit Ledger -->
    <section v-if="activeTab === 'ledger'" class="card p-6">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="text-2xl font-serif">Payments Audit Ledger</h2>
          <p class="text-xs text-[var(--muted)] mt-1">Immutable record of all processed, failed, and exception payment events.</p>
        </div>
        <div class="flex items-center gap-1 border border-[var(--line)] rounded-lg p-1 bg-[var(--card)]">
          <button
            v-for="st in ['ALL', 'SETTLED', 'PENDING', 'FAILED', 'EXCEPTION'] as const"
            :key="st"
            class="px-2.5 py-1 text-[11px] rounded transition-colors"
            :class="paymentStatus === st ? 'bg-[var(--line)] font-bold' : 'text-[var(--muted)]'"
            @click="paymentStatus = st"
          >
            {{ st }}
          </button>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-[var(--line)] text-[var(--muted)]">
              <th class="py-3 px-2">Payment ID</th>
              <th class="py-3 px-2">Booking Ref</th>
              <th class="py-3 px-2">Guest</th>
              <th class="py-3 px-2">Gateway Ref</th>
              <th class="py-3 px-2 text-right">Amount</th>
              <th class="py-3 px-2 text-center">Status</th>
              <th class="py-3 px-2">Settled At</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--line)]">
            <tr v-for="p in payments.data.value || []" :key="p.id" class="hover:bg-[var(--card)]/80">
              <td class="py-3 px-2 font-mono">#{{ p.id }}</td>
              <td class="py-3 px-2 font-mono font-bold">{{ p.reference }}</td>
              <td class="py-3 px-2">{{ p.guest_name }}</td>
              <td class="py-3 px-2 font-mono text-[11px] text-[var(--muted)]">{{ p.gateway_reference || 'N/A' }}</td>
              <td class="py-3 px-2 text-right font-mono font-bold">{{ money(p.amount_minor) }}</td>
              <td class="py-3 px-2 text-center">
                <span
                  class="badge text-[10px]"
                  :class="{
                    'bg-emerald-500/10 text-emerald-600': p.status === 'SETTLED',
                    'bg-amber-500/10 text-amber-500': p.status === 'PENDING',
                    'bg-rose-500/10 text-rose-500': p.status === 'FAILED',
                    'bg-purple-500/10 text-purple-500': p.status === 'EXCEPTION'
                  }"
                >
                  {{ p.status }}
                </span>
              </td>
              <td class="py-3 px-2 text-[var(--muted)] text-[11px]">
                {{ p.settled_at ? new Date(p.settled_at).toLocaleString() : 'Pending' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- TAB 3: Approved Refunds Settlement Queue -->
    <section v-if="activeTab === 'refunds'" class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-serif">Manager-Approved Refunds Queue</h2>
          <p class="text-xs text-[var(--muted)] mt-1">Disburse settled funds for refunds reviewed and authorized by Management.</p>
        </div>
        <span class="badge">{{ approvedRefunds.length }} pending settlement</span>
      </div>

      <div v-if="approvedRefunds.length === 0" class="py-12 text-center text-sm text-[var(--muted)]">
        No approved refunds waiting for settlement.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="rf in approvedRefunds"
          :key="rf.id"
          class="p-4 rounded-xl border border-[var(--line)] bg-[var(--card)]/60 flex flex-wrap items-center justify-between gap-4"
        >
          <div class="space-y-1">
            <div class="flex items-center gap-3">
              <span class="font-bold text-base">{{ money(rf.amount_minor) }}</span>
              <span class="badge text-[10px] font-mono">{{ rf.reservation_reference }}</span>
              <span class="badge text-[10px] bg-blue-500/10 text-blue-600 border-blue-500/30">APPROVED</span>
            </div>
            <p class="text-xs text-[var(--muted)]">Guest: {{ rf.guest_name }} · Reason: "{{ rf.reason }}"</p>
            <p class="text-[10px] text-[var(--muted)]">
              Requested by: {{ rf.requested_by || 'Staff' }} · Authorized by: {{ rf.reviewed_by || 'Manager' }}
            </p>
          </div>

          <button
            class="btn text-xs py-2 px-4"
            :disabled="busy"
            @click="settleRefund(rf.id)"
          >
            Settle Refund Disbursal →
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
