<script setup lang="ts">
import ThemeToggle from '../components/ThemeToggle.vue'

defineProps<{ area: 'staff' | 'admin' }>()
</script>

<template>
  <div class="portal-shell">
    <aside class="portal-rail" aria-label="Private workspace identity">
      <RouterLink :to="area === 'admin' ? '/admin' : '/staff'" class="portal-brand-lockup flex items-center gap-3.5 group" aria-label="Luma Haven">
        <img
          src="/images/luma-haven/branding/logo.png"
          alt="Luma Haven Logo"
          class="w-12 h-12 object-contain shrink-0 transition-transform duration-300 group-hover:scale-105"
        />
        <div class="flex flex-col justify-center leading-none select-none">
          <span class="serif font-semibold text-[1.4rem] tracking-tight text-white leading-[1.08]">Luma</span>
          <span class="serif font-semibold text-[1.4rem] tracking-tight text-white leading-[1.08] mt-0.5">Haven<span class="text-[#d7b683]">.</span></span>
        </div>
      </RouterLink>
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
        <RouterLink :to="area === 'admin' ? '/admin' : '/staff'" class="serif text-xl flex items-center gap-2">
          <img src="/images/luma-haven/branding/logo.png" alt="Luma Haven Logo" class="w-6 h-6 object-contain" />
          <span>Luma Haven<span class="text-[#d7b683]">.</span></span>
        </RouterLink>
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
