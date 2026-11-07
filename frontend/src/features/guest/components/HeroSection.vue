<script setup lang="ts">
import { responsiveSrcset, SIZES } from '../../../utils/responsiveImage'
defineEmits<{ (e: 'focusSearch'): void }>()
</script>

<template>
  <section class="hero" aria-labelledby="hero-heading">
    <h1 id="hero-heading" class="hero-title">Rest by the river in Phnom Penh</h1>
    <p class="hero-copy">A quiet room by the riverside. Choose your dates, see the full price, and collect your key at reception.</p>
    <div class="hero-photo">
      <img
        src="/images/luma-haven/rooms/riverfront-suite/main.jpg"
        :srcset="responsiveSrcset('/images/luma-haven/rooms/riverfront-suite/main.jpg')"
        :sizes="SIZES.wide"
        alt="Riverfront Suite at Luma Haven with a king bed, curved sofa and floor-to-ceiling windows over the river"
        width="1290"
        height="860"
        loading="eager"
        fetchpriority="high"
      />
    </div>
  </section>
</template>

<style scoped>
.hero { padding-top: 2rem; }
.hero-title { font-size: clamp(2.4375rem, 8vw, 3.8125rem); max-width: 16ch; color: var(--river); }
.hero-copy { margin-top: .75rem; font-size: 1.25rem; line-height: 1.4; color: var(--silt); max-width: 52ch; }
.hero-photo { margin-top: 1.75rem; aspect-ratio: 16 / 9; border-radius: var(--radius-photo); overflow: hidden; background: var(--sunk); }
.hero-photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
@media (max-width: 639px) { .hero-photo { aspect-ratio: 4 / 3; } }

/* The one orchestrated moment: the photo un-crops and the title settles, once. */
@media (prefers-reduced-motion: no-preference) {
  .hero-photo { animation: uncrop 900ms var(--ease-out) both; }
  .hero-title { animation: settle 700ms var(--ease-out) both; }
}
@keyframes uncrop { from { clip-path: inset(6%); } to { clip-path: inset(0); } }
@keyframes settle { from { letter-spacing: .02em; opacity: .0; } to { letter-spacing: -.01em; opacity: 1; } }
</style>
