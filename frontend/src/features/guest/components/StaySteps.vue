<script setup lang="ts">
// A stay told by the clock. The times are the hotel's real rules (see the footer and Location).
const stops = [
  { when: 'Before', title: 'Book and verify', text: 'Pick dates and a room online. We email a six-digit code so you can open My stay.' },
  { when: '14:00', title: 'Check in', text: 'Reception checks your ID and hands you the room key.' },
  { when: '22:00', title: 'Quiet hours', text: 'Corridors and courtyards stay quiet until 07:00. Ask for anything from My stay.' },
  { when: '12:00', title: 'Check out', text: 'Leave by noon on your last day. Reception can hold your luggage.' },
]
</script>

<template>
  <section class="clock" aria-labelledby="clock-heading">
    <h2 id="clock-heading">Your stay, by the clock</h2>
    <ol class="clock-line">
      <li v-for="stop in stops" :key="stop.title">
        <span class="clock-when">{{ stop.when }}</span>
        <h3>{{ stop.title }}</h3>
        <p>{{ stop.text }}</p>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.clock { margin-bottom: 1rem; padding: clamp(1.25rem, 3vw, 2.5rem); background: var(--paper); border-radius: var(--radius-panel); }
.clock h2 { font-size: clamp(2rem, 4vw, 3rem); color: var(--ink); margin-bottom: 2.5rem; }
.clock-line { display: grid; gap: 2rem; }
.clock-line li { position: relative; display: grid; grid-template-rows: auto auto 1fr; align-content: start; gap: .4rem; padding-left: 1.5rem; border-left: 1px solid var(--river); }
.clock-line li::before { content: ''; position: absolute; left: -5px; top: .9rem; width: 9px; height: 9px; border-radius: 50%; background: var(--laterite); }
.clock-when { display: block; height: 1em; font: 600 clamp(2rem, 3.4vw, 3rem)/1 var(--font-display); color: var(--river); font-variant-numeric: tabular-nums; letter-spacing: -.03em; }
.clock h3 { margin-top: .6rem; font: 600 1.0625rem/1.3 var(--font-text); color: var(--river); }
.clock p { font-size: .9375rem; color: var(--silt); max-width: 34ch; }

/* Desktop: one horizontal line through the day, a dot at each stop. */
@media (min-width: 900px) {
  .clock-line { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 2rem; border-top: 1px solid var(--river); }
  .clock-line li { border-left: 0; padding: 1.75rem 0 0; }
  .clock-line li::before { left: 0; top: -5px; }
}
</style>
