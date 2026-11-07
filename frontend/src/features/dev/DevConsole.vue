<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { adminApi } from '../../services/api'

const props = defineProps<{ role: string }>()
const canWrite = computed(() => props.role === 'DEVELOPER')
const client = useQueryClient()
const tabs = [
  ['health', 'System health'], ['jobs', 'Jobs'], ['outbox', 'Outbox'], ['provider', 'Payment provider'],
  ['flags', 'Feature flags'], ['config', 'Config'], ['errors', 'Errors'], ['security', 'Security'],
] as const
type Tab = typeof tabs[number][0]
const tab = ref<Tab>('health')
const message = ref('')
const ok = ref(true)
const busy = ref(false)

const get = <T,>(path: string) => adminApi<T>(`/admin/dev/${path}`)
const health = useQuery({ queryKey: ['dev', 'health'], queryFn: () => get<Health>('health'), enabled: computed(() => tab.value === 'health'), refetchInterval: 15000 })
const jobs = useQuery({ queryKey: ['dev', 'jobs'], queryFn: () => get<Jobs>('jobs'), enabled: computed(() => tab.value === 'jobs') })
const outbox = useQuery({ queryKey: ['dev', 'outbox'], queryFn: () => get<Outbox>('outbox'), enabled: computed(() => tab.value === 'outbox') })
const provider = useQuery({ queryKey: ['dev', 'provider'], queryFn: () => get<Provider>('payment-provider'), enabled: computed(() => tab.value === 'provider') })
const flagList = useQuery({ queryKey: ['dev', 'flags'], queryFn: () => get<Flag[]>('flags'), enabled: computed(() => tab.value === 'flags') })
const config = useQuery({ queryKey: ['dev', 'config'], queryFn: () => get<Record<string, unknown>>('config'), enabled: computed(() => tab.value === 'config') })
const errors = useQuery({ queryKey: ['dev', 'errors'], queryFn: () => get<ErrorRow[]>('errors'), enabled: computed(() => tab.value === 'errors') })
const security = useQuery({ queryKey: ['dev', 'security'], queryFn: () => get<Security>('security'), enabled: computed(() => tab.value === 'security') })

interface Health { database: { ok: boolean; latency_ms: number | null }; cache: { ok: boolean }; celery: { healthy: boolean; last_beat_task_seconds_ago: number | null }
  pending_migrations: number | null; backup: { configured: boolean; ok: boolean; finished_at: string | null; age_seconds: number | null; size_bytes: number | null; last_restore_drill: { ok: boolean; at: string } | null }
  outbox_pending: number; errors_24h: number; versions: Record<string, string>; environment: string; debug: boolean }
interface Jobs { summary: { task: string; runs: number; failures: number }[]; recent: { id: number; task: string; status: string; started_at: string; duration_ms: number; error: string }[] }
interface Outbox { pending_count: number; delivered_count: number; note: string; pending: { id: number; kind: string; target: string; created_at: string }[] }
interface Provider { provider: string; env_default: string; bank_ready: boolean; can_use_demo: boolean; currency: string; configured: Record<string, boolean>; attempts_24h: Record<string, number>; attempt_window_minutes: number; late_window_hours: number
  last_sweep: { status: string; started_at: string; duration_ms: number; error: string } | null }
interface Flag { key: string; enabled: boolean; description: string; updated_by: string; updated_at: string }
interface ErrorRow { id: number; created_at: string; request_id: string; method: string; path: string; exc_type: string; message: string }
interface Security { failed_logins_24h: { username: string; portal: string; count: number }[]; active_sessions: { user_id: number; username: string; role: string; sessions: number }[] }

const probe = ref<{ ok: boolean; status?: string; error?: string; latency_ms: number } | null>(null)
const newFlag = ref('')

async function act(action: () => Promise<void>, success: string, refreshKey?: string) {
  if (busy.value) return
  busy.value = true
  message.value = ''
  try {
    await action()
    ok.value = true
    message.value = success
    if (refreshKey) await client.invalidateQueries({ queryKey: ['dev', refreshKey] })
  } catch (caught) {
    ok.value = false
    message.value = String(caught)
  } finally {
    busy.value = false
  }
}

const toggle = (f: Flag) => act(async () => { await adminApi(`/admin/dev/flags/${f.key}`, { enabled: !f.enabled }, 'PATCH') }, `${f.key} is now ${f.enabled ? 'off' : 'on'}.`, 'flags')
const addFlag = () => act(async () => { await adminApi('/admin/dev/flags', { key: newFlag.value }); newFlag.value = '' }, 'Flag created (off).', 'flags')
const checkBakong = () => act(async () => { probe.value = await adminApi('/admin/dev/payment-provider/check', {}) }, 'Connectivity check finished.')
const setMode = (mode: 'demo' | 'bank') => act(async () => { await adminApi('/admin/dev/payment-mode', { mode }) },
  mode === 'bank' ? 'Bank payments (Bakong KHQR) are now used for new payments.' : 'Demo payments are now used for new payments.', 'provider')
const revoke = (id: number, name: string) => act(async () => { await adminApi(`/admin/dev/security/revoke/${id}`, {}) }, `Signed out ${name} everywhere.`, 'security')
const badge = (good: boolean) => (good ? 'text-[var(--status-available)] ' : 'text-[var(--status-out)]')
const stamp = (v: string) => v.slice(0, 19).replace('T', ' ')
</script>

<template>
  <section aria-label="Developer console" class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-2xl">Developer console</h2>
      <span v-if="!canWrite" class="badge">Read-only for administrators</span>
    </div>
    <nav class="flex flex-wrap gap-2" aria-label="Developer sections">
      <button v-for="[id, label] in tabs" :key="id" type="button" :class="tab === id ? 'btn' : 'btn-secondary'" @click="tab = id">{{ label }}</button>
    </nav>
    <Notice :message="message" :status="ok" />

    <div v-if="tab === 'health'" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <p v-if="health.isPending.value" role="status">Checking…</p>
      <template v-if="health.data.value">
        <div class="card p-4"><p class="label">Database</p><p :class="badge(health.data.value.database.ok)" class="text-xl font-semibold">{{ health.data.value.database.ok ? 'Online' : 'Offline' }}</p><p class="text-xs text-[var(--silt)]">{{ health.data.value.database.latency_ms }} ms</p></div>
        <div class="card p-4"><p class="label">Cache / Redis</p><p :class="badge(health.data.value.cache.ok)" class="text-xl font-semibold">{{ health.data.value.cache.ok ? 'Online' : 'Degraded' }}</p></div>
        <div class="card p-4"><p class="label">Celery beat + worker</p><p :class="badge(health.data.value.celery.healthy)" class="text-xl font-semibold">{{ health.data.value.celery.healthy ? 'Running' : 'No recent run' }}</p><p class="text-xs text-[var(--silt)]">last task {{ health.data.value.celery.last_beat_task_seconds_ago ?? '—' }} s ago</p></div>
        <div class="card p-4"><p class="label">Pending migrations</p><p :class="badge(health.data.value.pending_migrations === 0)" class="text-xl font-semibold">{{ health.data.value.pending_migrations ?? 'unknown' }}</p></div>
        <div class="card p-4"><p class="label">Database backup</p>
          <p :class="badge(health.data.value.backup.ok)" class="text-xl font-semibold">{{ !health.data.value.backup.configured ? 'Not configured' : health.data.value.backup.ok ? 'Healthy' : 'Stale or failed' }}</p>
          <p class="text-xs text-[var(--silt)]"><template v-if="health.data.value.backup.finished_at">last {{ stamp(health.data.value.backup.finished_at) }} · {{ Math.round((health.data.value.backup.size_bytes ?? 0) / 1024) }} KB</template><template v-else>no marker file found</template></p>
          <p class="text-xs" :class="health.data.value.backup.last_restore_drill?.ok ? 'text-[var(--silt)]' : 'text-[var(--status-out)]'">restore drill: {{ health.data.value.backup.last_restore_drill ? (health.data.value.backup.last_restore_drill.ok ? 'passed ' + stamp(health.data.value.backup.last_restore_drill.at) : 'FAILED') : 'never run' }}</p></div>
        <div class="card p-4"><p class="label">Outbox pending</p><p class="text-xl font-semibold">{{ health.data.value.outbox_pending }}</p></div>
        <div class="card p-4"><p class="label">Errors (24 h)</p><p :class="badge(health.data.value.errors_24h === 0)" class="text-xl font-semibold">{{ health.data.value.errors_24h }}</p></div>
        <div class="card p-4 sm:col-span-2 lg:col-span-3 text-sm">
          Environment <strong>{{ health.data.value.environment }}</strong> · debug <strong :class="badge(!health.data.value.debug)">{{ health.data.value.debug ? 'ON' : 'off' }}</strong> ·
          app {{ health.data.value.versions.app }} · Django {{ health.data.value.versions.django }} · Python {{ health.data.value.versions.python }}
        </div>
      </template>
      <Notice :message="health.error.value ? String(health.error.value) : ''" />
    </div>

    <div v-else-if="tab === 'jobs'" class="space-y-4">
      <div class="card overflow-auto"><table class="data-table w-full text-left text-sm"><caption class="text-left p-3 font-semibold">Last 24 hours</caption>
        <thead><tr><th>Task</th><th>Runs</th><th>Failures</th></tr></thead>
        <tbody><tr v-for="s in jobs.data.value?.summary" :key="s.task"><td>{{ s.task }}</td><td>{{ s.runs }}</td><td :class="s.failures ? 'text-[var(--status-out)] font-semibold' : ''">{{ s.failures }}</td></tr></tbody></table></div>
      <div class="card overflow-auto"><table class="data-table w-full text-left text-sm"><caption class="text-left p-3 font-semibold">Recent runs</caption>
        <thead><tr><th>When</th><th>Task</th><th>Status</th><th>ms</th><th>Error</th></tr></thead>
        <tbody><tr v-for="r in jobs.data.value?.recent" :key="r.id"><td>{{ stamp(r.started_at) }}</td><td>{{ r.task }}</td><td :class="r.status === 'FAILURE' ? 'text-[var(--status-out)]' : ''">{{ r.status }}</td><td>{{ r.duration_ms }}</td><td>{{ r.error }}</td></tr></tbody></table></div>
    </div>

    <div v-else-if="tab === 'outbox'" class="card p-4 space-y-3">
      <p v-if="outbox.data.value" class="text-sm">{{ outbox.data.value.pending_count }} pending · {{ outbox.data.value.delivered_count }} delivered. <span class="text-[var(--silt)]">{{ outbox.data.value.note }}</span></p>
      <table v-if="outbox.data.value?.pending.length" class="data-table w-full text-left text-sm"><thead><tr><th>Created</th><th>Kind</th><th>Target</th></tr></thead>
        <tbody><tr v-for="o in outbox.data.value.pending" :key="o.id"><td>{{ stamp(o.created_at) }}</td><td>{{ o.kind }}</td><td>{{ o.target }}</td></tr></tbody></table>
    </div>

    <div v-else-if="tab === 'provider'" class="space-y-4">
      <div v-if="provider.data.value" class="card p-4 space-y-3">
        <p class="label">Payment mode for new payments</p>
        <div class="inline-flex rounded-full border border-[var(--rule)] overflow-hidden" role="group" aria-label="Payment mode">
          <button type="button" class="px-4 py-2 text-sm" :class="provider.data.value.provider === 'development' ? 'bg-[var(--laterite)] text-white' : ''"
            :aria-pressed="provider.data.value.provider === 'development'" :disabled="busy || !canWrite || !provider.data.value.can_use_demo" @click="setMode('demo')">Demo payment</button>
          <button type="button" class="px-4 py-2 text-sm" :class="provider.data.value.provider === 'bakong' ? 'bg-[var(--laterite)] text-white' : ''"
            :aria-pressed="provider.data.value.provider === 'bakong'" :disabled="busy || !canWrite || !provider.data.value.bank_ready" @click="setMode('bank')">Bank payment (Bakong)</button>
        </div>
        <p class="text-xs text-[var(--silt)]">Demo = simulated checkout, no money moves. Bank = real Bakong KHQR. Payments already started keep their original mode and bank payments are still confirmed after switching.
          <span v-if="!provider.data.value.bank_ready" class="text-[var(--status-out)]"> Bank mode needs the BAKONG_* values in the server environment.</span>
          <span v-if="!canWrite"> Only developers can switch.</span></p>
      </div>
      <div v-if="provider.data.value" class="card p-4 space-y-3 text-sm">
        <p>Active provider: <strong>{{ provider.data.value.provider }}</strong> · currency {{ provider.data.value.currency }} · QR window {{ provider.data.value.attempt_window_minutes }} min · late-payment watch {{ provider.data.value.late_window_hours }} h</p>
        <p>Credentials: <span v-for="(set, name) in provider.data.value.configured" :key="name" class="mr-3" :class="badge(set)">{{ name }}: {{ set ? 'set' : 'MISSING' }}</span></p>
        <p>Attempts (24 h): <span v-for="(n, status) in provider.data.value.attempts_24h" :key="status" class="mr-3">{{ status }} {{ n }}</span><span v-if="!Object.keys(provider.data.value.attempts_24h).length">none</span></p>
        <p v-if="provider.data.value.last_sweep">Last sweep: {{ stamp(provider.data.value.last_sweep.started_at) }} · {{ provider.data.value.last_sweep.status }} · {{ provider.data.value.last_sweep.duration_ms }} ms {{ provider.data.value.last_sweep.error }}</p>
        <div v-if="canWrite && provider.data.value.bank_ready">
          <button class="btn" :disabled="busy" @click="checkBakong">Test Bakong connectivity</button>
          <p v-if="probe" class="mt-2" :class="badge(probe.ok)">{{ probe.ok ? `Reachable (${probe.status})` : probe.error }} · {{ probe.latency_ms }} ms</p>
        </div>
        <p v-else-if="provider.data.value.provider !== 'bakong'" class="text-[var(--silt)]">The development emulator is active; no Bakong calls are made.</p>
      </div>
    </div>

    <div v-else-if="tab === 'flags'" class="card p-4 space-y-3">
      <ul class="divide-y divide-[var(--rule)]">
        <li v-for="f in flagList.data.value" :key="f.key" class="py-3 flex items-center justify-between gap-3">
          <div><p class="tabular-nums text-sm">{{ f.key }}</p><p class="text-xs text-[var(--silt)]">{{ f.description }} <span v-if="f.updated_by">· last by {{ f.updated_by }}</span></p></div>
          <button class="btn-secondary" :disabled="busy || !canWrite" :aria-pressed="f.enabled" @click="toggle(f)">{{ f.enabled ? 'ON' : 'off' }}</button>
        </li>
      </ul>
      <form v-if="canWrite" class="flex gap-3" @submit.prevent="addFlag">
        <input v-model="newFlag" class="field flex-1" placeholder="new_flag_key" aria-label="New flag key" pattern="[a-z0-9_]{2,60}" required />
        <button class="btn" :disabled="busy">Add flag</button>
      </form>
    </div>

    <pre v-else-if="tab === 'config'" class="card p-4 text-xs overflow-auto">{{ JSON.stringify(config.data.value, null, 2) }}</pre>

    <div v-else-if="tab === 'errors'" class="card overflow-auto">
      <table class="data-table w-full text-left text-sm"><thead><tr><th>When</th><th>Request</th><th>Error</th><th>Request ID</th></tr></thead>
        <tbody>
          <tr v-for="e in errors.data.value" :key="e.id"><td>{{ stamp(e.created_at) }}</td><td>{{ e.method }} {{ e.path }}</td><td>{{ e.exc_type }}: {{ e.message }}</td><td class="tabular-nums text-xs">{{ e.request_id.slice(0, 8) }}</td></tr>
          <tr v-if="errors.data.value?.length === 0"><td colspan="4" class="text-[var(--silt)]">No server errors recorded.</td></tr>
        </tbody></table>
    </div>

    <div v-else-if="tab === 'security'" class="grid lg:grid-cols-2 gap-4">
      <div class="card overflow-auto"><table class="data-table w-full text-left text-sm"><caption class="text-left p-3 font-semibold">Failed sign-ins (24 h)</caption>
        <thead><tr><th>Username</th><th>Portal</th><th>Count</th></tr></thead>
        <tbody>
          <tr v-for="f in security.data.value?.failed_logins_24h" :key="f.username + f.portal"><td>{{ f.username }}</td><td>{{ f.portal }}</td><td :class="f.count >= 5 ? 'text-[var(--status-out)] font-semibold' : ''">{{ f.count }}</td></tr>
          <tr v-if="security.data.value?.failed_logins_24h.length === 0"><td colspan="3" class="text-[var(--silt)]">None.</td></tr>
        </tbody></table></div>
      <div class="card overflow-auto"><table class="data-table w-full text-left text-sm"><caption class="text-left p-3 font-semibold">Active staff sessions</caption>
        <thead><tr><th>User</th><th>Role</th><th>Sessions</th><th /></tr></thead>
        <tbody><tr v-for="s in security.data.value?.active_sessions" :key="s.user_id"><td>{{ s.username }}</td><td>{{ s.role }}</td><td>{{ s.sessions }}</td>
          <td><button v-if="canWrite" class="btn-secondary" :disabled="busy" @click="revoke(s.user_id, s.username)">Sign out everywhere</button></td></tr></tbody></table></div>
    </div>
  </section>
</template>
