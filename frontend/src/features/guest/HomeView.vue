<script setup lang="ts">
import SiteLayout from '../../layouts/SiteLayout.vue'
import HeroSection from './components/HeroSection.vue'
import AvailabilitySearch from './components/AvailabilitySearch.vue'
import FeaturedRoomTypes from './components/FeaturedRoomTypes.vue'
import HotelGallery from './components/HotelGallery.vue'
import StaySteps from './components/StaySteps.vue'
import LocationSection from './components/LocationSection.vue'

function handleFocusSearch() {
  const el = document.getElementById('search')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
    const input = el.querySelector('input')
    if (input) input.focus()
  }
}
</script>

<template>
  <SiteLayout>
    <!-- Section 2: Hero -->
    <HeroSection @focus-search="handleFocusSearch" />

    <!-- Section 3: Availability search -->
    <div class="search-overlap">
      <AvailabilitySearch :navigate-on-submit="true" />
    </div>

    <!-- Section 5: Featured room types -->
    <FeaturedRoomTypes />

    <!-- Section 6: Hotel gallery carousel -->
    <HotelGallery />

    <StaySteps />

    <!-- Section 9: Location and practical details -->
    <LocationSection />
  </SiteLayout>
</template>

<style scoped>
.search-overlap { position: relative; z-index: 10; margin-top: -2rem; margin-bottom: 1rem; padding-inline: .5rem; }
@media (min-width: 900px) { .search-overlap { margin-top: -2.5rem; padding-inline: 3rem; } }
</style>
