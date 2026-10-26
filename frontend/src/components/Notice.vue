<script setup lang="ts">
defineProps<{ error: string }>()
</script>

<template>
  <div
    v-if="error"
    role="alert"
    class="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 my-4"
  >
    {{ error }}
  </div>
</template>
