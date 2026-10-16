<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

/**
 * 403 页面：已登录但当前账号没有访问该页面的权限。
 * <p>会被两个地方引导到这里：路由守卫（页面级权限不足）、
 * 以及后端返回 403 时的提示（接口级权限不足）。
 */
const router = useRouter()
const userStore = useUserStore()
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <el-result icon="warning" title="403" sub-title="当前账号没有访问该页面的权限">
        <template #extra>
          <div class="info">
            <p>当前账号：{{ userStore.userInfo?.nickname }}（{{ userStore.roleNames.join('、') }}）</p>
            <p class="hint">
              菜单与页面权限由后台的角色配置决定。若确实需要访问，请联系管理员在「角色管理」中为该角色勾选对应菜单。
            </p>
          </div>
          <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  max-width: 720px;
  margin: 60px auto;
}

.info {
  margin-bottom: 16px;
  color: #4b5563;
}

.hint {
  color: #9ca3af;
  font-size: 13px;
}
</style>
