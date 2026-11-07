<script setup lang="ts">
import SiteLayout from '../../layouts/SiteLayout.vue'
import HeroSection from './components/HeroSection.vue'
import FeaturedRoomTypes from './components/FeaturedRoomTypes.vue'
import HouseSection from './components/HouseSection.vue'
import StaySteps from './components/StaySteps.vue'
import LocationSection from './components/LocationSection.vue'
</script>

<template>
  <SiteLayout>
    <HeroSection />
    <FeaturedRoomTypes />
    <HouseSection />
    <StaySteps />
    <LocationSection />
  </SiteLayout>
</template>
