<script setup lang="ts">
import { ref } from 'vue'
import Notice from '../../../components/Notice.vue'
import { api } from '../../../services/api'
import type { DataRequestResult } from '../../../types'

const props = defineProps<{ bookingId: string | number; verified: boolean }>()
const message = ref('')
const ok = ref(true)
const busy = ref(false)
const confirmDelete = ref(false)

async function run(action: () => Promise<string>) {
  if (busy.value) return
  busy.value = true
  message.value = ''
  try {
    message.value = await action()
    ok.value = true
  } catch (caught) {
    ok.value = false
    message.value = String(caught)
  } finally {
    busy.value = false
  }
}

const download = () => run(async () => {
  const data = await api<unknown>(`/reservations/${props.bookingId}/data-export`)
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'my-luma-haven-data.json'
  link.click()
  // Revoking immediately can cancel the download in Firefox/Safari.
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
  return 'Your data export has been downloaded.'
})

const request = (type: 'RECTIFY' | 'DELETE') => run(async () => {
  const result = await api<DataRequestResult>(`/reservations/${props.bookingId}/data-requests`, { type })
  confirmDelete.value = false
  return `Request received. The hotel will respond by ${result.due_at.slice(0, 10)}.`
})
</script>

<template>
  <section class="card p-6 mt-5" aria-labelledby="my-data-title">
    <h2 id="my-data-title" class="text-2xl">My data</h2>
    <p class="text-sm text-[var(--muted)] mt-2">
      You can download a copy of your personal data, ask us to correct it, or ask us to delete it.
      Accounting records we must keep by law are retained in anonymised form.
      <RouterLink class="underline text-[var(--brass)]" to="/legal/privacy">Privacy Policy</RouterLink>
    </p>
    <p v-if="!verified" class="text-sm mt-3">Verify your booking with the emailed code to use these options.</p>
    <div v-else class="flex flex-wrap gap-3 mt-4">
      <button class="btn-secondary" :disabled="busy" @click="download">Download my data</button>
      <button class="btn-secondary" :disabled="busy" @click="request('RECTIFY')">Request a correction</button>
      <button v-if="!confirmDelete" class="btn-secondary" :disabled="busy" @click="confirmDelete = true">Request deletion</button>
      <template v-else>
        <button class="btn" :disabled="busy" @click="request('DELETE')">Confirm deletion request</button>
        <button class="btn-secondary" :disabled="busy" @click="confirmDelete = false">Cancel</button>
      </template>
    </div>
    <Notice :message="message" :status="ok" class="mt-3" />
  </section>
</template>
