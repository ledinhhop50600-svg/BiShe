<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import SidebarItem from './SidebarItem.vue'

/**
 * 后台主框架：左侧动态菜单 + 顶部栏 + 内容区。
 * <p>菜单来自后端下发的菜单树，不同角色看到的导航不同；侧边栏底部的
 * 「系统架构」是技术说明页，不属于业务菜单，所以固定放在这里。
 */
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const activeMenu = computed(() => route.path)
const nickname = computed(() => userStore.userInfo?.nickname || '')
const roleNames = computed(() => userStore.roleNames)
const currentTitle = computed(() => route.meta?.title || '')

function filterVisible(list) {
  const result = []
  for (const menu of list) {
    if (menu.visible !== 1) {
      continue
    }
    const children = menu.children ? filterVisible(menu.children) : []
    if (menu.menuType === 'M' && children.length === 0) {
      continue
    }
    result.push({ ...menu, children })
  }
  return result
}

const menus = computed(() => filterVisible(userStore.menus))

async function onLogout() {
  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside :width="isCollapse ? '68px' : '232px'" class="aside" :class="{ 'is-collapse': isCollapse }">
      <div class="logo">
        <span class="logo-mark">自</span>
        <div v-if="!isCollapse" class="logo-text">
          <span>自媒体平台</span>
          <small>CONTENT STUDIO</small>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        unique-opened
        class="menu"
      >
        <SidebarItem v-for="menu in menus" :key="menu.id" :item="menu" />
      </el-menu>

      <div class="aside-footer" @click="router.push('/architecture')">
        <el-icon><Grid /></el-icon>
        <span v-if="!isCollapse">系统架构</span>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <component :is="isCollapse ? 'Expand' : 'Fold'" />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle">{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-tag v-for="r in roleNames" :key="r" size="small" class="role-tag">{{ r }}</el-tag>
          <el-dropdown>
            <span class="user-info">
              {{ nickname }}
              <el-icon><component is="ArrowDown" /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/architecture')">系统架构</el-dropdown-item>
                <el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item>
                <el-dropdown-item divided @click="onLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #1b302d 0%, #13211f 100%);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.04);
  transition: width 0.2s ease;
  overflow: hidden;
}

.logo {
  height: 72px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.is-collapse .logo {
  justify-content: center;
  padding: 0;
}

.logo-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #c7a578, #9c7848);
  color: #1b302d;
  font-family: var(--app-serif);
  font-size: 18px;
  font-weight: 700;
  box-shadow: 0 6px 16px rgba(176, 138, 90, 0.28);
  flex-shrink: 0;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  color: #f4e8d6;
  font-family: var(--app-serif);
  font-size: 15px;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.logo-text small {
  margin-top: 4px;
  color: #8fa39c;
  font-family: var(--app-sans);
  font-size: 8px;
  letter-spacing: 0.22em;
}

.menu {
  flex: 1;
  border-right: none;
  background: transparent;
  padding: 10px 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.menu :deep(.el-menu-item),
.menu :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  margin: 3px 12px;
  border-radius: 10px;
  color: #c3d1cc;
  font-size: 13.5px;
  transition: all 0.16s ease;
}

.menu :deep(.el-menu-item:hover),
.menu :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.055);
  color: #f4e8d6;
}

.menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(176, 138, 90, 0.22), rgba(176, 138, 90, 0.05));
  color: #f8ecda;
  box-shadow: inset 3px 0 0 #b08a5a;
}

.menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #f4e8d6;
}

.menu :deep(.el-sub-menu .el-menu) {
  background: transparent;
}

.is-collapse .menu :deep(.el-menu-item),
.is-collapse .menu :deep(.el-sub-menu__title) {
  margin: 3px 8px;
}

.aside-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  color: #8fa39c;
  font-size: 12px;
  cursor: pointer;
  transition: color 0.16s ease;
}

.is-collapse .aside-footer {
  justify-content: center;
  padding: 14px 0;
}

.aside-footer:hover {
  color: #f4e8d6;
}

.header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  background: rgba(255, 253, 248, 0.78);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--app-line);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
  font-size: 18px;
  color: #6d6458;
  transition: color 0.16s ease;
}

.collapse-btn:hover {
  color: var(--app-primary);
}

.header :deep(.el-breadcrumb__inner) {
  color: var(--app-muted);
  font-weight: 400;
}

.header :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--app-ink);
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-tag {
  background: var(--app-gold-soft);
  border-color: #ead9c0;
  color: #8a6a42;
}

.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  color: #3d4745;
  font-size: 13.5px;
  font-weight: 500;
  outline: none;
  transition: color 0.16s ease;
}

.user-info:hover {
  color: var(--app-primary);
}

.main {
  padding: 22px 24px 28px;
  overflow-y: auto;
  background: transparent;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(5px);
}

.page-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .main {
    padding: 16px;
  }
}
</style>
