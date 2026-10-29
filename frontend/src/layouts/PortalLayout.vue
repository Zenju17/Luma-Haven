<script setup lang="ts">
import ThemeToggle from '../components/ThemeToggle.vue'

defineProps<{ area: 'staff' | 'admin' }>()
</script>

<template>
  <div class="portal-shell">
    <aside class="portal-rail" aria-label="Private workspace identity">
      <RouterLink :to="area === 'admin' ? '/admin' : '/staff'" class="brand-mark serif text-2xl font-semibold">Luma Haven<span class="text-[#d7b683]">.</span></RouterLink>
      <div class="portal-rail-rule" aria-hidden="true" />
      <p class="portal-rail-title">{{ area === 'admin' ? 'The hotel, at a glance.' : 'A clearer day at the desk.' }}</p>
      <p class="portal-rail-note mt-5">{{ area === 'admin' ? 'People, performance and the decisions behind every stay.' : 'Arrivals, rooms and requests in one working view.' }}</p>
      <div class="portal-rail-bottom">
        <div class="flex items-center justify-between gap-3 mb-3">
          <span>{{ area === 'admin' ? 'Administration console' : 'Staff operations' }}</span>
          <ThemeToggle />
        </div>
        Luma Haven
      </div>
    </aside>
    <div class="portal-stage">
      <header class="portal-mobile-header">
        <RouterLink :to="area === 'admin' ? '/admin' : '/staff'" class="serif text-xl">Luma Haven<span class="text-[#d7b683]">.</span></RouterLink>
        <div class="flex items-center gap-3">
          <span class="text-xs">{{ area === 'admin' ? 'Administration' : 'Staff operations' }}</span>
          <ThemeToggle />
        </div>
      </header>
      <main><slot /></main>
      <footer class="portal-footer p-6 text-center text-xs">Private hotel workspace · Luma Haven</footer>
    </div>
  </div>
</template>
