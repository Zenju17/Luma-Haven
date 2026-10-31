<script setup lang="ts">
import { ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { adminApi } from '../../services/api'

interface Req { id: number; type: string; status: string; guest_name: string; guest_email: string; note: string; resolution: string; requested_at: string; due_at: string; overdue: boolean; handled_by: string }
const client = useQueryClient()
const requests = useQuery({ queryKey: ['admin', 'data-requests'], queryFn: () => adminApi<Req[]>('/admin/data-requests') })
const message = ref('')
const ok = ref(true)
const busy = ref(false)
const resolution = ref<Record<number, string>>({})

async function resolve(r: Req, decision: 'complete' | 'reject') {
  if (busy.value) return
  busy.value = true
  message.value = ''
  try {
    await adminApi(`/admin/data-requests/${r.id}/resolve`, { decision, resolution: resolution.value[r.id] ?? '' })
    ok.value = true
    message.value = decision === 'complete' ? (r.type === 'DELETE' ? 'Guest anonymised; accounting records kept.' : 'Request marked complete.') : 'Request rejected.'
    await client.invalidateQueries({ queryKey: ['admin', 'data-requests'] })
  } catch (caught) {
    ok.value = false
    message.value = String(caught)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section aria-label="Privacy requests" class="space-y-4">
    <h2 class="text-2xl">Privacy requests</h2>
    <p class="text-sm text-[var(--muted)]">Guests must be answered within 30 days. Deleting anonymises the guest profile and is blocked while they have an active or upcoming reservation.</p>
    <Notice :message="message" :status="ok" />
    <p v-if="requests.isPending.value" role="status">Loading requests…</p>
    <Notice :message="requests.error.value ? String(requests.error.value) : ''" />
    <p v-if="requests.data.value?.length === 0" class="text-[var(--muted)]">No privacy requests.</p>
    <div v-for="r in requests.data.value" :key="r.id" class="card p-4 space-y-2">
      <p class="font-semibold">{{ r.type }} · {{ r.guest_name }} <span class="font-normal text-[var(--muted)]">{{ r.guest_email }}</span></p>
      <p class="text-sm text-[var(--muted)]">Requested {{ r.requested_at.slice(0, 10) }} · due {{ r.due_at.slice(0, 10) }}
        <span v-if="r.overdue" class="text-rose-500 font-semibold"> · OVERDUE</span> · {{ r.status }}<template v-if="r.handled_by"> by {{ r.handled_by }}</template></p>
      <p v-if="r.note" class="text-sm">“{{ r.note }}”</p>
      <p v-if="r.resolution" class="text-sm">Resolution: {{ r.resolution }}</p>
      <div v-if="r.status === 'OPEN'" class="flex flex-wrap items-center gap-3">
        <input v-model="resolution[r.id]" class="field flex-1 min-w-[12rem]" placeholder="Resolution note (required to reject)" :aria-label="`Resolution for request ${r.id}`" />
        <button class="btn" :disabled="busy" @click="resolve(r, 'complete')">Complete</button>
        <button class="btn-secondary" :disabled="busy" @click="resolve(r, 'reject')">Reject</button>
      </div>
    </div>
  </section>
</template>
