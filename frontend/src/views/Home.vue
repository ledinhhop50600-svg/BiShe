<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

/**
 * 阶段 1 的首页：用来验证"登录成功后能拿到自己的角色、菜单和权限"。
 * <p>阶段 2 会把它替换为真正的后台布局（左侧动态菜单 + 顶部栏 + 内容区），
 * 那时这里的菜单树会直接变成侧边栏的导航数据。
 */
const router = useRouter()
const userStore = useUserStore()

const nickname = computed(() => userStore.userInfo?.nickname || '')
const username = computed(() => userStore.userInfo?.username || '')
const roleNames = computed(() => userStore.roleNames)
const permissions = computed(() => userStore.permissions)
const menus = computed(() => userStore.menus)

// el-tree 默认按 label / children 取字段，这里告诉它我们的字段叫 menuName
const treeProps = { label: 'menuName', children: 'children' }

async function onLogout() {
  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="header">
          <div>
            <span class="welcome">你好，{{ nickname }}</span>
            <el-tag v-for="r in roleNames" :key="r" size="small" class="role-tag">{{ r }}</el-tag>
          </div>
          <el-button size="small" @click="onLogout">退出登录</el-button>
        </div>
      </template>

      <el-alert type="success" :closable="false" show-icon class="tip">
        <template #title>
          登录认证已打通：本页的角色、菜单、权限全部由后端按你的账号返回，不是前端写死的。
        </template>
      </el-alert>

      <el-descriptions :column="2" border class="block">
        <el-descriptions-item label="账号">{{ username }}</el-descriptions-item>
        <el-descriptions-item label="昵称">{{ nickname }}</el-descriptions-item>
        <el-descriptions-item label="角色标识">
          <el-tag v-for="k in userStore.roleKeys" :key="k" size="small" type="info" class="role-tag">
            {{ k }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="权限数量">{{ permissions.length }} 项</el-descriptions-item>
      </el-descriptions>

      <el-row :gutter="16" class="block">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><b>我的菜单（后端动态下发）</b></template>
            <el-tree :data="menus" :props="treeProps" default-expand-all :expand-on-click-node="false" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><b>我的权限标识</b></template>
            <div class="perm-list">
              <el-tag v-for="p in permissions" :key="p" size="small" class="perm-tag">{{ p }}</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-alert type="info" :closable="false" class="block">
        <template #title>
          阶段 2 会把这些菜单变成左侧真实导航，并做出用户 / 角色 / 菜单三个管理页面。
        </template>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  max-width: 1080px;
  margin: 40px auto;
  padding: 0 16px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.welcome {
  font-size: 18px;
  font-weight: 600;
  margin-right: 10px;
}

.role-tag {
  margin-right: 6px;
}

.block {
  margin-top: 16px;
}

.perm-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.perm-tag {
  font-family: monospace;
}
</style>
