<script setup lang="ts">
import { responsiveSrcset } from '../../../utils/responsiveImage'

// Only images without text baked into them. The gallery and facility files carry
// poster captions, so the pool and restaurant use copies cropped above the text.
const pool = '/images/luma-haven/clean/pool.jpg'
const dining = '/images/luma-haven/clean/dining.jpg'
const lounge = '/images/luma-haven/facilities/lounge.jpg'
</script>

<template>
  <section class="house" aria-labelledby="house-heading">
    <div class="house-head">
      <h2 id="house-heading">Beyond your room</h2>
      <p>A pool on the roof, a restaurant in the courtyard and a lounge for slow afternoons.</p>
    </div>
    <div class="house-grid">
      <figure class="house-big">
        <img :src="pool" :srcset="responsiveSrcset(pool)" sizes="(min-width: 900px) 62vw, 100vw" alt="Rooftop pool at dusk, lined with loungers and potted palms, the city behind" width="1600" height="696" loading="lazy" />
        <figcaption>Rooftop pool, level 4</figcaption>
      </figure>
      <figure>
        <img :src="dining" :srcset="responsiveSrcset(dining)" sizes="(min-width: 900px) 34vw, 100vw" alt="Courtyard restaurant with glass pendant lamps, wooden tables and plants" width="1600" height="583" loading="lazy" />
        <figcaption>Courtyard restaurant</figcaption>
      </figure>
      <figure>
        <img :src="lounge" :srcset="responsiveSrcset(lounge)" sizes="(min-width: 900px) 34vw, 100vw" alt="Guest lounge with armchairs around low tables under a high ceiling" width="2400" height="1603" loading="lazy" />
        <figcaption>Guest lounge</figcaption>
      </figure>
    </div>
    <p class="house-honest">These are design visualisations of the hotel. Photographs will replace them once the spaces are finished.</p>
    <RouterLink to="/gallery" class="house-link">See the full gallery</RouterLink>
  </section>
</template>

<style scoped>
.house { margin-bottom: 1rem; padding: clamp(1.25rem, 3vw, 2.5rem); background: var(--paper); border-radius: var(--radius-panel); }
.house-head { display: grid; gap: .5rem; margin-bottom: 2rem; }
.house-head h2 { font-size: clamp(2rem, 4vw, 3rem); color: var(--ink); }
.house-head p { color: var(--silt); }
.house-grid { display: grid; gap: 1.25rem; }
.house-grid figure { margin: 0; }
.house-grid img { width: 100%; aspect-ratio: 3 / 2; object-fit: cover; display: block; border-radius: var(--radius-photo); background: var(--sunk); }
.house-grid figcaption { margin-top: .5rem; font-size: .875rem; color: var(--silt); }
.house-honest { margin-top: 1.5rem; font-size: .8125rem; color: var(--silt); }
.house-link { display: inline-flex; align-items: center; min-height: 44px; margin-top: .5rem; color: var(--river); font-weight: 600; text-decoration: underline; }

@media (min-width: 900px) {
  .house-grid { grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); grid-template-rows: auto auto; }
  .house-big { grid-row: span 2; }
  .house-big img { aspect-ratio: auto; height: calc(100% - 1.75rem); min-height: 28rem; }
}
</style>
