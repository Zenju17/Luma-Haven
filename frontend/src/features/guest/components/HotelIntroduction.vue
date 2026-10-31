<script setup lang="ts">
</script>

<template>
  <section id="about" class="py-16 sm:py-24 border-t border-[var(--line)]" aria-labelledby="intro-heading">
    <div class="max-w-4xl mx-auto text-center space-y-6">
      <span class="text-xs font-semibold uppercase tracking-widest text-[var(--brass)]">
        The Philosophy of Luma Haven
      </span>

      <h2 id="intro-heading" class="serif text-3xl sm:text-4xl lg:text-5xl font-normal text-[var(--brand-text)] leading-tight">
        A place designed for rest, <br class="hidden sm:inline" />
        <span class="italic text-[var(--brass)]">not rush.</span>
      </h2>

      <p class="text-base sm:text-lg text-[var(--muted)] leading-relaxed font-normal pt-2">
        In the heart of Phnom Penh, Luma Haven is built around a simple idea: that travel should restore you, not drain you. We chose mindful acoustic insulation over hollow glitz, shaded garden courtyards over cavernous lobbies, and personal human reception over automated kiosks.
      </p>

      <p class="text-sm sm:text-base text-[var(--muted)] leading-relaxed max-w-2xl mx-auto">
        When you arrive at 14:00, our front desk team hands you a solid brass room key stamped with your room number. No plastic card to demagnetize, no app to install—just an authentic sanctuary where you can truly pause.
      </p>
    </div>

    <!-- 3 Ethos Pillars -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 mt-12 sm:mt-16">
      <div class="card p-6 sm:p-8 rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)]/70 space-y-3">
        <div class="w-12 h-12 rounded-xl bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center font-serif text-xl font-semibold">
          01
        </div>
        <h3 class="serif text-xl font-medium text-[var(--brand-text)]">
          Mindful Architecture
        </h3>
        <p class="text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
          Natural ventilation, private garden pockets, and acoustic dampening to shield you from the vibrant pulse of the city outside.
        </p>
      </div>

      <div class="card p-6 sm:p-8 rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)]/70 space-y-3">
        <div class="w-12 h-12 rounded-xl bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center font-serif text-xl font-semibold">
          02
        </div>
        <h3 class="serif text-xl font-medium text-[var(--brand-text)]">
          The Weight of Brass
        </h3>
        <p class="text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
          Physical keys kept in pigeonholes behind reception. Hand-forged brass fobs that remind you where you belong for the night.
        </p>
      </div>

      <div class="card p-6 sm:p-8 rounded-2xl border border-[var(--glass-border)] bg-[var(--surface-raised)]/70 space-y-3">
        <div class="w-12 h-12 rounded-xl bg-[var(--surface-muted)] text-[var(--brass)] flex items-center justify-center font-serif text-xl font-semibold">
          03
        </div>
        <h3 class="serif text-xl font-medium text-[var(--brand-text)]">
          Attentive, Calm Service
        </h3>
        <p class="text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
          From in-room service requests to seamless guest verification, our staff knows you by name and respects your time and peace.
        </p>
      </div>
    </div>
  </section>
</template>
