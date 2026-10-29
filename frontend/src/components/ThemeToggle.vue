<script setup lang="ts">
import { ref, watchEffect } from 'vue'

type Theme = 'light' | 'dark' | 'auto'

const stored = localStorage.getItem('lh-theme') as Theme | null
const preference = ref<Theme>(stored ?? 'auto')
const isDark = ref(false)

const mq = window.matchMedia('(prefers-color-scheme: dark)')

function apply() {
  const dark = preference.value === 'dark' || (preference.value === 'auto' && mq.matches)
  isDark.value = dark
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.classList.toggle('auto-theme', preference.value === 'auto')
}

watchEffect(apply)
mq.addEventListener('change', apply)

function toggle() {
  preference.value = isDark.value ? 'light' : 'dark'
  localStorage.setItem('lh-theme', preference.value)
}
</script>

<template>
  <button type="button" class="theme-toggle" :aria-label="isDark ? 'Switch to light theme' : 'Switch to dark theme'" @click="toggle">
    <svg v-if="isDark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
    <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
  </button>
</template>
