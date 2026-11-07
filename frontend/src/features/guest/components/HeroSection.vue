<script setup lang="ts">
import { responsiveSrcset } from '../../../utils/responsiveImage'
import AvailabilitySearch from './AvailabilitySearch.vue'
</script>

<template>
  <section class="hero" aria-labelledby="hero-heading">
    <div class="hero-words">
      <h1 id="hero-heading" class="hero-title">Rest by the river in Phnom Penh</h1>
      <p class="hero-km" lang="km">សម្រាកក្បែរមាត់ទន្លេ នៅភ្នំពេញ</p>
      <div class="hero-ask">
        <AvailabilitySearch sentence :navigate-on-submit="true" />
      </div>
      <p class="hero-note">You see the full price, with tax, before you pay. Check-in from 14:00.</p>
    </div>
    <figure class="hero-photo">
      <img
        src="/images/luma-haven/rooms/riverfront-suite/main.jpg"
        :srcset="responsiveSrcset('/images/luma-haven/rooms/riverfront-suite/main.jpg')"
        sizes="(min-width: 1000px) 55vw, 100vw"
        alt="Riverfront Suite with a king bed, a curved sofa and floor-to-ceiling windows over the river"
        width="1290"
        height="860"
        loading="eager"
        fetchpriority="high"
      />
      <figcaption>Riverfront Suite, facing the water</figcaption>
    </figure>
  </section>
</template>

<style scoped>
.hero { display: grid; gap: 2rem; padding: 2.5rem 0 3.5rem; }
.hero-title {
  font-size: clamp(3.0625rem, 7.4vw, 6.375rem);
  line-height: .92;
  letter-spacing: -.02em;
  color: var(--river);
  max-width: 12ch;
  text-wrap: balance;
}
.hero-km { margin-top: 1rem; font: 400 1.25rem/1.5 'Kantumruy Pro', sans-serif; color: var(--silt); }
.hero-ask { margin-top: 2.25rem; }
.hero-note { margin-top: 1.25rem; font-size: .875rem; color: var(--silt); }
.hero-photo { margin: 0; }
.hero-photo img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; display: block; border-radius: var(--radius-photo); background: var(--sunk); }
.hero-photo figcaption { margin-top: .6rem; font-size: .8125rem; color: var(--silt); }

/* Desktop: words on the left, the photo runs off the right edge of the window. */
@media (min-width: 1000px) {
  .hero { grid-template-columns: minmax(0, 6fr) minmax(0, 5fr); gap: 4rem; align-items: end; padding: 4rem 0 5rem; }
  /* Distance from the content edge to the window edge (main is max-w-6xl with 1.25rem padding). */
  .hero-photo { margin-right: calc(-1 * ((100vw - min(100vw, 72rem)) / 2 + 1.25rem)); }
  .hero-photo img { aspect-ratio: 4 / 5; max-height: 78vh; border-radius: var(--radius-photo) 0 0 var(--radius-photo); object-position: 30% center; }
}

/* The one orchestrated moment: the photo un-crops and the title settles, once. */
@media (prefers-reduced-motion: no-preference) {
  .hero-photo img { animation: uncrop 900ms var(--ease-out) both; }
  .hero-title { animation: settle 700ms var(--ease-out) both; }
}
@keyframes uncrop { from { clip-path: inset(6%); } to { clip-path: inset(0); } }
@keyframes settle { from { letter-spacing: 0; opacity: 0; } to { letter-spacing: -.02em; opacity: 1; } }
</style>
