import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import Layout from '@/layout/index.vue'

/**
 * 前端路由表。
 *
 * 设计说明（答辩可能被问到）：
 *  - **路由与组件是代码资产**，必须在前端存在，不可能由数据库凭空生成，所以路由在这里静态声明；
 *  - **能看到哪些菜单、能不能访问某个页面，由后端下发** —— 每个路由用 meta.perms 声明所需权限，
 *    守卫会拿它跟当前用户的权限列表比对，没有权限就跳 403；
 *  - 侧边栏的菜单项完全来自后端返回的菜单树，前端没有写死。
 *
 * 后续阶段的页面（内容管理、审核中心等）本阶段先用统一的占位页，避免点菜单出现空白页。
 */
const underConstruction = () => import('@/views/common/UnderConstruction.vue')

/** 生成"后续阶段实现"的占位路由 */
const todo = (path, title, perms) => ({
  path,
  component: underConstruction,
  meta: { title, perms, todo: true },
})

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/error/403.vue'),
    meta: { public: true, title: '无权限' },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '数据看板', perms: 'dashboard:view' },
      },

      // ---------- 系统管理（本阶段实现） ----------
      {
        path: 'system/user',
        name: 'SystemUser',
        component: () => import('@/views/system/user/index.vue'),
        meta: { title: '用户管理', perms: 'system:user' },
      },
      {
        path: 'system/role',
        name: 'SystemRole',
        component: () => import('@/views/system/role/index.vue'),
        meta: { title: '角色管理', perms: 'system:role' },
      },
      {
        path: 'system/menu',
        name: 'SystemMenu',
        component: () => import('@/views/system/menu/index.vue'),
        meta: { title: '菜单管理', perms: 'system:menu' },
      },

      // ---------- 内容管理（阶段 3 实现） ----------
      todo('content/article', '稿件管理', 'article:list'),
      todo('content/category', '分类管理', 'category:manage'),
      todo('content/report', '举报处理', 'report:handle'),

      // ---------- 审核中心（阶段 5～7 实现） ----------
      todo('audit/workbench', '审核工作台', 'audit:workbench'),
      todo('audit/record', '审核记录', 'audit:record'),
      todo('audit/rule', '审核规则库', 'audit:rule'),
      todo('audit/sensitive', '敏感词库', 'audit:sensitive'),

      // ---------- 平台管理与适配 ----------
      todo('platform', '平台管理', 'platform:manage'),
      todo('creator/article', '我的稿件', 'creator:article'),
      todo('creator/submit', '去投稿', 'creator:submit'),
      todo('creator/adapt', '跨平台适配', 'creator:adapt'),

      // ---------- 评测中心（阶段 8 实现） ----------
      todo('eval', '评测中心', 'eval:manage'),
    ],
  },
  // 未匹配到的地址统一回首页
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

/**
 * 全局前置守卫。
 * <p>三件事：公开页面直接放行；未登录跳登录页（记住原目标地址）；
 * 已登录但缺少该页面所需权限时跳 403 页。
 */
router.beforeEach(async (to) => {
  const userStore = useUserStore()

  if (to.meta.public) {
    return true
  }

  if (!userStore.isLogin) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 刷新页面后内存状态丢失，先拉一次用户信息
  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch (e) {
      return { path: '/login' }
    }
  }

  // 页面级权限校验
  if (to.meta.perms && !userStore.hasPermission(to.meta.perms)) {
    return { path: '/403' }
  }

  return true
})

export default router
