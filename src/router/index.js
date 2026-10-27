import { createRouter, createWebHistory } from 'vue-router'
import { expireSession, isIdleExpired } from '@/utils/idleSession'

const PublicLayout = () => import('@/layouts/PublicLayout.vue')
const ConsoleLayout = () => import('@/layouts/ConsoleLayout.vue')

const routes = [
  {
    path: '/',
    component: PublicLayout,
    children: [
      { path: '', name: 'home', component: () => import('@/views/public/Home.vue') },
      { path: 'products', name: 'products', component: () => import('@/views/public/Products.vue') },
      { path: 'products/:id', name: 'product-detail', component: () => import('@/views/public/ProductDetail.vue') },
      { path: 'about', name: 'about', component: () => import('@/views/public/About.vue') },
      { path: 'help', name: 'help', component: () => import('@/views/public/Help.vue') },
    ],
  },
  { path: '/login', name: 'login', component: () => import('@/views/auth/Login.vue'), meta: { guestOnly: true } },
  {
    path: '/console/vps/:id/vnc',
    name: 'vps-vnc',
    component: () => import('@/views/console/VpsVncConsole.vue'),
    meta: { requiresAuth: true },
  },
  { path: '/register', name: 'register', component: () => import('@/views/auth/Register.vue'), meta: { guestOnly: true } },
  {
    path: '/console',
    component: ConsoleLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: { name: 'dashboard' } },
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/console/Dashboard.vue') },
      { path: 'services', name: 'services', component: () => import('@/views/console/Services.vue') },
      { path: 'orders', name: 'orders', component: () => import('@/views/console/Orders.vue') },
      { path: 'inquiries', name: 'inquiries', component: () => import('@/views/console/Inquiries.vue') },
      { path: 'tickets', name: 'tickets', component: () => import('@/views/console/Tickets.vue') },
      { path: 'bills', name: 'bills', component: () => import('@/views/console/Bills.vue') },
      { path: 'resources', name: 'resources', component: () => import('@/views/console/Resources.vue') },
      { path: 'profile', name: 'profile', component: () => import('@/views/console/Profile.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to) {
    if (to.hash) {
      return { el: to.hash, top: 72, behavior: 'smooth' }
    }
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const access = localStorage.getItem('ispweb_access')
  if (access && isIdleExpired()) {
    expireSession()
    if (to.name === 'login' && to.query.expired === '1') return true
    return { name: 'login', query: { expired: '1', redirect: to.fullPath } }
  }
  if (to.meta.requiresAuth && !access) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && access) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
