<script setup lang="ts">
defineProps<{ selected?: boolean; title: string }>()
defineEmits<{ (e: 'select'): void }>()
</script>

<template>
  <article class="stay" :class="{ 'stay--selected': selected }">
    <div class="stay__photo"><slot name="photo" /><div class="stay__more"><slot name="more" /></div></div>
    <div class="stay__body">
      <h3 class="stay__title">{{ title }}</h3>
      <div class="stay__facts"><slot name="facts" /></div>
      <div class="stay__note"><slot /></div>
    </div>
    <div class="stay__price">
      <slot name="price" />
      <slot name="action" />
    </div>
  </article>
</template>

<style scoped>
.stay { display: grid; grid-template-columns: 1fr; background: var(--paper); border-radius: var(--radius-panel); border: 2px solid transparent; overflow: hidden; }
.stay--selected { border-color: var(--river); }
.stay__photo { position: relative; aspect-ratio: 4 / 3; border-radius: var(--radius-photo); overflow: hidden; margin: .75rem; }
.stay__more { position: absolute; left: .75rem; bottom: .75rem; }
.stay__body { padding: .25rem 1.25rem 1rem; display: grid; gap: .6rem; align-content: start; }
.stay__title { font-size: 1.9375rem; color: var(--river); }
.stay__facts { display: flex; flex-wrap: wrap; gap: .5rem; }
.stay__note { color: var(--silt); font-size: .875rem; }
.stay__price { display: grid; gap: .75rem; padding: 1rem 1.25rem; border-top: 1px solid var(--rule); align-content: center; }
@media (min-width: 720px) {
  .stay { grid-template-columns: 260px 1fr 190px; }
  .stay__photo { margin: .75rem 0 .75rem .75rem; aspect-ratio: auto; min-height: 190px; }
  .stay__body { padding: 1rem 1.25rem; }
  .stay__price { border-top: 0; border-left: 1px solid var(--rule); margin: 1rem 0; }
}
</style>
