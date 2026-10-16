import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

/**
 * 前端路由。
 * <p>meta.public = true 的路由无需登录（目前只有登录页）。
 * <p>其余路由都需要登录，由下面的全局守卫把关。
 * <p>注意：前端的守卫只是"体验层"的拦截（避免未登录用户看到空页面），
 * 真正的权限校验必须在后端 —— 前端拦截永远可以被绕过。
 */
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true, title: '登录' },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/Home.vue'),
      meta: { title: '首页' },
    },
    // 未匹配到的地址统一回首页
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

/**
 * 全局前置守卫。
 * <p>三种情况：
 *  1. 公开页面 —— 直接放行；
 *  2. 未登录 —— 跳转登录页，并记下原目标地址，登录成功后回到那里；
 *  3. 已登录但没有用户信息（例如刷新页面后内存状态清空）—— 先拉一次用户信息再放行。
 */
router.beforeEach(async (to) => {
  const userStore = useUserStore()

  if (to.meta.public) {
    return true
  }

  if (!userStore.isLogin) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch (e) {
      // 令牌失效或后端异常：回到登录页重新登录
      return { path: '/login' }
    }
  }

  return true
})

export default router
