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
    <div class="card p-6 flex flex-wrap items-center justify-between gap-5 ">
      <div>
        <p class="label">Management Information System</p>
        <h1 class="text-3xl font-serif text-[color:var(--river)] dark:text-[color:var(--river)]">
          Manager Intelligence Dashboard
        </h1>
        <p class="text-sm text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
          Accurate operational transactions, recognized revenues, and prescriptive decision support.
        </p>
      </div>

      <!-- Presets and Date Controls -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="inline-flex rounded-lg border border-[color:var(--rule)] dark:border-[color:var(--rule)] p-1 bg-[var(--sunk)] dark:bg-[var(--sunk)] text-xs">
          <button
            type="button"
            class="px-3 py-1.5 rounded-md transition font-medium"
            :class="activePreset === 'today' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'text-[color:var(--silt)] hover:text-[color:var(--river)] dark:text-[color:var(--silt)] dark:hover:text-[color:var(--river)]'"
            @click="selectPreset('today')"
          >
            Today
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md transition font-medium"
            :class="activePreset === '7days' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'text-[color:var(--silt)] hover:text-[color:var(--river)] dark:text-[color:var(--silt)] dark:hover:text-[color:var(--river)]'"
            @click="selectPreset('7days')"
          >
            Last 7 Days
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md transition font-medium"
            :class="activePreset === 'month' ? 'bg-[var(--river)] text-[color:var(--palm-leaf)]' : 'text-[color:var(--silt)] hover:text-[color:var(--river)] dark:text-[color:var(--silt)] dark:hover:text-[color:var(--river)]'"
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
          <span class="text-[color:var(--silt)] dark:text-[color:var(--silt)]">to</span>
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
    <div v-if="isHousekeeping" class="card p-6 border-l-4 border-[var(--status-dirty)]">
      <p class="font-medium text-[var(--status-dirty)] ">Role-Restricted View</p>
      <p class="text-sm mt-1 text-[color:var(--silt)] dark:text-[color:var(--silt)]">
        Housekeeping accounts have access to room operations and turnover queues. Financial performance metrics and ledger reconciliations are restricted to management and accounting roles.
      </p>
    </div>

    <template v-else-if="kpis">
      <!-- Section 1: Attention Needed (Decision Support) -->
      <AttentionNeeded :alerts="alerts" @navigate="dest => emit('navigate', dest)" />

      <!-- Section 2: Executive KPI Cards with Tooltips & Definitions -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-serif text-[color:var(--river)] dark:text-[color:var(--river)]">Executive Financial & Operational KPIs</h2>
          <span class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">
            Period: {{ kpis.start }} to {{ kpis.end_exclusive }} ({{ kpis.days }} {{ kpis.days === 1 ? 'day' : 'days' }}) · Hotel: {{ kpis.hotel }}
          </span>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <!-- KPI 1: Occupancy Rate -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Occupancy Rate</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Formula: Sold Room-Nights ÷ Sellable Room-Nights × 100. Accurately adjusts for early checkouts and historical maintenance blocks.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[color:var(--river)] dark:text-[color:var(--river)]">
              {{ kpis.occupancy_rate_percent !== null ? `${kpis.occupancy_rate_percent}%` : 'N/A' }}
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
              {{ kpis.sold_room_nights }} sold / {{ kpis.sellable_room_nights }} sellable nights
            </p>
          </div>

          <!-- KPI 2: ADR -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Average Daily Rate (ADR)</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Formula: Net Room Revenue ÷ Sold Room-Nights. Measures the average realized rental income per paid room night, excluding taxes.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[color:var(--river)] dark:text-[color:var(--river)]">
              {{ kpis.average_daily_rate_minor !== null ? money(kpis.average_daily_rate_minor) : 'N/A' }}
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
              Per occupied room night
            </p>
          </div>

          <!-- KPI 3: RevPAR -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">RevPAR</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Formula: Net Room Revenue ÷ Sellable Room-Nights. Comprehensive metric combining pricing discipline with inventory occupancy.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[color:var(--river)] dark:text-[color:var(--river)]">
              {{ kpis.revpar_minor !== null ? money(kpis.revpar_minor) : 'N/A' }}
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
              Per sellable room night
            </p>
          </div>

          <!-- KPI 4: Net Room Revenue -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Net Room Revenue</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Earned room revenue recognized strictly by service date for nights stayed. Excludes taxes, unstayed nights, and non-room items.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[color:var(--river)] dark:text-[color:var(--river)]">
              {{ money(kpis.net_room_revenue_minor) }}
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
              Service-date recognized
            </p>
          </div>

          <!-- KPI 5: Net Settled Cash -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Net Settled Cash</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Net cash collected = Gross settled payments minus settled refunds in hotel timezone during this period.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[var(--status-available)] ">
              {{ money(kpis.settled_cash_minor) }}
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
              Gross: {{ money(kpis.gross_cash_minor) }} · Refunds: -{{ money(kpis.refunded_cash_minor) }}
            </p>
          </div>

          <!-- KPI 6: Outstanding Balances -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Outstanding Balances</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Unsettled balances across active confirmed and checked-in reservation folios. Accounts receivable asset.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2" :class="kpis.outstanding_balances_minor > 0 ? 'text-[var(--status-dirty)] ' : 'text-[color:var(--river)] dark:text-[color:var(--river)]'">
              {{ money(kpis.outstanding_balances_minor) }}
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
              Unsettled active folios
            </p>
          </div>

          <!-- KPI 7: Cancellations & No-Shows -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Cancellations / No-Shows</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Cancelled reservations during period, plus arrivals marked as no-show. Rate calculated against booking cohorts.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[color:var(--river)] dark:text-[color:var(--river)]">
              {{ kpis.cancellations_count }} <span class="text-base font-normal text-[color:var(--silt)] dark:text-[color:var(--silt)]">/ {{ kpis.no_shows_count }} no-shows</span>
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
              Cancellation rate: {{ kpis.cancellation_rate_percent !== null ? `${kpis.cancellation_rate_percent}%` : 'N/A' }}
            </p>
          </div>

          <!-- KPI 8: Housekeeping Turnaround -->
          <div class="card p-5 metric-card relative group">
            <div class="flex items-center justify-between">
              <span class="label text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Avg Turnover Time</span>
              <span class="cursor-help text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]" title="Average duration from guest checkout to housekeeping completion and ready inspection for rooms turned over in period.">ⓘ</span>
            </div>
            <p class="text-3xl font-bold mt-2 text-[color:var(--river)] dark:text-[color:var(--river)]">
              {{ kpis.avg_housekeeping_turnaround_minutes !== null ? `${kpis.avg_housekeeping_turnaround_minutes}m` : 'N/A' }}
            </p>
            <p class="text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] mt-1">
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
              <p class="text-xs text-[var(--silt)]">Sellable inventory vs booked room-nights per date.</p>
            </div>
            <div class="flex items-center gap-3 text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[var(--sunk)] border border-[color:var(--rule)] dark:border-transparent dark:bg-[var(--sunk)]" /> Capacity</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[var(--river)]" /> Sold</span>
            </div>
          </div>

          <div v-if="trends.length === 0" class="h-48 flex items-center justify-center text-sm text-[var(--silt)]">
            No daily trend points in selected range.
          </div>
          <div v-else class="relative h-48 w-full">
            <svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 60">
              <!-- Grid lines -->
              <line x1="0" y1="15" x2="100" y2="15" stroke="currentColor" class="text-[var(--rule,#e2e8e0)] dark:text-[color:var(--river)]" stroke-dasharray="2,2" stroke-width="0.5" />
              <line x1="0" y1="30" x2="100" y2="30" stroke="currentColor" class="text-[var(--rule,#e2e8e0)] dark:text-[color:var(--river)]" stroke-dasharray="2,2" stroke-width="0.5" />
              <line x1="0" y1="45" x2="100" y2="45" stroke="currentColor" class="text-[var(--rule,#e2e8e0)] dark:text-[color:var(--river)]" stroke-dasharray="2,2" stroke-width="0.5" />

              <!-- Daily bars -->
              <g v-for="(point, idx) in trends" :key="point.date">
                <!-- Bar group centered -->
                <rect
                  :x="((idx + 0.2) / trends.length) * 100"
                  :y="50 - (point.sellable / maxOccupancyValue) * 45"
                  :width="(0.6 / trends.length) * 100"
                  :height="(point.sellable / maxOccupancyValue) * 45"
                  class="fill-[var(--sunk)] rx-1"
                />
                <rect
                  :x="((idx + 0.2) / trends.length) * 100"
                  :y="50 - (point.sold / maxOccupancyValue) * 45"
                  :width="(0.6 / trends.length) * 100"
                  :height="(point.sold / maxOccupancyValue) * 45"
                  class="fill-[var(--river)] transition-all hover:opacity-80 cursor-pointer rx-1"
                  @mouseenter="hoveredTrendIndex = idx"
                  @mouseleave="hoveredTrendIndex = null"
                />
              </g>
            </svg>

            <!-- Bottom dates -->
            <div class="flex justify-between text-[10px] text-[var(--silt)] mt-2">
              <span>{{ trends[0]?.date }}</span>
              <span>{{ trends[trends.length - 1]?.date }}</span>
            </div>

            <!-- Hover tooltip -->
            <div
              v-if="hoveredTrendIndex !== null && trends[hoveredTrendIndex]"
              class="absolute top-2 right-2 p-2 rounded bg-[var(--river)] text-[color:var(--palm-leaf)] text-xs shadow-[var(--shadow-float)] space-y-0.5"
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
              <p class="text-xs text-[var(--silt)]">Net room revenue recognized per stay service date.</p>
            </div>
            <span class="text-xs tabular-nums text-[color:var(--laterite)] dark:text-[color:var(--laterite)] font-semibold">
              Peak: {{ money(maxRevenueValue) }}
            </span>
          </div>

          <div v-if="trends.length === 0" class="h-48 flex items-center justify-center text-sm text-[var(--silt)]">
            No daily trend points in selected range.
          </div>
          <div v-else class="relative h-48 w-full">
            <svg class="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 60">
              <!-- Area fill & stroke line for revenue -->
              <polyline
                fill="none"
                stroke="currentColor"
                class="text-[var(--status-available)] dark:text-[color:var(--laterite)]"
                stroke-width="2"
                :points="trends.map((p, i) => `${((i + 0.5) / trends.length) * 100},${50 - (p.revenue_minor / maxRevenueValue) * 45}`).join(' ')"
              />
              <circle
                v-for="(p, i) in trends"
                :key="i"
                :cx="((i + 0.5) / trends.length) * 100"
                :cy="50 - (p.revenue_minor / maxRevenueValue) * 45"
                r="1.5"
                class="fill-[var(--status-available)] "
              />
            </svg>

            <div class="flex justify-between text-[10px] text-[var(--silt)] mt-2">
              <span>{{ trends[0]?.date }}</span>
              <span>{{ trends[trends.length - 1]?.date }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Section 4: Room-Type Performance Table -->
      <div class="card overflow-hidden">
        <div class="p-6 border-b border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)] flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 class="text-xl font-serif">Room-Type Performance Breakdown</h3>
            <p class="text-xs text-[var(--silt)] mt-0.5">Comparative yield, sellable nights, and ADR across room inventory categories.</p>
          </div>
          <span class="text-xs text-[var(--silt)]">
            Total Inventory: {{ readiness?.total }} rooms
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="data-table w-full text-left text-sm">
            <thead>
              <tr class="bg-[var(--sunk)] text-[color:var(--river)] border-b border-[color:var(--rule)] dark:bg-[var(--sunk)] dark:text-[color:var(--river)] dark:border-[color:var(--rule)]">
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
                class="border-t border-[color:var(--rule)] dark:border-[color:var(--rule)] hover:bg-[var(--sunk)]/60 dark:hover:bg-[var(--sunk)]/60 transition"
              >
                <td class="p-4 font-medium">{{ rt.name }}</td>
                <td class="p-4">{{ rt.total_rooms }}</td>
                <td class="p-4">{{ money(rt.nightly_rate_minor) }}</td>
                <td class="p-4">{{ rt.sellable_room_nights }}</td>
                <td class="p-4 font-semibold">{{ rt.sold_room_nights }}</td>
                <td class="p-4">
                  <span
                    class="px-2 py-0.5 rounded text-xs font-medium"
                    :class="(rt.occupancy_rate_percent || 0) >= 70 ? 'bg-[var(--status-available)]/10 text-[var(--status-available)] ' : 'bg-[var(--sunk)] text-[var(--ink)] '"
                  >
                    {{ rt.occupancy_rate_percent !== null ? `${rt.occupancy_rate_percent}%` : 'N/A' }}
                  </span>
                </td>
                <td class="p-4 tabular-nums font-medium">{{ money(rt.net_room_revenue_minor) }}</td>
                <td class="p-4 tabular-nums">{{ rt.adr_minor !== null ? money(rt.adr_minor) : 'N/A' }}</td>
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
            <div class="flex items-center justify-between p-3 rounded-lg bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)]">
              <span class="text-sm">Expected Arrivals</span>
              <span class="font-bold text-base">{{ operations.arrivals.total }}</span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-xs">
              <div class="p-2 rounded bg-[var(--status-available)]/10 text-[var(--status-available)] ">
                Checked in: <strong>{{ operations.arrivals.checked_in }}</strong>
              </div>
              <div class="p-2 rounded bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] ">
                Pending: <strong>{{ operations.arrivals.pending }}</strong>
              </div>
            </div>

            <div class="flex items-center justify-between p-3 rounded-lg bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)] mt-2">
              <span class="text-sm">Expected Departures</span>
              <span class="font-bold text-base">{{ operations.departures.total }}</span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-xs">
              <div class="p-2 rounded bg-[var(--sunk)] text-[var(--ink)] ">
                Checked out: <strong>{{ operations.departures.checked_out }}</strong>
              </div>
              <div class="p-2 rounded bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] ">
                In-house: <strong>{{ operations.departures.pending }}</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- Card 2: Room Readiness Distribution -->
        <div v-if="readiness" class="card p-6 space-y-4">
          <h3 class="text-lg font-serif">Room Readiness Status</h3>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between items-center py-1 border-b border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[var(--status-available)]" /> Ready for Check-in</span>
              <span class="font-bold">{{ readiness.ready }}</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[var(--status-occupied)]" /> Cleaning in Progress</span>
              <span class="font-bold">{{ readiness.cleaning }}</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[var(--status-occupied)]" /> Inspection Pending</span>
              <span class="font-bold">{{ readiness.inspection }}</span>
            </div>
            <div class="flex justify-between items-center py-1 border-b border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)]">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[var(--status-dirty)]" /> Dirty (Awaiting Turnover)</span>
              <span class="font-bold">{{ readiness.dirty }}</span>
            </div>
            <div class="flex justify-between items-center py-1">
              <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[var(--status-out)]" /> Out of Service (Maintenance)</span>
              <span class="font-bold">{{ readiness.out_of_service }}</span>
            </div>
          </div>

          <!-- Unready Arrivals Alert if any -->
          <div v-if="operations.unready_arrivals_today.length > 0" class="p-3 rounded-lg bg-[var(--status-out)]/10 border border-[var(--status-out)]/30  text-xs text-[var(--status-out)] ">
            <strong>Urgent Turnover Needed:</strong>
            {{ operations.unready_arrivals_today.length }} room(s) with arrival today not yet ready!
          </div>
        </div>

        <!-- Card 3: Quality & Exceptions Queue -->
        <div class="card p-6 space-y-4">
          <h3 class="text-lg font-serif">Exceptions & Pending Queue</h3>
          <div class="space-y-2.5 text-xs">
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)]">
              <span>Active Maintenance Tickets</span>
              <span class="font-bold tabular-nums px-2 py-0.5 rounded bg-[var(--sunk)] text-[var(--ink)] ">
                {{ operations.open_maintenance.length }}
              </span>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)]">
              <span>Open Guest Service Requests</span>
              <span class="font-bold tabular-nums px-2 py-0.5 rounded bg-[var(--sunk)] text-[var(--ink)] ">
                {{ operations.open_requests.length }}
              </span>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)]">
              <span>Pending Refunds for Review</span>
              <span class="font-bold tabular-nums px-2 py-0.5 rounded" :class="operations.pending_refunds.length > 0 ? 'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] font-bold' : 'bg-[var(--sunk)] text-[var(--ink)] '">
                {{ operations.pending_refunds.length }}
              </span>
            </div>
            <div class="flex justify-between items-center p-2.5 rounded bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)]">
              <span>Payment Exceptions</span>
              <span class="font-bold tabular-nums px-2 py-0.5 rounded" :class="operations.payment_exceptions_count > 0 ? 'bg-[var(--status-out)]/10 text-[var(--status-out)] font-bold' : 'bg-[var(--sunk)] text-[var(--ink)] '">
                {{ operations.payment_exceptions_count }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
