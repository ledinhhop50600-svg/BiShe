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

      // ---------- 内容管理（阶段 3 已实现） ----------
      {
        path: 'content/article',
        name: 'ContentArticle',
        component: () => import('@/views/content/article/index.vue'),
        meta: { title: '稿件管理', perms: 'article:list' },
      },
      {
        path: 'content/category',
        name: 'ContentCategory',
        component: () => import('@/views/content/category/index.vue'),
        meta: { title: '分类管理', perms: 'category:manage' },
      },
      {
        path: 'content/report',
        name: 'ContentReport',
        component: () => import('@/views/content/report/index.vue'),
        meta: { title: '举报处理', perms: 'report:handle' },
      },

      // ---------- 审核中心 ----------
      {
        path: 'audit/workbench',
        name: 'AuditWorkbench',
        component: () => import('@/views/audit/workbench/index.vue'),
        meta: { title: '审核工作台', perms: 'audit:workbench' },
      },
      {
        path: 'audit/sensitive',
        name: 'AuditSensitive',
        component: () => import('@/views/audit/sensitive/index.vue'),
        meta: { title: '敏感词库', perms: 'audit:sensitive' },
      },
      // 审核记录与规则库在阶段 5 之后实现
      todo('audit/record', '审核记录', 'audit:record'),
      todo('audit/rule', '审核规则库', 'audit:rule'),

      // ---------- 平台管理与创作中心 ----------
      {
        path: 'platform',
        name: 'Platform',
        component: () => import('@/views/platform/index.vue'),
        meta: { title: '平台管理', perms: 'platform:manage' },
      },
      {
        path: 'creator/article',
        name: 'CreatorArticle',
        component: () => import('@/views/creator/article/index.vue'),
        meta: { title: '我的稿件', perms: 'creator:article' },
      },
      {
        path: 'creator/submit',
        name: 'CreatorSubmit',
        component: () => import('@/views/creator/submit/index.vue'),
        meta: { title: '去投稿', perms: 'creator:submit' },
      },
      {
        path: 'creator/plaza',
        name: 'CreatorPlaza',
        component: () => import('@/views/creator/plaza/index.vue'),
        meta: { title: '内容广场', perms: 'creator:plaza' },
      },
      {
        path: 'creator/adapt',
        name: 'CreatorAdapt',
        component: () => import('@/views/creator/adapt/index.vue'),
        meta: { title: '跨平台适配', perms: 'creator:adapt' },
      },

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
