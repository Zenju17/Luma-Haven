<script setup lang="ts">
import SiteLayout from '../../layouts/SiteLayout.vue'
import SpacesExplorer from './components/SpacesExplorer.vue'
</script>

<template>
  <SiteLayout>
    <div class="pt-8 sm:pt-12 pb-16">
      <div class="sp-head">
        <h1>Spaces</h1>
        <p>Every room and shared area, named by where it is in the hotel.</p>
      </div>
      <SpacesExplorer />
    </div>
  </SiteLayout>
</template>

<style scoped>
.sp-head { display: grid; gap: .5rem; max-width: 60ch; }
.sp-head h1 { font-size: 3.0625rem; color: var(--river); }
.sp-head p { color: var(--silt); }
</style>
