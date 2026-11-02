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
  }>(),
  {
    initialArrival: '',
    initialDeparture: '',
    initialOccupants: 2,
    navigateOnSubmit: true,
    compact: false,
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
    <div
      :class="[
        'card p-6 sm:p-8 border border-[var(--glass-border)] shadow-xl bg-[var(--surface-raised)] backdrop-blur-md rounded-2xl',
        compact ? 'p-4 sm:p-5' : '',
      ]"
    >
      <div v-if="!compact" class="mb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--line)] pb-4">
        <div>
          <h2 class="text-xl sm:text-2xl font-semibold text-[var(--brand-text)] serif">
            When are you staying?
          </h2>
          <p class="text-xs sm:text-sm text-[var(--muted)]">
            Pick your dates and we'll show every room that is free, with the full price.
          </p>
        </div>
      </div>

      <form class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end" @submit.prevent="handleSubmit">
        <!-- Arrival Field -->
        <div>
          <label for="arrival-input" class="label block text-xs font-semibold text-[var(--muted)] mb-1.5 uppercase tracking-wider">
            Arrival
          </label>
          <input
            id="arrival-input"
            v-model="arrival"
            aria-label="Arrival"
            class="field w-full cursor-pointer font-medium text-sm sm:text-base"
            type="date"
            :min="hotelToday()"
            required
            @change="handleArrivalChange"
          />
        </div>

        <!-- Departure Field -->
        <div>
          <label for="departure-input" class="label block text-xs font-semibold text-[var(--muted)] mb-1.5 uppercase tracking-wider">
            Departure
          </label>
          <input
            id="departure-input"
            v-model="departure"
            aria-label="Departure"
            class="field w-full cursor-pointer font-medium text-sm sm:text-base"
            type="date"
            :min="arrival ? followingDay(arrival) : followingDay(hotelToday())"
            required
          />
        </div>

        <!-- Guests Field -->
        <div>
          <label for="guests-input" class="label block text-xs font-semibold text-[var(--muted)] mb-1.5 uppercase tracking-wider">
            Guests
          </label>
          <input
            id="guests-input"
            v-model.number="occupants"
            aria-label="Guests"
            class="field w-full font-medium text-sm sm:text-base"
            type="number"
            min="1"
            max="8"
            required
          />
        </div>

        <!-- Search Action Button -->
        <div>
          <button
            type="submit"
            class="btn w-full h-[46px] flex items-center justify-center gap-2 font-semibold text-base shadow-md hover:shadow-lg transition-all"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Search rooms
          </button>
        </div>
      </form>

      <Notice v-if="error" :message="error" class="mt-4" />
    </div>
  </div>
</template>
