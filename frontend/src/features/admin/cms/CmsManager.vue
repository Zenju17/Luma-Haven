<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import Notice from '../../../components/Notice.vue'
import { adminApi } from '../../../services/api'
import { renderMarkdown } from '../../../utils/markdown'

const props = defineProps<{ role: string }>()
interface PageRow { id: number; slug: string; language: 'en' | 'km'; title: string; is_published: boolean; has_unpublished_changes: boolean; updated_by: string; updated_at: string }
interface Revision { id: number; action: string; saved_by: string; saved_at: string }
interface PageDetail extends PageRow { body_markdown: string; seo_description: string; revisions: Revision[] }
interface BlockRow { id: number; key: string; language: 'en' | 'km'; content: Record<string, string>; is_published: boolean; has_unpublished_changes: boolean; starts_at: string | null; ends_at: string | null }

const client = useQueryClient()
const canPublish = computed(() => props.role === 'ADMIN')
const tab = ref<'pages' | 'blocks'>('pages')
const message = ref('')
const ok = ref(true)
const busy = ref(false)

const pages = useQuery({ queryKey: ['cms', 'pages'], queryFn: () => adminApi<PageRow[]>('/admin/cms/pages') })
const blocks = useQuery({ queryKey: ['cms', 'blocks'], queryFn: () => adminApi<BlockRow[]>('/admin/cms/blocks') })

// ---- page editor
const editing = ref<PageDetail | null>(null)
const isNew = ref(false)
const form = ref({ slug: '', language: 'en' as 'en' | 'km', title: '', body_markdown: '', seo_description: '' })
const preview = computed(() => renderMarkdown(form.value.body_markdown))

async function run(action: () => Promise<void>, success: string) {
  if (busy.value) return
  busy.value = true
  message.value = ''
  try {
    await action()
    ok.value = true
    message.value = success
  } catch (caught) {
    ok.value = false
    message.value = String(caught)
  } finally {
    busy.value = false
  }
}

function startNew() {
  isNew.value = true
  editing.value = null
  form.value = { slug: '', language: 'en', title: '', body_markdown: '', seo_description: '' }
}

async function open(row: PageRow) {
  await run(async () => {
    const detail = await adminApi<PageDetail>(`/admin/cms/pages/${row.id}`)
    isNew.value = false
    editing.value = detail
    form.value = { slug: detail.slug, language: detail.language, title: detail.title, body_markdown: detail.body_markdown, seo_description: detail.seo_description }
  }, '')
}

const refresh = () => client.invalidateQueries({ queryKey: ['cms'] })

function save() {
  return run(async () => {
    const saved = isNew.value
      ? await adminApi<PageDetail>('/admin/cms/pages', form.value)
      : await adminApi<PageDetail>(`/admin/cms/pages/${editing.value!.id}`, form.value, 'PATCH')
    editing.value = saved
    isNew.value = false
    await refresh()
  }, 'Draft saved.')
}

function pageAction(action: 'publish' | 'unpublish') {
  return run(async () => {
    editing.value = await adminApi<PageDetail>(`/admin/cms/pages/${editing.value!.id}/${action}`, {})
    await refresh()
  }, action === 'publish' ? 'Published. Guests now see this version.' : 'Unpublished.')
}

function restore(revisionId: number) {
  return run(async () => {
    const detail = await adminApi<PageDetail>(`/admin/cms/pages/${editing.value!.id}/restore`, { revision_id: revisionId })
    editing.value = detail
    form.value = { slug: detail.slug, language: detail.language, title: detail.title, body_markdown: detail.body_markdown, seo_description: detail.seo_description }
    await refresh()
  }, 'Revision restored to the draft. Publish to make it live.')
}

// ---- blocks
const blockForm = ref({ key: 'site.announcement', language: 'en' as 'en' | 'km', text: '', link: '', starts_at: '', ends_at: '' })

function editBlock(b: BlockRow) {
  blockForm.value = { key: b.key, language: b.language, text: b.content.text ?? '', link: b.content.link ?? '',
    starts_at: b.starts_at ? b.starts_at.slice(0, 16) : '', ends_at: b.ends_at ? b.ends_at.slice(0, 16) : '' }
}

function saveBlock() {
  const f = blockForm.value
  const content: Record<string, string> = { text: f.text }
  if (f.link) content.link = f.link
  const iso = (v: string) => (v ? new Date(v).toISOString() : null)
  return run(async () => {
    await adminApi('/admin/cms/blocks', { key: f.key, language: f.language, content, starts_at: iso(f.starts_at), ends_at: iso(f.ends_at) })
    await refresh()
  }, 'Block draft saved.')
}

function blockAction(b: BlockRow, action: 'publish' | 'unpublish') {
  return run(async () => {
    await adminApi(`/admin/cms/blocks/${b.id}/${action}`, {})
    await refresh()
  }, action === 'publish' ? 'Block published.' : 'Block unpublished.')
}
</script>

<template>
  <section aria-label="Content management" class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-2xl">Content (CMS)</h2>
      <div class="flex gap-2" role="tablist">
        <button type="button" role="tab" :aria-selected="tab === 'pages'" :class="tab === 'pages' ? 'btn' : 'btn-secondary'" @click="tab = 'pages'">Pages</button>
        <button type="button" role="tab" :aria-selected="tab === 'blocks'" :class="tab === 'blocks' ? 'btn' : 'btn-secondary'" @click="tab = 'blocks'">Banners &amp; blocks</button>
      </div>
    </div>
    <p class="text-sm text-[var(--silt)]">Editors save drafts; only an administrator publishes. Guests always see the last published version. Markdown is rendered safely — raw HTML is shown as text.</p>
    <Notice :message="message" :status="ok" />

    <template v-if="tab === 'pages'">
      <div class="grid lg:grid-cols-[minmax(0,22rem)_1fr] gap-6">
        <div class="card p-4 space-y-3">
          <button class="btn w-full" @click="startNew">New page</button>
          <p v-if="pages.isPending.value" role="status">Loading pages…</p>
          <Notice :message="pages.error.value ? String(pages.error.value) : ''" />
          <ul class="divide-y divide-[var(--rule)]">
            <li v-for="p in pages.data.value" :key="p.id">
              <button class="w-full text-left py-3" @click="open(p)">
                <span class="font-semibold">{{ p.title }}</span>
                <span class="block text-xs text-[var(--silt)]">/p/{{ p.slug }} · {{ p.language.toUpperCase() }} ·
                  {{ p.is_published ? (p.has_unpublished_changes ? 'published, draft differs' : 'published') : 'draft' }}</span>
              </button>
            </li>
          </ul>
          <p v-if="pages.data.value?.length === 0" class="text-sm text-[var(--silt)]">No pages yet.</p>
        </div>

        <form v-if="isNew || editing" class="card p-5 space-y-4" @submit.prevent="save">
          <div class="grid sm:grid-cols-3 gap-3">
            <label class="label">Slug<input v-model="form.slug" class="field mt-1 w-full" :disabled="!isNew" placeholder="about" required /></label>
            <label class="label">Language
              <select v-model="form.language" class="field mt-1 w-full" :disabled="!isNew"><option value="en">English</option><option value="km">ខ្មែរ</option></select>
            </label>
            <label class="label">Title<input v-model="form.title" class="field mt-1 w-full" maxlength="160" required /></label>
          </div>
          <label class="label block">Search description (optional)<input v-model="form.seo_description" class="field mt-1 w-full" maxlength="300" /></label>
          <div class="grid md:grid-cols-2 gap-4">
            <label class="label">Body (Markdown)<textarea v-model="form.body_markdown" class="field mt-1 w-full font-mono text-sm" rows="14" /></label>
            <div><p class="label">Preview</p><div class="mt-1 text-sm leading-relaxed cms-preview" v-html="preview" /></div>
          </div>
          <div class="flex flex-wrap gap-3">
            <button class="btn" :disabled="busy || !form.title">Save draft</button>
            <template v-if="editing && canPublish">
              <button type="button" class="btn-secondary" :disabled="busy" @click="pageAction('publish')">Publish</button>
              <button v-if="editing.is_published" type="button" class="btn-secondary" :disabled="busy" @click="pageAction('unpublish')">Unpublish</button>
            </template>
            <p v-else-if="editing" class="text-xs text-[var(--silt)] self-center">Ask an administrator to publish.</p>
          </div>
          <div v-if="editing?.revisions.length">
            <p class="label">History</p>
            <ul class="text-sm divide-y divide-[var(--rule)] mt-1">
              <li v-for="r in editing.revisions" :key="r.id" class="py-2 flex items-center justify-between gap-3">
                <span>{{ r.action }} · {{ r.saved_by }} · {{ r.saved_at.slice(0, 16).replace('T', ' ') }}</span>
                <button type="button" class="btn-secondary" :disabled="busy" @click="restore(r.id)">Restore to draft</button>
              </li>
            </ul>
          </div>
        </form>
        <div v-else class="card p-8 text-[var(--silt)]">Select a page or create a new one.</div>
      </div>
    </template>

    <template v-else>
      <div class="grid lg:grid-cols-2 gap-6">
        <form class="card p-5 space-y-3" @submit.prevent="saveBlock">
          <h3 class="text-lg font-semibold">Banner / block</h3>
          <label class="label block">Key<input v-model="blockForm.key" class="field mt-1 w-full" required /></label>
          <p class="text-xs text-[var(--silt)]">Use <code>site.announcement</code> for the banner shown at the top of every guest page.</p>
          <label class="label block">Language
            <select v-model="blockForm.language" class="field mt-1 w-full"><option value="en">English</option><option value="km">ខ្មែរ</option></select>
          </label>
          <label class="label block">Text<input v-model="blockForm.text" class="field mt-1 w-full" maxlength="500" required /></label>
          <label class="label block">Link (optional, / or https://)<input v-model="blockForm.link" class="field mt-1 w-full" maxlength="500" /></label>
          <div class="grid grid-cols-2 gap-3">
            <label class="label">Show from<input v-model="blockForm.starts_at" type="datetime-local" class="field mt-1 w-full" /></label>
            <label class="label">Show until<input v-model="blockForm.ends_at" type="datetime-local" class="field mt-1 w-full" /></label>
          </div>
          <button class="btn" :disabled="busy || !blockForm.text">Save draft</button>
        </form>
        <div class="card p-4">
          <p v-if="blocks.isPending.value" role="status">Loading blocks…</p>
          <ul class="divide-y divide-[var(--rule)]">
            <li v-for="b in blocks.data.value" :key="b.id" class="py-3 space-y-1">
              <p class="font-semibold">{{ b.key }} · {{ b.language.toUpperCase() }}
                <span class="text-xs font-normal text-[var(--silt)]">{{ b.is_published ? (b.has_unpublished_changes ? 'published, draft differs' : 'published') : 'draft' }}</span></p>
              <p class="text-sm">{{ b.content.text }}</p>
              <div class="flex gap-2">
                <button class="btn-secondary" type="button" @click="editBlock(b)">Edit</button>
                <template v-if="canPublish">
                  <button class="btn-secondary" type="button" :disabled="busy" @click="blockAction(b, 'publish')">Publish</button>
                  <button v-if="b.is_published" class="btn-secondary" type="button" :disabled="busy" @click="blockAction(b, 'unpublish')">Unpublish</button>
                </template>
              </div>
            </li>
          </ul>
          <p v-if="blocks.data.value?.length === 0" class="text-sm text-[var(--silt)]">No blocks yet.</p>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.cms-preview :deep(h2) { font-size: 1.3rem; margin: 0.5rem 0; }
.cms-preview :deep(p) { margin: 0.5rem 0; }
.cms-preview :deep(ul), .cms-preview :deep(ol) { margin-left: 1.25rem; list-style: revert; }
</style>
