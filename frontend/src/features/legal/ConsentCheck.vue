<script setup lang="ts">
import { computed, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../services/api'
import { useLanguage } from '../../composables/useLanguage'
import type { LegalDocSummary } from '../../types'

const REQUIRED = ['TERMS', 'PRIVACY', 'CANCELLATION']
const accepted = defineModel<boolean>('accepted', { default: false })
const ids = defineModel<number[]>('documentIds', { default: () => [] })
const { lang } = useLanguage()

const docs = useQuery({
  queryKey: computed(() => ['legal-list', lang.value]),
  queryFn: () => api<LegalDocSummary[]>(`/legal/documents?lang=${lang.value}`),
})
const required = computed(() => (docs.data.value ?? []).filter(d => REQUIRED.includes(d.kind)))
// Nothing published to accept: the server does not require consent, so do not block booking.
const nothingToAccept = computed(() => docs.isSuccess.value && required.value.length === 0)
watch(nothingToAccept, none => { if (none) accepted.value = true }, { immediate: true })
watch([required, accepted], () => { ids.value = accepted.value ? required.value.map(d => d.id) : [] }, { immediate: true })
watch(lang, () => { accepted.value = false })
const label: Record<string, string> = { TERMS: 'Terms and Conditions', PRIVACY: 'Privacy Policy', CANCELLATION: 'Cancellation Policy' }
</script>

<template>
  <p v-if="docs.isError.value" class="mt-5 text-sm notice-error" role="alert">
    We could not load the booking terms.
    <button type="button" class="underline font-semibold" @click="docs.refetch()">Try again</button>
  </p>
  <p v-else-if="docs.isPending.value" class="mt-5 text-sm text-[var(--muted)]" role="status">Loading booking terms…</p>
  <label v-else-if="!nothingToAccept" class="flex items-start gap-3 mt-5 text-sm text-[var(--muted)] normal-case tracking-normal font-normal">
    <input v-model="accepted" type="checkbox" class="mt-1 h-4 w-4" :disabled="!required.length" />
    <span>
      I have read and accept the
      <template v-for="(doc, index) in required" :key="doc.id">
        <a :href="`/legal/${doc.kind.toLowerCase()}`" target="_blank" rel="noopener" class="underline text-[var(--brass)]">{{ label[doc.kind] ?? doc.title }}</a><template v-if="index < required.length - 2">, </template><template v-else-if="index === required.length - 2"> and </template>
      </template>.
      <span class="inline-flex gap-1 ml-1 text-xs">
        <button type="button" class="underline" @click.prevent="lang = 'en'">EN</button>/<button type="button" class="underline" @click.prevent="lang = 'km'">ខ្មែរ</button>
      </span>
    </span>
  </label>
</template>
