<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { staffApi, queryClient } from '../../services/api'
import {
  money,
  type Booking,
  type GuestRequest,
  type Room,
  type Task,
  type ReservationDiagnostics
} from '../../types'

const props = defineProps<{
  userRole: string
  username: string
}>()

const busy = ref(false)
const error = ref('')
const successNotice = ref('')

// Data queries
const reservations = useQuery({
  queryKey: ['staff-reservations'],
  queryFn: () => staffApi<Booking[]>('/staff/reservations'),
})

const rooms = useQuery({
  queryKey: ['rooms', 'reception'],
  queryFn: () => staffApi<Room[]>('/rooms'),
})

const tasks = useQuery({
  queryKey: ['tasks', 'reception'],
  queryFn: () => staffApi<Task[]>('/housekeeping/tasks'),
})

const requests = useQuery({
  queryKey: ['requests', 'reception'],
  queryFn: () => staffApi<GuestRequest[]>('/staff/service-requests'),
})

// Today's Movements
const today = computed(() => {
  const first = reservations.data.value?.[0]
  if (first?.hotel_today) return first.hotel_today
  return new Date().toISOString().split('T')[0]
})

const arrivalsToday = computed(() => {
  return (reservations.data.value || []).filter(r => r.arrival === today.value && r.status !== 'CANCELLED')
})

const departuresToday = computed(() => {
  return (reservations.data.value || []).filter(r => r.departure === today.value && r.status === 'CHECKED_IN')
})

const pendingInspections = computed(() => {
  return (tasks.data.value || []).filter(t => t.status === 'INSPECTION')
})

const activeRequests = computed(() => {
  return (requests.data.value || []).filter(r => r.status !== 'COMPLETED')
})

// Pre-flight Diagnostics Modal
const selectedReservation = ref<Booking | null>(null)
const diagnostics = ref<ReservationDiagnostics | null>(null)
const loadingDiagnostics = ref(false)
const reassignRoomId = ref<number | ''>('')

async function openDiagnostics(b: Booking) {
  selectedReservation.value = b
  diagnostics.value = null
  reassignRoomId.value = ''
  error.value = ''
  loadingDiagnostics.value = true
  try {
    diagnostics.value = await staffApi<ReservationDiagnostics>(`/staff/reservations/${b.id}/diagnostics`)
  } catch (err) {
    error.value = String(err)
  } finally {
    loadingDiagnostics.value = false
  }
}

async function executeCheckIn() {
  if (!selectedReservation.value) return
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/reservations/${selectedReservation.value.id}/check-in`, {})
    successNotice.value = `Guest ${selectedReservation.value.guest_name} successfully checked into Room ${selectedReservation.value.room}.`
    selectedReservation.value = null
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['staff-reservations'] }),
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    ])
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

async function executeReassign() {
  if (!selectedReservation.value || !reassignRoomId.value) return
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/staff/reservations/${selectedReservation.value.id}/reassign`, {
      room_id: Number(reassignRoomId.value)
    })
    successNotice.value = `Room successfully reassigned.`
    // Refresh diagnostics
    diagnostics.value = await staffApi<ReservationDiagnostics>(`/staff/reservations/${selectedReservation.value.id}/diagnostics`)
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['staff-reservations'] }),
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    ])
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

async function inspectAndReady(taskId: number) {
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/housekeeping/tasks/${taskId}/transition`, { status: 'READY' })
    successNotice.value = `Room verified and released to READY service state.`
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['tasks'] }),
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    ])
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

async function completeRequest(requestId: number) {
  busy.value = true
  error.value = ''
  try {
    await staffApi(`/staff/service-requests/${requestId}/complete`, {})
    successNotice.value = `Service request completed.`
    await queryClient.invalidateQueries({ queryKey: ['requests'] })
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-8">
    <Notice :message="error || (reservations.error.value ? String(reservations.error.value) : '')" />
    <div v-if="successNotice" class="p-4 rounded-xl bg-[var(--status-available)]/10 border border-[var(--status-available)]/30 text-[var(--status-available)] text-sm flex items-center justify-between">
      <span>{{ successNotice }}</span>
      <button class="text-xs font-semibold hover:underline ml-4" @click="successNotice = ''">Dismiss</button>
    </div>

    <!-- Desk Movements KPI Strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-5">
        <span class="label text-[10px]">Today's Date</span>
        <p class="text-xl font-serif mt-1">{{ today }}</p>
        <span class="text-xs text-[var(--silt)]">Hotel local time</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Expected Arrivals</span>
        <p class="text-xl font-serif mt-1">{{ arrivalsToday.length }}</p>
        <span class="text-xs text-[var(--silt)]">
          {{ arrivalsToday.filter(r => r.status === 'CHECKED_IN').length }} checked in
        </span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Expected Departures</span>
        <p class="text-xl font-serif mt-1">{{ departuresToday.length }}</p>
        <span class="text-xs text-[var(--silt)]">Active stays</span>
      </div>
      <div class="card p-5">
        <span class="label text-[10px]">Awaiting Inspection</span>
        <p class="text-xl font-serif mt-1" :class="pendingInspections.length ? 'text-[var(--status-dirty)] font-bold' : ''">
          {{ pendingInspections.length }}
        </p>
        <span class="text-xs text-[var(--silt)]">Cleaned, ready to inspect</span>
      </div>
    </div>

    <!-- Section 1: Arrivals Today & Assisted Check-in -->
    <section class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-serif">Front Desk · Arrivals Today</h2>
          <p class="text-xs text-[var(--silt)] mt-1">Review guest identity, room readiness, and balance before granting key access.</p>
        </div>
        <span class="badge text-xs">{{ arrivalsToday.length }} arrivals</span>
      </div>

      <div v-if="arrivalsToday.length === 0" class="py-8 text-center text-sm text-[var(--silt)]">
        No arrivals scheduled for today.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="res in arrivalsToday"
          :key="res.id"
          class="p-4 rounded-xl border border-[var(--rule)] bg-[var(--paper)]/60 flex flex-wrap items-center justify-between gap-4"
        >
          <div class="space-y-1">
            <div class="flex items-center gap-3">
              <span class="font-semibold text-base">{{ res.guest_name }}</span>
              <span class="badge text-[11px]">{{ res.reference }}</span>
              <span
                class="badge text-[10px] font-bold"
                :class="{
                  'bg-[var(--status-available)]/10 text-[var(--status-available)] border-[var(--status-available)]/30': res.status === 'CHECKED_IN',
 'bg-[var(--status-dirty)]/10 text-[var(--status-dirty)] border-[var(--status-dirty)]/30': res.status === 'CONFIRMED'
                }"
              >
                {{ res.status }}
              </span>
            </div>
            <p class="text-xs text-[var(--silt)]">
              Room {{ res.room }} ({{ res.room_type }}) · Departs {{ res.departure }}
              <span v-if="res.balance_minor > 0" class="text-[var(--status-out)] font-medium ml-2">
                Due: {{ money(res.balance_minor) }}
              </span>
              <span v-else class="text-[var(--status-available)] ml-2">Folio Paid</span>
            </p>
          </div>

          <div class="flex items-center gap-2">
            <button
              v-if="res.status === 'CONFIRMED'"
              class="btn text-xs py-2 px-4"
              :disabled="busy"
              @click="openDiagnostics(res)"
            >
              Assist Check-in →
            </button>
            <span v-else-if="res.status === 'CHECKED_IN'" class="text-xs font-semibold text-[var(--status-available)]">
              Key Issued ✓
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- Section 2: Room Turnaround Inspections -->
    <section v-if="pendingInspections.length > 0" class="card p-6 border-[var(--status-dirty)]/30 bg-[var(--status-dirty)]/5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-serif text-[var(--status-dirty)] ">Housekeeping Inspections Required</h2>
          <p class="text-xs text-[var(--silt)] mt-1">Reception/Management inspection required before rooms can be sold or occupied.</p>
        </div>
        <span class="badge bg-[var(--status-dirty)]/20 text-[var(--status-dirty)] ">{{ pendingInspections.length }} rooms waiting</span>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        <div
          v-for="t in pendingInspections"
          :key="t.id"
          class="card p-4 flex items-center justify-between"
        >
          <div>
            <span class="font-bold">Room {{ t.room__number }}</span>
            <p v-if="t.notes" class="text-xs text-[var(--silt)] mt-1 italic">"{{ t.notes }}"</p>
            <p v-if="t.assignee__username" class="text-[10px] text-[var(--silt)]">Cleaned by: {{ t.assignee__username }}</p>
          </div>
          <button
            class="btn-secondary text-xs"
            :disabled="busy"
            @click="inspectAndReady(t.id)"
          >
            Inspect & Mark Ready ✓
          </button>
        </div>
      </div>
    </section>

    <!-- Section 3: Guest Service Requests -->
    <section class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-serif">Active Guest Requests</h2>
          <p class="text-xs text-[var(--silt)] mt-1">Pending guest requests requiring front desk or concierge attention.</p>
        </div>
        <span class="badge">{{ activeRequests.length }} active</span>
      </div>

      <p v-if="activeRequests.length === 0" class="text-sm text-[var(--silt)] py-4">No active service requests.</p>
      <div v-else class="space-y-3">
        <div
          v-for="req in activeRequests"
          :key="req.id"
          class="card p-4 flex items-center justify-between gap-3"
        >
          <div>
            <span class="font-semibold">{{ req.type }}</span>
            <p class="text-xs text-[var(--silt)] mt-1">{{ req.description }}</p>
            <span class="badge text-[10px] mt-2">{{ req.status }}</span>
          </div>
          <button
            class="btn-secondary text-xs"
            :disabled="busy"
            @click="completeRequest(req.id)"
          >
            Complete
          </button>
        </div>
      </div>
    </section>

    <!-- Modal: Pre-Flight Check-in Diagnostics & Room Reassignment -->
    <div
      v-if="selectedReservation"
      class="fixed inset-0 z-50 bg-[var(--scrim)] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      @click.self="selectedReservation = null"
    >
      <div class="card p-6 w-full max-w-lg space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <span class="label text-[10px]">Pre-Flight Check-In</span>
            <h3 class="text-2xl font-serif">{{ selectedReservation.guest_name }}</h3>
            <p class="text-xs text-[var(--silt)]">Booking {{ selectedReservation.reference }} · Room {{ selectedReservation.room }}</p>
          </div>
          <button class="text-xl p-1" @click="selectedReservation = null">✕</button>
        </div>

        <div v-if="loadingDiagnostics" class="py-8 text-center text-sm text-[var(--silt)]">
          Checking room and folio eligibility…
        </div>
        <div v-else-if="diagnostics" class="space-y-5">
          <!-- Eligibility Summary Banner -->
          <div
            class="p-4 rounded-xl border flex items-center gap-3"
            :class="diagnostics.eligible_check_in
 ? 'bg-[var(--status-available)]/10 border-[var(--status-available)]/30 text-[var(--status-available)] '
 : 'bg-[var(--status-dirty)]/10 border-[var(--status-dirty)]/30 text-[var(--status-dirty)] '"
          >
            <span class="text-xl">{{ diagnostics.eligible_check_in ? '✓' : '⚠' }}</span>
            <div>
              <p class="font-bold text-sm">
                {{ diagnostics.eligible_check_in ? 'Guest is fully eligible for check-in' : 'Requirements pending for check-in' }}
              </p>
              <p class="text-xs mt-0.5 opacity-90">
                {{ diagnostics.eligible_check_in ? 'All identity, folio, and room readiness criteria met.' : 'Review diagnostic flags below.' }}
              </p>
            </div>
          </div>

          <!-- Diagnostic Check Items -->
          <div class="space-y-2">
            <div
              v-for="item in diagnostics.check_in_diagnostics"
              :key="item.code"
              class="p-3 rounded-lg border flex items-start gap-3 text-xs"
              :class="{
                'bg-[var(--status-out)]/10 border-[var(--status-out)]/30 text-[var(--status-out)] ': item.severity === 'ERROR',
 'bg-[var(--status-dirty)]/10 border-[var(--status-dirty)]/30 text-[var(--status-dirty)] ': item.severity === 'WARNING',
                'bg-[var(--status-available)]/10 border-[var(--status-available)]/30 text-[var(--status-available)] ': item.severity === 'INFO'
              }"
            >
              <span class="font-bold text-[10px]">{{ item.severity }}</span>
              <span class="flex-1">{{ item.message }}</span>
            </div>
          </div>

          <!-- Room Reassignment if Room is not READY -->
          <div v-if="diagnostics.room_cleaning !== 'READY' || !diagnostics.eligible_check_in" class="p-4 rounded-xl border border-[var(--rule)] bg-[var(--paper)]/40 space-y-3">
            <span class="label text-[10px]">Room Reassignment</span>
            <p class="text-xs text-[var(--silt)]">If current room {{ diagnostics.room_number }} is delayed in cleaning, reassign to another clean room:</p>
            <div class="flex items-center gap-2">
              <select v-model="reassignRoomId" class="field text-xs flex-1">
                <option value="">Select clean alternative room…</option>
                <option
                  v-for="rm in (rooms.data.value || []).filter(r => r.cleaning === 'READY' && r.in_service && !r.occupied)"
                  :key="rm.id"
                  :value="rm.id"
                >
                  Room {{ rm.number }} · {{ rm.type }} (READY)
                </option>
              </select>
              <button
                class="btn-secondary text-xs"
                :disabled="busy || !reassignRoomId"
                @click="executeReassign"
              >
                Reassign
              </button>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex justify-end gap-3 pt-4 border-t border-[var(--rule)]">
            <button class="btn-secondary text-xs" @click="selectedReservation = null">Cancel</button>
            <button
              class="btn text-xs"
              :disabled="busy || !diagnostics.eligible_check_in"
              @click="executeCheckIn"
            >
              Complete Check-In & Issue Key →
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
