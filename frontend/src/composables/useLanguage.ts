import { ref, watch } from 'vue'

export type Lang = 'en' | 'km'
const KEY = 'luma-lang'

function initial(): Lang {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === 'en' || saved === 'km') return saved
  } catch { /* storage unavailable */ }
  return 'en'
}

// Shared across components so the footer, legal pages and consent box stay in sync.
const lang = ref<Lang>(initial())
watch(lang, value => {
  try { localStorage.setItem(KEY, value) } catch { /* storage unavailable */ }
})

export function useLanguage() {
  return { lang }
}
