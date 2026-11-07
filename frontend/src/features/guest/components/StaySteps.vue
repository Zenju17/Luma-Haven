<script setup lang="ts">
const steps = [
  { title: 'Book online', description: 'Choose your dates and room. The server quotes the exact room rate and tax before you commit.' },
  { title: 'Verify your booking', description: 'Open My stay and enter the six-digit code we email you to see your reservation.' },
  { title: 'Arrive and collect your key', description: 'Reception opens for check-in from 14:00 and hands you your room key.' },
  { title: 'Stay and check out', description: 'Send service requests from My stay. Check-out is by 12:00 on your last day.' },
]
</script>

<template>
  <section class="py-16 sm:py-20 border-t border-[var(--rule)]" aria-labelledby="steps-heading">
    <h2 id="steps-heading" class="steps-h">How your stay works</h2>
    <ol class="steps">
      <li v-for="(step, index) in steps" :key="step.title">
        <span class="steps-n">{{ index + 1 }}</span>
        <h3>{{ step.title }}</h3>
        <p>{{ step.description }}</p>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.steps-h { font-size: 2.4375rem; color: var(--river); margin-bottom: 1.5rem; }
.steps { display: grid; gap: 1.5rem; }
.steps li { display: grid; gap: .35rem; padding-top: 1rem; border-top: 2px solid var(--river); }
.steps-n { font: 400 1.5625rem/1 var(--font-display); color: var(--laterite); }
.steps h3 { font-size: 1.5625rem; color: var(--river); }
.steps p { color: var(--silt); font-size: .9375rem; }
@media (min-width: 900px) { .steps { grid-template-columns: repeat(4, 1fr); gap: 2rem; } }
</style>
