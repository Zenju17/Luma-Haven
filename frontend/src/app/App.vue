<script setup lang="ts">
const presentationDemo = import.meta.env.VITE_PRESENTATION_DEMO === 'true'
</script>

<template>
  <aside v-if="presentationDemo" class="bg-[var(--ink)] text-[var(--mist)] px-4 py-2 text-center text-xs" aria-label="University demonstration">
    University presentation · Simulated payments and verification · Use fictional guest details
  </aside>
  <RouterView v-slot="{ Component }">
    <Transition name="page" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>
</template>
