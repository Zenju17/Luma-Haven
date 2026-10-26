<script setup lang="ts">
defineProps<{ message: string; status?: boolean }>()
</script>

<template>
  <p v-if="message" :role="status ? 'status' : 'alert'" :class="status ? 'text-[#175d4b] mt-4' : 'rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 my-4'">{{ message }}</p>
</template>
