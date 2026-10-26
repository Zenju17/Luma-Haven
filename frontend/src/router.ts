import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import BookingView from './views/BookingView.vue'
import CheckoutView from './views/CheckoutView.vue'
import VerifyView from './views/VerifyView.vue'
import StaffView from './views/StaffView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/booking/:id', name: 'booking', component: BookingView },
    { path: '/checkout/:id', name: 'checkout', component: CheckoutView },
    { path: '/verify', name: 'verify', component: VerifyView },
    { path: '/staff', name: 'staff', component: StaffView },
  ],
})
