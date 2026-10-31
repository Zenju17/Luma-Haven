import { createRouter, createWebHistory } from 'vue-router'

const HomeView = () => import('../features/guest/HomeView.vue')
const RoomsView = () => import('../features/guest/RoomsView.vue')
const GalleryView = () => import('../features/guest/GalleryView.vue')
const SpacesView = () => import('../features/guest/SpacesView.vue')
const BookingView = () => import('../features/guest/BookingView.vue')
const CheckoutView = () => import('../features/guest/CheckoutView.vue')
const LegalPage = () => import('../features/legal/LegalPage.vue')
const VerifyView = () => import('../features/guest/VerifyView.vue')
const StaffView = () => import('../features/staff/StaffView.vue')
const AdminView = () => import('../features/admin/AdminView.vue')
const ManagerView = () => import('../features/manager/ManagerView.vue')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/rooms', component: RoomsView },
    { path: '/gallery', component: GalleryView },
    { path: '/spaces', component: SpacesView },
    { path: '/booking/:id', component: BookingView },
    { path: '/checkout/:id', component: CheckoutView },
    { path: '/verify', component: VerifyView },
    { path: '/legal/:kind', component: LegalPage },
    { path: '/staff', component: StaffView },
    { path: '/manager', component: ManagerView },
    { path: '/admin', component: AdminView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
