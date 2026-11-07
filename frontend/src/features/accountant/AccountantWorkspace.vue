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
    <div v-if="successNotice" class="p-4 rounded-xl bg-[var(--status-available)]/10 border border-[var(--status-available)]/30 text-[var(--status-available)] text-sm flex items-center justify-between">
      <span>{{ successNotice }}</span>
      <button class="text-xs font-semibold hover:underline ml-4" @click="successNotice = ''">Dismiss</button>
    </div>

    <!-- Summary KPI Strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-5">
        <span class="label text-[10px]">Unbalanced Folios</span>
        <p class="text-xl font-serif mt-1" :class="unbalancedFolios.length ? 'text-[var(--status-dirty)] font-bold' : ''">
          {{ unbalancedFolios.length }}
        </p>
        <span class="text-xs text-[var(--silt)]">Require ledger balance</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Approved Refunds</span>
        <p class="text-xl font-serif mt-1" :class="approvedRefunds.length ? 'text-[var(--status-occupied)] font-bold' : ''">
          {{ approvedRefunds.length }}
        </p>
        <span class="text-xs text-[var(--silt)]">Ready for settlement</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Segregation of Duties</span>
        <p class="text-xs font-medium mt-2 text-[var(--status-available)] ">Enforced</p>
        <span class="text-[10px] text-[var(--silt)]">No self-approval or manual charge invention</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Payment Audit Status</span>
        <p class="text-xs font-medium mt-2 text-[var(--status-available)] ">Gateway Synchronized</p>
        <span class="text-[10px] text-[var(--silt)]">Settlement matching active</span>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex items-center gap-2 border-b border-[var(--rule)] pb-4">
      <button
        class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
        :class="activeTab === 'reconciliation' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'btn-secondary'"
        @click="activeTab = 'reconciliation'"
      >
        Folio Reconciliation
      </button>
      <button
        class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
        :class="activeTab === 'ledger' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'btn-secondary'"
        @click="activeTab = 'ledger'"
      >
        Payments Audit Ledger
      </button>
      <button
        class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors"
        :class="activeTab === 'refunds' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'btn-secondary'"
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
          <p class="text-xs text-[var(--silt)] mt-1">Cross-check ledger entries, settled transactions, and calculate outstanding variance.</p>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-[var(--rule)] text-[var(--silt)]">
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
          <tbody class="divide-y divide-[var(--rule)]">
            <tr v-for="item in reconciliation.data.value || []" :key="item.reservation_id" class="hover:bg-[var(--paper)]/80">
              <td class="py-3 px-2 tabular-nums font-bold">{{ item.reference }}</td>
              <td class="py-3 px-2">{{ item.guest_name }}</td>
              <td class="py-3 px-2 text-[var(--silt)]">{{ item.arrival }} → {{ item.departure }}</td>
              <td class="py-3 px-2 text-right tabular-nums">{{ money(item.charges_minor) }}</td>
              <td class="py-3 px-2 text-right tabular-nums text-[var(--status-available)]">{{ money(item.settled_minor) }}</td>
              <td class="py-3 px-2 text-right tabular-nums text-[var(--status-out)]">{{ money(item.refunds_minor) }}</td>
              <td class="py-3 px-2 text-right tabular-nums font-bold" :class="item.balance_minor === 0 ? 'text-[var(--status-available)]' : 'text-[var(--status-out)]'">
                {{ money(item.balance_minor) }}
              </td>
              <td class="py-3 px-2 text-center">
                <span
                  class="badge text-[10px]"
                  :class="item.is_balanced ? 'bg-[var(--status-available)]/10 text-[var(--status-available)] border-[var(--status-available)]/30' : 'bg-[var(--status-out)]/10 text-[var(--status-out)] border-[var(--status-out)]/30'"
                >
                  {{ item.is_balanced ? 'Balanced' : 'Discrepancy' }}
                </span>
              </td>
              <td class="py-3 px-4 text-right whitespace-nowrap">
                <div class="table-actions">
                  <button
                    type="button"
                    class="table-action-btn"
                    :disabled="busy || !item.is_balanced"
                    @click="reconcileFolio(item.reservation_id, item.reference)"
                  >
                    <svg class="w-3.5 h-3.5 shrink-0 text-[var(--status-available)] " fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <span>Audit Folio</span>
                  </button>
                </div>
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
          <p class="text-xs text-[var(--silt)] mt-1">Immutable record of all processed, failed, and exception payment events.</p>
        </div>
        <div class="flex items-center gap-1 border border-[var(--rule)] rounded-lg p-1 bg-[var(--paper)]">
          <button
            v-for="st in ['ALL', 'SETTLED', 'PENDING', 'FAILED', 'EXCEPTION'] as const"
            :key="st"
            class="px-2.5 py-1 text-[11px] rounded transition-colors"
            :class="paymentStatus === st ? 'bg-[var(--rule)] font-bold' : 'text-[var(--silt)]'"
            @click="paymentStatus = st"
          >
            {{ st }}
          </button>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-[var(--rule)] text-[var(--silt)]">
              <th class="py-3 px-2">Payment ID</th>
              <th class="py-3 px-2">Booking Ref</th>
              <th class="py-3 px-2">Guest</th>
              <th class="py-3 px-2">Gateway Ref</th>
              <th class="py-3 px-2 text-right">Amount</th>
              <th class="py-3 px-2 text-center">Status</th>
              <th class="py-3 px-2">Settled At</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--rule)]">
            <tr v-for="p in payments.data.value || []" :key="p.id" class="hover:bg-[var(--paper)]/80">
              <td class="py-3 px-2 tabular-nums">#{{ p.id }}</td>
              <td class="py-3 px-2 tabular-nums font-bold">{{ p.reference }}</td>
              <td class="py-3 px-2">{{ p.guest_name }}</td>
              <td class="py-3 px-2 tabular-nums text-[11px] text-[var(--silt)]">{{ p.gateway_reference || 'N/A' }}</td>
              <td class="py-3 px-2 text-right tabular-nums font-bold">{{ money(p.amount_minor) }}</td>
              <td class="py-3 px-2 text-center">
                <span
                  class="badge text-[10px]"
                  :class="{
                    'bg-[var(--status-available)]/10 text-[var(--status-available)]': p.status === 'SETTLED',
 'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)]': p.status === 'PENDING',
                    'bg-[var(--status-out)]/10 text-[var(--status-out)]': p.status === 'FAILED',
                    'bg-[var(--laterite)]/10 text-[var(--laterite)]': p.status === 'EXCEPTION'
                  }"
                >
                  {{ p.status }}
                </span>
              </td>
              <td class="py-3 px-2 text-[var(--silt)] text-[11px]">
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
          <p class="text-xs text-[var(--silt)] mt-1">Disburse settled funds for refunds reviewed and authorized by Management.</p>
        </div>
        <span class="badge">{{ approvedRefunds.length }} pending settlement</span>
      </div>

      <div v-if="approvedRefunds.length === 0" class="py-12 text-center text-sm text-[var(--silt)]">
        No approved refunds waiting for settlement.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="rf in approvedRefunds"
          :key="rf.id"
          class="p-4 rounded-xl border border-[var(--rule)] bg-[var(--paper)]/60 flex flex-wrap items-center justify-between gap-4"
        >
          <div class="space-y-1">
            <div class="flex items-center gap-3">
              <span class="font-bold text-base">{{ money(rf.amount_minor) }}</span>
              <span class="badge text-[10px] tabular-nums">{{ rf.reservation_reference }}</span>
              <span class="badge text-[10px] bg-[var(--status-occupied)]/10 text-[var(--status-occupied)] border-[var(--status-occupied)]/30">APPROVED</span>
            </div>
            <p class="text-xs text-[var(--silt)]">Guest: {{ rf.guest_name }} · Reason: "{{ rf.reason }}"</p>
            <p class="text-[10px] text-[var(--silt)]">
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
