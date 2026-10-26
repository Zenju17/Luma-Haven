import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../features/guest/HomeView.vue'
import BookingView from '../features/guest/BookingView.vue'
import CheckoutView from '../features/guest/CheckoutView.vue'
import VerifyView from '../features/guest/VerifyView.vue'
import StaffView from '../features/staff/StaffView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/booking/:id', component: BookingView },
    { path: '/checkout/:id', component: CheckoutView },
    { path: '/verify', component: VerifyView },
    { path: '/staff', component: StaffView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
