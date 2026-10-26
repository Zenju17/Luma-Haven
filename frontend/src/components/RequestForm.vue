<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../lib/api'
import Notice from './Notice.vue'

const props = defineProps<{ id: string }>()
const emit = defineEmits<{ done: [] }>()

const type = ref('Towels')
const description = ref('')
const error = ref('')

async function submit() {
  try {
    await api(`/reservations/${props.id}/service-requests`, {
      type: type.value,
      description: description.value,
    })
    description.value = ''
    error.value = ''
    emit('done')
  } catch (e) {
    error.value = String(e)
  }
}
</script>

<template>
  <form class="flex flex-col gap-3 mt-4" @submit.prevent="submit">
    <select v-model="type" class="field">
      <option>Towels</option>
      <option>Cleaning</option>
      <option>Maintenance</option>
      <option>Reception</option>
    </select>
    <input
      v-model="description"
      class="field"
      placeholder="How can we help?"
      required
    />
    <button class="btn-secondary">Send request</button>
    <Notice :error="error" />
  </form>
</template>
