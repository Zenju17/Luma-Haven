<script setup lang="ts">
const emit = defineEmits<{
  (e: 'focusSearch'): void
}>()

function scrollToSearch() {
  emit('focusSearch')
}
</script>

<template>
  <section class="hero" aria-labelledby="hero-heading">
    <div class="hero-photo">
      <img
        src="/images/luma-haven/rooms/riverfront-suite/main.jpg"
        alt="Riverfront Suite at Luma Haven with a king bed, curved sofa and floor-to-ceiling windows over the river"
        width="1290"
        height="860"
        loading="eager"
        fetchpriority="high"
      />
    </div>

    <div class="lh-hero-panel">
      <h1 id="hero-heading" class="serif hero-title">
        Rest by the river in Phnom Penh
      </h1>
      <p class="lh-hero-copy">
        Ten room types, from a quiet queen to a riverfront suite. Choose your dates, see the full price
        before you book, and pick up your key at reception.
      </p>
      <div class="hero-actions">
        <button type="button" class="btn-cta" @click="scrollToSearch">Check dates</button>
        <RouterLink to="/rooms" class="btn-ghost-light">See all rooms</RouterLink>
      </div>
      <dl class="hero-facts">
        <div><dt>Check-in</dt><dd>from 14:00</dd></div>
        <div><dt>Check-out</dt><dd>by 12:00</dd></div>
        <div><dt>Quiet hours</dt><dd>22:00–07:00</dd></div>
      </dl>
    </div>
  </section>
</template>

<style scoped>
.hero {
  display: grid;
  margin: 0 -1rem;
  padding-bottom: 2.5rem;
}
.hero-photo {
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--surface-muted);
}
.hero-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.lh-hero-panel {
  background: var(--brand-teal);
  color: var(--brand-celadon);
  padding: 1.75rem 1.25rem 1.5rem;
}
.hero-title {
  font-size: clamp(2rem, 7vw, 3.75rem);
  line-height: 1.05;
  font-weight: 500;
  color: #fff;
  max-width: 14ch;
}
.lh-hero-copy {
  margin-top: 1rem;
  max-width: 46ch;
  line-height: 1.6;
  color: color-mix(in srgb, var(--brand-celadon) 88%, transparent);
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1.5rem;
}
.hero-actions > * {
  flex: 1 1 10rem;
  justify-content: center;
}
.hero-facts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-top: 1.75rem;
  padding-top: 1.25rem;
  border-top: 1px solid color-mix(in srgb, var(--brand-celadon) 25%, transparent);
  font-size: 0.8125rem;
}
.hero-facts dt {
  color: color-mix(in srgb, var(--brand-celadon) 70%, transparent);
}
.hero-facts dd {
  color: #fff;
  font-weight: 600;
  margin-top: 0.125rem;
}

@media (min-width: 640px) {
  .hero { margin: 0; padding-top: 1.5rem; }
  .hero-photo, .lh-hero-panel { border-radius: 0; }
  .hero-photo { border-radius: 1.5rem 1.5rem 0 0; }
  .lh-hero-panel { border-radius: 0 0 1.5rem 1.5rem; padding: 2rem; }
}

@media (min-width: 1024px) {
  .hero {
    grid-template-columns: repeat(12, 1fr);
    align-items: end;
    padding-top: 2rem;
    padding-bottom: 4rem;
  }
  .hero-photo {
    grid-column: 1 / 13;
    grid-row: 1;
    aspect-ratio: 16 / 8;
    border-radius: 1.75rem;
  }
  .lh-hero-panel {
    grid-column: 1 / 7;
    grid-row: 1;
    margin: 0 0 -2.5rem 2rem;
    border-radius: 1.25rem;
    padding: 2.5rem;
    box-shadow: 0 24px 48px -24px rgb(6 40 41 / 0.6);
  }
  .hero-actions > * { flex: 0 0 auto; }
}
</style>
