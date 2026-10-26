import { createApp } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './app/App.vue'
import { router } from './app/router'
import { queryClient } from './services/api'
import './style.css'

createApp(App).use(router).use(VueQueryPlugin, { queryClient }).mount('#app')
