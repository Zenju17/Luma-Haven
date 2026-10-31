<script setup lang="ts">
import SiteLayout from '../../layouts/SiteLayout.vue'
import HeroSection from './components/HeroSection.vue'
import AvailabilitySearch from './components/AvailabilitySearch.vue'
import HotelIntroduction from './components/HotelIntroduction.vue'
import FeaturedRoomTypes from './components/FeaturedRoomTypes.vue'
import HotelGallery from './components/HotelGallery.vue'
import ExperienceSection from './components/ExperienceSection.vue'
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
    <div class="relative z-10 -mt-6 sm:-mt-10 mb-8 sm:mb-12">
      <AvailabilitySearch :navigate-on-submit="true" />
    </div>

    <!-- Section 4: Hotel introduction -->
    <HotelIntroduction />

    <!-- Section 5: Featured room types -->
    <FeaturedRoomTypes />

    <!-- Section 6: Hotel gallery carousel -->
    <HotelGallery />

    <!-- Section 7: Experience section -->
    <ExperienceSection />

    <!-- Section 8: How your stay works -->
    <StaySteps />

    <!-- Section 9: Location and practical details -->
    <LocationSection />
  </SiteLayout>
</template>
