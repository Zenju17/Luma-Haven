<script setup lang="ts">
import { computed, ref } from 'vue'
import { api, money } from '../lib/api'
import type { Booking, HousekeepingTask, Room, ServiceRequest, StaffUser } from '../types'
import Notice from '../components/Notice.vue'

const user = ref<StaffUser | null>(null)
const username = ref('')
const password = ref('')
const error = ref('')

const summary = ref<Record<string, number> | null>(null)
const rooms = ref<Room[] | null>(null)
const tasks = ref<HousekeepingTask[] | null>(null)
const requests = ref<ServiceRequest[] | null>(null)
const bookings = ref<Booking[] | null>(null)

const summaryEntries = computed(() => Object.entries(summary.value ?? {}))

const nextStatus: Record<string, string> = {
  DIRTY: 'CLEANING',
  CLEANING: 'INSPECTION',
  INSPECTION: 'READY',
}

async function login() {
  error.value = ''
  try {
    user.value = await api<StaffUser>('/auth/login', {
      username: username.value,
      password: password.value,
    })
    await loadAll()
  } catch (e) {
    error.value = String(e)
  }
}

async function loadAll() {
  if (!user.value) return
  const role = user.value.role
  const calls: Promise<unknown>[] = [
    api<Record<string, number>>('/dashboard/summary').then((value) => (summary.value = value)),
    api<Room[]>('/rooms').then((value) => (rooms.value = value)),
  ]
  if (role !== 'ACCOUNTANT') {
    calls.push(
      api<HousekeepingTask[]>('/housekeeping/tasks').then((value) => (tasks.value = value)),
    )
  }
  if (role !== 'ACCOUNTANT' && role !== 'HOUSEKEEPING') {
    calls.push(
      api<ServiceRequest[]>('/staff/service-requests').then((value) => (requests.value = value)),
    )
  }
  if (role !== 'HOUSEKEEPING') {
    calls.push(api<Booking[]>('/staff/reservations').then((value) => (bookings.value = value)))
  }
  error.value = ''
  const results = await Promise.allSettled(calls)
  const failed = results.find((result) => result.status === 'rejected')
  if (failed && failed.status === 'rejected') error.value = String(failed.reason)
}

async function refreshOperational() {
  if (!user.value) return
  const role = user.value.role
  const calls: Promise<unknown>[] = [
    api<Record<string, number>>('/dashboard/summary').then((value) => (summary.value = value)),
  ]
  if (role !== 'ACCOUNTANT') {
    calls.push(
      api<HousekeepingTask[]>('/housekeeping/tasks').then((value) => (tasks.value = value)),
    )
  }
  if (role !== 'ACCOUNTANT' && role !== 'HOUSEKEEPING') {
    calls.push(
      api<ServiceRequest[]>('/staff/service-requests').then((value) => (requests.value = value)),
    )
  }
  error.value = ''
  const results = await Promise.allSettled(calls)
  const failed = results.find((result) => result.status === 'rejected')
  if (failed && failed.status === 'rejected') error.value = String(failed.reason)
}

async function act(fn: () => Promise<unknown>) {
  try {
    await fn()
  } catch (e) {
    error.value = String(e)
    return
  }
  await refreshOperational()
}

function advanceTask(task: HousekeepingTask) {
  return act(() =>
    api(`/housekeeping/tasks/${task.id}/transition`, { status: nextStatus[task.status] }),
  )
}

function completeRequest(request: ServiceRequest) {
  return act(() => api(`/staff/service-requests/${request.id}/complete`, {}))
}

async function logout() {
  try {
    await api('/auth/logout', {})
  } catch {
    // The local session is cleared regardless of the server response.
  }
  user.value = null
  summary.value = null
  rooms.value = null
  tasks.value = null
  requests.value = null
  bookings.value = null
}
</script>

<template>
  <form v-if="!user" class="card p-8 max-w-md mx-auto space-y-5" @submit.prevent="login">
    <p class="label">Team access</p>
    <h1 class="text-3xl">Staff sign in</h1>
    <input
      v-model="username"
      class="field"
      placeholder="Username"
      aria-label="Username"
      required
    />
    <input
      v-model="password"
      class="field"
      placeholder="Password"
      aria-label="Password"
      type="password"
      required
    />
    <button class="btn w-full">Sign in</button>
    <Notice :error="error" />
  </form>

  <div v-else>
    <div class="flex justify-between items-center">
      <div>
        <p class="label">Operations · {{ user.role }}</p>
        <h1 class="text-4xl">Good to see you, {{ user.username }}.</h1>
      </div>
      <button class="btn-secondary" @click="logout">Sign out</button>
    </div>

    <Notice :error="error" />

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
      <div v-for="[key, value] in summaryEntries" :key="key" class="card p-5">
        <p class="label">{{ key.replaceAll('_', ' ') }}</p>
        <p class="text-3xl font-bold">{{ key.includes('minor') ? money(value) : value }}</p>
      </div>
    </div>

    <h2 class="text-2xl mt-10 mb-4">Room board</h2>
    <div class="grid md:grid-cols-4 gap-4">
      <div v-for="room in rooms ?? []" :key="room.id" class="card p-5">
        <span class="label">Room {{ room.number }}</span>
        <h3 class="text-xl">{{ room.type }}</h3>
        <p class="mt-2 text-sm">
          {{ room.occupied ? 'Occupied' : 'Vacant' }} · {{ room.cleaning }} ·
          {{ room.in_service ? 'In service' : 'Out of service' }}
        </p>
      </div>
    </div>

    <template v-if="tasks">
      <h2 class="text-2xl mt-10 mb-4">Housekeeping queue</h2>
      <div class="space-y-3">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="card p-4 flex items-center justify-between"
        >
          <span>Room {{ task.room__number }} · {{ task.status }}</span>
          <button
            v-if="task.status !== 'READY'"
            class="btn-secondary"
            @click="advanceTask(task)"
          >
            Next step →
          </button>
        </div>
      </div>
    </template>

    <template v-if="requests">
      <h2 class="text-2xl mt-10 mb-4">Guest requests</h2>
      <div class="space-y-3">
        <div
          v-for="request in requests"
          :key="request.id"
          class="card p-4 flex justify-between"
        >
          <span>{{ request.type }} · {{ request.description }} · {{ request.status }}</span>
          <button
            v-if="request.status !== 'COMPLETED'"
            class="btn-secondary"
            @click="completeRequest(request)"
          >
            Complete
          </button>
        </div>
      </div>
    </template>

    <template v-if="bookings">
      <h2 class="text-2xl mt-10 mb-4">Reservations</h2>
      <div class="card overflow-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-[#eaf2eb]">
            <tr>
              <th
                v-for="heading in ['Reference', 'Guest', 'Room', 'Arrival', 'Status']"
                :key="heading"
                class="p-4"
              >
                {{ heading }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="booking in bookings" :key="booking.id" class="border-t">
              <td class="p-4">{{ booking.reference }}</td>
              <td class="p-4">{{ booking.guest_name }}</td>
              <td class="p-4">{{ booking.room }}</td>
              <td class="p-4">{{ booking.arrival }}</td>
              <td class="p-4">{{ booking.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
