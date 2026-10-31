import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const proxyTarget = process.env.API_PROXY_TARGET || 'http://backend:8000'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': proxyTarget,
      '/media': proxyTarget,
    },
  },
})
