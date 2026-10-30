<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import PortalLayout from '../../layouts/PortalLayout.vue'
import ManagerDashboard from '../manager/ManagerDashboard.vue'
import Notice from '../../components/Notice.vue'
import { adminApi, queryClient } from '../../services/api'
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

const user = ref<StaffUser | null>(null)
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)
const editingUser = ref<TeamMember | null>(null)
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
const passwordBusy = ref(false)
const section = ref<'overview' | 'team' | 'audit' | 'settings' | 'reports'>('overview')
const sections = [
  { id: 'overview', label: 'Overview' }, { id: 'team', label: 'Staff accounts' },
  { id: 'audit', label: 'Audit history' }, { id: 'settings', label: 'Settings' },
  { id: 'reports', label: 'Reports' },
] as const

const identity = useQuery({ queryKey: ['auth', 'me', 'admin'], queryFn: () => adminApi<StaffUser>('/auth/me') })
watch(identity.data, current => {
  if (current && 'username' in current) user.value = current
}, { immediate: true })
const isAdmin = computed(() => user.value?.role === 'ADMIN')

const team = useQuery({
  queryKey: ['admin', 'team'], queryFn: () => adminApi<TeamMember[]>('/admin/staff'),
  enabled: computed(() => isAdmin.value && section.value === 'team'),
})
const audit = useQuery({
  queryKey: ['admin', 'audit'], queryFn: () => adminApi<AuditEntry[]>('/admin/audit'),
  enabled: computed(() => isAdmin.value && section.value === 'audit'),
})
const hotel = useQuery({
  queryKey: ['admin', 'hotel'], queryFn: () => adminApi<HotelSettings>('/admin/hotel'), enabled: isAdmin,
})
const start = ref(businessDate('Asia/Phnom_Penh'))
const end = ref(businessDate('Asia/Phnom_Penh', 1))
const report = useQuery({
  queryKey: computed(() => ['admin', 'report', start.value, end.value]),
  queryFn: () => adminApi<Report>(`/admin/reports/summary?start=${start.value}&end=${end.value}`),
  enabled: computed(() => isAdmin.value && section.value === 'reports' && Boolean(start.value && end.value)),
})
const csvUrl = computed(() => `/api/v1/admin/reports/summary?start=${start.value}&end=${end.value}&export=csv`)
const csvDaily = computed(() => '/api/v1/admin/reports/daily-summary?export=csv')
const csvRevOcc = computed(() => `/api/v1/admin/reports/revenue-occupancy?start=${start.value}&end=${end.value}&export=csv`)
const csvCash = computed(() => `/api/v1/admin/reports/cash-reconciliation?start=${start.value}&end=${end.value}&export=csv`)
const csvHK = computed(() => `/api/v1/admin/reports/housekeeping-turnaround?start=${start.value}&end=${end.value}&export=csv`)
const csvAR = computed(() => '/api/v1/admin/reports/accounts-receivable?export=csv')

async function signIn() {
  error.value = ''
  busy.value = true
  try {
    const account = await adminApi<StaffUser>('/auth/login', { username: username.value, password: password.value })
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
  error.value = ''
  busy.value = true
  try {
    await adminApi('/auth/logout', {})
    user.value = null
    queryClient.clear()
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}

function openPasswordForm(member: TeamMember) {
  editingUser.value = member
  newPassword.value = ''
  confirmPassword.value = ''
  passwordError.value = ''
  passwordSuccess.value = ''
}

function closePasswordForm() {
  editingUser.value = null
  newPassword.value = ''
  confirmPassword.value = ''
  passwordError.value = ''
}

async function changeStaffPassword() {
  if (!editingUser.value || passwordBusy.value) return
  passwordError.value = ''
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'Passwords do not match. Please ensure both fields are identical.'
    return
  }
  if (newPassword.value.length < 8) {
    passwordError.value = `Password must be at least 8 characters long (currently ${newPassword.value.length} characters).`
    return
  }
  if (newPassword.value.length > 12) {
    passwordError.value = `Password cannot exceed 12 characters (currently ${newPassword.value.length} characters).`
    return
  }
  passwordBusy.value = true
  const target = editingUser.value
  try {
    await adminApi(`/admin/staff/${target.id}/password`, {
      new_password: newPassword.value,
      confirm_password: confirmPassword.value,
    })
    closePasswordForm()
    passwordSuccess.value = `Password changed for ${target.username}. The private local credentials file was updated.`
    await audit.refetch()
  } catch (caught) {
    passwordError.value = String(caught)
  } finally {
    passwordBusy.value = false
  }
}
</script>

<template>
  <PortalLayout area="admin">
    <div v-if="identity.isPending.value" role="status" class="space-y-4">
      <p>Checking your administrator session…</p>
      <div class="skeleton h-8 w-48"></div>
      <div class="skeleton h-32 w-full"></div>
    </div>
    <form v-else-if="!user" class="card portal-login p-8 max-w-md mx-auto space-y-5" @submit.prevent="signIn">
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
      <nav class="admin-tabs flex flex-wrap gap-2 mt-8 pb-4" aria-label="Administration sections">
        <button v-for="item in sections" :key="item.id" type="button" :class="section === item.id ? 'btn' : 'btn-secondary'" @click="section = item.id">{{ item.label }}</button>
      </nav>

      <section v-if="section === 'overview'" aria-label="Executive MIS Intelligence">
        <ManagerDashboard portal="admin" :user="user" />
      </section>

      <section v-else-if="section === 'team'" aria-label="Staff accounts">
        <h2 class="text-2xl mt-8 mb-4">Staff accounts</h2>
        <Notice :message="passwordSuccess" status />
        <p v-if="team.isPending.value" role="status">Loading staff accounts…</p>
        <Notice :message="team.error.value ? String(team.error.value) : ''" />
        <p v-if="team.data.value?.length === 0">No staff accounts configured.</p>
        <div v-else-if="team.data.value" class="card overflow-auto">
          <table class="data-table w-full text-left text-sm">
            <thead><tr><th class="p-4">Username</th><th class="p-4">Role</th><th class="p-4">Status</th><th class="p-4">Action</th></tr></thead>
            <tbody><tr v-for="member in team.data.value" :key="member.id" class="border-t border-[var(--line)]"><td class="p-4">{{ member.username }}</td><td class="p-4">{{ member.role }}</td><td class="p-4">{{ member.is_active ? 'Active' : 'Inactive' }}</td><td class="p-4"><button v-if="member.username !== user?.username" class="btn-secondary" @click="openPasswordForm(member)">Change password</button><span v-else>Use changepassword for your account</span></td></tr></tbody>
          </table>
        </div>
        <Transition name="modal">
          <div v-if="editingUser" class="modal-backdrop" role="dialog" aria-modal="true" aria-label="Change staff password" @click.self="closePasswordForm">
            <form class="card p-8 w-full max-w-lg" @submit.prevent="changeStaffPassword">
              <button type="button" class="float-right" aria-label="Close" @click="closePasswordForm">✕</button>
              <p class="label">Administrator action</p>
              <h3 class="text-2xl">Change password for {{ editingUser.username }}</h3>
              <p class="mt-3 text-sm text-[var(--muted)]">The new password will be hashed in the database and stored in the owner-only local <code>backend/.private-staff-passwords</code> file. It will not appear in the API response or audit log.</p>
              <div class="mt-5">
                <div class="flex justify-between items-center mb-1">
                  <label for="new-staff-password" class="label mb-0">New password</label>
                  <span v-if="newPassword.length > 0" class="text-xs" :class="newPassword.length >= 8 && newPassword.length <= 12 ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-amber-600 dark:text-amber-400'">
                    {{ newPassword.length }} characters {{ newPassword.length >= 8 && newPassword.length <= 12 ? '✓' : '(8–12 characters)' }}
                  </span>
                </div>
                <input id="new-staff-password" v-model="newPassword" class="field w-full" type="password" autocomplete="new-password" minlength="8" maxlength="12" required />
              </div>

              <div class="mt-4">
                <div class="flex justify-between items-center mb-1">
                  <label for="confirm-staff-password" class="label mb-0">Confirm new password</label>
                  <span v-if="confirmPassword.length > 0" class="text-xs font-medium" :class="newPassword === confirmPassword ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'">
                    {{ newPassword === confirmPassword ? 'Passwords match ✓' : 'Passwords do not match' }}
                  </span>
                </div>
                <input id="confirm-staff-password" v-model="confirmPassword" class="field w-full" type="password" autocomplete="new-password" minlength="8" maxlength="12" required />
              </div>

              <div class="mt-4 p-3 rounded-lg bg-[var(--surface-muted,#eaf1ee)] dark:bg-[var(--surface-muted,#122523)] text-xs text-[var(--muted)] space-y-1">
                <p class="font-medium text-[var(--brand-text)]">Password requirements:</p>
                <ul class="list-disc list-inside space-y-0.5">
                  <li>Between 8 and 12 characters</li>
                  <li>Cannot be too similar to the username or email</li>
                  <li>Cannot be a commonly used password or entirely numeric</li>
                  <li>Must differ from the user's current password</li>
                </ul>
              </div>
              <Notice :message="passwordError" />
              <button class="btn w-full mt-6" :disabled="passwordBusy || !newPassword || !confirmPassword">{{ passwordBusy ? 'Saving…' : 'Save password' }}</button>
            </form>
          </div>
        </Transition>
      </section>

      <section v-else-if="section === 'audit'" aria-label="Audit history">
        <h2 class="text-2xl mt-8 mb-4">Audit history</h2>
        <p v-if="audit.isPending.value" role="status">Loading audit history…</p>
        <Notice :message="audit.error.value ? String(audit.error.value) : ''" />
        <p v-if="audit.data.value?.length === 0">No sensitive actions recorded yet.</p>
        <div v-else-if="audit.data.value" class="card overflow-auto">
          <table class="data-table w-full text-left text-sm">
            <thead><tr><th class="p-4">Time</th><th class="p-4">Actor</th><th class="p-4">Action</th><th class="p-4">Target</th></tr></thead>
            <tbody><tr v-for="entry in audit.data.value" :key="entry.id" class="border-t border-[var(--line)]"><td class="p-4">{{ entry.timestamp }}</td><td class="p-4">{{ entry.actor }}</td><td class="p-4">{{ entry.action }}</td><td class="p-4">{{ entry.target }}</td></tr></tbody>
          </table>
        </div>
      </section>

      <section v-else-if="section === 'settings'" aria-label="Hotel settings">
        <h2 class="text-2xl mt-8 mb-4">Hotel settings</h2>
        <p v-if="hotel.isPending.value" role="status">Loading hotel settings…</p>
        <Notice :message="hotel.error.value ? String(hotel.error.value) : ''" />
        <dl v-if="hotel.data.value" class="card settings-sheet p-6 grid sm:grid-cols-2 gap-6">
          <div v-for="[label, value] in [
            ['Name', hotel.data.value.name], ['Email', hotel.data.value.email || 'Not set'],
            ['Phone', hotel.data.value.phone || 'Not set'], ['Timezone', hotel.data.value.timezone],
            ['Currency', hotel.data.value.currency], ['Check-in time', hotel.data.value.check_in_time],
            ['Check-out time', hotel.data.value.check_out_time], ['Deposit percentage', `${hotel.data.value.deposit_percent}%`],
          ]" :key="label"><dt class="label">{{ label }}</dt><dd>{{ value }}</dd></div>
        </dl>
      </section>

      <section v-else aria-label="Reports">
        <h2 class="text-2xl mt-8 mb-2 font-serif">Executive Management Reports</h2>
        <p class="text-sm text-[var(--muted)] mb-6">
          Pre-formatted, authorized management information reports with formula-injection-sanitized CSV export for compliance and auditing.
        </p>

        <!-- The 5 MIS Reports Grid -->
        <div class="grid md:grid-cols-2 gap-4 mb-8">
          <div class="card p-5 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between">
                <span class="label text-xs">MIS Report 1</span>
                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">Daily Archive</span>
              </div>
              <h3 class="text-lg font-serif mt-1">Daily Manager Summary</h3>
              <p class="text-xs text-[var(--muted)] mt-1">
                Executive operational snapshot: sellable/sold room-nights, RevPAR, ADR, cash collections, and room readiness for today.
              </p>
            </div>
            <a :href="csvDaily" download="daily-manager-summary.csv" class="btn-secondary text-xs text-center">
              Export Daily Summary (CSV) ↓
            </a>
          </div>

          <div class="card p-5 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between">
                <span class="label text-xs">MIS Report 2</span>
                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300">Yield & Demand</span>
              </div>
              <h3 class="text-lg font-serif mt-1">Revenue & Occupancy by Room Type</h3>
              <p class="text-xs text-[var(--muted)] mt-1">
                Comparative room-type performance: capacity, sellable nights, realized occupancy %, net revenue, and ADR.
              </p>
            </div>
            <a :href="csvRevOcc" download="revenue-occupancy-report.csv" class="btn-secondary text-xs text-center">
              Export Room Type Yield (CSV) ↓
            </a>
          </div>

          <div class="card p-5 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between">
                <span class="label text-xs">MIS Report 3</span>
                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">Financial Audit</span>
              </div>
              <h3 class="text-lg font-serif mt-1">Cash Reconciliation & Audit Ledger</h3>
              <p class="text-xs text-[var(--muted)] mt-1">
                Gross payment collections, settled refunds, net cash variance, and payment gateway audit records.
              </p>
            </div>
            <a :href="csvCash" download="cash-reconciliation.csv" class="btn-secondary text-xs text-center">
              Export Cash Reconciliation (CSV) ↓
            </a>
          </div>

          <div class="card p-5 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between">
                <span class="label text-xs">MIS Report 4</span>
                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">Operational SLA</span>
              </div>
              <h3 class="text-lg font-serif mt-1">Housekeeping Turnaround & Efficiency</h3>
              <p class="text-xs text-[var(--muted)] mt-1">
                Turnover duration from checkout to ready status, staff member task completion, and inspection logs.
              </p>
            </div>
            <a :href="csvHK" download="housekeeping-turnaround.csv" class="btn-secondary text-xs text-center">
              Export Housekeeping Efficiency (CSV) ↓
            </a>
          </div>

          <div class="card p-5 flex flex-col justify-between space-y-3 md:col-span-2">
            <div>
              <div class="flex items-center justify-between">
                <span class="label text-xs">MIS Report 5</span>
                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">Credit Risk</span>
              </div>
              <h3 class="text-lg font-serif mt-1">Accounts Receivable Aging & Outstanding Balances</h3>
              <p class="text-xs text-[var(--muted)] mt-1">
                Aging buckets (Current 0–7 days, 8–14 days, 15–30 days, 30+ days) across unclosed active reservation folios.
              </p>
            </div>
            <a :href="csvAR" download="accounts-receivable-aging.csv" class="btn-secondary text-xs text-center">
              Export Accounts Receivable Aging (CSV) ↓
            </a>
          </div>
        </div>

        <!-- Custom Date Range KPI Report -->
        <h3 class="text-xl font-serif mt-8 mb-2">Custom Period Financial Metrics</h3>
        <p class="text-sm text-[var(--muted)] mb-4">Room revenue recognizes stay dates; cash uses payment settlement dates. Period end is exclusive.</p>
        <div class="flex flex-wrap gap-4 items-end mb-5">
          <label><span class="label">Start date</span><input v-model="start" class="field" type="date" /></label>
          <label><span class="label">End date (exclusive)</span><input v-model="end" class="field" type="date" /></label>
          <a :href="csvUrl" class="btn-secondary" download="hotel-report.csv">Download CSV</a>
        </div>
        <p v-if="report.isPending.value" role="status">Calculating report…</p>
        <Notice :message="report.error.value ? String(report.error.value) : ''" />
        <div v-if="report.data.value" class="card report-sheet p-6">
          <p class="label">{{ report.data.value.hotel }} · {{ report.data.value.timezone }} · {{ report.data.value.currency }}</p>
          <div class="grid sm:grid-cols-3 gap-5 mt-5">
            <div><p class="label">Occupancy rate</p><p class="text-2xl font-bold">{{ report.data.value.occupancy_rate_percent ?? 'N/A' }}{{ report.data.value.occupancy_rate_percent === null ? '' : '%' }}</p></div>
            <div><p class="label">Average daily rate</p><p class="text-2xl font-bold">{{ report.data.value.average_daily_rate_minor === null ? 'N/A' : money(report.data.value.average_daily_rate_minor) }}</p></div>
            <div><p class="label">Revenue per available room</p><p class="text-2xl font-bold">{{ report.data.value.revpar_minor === null ? 'N/A' : money(report.data.value.revpar_minor) }}</p></div>
            <div><p class="label">Sold room-nights</p><p class="text-2xl font-bold">{{ report.data.value.sold_room_nights }}</p></div>
            <div><p class="label">Net room revenue</p><p class="text-2xl font-bold font-mono">{{ money(report.data.value.net_room_revenue_minor) }}</p></div>
            <div><p class="label">Settled cash</p><p class="text-2xl font-bold font-mono text-emerald-700 dark:text-emerald-400">{{ money(report.data.value.settled_cash_minor) }}</p></div>
          </div>
        </div>
      </section>
    </div>
  </PortalLayout>
</template>
