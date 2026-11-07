<script setup lang="ts">
defineProps<{ overlay?: boolean }>()
</script>

<template>
  <span class="fact" :class="{ 'fact--overlay': overlay }"><slot name="icon" /><span><slot /></span></span>
</template>

<style scoped>
.fact { display: inline-flex; align-items: center; gap: .4rem; padding: .35rem .8rem; border-radius: var(--radius-pill); border: 1px solid var(--rule); color: var(--river); font: 500 .875rem/1.2 var(--font-text); }
.fact--overlay { background: var(--paper); border-color: transparent; }
.fact :deep(svg) { width: 16px; height: 16px; }
</style>
