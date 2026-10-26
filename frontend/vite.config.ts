import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')

  return {
    plugins: [vue(), tailwindcss()],
    server: {
      proxy: {
        // Compose uses the backend service name; local development can override
        // this with VITE_API_PROXY_TARGET=http://127.0.0.1:8000.
        '/api': env.VITE_API_PROXY_TARGET || 'http://backend:8000',
      },
    },
  }
})
