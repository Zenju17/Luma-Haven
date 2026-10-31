<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import PortalLayout from '../../layouts/PortalLayout.vue'
import ManagerDashboard from '../manager/ManagerDashboard.vue'
import Notice from '../../components/Notice.vue'
import { staffApi, queryClient } from '../../services/api'
import {
  money,
  type Booking,
  type GuestRequest,
  type RefundRecord,
  type Room,
  type RoomTypeRate,
  type StaffUser,
  type Task
} from '../../types'

const user = ref<StaffUser | null>(null)
const username = ref('')
const password = ref('')
const error = ref('')
const successNotice = ref('')
const busy = ref(false)

const identity = useQuery({ queryKey: ['auth', 'me', 'staff'], queryFn: () => staffApi<StaffUser>('/auth/me') })
watch(identity.data, current => {
  if (current && 'username' in current) user.value = current
}, { immediate: true })

const role = computed(() => user.value?.role)
const hasStaff = computed(() => Boolean(user.value))
const isManagerOrAdmin = computed(() => ['ADMIN', 'MANAGER', 'ACCOUNTANT'].includes(role.value || ''))
const canClean = computed(() => ['ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING'].includes(role.value || ''))
const canServe = computed(() => ['ADMIN', 'MANAGER', 'RECEPTION'].includes(role.value || ''))
const canSeeReservations = computed(() => ['ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT'].includes(role.value || ''))

// Active Tab
const tab = ref<'operations' | 'reservations' | 'refunds' | 'rates' | 'manager'>('operations')

const summary = useQuery({
  queryKey: computed(() => ['summary', role.value]),
  queryFn: () => staffApi<Record<string, number>>('/dashboard/summary'),
  enabled: hasStaff,
})
const rooms = useQuery({
  queryKey: computed(() => ['rooms', role.value]),
  queryFn: () => staffApi<Room[]>('/rooms'),
  enabled: hasStaff,
})
const tasks = useQuery({
  queryKey: computed(() => ['tasks', role.value]),
  queryFn: () => staffApi<Task[]>('/housekeeping/tasks'),
  enabled: canClean,
})
const requests = useQuery({
  queryKey: computed(() => ['requests', role.value]),
  queryFn: () => staffApi<GuestRequest[]>('/staff/service-requests'),
  enabled: canServe,
})
const reservations = useQuery({
  queryKey: computed(() => ['staff-reservations', role.value]),
  queryFn: () => staffApi<Booking[]>('/staff/reservations'),
  enabled: canSeeReservations,
})
const refunds = useQuery({
  queryKey: computed(() => ['staff-refunds', role.value]),
  queryFn: () => staffApi<RefundRecord[]>('/staff/refunds'),
  enabled: isManagerOrAdmin,
})
const rates = useQuery({
  queryKey: computed(() => ['staff-rates', role.value]),
  queryFn: () => staffApi<RoomTypeRate[]>('/staff/rates'),
  enabled: isManagerOrAdmin,
})

// Search query for reservations
const searchReservationQuery = ref('')
const filteredReservations = computed(() => {
  const q = searchReservationQuery.value.trim().toLowerCase()
  if (!q) return reservations.data.value || []
  return (reservations.data.value || []).filter(b =>
    b.reference.toLowerCase().includes(q) ||
    b.guest_name.toLowerCase().includes(q) ||
    b.room.toLowerCase().includes(q) ||
    b.status.toLowerCase().includes(q)
  )
})

// Modals State
const detailBooking = ref<Booking | null>(null)

// Amend Modal
const amendBooking = ref<Booking | null>(null)
const amendArrival = ref('')
const amendDeparture = ref('')
const amendOccupants = ref(1)

function openAmend(b: Booking) {
  amendBooking.value = b
  amendArrival.value = b.arrival
  amendDeparture.value = b.departure
  // Extract occupants from entries or default to 2
  amendOccupants.value = 2
  error.value = ''
  successNotice.value = ''
}

// Reassign Room Modal
const reassignBooking = ref<Booking | null>(null)
const targetRoomId = ref<number | ''>('')

function openReassign(b: Booking) {
  reassignBooking.value = b
  targetRoomId.value = ''
  error.value = ''
  successNotice.value = ''
}

// Refund Request Modal
const refundReqBooking = ref<Booking | null>(null)
const refundAmountDollars = ref('')
const refundReason = ref('')

function openRequestRefund(b: Booking) {
  refundReqBooking.value = b
  refundAmountDollars.value = ''
  refundReason.value = ''
  error.value = ''
  successNotice.value = ''
}

// Rate Update Modal
const editingRate = ref<RoomTypeRate | null>(null)
const newRateDollars = ref('')

function openEditRate(rt: RoomTypeRate) {
  editingRate.value = rt
  newRateDollars.value = (rt.nightly_rate_minor / 100).toFixed(2)
  error.value = ''
  successNotice.value = ''
}

async function signIn() {
  error.value = ''
  busy.value = true
  try {
    const account = await staffApi<StaffUser>('/auth/login', { username: username.value, password: password.value })
    password.value = ''
    queryClient.clear()
    user.value = account
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

async function signOut() {
  try {
    await staffApi('/auth/logout', {})
    user.value = null
    queryClient.clear()
  } catch (caught) {
    error.value = String(caught)
  }
}

async function act(action: () => Promise<unknown>, successMsg = '') {
  error.value = ''
  successNotice.value = ''
  busy.value = true
  try {
    await action()
    if (successMsg) successNotice.value = successMsg
    await Promise.all([
      summary.refetch(),
      rooms.refetch(),
      ...(canClean.value ? [tasks.refetch()] : []),
      ...(canServe.value ? [requests.refetch()] : []),
      ...(canSeeReservations.value ? [reservations.refetch()] : []),
      ...(isManagerOrAdmin.value ? [refunds.refetch(), rates.refetch()] : []),
    ])
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

// Workflow action handlers
async function submitAmend() {
  if (!amendBooking.value) return
  const id = amendBooking.value.id
  await act(async () => {
    const updated = await staffApi<Booking>(`/staff/reservations/${id}/amend`, {
      arrival: amendArrival.value,
      departure: amendDeparture.value,
      occupants: amendOccupants.value,
    })
    amendBooking.value = null
    detailBooking.value = updated
  }, 'Reservation dates and charges successfully amended.')
}

async function submitReassign() {
  if (!reassignBooking.value || !targetRoomId.value) return
  const id = reassignBooking.value.id
  await act(async () => {
    const updated = await staffApi<Booking>(`/staff/reservations/${id}/reassign`, {
      room_id: targetRoomId.value,
    })
    reassignBooking.value = null
    detailBooking.value = updated
  }, 'Room successfully reassigned.')
}

async function handleNoShow(b: Booking) {
  if (!confirm(`Mark reservation ${b.reference} for ${b.guest_name} as NO-SHOW? This will release the room inventory.`)) return
  await act(async () => {
    await staffApi(`/staff/reservations/${b.id}/no-show`, {})
  }, `Reservation ${b.reference} marked as No-Show.`)
}

async function submitRequestRefund() {
  if (!refundReqBooking.value) return
  const id = refundReqBooking.value.id
  const minor = Math.round(parseFloat(refundAmountDollars.value) * 100)
  if (isNaN(minor) || minor <= 0) {
    error.value = 'Please enter a valid positive refund amount.'
    return
  }
  await act(async () => {
    await staffApi(`/staff/reservations/${id}/request-refund`, {
      amount_minor: minor,
      reason: refundReason.value,
    })
    refundReqBooking.value = null
  }, 'Refund request submitted for management review.')
}

async function submitApproveRefund(r: RefundRecord) {
  await act(async () => {
    await staffApi(`/staff/refunds/${r.id}/approve`, {})
  }, `Refund #${r.id} approved.`)
}

async function submitSettleRefund(r: RefundRecord) {
  await act(async () => {
    await staffApi(`/staff/refunds/${r.id}/settle`, {})
  }, `Refund #${r.id} settled. Folio credited with ${money(r.amount_minor)}.`)
}

async function submitRejectRefund(r: RefundRecord) {
  const reason = prompt('Reason for rejection:')
  if (reason === null) return
  await act(async () => {
    await staffApi(`/staff/refunds/${r.id}/reject`, { reason })
  }, `Refund #${r.id} rejected.`)
}

async function submitRateUpdate() {
  if (!editingRate.value) return
  const id = editingRate.value.id
  const minor = Math.round(parseFloat(newRateDollars.value) * 100)
  if (isNaN(minor) || minor <= 0) {
    error.value = 'Please enter a valid positive nightly rate.'
    return
  }
  await act(async () => {
    await staffApi(`/staff/rates/${id}`, { nightly_rate_minor: minor })
    editingRate.value = null
  }, `Nightly rate updated to ${money(minor)} with audit trail.`)
}

async function assignCleaner(task: Task, cleanerUsername: string) {
  await act(async () => {
    await staffApi(`/housekeeping/tasks/${task.id}/assign`, { username: cleanerUsername })
  }, `Task assigned to ${cleanerUsername}.`)
}

const nextStep: Record<string, string> = { DIRTY: 'CLEANING', CLEANING: 'INSPECTION', INSPECTION: 'READY' }
</script>

<template>
  <PortalLayout area="staff">
    <div v-if="identity.isPending.value" role="status" class="space-y-4">
      <p>Checking your staff session…</p>
      <div class="skeleton h-8 w-48" />
      <div class="skeleton h-32 w-full" />
    </div>

    <!-- Sign In Form -->
    <form v-else-if="!user" class="card portal-login p-8 max-w-md mx-auto space-y-5" @submit.prevent="signIn">
      <p class="label">Team access</p>
      <h1 class="text-3xl font-serif">Staff sign in</h1>
      <input v-model="username" class="field" placeholder="Username" aria-label="Username" required />
      <input v-model="password" class="field" placeholder="Password" aria-label="Password" type="password" required />
      <button class="btn w-full" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
      <Notice :message="error" />
    </form>

    <!-- Signed-In Staff Portal -->
    <div v-else class="space-y-6">
      <div class="flex flex-wrap justify-between items-center gap-4">
        <div>
          <p class="label">Operations · {{ user.role }}</p>
          <h1 class="text-4xl font-serif">Good to see you, {{ user.username }}.</h1>
        </div>
        <div class="flex items-center gap-3">
          <RouterLink v-if="isManagerOrAdmin" to="/manager" class="btn-secondary text-xs">Manager View</RouterLink>
          <button class="btn-secondary text-xs" :disabled="busy" @click="signOut">Sign out</button>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <nav class="flex flex-wrap gap-2 border-b border-[var(--line,#e2e8e0)] dark:border-[#1a3330] pb-3" aria-label="Staff navigation">
        <button
          type="button"
          class="px-4 py-2 rounded-lg text-sm transition"
          :class="tab === 'operations' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] font-semibold' : 'btn-secondary'"
          @click="tab = 'operations'"
        >
          Daily Operations
        </button>

        <button
          v-if="canSeeReservations"
          type="button"
          class="px-4 py-2 rounded-lg text-sm transition"
          :class="tab === 'reservations' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] font-semibold' : 'btn-secondary'"
          @click="tab = 'reservations'"
        >
          Reservations & Amendments
        </button>

        <button
          v-if="isManagerOrAdmin"
          type="button"
          class="px-4 py-2 rounded-lg text-sm transition flex items-center gap-2"
          :class="tab === 'refunds' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] font-semibold' : 'btn-secondary'"
          @click="tab = 'refunds'"
        >
          Refunds & Reconciliation
          <span v-if="refunds.data.value?.filter(r => r.status === 'PENDING').length" class="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
        </button>

        <button
          v-if="isManagerOrAdmin"
          type="button"
          class="px-4 py-2 rounded-lg text-sm transition"
          :class="tab === 'rates' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] font-semibold' : 'btn-secondary'"
          @click="tab = 'rates'"
        >
          Room Rates & Pricing
        </button>

        <button
          v-if="isManagerOrAdmin"
          type="button"
          class="px-4 py-2 rounded-lg text-sm transition"
          :class="tab === 'manager' ? 'bg-[#0c2b26] text-white dark:bg-[#d7b683] dark:text-[#0c2b26] font-semibold' : 'btn-secondary'"
          @click="tab = 'manager'"
        >
          Manager Intelligence
        </button>
      </nav>

      <Notice :message="error" />
      <Notice :message="successNotice" status />

      <!-- TAB 1: OPERATIONS -->
      <section v-if="tab === 'operations'" class="space-y-8">
        <!-- Summary Metric Tiles -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div v-for="(value, key) in summary.data.value || {}" :key="key" class="card metric-card">
            <p class="label">{{ String(key).replaceAll('_', ' ') }}</p>
            <p class="text-3xl font-bold">{{ String(key).includes('minor') ? money(value) : value }}</p>
          </div>
        </div>

        <!-- Room Board -->
        <div>
          <h2 class="text-2xl font-serif mb-4">Room Board</h2>
          <Notice :message="rooms.error.value ? String(rooms.error.value) : ''" />
          <div class="grid md:grid-cols-4 gap-4">
            <div
              v-for="room in rooms.data.value"
              :key="room.id"
              class="card room-tile p-4 transition hover:shadow-md relative"
              :data-cleaning="room.cleaning"
              :data-service="room.in_service ? 'in' : 'out'"
            >
              <span
                class="absolute top-4 right-4 w-2.5 h-2.5 rounded-full"
                :class="{
                  'bg-emerald-500': room.cleaning === 'READY' && room.in_service,
                  'bg-sky-500': room.cleaning === 'CLEANING',
                  'bg-indigo-500': room.cleaning === 'INSPECTION',
                  'bg-amber-500': room.cleaning === 'DIRTY',
                  'bg-rose-500': !room.in_service
                }"
              />
              <span class="label">Room {{ room.number }}</span>
              <h3 class="text-xl font-serif mt-1">{{ room.type }}</h3>
              <p class="mt-2 text-xs text-[var(--muted)]">
                {{ room.occupied ? 'Occupied' : 'Vacant' }} · {{ room.cleaning }} · {{ room.in_service ? 'In service' : 'Out of service' }}
              </p>
              <p v-if="room.rate_minor" class="text-xs font-mono font-medium mt-2">
                {{ money(room.rate_minor) }} <span class="text-[10px] text-[var(--muted)]">/ night</span>
              </p>
            </div>
          </div>
        </div>

        <!-- Housekeeping Queue -->
        <div v-if="canClean">
          <h2 class="text-2xl font-serif mb-4">Housekeeping Queue</h2>
          <Notice :message="tasks.error.value ? String(tasks.error.value) : ''" />
          <p v-if="tasks.data.value?.length === 0" class="text-sm text-[var(--muted)]">No housekeeping tasks.</p>
          <div v-else class="space-y-3">
            <div v-for="task in tasks.data.value" :key="task.id" class="card queue-row p-4 flex flex-wrap items-center justify-between gap-3">
              <span>
                Room {{ task.room__number }} · {{ task.status }}
                <span v-if="task.assignee__username" class="text-xs text-[var(--muted)] ml-2 font-normal">
                  (Assigned: {{ task.assignee__username }})
                </span>
                <span v-else class="text-xs text-amber-600 dark:text-amber-400 ml-2 font-normal">
                  (Unassigned)
                </span>
              </span>
              <div class="flex items-center gap-2">
                <button
                  v-if="isManagerOrAdmin && !task.assignee__username"
                  class="btn-secondary text-xs"
                  :disabled="busy"
                  @click="assignCleaner(task, user?.username || '')"
                >
                  Assign to me
                </button>
                <button
                  v-if="task.status !== 'READY' && !(task.status === 'INSPECTION' && role === 'HOUSEKEEPING')"
                  class="btn-secondary text-xs"
                  :disabled="busy"
                  @click="act(() => staffApi(`/housekeeping/tasks/${task.id}/transition`, { status: nextStep[task.status] }))"
                >
                  Next step →
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Guest Service Requests -->
        <div v-if="canServe">
          <h2 class="text-2xl font-serif mb-4">Guest Requests</h2>
          <Notice :message="requests.error.value ? String(requests.error.value) : ''" />
          <p v-if="requests.data.value?.length === 0" class="text-sm text-[var(--muted)]">No guest requests.</p>
          <div v-else class="space-y-3">
            <div v-for="request in requests.data.value" :key="request.id" class="card queue-row p-4 flex justify-between items-center">
              <span>{{ request.type }} · {{ request.description }} · {{ request.status }}</span>
              <button
                v-if="request.status !== 'COMPLETED'"
                class="btn-secondary text-xs"
                :disabled="busy"
                @click="act(() => staffApi(`/staff/service-requests/${request.id}/complete`, {}))"
              >
                Complete
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- TAB 2: RESERVATIONS & AMENDMENTS -->
      <section v-else-if="tab === 'reservations'" class="space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 class="text-2xl font-serif">Reservation Management</h2>
            <p class="text-xs text-[var(--muted)]">Inspect folios, amend dates, reassign rooms, or record cancellations and no-shows.</p>
          </div>
          <div class="flex items-center gap-3">
            <span v-if="searchReservationQuery" class="text-xs text-[var(--muted)]">
              Showing {{ filteredReservations.length }} of {{ reservations.data.value?.length || 0 }}
            </span>
            <div class="relative w-64">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--muted)]">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </div>
              <input
                v-model="searchReservationQuery"
                type="search"
                placeholder="Search reference, guest, room…"
                class="field pl-8 pr-7 py-1.5 text-xs w-full rounded-lg"
              />
              <button
                v-if="searchReservationQuery"
                type="button"
                class="absolute inset-y-0 right-0 pr-2.5 flex items-center text-xs text-[var(--muted)] hover:text-inherit"
                title="Clear search"
                @click="searchReservationQuery = ''"
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        <div v-if="reservations.isPending.value" role="status">Loading reservations…</div>
        <Notice :message="reservations.error.value ? String(reservations.error.value) : ''" />

        <div v-if="filteredReservations.length === 0" class="card p-8 text-center text-sm text-[var(--muted)]">
          No matching reservations found.
        </div>

        <div v-else class="card overflow-auto">
          <table class="data-table w-full text-left text-sm min-w-[980px]">
            <thead>
              <tr class="bg-[#f0f6f4] text-[#1f3330] border-b border-[#cbdad4] dark:bg-[#0c1c1a] dark:text-[#d8ece4] dark:border-[#1a3330]">
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb] w-28">Reference</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Guest</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Room</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Stay Dates</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Status</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb] text-right">Balance</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb] text-right min-w-[340px]">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="b in filteredReservations" :key="b.id" class="border-t border-[#cbdad4] dark:border-[#1a3330] hover:bg-[#f0f6f4]/60 dark:hover:bg-[#122523]/60 transition">
                <td class="py-3 px-4 font-mono font-bold text-xs text-[#0c2b26] dark:text-[#88e2cb] whitespace-nowrap">{{ b.reference }}</td>
                <td class="py-3 px-4 font-medium whitespace-nowrap">{{ b.guest_name }}</td>
                <td class="py-3 px-4 whitespace-nowrap">
                  <span class="font-medium">Room {{ b.room }}</span>
                  <span class="text-xs text-[var(--muted)] ml-1">({{ b.room_type }})</span>
                </td>
                <td class="py-3 px-4 text-xs font-mono text-[var(--muted)] whitespace-nowrap">
                  <span>{{ b.arrival }}</span>
                  <span class="mx-1 text-[#9ab4ac]">→</span>
                  <span>{{ b.departure }}</span>
                </td>
                <td class="py-3 px-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide border uppercase"
                    :class="{
                      'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/50': b.status === 'CONFIRMED',
                      'bg-teal-50 text-teal-800 border-teal-200 dark:bg-teal-950/60 dark:text-teal-300 dark:border-teal-800/50': b.status === 'CHECKED_IN',
                      'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700/50': b.status === 'CHECKED_OUT',
                      'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/50': b.status === 'HOLD',
                      'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/50': b.status === 'CANCELLED' || b.status === 'NO_SHOW'
                    }"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full"
                      :class="{
                        'bg-emerald-500': b.status === 'CONFIRMED',
                        'bg-teal-500': b.status === 'CHECKED_IN',
                        'bg-slate-400': b.status === 'CHECKED_OUT',
                        'bg-amber-500': b.status === 'HOLD',
                        'bg-rose-500': b.status === 'CANCELLED' || b.status === 'NO_SHOW'
                      }"
                    />
                    {{ b.status.replace('_', ' ') }}
                  </span>
                </td>
                <td class="py-3 px-4 font-mono text-xs text-right whitespace-nowrap" :class="b.balance_minor > 0 ? 'text-amber-800 dark:text-amber-400 font-bold' : 'text-[var(--muted)]'">
                  {{ money(b.balance_minor) }}
                </td>
                <td class="py-3 px-4 text-right whitespace-nowrap">
                  <div class="table-actions">
                    <button
                      type="button"
                      class="table-action-btn table-action-btn-primary"
                      title="Inspect Folio & Billing"
                      @click="detailBooking = b"
                    >
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                      </svg>
                      <span>Folio</span>
                    </button>

                    <template v-if="b.status === 'CONFIRMED' || b.status === 'HOLD'">
                      <button
                        type="button"
                        class="table-action-btn"
                        title="Amend Reservation Dates"
                        @click="openAmend(b)"
                      >
                        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                        </svg>
                        <span>Amend</span>
                      </button>
                      <button
                        type="button"
                        class="table-action-btn"
                        title="Reassign Room"
                        @click="openReassign(b)"
                      >
                        <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
                        </svg>
                        <span>Reassign</span>
                      </button>
                    </template>

                    <button
                      v-if="isManagerOrAdmin && b.status !== 'HOLD'"
                      type="button"
                      class="table-action-btn"
                      title="Request or Issue Refund"
                      @click="openRequestRefund(b)"
                    >
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M16 15v-1a4 4 0 00-4-4H8m0 0l3 3m-3-3l3-3m9 14V5a2 2 0 00-2-2H6a2 2 0 00-2 2v16l4-2 4 2 4-2 4 2z"/>
                      </svg>
                      <span>Refund</span>
                    </button>

                    <button
                      v-if="b.status === 'CONFIRMED' || b.status === 'HOLD'"
                      type="button"
                      class="table-action-btn table-action-btn-danger"
                      title="Mark as Guest No-Show"
                      @click="handleNoShow(b)"
                    >
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                      </svg>
                      <span>No-Show</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- TAB 3: REFUNDS & RECONCILIATION -->
      <section v-else-if="tab === 'refunds'" class="space-y-6">
        <div>
          <h2 class="text-2xl font-serif">Refund Management & Ledger Reconciliation</h2>
          <p class="text-xs text-[var(--muted)]">Two-person review control: refunds requested by staff require approval and settlement by management before folio credits are posted.</p>
        </div>

        <div v-if="refunds.isPending.value" role="status">Loading refunds ledger…</div>
        <Notice :message="refunds.error.value ? String(refunds.error.value) : ''" />

        <div v-if="refunds.data.value?.length === 0" class="card p-8 text-center text-sm text-[var(--muted)]">
          No refund records in ledger.
        </div>

        <div v-else class="card overflow-auto">
          <table class="data-table w-full text-left text-sm min-w-[920px]">
            <thead>
              <tr class="bg-[#f0f6f4] text-[#1f3330] border-b border-[#cbdad4] dark:bg-[#0c1c1a] dark:text-[#d8ece4] dark:border-[#1a3330]">
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb] w-24">Refund ID</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb] w-32">Reservation Ref</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Guest</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Amount</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Reason</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Status</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb]">Requested By</th>
                <th class="py-3 px-4 font-semibold text-xs tracking-wider uppercase text-[#35534c] dark:text-[#a5c4bb] text-right min-w-[260px]">Review Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in refunds.data.value" :key="r.id" class="border-t border-[#cbdad4] dark:border-[#1a3330] hover:bg-[#f0f6f4]/60 dark:hover:bg-[#122523]/60 transition">
                <td class="py-3 px-4 font-mono font-medium whitespace-nowrap">#{{ r.id }}</td>
                <td class="py-3 px-4 font-mono font-bold text-xs text-[#0c2b26] dark:text-[#88e2cb] whitespace-nowrap">{{ r.reservation_reference }}</td>
                <td class="py-3 px-4 font-medium whitespace-nowrap">{{ r.guest_name }}</td>
                <td class="py-3 px-4 font-mono font-bold whitespace-nowrap">{{ money(r.amount_minor) }}</td>
                <td class="py-3 px-4 text-xs max-w-xs">{{ r.reason }}</td>
                <td class="py-3 px-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide border uppercase"
                    :class="{
                      'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/60 dark:text-amber-200 dark:border-amber-800/50': r.status === 'PENDING',
                      'bg-sky-50 text-sky-800 border-sky-200 dark:bg-sky-950/60 dark:text-sky-200 dark:border-sky-800/50': r.status === 'APPROVED',
                      'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-200 dark:border-emerald-800/50': r.status === 'SETTLED',
                      'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/60 dark:text-rose-200 dark:border-rose-800/50': r.status === 'REJECTED'
                    }"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full"
                      :class="{
                        'bg-amber-500': r.status === 'PENDING',
                        'bg-sky-500': r.status === 'APPROVED',
                        'bg-emerald-500': r.status === 'SETTLED',
                        'bg-rose-500': r.status === 'REJECTED'
                      }"
                    />
                    {{ r.status }}
                  </span>
                </td>
                <td class="py-3 px-4 text-xs text-[var(--muted)] whitespace-nowrap">{{ r.requested_by || 'system' }}</td>
                <td class="py-3 px-4 text-right whitespace-nowrap">
                  <div class="table-actions">
                    <button
                      v-if="r.status === 'PENDING'"
                      type="button"
                      class="table-action-btn"
                      :disabled="busy"
                      title="Approve refund request"
                      @click="submitApproveRefund(r)"
                    >
                      <svg class="w-3.5 h-3.5 shrink-0 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      <span>Approve</span>
                    </button>
                    <button
                      v-if="r.status === 'APPROVED' || r.status === 'PENDING'"
                      type="button"
                      class="table-action-btn table-action-btn-primary"
                      :disabled="busy"
                      title="Settle refund and post credit to folio"
                      @click="submitSettleRefund(r)"
                    >
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                      <span>Settle & Credit</span>
                    </button>
                    <button
                      v-if="r.status === 'PENDING' || r.status === 'APPROVED'"
                      type="button"
                      class="table-action-btn table-action-btn-danger"
                      :disabled="busy"
                      title="Reject refund request"
                      @click="submitRejectRefund(r)"
                    >
                      <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                      <span>Reject</span>
                    </button>
                    <span
                      v-if="r.status === 'SETTLED'"
                      class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/50"
                    >
                      <svg class="w-3 h-3 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      Settled
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- TAB 4: ROOM RATES & PRICING -->
      <section v-else-if="tab === 'rates'" class="space-y-6">
        <div>
          <h2 class="text-2xl font-serif">Room Rate Management</h2>
          <p class="text-xs text-[var(--muted)]">Adjust inventory nightly rates. Changes are immutably audited and reflected in real-time booking quotes.</p>
        </div>

        <div v-if="rates.isPending.value" role="status">Loading room rates…</div>
        <Notice :message="rates.error.value ? String(rates.error.value) : ''" />

        <div class="grid md:grid-cols-2 gap-6">
          <div v-for="rt in rates.data.value" :key="rt.id" class="card p-6 flex flex-col justify-between space-y-4">
            <div>
              <div class="flex items-center justify-between">
                <span class="label">Room Category</span>
                <span class="text-xs text-[var(--muted)]">{{ rt.total_rooms }} rooms in inventory</span>
              </div>
              <h3 class="text-2xl font-serif mt-1">{{ rt.name }}</h3>
              <p class="text-sm text-[var(--muted)] mt-2">{{ rt.description || 'Luxury accommodation at Luma Haven.' }}</p>
              <p class="text-xs text-[var(--muted)] mt-1">Capacity: Up to {{ rt.capacity }} guests</p>
            </div>

            <div class="flex items-baseline justify-between pt-4 border-t border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
              <div>
                <span class="text-2xl font-bold font-mono">{{ money(rt.nightly_rate_minor) }}</span>
                <span class="text-xs text-[var(--muted)]"> / night</span>
              </div>
              <button type="button" class="btn-secondary text-xs" @click="openEditRate(rt)">
                Adjust Rate ✎
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- TAB 5: MANAGER INTELLIGENCE DASHBOARD -->
      <section v-else-if="tab === 'manager' && isManagerOrAdmin">
        <ManagerDashboard portal="staff" :user="user" @navigate="d => tab = (d === 'reservations' || d === 'rates' || d === 'refunds' ? d : 'operations')" />
      </section>
    </div>

    <!-- MODAL 1: RESERVATION DETAILS & FOLIO INSPECTOR -->
    <Transition name="modal">
      <div v-if="detailBooking" class="modal-backdrop" role="dialog" aria-modal="true" @click.self="detailBooking = null">
        <div class="card p-8 w-full max-w-2xl max-h-[90vh] overflow-y-auto space-y-6">
          <div class="flex justify-between items-start">
            <div>
              <span class="label">Folio Inspector</span>
              <h3 class="text-2xl font-serif">Reservation {{ detailBooking.reference }}</h3>
              <p class="text-sm text-[var(--muted)]">Guest: {{ detailBooking.guest_name }} · Room {{ detailBooking.room }} ({{ detailBooking.room_type }})</p>
            </div>
            <button type="button" class="text-xl" @click="detailBooking = null">✕</button>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-lg bg-[#f0f6f4] border border-[#cbdad4] text-[#1f3330] dark:bg-[#122523] dark:border-[#1a3330] dark:text-[#d8ece4] text-xs">
            <div><span class="label text-[10px]">Arrival</span><p class="font-medium">{{ detailBooking.arrival }}</p></div>
            <div><span class="label text-[10px]">Departure</span><p class="font-medium">{{ detailBooking.departure }}</p></div>
            <div><span class="label text-[10px]">Status</span><p class="font-medium">{{ detailBooking.status }}</p></div>
            <div><span class="label text-[10px]">Balance</span><p class="font-mono font-bold" :class="detailBooking.balance_minor > 0 ? 'text-amber-800 dark:text-amber-400' : 'text-emerald-700 dark:text-emerald-400'">{{ money(detailBooking.balance_minor) }}</p></div>
          </div>

          <!-- Folio Entries Immutable Ledger Table -->
          <div>
            <h4 class="text-lg font-serif mb-2">Folio Ledger Entries (Immutable)</h4>
            <div class="card overflow-hidden">
              <table class="data-table w-full text-left text-xs">
                <thead>
                  <tr class="bg-[#f0f6f4] text-[#1f3330] border-b border-[#cbdad4] dark:bg-[#0c1c1a] dark:text-[#d8ece4] dark:border-[#1a3330]">
                    <th class="p-3">Category</th>
                    <th class="p-3">Description</th>
                    <th class="p-3">Service Date</th>
                    <th class="p-3 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(entry, idx) in detailBooking.entries" :key="idx" class="border-t border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
                    <td class="p-3 font-semibold">{{ entry.category }}</td>
                    <td class="p-3">{{ entry.description }}</td>
                    <td class="p-3 font-mono">{{ entry.service_date }}</td>
                    <td class="p-3 text-right font-mono" :class="entry.amount_minor < 0 ? 'text-emerald-600 dark:text-emerald-400' : ''">
                      {{ money(entry.amount_minor) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-[var(--line,#e2e8e0)] dark:border-[#1a3330]">
            <button type="button" class="btn-secondary text-xs" @click="detailBooking = null">Close</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- MODAL 2: AMEND RESERVATION -->
    <Transition name="modal">
      <div v-if="amendBooking" class="modal-backdrop" role="dialog" aria-modal="true" @click.self="amendBooking = null">
        <form class="card p-8 w-full max-w-lg space-y-5" @submit.prevent="submitAmend">
          <div class="flex justify-between items-start">
            <div>
              <span class="label">Operational Amendment</span>
              <h3 class="text-2xl font-serif">Amend Reservation</h3>
              <p class="text-xs text-[var(--muted)]">Ref: {{ amendBooking.reference }} · Current: {{ amendBooking.arrival }} to {{ amendBooking.departure }}</p>
            </div>
            <button type="button" class="text-xl" @click="amendBooking = null">✕</button>
          </div>

          <div>
            <label class="label">New Arrival Date</label>
            <input v-model="amendArrival" type="date" class="field w-full" required />
          </div>

          <div>
            <label class="label">New Departure Date</label>
            <input v-model="amendDeparture" type="date" class="field w-full" required />
          </div>

          <div>
            <label class="label">Number of Occupants</label>
            <input v-model.number="amendOccupants" type="number" min="1" max="8" class="field w-full" required />
          </div>

          <p class="text-xs text-[var(--muted)]">
            Amending dates performs real-time database exclusion checks and automatically posts immutable folio adjustments for rate differences.
          </p>

          <Notice :message="error" />
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="btn-secondary text-xs" @click="amendBooking = null">Cancel</button>
            <button type="submit" class="btn text-xs" :disabled="busy">{{ busy ? 'Saving…' : 'Apply Amendment' }}</button>
          </div>
        </form>
      </div>
    </Transition>

    <!-- MODAL 3: REASSIGN ROOM -->
    <Transition name="modal">
      <div v-if="reassignBooking" class="modal-backdrop" role="dialog" aria-modal="true" @click.self="reassignBooking = null">
        <form class="card p-8 w-full max-w-lg space-y-5" @submit.prevent="submitReassign">
          <div class="flex justify-between items-start">
            <div>
              <span class="label">Inventory Reassignment</span>
              <h3 class="text-2xl font-serif">Reassign Room</h3>
              <p class="text-xs text-[var(--muted)]">Ref: {{ reassignBooking.reference }} · Currently in Room {{ reassignBooking.room }}</p>
            </div>
            <button type="button" class="text-xl" @click="reassignBooking = null">✕</button>
          </div>

          <div>
            <label class="label">Select Target Room</label>
            <select v-model.number="targetRoomId" class="field w-full" required>
              <option disabled value="">Choose available room…</option>
              <option
                v-for="r in (rooms.data.value || []).filter(rm => rm.number !== reassignBooking?.room && rm.in_service)"
                :key="r.id"
                :value="r.id"
              >
                Room {{ r.number }} ({{ r.type }} · Capacity: {{ r.capacity }} · {{ r.cleaning }})
              </option>
            </select>
          </div>

          <p class="text-xs text-[var(--muted)]">
            Transfers booking allocation under row-level database locking. If room rates differ, an adjustment entry is automatically posted to the folio.
          </p>

          <Notice :message="error" />
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="btn-secondary text-xs" @click="reassignBooking = null">Cancel</button>
            <button type="submit" class="btn text-xs" :disabled="busy || !targetRoomId">{{ busy ? 'Reassigning…' : 'Confirm Reassignment' }}</button>
          </div>
        </form>
      </div>
    </Transition>

    <!-- MODAL 4: REQUEST REFUND -->
    <Transition name="modal">
      <div v-if="refundReqBooking" class="modal-backdrop" role="dialog" aria-modal="true" @click.self="refundReqBooking = null">
        <form class="card p-8 w-full max-w-lg space-y-5" @submit.prevent="submitRequestRefund">
          <div class="flex justify-between items-start">
            <div>
              <span class="label">Financial Control</span>
              <h3 class="text-2xl font-serif">Request Refund</h3>
              <p class="text-xs text-[var(--muted)]">Ref: {{ refundReqBooking.reference }} · Guest: {{ refundReqBooking.guest_name }}</p>
            </div>
            <button type="button" class="text-xl" @click="refundReqBooking = null">✕</button>
          </div>

          <div>
            <label class="label">Refund Amount ($ USD)</label>
            <input v-model="refundAmountDollars" type="number" step="0.01" min="0.01" placeholder="e.g. 150.00" class="field w-full" required />
          </div>

          <div>
            <label class="label">Reason for Refund</label>
            <textarea v-model="refundReason" rows="3" placeholder="Provide operational rationale for this refund request…" class="field w-full" required />
          </div>

          <p class="text-xs text-[var(--muted)]">
            Refund requests require secondary approval and settlement by management before cash is disbursed and folio credit is granted.
          </p>

          <Notice :message="error" />
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="btn-secondary text-xs" @click="refundReqBooking = null">Cancel</button>
            <button type="submit" class="btn text-xs" :disabled="busy || !refundAmountDollars || !refundReason">{{ busy ? 'Submitting…' : 'Submit Refund Request' }}</button>
          </div>
        </form>
      </div>
    </Transition>

    <!-- MODAL 5: ADJUST ROOM RATE -->
    <Transition name="modal">
      <div v-if="editingRate" class="modal-backdrop" role="dialog" aria-modal="true" @click.self="editingRate = null">
        <form class="card p-8 w-full max-w-lg space-y-5" @submit.prevent="submitRateUpdate">
          <div class="flex justify-between items-start">
            <div>
              <span class="label">Revenue Strategy</span>
              <h3 class="text-2xl font-serif">Update Room Rate</h3>
              <p class="text-xs text-[var(--muted)]">{{ editingRate.name }} · Current: {{ money(editingRate.nightly_rate_minor) }}/night</p>
            </div>
            <button type="button" class="text-xl" @click="editingRate = null">✕</button>
          </div>

          <div>
            <label class="label">New Nightly Rate ($ USD)</label>
            <input v-model="newRateDollars" type="number" step="0.01" min="1.00" class="field w-full" required />
          </div>

          <p class="text-xs text-[var(--muted)]">
            Updating room rates will affect all future quotes. An immutable audit record will log this rate modification with your staff username.
          </p>

          <Notice :message="error" />
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="btn-secondary text-xs" @click="editingRate = null">Cancel</button>
            <button type="submit" class="btn text-xs" :disabled="busy || !newRateDollars">{{ busy ? 'Updating…' : 'Save Rate' }}</button>
          </div>
        </form>
      </div>
    </Transition>
  </PortalLayout>
</template>
