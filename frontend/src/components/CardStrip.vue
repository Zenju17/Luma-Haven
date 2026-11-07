<script setup lang="ts">
defineProps<{ items: { id: string | number; title: string; price?: string }[]; selectedId?: string | number | null; label: string }>()
defineEmits<{ (e: 'select', id: string | number): void }>()
</script>

<template>
  <div class="strip" role="list" :aria-label="label">
    <button v-for="it in items" :key="it.id" type="button" role="listitem" class="strip__card" :class="{ 'strip__card--on': it.id === selectedId }" :aria-current="it.id === selectedId" @click="$emit('select', it.id)">
      <span class="strip__photo"><slot name="photo" :item="it" /></span>
      <span class="strip__title">{{ it.title }}</span>
      <span v-if="it.price" class="strip__price">{{ it.price }}</span>
    </button>
  </div>
</template>

<style scoped>
.strip { display: flex; gap: .75rem; overflow-x: auto; scroll-snap-type: x mandatory; padding: 4px; }
.strip__card { flex: 0 0 140px; scroll-snap-align: start; display: grid; gap: .3rem; text-align: left; padding: .5rem; border-radius: var(--radius-photo); border: 2px solid transparent; background: var(--paper); color: var(--river); font: 500 .875rem var(--font-text); }
.strip__card--on { border-color: var(--river); }
.strip__photo { display: block; aspect-ratio: 4 / 3; border-radius: 10px; overflow: hidden; background: var(--sunk); }
.strip__price { color: var(--laterite); font-weight: 600; font-variant-numeric: tabular-nums; }
</style>
