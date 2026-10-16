import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 阶段 0 的链路验证页；阶段 1 起会替换为登录页与后台各功能页面
    { path: '/', name: 'ping', component: () => import('@/views/PingTest.vue') },
  ],
})

export default router
