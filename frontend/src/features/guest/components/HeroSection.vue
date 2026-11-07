<script setup lang="ts">
import { responsiveSrcset } from '../../../utils/responsiveImage'
import AvailabilitySearch from './AvailabilitySearch.vue'

const picks = [
  { name: 'City King', note: 'Sleeps 2, 1 king bed', src: '/images/luma-haven/rooms/city-king/main.jpg', alt: 'King bed with a blue throw beside full-height sheer curtains' },
  { name: 'Garden King', note: 'Sleeps 2, faces the courtyard', src: '/images/luma-haven/rooms/garden-king/main.jpg', alt: 'King bed beside floor-to-ceiling windows onto green trees' },
]
const wide = '/images/luma-haven/rooms/riverfront-suite/main.jpg'
const family = '/images/luma-haven/rooms/family-suite/main.jpg'
</script>

<template>
  <section class="hero" aria-labelledby="hero-heading">
    <div class="hero-panel">
      <div class="hero-words">
        <p class="hero-place">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z" fill="none" stroke="currentColor" stroke-width="1.8" /><circle cx="12" cy="9.5" r="2.4" fill="currentColor" /></svg>
          Daun Penh, Phnom Penh
        </p>
        <h1 id="hero-heading" class="hero-title">Rest by the river in Phnom Penh</h1>
        <p class="hero-copy">Ten room types a short walk from the riverside. See the full price, with tax, before you pay, then collect your key at reception from 14:00.</p>
        <div class="hero-search"><AvailabilitySearch sentence :navigate-on-submit="true" /></div>
        <p class="hero-pay">Pay by KHQR with Bakong, ABA, ACLEDA or Wing.</p>
      </div>
      <div class="hero-photo">
        <img
          :src="wide"
          :srcset="responsiveSrcset(wide)"
          sizes="(min-width: 1000px) 50vw, 100vw"
          alt="Riverfront Suite with a king bed, a curved sofa and floor-to-ceiling windows over the river"
          width="1290"
          height="860"
          loading="eager"
          fetchpriority="high"
        />
      </div>
    </div>

    <div class="picks">
      <RouterLink v-for="pick in picks" :key="pick.name" :to="{ path: '/rooms', query: { type: pick.name } }" class="pick">
        <img :src="pick.src" :srcset="responsiveSrcset(pick.src)" sizes="(min-width: 1000px) 25vw, 100vw" :alt="pick.alt" width="800" height="600" loading="lazy" />
        <span class="pick-name">{{ pick.name }}</span>
        <span class="pick-note">{{ pick.note }}</span>
      </RouterLink>
      <RouterLink to="/rooms" class="pick-wide">
        <span class="pick-wide-text">
          <span class="pick-wide-title">Rooms for couples, friends and families</span>
          <span class="pick-wide-link">See all rooms</span>
        </span>
        <img :src="family" :srcset="responsiveSrcset(family)" sizes="(min-width: 1000px) 20vw, 50vw" alt="Family Suite with a king bed and a single bed" width="800" height="600" loading="lazy" />
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.hero { padding: 1.25rem 0 3rem; display: grid; gap: 1rem; }
.hero-panel { display: grid; gap: 1.5rem; padding: 1rem; background: var(--paper); border-radius: var(--radius-panel); }
.hero-words { display: grid; align-content: center; justify-items: start; padding: .75rem .5rem; }
.hero-place { display: inline-flex; align-items: center; gap: .4rem; padding: .45rem .85rem; border-radius: var(--radius-pill); background: var(--palm-leaf); font-size: .8125rem; font-weight: 600; color: var(--ink); }
.hero-title { margin-top: 1.25rem; font-size: clamp(2.6rem, 5.4vw, 4.4rem); line-height: 1.02; color: var(--ink); max-width: 13ch; text-wrap: balance; }
.hero-copy { margin-top: 1rem; color: var(--silt); max-width: 44ch; }
.hero-search { margin-top: 1.75rem; width: 100%; }
.hero-pay { margin-top: 1rem; font-size: .8125rem; color: var(--silt); }
.hero-photo { border-radius: calc(var(--radius-panel) - 6px); overflow: hidden; background: var(--sunk); }
.hero-photo img { width: 100%; height: 100%; aspect-ratio: 4 / 3; object-fit: cover; display: block; }

.picks { display: grid; gap: 1rem; }
.pick { display: grid; gap: .25rem; color: var(--ink); text-decoration: none; }
.pick img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: var(--radius-photo); background: var(--sunk); margin-bottom: .5rem; }
.pick-name { font-weight: 600; }
.pick-note { font-size: .8125rem; color: var(--silt); }
.pick:hover .pick-name, .pick-wide:hover .pick-wide-link { text-decoration: underline; text-underline-offset: 4px; }
.pick-wide { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1rem; padding: 1rem; background: var(--paper); border-radius: var(--radius-panel); color: var(--ink); text-decoration: none; }
.pick-wide-text { display: flex; flex-direction: column; justify-content: space-between; gap: 1rem; padding: .25rem; }
.pick-wide-title { font-size: 1.25rem; font-weight: 600; letter-spacing: -.015em; line-height: 1.25; }
.pick-wide-link { font-size: .875rem; font-weight: 600; color: var(--river); }
.pick-wide img { width: 100%; height: 100%; min-height: 9rem; object-fit: cover; border-radius: var(--radius-photo); }

@media (min-width: 1000px) {
  .hero-panel { grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr); gap: 2.5rem; padding: 1.25rem; min-height: 560px; }
  .hero-words { padding: 1.5rem 0 1.5rem 1.75rem; }
  .hero-photo img { aspect-ratio: auto; }
  .picks { grid-template-columns: 1fr 1fr 2fr; }
}

/* The one orchestrated moment: the photo un-crops once on load. */
@media (prefers-reduced-motion: no-preference) {
  .hero-photo img { animation: uncrop 900ms var(--ease-out) both; }
}
@keyframes uncrop { from { clip-path: inset(5%); } to { clip-path: inset(0); } }
</style>
