<template>
  <div class="min-h-screen flex flex-col">
    <header class="border-b border-[#dfe7df] bg-white">
      <div class="max-w-6xl mx-auto px-5 h-20 flex items-center justify-between">
        <RouterLink to="/" class="serif text-2xl font-semibold tracking-tight text-[#175d4b]">Luma Haven<span class="text-[#c99a5a]">.</span></RouterLink>
        <nav aria-label="Main navigation" class="flex items-center gap-6 text-sm font-semibold">
          <RouterLink to="/" class="hover:text-[#317e6a]">Find a room</RouterLink>
          <RouterLink to="/verify" class="hover:text-[#317e6a]">My stay</RouterLink>
        </nav>
      </div>
    </header>
    <main class="max-w-6xl mx-auto px-5 py-10 w-full grow"><slot /></main>
    <footer class="border-t border-[#e0e8dd] p-8 text-center text-sm text-[#738279]">Luma Haven · Your place to pause · Physical keys available at reception</footer>
  </div>
</template>
