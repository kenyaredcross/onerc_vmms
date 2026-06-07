import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  // Public
  { path: '/login',          name: 'Login',           component: () => import('../pages/LoginPage.vue'),          meta: { public: true, title: 'Sign In' } },
  { path: '/register',       name: 'Register',        component: () => import('../pages/RegisterPage.vue'),       meta: { public: true, title: 'Register' } },
  { path: '/verify/:volId',  name: 'Verify',          component: () => import('../pages/VerifyPage.vue'),         meta: { public: true, title: 'Verify Member' } },
  // Protected
  { path: '/dashboard',      name: 'Dashboard',       component: () => import('../pages/DashboardPage.vue'),      meta: { title: 'Dashboard' } },
  { path: '/profile',        name: 'Profile',         component: () => import('../pages/ProfilePage.vue'),        meta: { title: 'My Profile' } },
  { path: '/deployments',    name: 'Deployments',     component: () => import('../pages/DeploymentsPage.vue'),    meta: { title: 'Deployments' } },
  { path: '/deployments/:id',name: 'DeploymentDetail',component: () => import('../pages/DeploymentDetailPage.vue'),meta: { title: 'Deployment Detail' } },
  { path: '/membership',     name: 'Membership',      component: () => import('../pages/MembershipPage.vue'),     meta: { title: 'Membership' } },
  // Catch-all
  { path: '/',               redirect: '/dashboard' },
  { path: '/:pathMatch(.*)*',name: 'NotFound',        component: () => import('../pages/NotFoundPage.vue'),       meta: { public: true, title: '404' } },
]

const router = createRouter({
  history: createWebHistory('/vmms/'),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async to => {
  const auth = useAuthStore()
  if (auth.checking) await auth.check()

  const isPublic = !!to.meta.public
  if (!isPublic && !auth.isLoggedIn) return { name: 'Login', query: { redirect: to.fullPath } }
  if (to.name === 'Login' && auth.isLoggedIn) return { name: 'Dashboard' }
})

export default router
