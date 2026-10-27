<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import PortalLayout from '../../layouts/PortalLayout.vue'
import Notice from '../../components/Notice.vue'
import { api, queryClient } from '../../services/api'
import { money, type StaffUser } from '../../types'

interface TeamMember { id: number; username: string; role: string; is_active: boolean; date_joined: string }
interface AuditEntry { id: number; actor: string; action: string; target: string; timestamp: string }
interface HotelSettings {
  name: string; email: string; phone: string; timezone: string; currency: string
  check_in_time: string; check_out_time: string; tax_percent: number; deposit_percent: number
}
interface Report {
  hotel: string; timezone: string; currency: string; sold_room_nights: number; sellable_room_nights: number
  occupancy_rate_percent: number | null; average_daily_rate_minor: number | null
  revpar_minor: number | null; net_room_revenue_minor: number; settled_cash_minor: number
}

function businessDate(timezone: string, offset = 0) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const date = Object.fromEntries(parts.map(({ type, value }) => [type, value]))
  const result = new Date(`${date.year}-${date.month}-${date.day}T00:00:00Z`)
  result.setUTCDate(result.getUTCDate() + offset)
  return result.toISOString().slice(0, 10)
}

const router = useRouter()
const user = ref<StaffUser | null>(null)
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)
const section = ref<'overview' | 'team' | 'audit' | 'settings' | 'reports'>('overview')
const sections = [
  { id: 'overview', label: 'Overview' }, { id: 'team', label: 'Staff accounts' },
  { id: 'audit', label: 'Audit history' }, { id: 'settings', label: 'Settings' },
  { id: 'reports', label: 'Reports' },
] as const

const identity = useQuery({ queryKey: ['auth', 'me'], queryFn: () => api<StaffUser | { guest_reservation?: number }>('/auth/me') })
watch(identity.data, current => {
  if (current && 'username' in current) user.value = current
}, { immediate: true })
const isAdmin = computed(() => user.value?.role === 'ADMIN')

const summary = useQuery({
  queryKey: ['admin', 'summary'], queryFn: () => api<Record<string, number>>('/dashboard/summary'), enabled: isAdmin,
})
const team = useQuery({
  queryKey: ['admin', 'team'], queryFn: () => api<TeamMember[]>('/admin/staff'),
  enabled: computed(() => isAdmin.value && section.value === 'team'),
})
const audit = useQuery({
  queryKey: ['admin', 'audit'], queryFn: () => api<AuditEntry[]>('/admin/audit'),
  enabled: computed(() => isAdmin.value && section.value === 'audit'),
})
const hotel = useQuery({
  queryKey: ['admin', 'hotel'], queryFn: () => api<HotelSettings>('/admin/hotel'), enabled: isAdmin,
})
const start = ref(businessDate('Asia/Phnom_Penh'))
const end = ref(businessDate('Asia/Phnom_Penh', 1))
const report = useQuery({
  queryKey: computed(() => ['admin', 'report', start.value, end.value]),
  queryFn: () => api<Report>(`/reports/summary?start=${start.value}&end=${end.value}`),
  enabled: computed(() => isAdmin.value && section.value === 'reports' && Boolean(start.value && end.value)),
})
const csvUrl = computed(() => `/api/v1/reports/summary?start=${start.value}&end=${end.value}&export=csv`)

async function signIn() {
  error.value = ''
  busy.value = true
  try {
    const account = await api<StaffUser>('/auth/login', { username: username.value, password: password.value })
    password.value = ''
    queryClient.clear()
    user.value = account
    if (account.role !== 'ADMIN') await router.replace('/staff')
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

async function signOut() {
  error.value = ''
  busy.value = true
  try {
    await api('/auth/logout', {})
    user.value = null
    queryClient.clear()
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <PortalLayout area="admin">
    <p v-if="identity.isPending.value" role="status">Checking your administrator session…</p>
    <form v-else-if="!user" class="card p-8 max-w-md mx-auto space-y-5" @submit.prevent="signIn">
      <p class="label">Restricted access</p>
      <h1 class="text-3xl">Administrator sign in</h1>
      <input v-model="username" class="field" placeholder="Username" aria-label="Username" required />
      <input v-model="password" class="field" placeholder="Password" aria-label="Password" type="password" required />
      <button class="btn w-full" :disabled="busy">Sign in</button>
      <Notice :message="error" />
    </form>
    <div v-else-if="!isAdmin" class="card p-8 max-w-xl mx-auto">
      <h1 class="text-3xl">Administrator access required</h1>
      <p class="mt-3">Your staff role cannot view administration records.</p>
      <RouterLink class="btn inline-block mt-5" to="/staff">Open staff workspace</RouterLink>
    </div>
    <div v-else>
      <div class="flex flex-wrap justify-between items-center gap-4">
        <div><p class="label">Administrator · {{ user.username }}</p><h1 class="text-4xl">Administration overview</h1></div>
        <button class="btn-secondary" :disabled="busy" @click="signOut">Sign out</button>
      </div>
      <Notice :message="error" />
      <nav class="flex flex-wrap gap-2 mt-8 border-b pb-4" aria-label="Administration sections">
        <button v-for="item in sections" :key="item.id" type="button" :class="section === item.id ? 'btn' : 'btn-secondary'" @click="section = item.id">{{ item.label }}</button>
      </nav>

      <section v-if="section === 'overview'" aria-label="Operational overview">
        <h2 class="text-2xl mt-8 mb-4">Hotel operations</h2>
        <p v-if="summary.isPending.value" role="status">Loading operational metrics…</p>
        <Notice :message="summary.error.value ? String(summary.error.value) : ''" />
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div v-for="(value, key) in summary.data.value || {}" :key="key" class="card p-5">
            <p class="label">{{ String(key).replaceAll('_', ' ') }}</p>
            <p class="text-3xl font-bold">{{ String(key).includes('minor') ? money(value) : value }}</p>
          </div>
        </div>
      </section>

      <section v-else-if="section === 'team'" aria-label="Staff accounts">
        <h2 class="text-2xl mt-8 mb-4">Staff accounts</h2>
        <p v-if="team.isPending.value" role="status">Loading staff accounts…</p>
        <Notice :message="team.error.value ? String(team.error.value) : ''" />
        <p v-if="team.data.value?.length === 0">No staff accounts configured.</p>
        <div v-else-if="team.data.value" class="card overflow-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-[#eaf2eb]"><tr><th class="p-4">Username</th><th class="p-4">Role</th><th class="p-4">Status</th></tr></thead>
            <tbody><tr v-for="member in team.data.value" :key="member.id" class="border-t"><td class="p-4">{{ member.username }}</td><td class="p-4">{{ member.role }}</td><td class="p-4">{{ member.is_active ? 'Active' : 'Inactive' }}</td></tr></tbody>
          </table>
        </div>
      </section>

      <section v-else-if="section === 'audit'" aria-label="Audit history">
        <h2 class="text-2xl mt-8 mb-4">Audit history</h2>
        <p v-if="audit.isPending.value" role="status">Loading audit history…</p>
        <Notice :message="audit.error.value ? String(audit.error.value) : ''" />
        <p v-if="audit.data.value?.length === 0">No sensitive actions recorded yet.</p>
        <div v-else-if="audit.data.value" class="card overflow-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-[#eaf2eb]"><tr><th class="p-4">Time</th><th class="p-4">Actor</th><th class="p-4">Action</th><th class="p-4">Target</th></tr></thead>
            <tbody><tr v-for="entry in audit.data.value" :key="entry.id" class="border-t"><td class="p-4">{{ entry.timestamp }}</td><td class="p-4">{{ entry.actor }}</td><td class="p-4">{{ entry.action }}</td><td class="p-4">{{ entry.target }}</td></tr></tbody>
          </table>
        </div>
      </section>

      <section v-else-if="section === 'settings'" aria-label="Hotel settings">
        <h2 class="text-2xl mt-8 mb-4">Hotel settings</h2>
        <p v-if="hotel.isPending.value" role="status">Loading hotel settings…</p>
        <Notice :message="hotel.error.value ? String(hotel.error.value) : ''" />
        <dl v-if="hotel.data.value" class="card p-6 grid sm:grid-cols-2 gap-6">
          <div v-for="[label, value] in [
            ['Name', hotel.data.value.name], ['Email', hotel.data.value.email || 'Not set'],
            ['Phone', hotel.data.value.phone || 'Not set'], ['Timezone', hotel.data.value.timezone],
            ['Currency', hotel.data.value.currency], ['Check-in time', hotel.data.value.check_in_time],
            ['Check-out time', hotel.data.value.check_out_time], ['Deposit percentage', `${hotel.data.value.deposit_percent}%`],
          ]" :key="label"><dt class="label">{{ label }}</dt><dd>{{ value }}</dd></div>
        </dl>
      </section>

      <section v-else aria-label="Reports">
        <h2 class="text-2xl mt-8 mb-4">Reports</h2>
        <p class="text-sm text-[#6d8075] mb-5">Room revenue uses service dates; cash uses payment settlement dates. Period end is exclusive.</p>
        <div class="flex flex-wrap gap-4 items-end mb-5">
          <label><span class="label">Start date</span><input v-model="start" class="field" type="date" /></label>
          <label><span class="label">End date (exclusive)</span><input v-model="end" class="field" type="date" /></label>
          <a :href="csvUrl" class="btn-secondary" download="hotel-report.csv">Download CSV</a>
        </div>
        <p v-if="report.isPending.value" role="status">Calculating report…</p>
        <Notice :message="report.error.value ? String(report.error.value) : ''" />
        <div v-if="report.data.value" class="card p-6">
          <p class="label">{{ report.data.value.hotel }} · {{ report.data.value.timezone }} · {{ report.data.value.currency }}</p>
          <div class="grid sm:grid-cols-3 gap-5 mt-5">
            <div><p class="label">Occupancy rate</p><p>{{ report.data.value.occupancy_rate_percent ?? 'N/A' }}{{ report.data.value.occupancy_rate_percent === null ? '' : '%' }}</p></div>
            <div><p class="label">Average daily rate</p><p>{{ report.data.value.average_daily_rate_minor === null ? 'N/A' : money(report.data.value.average_daily_rate_minor) }}</p></div>
            <div><p class="label">Revenue per available room</p><p>{{ report.data.value.revpar_minor === null ? 'N/A' : money(report.data.value.revpar_minor) }}</p></div>
            <div><p class="label">Sold room-nights</p><p>{{ report.data.value.sold_room_nights }}</p></div>
            <div><p class="label">Net room revenue</p><p>{{ money(report.data.value.net_room_revenue_minor) }}</p></div>
            <div><p class="label">Settled cash</p><p>{{ money(report.data.value.settled_cash_minor) }}</p></div>
          </div>
        </div>
      </section>
    </div>
  </PortalLayout>
</template>
