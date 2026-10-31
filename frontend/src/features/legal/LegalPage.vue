<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import { renderMarkdown } from '../../utils/markdown'
import { useLanguage } from '../../composables/useLanguage'
import type { LegalDoc } from '../../types'

const route = useRoute()
const { lang } = useLanguage()
const kind = computed(() => String(route.params.kind))
const doc = useQuery({
  queryKey: computed(() => ['legal', kind.value, lang.value]),
  queryFn: () => api<LegalDoc>(`/legal/documents/${kind.value}?lang=${lang.value}`),
})
const html = computed(() => renderMarkdown(doc.data.value?.body_markdown ?? ''))
</script>

<template>
  <SiteLayout>
    <div class="py-8 sm:py-12 max-w-3xl mx-auto space-y-6">
      <div class="flex items-center justify-between gap-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">Legal</p>
        <div class="inline-flex rounded-full border border-[var(--glass-border)] overflow-hidden text-xs" role="group" aria-label="Language">
          <button type="button" class="px-3 py-1.5" :class="lang === 'en' ? 'bg-[var(--brass)] text-white' : ''" :aria-pressed="lang === 'en'" @click="lang = 'en'">English</button>
          <button type="button" class="px-3 py-1.5" :class="lang === 'km' ? 'bg-[var(--brass)] text-white' : ''" :aria-pressed="lang === 'km'" @click="lang = 'km'">ខ្មែរ</button>
        </div>
      </div>
      <div v-if="doc.isPending.value" class="skeleton h-64 w-full" role="status" />
      <Notice v-else-if="doc.error.value" :message="String(doc.error.value)" />
      <article v-else-if="doc.data.value" class="card p-6 sm:p-8">
        <div class="legal-body text-sm sm:text-base leading-relaxed" :lang="doc.data.value.language" v-html="html" />
        <p class="mt-6 pt-4 border-t border-[var(--line)] text-xs text-[var(--muted)]">
          Version {{ doc.data.value.version }}<template v-if="doc.data.value.effective_at"> · effective {{ doc.data.value.effective_at.slice(0, 10) }}</template>
        </p>
      </article>
    </div>
  </SiteLayout>
</template>

<style scoped>
.legal-body :deep(h2) { font-size: 1.6rem; margin-bottom: 1rem; font-family: var(--font-serif, serif); }
.legal-body :deep(p) { margin: 0.75rem 0; }
.legal-body :deep(ul), .legal-body :deep(ol) { margin: 0.75rem 0 0.75rem 1.25rem; list-style: revert; }
.legal-body :deep(li) { margin: 0.35rem 0; }
.legal-body :deep(blockquote) { border-left: 3px solid var(--brass); padding: 0.25rem 0.75rem; color: var(--muted); font-size: 0.85rem; }
</style>
