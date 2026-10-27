<script setup lang="ts">
defineProps<{ area: 'staff' | 'admin' }>()
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#f4f7f5]">
    <header class="bg-[#123e35] text-white">
      <div class="max-w-6xl mx-auto px-5 min-h-20 flex items-center justify-between gap-4">
        <RouterLink :to="area === 'admin' ? '/admin' : '/staff'" class="serif text-2xl font-semibold">Luma Haven<span class="text-[#d7b683]">.</span></RouterLink>
        <span class="text-xs uppercase tracking-[.2em] text-[#c0d7c9]">{{ area === 'admin' ? 'Administration console' : 'Staff operations' }}</span>
      </div>
    </header>
    <main class="max-w-6xl mx-auto px-5 py-10 w-full grow"><slot /></main>
    <footer class="border-t border-[#dfe7df] p-6 text-center text-xs text-[#738279]">Private hotel workspace · Luma Haven</footer>
  </div>
</template>
