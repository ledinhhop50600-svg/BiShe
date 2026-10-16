<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import SidebarItem from './SidebarItem.vue'

/**
 * 后台主框架：左侧动态菜单 + 顶部栏 + 内容区。
 * <p>菜单数据来自登录时后端返回的菜单树（存在 Pinia 里），
 * 所以不同角色登录看到的导航不同 —— 前端没有写死任何一项菜单。
 */
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)

/** 当前高亮的菜单项：直接用当前路由地址匹配菜单的 path */
const activeMenu = computed(() => route.path)

const nickname = computed(() => userStore.userInfo?.nickname || '')
const roleNames = computed(() => userStore.roleNames)

/** 面包屑：取当前路由的标题 */
const currentTitle = computed(() => route.meta?.title || '')

/**
 * 过滤菜单：只保留 visible = 1 的；如果一个目录下的子菜单全被过滤掉了，
 * 这个目录本身也不再显示（避免点开是空的）。
 */
function filterVisible(list) {
  const result = []
  for (const menu of list) {
    if (menu.visible !== 1) {
      continue
    }
    const children = menu.children ? filterVisible(menu.children) : []
    // 目录类型若没有可见子菜单，则整项隐藏
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
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <span v-if="!isCollapse">自媒体平台管理系统</span>
        <span v-else>自</span>
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
          <el-tag v-for="r in roleNames" :key="r" size="small" type="info" class="role-tag">{{ r }}</el-tag>
          <el-dropdown>
            <span class="user-info">
              {{ nickname }}
              <el-icon><component is="ArrowDown" /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="onLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  background: #1f2937;
  transition: width 0.2s;
  overflow-x: hidden;
}

.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f8fafc;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #374151;
}

.menu {
  border-right: none;
  background: transparent;
}

.menu :deep(.el-menu-item),
.menu :deep(.el-sub-menu__title) {
  color: #cbd5e1;
}

.menu :deep(.el-menu-item:hover),
.menu :deep(.el-sub-menu__title:hover) {
  background-color: #374151;
  color: #fff;
}

.menu :deep(.el-menu-item.is-active) {
  background-color: #409eff;
  color: #fff;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  height: 56px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
  font-size: 18px;
  color: #4b5563;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-tag {
  margin-right: 0;
}

.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #374151;
  outline: none;
}

.main {
  background: #f3f4f6;
  padding: 16px;
  overflow-y: auto;
}
</style>
