<script setup lang="ts">
defineProps<{ message: string; status?: boolean }>()
</script>

<template>
  <Transition name="slide-down">
    <p v-if="message" :role="status ? 'status' : 'alert'" :class="status ? 'notice-success' : 'notice-error'">{{ message }}</p>
  </Transition>
</template>
