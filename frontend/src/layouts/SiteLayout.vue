<script setup lang="ts">
import { ref } from 'vue'
import ThemeToggle from '../components/ThemeToggle.vue'

const mobileOpen = ref(false)
const toggleMobile = () => { mobileOpen.value = !mobileOpen.value }
const closeMobile = () => { mobileOpen.value = false }
</script>

<template>
  <div class="site-layout min-h-screen flex flex-col">
    <header class="guest-header">
      <div class="guest-header-inner max-w-6xl mx-auto px-5 flex items-center justify-between gap-4">
        <RouterLink to="/" class="brand-mark serif text-2xl font-semibold" @click="closeMobile">
          Luma Haven<span class="text-[var(--brass)]">.</span>
        </RouterLink>

        <!-- Desktop Navigation -->
        <div class="hidden sm:flex items-center gap-6">
          <nav aria-label="Main navigation" class="guest-nav flex items-center gap-7 text-sm font-semibold">
            <RouterLink to="/">Find a room</RouterLink>
            <RouterLink to="/verify">My stay</RouterLink>
          </nav>
          <div class="h-5 w-[1px] bg-[var(--line)]" aria-hidden="true" />
          <ThemeToggle />
        </div>

        <!-- Mobile Header Controls -->
        <div class="flex sm:hidden items-center gap-3">
          <ThemeToggle />
          <button
            type="button"
            class="p-2 rounded-md border border-[var(--glass-border)] text-[var(--brand-text)] hover:border-[var(--brass)] transition-colors"
            :aria-expanded="mobileOpen"
            aria-label="Toggle navigation menu"
            @click="toggleMobile"
          >
            <svg v-if="!mobileOpen" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Mobile Navigation Drawer -->
      <Transition name="slide-down">
        <nav
          v-if="mobileOpen"
          aria-label="Mobile navigation"
          class="sm:hidden mobile-nav-panel px-5 py-4 border-t border-[var(--glass-border)] space-y-3"
        >
          <RouterLink
            to="/"
            class="block py-2 text-base font-semibold text-[var(--nav-link)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            Find a room
          </RouterLink>
          <RouterLink
            to="/verify"
            class="block py-2 text-base font-semibold text-[var(--nav-link)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            My stay
          </RouterLink>
        </nav>
      </Transition>
    </header>

    <main class="max-w-6xl mx-auto px-5 py-10 w-full grow">
      <slot />
    </main>

    <footer class="guest-footer p-8 text-center text-sm border-t border-[var(--glass-border)]">
      <div class="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <span class="serif font-medium text-[var(--brand-text)]">Luma Haven<span class="text-[var(--brass)]">.</span></span>
        <p class="text-[var(--muted)] text-xs sm:text-sm">Your place to pause · Physical keys available at reception</p>
      </div>
    </footer>
  </div>
</template>
