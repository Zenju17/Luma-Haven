<script setup lang="ts">
import { ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { adminApi } from '../../services/api'
import { renderMarkdown } from '../../utils/markdown'

interface Doc { id: number; kind: string; language: 'en' | 'km'; version: number; title: string; status: string; effective_at: string | null; consent_count: number; created_by: string }
interface DocDetail extends Doc { body_markdown: string }
const KINDS = ['TERMS', 'PRIVACY', 'CANCELLATION', 'COOKIES', 'PAYMENT', 'STAFF_AGREEMENT']

const client = useQueryClient()
const docs = useQuery({ queryKey: ['admin', 'legal'], queryFn: () => adminApi<Doc[]>('/admin/legal') })
const message = ref('')
const ok = ref(true)
const busy = ref(false)
const current = ref<DocDetail | null>(null)
const form = ref({ kind: 'TERMS', language: 'en' as 'en' | 'km', title: '', body_markdown: '' })

async function run(action: () => Promise<void>, success: string) {
  if (busy.value) return
  busy.value = true
  message.value = ''
  try {
    await action()
    ok.value = true
    message.value = success
    await client.invalidateQueries({ queryKey: ['admin', 'legal'] })
  } catch (caught) {
    ok.value = false
    message.value = String(caught)
  } finally {
    busy.value = false
  }
}

const view = (d: Doc) => run(async () => { current.value = await adminApi<DocDetail>(`/admin/legal/${d.id}`) }, '')
const createDraft = () => run(async () => {
  current.value = await adminApi<DocDetail>('/admin/legal', form.value)
}, 'Draft created. Edit and publish it to start a new version.')
const saveDraft = () => run(async () => {
  const c = current.value!
  current.value = await adminApi<DocDetail>(`/admin/legal/${c.id}`, { title: c.title, body_markdown: c.body_markdown }, 'PATCH')
}, 'Draft saved.')
const publish = () => run(async () => {
  current.value = await adminApi<DocDetail>(`/admin/legal/${current.value!.id}/publish`, {})
}, 'Published. Guests must re-accept the new version at their next booking.')
</script>

<template>
  <section aria-label="Legal documents" class="space-y-6">
    <h2 class="text-2xl">Legal documents</h2>
    <p class="text-sm text-[var(--muted)]">Published versions are permanent. To change a policy, create a draft, publish it as a new version, and guests will be asked to accept it again. The seeded texts are templates and need legal review.</p>
    <Notice :message="message" :status="ok" />
    <div class="grid lg:grid-cols-2 gap-6">
      <div class="card overflow-auto">
        <table class="data-table w-full text-left text-sm min-w-[480px]">
          <thead><tr><th>Document</th><th>Lang</th><th>Ver</th><th>Status</th><th>Accepted</th><th /></tr></thead>
          <tbody>
            <tr v-for="d in docs.data.value" :key="d.id">
              <td>{{ d.kind }}</td><td>{{ d.language.toUpperCase() }}</td><td>v{{ d.version }}</td><td>{{ d.status }}</td><td>{{ d.consent_count }}</td>
              <td><button class="btn-secondary" @click="view(d)">Open</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="docs.isPending.value" class="p-4" role="status">Loading…</p>
      </div>
      <div class="space-y-6">
        <form class="card p-5 space-y-3" @submit.prevent="createDraft">
          <h3 class="text-lg font-semibold">New version draft</h3>
          <div class="grid grid-cols-2 gap-3">
            <label class="label">Kind<select v-model="form.kind" class="field mt-1 w-full"><option v-for="k in KINDS" :key="k">{{ k }}</option></select></label>
            <label class="label">Language<select v-model="form.language" class="field mt-1 w-full"><option value="en">English</option><option value="km">ខ្មែរ</option></select></label>
          </div>
          <label class="label block">Title<input v-model="form.title" class="field mt-1 w-full" required /></label>
          <label class="label block">Text (Markdown)<textarea v-model="form.body_markdown" class="field mt-1 w-full font-mono text-sm" rows="6" required /></label>
          <button class="btn" :disabled="busy">Create draft</button>
        </form>
        <div v-if="current" class="card p-5 space-y-3">
          <p class="label">{{ current.kind }} · {{ current.language.toUpperCase() }} · v{{ current.version }} · {{ current.status }}</p>
          <template v-if="current.status === 'DRAFT'">
            <input v-model="current.title" class="field w-full" aria-label="Title" />
            <textarea v-model="current.body_markdown" class="field w-full font-mono text-sm" rows="10" aria-label="Text" />
            <div class="flex gap-3">
              <button class="btn-secondary" :disabled="busy" @click="saveDraft">Save draft</button>
              <button class="btn" :disabled="busy" @click="publish">Publish new version</button>
            </div>
          </template>
          <div v-else class="text-sm leading-relaxed space-y-2" v-html="renderMarkdown(current.body_markdown)" />
        </div>
      </div>
    </div>
  </section>
</template>
