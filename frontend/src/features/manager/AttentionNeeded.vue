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
</script>

<template>
  <div class="attention-needed space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <span class="inline-block w-2.5 h-2.5 rounded-full" :class="urgentCount > 0 ? 'bg-rose-500 animate-pulse' : 'bg-emerald-500'" />
          <h2 class="text-2xl font-serif">Attention Needed · Decision Support</h2>
        </div>
        <p class="text-sm text-[var(--muted,#5e7470)] mt-1">
          Server-evaluated transparent business rules alerting management to operational risks and revenue opportunities.
        </p>
      </div>

      <!-- Severity Filter Pills -->
      <div class="flex flex-wrap gap-2 text-xs">
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition"
          :class="filter === 'ALL' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] border-transparent font-medium' : 'border-[var(--line,#e2e8e0)] text-[var(--muted,#5e7470)] hover:border-[#0c2b26]'"
          @click="filter = 'ALL'"
        >
          All ({{ alerts.length }})
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition flex items-center gap-1.5"
          :class="filter === 'URGENT' ? 'bg-rose-600 text-white border-transparent font-medium' : 'border-rose-300/60 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/20'"
          @click="filter = 'URGENT'"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-rose-500" />
          Urgent ({{ urgentCount }})
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition flex items-center gap-1.5"
          :class="filter === 'WARNING' ? 'bg-amber-600 text-white border-transparent font-medium' : 'border-amber-300/60 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/20'"
          @click="filter = 'WARNING'"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-amber-500" />
          Warning ({{ warningCount }})
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-full border transition"
          :class="filter === 'INFO' ? 'bg-sky-600 text-white border-transparent font-medium' : 'border-sky-300/60 text-sky-600 dark:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-950/20'"
          @click="filter = 'INFO'"
        >
          Info ({{ infoCount }})
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="filteredAlerts.length === 0" class="card p-8 text-center text-[var(--muted,#5e7470)]">
      <p class="text-base font-medium text-[var(--brand-text,#0c2b26)] dark:text-emerald-400">✓ All systems operating within normal parameters.</p>
      <p class="text-sm mt-1">No alerts matching the selected filter.</p>
    </div>

    <!-- Alert Cards List -->
    <div v-else class="space-y-4">
      <article
        v-for="alert in filteredAlerts"
        :key="alert.id"
        class="card p-6 border-l-4 transition hover:shadow-md"
        :class="{
          'border-l-rose-500 bg-gradient-to-r from-rose-50/40 to-transparent dark:from-rose-950/20': alert.severity === 'URGENT',
          'border-l-amber-500 bg-gradient-to-r from-amber-50/40 to-transparent dark:from-amber-950/20': alert.severity === 'WARNING',
          'border-l-sky-500 bg-gradient-to-r from-sky-50/40 to-transparent dark:from-sky-950/20': alert.severity === 'INFO'
        }"
      >
        <!-- Header -->
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div class="flex items-center gap-2">
            <span
              class="px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wider"
              :class="{
                'bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-200': alert.severity === 'URGENT',
                'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200': alert.severity === 'WARNING',
                'bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-200': alert.severity === 'INFO'
              }"
            >
              {{ alert.severity }}
            </span>
            <span class="text-xs uppercase tracking-wider text-[var(--muted,#5e7470)] font-medium">
              {{ alert.category.replace(/_/g, ' ') }}
            </span>
          </div>
          <button
            type="button"
            class="text-xs font-semibold text-[#8f6826] dark:text-[#d7b683] hover:underline flex items-center gap-1"
            @click="emit('navigate', actionTarget(alert))"
          >
            Action in Operations →
          </button>
        </div>

        <h3 class="text-xl font-serif text-[#0c2b26] dark:text-[#f3ede2]">
          {{ alert.title }}
        </h3>

        <!-- 4-Part Structure -->
        <div class="grid md:grid-cols-2 gap-4 mt-4 text-sm">
          <div class="p-3 rounded-lg bg-[#f0f6f4] border border-[#cbdad4] text-[#1f3330] dark:bg-[#122523] dark:border-[#1a3330] dark:text-[#e4ded5] space-y-1">
            <span class="label text-[10px] uppercase font-bold text-[#536b66] dark:text-[#9ab4ac]">1. What happened</span>
            <p class="text-[#0c2b26] dark:text-[#e4ded5]">{{ alert.what_happened }}</p>
          </div>

          <div class="p-3 rounded-lg bg-[#f0f6f4] border border-[#cbdad4] text-[#1f3330] dark:bg-[#122523] dark:border-[#1a3330] dark:text-[#e4ded5] space-y-1">
            <span class="label text-[10px] uppercase font-bold text-[#536b66] dark:text-[#9ab4ac]">2. Records involved</span>
            <p class="font-mono text-xs text-[#0c2b26] dark:text-[#e4ded5] break-words">{{ alert.records_involved }}</p>
          </div>

          <div class="p-3 rounded-lg bg-[#f0f6f4] border border-[#cbdad4] text-[#1f3330] dark:bg-[#122523] dark:border-[#1a3330] dark:text-[#e4ded5] space-y-1">
            <span class="label text-[10px] uppercase font-bold text-[#536b66] dark:text-[#9ab4ac]">3. Why it matters</span>
            <p class="text-[#0c2b26] dark:text-[#e4ded5]">{{ alert.why_it_matters }}</p>
          </div>

          <div class="p-3 rounded-lg bg-[#fbf8f2] border border-[#8f6826]/30 dark:bg-[#122523] dark:border-[#d7b683]/30 space-y-1">
            <span class="label text-[10px] uppercase font-bold text-[#8f6826] dark:text-[#d7b683]">4. Recommended action</span>
            <p class="text-[#0c2b26] dark:text-[#f3ede2] font-medium">{{ alert.recommended_action }}</p>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
