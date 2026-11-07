<script setup lang="ts">
import AgreementGate from '../legal/AgreementGate.vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import PortalLayout, { type PortalNavItem } from '../../layouts/PortalLayout.vue'
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

const route = useRoute()
const router = useRouter()

const user = ref<StaffUser | null>(null)
const username = ref('')
const password = ref('')
const error = ref('')
const successNotice = ref('')
const busy = ref(false)
const identityChecked = ref(false)

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

// Active Tab with deep-linking & sync
const validTabs = ['operations', 'reservations', 'refunds', 'rates', 'manager'] as const
type TabType = typeof validTabs[number]

const tab = ref<TabType>(
  (route.query.tab && validTabs.includes(route.query.tab as TabType))
    ? (route.query.tab as TabType)
    : 'operations'
)

watch(() => route.query.tab, newTab => {
  if (newTab && typeof newTab === 'string' && validTabs.includes(newTab as TabType)) {
    tab.value = newTab as TabType
  }
})

const pendingRefunds = computed(() => Boolean(refunds.data.value?.some(r => r.status === 'PENDING')))
const navItems = computed<PortalNavItem[]>(() => {
  if (!user.value) return []
  const items: PortalNavItem[] = [{ id: 'operations', label: 'Daily Operations', icon: 'home' }]
  if (canSeeReservations.value) items.push({ id: 'reservations', label: 'Reservations & Amendments', icon: 'calendar' })
  if (isManagerOrAdmin.value) {
    items.push(
      { id: 'refunds', label: 'Refunds & Reconciliation', icon: 'coin', badge: pendingRefunds.value },
      { id: 'rates', label: 'Room Rates & Pricing', icon: 'tag' },
      { id: 'manager', label: 'Manager Intelligence', icon: 'chart' },
      { id: 'manager-view', label: 'Manager View', icon: 'report', group: 'more', to: '/manager' },
    )
  }
  return items
})

function setTab(nextTab: TabType) {
  tab.value = nextTab
  void router.replace({ query: { ...route.query, tab: nextTab } })
}

function handleManagerNavigate(destination: string) {
  const targetTab: TabType = (destination === 'reservations' || destination === 'rates' || destination === 'refunds')
    ? destination
    : 'operations'
  setTab(targetTab)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

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
async function recordStayTransition(action: 'check-in' | 'check-out') {
  if (!detailBooking.value || busy.value) return
  const booking = detailBooking.value
  await act(async () => {
    detailBooking.value = await staffApi<Booking>(`/reservations/${booking.id}/${action}`,
      action === 'check-out' ? { folio_version: booking.folio_version } : {})
  }, action === 'check-out' ? 'Guest checkout recorded. The room is awaiting housekeeping.' : 'Guest check-in recorded.')
}

async function recordVerification() {
  if (!detailBooking.value || !identityChecked.value || busy.value) return
  const id = detailBooking.value.id
  await act(async () => {
    detailBooking.value = await staffApi<Booking>(`/staff/reservations/${id}/verify`, { identity_checked: true })
    identityChecked.value = false
  }, 'In-person guest verification recorded.')
}

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
  <PortalLayout area="staff" :items="navItems" :active="tab" @select="setTab($event as TabType)">
    <AgreementGate portal="staff" :active="hasStaff" />
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
              class="card room-tile p-4 transition relative"
              :data-cleaning="room.cleaning"
              :data-service="room.in_service ? 'in' : 'out'"
            >
              <span
                class="status absolute top-4 right-4"
                :class="!room.in_service ? 'status--out' : room.cleaning === 'READY' ? 'status--available' : room.cleaning === 'DIRTY' ? 'status--dirty' : 'status--occupied'"
                aria-hidden="true"
              >{{ !room.in_service ? 'Out' : room.cleaning === 'READY' ? 'Ready' : room.cleaning === 'DIRTY' ? 'Dirty' : room.cleaning === 'INSPECTION' ? 'Inspection' : 'Cleaning' }}</span>
              <span class="label">Room {{ room.number }}</span>
              <h3 class="text-xl font-serif mt-1">{{ room.type }}</h3>
              <p class="mt-2 text-xs text-[var(--silt)]">
                {{ room.occupied ? 'Occupied' : 'Vacant' }} · {{ room.cleaning }} · {{ room.in_service ? 'In service' : 'Out of service' }}
              </p>
              <p v-if="room.rate_minor" class="text-xs tabular-nums font-medium mt-2">
                {{ money(room.rate_minor) }} <span class="text-[10px] text-[var(--silt)]">/ night</span>
              </p>
            </div>
          </div>
        </div>

        <!-- Housekeeping Queue -->
        <div v-if="canClean">
          <h2 class="text-2xl font-serif mb-4">Housekeeping Queue</h2>
          <Notice :message="tasks.error.value ? String(tasks.error.value) : ''" />
          <p v-if="tasks.data.value?.length === 0" class="text-sm text-[var(--silt)]">No housekeeping tasks.</p>
          <div v-else class="space-y-3">
            <div v-for="task in tasks.data.value" :key="task.id" class="card queue-row p-4 flex flex-wrap items-center justify-between gap-3">
              <span>
                Room {{ task.room__number }} · {{ task.status }}
                <span v-if="task.assignee__username" class="text-xs text-[var(--silt)] ml-2 font-normal">
                  (Assigned: {{ task.assignee__username }})
                </span>
                <span v-else class="text-xs text-[var(--status-dirty)] ml-2 font-normal">
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
          <p v-if="requests.data.value?.length === 0" class="text-sm text-[var(--silt)]">No guest requests.</p>
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
            <p class="text-xs text-[var(--silt)]">Inspect folios, amend dates, reassign rooms, or record cancellations and no-shows.</p>
          </div>
          <div class="flex items-center gap-3">
            <span v-if="searchReservationQuery" class="text-xs text-[var(--silt)]">
              Showing {{ filteredReservations.length }} of {{ reservations.data.value?.length || 0 }}
            </span>
            <div class="relative w-64">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--silt)]">
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
                class="absolute inset-y-0 right-0 pr-2.5 flex items-center text-xs text-[var(--silt)] hover:text-inherit"
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

        <div v-if="filteredReservations.length === 0" class="card p-8 text-center text-sm text-[var(--silt)]">
          No matching reservations found.
        </div>

        <div v-else class="card overflow-auto">
          <table class="data-table w-full text-left text-sm min-w-[980px]">
            <thead>
              <tr class="bg-[var(--sunk)] text-[color:var(--river)] border-b border-[color:var(--rule)] dark:bg-[var(--sunk)] dark:text-[color:var(--river)] dark:border-[color:var(--rule)]">
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] w-28">Reference</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Guest</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Room</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Stay Dates</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Status</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] text-right">Balance</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] text-right min-w-[340px]">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="b in filteredReservations" :key="b.id" class="border-t border-[color:var(--rule)] dark:border-[color:var(--rule)] hover:bg-[var(--sunk)]/60 dark:hover:bg-[var(--sunk)]/60 transition">
                <td class="py-3 px-4 tabular-nums font-bold text-xs text-[color:var(--river)] dark:text-[color:var(--status-available)] whitespace-nowrap">{{ b.reference }}</td>
                <td class="py-3 px-4 font-medium whitespace-nowrap">{{ b.guest_name }}</td>
                <td class="py-3 px-4 whitespace-nowrap">
                  <span class="font-medium">Room {{ b.room }}</span>
                  <span class="text-xs text-[var(--silt)] ml-1">({{ b.room_type }})</span>
                </td>
                <td class="py-3 px-4 text-xs tabular-nums text-[var(--silt)] whitespace-nowrap">
                  <span>{{ b.arrival }}</span>
                  <span class="mx-1 text-[color:var(--silt)]">→</span>
                  <span>{{ b.departure }}</span>
                </td>
                <td class="py-3 px-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide border "
                    :class="{
                      'bg-[var(--status-available)]/10 text-[var(--status-available)] border-[var(--status-available)]/30 ': b.status === 'CONFIRMED',
                      'bg-[var(--river)]/10 text-[var(--river)] border-[var(--river)]/30   ': b.status === 'CHECKED_IN',
                      'bg-[var(--sunk)] text-[var(--ink)] border-[var(--rule)]   ': b.status === 'CHECKED_OUT',
                      'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] border-[var(--status-dirty)]/30   ': b.status === 'HOLD',
                      'bg-[var(--status-out)]/10 text-[var(--status-out)] border-[var(--status-out)]/30   ': b.status === 'CANCELLED' || b.status === 'NO_SHOW'
                    }"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full"
                      :class="{
                        'bg-[var(--status-available)]': b.status === 'CONFIRMED',
 'bg-[var(--river)]': b.status === 'CHECKED_IN',
                        'bg-[var(--rule-strong)]': b.status === 'CHECKED_OUT',
                        'bg-[var(--status-dirty)]': b.status === 'HOLD',
                        'bg-[var(--status-out)]': b.status === 'CANCELLED' || b.status === 'NO_SHOW'
                      }"
                    />
                    {{ b.status.replace('_', ' ') }}
                  </span>
                </td>
                <td class="py-3 px-4 tabular-nums text-xs text-right whitespace-nowrap" :class="b.balance_minor > 0 ? 'text-[var(--status-dirty)] font-bold' : 'text-[var(--silt)]'">
                  {{ money(b.balance_minor) }}
                </td>
                <td class="py-3 px-4 text-right whitespace-nowrap">
                  <div class="table-actions">
                    <button
                      type="button"
                      class="table-action-btn table-action-btn-primary"
                      title="Inspect Folio & Billing"
                      @click="detailBooking = b; identityChecked = false"
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
          <p class="text-xs text-[var(--silt)]">Two-person review control: refunds requested by staff require approval and settlement by management before folio credits are posted.</p>
        </div>

        <div v-if="refunds.isPending.value" role="status">Loading refunds ledger…</div>
        <Notice :message="refunds.error.value ? String(refunds.error.value) : ''" />

        <div v-if="refunds.data.value?.length === 0" class="card p-8 text-center text-sm text-[var(--silt)]">
          No refund records in ledger.
        </div>

        <div v-else class="card overflow-auto">
          <table class="data-table w-full text-left text-sm min-w-[920px]">
            <thead>
              <tr class="bg-[var(--sunk)] text-[color:var(--river)] border-b border-[color:var(--rule)] dark:bg-[var(--sunk)] dark:text-[color:var(--river)] dark:border-[color:var(--rule)]">
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] w-24">Refund ID</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] w-32">Reservation Ref</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Guest</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Amount</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Reason</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Status</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)]">Requested By</th>
                <th class="py-3 px-4 font-semibold text-xs text-[color:var(--silt)] dark:text-[color:var(--silt)] text-right min-w-[260px]">Review Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in refunds.data.value" :key="r.id" class="border-t border-[color:var(--rule)] dark:border-[color:var(--rule)] hover:bg-[var(--sunk)]/60 dark:hover:bg-[var(--sunk)]/60 transition">
                <td class="py-3 px-4 tabular-nums font-medium whitespace-nowrap">#{{ r.id }}</td>
                <td class="py-3 px-4 tabular-nums font-bold text-xs text-[color:var(--river)] dark:text-[color:var(--status-available)] whitespace-nowrap">{{ r.reservation_reference }}</td>
                <td class="py-3 px-4 font-medium whitespace-nowrap">{{ r.guest_name }}</td>
                <td class="py-3 px-4 tabular-nums font-bold whitespace-nowrap">{{ money(r.amount_minor) }}</td>
                <td class="py-3 px-4 text-xs max-w-xs">{{ r.reason }}</td>
                <td class="py-3 px-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide border "
                    :class="{
                      'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] border-[var(--status-dirty)]/30 ': r.status === 'PENDING',
                      'bg-[var(--status-occupied)]/10 text-[var(--status-occupied)] border-[var(--status-occupied)]/30   ': r.status === 'APPROVED',
                      'bg-[var(--status-available)]/10 text-[var(--status-available)] border-[var(--status-available)]/30   ': r.status === 'SETTLED',
                      'bg-[var(--status-out)]/10 text-[var(--status-out)] border-[var(--status-out)]/30   ': r.status === 'REJECTED'
                    }"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full"
                      :class="{
                        'bg-[var(--status-dirty)]': r.status === 'PENDING',
 'bg-[var(--status-occupied)]': r.status === 'APPROVED',
                        'bg-[var(--status-available)]': r.status === 'SETTLED',
                        'bg-[var(--status-out)]': r.status === 'REJECTED'
                      }"
                    />
                    {{ r.status }}
                  </span>
                </td>
                <td class="py-3 px-4 text-xs text-[var(--silt)] whitespace-nowrap">{{ r.requested_by || 'system' }}</td>
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
                      <svg class="w-3.5 h-3.5 shrink-0 text-[var(--status-dirty)] " fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
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
                      class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[var(--status-available)]/10 text-[var(--status-available)] border border-[var(--status-available)]/30 "
                    >
                      <svg class="w-3 h-3 text-[var(--status-available)] " fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
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
          <p class="text-xs text-[var(--silt)]">Adjust inventory nightly rates. Changes are immutably audited and reflected in real-time booking quotes.</p>
        </div>

        <div v-if="rates.isPending.value" role="status">Loading room rates…</div>
        <Notice :message="rates.error.value ? String(rates.error.value) : ''" />

        <div class="grid md:grid-cols-2 gap-6">
          <div v-for="rt in rates.data.value" :key="rt.id" class="card p-6 flex flex-col justify-between space-y-4">
            <div>
              <div class="flex items-center justify-between">
                <span class="label">Room Category</span>
                <span class="text-xs text-[var(--silt)]">{{ rt.total_rooms }} rooms in inventory</span>
              </div>
              <h3 class="text-2xl font-serif mt-1">{{ rt.name }}</h3>
              <p class="text-sm text-[var(--silt)] mt-2">{{ rt.description || 'Luxury accommodation at Luma Haven.' }}</p>
              <p class="text-xs text-[var(--silt)] mt-1">Capacity: Up to {{ rt.capacity }} guests</p>
            </div>

            <div class="flex items-baseline justify-between pt-4 border-t border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)]">
              <div>
                <span class="text-2xl font-bold tabular-nums">{{ money(rt.nightly_rate_minor) }}</span>
                <span class="text-xs text-[var(--silt)]"> / night</span>
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
        <ManagerDashboard portal="staff" :user="user" @navigate="handleManagerNavigate" />
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
              <p class="text-sm text-[var(--silt)]">Guest: {{ detailBooking.guest_name }} · Room {{ detailBooking.room }} ({{ detailBooking.room_type }})</p>
            </div>
            <button type="button" class="text-xl" @click="detailBooking = null">✕</button>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-lg bg-[var(--sunk)] border border-[color:var(--rule)] text-[color:var(--river)] dark:bg-[var(--sunk)] dark:border-[color:var(--rule)] dark:text-[color:var(--river)] text-xs">
            <div><span class="label text-[10px]">Arrival</span><p class="font-medium">{{ detailBooking.arrival }}</p></div>
            <div><span class="label text-[10px]">Departure</span><p class="font-medium">{{ detailBooking.departure }}</p></div>
            <div><span class="label text-[10px]">Status</span><p class="font-medium">{{ detailBooking.status }}</p></div>
            <div><span class="label text-[10px]">Balance</span><p class="tabular-nums font-bold" :class="detailBooking.balance_minor > 0 ? 'text-[var(--status-dirty)] ' : 'text-[var(--status-available)] '">{{ money(detailBooking.balance_minor) }}</p></div>
          </div>

          <section v-if="detailBooking.status === 'CONFIRMED' && ['ADMIN', 'RECEPTION'].includes(role || '')" class="p-4 rounded-lg border border-[var(--rule)] space-y-3">
            <p v-if="detailBooking.verified" class="text-sm" role="status">Guest verification completed.</p>
            <template v-else>
              <h4 class="font-semibold text-sm">Verify guest at reception</h4>
              <label class="flex gap-2 text-sm">
                <input v-model="identityChecked" type="checkbox" />
                <span>I checked this guest's identity in person.</span>
              </label>
              <button type="button" class="btn-secondary text-xs" :disabled="busy || !identityChecked" @click="recordVerification">Record in-person verification</button>
              <Notice :message="error" />
            </template>
          </section>

          <!-- Folio Entries Immutable Ledger Table -->
          <div>
            <h4 class="text-lg font-serif mb-2">Folio Ledger Entries (Immutable)</h4>
            <div class="card overflow-hidden">
              <table class="data-table w-full text-left text-xs">
                <thead>
                  <tr class="bg-[var(--sunk)] text-[color:var(--river)] border-b border-[color:var(--rule)] dark:bg-[var(--sunk)] dark:text-[color:var(--river)] dark:border-[color:var(--rule)]">
                    <th class="p-3">Category</th>
                    <th class="p-3">Description</th>
                    <th class="p-3">Service Date</th>
                    <th class="p-3 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(entry, idx) in detailBooking.entries" :key="idx" class="border-t border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)]">
                    <td class="p-3 font-semibold">{{ entry.category }}</td>
                    <td class="p-3">{{ entry.description }}</td>
                    <td class="p-3 tabular-nums">{{ entry.service_date }}</td>
                    <td class="p-3 text-right tabular-nums" :class="entry.amount_minor < 0 ? 'text-[var(--status-available)] ' : ''">
                      {{ money(entry.amount_minor) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <Notice :message="error" />
          <div class="flex justify-end gap-3 pt-4 border-t border-[var(--rule,#e2e8e0)] dark:border-[color:var(--rule)]">
            <button v-if="canServe && detailBooking.status === 'CONFIRMED'" type="button" class="btn text-xs"
              :disabled="busy || !detailBooking.verified || detailBooking.balance_minor > 0 || detailBooking.hotel_today < detailBooking.arrival || detailBooking.hotel_today >= detailBooking.departure"
              @click="recordStayTransition('check-in')">Check in guest</button>
            <button v-if="canServe && detailBooking.status === 'CHECKED_IN'" type="button" class="btn text-xs"
              :disabled="busy || detailBooking.balance_minor > 0" @click="recordStayTransition('check-out')">Check out guest</button>
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
              <p class="text-xs text-[var(--silt)]">Ref: {{ amendBooking.reference }} · Current: {{ amendBooking.arrival }} to {{ amendBooking.departure }}</p>
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

          <p class="text-xs text-[var(--silt)]">
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
              <p class="text-xs text-[var(--silt)]">Ref: {{ reassignBooking.reference }} · Currently in Room {{ reassignBooking.room }}</p>
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

          <p class="text-xs text-[var(--silt)]">
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
              <p class="text-xs text-[var(--silt)]">Ref: {{ refundReqBooking.reference }} · Guest: {{ refundReqBooking.guest_name }}</p>
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

          <p class="text-xs text-[var(--silt)]">
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
              <p class="text-xs text-[var(--silt)]">{{ editingRate.name }} · Current: {{ money(editingRate.nightly_rate_minor) }}/night</p>
            </div>
            <button type="button" class="text-xl" @click="editingRate = null">✕</button>
          </div>

          <div>
            <label class="label">New Nightly Rate ($ USD)</label>
            <input v-model="newRateDollars" type="number" step="0.01" min="1.00" class="field w-full" required />
          </div>

          <p class="text-xs text-[var(--silt)]">
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
