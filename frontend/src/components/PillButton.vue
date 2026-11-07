<script setup lang="ts">
withDefaults(defineProps<{ variant?: 'primary' | 'outline' | 'quiet'; type?: 'button' | 'submit'; disabled?: boolean }>(), {
  variant: 'primary',
  type: 'button',
})
</script>

<template>
  <button :type="type" :disabled="disabled" class="pill-btn" :class="`pill-btn--${variant}`"><slot /></button>
</template>

<style scoped>
.pill-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: .5rem;
  min-height: 44px; padding: 0 1.4rem; border-radius: var(--radius-pill);
  font: 600 .9375rem/1 var(--font-text); border: 1.5px solid transparent;
  transition: background-color var(--duration-fast) ease, border-color var(--duration-fast) ease;
}
.pill-btn--primary { background: var(--river); color: var(--on-river); }
.pill-btn--primary:hover:not(:disabled) { background: var(--river-hover); }
.pill-btn--outline { background: transparent; color: var(--river); border-color: var(--river); }
.pill-btn--outline:hover:not(:disabled) { background: var(--sunk); }
.pill-btn--quiet { background: transparent; color: var(--river); }
.pill-btn--quiet:hover:not(:disabled) { background: var(--sunk); }
</style>
