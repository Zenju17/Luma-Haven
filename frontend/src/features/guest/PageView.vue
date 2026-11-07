<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import SiteLayout from '../../layouts/SiteLayout.vue'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import { renderMarkdown } from '../../utils/markdown'
import { useLanguage } from '../../composables/useLanguage'

interface CmsPage { slug: string; language: string; title: string; body_markdown: string }
const route = useRoute()
const { lang } = useLanguage()
const slug = computed(() => String(route.params.slug))
const page = useQuery({
  queryKey: computed(() => ['cms-page', slug.value, lang.value]),
  queryFn: () => api<CmsPage>(`/cms/pages/${slug.value}?lang=${lang.value}`),
})
const html = computed(() => renderMarkdown(page.data.value?.body_markdown ?? ''))
</script>

<template>
  <SiteLayout>
    <div class="py-8 sm:py-12 max-w-3xl mx-auto">
      <div v-if="page.isPending.value" class="skeleton h-64 w-full" role="status" />
      <div v-else-if="page.error.value" class="card p-8">
        <h1 class="text-3xl">Page not found</h1>
        <Notice :message="String(page.error.value)" />
        <RouterLink class="btn inline-block mt-4" to="/">Back to the hotel</RouterLink>
      </div>
      <article v-else-if="page.data.value" class="card p-6 sm:p-8">
        <h1 class="serif text-3xl sm:text-4xl mb-4">{{ page.data.value.title }}</h1>
        <div class="cms-body text-sm sm:text-base leading-relaxed" :lang="page.data.value.language" v-html="html" />
      </article>
    </div>
  </SiteLayout>
</template>

<style scoped>
.cms-body :deep(h2), .cms-body :deep(h3), .cms-body :deep(h4) { font-family: var(--font-display); margin: 1.25rem 0 0.5rem; }
.cms-body :deep(p) { margin: 0.75rem 0; }
.cms-body :deep(ul), .cms-body :deep(ol) { margin: 0.75rem 0 0.75rem 1.25rem; list-style: revert; }
.cms-body :deep(blockquote) { border-left: 3px solid var(--laterite); padding: 0.25rem 0.75rem; color: var(--silt); }
</style>
