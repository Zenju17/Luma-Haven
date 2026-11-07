<script setup lang="ts">
defineProps<{ modelValue: number; min: number; max: number; step?: number; label: string; format?: (n: number) => string }>()
defineEmits<{ (e: 'update:modelValue', v: number): void }>()
</script>

<template>
  <label class="range">
    <span class="range__head"><span>{{ label }}</span><output>{{ format ? format(modelValue) : modelValue }}</output></span>
    <input type="range" :min="min" :max="max" :step="step ?? 1" :value="modelValue" @input="$emit('update:modelValue', Number(($event.target as HTMLInputElement).value))" />
  </label>
</template>

<style scoped>
.range { display: grid; gap: .5rem; color: var(--river); font: 500 .875rem var(--font-text); }
.range__head { display: flex; justify-content: space-between; }
output { color: var(--laterite); font-weight: 600; font-variant-numeric: tabular-nums; }
input { width: 100%; height: 44px; accent-color: var(--laterite); background: transparent; }
</style>
