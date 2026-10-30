import { createRouter, createWebHistory } from 'vue-router'

const HomeView = () => import('../features/guest/HomeView.vue')
const BookingView = () => import('../features/guest/BookingView.vue')
const CheckoutView = () => import('../features/guest/CheckoutView.vue')
const VerifyView = () => import('../features/guest/VerifyView.vue')
const StaffView = () => import('../features/staff/StaffView.vue')
const AdminView = () => import('../features/admin/AdminView.vue')
const ManagerView = () => import('../features/manager/ManagerView.vue')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/booking/:id', component: BookingView },
    { path: '/checkout/:id', component: CheckoutView },
    { path: '/verify', component: VerifyView },
    { path: '/staff', component: StaffView },
    { path: '/manager', component: ManagerView },
    { path: '/admin', component: AdminView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
