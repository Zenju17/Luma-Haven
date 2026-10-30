<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import AttentionNeeded from './AttentionNeeded.vue'
import Notice from '../../components/Notice.vue'
import { staffApi, adminApi } from '../../services/api'
import { money, type ManagerDashboardData, type StaffUser } from '../../types'

const props = withDefaults(defineProps<{
  portal?: 'staff' | 'admin'
  user?: StaffUser | null
}>(), {
  portal: 'staff',
  user: null,
})

const emit = defineEmits<{
  (e: 'navigate', section: string): void
}>()

function getBusinessDate(offset = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return d.toISOString().slice(0, 10)
}

function getMonthStart(): string {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}

function getMonthEnd(): string {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth() + 1, 1).toISOString().slice(0, 10)
}

const activePreset = ref<'today' | '7days' | 'month' | 'custom'>('7days')
const start = ref(getBusinessDate(-6))
const end = ref(getBusinessDate(1)) // exclusive end date

function selectPreset(preset: 'today' | '7days' | 'month') {
  activePreset.value = preset
  if (preset === 'today') {
    start.value = getBusinessDate(0)
    end.value = getBusinessDate(1)
  } else if (preset === '7days') {
    start.value = getBusinessDate(-6)
    end.value = getBusinessDate(1)
  } else if (preset === 'month') {
    start.value = getMonthStart()
    end.value = getMonthEnd()
  }
}

watch([start, end], () => {
  if (activePreset.value !== 'custom') {
    const isToday = start.value === getBusinessDate(0) && end.value === getBusinessDate(1)
    const is7Days = start.value === getBusinessDate(-6) && end.value === getBusinessDate(1)
    const isMonth = start.value === getMonthStart() && end.value === getMonthEnd()
    if (!isToday && !is7Days && !isMonth) {
      activePreset.value = 'custom'
    }
  }
})

const apiFn = computed(() => (props.portal === 'admin' ? adminApi : staffApi))

const dashboardQuery = useQuery({
  queryKey: computed(() => ['manager', 'dashboard', props.portal, start.value, end.value]),
  queryFn: () => apiFn.value<ManagerDashboardData>(`/manager/dashboard?start=${start.value}&end=${end.value}`),
  enabled: computed(() => Boolean(start.value && end.value && start.value < end.value)),
})

const data = computed(() => dashboardQuery.data.value)
const kpis = computed(() => data.value?.kpis)
const roomTypes = computed(() => data.value?.room_types || [])
const readiness = computed(() => data.value?.readiness)
const operations = computed(() => data.value?.operations)
const alerts = computed(() => data.value?.alerts || [])
const trends = computed(() => data.value?.trends || [])

// Native SVG Chart Helpers
const hoveredTrendIndex = ref<number | null>(null)

const maxOccupancyValue = computed(() => {
  if (!trends.value.length) return 10
  return Math.max(...trends.value.map(t => Math.max(t.sellable, t.sold)), 1)
})

const maxRevenueValue = computed(() => {
  if (!trends.value.length) return 10000
  return Math.max(...trends.value.map(t => t.revenue_minor), 1000)
})

const isHousekeeping = computed(() => props.user?.role === 'HOUSEKEEPING')
</script>

<template>
  <div class="manager-dashboard space-y-8">
    <!-- Header & Period Filter Controls -->
    <div class="card p-6 flex flex-wrap items-center justify-between gap-5 bg-gradient-to-r from-[var(--surface,#ffffff)] via-[var(--surface,#ffffff)] to-[var(--surface-muted,#f3f7f5)] dark:from-[#0f211f] dark:to-[#081514]">
      <div>
        <p class="label">Management Information System</p>
        <h1 class="text-3xl font-serif text-[var(--brand-text,#0c2b26)] dark:text-[#f3ede2]">
          Manager Intelligence Dashboard
        </h1>
        <p class="text-sm text-[var(--muted,#5e7470)] mt-1">
          Accurate operational transactions, recognized revenues, and prescriptive decision support.
        </p>
      </div>

      <!-- Presets and Date Controls -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="inline-flex rounded-lg border border-[var(--line,#e2e8e0)] dark:border-[#223936] p-1 bg-[var(--surface-muted,#eaf1ee)] dark:bg-[#0a1716] text-xs">
          <button
            type="button"
            class="px-3 py-1.5 rounded-md transition font-medium"
            :class="activePreset === 'today' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] shadow-sm' : 'text-[var(--muted,#5e7470)] hover:text-[var(--brand-text)]'"
            @click="selectPreset('today')"
          >
            Today
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md transition font-medium"
            :class="activePreset === '7days' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] shadow-sm' : 'text-[var(--muted,#5e7470)] hover:text-[var(--brand-text)]'"
            @click="selectPreset('7days')"
          >
            Last 7 Days
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md transition font-medium"
            :class="activePreset === 'month' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] shadow-sm' : 'text-[var(--muted,#5e7470)] hover:text-[var(--brand-text)]'"
            @click="selectPreset('month')"
          >
            This Month
          </button>
        </div>

        <div class="flex items-center gap-2 text-xs">
          <input
            v-model="start"
            type="date"
            class="field py-1.5 px-2.5 text-xs rounded-lg"
            aria-label="Start date"
          />
          <span class="text-[var(--muted)]">to</span>
          <input
            v-model="end"
            type="date"
            class="field py-1.5 px-2.5 text-xs rounded-lg"
            aria-label="End date (exclusive)"
          />
        </div>

        <button
          type="button"
          class="btn-secondary py-1.5 px-3 text-xs"
          :disabled="dashboardQuery.isFetching.value"
          @click="dashboardQuery.refetch()"
        >
          {{ dashboardQuery.isFetching.value ? 'Refreshing…' : '↻ Refresh' }}
        </button>
      </div>
    </div>

    <!-- Error state -->
    <Notice :message="dashboardQuery.error.value ? String(dashboardQuery.error.value) : ''" />

    <!-- Role Restriction Notice -->
    <div v-if="isHousekeeping" class="card p-6 border-l-4 border-amber-500">
      <p class="font-medium text-amber-800 dark:text-amber-200">Role-Restricted View</p>
      <p class="text-sm mt-1 text-[var(--muted)]">
        Housekeeping accounts have access to room operations and turnover queues. Financial performance metrics and ledger reconciliations are restricted to management and accounting roles.
      </p>
    </div>

    <template v-else-if="kpis">
      <!-- Section 1: Attention Needed (Decision Support) -->
      <AttentionNeeded :alerts="alerts" @navigate="dest => emit('navigate', dest)" />

      <!-- Section 2: Executive KPI Cards with Tooltips & Definitions -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-serif">Executive Financial & Operational KPIs</h2>
          <span class="text-xs text-[var(--muted)]">
            Period: {{ kpis.start }} to {{ kpis.end_exclusive }} ({{ kpis.days }} {{ kpis.days === 1 ? 'day' : 'days' }}) · Hotel: {{ kpis.hotel }}
          </span>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <!-- KPI 1: Occupancy Rate -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">Occupancy Rate</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Formula: Sold Room-Nights ÷ Sellable Room-Nights × 100. Accurately adjusts for early checkouts and historical maintenance blocks.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[var(--brand-text,#0c2b26)] dark:text-[#f3ede2]">
              {{ kpis.occupancy_rate_percent !== null ? `${kpis.occupancy_rate_percent}%` : 'N/A' }}
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              {{ kpis.sold_room_nights }} sold / {{ kpis.sellable_room_nights }} sellable nights
            </p>
          </div>

          <!-- KPI 2: ADR -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">Average Daily Rate (ADR)</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Formula: Net Room Revenue ÷ Sold Room-Nights. Measures the average realized rental income per paid room night, excluding taxes.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[var(--brand-text,#0c2b26)] dark:text-[#f3ede2]">
              {{ kpis.average_daily_rate_minor !== null ? money(kpis.average_daily_rate_minor) : 'N/A' }}
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              Per occupied room night
            </p>
          </div>

          <!-- KPI 3: RevPAR -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">RevPAR</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Formula: Net Room Revenue ÷ Sellable Room-Nights. Comprehensive metric combining pricing discipline with inventory occupancy.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[var(--brand-text,#0c2b26)] dark:text-[#f3ede2]">
              {{ kpis.revpar_minor !== null ? money(kpis.revpar_minor) : 'N/A' }}
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              Per sellable room night
            </p>
          </div>

          <!-- KPI 4: Net Room Revenue -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">Net Room Revenue</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Earned room revenue recognized strictly by service date for nights stayed. Excludes taxes, unstayed nights, and non-room items.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[var(--brand-text,#0c2b26)] dark:text-[#f3ede2]">
              {{ money(kpis.net_room_revenue_minor) }}
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              Service-date recognized
            </p>
          </div>

          <!-- KPI 5: Net Settled Cash -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">Net Settled Cash</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Net cash collected = Gross settled payments minus settled refunds in hotel timezone during this period.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-emerald-700 dark:text-emerald-400">
              {{ money(kpis.settled_cash_minor) }}
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              Gross: {{ money(kpis.gross_cash_minor) }} · Refunds: -{{ money(kpis.refunded_cash_minor) }}
            </p>
          </div>

          <!-- KPI 6: Outstanding Balances -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">Outstanding Balances</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Unsettled balances across active confirmed and checked-in reservation folios. Accounts receivable asset.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2" :class="kpis.outstanding_balances_minor > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-[var(--brand-text)]'">
              {{ money(kpis.outstanding_balances_minor) }}
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              Unsettled active folios
            </p>
          </div>

          <!-- KPI 7: Cancellations & No-Shows -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">Cancellations / No-Shows</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Cancelled reservations during period, plus arrivals marked as no-show. Rate calculated against booking cohorts.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[var(--brand-text,#0c2b26)] dark:text-[#f3ede2]">
              {{ kpis.cancellations_count }} <span class="text-base font-normal text-[var(--muted)]">/ {{ kpis.no_shows_count }} no-shows</span>
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              Cancellation rate: {{ kpis.cancellation_rate_percent !== null ? `${kpis.cancellation_rate_percent}%` : 'N/A' }}
            </p>
          </div>

          <!-- KPI 8: Housekeeping Turnaround -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs uppercase tracking-wider">Avg Turnover Time</span>
              <span class="cursor-help text-xs text-[var(--muted)]" title="Average duration from guest checkout to housekeeping completion and ready inspection for rooms turned over in period.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[var(--brand-text,#0c2b26)] dark:text-[#f3ede2]">
              {{ kpis.avg_housekeeping_turnaround_minutes !== null ? `${kpis.avg_housekeeping_turnaround_minutes}m` : 'N/A' }}
            </p>
            <p class="text-xs text-[var(--muted)] mt-1">
              Checkout to ready state
            </p>
          </div>
        </div>
      </div>

      <!-- Section 3: Native SVG Trend Visualizations -->
      <div class="grid md:grid-cols-2 gap-6">
        <!-- Chart 1: Occupancy Trend -->
        <div class="card p-6 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-serif">Daily Room Demand & Capacity</h3>
              <p class="text-xs text-[var(--muted)]">Sellable inventory vs booked room-nights per date.</p>
            </div>
            <div class="flex items-center gap-3 text-xs">
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[var(--surface-muted,#d1ded9)] dark:bg-[#1a3834]" /> Capacity</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[#0c2b26] dark:bg-[#d7b683]" /> Sold</span>
            </div>
          </div>

          <div v-if="trends.length === 0" class="h-48 flex items-center justify-center text-sm text-[var(--muted)]">
            No daily trend points in selected range.
          </div>
          <div v-else class="relative h-48 w-full">
            <svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 60">
              <!-- Grid lines -->
              <line x1="0" y1="15" x2="100" y2="15" stroke="currentColor" class="text-[var(--line,#e2e8e0)] dark:text-[#18312e]" stroke-dasharray="2,2" stroke-width="0.5" />
              <line x1="0" y1="30" x2="100" y2="30" stroke="currentColor" class="text-[var(--line,#e2e8e0)] dark:text-[#18312e]" stroke-dasharray="2,2" stroke-width="0.5" />
              <line x1="0" y1="45" x2="100" y2="45" stroke="currentColor" class="text-[var(--line,#e2e8e0)] dark:text-[#18312e]" stroke-dasharray="2,2" stroke-width="0.5" />

              <!-- Daily bars -->
              <g v-for="(point, idx) in trends" :key="point.date">
                <!-- Bar group centered -->
                <rect
                  :x="((idx + 0.2) / trends.length) * 100"
                  :y="50 - (point.sellable / maxOccupancyValue) * 45"
                  :width="(0.6 / trends.length) * 100"
                  :height="(point.sellable / maxOccupancyValue) * 45"
                  class="fill-[var(--surface-muted,#d1ded9)] dark:fill-[#1a3834] rx-1"
                />
                <rect
                  :x="((idx + 0.2) / trends.length) * 100"
                  :y="50 - (point.sold / maxOccupancyValue) * 45"
                  :width="(0.6 / trends.length) * 100"
                  :height="(point.sold / maxOccupancyValue) * 45"
                  class="fill-[#0c2b26] dark:fill-[#d7b683] transition-all hover:opacity-80 cursor-pointer rx-1"
                  @mouseenter="hoveredTrendIndex = idx"
                  @mouseleave="hoveredTrendIndex = null"
                />
              </g>
            </svg>

            <!-- Bottom dates -->
            <div class="flex justify-between text-[10px] text-[var(--muted)] mt-2">
              <span>{{ trends[0]?.date }}</span>
              <span>{{ trends[trends.length - 1]?.date }}</span>
            </div>

            <!-- Hover tooltip -->
            <div
              v-if="hoveredTrendIndex !== null && trends[hoveredTrendIndex]"
              class="absolute top-2 right-2 p-2 rounded bg-[#0c2b26] text-white text-xs shadow-lg space-y-0.5"
            >
              <p class="font-bold">{{ trends[hoveredTrendIndex].date }}</p>
              <p>Sold: {{ trends[hoveredTrendIndex].sold }} / Sellable: {{ trends[hoveredTrendIndex].sellable }}</p>
              <p>Revenue: {{ money(trends[hoveredTrendIndex].revenue_minor) }}</p>
            </div>
          </div>
        </div>

        <!-- Chart 2: Revenue Trend -->
        <div class="card p-6 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-serif">Daily Room Revenue Trend</h3>
              <p class="text-xs text-[var(--muted)]">Net room revenue recognized per stay service date.</p>
            </div>
            <span class="text-xs font-mono text-[var(--brand-gold,#d7b683)] font-semibold">
              Peak: {{ money(maxRevenueValue) }}
            </span>
          </div>

          <div v-if="trends.length === 0" class="h-48 flex items-center justify-center text-sm text-[var(--muted)]">
            No daily trend points in selected range.
          </div>
          <div v-else class="relative h-48 w-full">
            <svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 60">
              <!-- Area fill & stroke line for revenue -->
              <polyline
                fill="none"
                stroke="currentColor"
                class="text-emerald-600 dark:text-[#d7b683]"
                stroke-width="2"
                :points="trends.map((p, i) => `${((i + 0.5) / trends.length) * 100},${50 - (p.revenue_minor / maxRevenueValue) * 45}`).join(' ')"
              />
              <circle
                v-for="(p, i) in trends"
                :key="i"
                :cx="((i + 0.5) / trends.length) * 100"
                :cy="50 - (p.revenue_minor / maxRevenueValue) * 45"
                r="1.5"
                class="fill-emerald-700 dark:fill-[#d7b683]"
              />
            </svg>

            <div class="flex justify-between text-[10px] text-[var(--muted)] mt-2">
              <span>{{ trends[0]?.date }}</span>
              <span>{{ trends[trends.length - 1]?.date }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Section 4: Room-Type Performance Table -->
      <div class="card overflow-hidden">
        <div class="p-6 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330] flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 class="text-xl font-serif">Room-Type Performance Breakdown</h3>
            <p class="text-xs text-[var(--muted)] mt-0.5">Comparative yield, sellable nights, and ADR across room inventory categories.</p>
          </div>
          <span class="text-xs text-[var(--muted)]">
            Total Inventory: {{ readiness?.total }} rooms
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="data-table w-full text-left text-sm">
            <thead>
              <tr class="bg-[var(--surface-muted,#f3f7f5)] dark:bg-[#0c1c1a]">
                <th class="p-4">Room Type</th>
                <th class="p-4">Total Rooms</th>
                <th class="p-4">Base Rate</th>
                <th class="p-4">Sellable Nights</th>
                <th class="p-4">Sold Nights</th>
                <th class="p-4">Occupancy %</th>
                <th class="p-4">Net Revenue</th>
                <th class="p-4">ADR</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="rt in roomTypes"
                :key="rt.id"
                class="border-t border-[var(--line,#e2e8e0)] dark:border-[#1a3330] hover:bg-[var(--surface-muted,#f3f7f5)]/50 transition"
              >
                <td class="p-4 font-medium">{{ rt.name }}</td>
                <td class="p-4">{{ rt.total_rooms }}</td>
                <td class="p-4">{{ money(rt.nightly_rate_minor) }}</td>
                <td class="p-4">{{ rt.sellable_room_nights }}</td>
                <td class="p-4 font-semibold">{{ rt.sold_room_nights }}</td>
                <td class="p-4">
                  <span
                    class="px-2 py-0.5 rounded text-xs font-medium"
                    :class="(rt.occupancy_rate_percent || 0) >= 70 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'"
                  >
                    {{ rt.occupancy_rate_percent !== null ? `${rt.occupancy_rate_percent}%` : 'N/A' }}
                  </span>
                </td>
                <td class="p-4 font-mono font-medium">{{ money(rt.net_room_revenue_minor) }}</td>
                <td class="p-4 font-mono">{{ rt.adr_minor !== null ? money(rt.adr_minor) : 'N/A' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Section 5: Real-Time Operations Snapshot -->
      <div v-if="operations" class="grid md:grid-cols-3 gap-6">
        <!-- Card 1: Today's Front Desk Movements -->
        <div class="card p-6 space-y-4">
          <h3 class="text-lg font-serif">Today's Desk Movements</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between p-3 rounded-lg bg-[var(--surface-muted,#f3f7f5)] dark:bg-[#122523]">
              <span class="text-sm">Expected Arrivals</span>
              <span class="font-bold text-base">{{ operations.arrivals.total }}</span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-xs">
              <div class="p-2 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300">
                Checked in: <strong>{{ operations.arrivals.checked_in }}</strong>
              </div>
              <div class="p-2 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300">
                Pending: <strong>{{ operations.arrivals.pending }}</strong>
              </div>
            </div>

            <div class="flex items-center justify-between p-3 rounded-lg bg-[var(--surface-muted,#f3f7f5)] dark:bg-[#122523] mt-2">
              <span class="text-sm">Expected Departures</span>
              <span class="font-bold text-base">{{ operations.departures.total }}</span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-xs">
              <div class="p-2 rounded bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-300">
                Checked out: <strong>{{ operations.departures.checked_out }}</strong>
              </div>
              <div class="p-2 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300">
                In-house: <strong>{{ operations.departures.pending }}</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- Card 2: Room Readiness Distribution -->
        <div v-if="readiness" class="card p-6 space-y-4">
          <h3 class="text-lg font-serif">Room Readiness Status</h3>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between items-center py-1 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Ready for Check-in</span>
              <span class="font-bold">{{ readiness.ready }}</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-sky-500" /> Cleaning in Progress</span>
              <span class="font-bold">{{ readiness.cleaning }}</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-indigo-500" /> Inspection Pending</span>
              <span class="font-bold">{{ readiness.inspection }}</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-amber-500" /> Dirty (Awaiting Turnover)</span>
              <span class="font-bold">{{ readiness.dirty }}</span>
            </div>
            <div class="flex justify-between items-center py-1">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-rose-500" /> Out of Service (Maintenance)</span>
              <span class="font-bold">{{ readiness.out_of_service }}</span>
            </div>
          </div>

          <!-- Unready Arrivals Alert if any -->
          <div v-if="operations.unready_arrivals_today.length > 0" class="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-xs text-rose-800 dark:text-rose-200">
            <strong>Urgent Turnover Needed:</strong>
            {{ operations.unready_arrivals_today.length }} room(s) with arrival today not yet ready!
          </div>
        </div>

        <!-- Card 3: Quality & Exceptions Queue -->
        <div class="card p-6 space-y-4">
          <h3 class="text-lg font-serif">Exceptions & Pending Queue</h3>
          <div class="space-y-2.5 text-xs">
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--surface-muted,#f3f7f5)] dark:bg-[#122523]">
              <span>Active Maintenance Tickets</span>
              <span class="font-bold font-mono px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700">
                {{ operations.open_maintenance.length }}
              </span>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--surface-muted,#f3f7f5)] dark:bg-[#122523]">
              <span>Open Guest Service Requests</span>
              <span class="font-bold font-mono px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700">
                {{ operations.open_requests.length }}
              </span>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--surface-muted,#f3f7f5)] dark:bg-[#122523]">
              <span>Pending Refunds for Review</span>
              <span class="font-bold font-mono px-2 py-0.5 rounded" :class="operations.pending_refunds.length > 0 ? 'bg-amber-200 text-amber-900 dark:bg-amber-900 dark:text-amber-200 font-bold' : 'bg-slate-200 dark:bg-slate-700'">
                {{ operations.pending_refunds.length }}
              </span>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--surface-muted,#f3f7f5)] dark:bg-[#122523]">
              <span>Payment Exceptions</span>
              <span class="font-bold font-mono px-2 py-0.5 rounded" :class="operations.payment_exceptions_count > 0 ? 'bg-rose-200 text-rose-900 dark:bg-rose-950 dark:text-rose-200 font-bold' : 'bg-slate-200 dark:bg-slate-700'">
                {{ operations.payment_exceptions_count }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
