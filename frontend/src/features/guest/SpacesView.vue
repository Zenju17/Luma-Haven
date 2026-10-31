<script setup lang="ts">
import SiteLayout from '../../layouts/SiteLayout.vue'
import SpacesExplorer from './components/SpacesExplorer.vue'
</script>

<template>
  <SiteLayout>
    <div class="pt-8 sm:pt-12 pb-16">
      <!-- Section Header -->
      <div class="max-w-3xl mb-10 space-y-3">
        <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">
          Hotel Spaces &amp; Visual Locations
        </span>
        <h1 class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
          Explore every corner of Luma Haven<span class="text-[var(--brass)]">.</span>
        </h1>
        <p class="text-sm sm:text-base text-[var(--muted)] leading-relaxed">
          Review our hotel photography and design concepts, with each space and room amenity categorized by its exact location and name.
        </p>
      </div>

      <!-- Spaces Explorer Grid & Lightbox -->
      <SpacesExplorer />
    </div>
  </SiteLayout>
</template>
