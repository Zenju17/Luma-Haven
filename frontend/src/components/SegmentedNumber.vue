<script setup lang="ts">
const props = defineProps<{ modelValue: number | null; options: number[]; label: string; plusFrom?: number }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: number | null): void }>()
function text(n: number) { return props.plusFrom && n >= props.plusFrom ? `${n}+` : String(n) }
function pick(n: number) { emit('update:modelValue', props.modelValue === n ? null : n) }
</script>

<template>
  <div class="seg" role="group" :aria-label="label">
    <button v-for="n in options" :key="n" type="button" class="seg__btn" :class="{ 'seg__btn--on': modelValue === n }" :aria-pressed="modelValue === n" @click="pick(n)">{{ text(n) }}</button>
  </div>
</template>

<style scoped>
.seg { display: inline-flex; border: 1.5px solid var(--rule); border-radius: var(--radius-pill); overflow: hidden; }
.seg__btn { min-width: 44px; min-height: 44px; padding: 0 .75rem; color: var(--river); font: 500 .9375rem var(--font-text); font-variant-numeric: tabular-nums; }
.seg__btn + .seg__btn { border-left: 1px solid var(--rule); }
.seg__btn--on { background: var(--river); color: var(--palm-leaf); }
</style>
