<script setup lang="ts">
const steps = [
  {
    number: '01',
    title: 'Book Online',
    description: 'Select your stay dates and preferred room type. Instant server quotes calculate exact room rates and taxes with zero hidden surprises.',
  },
  {
    number: '02',
    title: 'Verify & Check In',
    description: 'Check in digitally anytime at My Stay. Receive a secure six-digit code by email for instant access to your reservation details.',
  },
  {
    number: '03',
    title: 'Collect Physical Key',
    description: 'Arrive at reception starting at 14:00. Our front desk team hands you your weighted brass room key and guides you to your room.',
  },
  {
    number: '04',
    title: 'Rest & Settle Out',
    description: 'Unwind in quiet comfort, submit service requests with a single tap, and enjoy a relaxed check-out until 12:00 noon on your final day.',
  },
]
</script>

<template>
  <section class="py-16 sm:py-24 border-t border-[var(--line)]" aria-labelledby="steps-heading">
    <div class="text-center max-w-2xl mx-auto mb-12 sm:mb-16 space-y-3">
      <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">
        Simple &amp; Transparent
      </span>
      <h2 id="steps-heading" class="serif text-3xl sm:text-4xl lg:text-5xl font-medium text-[var(--brand-text)]">
        How your stay works<span class="text-[var(--brass)]">.</span>
      </h2>
      <p class="text-sm sm:text-base text-[var(--muted)]">
        From selecting your dates to departing well-rested, every step is designed for ease.
      </p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 relative">
      <div
        v-for="(step, index) in steps"
        :key="step.number"
        class="card p-6 rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)] relative flex flex-col justify-between space-y-4"
      >
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="serif text-3xl font-semibold text-[var(--brass)]">
              {{ step.number }}
            </span>
            <span v-if="index < 3" class="hidden lg:block text-xs font-bold text-[var(--line)]" aria-hidden="true">
              →
            </span>
          </div>

          <h3 class="serif text-xl font-medium text-[var(--brand-text)]">
            {{ step.title }}
          </h3>

          <p class="text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
            {{ step.description }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
