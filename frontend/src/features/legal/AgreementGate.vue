<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import Notice from '../../components/Notice.vue'
import { api } from '../../services/api'
import { renderMarkdown } from '../../utils/markdown'
import type { LegalDoc } from '../../types'

const props = defineProps<{ portal: 'staff' | 'admin'; active: boolean }>()
interface Me { pending_agreements?: { id: number }[] }

const client = useQueryClient()
const me = useQuery({
  queryKey: computed(() => ['agreement', props.portal]),
  queryFn: () => api<Me>('/auth/me', undefined, props.portal),
  enabled: computed(() => props.active),
})
const pendingId = computed(() => me.data.value?.pending_agreements?.[0]?.id)
const doc = useQuery({
  queryKey: computed(() => ['agreement-doc', props.portal]),
  queryFn: () => api<LegalDoc>('/legal/documents/staff_agreement'),
  enabled: computed(() => Boolean(pendingId.value)),
})
const checked = ref(false)
const busy = ref(false)
const error = ref('')

async function accept() {
  if (!pendingId.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await api('/auth/accept-agreement', { consent_document_ids: [doc.data.value?.id ?? pendingId.value] }, props.portal)
    checked.value = false
    await client.invalidateQueries({ queryKey: ['agreement', props.portal] })
  } catch (caught) {
    error.value = String(caught)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="pendingId && doc.data.value" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" role="dialog" aria-modal="true" aria-label="Staff agreement">
    <div class="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-[var(--paper)]">
      <div class="text-sm leading-relaxed space-y-2" v-html="renderMarkdown(doc.data.value.body_markdown)" />
      <label class="flex items-start gap-3 mt-5 text-sm">
        <input v-model="checked" type="checkbox" class="mt-1 h-4 w-4" />
        <span>I have read and agree to this agreement.</span>
      </label>
      <Notice :message="error" class="mt-3" />
      <button class="btn mt-4" :disabled="!checked || busy" @click="accept">Accept and continue</button>
    </div>
  </div>
</template>
