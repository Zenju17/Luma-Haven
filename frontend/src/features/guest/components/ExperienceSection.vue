<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '../../../services/api'
import type { PublicVisualAssetsResponse, VisualAsset } from '../../../types'

interface ExperiencePillar {
  title: string
  subtitle: string
  description: string
  details: string[]
  icon: string
}

const experiences: ExperiencePillar[] = [
  {
    title: 'Solid Brass Reception',
    subtitle: 'A tactile, genuine welcome',
    description: 'No plastic RFID cards or glitchy app downloads. When you arrive, our reception team personally hands you your weighted brass key, stamped with your room number.',
    details: ['Front desk available daily', 'Complimentary luggage storage', 'Personal neighborhood recommendations'],
    icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z',
  },
  {
    title: 'In-Room Service Requests',
    subtitle: 'Direct guest portal on your phone',
    description: 'Once verified, access your stay portal at any time to request extra towels, mineral water, luggage assistance, or maintenance with real-time status updates.',
    details: ['Quick one-tap requests', 'Housekeeping dispatch integration', 'No login password needed (secure code)'],
    icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z',
  },
  {
    title: 'Workspaces & Fiber Wi-Fi',
    subtitle: 'Quiet concentration anywhere',
    description: 'High-speed fiber connectivity extends across every guest room, garden courtyard nook, and rooftop terrace. Acoustic walls protect your video calls and mindful focus.',
    details: ['Solid timber writing desks', 'Dedicated in-room Wi-Fi access points', 'Acoustically insulated walls'],
    icon: 'M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0',
  },
  {
    title: 'Unhurried Hours',
    subtitle: '14:00 Check-in · 12:00 Check-out',
    description: 'We give you extra time to settle in and savor your morning coffee. Enjoy quiet hours from 22:00 to 07:00 so every guest experiences deep, restorative sleep.',
    details: ['Check-in from 14:00 (Asia/Phnom_Penh)', 'Relaxed check-out until 12:00 noon', 'Quiet hours observed 22:00–07:00'],
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  },
]

const visualAssets = useQuery({
  queryKey: ['visual-assets'],
  queryFn: () => api<PublicVisualAssetsResponse>('/visual-assets'),
})

interface FeatureLocationCard {
  id: string
  title: string
  locationName: string
  caption: string
  asset: VisualAsset | null
  fallbackSrc: string
}

const featureCards = computed<FeatureLocationCard[]>(() => {
  const items = visualAssets.data.value?.features || []

  const poolAsset = items.find(a => a.original_filename?.includes('pool')) || null
  const diningAsset = items.find(a => a.original_filename?.includes('dining')) || null
  const gymAsset = items.find(a => a.original_filename?.includes('gym')) || null
  const detailsAsset = items.find(a => a.original_filename?.includes('details')) || null
  const loungeAsset = items.find(a => a.original_filename?.includes('lounge')) || null

  return [
    {
      id: 'pool',
      title: 'Shaded Pool & Daybeds',
      locationName: 'Rooftop Pool Terrace',
      caption: 'Canopied loungers and tranquil waters designed for unhurried midday pause.',
      asset: poolAsset,
      fallbackSrc: '/images/luma-haven/facilities/pool.jpg',
    },
    {
      id: 'dining',
      title: 'Bistro & Courtyard Dining',
      locationName: 'Hotel Bistro & Dining',
      caption: 'Seasonal Cambodian fare and local roast coffee in an intimate courtyard setting.',
      asset: diningAsset,
      fallbackSrc: '/images/luma-haven/facilities/dining.jpg',
    },
    {
      id: 'gym',
      title: 'Movement & Wellness Studio',
      locationName: 'Wellness Center',
      caption: 'Dedicated equipment for morning stretching, light cardio, and restorative exercise.',
      asset: gymAsset,
      fallbackSrc: '/images/luma-haven/facilities/gym.jpg',
    },
    {
      id: 'lounge',
      title: 'Mezzanine Reading Lounge',
      locationName: 'Guest Library Lounge',
      caption: 'A quiet sanctuary with literature and deep armchairs for mindful downtime.',
      asset: loungeAsset,
      fallbackSrc: '/images/luma-haven/facilities/lounge.jpg',
    },
    {
      id: 'details',
      title: 'Thoughtful Guest Touches',
      locationName: 'Guest Room Amenities',
      caption: 'Organic botanical toiletries, waffle robes, and hand-milled soaps on solid timber trays.',
      asset: detailsAsset,
      fallbackSrc: '/images/luma-haven/facilities/details.jpg',
    },
  ]
})
</script>

<template>
  <section id="experience" class="py-16 sm:py-24 border-t border-[var(--line)]" aria-labelledby="exp-heading">
    <!-- Header -->
    <div class="max-w-3xl mb-12 sm:mb-16 space-y-3">
      <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">
        The Guest Experience
      </span>
      <h2 id="exp-heading" class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
        Thoughtful amenities for real comfort<span class="text-[var(--brass)]">.</span>
      </h2>
      <p class="text-sm sm:text-base text-[var(--muted)] leading-relaxed">
        Everything you need for an easy stay, with none of the friction. Verified services grounded in our hotel operations.
      </p>
    </div>

    <!-- 4 Operational Pillars Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16 sm:mb-20">
      <div
        v-for="(item, index) in experiences"
        :key="index"
        class="card p-6 sm:p-8 rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)] space-y-4 hover:border-[var(--brass)]/50 transition-colors shadow-sm"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="w-12 h-12 rounded-xl bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center shrink-0 border border-[var(--glass-border)]">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" :d="item.icon" />
            </svg>
          </div>
          <span class="text-xs font-mono font-semibold text-[var(--muted)] px-2.5 py-1 rounded-full bg-[var(--surface-muted)]">
            0{{ index + 1 }}
          </span>
        </div>

        <div class="space-y-1">
          <h3 class="serif text-2xl font-medium text-[var(--brand-text)]">
            {{ item.title }}
          </h3>
          <p class="text-xs font-semibold text-[var(--brass)] uppercase tracking-wide">
            {{ item.subtitle }}
          </p>
        </div>

        <p class="text-sm text-[var(--muted)] leading-relaxed">
          {{ item.description }}
        </p>

        <ul class="pt-3 border-t border-[var(--line)] space-y-2 text-xs sm:text-sm text-[var(--brand-text)]">
          <li v-for="(detail, dIndex) in item.details" :key="dIndex" class="flex items-center gap-2 text-[var(--muted)]">
            <svg class="w-4 h-4 text-[var(--brass)] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
            </svg>
            <span>{{ detail }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Feature Photos & Visual Locations (Defined by Name) -->
    <div class="pt-8 border-t border-[var(--line)] space-y-8">
      <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div class="space-y-2">
          <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)]">
            Visual Locations
          </span>
          <h3 class="serif text-2xl sm:text-3xl font-medium text-[var(--brand-text)]">
            Experience our atmosphere &amp; spaces<span class="text-[var(--brass)]">.</span>
          </h3>
        </div>
        <RouterLink
          to="/spaces"
          class="text-xs sm:text-sm font-semibold text-[var(--brass)] hover:underline inline-flex items-center gap-1.5"
        >
          View all 28 hotel locations &rarr;
        </RouterLink>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-5">
        <RouterLink
          v-for="card in featureCards"
          :key="card.id"
          to="/spaces"
          class="group card rounded-2xl overflow-hidden border border-[var(--glass-border)] bg-[var(--surface-raised)] hover:border-[var(--brass)]/60 transition-all shadow-sm hover:shadow-md flex flex-col"
        >
          <div class="relative aspect-[4/3] overflow-hidden bg-[var(--deep)]">
            <img
              :src="card.asset ? card.asset.image_url : card.fallbackSrc"
              :alt="card.asset?.alt_text || card.title"
              class="w-full h-full object-cover transform transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-60 group-hover:opacity-30 transition-opacity" />

            <div class="absolute top-2.5 left-2.5 px-2 py-0.5 rounded text-[10px] font-medium bg-black/60 backdrop-blur-md text-white border border-white/20">
              Location: {{ card.locationName }}
            </div>

            <div v-if="card.asset?.source_type === 'CONCEPT'" class="absolute top-2.5 right-2.5 px-2 py-0.5 rounded text-[9px] font-semibold bg-black/60 backdrop-blur-md text-[#d9b87f] border border-[#d9b87f]/40">
              Concept
            </div>
          </div>

          <div class="p-4 space-y-1 grow flex flex-col justify-between">
            <div class="space-y-1">
              <h4 class="serif text-lg font-medium text-[var(--brand-text)] group-hover:text-[var(--brass)] transition-colors">
                {{ card.title }}
              </h4>
              <p class="text-xs text-[var(--muted)] leading-relaxed">
                {{ card.caption }}
              </p>
            </div>
            <div class="pt-2 text-[11px] font-semibold text-[var(--brass)] group-hover:translate-x-0.5 transition-transform inline-flex items-center gap-1">
              Explore location &rarr;
            </div>
          </div>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
