<script setup lang="ts">
</script>

<template>
  <section id="location" class="py-16 sm:py-24 border-t border-[var(--line)]" aria-labelledby="location-heading">
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
      <!-- Left Column: Details & Practical Info (7 cols) -->
      <div class="lg:col-span-7 space-y-8">
        <div class="space-y-3">
          <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">
            Location &amp; Practical Details
          </span>
          <h2 id="location-heading" class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
            A quiet sanctuary in Phnom Penh<span class="text-[var(--brass)]">.</span>
          </h2>
          <p class="text-sm sm:text-base text-[var(--muted)] leading-relaxed">
            Nestled along a tree-lined residential lane in the historic Daun Penh district, Luma Haven is situated within gentle walking distance of cafes, independent bookshops, and cultural landmarks, while maintaining absolute acoustic seclusion inside.
          </p>
        </div>

        <!-- 2x2 Grid of Practical Policies -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="card p-5 rounded-xl border border-[var(--glass-border)] bg-[var(--surface-raised)] space-y-1.5">
            <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)] block">
              Check-in &amp; Check-out
            </span>
            <p class="serif text-lg font-medium text-[var(--brand-text)]">
              14:00 In · 12:00 Out
            </p>
            <p class="text-xs text-[var(--muted)] leading-relaxed">
              Asia/Phnom_Penh timezone. Complimentary luggage storage available at reception before or after.
            </p>
          </div>

          <div class="card p-5 rounded-xl border border-[var(--glass-border)] bg-[var(--surface-raised)] space-y-1.5">
            <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)] block">
              Restful Quiet Hours
            </span>
            <p class="serif text-lg font-medium text-[var(--brand-text)]">
              22:00 – 07:00 Daily
            </p>
            <p class="text-xs text-[var(--muted)] leading-relaxed">
              Quiet hours are gently observed throughout our guest corridors and courtyards for restorative sleep.
            </p>
          </div>

          <div class="card p-5 rounded-xl border border-[var(--glass-border)] bg-[var(--surface-raised)] space-y-1.5">
            <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)] block">
              Smoke-Free Property
            </span>
            <p class="serif text-lg font-medium text-[var(--brand-text)]">
              100% Smoke-Free
            </p>
            <p class="text-xs text-[var(--muted)] leading-relaxed">
              All guest rooms, indoor spaces, and courtyard balconies are strictly smoke-free.
            </p>
          </div>

          <div class="card p-5 rounded-xl border border-[var(--glass-border)] bg-[var(--surface-raised)] space-y-1.5">
            <span class="text-xs font-semibold uppercase tracking-wider text-[var(--brass)] block">
              Physical Key Care
            </span>
            <p class="serif text-lg font-medium text-[var(--brand-text)]">
              Key Drop at Reception
            </p>
            <p class="text-xs text-[var(--muted)] leading-relaxed">
              Leave your brass key with our front desk when heading into the city and collect it whenever you return.
            </p>
          </div>
        </div>

        <!-- Contact Links Bar -->
        <div class="pt-4 border-t border-[var(--line)] flex flex-wrap items-center gap-6 text-sm">
          <div>
            <span class="text-xs text-[var(--muted)] block">Email inquiries</span>
            <a href="mailto:hello@luma.local" class="font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors">
              hello@luma.local
            </a>
          </div>
          <div class="h-8 w-[1px] bg-[var(--line)] hidden sm:block" />
          <div>
            <span class="text-xs text-[var(--muted)] block">Front desk telephone</span>
            <a href="tel:+85500000000" class="font-medium text-[var(--brand-text)] hover:text-[var(--brass)] transition-colors">
              +855 00 000 000
            </a>
          </div>
          <div class="h-8 w-[1px] bg-[var(--line)] hidden sm:block" />
          <div>
            <span class="text-xs text-[var(--muted)] block">Physical address</span>
            <span class="font-medium text-[var(--brand-text)]">
              Daun Penh, Phnom Penh, Cambodia
            </span>
          </div>
        </div>
      </div>

      <!-- Right Column: Stylized Neighborhood Map Card (5 cols) -->
      <div class="lg:col-span-5">
        <div class="card p-6 sm:p-8 rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)] shadow-lg space-y-6">
          <div class="flex items-center justify-between border-b border-[var(--line)] pb-4">
            <div>
              <span class="serif text-xl font-medium text-[var(--brand-text)]">Neighborhood Guide</span>
              <p class="text-xs text-[var(--muted)]">Daun Penh Historical Quarter</p>
            </div>
            <span class="px-2.5 py-1 rounded-full bg-[var(--surface-muted)] text-[var(--brass)] text-xs font-semibold">
              Walkable
            </span>
          </div>

          <ul class="space-y-4 text-xs sm:text-sm">
            <li class="flex items-start gap-3">
              <span class="w-6 h-6 rounded-full bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center shrink-0 font-bold text-xs">
                1
              </span>
              <div>
                <p class="font-semibold text-[var(--brand-text)]">Street 240 Artisan Cafes</p>
                <p class="text-[var(--muted)] text-xs mt-0.5">3-minute walk · Specialty coffee, bakeries &amp; craft boutiques</p>
              </div>
            </li>

            <li class="flex items-start gap-3">
              <span class="w-6 h-6 rounded-full bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center shrink-0 font-bold text-xs">
                2
              </span>
              <div>
                <p class="font-semibold text-[var(--brand-text)]">Royal Palace &amp; Riverside</p>
                <p class="text-[var(--muted)] text-xs mt-0.5">10-minute walk · Historic gardens and riverfront breezes</p>
              </div>
            </li>

            <li class="flex items-start gap-3">
              <span class="w-6 h-6 rounded-full bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center shrink-0 font-bold text-xs">
                3
              </span>
              <div>
                <p class="font-semibold text-[var(--brand-text)]">National Museum of Cambodia</p>
                <p class="text-[var(--muted)] text-xs mt-0.5">8-minute walk · Terracotta courtyard and Khmer bronze collection</p>
              </div>
            </li>

            <li class="flex items-start gap-3">
              <span class="w-6 h-6 rounded-full bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center shrink-0 font-bold text-xs">
                4
              </span>
              <div>
                <p class="font-semibold text-[var(--brand-text)]">Phnom Penh International Airport</p>
                <p class="text-[var(--muted)] text-xs mt-0.5">35-minute drive · Airport transfer coordination upon request</p>
              </div>
            </li>
          </ul>

          <div class="pt-4 border-t border-[var(--line)]">
            <p class="text-xs text-[var(--muted)] italic">
              Need assistance finding us? Call reception at <span class="font-mono text-[var(--brand-text)] font-semibold">+855 00 000 000</span> for local directions.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
