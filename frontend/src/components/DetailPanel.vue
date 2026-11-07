<script setup lang="ts">
defineProps<{ open: boolean; label: string }>()
defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <Transition name="panel">
    <aside v-if="open" class="detail" role="complementary" :aria-label="label">
      <button type="button" class="detail__close" aria-label="Close details" @click="$emit('close')">
        <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3l10 10M13 3L3 13"/></svg>
      </button>
      <slot />
    </aside>
  </Transition>
</template>

<style scoped>
.detail { position: fixed; inset: 0; z-index: 40; overflow-y: auto; background: var(--paper); padding: 1rem; box-shadow: var(--shadow-float); }
.detail__close { position: absolute; top: .75rem; right: .75rem; z-index: 2; width: 44px; height: 44px; display: grid; place-items: center; border-radius: var(--radius-pill); background: var(--paper); color: var(--river); border: 1px solid var(--rule); }
.panel-enter-active, .panel-leave-active { transition: transform var(--duration-normal) var(--ease-out), opacity var(--duration-normal) ease; }
.panel-enter-from, .panel-leave-to { transform: translateX(24px); opacity: 0; }
@media (min-width: 1100px) {
  .detail { position: sticky; top: 1rem; inset: auto; max-height: calc(100vh - 2rem); width: 400px; border-radius: var(--radius-panel); box-shadow: none; border: 1px solid var(--rule); }
}
@media (prefers-reduced-motion: reduce) { .panel-enter-active, .panel-leave-active { transition: none; } }
</style>
