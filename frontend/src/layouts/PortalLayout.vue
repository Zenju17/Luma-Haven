<script setup lang="ts">
import { computed } from 'vue'
import ThemeToggle from '../components/ThemeToggle.vue'

export interface PortalNavItem {
  id: string
  label: string
  icon: string
  group?: string
  badge?: boolean
  to?: string // route link instead of an in-page section
}

const props = defineProps<{
  area: 'staff' | 'admin'
  items?: PortalNavItem[]
  active?: string
  navLabel?: string
}>()
const emit = defineEmits<{ (e: 'select', id: string): void }>()

// 24px stroke icons, drawn inline: the project has no icon library.
const ICONS: Record<string, string> = {
  home: 'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  coin: 'M12 3a9 9 0 100 18 9 9 0 000-18zM9 9.5c0-1 1.3-1.8 3-1.8s3 .8 3 1.8-1.3 1.6-3 2.2-3 1.2-3 2.3 1.3 1.8 3 1.8 3-.8 3-1.8',
  tag: 'M3 12V4h8l10 10-8 8zM7.5 8.5h.01',
  chart: 'M4 20V10M10 20V4M16 20v-8M22 20H2',
  image: 'M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M9 9h.01',
  bed: 'M3 18V6M3 14h18v4M21 14v-2a3 3 0 00-3-3h-7v5M7 11h.01',
  page: 'M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7',
  scale: 'M12 3v18M6 21h12M5 7h14M5 7l-3 7a3 3 0 006 0zM19 7l-3 7a3 3 0 006 0z',
  lock: 'M6 11h12v10H6zM8 11V7a4 4 0 018 0v4',
  card: 'M3 6h18v12H3zM3 10h18M7 15h3',
  report: 'M5 3h14v18H5zM9 8h6M9 12h6M9 16h3',
  people: 'M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2 20c0-3.5 3-6 7-6s7 2.5 7 6M17 5a3 3 0 010 6M19 14c2 .7 3 2.3 3 4',
  gear: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19 12l2-1-1-3-2 .3a7 7 0 00-1.5-1.5L16.8 4l-3-1-1 2h-1.6l-1-2-3 1 .3 2.2A7 7 0 005.2 7.7L3 7.4l-1 3 2 1a7 7 0 000 1.6l-2 1 1 3 2.2-.3a7 7 0 001.5 1.5L7.4 21l3 1 1-2h1.6l1 2 3-1-.3-2.2a7 7 0 001.5-1.5l2.2.3 1-3-2-1',
  clock: 'M12 3a9 9 0 100 18 9 9 0 000-18zM12 7v5l3 2',
  code: 'M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4 3.5-6 8-6s8 2 8 6',
}
const homeLink = computed(() => (props.area === 'admin' ? '/admin' : '/staff'))
const todayLabel = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())
</script>

<template>
  <div class="portal-shell">
    <aside class="rail" aria-label="Workspace">
      <RouterLink :to="homeLink" class="rail-mark" aria-label="Luma Haven">LH</RouterLink>
      <nav v-if="items?.length" class="rail-nav" :aria-label="navLabel ?? (area === 'admin' ? 'Administration sections' : 'Staff navigation')">
        <template v-for="(item, i) in items" :key="item.id">
          <span v-if="item.group && item.group !== items[i - 1]?.group" class="rail-rule" aria-hidden="true" />
          <component
            :is="item.to ? 'RouterLink' : 'button'"
            :to="item.to"
            :type="item.to ? undefined : 'button'"
            class="rail-item"
            :class="{ 'rail-item--on': active === item.id }"
            :aria-label="item.label"
            :aria-current="active === item.id ? 'page' : undefined"
            :data-tip="item.label"
            @click="!item.to && emit('select', item.id)"
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="ICONS[item.icon] ?? ICONS.page" /></svg>
            <span v-if="item.badge" class="rail-dot" aria-hidden="true" />
            <span v-if="active === item.id" class="rail-label" aria-hidden="true">{{ item.label }}</span>
          </component>
        </template>
      </nav>
      <div class="rail-foot"><ThemeToggle /></div>
    </aside>

    <div class="portal-stage">
      <header class="topbar">
        <RouterLink :to="homeLink" class="topbar-mark">Luma Haven</RouterLink>
        <span class="topbar-date">{{ todayLabel }}</span>
        <span class="topbar-area">{{ area === 'admin' ? 'Administration' : 'Staff' }}</span>
        <span class="topbar-theme"><ThemeToggle /></span>
      </header>
      <main><slot /></main>
      <footer class="portal-footer p-6 text-center text-xs">Private hotel workspace, Luma Haven</footer>
    </div>
  </div>
</template>

<style scoped>
.portal-shell { display: grid; grid-template-columns: 1fr; }
.rail {
  position: fixed; z-index: 30; inset: auto 0 0 0; display: flex; align-items: center; gap: .25rem;
  background: var(--sidebar-bg); color: var(--sidebar-text); padding: .25rem .5rem; padding-bottom: calc(.25rem + env(safe-area-inset-bottom));
}
.rail-mark, .rail-foot { display: none; }
.rail-nav { display: flex; gap: .25rem; overflow-x: auto; flex: 1; }
.rail-rule { flex: 0 0 1px; align-self: stretch; margin: .5rem .25rem; background: color-mix(in oklab, var(--sidebar-text) 25%, transparent); }
.rail-item {
  position: relative; flex: 0 0 auto; min-width: 48px; min-height: 48px; display: grid; place-items: center; align-content: center; gap: 2px;
  padding: .25rem .5rem; border-radius: 12px; color: var(--sidebar-text-muted);
}
.rail-item:hover { color: var(--sidebar-text); }
.rail-item--on { background: color-mix(in oklab, var(--sidebar-text) 14%, transparent); color: var(--sidebar-text); }
.rail-item:focus-visible { outline: 2px solid var(--laterite); outline-offset: 2px; }
.rail-label { font-size: .6875rem; font-weight: 600; line-height: 1.1; max-width: 72px; text-align: center; }
.rail-dot { position: absolute; top: 8px; right: 10px; width: 8px; height: 8px; border-radius: 50%; background: var(--laterite); }

.portal-stage { display: flex; flex-direction: column; min-width: 0; min-height: 100vh; padding-bottom: 64px; }
.portal-stage main { width: 100%; max-width: 1190px; margin: 0 auto; padding: 24px 18px; flex: 1; }
.topbar { display: flex; align-items: center; gap: .75rem; min-height: 56px; padding: 0 18px; border-bottom: 1px solid var(--rule); background: var(--palm-leaf); }
.topbar-mark { font: 500 1.5625rem/1 var(--font-display); color: var(--river); margin-right: auto; }
.topbar-date { display: none; color: var(--silt); font-size: .9375rem; }
.topbar-area { color: var(--silt); font-size: .875rem; }

@media (min-width: 851px) {
  .portal-shell { grid-template-columns: 72px minmax(0, 1fr); }
  .rail {
    position: sticky; top: 0; inset: auto; height: 100vh; flex-direction: column; justify-content: flex-start; gap: .75rem; padding: 1rem 0; align-items: stretch;
  }
  .rail-mark { display: grid; place-items: center; height: 44px; font: 500 1.4375rem/1 var(--font-display); color: var(--sidebar-text); }
  .rail-nav { flex-direction: column; align-items: center; overflow-y: auto; overflow-x: visible; flex: 1; scrollbar-width: none; }
  .rail-rule { flex: 0 0 1px; align-self: center; width: 28px; height: 1px; margin: .35rem 0; }
  .rail-item { width: 60px; min-height: 56px; }
  .rail-foot { display: grid; place-items: center; }
  .rail-item::after {
    content: attr(data-tip); position: fixed; left: 76px; padding: .35rem .7rem; border-radius: 8px; white-space: nowrap; pointer-events: none;
    background: var(--paper); color: var(--river); font: 500 .8125rem var(--font-text); box-shadow: var(--shadow-float); opacity: 0;
  }
  .rail-item:hover::after, .rail-item:focus-visible::after { opacity: 1; }
  .rail-item--on::after { display: none; }
  .portal-stage { padding-bottom: 0; }
  .portal-stage main { padding: 38px clamp(20px, 4vw, 54px); }
  .topbar { padding: 0 clamp(20px, 4vw, 54px); }
  .topbar-mark, .topbar-theme { display: none; }
  .topbar-date { display: inline; margin-right: auto; font-weight: 500; color: var(--river); }
}
@media print { .rail, .topbar { display: none; } }
</style>
