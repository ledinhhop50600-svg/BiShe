<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

// 表单校验规则，交给 Element Plus 的 el-form 执行，不用自己写一堆 if 判断
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  loading.value = true
  try {
    const data = await userStore.login(form)
    ElMessage.success(`欢迎回来，${data.userInfo.nickname}`)
    // 登录前如果被守卫拦下过，登录后回到原来想去的页面
    router.push(route.query.redirect || '/')
  } finally {
    loading.value = false
  }
}

// 演示账号：答辩时点一下就能填入，不用手打
const demoAccounts = [
  { username: 'admin', role: '超级管理员', desc: '管用户、角色、菜单、规则库、平台清单' },
  { username: 'reviewer', role: '审核员', desc: '处理待审稿件、复核改判、处理举报' },
  { username: 'creator', role: '创作者', desc: '投稿、查看审核反馈、做跨平台适配' },
]

function fillDemo(account) {
  form.username = account.username
  form.password = '123456'
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <div class="title">
        <h2>自媒体平台管理系统</h2>
        <p class="subtitle">内容创作 · 智能审核 · 跨平台适配</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="请输入账号" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="submit-btn" :loading="loading" @click="onSubmit">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider>演示账号（密码均为 123456）</el-divider>

      <div class="demo-list">
        <div v-for="acc in demoAccounts" :key="acc.username" class="demo-item" @click="fillDemo(acc)">
          <div class="demo-head">
            <el-tag size="small">{{ acc.role }}</el-tag>
            <span class="demo-username">{{ acc.username }}</span>
          </div>
          <div class="demo-desc">{{ acc.desc }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 60%, #ecfeff 100%);
}

.login-card {
  width: 460px;
  padding: 8px 12px;
}

.title {
  text-align: center;
  margin-bottom: 24px;
}

.title h2 {
  margin: 0 0 6px;
  color: #1f2937;
}

.subtitle {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.submit-btn {
  width: 100%;
}

.demo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.demo-item {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.demo-item:hover {
  border-color: #409eff;
  background: #f5f9ff;
}

.demo-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.demo-username {
  color: #374151;
  font-family: monospace;
  font-size: 13px;
}

.demo-desc {
  margin-top: 4px;
  color: #9ca3af;
  font-size: 12px;
}
</style>
