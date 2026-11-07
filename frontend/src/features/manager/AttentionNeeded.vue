<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DecisionAlert } from '../../types'

const props = defineProps<{
  alerts: DecisionAlert[]
}>()

const emit = defineEmits<{
  (e: 'navigate', destination: string): void
}>()

const filter = ref<'ALL' | 'URGENT' | 'WARNING' | 'INFO'>('ALL')

const filteredAlerts = computed(() => {
  if (filter.value === 'ALL') return props.alerts
  return props.alerts.filter(a => a.severity === filter.value)
})

const urgentCount = computed(() => props.alerts.filter(a => a.severity === 'URGENT').length)
const warningCount = computed(() => props.alerts.filter(a => a.severity === 'WARNING').length)
const infoCount = computed(() => props.alerts.filter(a => a.severity === 'INFO').length)

function actionTarget(alert: DecisionAlert): string {
  switch (alert.id) {
    case 'low_occupancy_upcoming':
      return 'rates'
    case 'unpaid_upcoming_reservations':
    case 'high_cancellation_rate':
      return 'reservations'
    case 'unresolved_payment_exceptions':
      return 'refunds'
    case 'unready_arrival_rooms':
      return 'housekeeping'
    case 'repeated_maintenance_issues':
      return 'maintenance'
    case 'overdue_service_requests':
      return 'requests'
    default:
      return 'overview'
  }
}

function actionLabel(alert: DecisionAlert): string {
  switch (alert.id) {
    case 'low_occupancy_upcoming':
      return 'Room Rates'
    case 'unpaid_upcoming_reservations':
    case 'high_cancellation_rate':
      return 'Reservations'
    case 'unresolved_payment_exceptions':
      return 'Refunds'
    case 'unready_arrival_rooms':
      return 'Housekeeping'
    case 'repeated_maintenance_issues':
      return 'Maintenance'
    case 'overdue_service_requests':
      return 'Service Requests'
    default:
      return 'Operations'
  }
}
</script>

<template>
  <div class="attention-needed space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-block w-2.5 h-2.5 rounded-full" :class="urgentCount > 0 ? 'bg-[var(--status-out)] ' : 'bg-[var(--status-available)]'" />
          <h2 class="text-2xl font-serif">Attention Needed · Decision Support</h2>
        </div>
        <p class="text-sm text-[var(--silt,#5e7470)] mt-1">
          Server-evaluated transparent business rules alerting management to operational risks and revenue opportunities.
        </p>
      </div>

      <!-- Severity Filter Pills -->
      <div class="flex flex-wrap gap-2 text-xs">
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition"
          :class="filter === 'ALL' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)] border-transparent font-medium' : 'border-[var(--rule,#e2e8e0)] text-[var(--silt,#5e7470)] hover:border-[var(--river)]'"
          @click="filter = 'ALL'"
        >
          All ({{ alerts.length }})
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition flex items-center gap-1.5"
          :class="filter === 'URGENT' ? 'bg-[var(--status-out)] text-white border-transparent font-medium' : 'border-[var(--status-out)]/30 text-[var(--status-out)] hover:bg-[var(--status-out)]/10 '"
          @click="filter = 'URGENT'"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-[var(--status-out)]" />
          Urgent ({{ urgentCount }})
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition flex items-center gap-1.5"
          :class="filter === 'WARNING' ? 'bg-[var(--status-dirty)] text-white border-transparent font-medium' : 'border-[var(--status-dirty)]/30 text-[var(--status-dirty)] hover:bg-[var(--status-dirty)]/10 '"
          @click="filter = 'WARNING'"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-[var(--status-dirty)]" />
          Warning ({{ warningCount }})
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition"
          :class="filter === 'INFO' ? 'bg-[var(--status-occupied)] text-white border-transparent font-medium' : 'border-[var(--status-occupied)]/30 text-[var(--status-occupied)] hover:bg-[var(--status-occupied)]/10 '"
          @click="filter = 'INFO'"
        >
          Info ({{ infoCount }})
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="filteredAlerts.length === 0" class="card p-8 text-center text-[var(--silt,#5e7470)]">
      <p class="text-base font-medium text-[var(--river,var(--river))] ">✓ All systems operating within normal parameters.</p>
      <p class="text-sm mt-1">No alerts matching the selected filter.</p>
    </div>

    <!-- Alert Cards List -->
    <div v-else class="space-y-4">
      <article
        v-for="alert in filteredAlerts"
        :key="alert.id"
        class="card p-6 border-l-4 transition"
        :class="{
          'border-l-[var(--status-out)] ': alert.severity === 'URGENT',
          'border-l-[var(--status-dirty)]  ': alert.severity === 'WARNING',
          'border-l-[var(--status-occupied)]  ': alert.severity === 'INFO'
        }"
      >
        <!-- Header -->
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div class="flex items-center gap-2">
            <span
              class="px-2.5 py-0.5 rounded text-xs font-semibold "
              :class="{
                'bg-[var(--status-out)]/10 text-[var(--status-out)] ': alert.severity === 'URGENT',
                'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)]  ': alert.severity === 'WARNING',
                'bg-[var(--status-occupied)]/10 text-[var(--status-occupied)]  ': alert.severity === 'INFO'
              }"
            >
              {{ alert.severity }}
            </span>
            <span class="text-xs text-[var(--silt,#5e7470)] font-medium">
              {{ alert.category.replace(/_/g, ' ') }}
            </span>
          </div>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold text-[color:var(--laterite)] bg-[var(--laterite)]/10 hover:bg-[var(--laterite)]/20 border border-[color:var(--laterite)]/30 dark:text-[color:var(--laterite)] dark:bg-[var(--laterite)]/15 dark:hover:bg-[var(--laterite)]/25 dark:border-[color:var(--laterite)]/30 transition cursor-pointer"
            :title="`Open ${actionLabel(alert)} in operations workspace`"
            @click="emit('navigate', actionTarget(alert))"
          >
            <span>Action in Operations</span>
            <span class="text-[11px] font-normal opacity-80">({{ actionLabel(alert) }})</span>
            <span aria-hidden="true">→</span>
          </button>
        </div>

        <h3 class="text-xl font-serif text-[color:var(--river)] dark:text-[color:var(--river)]">
          {{ alert.title }}
        </h3>

        <!-- 4-Part Structure -->
        <div class="grid md:grid-cols-2 gap-4 mt-4 text-sm">
          <div class="p-3 rounded-lg bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)] space-y-1">
            <span class="label text-[10px] font-bold text-[color:var(--silt)] dark:text-[color:var(--silt)]">1. What happened</span>
            <p class="text-[color:var(--river)] dark:text-[color:var(--river)]">{{ alert.what_happened }}</p>
          </div>

          <div class="p-3 rounded-lg bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)] space-y-1">
            <span class="label text-[10px] font-bold text-[color:var(--silt)] dark:text-[color:var(--silt)]">2. Records involved</span>
            <p class="tabular-nums text-xs text-[color:var(--river)] dark:text-[color:var(--river)] break-words">{{ alert.records_involved }}</p>
          </div>

          <div class="p-3 rounded-lg bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)] space-y-1">
            <span class="label text-[10px] font-bold text-[color:var(--silt)] dark:text-[color:var(--silt)]">3. Why it matters</span>
            <p class="text-[color:var(--river)] dark:text-[color:var(--river)]">{{ alert.why_it_matters }}</p>
          </div>

          <div class="p-3 rounded-lg bg-[var(--sunk)] border border-[color:var(--laterite)]/30 dark:bg-[var(--sunk)] dark:border-[color:var(--laterite)]/30 space-y-1">
            <span class="label text-[10px] font-bold text-[color:var(--laterite)] dark:text-[color:var(--laterite)]">4. Recommended action</span>
            <p class="text-[color:var(--river)] dark:text-[color:var(--river)] font-medium">{{ alert.recommended_action }}</p>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
