<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import PortalLayout from '../../layouts/PortalLayout.vue'
import Notice from '../../components/Notice.vue'
import { staffApi, queryClient } from '../../services/api'
import { money, type Booking, type GuestRequest, type Room, type StaffUser, type Task } from '../../types'

const user = ref<StaffUser | null>(null)
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

const identity = useQuery({ queryKey: ['auth', 'me', 'staff'], queryFn: () => staffApi<StaffUser>('/auth/me') })
watch(identity.data, current => {
  if (current && 'username' in current) user.value = current
}, { immediate: true })

const role = computed(() => user.value?.role)
const hasStaff = computed(() => Boolean(user.value))
const canClean = computed(() => ['ADMIN', 'MANAGER', 'RECEPTION', 'HOUSEKEEPING'].includes(role.value || ''))
const canServe = computed(() => ['ADMIN', 'MANAGER', 'RECEPTION'].includes(role.value || ''))
const canSeeReservations = computed(() => ['ADMIN', 'MANAGER', 'RECEPTION', 'ACCOUNTANT'].includes(role.value || ''))

const summary = useQuery({
  queryKey: computed(() => ['summary', role.value]),
  queryFn: () => staffApi<Record<string, number>>('/dashboard/summary'), enabled: hasStaff,
})
const rooms = useQuery({
  queryKey: computed(() => ['rooms', role.value]),
  queryFn: () => staffApi<Room[]>('/rooms'), enabled: hasStaff,
})
const tasks = useQuery({
  queryKey: computed(() => ['tasks', role.value]),
  queryFn: () => staffApi<Task[]>('/housekeeping/tasks'), enabled: canClean,
})
const requests = useQuery({
  queryKey: computed(() => ['requests', role.value]),
  queryFn: () => staffApi<GuestRequest[]>('/staff/service-requests'), enabled: canServe,
})
const reservations = useQuery({
  queryKey: computed(() => ['staff-reservations', role.value]),
  queryFn: () => staffApi<Booking[]>('/staff/reservations'), enabled: canSeeReservations,
})

async function signIn() {
  error.value = ''
  busy.value = true
  try {
    const account = await staffApi<StaffUser>('/auth/login', { username: username.value, password: password.value })
    password.value = ''
    queryClient.clear() // Never reuse financial records from another staff role.
    user.value = account
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

async function signOut() {
  error.value = ''
  try {
    await staffApi('/auth/logout', {})
    user.value = null
    queryClient.clear()
  } catch (caught) {
    error.value = String(caught)
  }
}

async function act(action: () => Promise<unknown>) {
  error.value = ''
  busy.value = true
  try {
    await action()
    await Promise.all([
      summary.refetch(), rooms.refetch(),
      ...(canClean.value ? [tasks.refetch()] : []),
      ...(canServe.value ? [requests.refetch()] : []),
      ...(canSeeReservations.value ? [reservations.refetch()] : []),
    ])
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

const nextStep: Record<string, string> = { DIRTY: 'CLEANING', CLEANING: 'INSPECTION', INSPECTION: 'READY' }
</script>

<template>
  <PortalLayout area="staff">
    <div v-if="identity.isPending.value" role="status" class="space-y-4">
      <p>Checking your staff session…</p>
      <div class="skeleton h-8 w-48"></div>
      <div class="skeleton h-32 w-full"></div>
    </div>
    <form v-else-if="!user" class="card portal-login p-8 max-w-md mx-auto space-y-5" @submit.prevent="signIn">
      <p class="label">Team access</p>
      <h1 class="text-3xl">Staff sign in</h1>
      <input v-model="username" class="field" placeholder="Username" aria-label="Username" required />
      <input v-model="password" class="field" placeholder="Password" aria-label="Password" type="password" required />
      <button class="btn w-full" :disabled="busy">Sign in</button>
      <Notice :message="error" />
    </form>
    <div v-else>
      <div class="flex justify-between items-center">
        <div><p class="label">Operations · {{ user.role }}</p><h1 class="text-4xl">Good to see you, {{ user.username }}.</h1></div>
        <button class="btn-secondary" @click="signOut">Sign out</button>
      </div>
      <Notice :message="error" />
      <Notice :message="summary.error.value ? String(summary.error.value) : ''" />

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
        <div v-for="(value, key) in summary.data.value || {}" :key="key" class="card metric-card">
          <p class="label">{{ String(key).replaceAll('_', ' ') }}</p>
          <p class="text-3xl font-bold">{{ String(key).includes('minor') ? money(value) : value }}</p>
        </div>
      </div>
      <h2 class="text-2xl mt-10 mb-4">Room board</h2>
      <Notice :message="rooms.error.value ? String(rooms.error.value) : ''" />
      <div class="grid md:grid-cols-4 gap-4">
        <div v-for="room in rooms.data.value" :key="room.id" class="card room-tile" :data-cleaning="room.cleaning" :data-service="room.in_service ? 'in' : 'out'">
          <span class="label">Room {{ room.number }}</span>
          <h3 class="text-xl">{{ room.type }}</h3>
          <p class="mt-2 text-sm">{{ room.occupied ? 'Occupied' : 'Vacant' }} · {{ room.cleaning }} · {{ room.in_service ? 'In service' : 'Out of service' }}</p>
        </div>
      </div>
      <p v-if="!rooms.isFetching.value && rooms.data.value?.length === 0">No rooms configured.</p>

      <template v-if="canClean">
        <h2 class="text-2xl mt-10 mb-4">Housekeeping queue</h2>
        <Notice :message="tasks.error.value ? String(tasks.error.value) : ''" />
        <p v-if="tasks.data.value?.length === 0">No housekeeping tasks.</p>
        <div class="space-y-3">
          <div v-for="task in tasks.data.value" :key="task.id" class="card queue-row flex items-center justify-between">
            <span>Room {{ task.room__number }} · {{ task.status }}</span>
            <button v-if="task.status !== 'READY' && !(task.status === 'INSPECTION' && role === 'HOUSEKEEPING')" class="btn-secondary" :disabled="busy" @click="act(() => staffApi(`/housekeeping/tasks/${task.id}/transition`, { status: nextStep[task.status] }))">Next step</button>
          </div>
        </div>
      </template>

      <template v-if="canServe">
        <h2 class="text-2xl mt-10 mb-4">Guest requests</h2>
        <Notice :message="requests.error.value ? String(requests.error.value) : ''" />
        <p v-if="requests.data.value?.length === 0">No guest requests.</p>
        <div class="space-y-3">
          <div v-for="request in requests.data.value" :key="request.id" class="card queue-row flex justify-between items-center">
            <span>{{ request.type }} · {{ request.description }} · {{ request.status }}</span>
            <button v-if="request.status !== 'COMPLETED'" class="btn-secondary" :disabled="busy" @click="act(() => staffApi(`/staff/service-requests/${request.id}/complete`, {}))">Complete</button>
          </div>
        </div>
      </template>

      <template v-if="canSeeReservations">
        <h2 class="text-2xl mt-10 mb-4">Reservations</h2>
        <Notice :message="reservations.error.value ? String(reservations.error.value) : ''" />
        <p v-if="reservations.data.value?.length === 0">No reservations found.</p>
        <div v-else class="card overflow-auto">
          <table class="data-table w-full text-left text-sm">
            <thead><tr><th v-for="heading in ['Reference', 'Guest', 'Room', 'Arrival', 'Status']" :key="heading" class="p-4">{{ heading }}</th></tr></thead>
            <tbody>
              <tr v-for="booking in reservations.data.value" :key="booking.id" class="border-t border-[var(--line)]">
                <td class="p-4">{{ booking.reference }}</td><td class="p-4">{{ booking.guest_name }}</td>
                <td class="p-4">{{ booking.room }}</td><td class="p-4">{{ booking.arrival }}</td><td class="p-4">{{ booking.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </PortalLayout>
</template>
