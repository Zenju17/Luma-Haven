<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import ThemeToggle from '../components/ThemeToggle.vue'
import { api } from '../services/api'
import type { PublicVisualAssetsResponse } from '../types'

const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})
const logoAsset = computed(() => visualAssets.data.value?.logo ?? null)

const toggleMobile = () => { mobileOpen.value = !mobileOpen.value }
const closeMobile = () => { mobileOpen.value = false }

function handleCheckAvailability() {
  closeMobile()
  if (route.path === '/') {
    const el = document.getElementById('search')
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
      const input = el.querySelector('input')
      if (input) input.focus()
      return
    }
  }
  router.push('/rooms')
}
</script>

<template>
  <div class="site-layout min-h-screen flex flex-col bg-[var(--mist)] text-[var(--ink)]">
    <!-- Section 1: Header -->
    <header class="guest-header sticky top-0 z-40 backdrop-blur-md bg-[var(--surface-overlay)] border-b border-[var(--glass-border)] transition-colors">
      <div class="guest-header-inner max-w-6xl mx-auto px-5 py-3.5 flex items-center justify-between gap-4">
        <!-- Logo -->
        <RouterLink to="/" class="brand-mark flex items-center gap-2.5 serif text-2xl font-semibold tracking-tight text-[var(--brand-text)] hover:opacity-90 transition-opacity" @click="closeMobile">
          <img
            :src="logoAsset ? logoAsset.image_url : '/images/logo.png'"
            :alt="logoAsset ? logoAsset.alt_text : 'Luma Haven Hotel'"
            class="h-8 w-auto object-contain"
            width="32"
            height="32"
          />
          <span>Luma Haven<span class="text-[var(--brass)]">.</span></span>
        </RouterLink>

        <!-- Desktop Navigation -->
        <div class="hidden lg:flex items-center gap-7">
          <nav aria-label="Main navigation" class="guest-nav flex items-center gap-6 text-sm font-medium text-[var(--brand-text)]">
            <RouterLink to="/rooms" class="hover:text-[var(--brass)] transition-colors">Rooms</RouterLink>
            <RouterLink to="/spaces" class="hover:text-[var(--brass)] transition-colors">Spaces</RouterLink>
            <a href="/#about" class="hover:text-[var(--brass)] transition-colors">About</a>
            <a href="/#experience" class="hover:text-[var(--brass)] transition-colors">Experience</a>
            <RouterLink to="/gallery" class="hover:text-[var(--brass)] transition-colors">Gallery</RouterLink>
            <a href="/#location" class="hover:text-[var(--brass)] transition-colors">Location</a>
            <RouterLink to="/verify" class="hover:text-[var(--brass)] transition-colors">My Stay</RouterLink>
          </nav>

          <div class="h-4 w-[1px] bg-[var(--line)]" aria-hidden="true" />

          <div class="flex items-center gap-4">
            <ThemeToggle />

            <!-- Clear Check Availability Action -->
            <button
              type="button"
              class="btn text-xs sm:text-sm font-semibold px-4 py-2 rounded-lg shadow-sm hover:shadow transition-all"
              @click="handleCheckAvailability"
            >
              Check availability
            </button>

            <!-- Discreet Staff Sign-in -->
            <RouterLink
              to="/staff"
              class="text-xs text-[var(--muted)] hover:text-[var(--brand-text)] transition-colors p-1"
              title="Staff sign-in"
              aria-label="Staff sign-in"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </RouterLink>
          </div>
        </div>

        <!-- Medium/Mobile Controls -->
        <div class="flex lg:hidden items-center gap-3">
          <ThemeToggle />
          <button
            type="button"
            class="btn text-xs px-3 py-1.5 font-semibold"
            @click="handleCheckAvailability"
          >
            Check dates
          </button>
          <button
            type="button"
            class="p-2 rounded-lg border border-[var(--glass-border)] text-[var(--brand-text)] hover:border-[var(--brass)] transition-colors"
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
          class="lg:hidden mobile-nav-panel px-5 py-5 border-t border-[var(--glass-border)] bg-[var(--surface-raised)] space-y-3.5 shadow-xl"
        >
          <RouterLink
            to="/rooms"
            class="block py-2 text-base font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            Rooms &amp; Suites
          </RouterLink>
          <RouterLink
            to="/spaces"
            class="block py-2 text-base font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            Hotel Spaces &amp; Locations
          </RouterLink>
          <a
            href="/#about"
            class="block py-2 text-base font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            About Luma Haven
          </a>
          <a
            href="/#experience"
            class="block py-2 text-base font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            The Experience
          </a>
          <RouterLink
            to="/gallery"
            class="block py-2 text-base font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            Hotel Gallery &amp; Photos
          </RouterLink>
          <a
            href="/#location"
            class="block py-2 text-base font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            Location &amp; Policies
          </a>
          <RouterLink
            to="/verify"
            class="block py-2 text-base font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors"
            @click="closeMobile"
          >
            My Stay (Guest Portal)
          </RouterLink>

          <div class="pt-3 border-t border-[var(--line)] flex items-center justify-between">
            <button
              type="button"
              class="btn w-full py-2.5 text-sm font-semibold"
              @click="handleCheckAvailability"
            >
              Check availability
            </button>
          </div>

          <div class="pt-2 text-center">
            <RouterLink
              to="/staff"
              class="text-xs text-[var(--muted)] hover:text-[var(--brass)] inline-flex items-center gap-1.5"
              @click="closeMobile"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Staff Portal Access
            </RouterLink>
          </div>
        </nav>
      </Transition>
    </header>

    <!-- Main Content Area -->
    <main class="max-w-6xl mx-auto px-5 w-full grow">
      <slot />
    </main>

    <!-- Section 10: Footer -->
    <footer class="guest-footer mt-20 border-t border-[var(--line)] bg-[var(--surface-raised)] text-[var(--ink)]">
      <div class="max-w-6xl mx-auto px-5 py-12 sm:py-16">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-8 lg:gap-12">
          <!-- Column 1: Brand & Philosophy (4 cols) -->
          <div class="lg:col-span-4 space-y-4">
            <RouterLink to="/" class="brand-mark flex items-center gap-2.5 serif text-2xl font-semibold tracking-tight text-[var(--brand-text)]">
              <img
                :src="logoAsset ? logoAsset.image_url : '/images/logo.png'"
                :alt="logoAsset ? logoAsset.alt_text : 'Luma Haven Hotel'"
                class="h-8 w-auto object-contain"
                width="32"
                height="32"
              />
              <span>Luma Haven<span class="text-[var(--brass)]">.</span></span>
            </RouterLink>
            <p class="text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
              A boutique hotel sanctuary in Phnom Penh, Cambodia. Thoughtful hospitality, mindful acoustics, and physical brass keys for the unhurried traveler.
            </p>
            <div class="pt-2 text-xs text-[var(--brass)] font-semibold flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[var(--brass)]" />
              Solid brass room keys at reception
            </div>
          </div>

          <!-- Column 2: Navigation Links (2 cols) -->
          <div class="lg:col-span-2 space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
              Explore
            </p>
            <ul class="space-y-2 text-xs sm:text-sm text-[var(--muted)]">
              <li><RouterLink to="/rooms" class="hover:text-[var(--brand-text)] transition-colors">Rooms &amp; Suites</RouterLink></li>
              <li><RouterLink to="/spaces" class="hover:text-[var(--brand-text)] transition-colors">Spaces &amp; Locations</RouterLink></li>
              <li><RouterLink to="/gallery" class="hover:text-[var(--brand-text)] transition-colors">Hotel Gallery</RouterLink></li>
              <li><a href="/#about" class="hover:text-[var(--brand-text)] transition-colors">About Luma Haven</a></li>
              <li><a href="/#experience" class="hover:text-[var(--brand-text)] transition-colors">The Experience</a></li>
              <li><a href="/#location" class="hover:text-[var(--brand-text)] transition-colors">Location &amp; Map</a></li>
            </ul>
          </div>

          <!-- Column 3: Guest Stay & Policies (3 cols) -->
          <div class="lg:col-span-3 space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
              Guest Care &amp; Stay
            </p>
            <ul class="space-y-2 text-xs sm:text-sm text-[var(--muted)]">
              <li><RouterLink to="/verify" class="font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors">My Stay Portal</RouterLink></li>
              <li><span class="text-[var(--muted)]">Check-in: 14:00 (Asia/Phnom_Penh)</span></li>
              <li><span class="text-[var(--muted)]">Check-out: 12:00 (Noon)</span></li>
              <li><span class="text-[var(--muted)]">Quiet Hours: 22:00 – 07:00</span></li>
              <li><span class="text-[var(--muted)]">100% Smoke-free property</span></li>
            </ul>
          </div>

          <!-- Column 4: Contact & Accessibility (3 cols) -->
          <div class="lg:col-span-3 space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
              Contact &amp; Assistance
            </p>
            <div class="text-xs sm:text-sm text-[var(--muted)] space-y-2">
              <p>Daun Penh, Phnom Penh, Cambodia</p>
              <p><a href="mailto:hello@luma.local" class="hover:text-[var(--brand-text)]">hello@luma.local</a></p>
              <p><a href="tel:+85500000000" class="hover:text-[var(--brand-text)] font-mono">+855 00 000 000</a></p>
            </div>
            <div class="pt-2 text-[11px] text-[var(--muted)] leading-normal border-t border-[var(--line)]">
              <strong class="text-[var(--brand-text)] block font-semibold mb-0.5">Accessibility Statement:</strong>
              Ground-floor step-free courtyard rooms, accessible tactile signage, and personal assistance available upon request.
            </div>
          </div>
        </div>

        <!-- Bottom Bar -->
        <div class="mt-12 pt-6 border-t border-[var(--line)] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[var(--muted)]">
          <p>© {{ new Date().getFullYear() }} Luma Haven Boutique Hotel. All rights reserved.</p>
          <div class="flex items-center gap-6">
            <RouterLink to="/verify" class="hover:text-[var(--brand-text)] transition-colors">Find My Stay</RouterLink>
            <RouterLink to="/legal/terms" class="hover:text-[var(--brand-text)] transition-colors">Terms</RouterLink>
            <RouterLink to="/legal/privacy" class="hover:text-[var(--brand-text)] transition-colors">Privacy</RouterLink>
            <RouterLink to="/legal/cancellation" class="hover:text-[var(--brand-text)] transition-colors">Cancellation</RouterLink>
            <RouterLink to="/legal/cookies" class="hover:text-[var(--brand-text)] transition-colors">Cookies</RouterLink>
            <RouterLink to="/staff" class="text-[var(--muted)]/75 hover:text-[var(--brand-text)] transition-colors flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Staff Sign-in
            </RouterLink>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>
