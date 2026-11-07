<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import ThemeToggle from '../components/ThemeToggle.vue'
import { api } from '../services/api'
import { useLanguage } from '../composables/useLanguage'
import type { PublicVisualAssetsResponse } from '../types'

const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)

// Kept so the shared ['visual-assets'] cache stays warm for other pages.
useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})

const { lang } = useLanguage()
interface CmsBlock { key: string; content: { text?: string; link?: string } }
const blocks = useQuery({
  queryKey: computed(() => ['cms-blocks', lang.value]),
  queryFn: () => api<CmsBlock[]>(`/cms/blocks?lang=${lang.value}`),
  staleTime: 60_000,
})
// Staff-edited announcement (CMS). Plain text only; links must be internal or https.
const announcement = computed(() => blocks.data.value?.find(b => b.key === 'site.announcement')?.content ?? null)
const announcementLink = computed(() => {
  const link = announcement.value?.link ?? ''
  return link.startsWith('/') && !link.startsWith('//') ? { internal: link } : link.startsWith('https://') ? { external: link } : null
})

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
  <div class="site-layout min-h-screen flex flex-col">
    <div v-if="announcement?.text" class="site-announce" role="status">
      <component :is="announcementLink?.internal ? 'RouterLink' : 'a'" v-if="announcementLink" :to="announcementLink.internal" :href="announcementLink.external" class="underline">{{ announcement.text }}</component>
      <span v-else>{{ announcement.text }}</span>
    </div>

    <header class="guest-header">
      <div class="guest-header-inner max-w-6xl mx-auto px-5 flex items-center justify-between gap-4">
        <RouterLink to="/" class="brand-mark" @click="closeMobile">Luma Haven</RouterLink>

        <div class="hidden lg:flex items-center gap-8">
          <nav aria-label="Main navigation" class="guest-nav flex items-center gap-7">
            <RouterLink to="/rooms">Rooms</RouterLink>
            <RouterLink to="/spaces">Spaces</RouterLink>
            <RouterLink to="/gallery">Gallery</RouterLink>
            <a href="/#location">Location</a>
            <RouterLink to="/verify">My stay</RouterLink>
          </nav>
          <div class="flex items-center gap-3">
            <ThemeToggle />
            <RouterLink to="/staff" class="header-icon-link" title="Staff sign-in" aria-label="Staff sign-in">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
            </RouterLink>
            <button type="button" class="header-cta" @click="handleCheckAvailability">Book a room</button>
          </div>
        </div>

        <div class="flex lg:hidden items-center gap-2">
          <ThemeToggle />
          <button type="button" class="menu-btn" :aria-expanded="mobileOpen" aria-label="Toggle navigation menu" @click="toggleMobile">{{ mobileOpen ? 'Close' : 'Menu' }}</button>
        </div>
      </div>

      <Transition name="fade">
        <nav v-if="mobileOpen" aria-label="Mobile navigation" class="lg:hidden mobile-sheet">
          <RouterLink to="/rooms" @click="closeMobile">Rooms</RouterLink>
          <RouterLink to="/spaces" @click="closeMobile">Spaces</RouterLink>
          <RouterLink to="/gallery" @click="closeMobile">Gallery</RouterLink>
          <a href="/#location" @click="closeMobile">Location</a>
          <RouterLink to="/verify" @click="closeMobile">My stay</RouterLink>
          <button type="button" class="header-cta mobile-sheet__cta" @click="handleCheckAvailability">Book a room</button>
          <RouterLink to="/staff" class="mobile-sheet__staff" @click="closeMobile">Staff sign-in</RouterLink>
        </nav>
      </Transition>
    </header>

    <main class="max-w-6xl mx-auto px-5 w-full grow">
      <slot />
    </main>

    <footer class="guest-footer mt-20">
      <div class="max-w-6xl mx-auto px-5 py-12 sm:py-16">
        <div class="footer-grid">
          <div class="footer-brand">
            <RouterLink to="/" class="brand-mark">Luma Haven</RouterLink>
            <p>A small hotel in Daun Penh, Phnom Penh. Quiet rooms, a short walk from the riverside.</p>
          </div>
          <div>
            <h2 class="footer-h">Explore</h2>
            <ul>
              <li><RouterLink to="/rooms">Rooms</RouterLink></li>
              <li><RouterLink to="/spaces">Spaces</RouterLink></li>
              <li><RouterLink to="/gallery">Gallery</RouterLink></li>
              <li><a href="/#location">Location</a></li>
              <li><RouterLink to="/verify">My stay</RouterLink></li>
            </ul>
          </div>
          <div>
            <h2 class="footer-h">House rules</h2>
            <ul>
              <li>Check-in from 14:00</li>
              <li>Check-out by 12:00</li>
              <li>Quiet hours 22:00 to 07:00</li>
              <li>Smoke-free property</li>
            </ul>
          </div>
          <div>
            <h2 class="footer-h">Contact</h2>
            <ul>
              <li>Daun Penh, Phnom Penh, Cambodia</li>
              <li><a href="mailto:hello@luma.local">hello@luma.local</a></li>
              <li><a href="tel:+85500000000">+855 00 000 000</a></li>
            </ul>
            <p class="footer-access">Ground-floor courtyard rooms are step-free. Ask reception for any other help you need.</p>
          </div>
        </div>

        <div class="footer-bottom">
          <p>© {{ new Date().getFullYear() }} Luma Haven. All rights reserved.</p>
          <div class="footer-legal">
            <RouterLink to="/legal/terms">Terms</RouterLink>
            <RouterLink to="/legal/privacy">Privacy</RouterLink>
            <RouterLink to="/legal/cancellation">Cancellation</RouterLink>
            <RouterLink to="/legal/cookies">Cookies</RouterLink>
            <RouterLink to="/staff">Staff sign-in</RouterLink>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.site-announce { background: var(--river); color: var(--palm-leaf); text-align: center; font-size: .875rem; padding: .5rem 1rem; }
.guest-header-inner { min-height: 72px; }
.header-icon-link { display: grid; place-items: center; width: 44px; height: 44px; color: var(--silt); }
.header-icon-link:hover { color: var(--river); }
.header-cta { min-height: 44px; padding: 0 1.25rem; border-radius: var(--radius-pill); background: var(--river); color: var(--on-river); font: 600 .9375rem var(--font-text); }
.header-cta:hover { background: var(--river-hover); }
.menu-btn { min-height: 44px; padding: 0 1rem; border-radius: var(--radius-pill); border: 1.5px solid var(--rule); color: var(--river); font: 600 .9375rem var(--font-text); }
.mobile-sheet { position: fixed; inset: 72px 0 0 0; z-index: 50; display: flex; flex-direction: column; gap: .25rem; padding: 1.5rem 1.25rem; background: var(--palm-leaf); overflow-y: auto; }
.mobile-sheet a:not(.mobile-sheet__staff) { font: 400 2.4375rem/1.1 var(--font-display); color: var(--river); padding: .5rem 0; border-bottom: 1px solid var(--rule); }
.mobile-sheet__cta { margin-top: 1.5rem; }
.mobile-sheet__staff { margin-top: 1rem; color: var(--silt); font-size: .875rem; min-height: 44px; display: inline-flex; align-items: center; }
.footer-grid { display: grid; gap: 2rem; grid-template-columns: 1fr; }
.footer-brand p { margin-top: .75rem; color: var(--silt); font-size: .9375rem; }
.footer-h { font: 600 .9375rem var(--font-text) !important; color: var(--river); margin-bottom: .75rem; letter-spacing: 0; }
.guest-footer ul { display: grid; gap: .5rem; color: var(--silt); font-size: .9375rem; }
.guest-footer a:hover { color: var(--river); text-decoration: underline; }
.footer-access { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--rule); color: var(--silt); font-size: .875rem; }
.footer-bottom { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--rule); display: flex; flex-direction: column; gap: 1rem; color: var(--silt); font-size: .875rem; }
.footer-legal { display: flex; flex-wrap: wrap; gap: .25rem 1.5rem; }
.footer-legal a { min-height: 44px; display: inline-flex; align-items: center; }
@media (min-width: 768px) { .footer-grid { grid-template-columns: 1.4fr 1fr 1fr 1.2fr; gap: 3rem; } .footer-bottom { flex-direction: row; justify-content: space-between; align-items: center; } }
</style>
