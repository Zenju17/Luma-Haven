<script setup lang="ts">
import { computed, ref } from 'vue'

// Dates are ISO yyyy-mm-dd strings. Booked nights are half-open [arrival, departure).
const props = defineProps<{
  booked?: { arrival: string; departure: string }[]
  selected?: { arrival: string; departure: string } | null
  month?: string // yyyy-mm
}>()
defineEmits<{ (e: 'pick', iso: string): void }>()

const today = new Date()
const cursor = ref(props.month ?? `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`)
const year = computed(() => Number(cursor.value.slice(0, 4)))
const mon = computed(() => Number(cursor.value.slice(5, 7)) - 1)
const title = computed(() => new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(new Date(year.value, mon.value, 1)))
const weekdays = computed(() => Array.from({ length: 7 }, (_, i) => new Intl.DateTimeFormat(undefined, { weekday: 'narrow' }).format(new Date(2024, 0, 1 + i))))

const iso = (d: number) => `${cursor.value}-${String(d).padStart(2, '0')}`
const cells = computed(() => {
  const lead = (new Date(year.value, mon.value, 1).getDay() + 6) % 7
  const days = new Date(year.value, mon.value + 1, 0).getDate()
  return [...Array(lead).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)] as (number | null)[]
})
function state(d: number) {
  const s = iso(d)
  const sel = props.selected
  if (sel && s === sel.arrival) return 'edge'
  if (sel && s === sel.departure) return 'edge'
  if (sel && s > sel.arrival && s < sel.departure) return 'range'
  for (const b of props.booked ?? []) {
    if (s === b.arrival || s === b.departure) return 'edge'
    if (s > b.arrival && s < b.departure) return 'booked'
  }
  return ''
}
function shift(n: number) {
  const d = new Date(year.value, mon.value + n, 1)
  cursor.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
</script>

<template>
  <div class="cal">
    <div class="cal__head">
      <button type="button" aria-label="Previous month" @click="shift(-1)">‹</button>
      <strong>{{ title }}</strong>
      <button type="button" aria-label="Next month" @click="shift(1)">›</button>
    </div>
    <div class="cal__grid">
      <span v-for="(w, i) in weekdays" :key="i" class="cal__dow">{{ w }}</span>
      <template v-for="(d, i) in cells" :key="i">
        <span v-if="d === null" />
        <button v-else type="button" class="cal__day" :class="`cal__day--${state(d) || 'free'}`" @click="$emit('pick', iso(d))">{{ d }}</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.cal { display: grid; gap: .5rem; color: var(--river); font-family: var(--font-text); }
.cal__head { display: flex; align-items: center; justify-content: space-between; }
.cal__head button { width: 44px; height: 44px; font-size: 1.25rem; color: inherit; }
.cal__grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; text-align: center; }
.cal__dow { font-size: .8rem; color: var(--silt); padding: .25rem 0; }
.cal__day { min-height: 44px; font-variant-numeric: tabular-nums; color: inherit; border-radius: 0; }
.cal__day--booked { background: var(--lotus); }
.cal__day--range { background: var(--lotus); }
.cal__day--edge { background: var(--laterite); color: #fff; border-radius: var(--radius-pill); }
</style>
