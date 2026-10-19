<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCaptcha } from '@/api/auth'
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

// ---------------- 注册 ----------------
const registerVisible = ref(false)
const registerRef = ref()
const registering = ref(false)
const captcha = ref(null)
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  nickname: '',
  captchaAnswer: '',
})

const registerRules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]{3,20}$/, message: '3-20 位字母、数字或下划线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d).{6,64}$/, message: '至少 6 位，且同时包含字母和数字', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  captchaAnswer: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

async function openRegister() {
  Object.assign(registerForm, {
    username: '',
    password: '',
    confirmPassword: '',
    nickname: '',
    captchaAnswer: '',
  })
  registerVisible.value = true
  registerRef.value?.clearValidate()
  await refreshCaptcha()
}

async function refreshCaptcha() {
  captcha.value = await getCaptcha()
  registerForm.captchaAnswer = ''
}

async function onRegister() {
  const valid = await registerRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  registering.value = true
  try {
    const data = await userStore.register({
      ...registerForm,
      captchaId: captcha.value?.captchaId,
    })
    ElMessage.success(`注册成功，欢迎 ${data.userInfo.nickname}`)
    registerVisible.value = false
    router.push(route.query.redirect || '/')
  } catch {
    // 验证码一次性使用：失败后必须换一题（拦截器已提示具体原因）
    await refreshCaptcha()
  } finally {
    registering.value = false
  }
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

      <div class="register-entry">
        <span>还没有账号？</span>
        <el-link type="primary" :underline="false" @click="openRegister">立即注册</el-link>
      </div>

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

    <el-dialog v-model="registerVisible" title="注册创作者账号" width="480px">
      <el-alert type="info" :closable="false" class="register-tip">
        <template #title>
          注册后默认获得「创作者」角色；管理员与审核员账号只能由管理员创建。
        </template>
      </el-alert>

      <el-form ref="registerRef" :model="registerForm" :rules="registerRules" label-width="86px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="registerForm.username" placeholder="3-20 位字母、数字或下划线" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="registerForm.nickname" placeholder="界面上显示的名字" maxlength="50" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="registerForm.password" type="password" show-password placeholder="至少 6 位，含字母和数字" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="registerForm.confirmPassword" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>
        <el-form-item label="验证码" prop="captchaAnswer">
          <div class="captcha-row">
            <span class="captcha-q">{{ captcha?.question || '加载中…' }}</span>
            <el-input v-model="registerForm.captchaAnswer" placeholder="答案" style="width: 110px" />
            <el-button link type="primary" @click="refreshCaptcha">换一题</el-button>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="registerVisible = false">取消</el-button>
        <el-button type="primary" :loading="registering" @click="onRegister">注册并登录</el-button>
      </template>
    </el-dialog>
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

.register-entry {
  text-align: center;
  color: #6b7280;
  font-size: 13px;
  margin-bottom: 4px;
}

.register-tip {
  margin-bottom: 14px;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.captcha-q {
  min-width: 100px;
  color: #374151;
  font-weight: 600;
  letter-spacing: 1px;
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
