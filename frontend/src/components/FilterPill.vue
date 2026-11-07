<script setup lang="ts">
defineProps<{ active?: boolean }>()
defineEmits<{ (e: 'click'): void; (e: 'remove'): void }>()
</script>

<template>
  <span class="filter-pill" :class="{ 'filter-pill--active': active }">
    <button type="button" class="filter-pill__main" :aria-pressed="!!active" @click="$emit('click')"><slot /></button>
    <button v-if="active" type="button" class="filter-pill__x" aria-label="Remove filter" @click="$emit('remove')">
      <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3l10 10M13 3L3 13"/></svg>
    </button>
  </span>
</template>

<style scoped>
.filter-pill {
  display: inline-flex; align-items: center; min-height: 44px; border-radius: var(--radius-pill);
  border: 1.5px solid var(--rule); color: var(--river); background: transparent; font: 500 .875rem/1 var(--font-text);
}
.filter-pill--active { background: var(--river); border-color: var(--river); color: var(--palm-leaf); }
.filter-pill__main { padding: 0 1rem; min-height: 44px; border-radius: inherit; color: inherit; font: inherit; }
.filter-pill--active .filter-pill__main { padding-right: .4rem; }
.filter-pill__x { display: grid; place-items: center; width: 36px; min-height: 44px; margin-right: .25rem; color: inherit; }
</style>
