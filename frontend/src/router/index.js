import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/customer',
    name: 'Customer',
    component: () => import('../views/Customer.vue'),
    meta: { role: 'customer' },
  },
  {
    path: '/merchant',
    name: 'Merchant',
    component: () => import('../views/Merchant.vue'),
    meta: { role: 'merchant' },
  },
  {
    path: '/courier',
    name: 'Courier',
    component: () => import('../views/Courier.vue'),
    meta: { role: 'courier' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── 路由守卫：角色校验 + 未登录重定向 ──────────────────
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.role) {
    if (!auth.token) {
      // 未登录 → 回登录页
      return next({ name: 'Login', query: { redirect: to.path } })
    }
    if (auth.role !== to.meta.role) {
      // 角色不匹配 → 回对应工作台
      const roleRoutes = { customer: '/customer', merchant: '/merchant', courier: '/courier' }
      return next(roleRoutes[auth.role] || '/')
    }
  }

  // 已登录访问登录页 → 自动跳转到对应工作台
  if (to.name === 'Login' && auth.token) {
    const roleRoutes = { customer: '/customer', merchant: '/merchant', courier: '/courier' }
    return next(roleRoutes[auth.role] || '/')
  }

  next()
})

export default router
