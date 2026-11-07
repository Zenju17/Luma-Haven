<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Notice from '../../../components/Notice.vue'
import { hotelToday, followingDay } from '../../../services/hotelDates'

const props = withDefaults(
  defineProps<{
    initialArrival?: string
    initialDeparture?: string
    initialOccupants?: number
    navigateOnSubmit?: boolean
    compact?: boolean
    stacked?: boolean
  }>(),
  {
    initialArrival: '',
    initialDeparture: '',
    initialOccupants: 2,
    navigateOnSubmit: true,
    compact: false,
    stacked: false,
  }
)

const emit = defineEmits<{
  (e: 'search', params: { arrival: string; departure: string; occupants: number }): void
}>()

const router = useRouter()
const arrival = ref(props.initialArrival || hotelToday())
const departure = ref(props.initialDeparture || followingDay(arrival.value))
const occupants = ref(props.initialOccupants)
const error = ref('')

watch(() => [props.initialArrival, props.initialDeparture, props.initialOccupants] as const, ([start, end, guests]) => {
  arrival.value = start || hotelToday()
  departure.value = end || followingDay(arrival.value)
  occupants.value = guests
})

function handleArrivalChange() {
  if (arrival.value && departure.value && departure.value <= arrival.value) {
    departure.value = followingDay(arrival.value)
  }
}

function handleSubmit() {
  error.value = ''
  if (!arrival.value || !departure.value) {
    error.value = 'Please select both your arrival and departure dates.'
    return
  }
  if (arrival.value >= departure.value) {
    error.value = 'Choose an arrival date before your departure date.'
    return
  }
  if (arrival.value < hotelToday()) {
    error.value = 'Arrival cannot be before today in Phnom Penh.'
    return
  }
  if (occupants.value < 1 || occupants.value > 8) {
    error.value = 'Guest count must be between 1 and 8.'
    return
  }

  if (props.navigateOnSubmit) {
    router.push({
      path: '/rooms',
      query: {
        arrival: arrival.value,
        departure: departure.value,
        occupants: String(occupants.value),
      },
    })
  } else {
    emit('search', {
      arrival: arrival.value,
      departure: departure.value,
      occupants: Number(occupants.value),
    })
  }
}
</script>

<template>
  <div id="search" class="w-full">
    <form :class="stacked ? 'stack-form' : 'pill-bar'" @submit.prevent="handleSubmit">
      <div class="pf pf--dates">
        <div class="pf-field">
          <label for="arrival-input" class="pf-label">Arrival</label>
          <input id="arrival-input" v-model="arrival" aria-label="Arrival" class="pf-input" type="date" :min="hotelToday()" required @change="handleArrivalChange" />
        </div>
        <span class="pf-to" aria-hidden="true">to</span>
        <div class="pf-field">
          <label for="departure-input" class="pf-label">Departure</label>
          <input id="departure-input" v-model="departure" aria-label="Departure" class="pf-input" type="date" :min="arrival ? followingDay(arrival) : followingDay(hotelToday())" required />
        </div>
      </div>
      <div class="pf-field pf-field--guests">
        <label for="guests-input" class="pf-label">Guests</label>
        <input id="guests-input" v-model.number="occupants" aria-label="Guests" class="pf-input" type="number" min="1" max="8" required />
      </div>
      <button type="submit" class="pf-submit">Search rooms</button>
    </form>
    <Notice v-if="error" :message="error" class="mt-4" />
  </div>
</template>

<style scoped>
.pill-bar, .stack-form { display: grid; gap: .75rem; background: var(--paper); }
.pill-bar { padding: 1rem; border-radius: var(--radius-panel); border: 1px solid var(--rule); box-shadow: var(--shadow-float); }
.pf { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: end; gap: .5rem; }
.stack-form { background: transparent; }
.stack-form .pf { grid-template-columns: 1fr; }
.stack-form .pf-to { display: none; }
@media (max-width: 479px) { .pf { grid-template-columns: 1fr; } .pf-to { display: none; } }
.pf-field { min-width: 0; display: grid; gap: .15rem; padding: .25rem .75rem; }
.stack-form .pf-field { padding: 0; }
.pf-label { color: var(--silt); font-size: .8125rem; font-weight: 500; }
.pf-input { min-width: 0; min-height: 44px; width: 100%; border: 0; border-bottom: 1.5px solid var(--rule); background: transparent; color: var(--river); font: 500 1rem var(--font-text); }
.pf-input:focus-visible { outline-offset: 2px; }
.pf-to { padding-bottom: .75rem; color: var(--silt); }
.pf-submit { min-height: 48px; padding: 0 1.75rem; border-radius: var(--radius-pill); background: var(--river); color: var(--on-river); font: 600 1rem var(--font-text); }
.pf-submit:hover { background: var(--river-hover); }
@media (min-width: 900px) {
  .pill-bar { grid-template-columns: auto 140px auto; align-items: end; justify-content: space-between; border-radius: var(--radius-pill); padding: .6rem .6rem .6rem 1.25rem; }
  .pf-field--guests { border-left: 1px solid var(--rule); padding-left: 1.25rem; }
  .pill-bar .pf-input { border-bottom: 0; }
  .pill-bar .pf-to { padding-bottom: .6rem; }
  .pf { grid-template-columns: 180px auto 180px; }
  .pf-submit { min-height: 52px; }
}
</style>
