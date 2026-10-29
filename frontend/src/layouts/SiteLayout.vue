<script setup lang="ts">
import ThemeToggle from '../components/ThemeToggle.vue'
</script>

<template>
  <div class="site-layout min-h-screen flex flex-col">
    <header class="guest-header">
      <div class="guest-header-inner max-w-6xl mx-auto px-5 flex items-center justify-between gap-4">
        <RouterLink to="/" class="brand-mark serif text-2xl font-semibold text-[var(--deep)]">Luma Haven<span class="text-[var(--brass)]">.</span></RouterLink>
        <div class="flex items-center gap-5">
          <nav aria-label="Main navigation" class="guest-nav flex items-center gap-6 text-sm font-semibold">
            <RouterLink to="/">Find a room</RouterLink>
            <RouterLink to="/verify">My stay</RouterLink>
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
    <main class="max-w-6xl mx-auto px-5 py-10 w-full grow">
      <slot />
    </main>
    <footer class="guest-footer p-8 text-center text-sm">Luma Haven · Your place to pause · Physical keys available at reception</footer>
  </div>
</template>
