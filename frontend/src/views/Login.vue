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

async function onSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  loading.value = true
  try {
    const data = await userStore.login(form)
    ElMessage.success(`欢迎回来，${data.userInfo.nickname}`)
    router.push(route.query.redirect || '/')
  } finally {
    loading.value = false
  }
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
    await refreshCaptcha()
  } finally {
    registering.value = false
  }
}

const demoAccounts = [
  { username: 'admin', role: '超级管理员', desc: '管用户、角色、菜单、规则库、平台清单' },
  { username: 'reviewer', role: '审核员', desc: '处理待审稿件、复核改判、处理举报' },
  { username: 'creator', role: '创作者', desc: '投稿、查看审核反馈、做跨平台适配' },
  { username: 'creator3', role: '创作者', desc: '持续更新型账号，看板有 8 篇发布记录' },
  { username: 'creator4', role: '创作者', desc: '阶段更新型账号，4 篇集中发布' },
  { username: 'creator5', role: '创作者', desc: '新账号，发布记录较少' },
]

function fillDemo(account) {
  form.username = account.username
  form.password = '123456'
}
</script>

<template>
  <div class="login-page">
    <div class="login-shell">
      <!-- 左侧：品牌与三句价值主张 -->
      <aside class="brand-panel">
        <div class="brand-top">
          <span class="brand-mark">自</span>
          <span class="brand-kicker">CONTENT STUDIO</span>
        </div>

        <div class="brand-copy">
          <h1>让内容创作<br />更有章法</h1>
          <p>创作、审核、跨平台适配，<br />在一个安静的后台里完成。</p>
        </div>

        <ul class="brand-points">
          <li><span>01</span>AI 初判，审核员终审</li>
          <li><span>02</span>规则可追溯，改判有留痕</li>
          <li><span>03</span>一篇内容，适配多个平台</li>
        </ul>

        <div class="brand-foot">广州航海学院 · 毕业设计</div>
      </aside>

      <!-- 右侧：登录与演示账号 -->
      <section class="form-panel">
        <div class="form-head">
          <div class="form-kicker">WELCOME BACK</div>
          <h2>登录</h2>
          <p>进入你的内容工作台</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="onSubmit">
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="请输入账号" clearable>
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password>
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
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

        <div class="demo-divider"><span>演示账号 · 密码均为 123456</span></div>

        <div class="demo-list">
          <button v-for="acc in demoAccounts" :key="acc.username" class="demo-item" @click="fillDemo(acc)">
            <span class="demo-role">{{ acc.role }}</span>
            <span class="demo-main">
              <b>{{ acc.username }}</b>
              <small>{{ acc.desc }}</small>
            </span>
            <el-icon class="demo-arrow"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>
    </div>

    <!-- 注册弹窗 -->
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
  display: grid;
  place-items: center;
  padding: 32px;
  background:
    radial-gradient(900px 500px at 12% 0%, #fffaf1 0%, transparent 55%),
    radial-gradient(700px 420px at 100% 100%, #e8f0ec 0%, transparent 50%),
    var(--app-bg);
}

.login-shell {
  width: min(1040px, 100%);
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  border-radius: 26px;
  overflow: hidden;
  background: var(--app-surface);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 34px 90px rgba(28, 45, 43, 0.2);
}

.brand-panel {
  position: relative;
  padding: 44px 44px 38px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, #1d3531 0%, #162825 55%, #1b302d 100%);
  color: #f4e8d6;
  overflow: hidden;
}

.brand-panel::before {
  content: '';
  position: absolute;
  top: -120px;
  right: -90px;
  width: 280px;
  height: 280px;
  border: 1px solid rgba(176, 138, 90, 0.28);
  border-radius: 50%;
}

.brand-panel::after {
  content: '';
  position: absolute;
  right: -60px;
  bottom: -110px;
  width: 300px;
  height: 300px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 50%;
}

.brand-top {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  z-index: 1;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #c7a578, #9c7848);
  color: #1b302d;
  font-family: var(--app-serif);
  font-size: 22px;
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(176, 138, 90, 0.3);
}

.brand-kicker,
.form-kicker {
  font-size: 9px;
  letter-spacing: 0.26em;
  color: #a9bcb5;
}

.brand-copy {
  position: relative;
  z-index: 1;
  margin-top: 62px;
}

.brand-copy h1 {
  margin: 0 0 16px;
  font-family: var(--app-serif);
  font-size: 38px;
  line-height: 1.32;
  font-weight: 600;
  color: #f8ecda;
  letter-spacing: 0.03em;
}

.brand-copy p {
  margin: 0;
  color: #b7c8c2;
  font-size: 13.5px;
  line-height: 1.95;
}

.brand-points {
  position: relative;
  z-index: 1;
  margin: 42px 0 0;
  padding: 0;
  list-style: none;
}

.brand-points li {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 13px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13.5px;
  color: #dce6e1;
}

.brand-points span {
  font-family: var(--app-serif);
  font-size: 12px;
  color: #b08a5a;
  letter-spacing: 0.08em;
}

.brand-foot {
  position: relative;
  z-index: 1;
  margin-top: auto;
  padding-top: 40px;
  color: #7f948e;
  font-size: 11px;
  letter-spacing: 0.12em;
}

.form-panel {
  padding: 44px 46px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: var(--app-surface);
}

.form-head {
  margin-bottom: 22px;
}

.form-head h2 {
  margin: 8px 0 2px;
  font-family: var(--app-serif);
  font-size: 30px;
  font-weight: 600;
  color: var(--app-ink);
}

.form-head p {
  margin: 0;
  color: var(--app-muted);
  font-size: 13px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  letter-spacing: 0.12em;
}

.register-entry {
  text-align: center;
  color: var(--app-muted);
  font-size: 12.5px;
  margin-top: 2px;
}

.demo-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0 12px;
  color: #a2988a;
  font-size: 10px;
  letter-spacing: 0.14em;
  white-space: nowrap;
}

.demo-divider::before,
.demo-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: var(--app-line);
}

.demo-list {
  max-height: 286px;
  overflow-y: auto;
  padding-right: 4px;

  display: flex;
  flex-direction: column;
  gap: 8px;
}

.demo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid var(--app-line);
  border-radius: 11px;
  background: #fffdf9;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: all 0.16s ease;
}

.demo-item:hover {
  border-color: var(--app-gold);
  background: #fdf8ef;
  transform: translateY(-1px);
}

.demo-role {
  flex-shrink: 0;
  min-width: 58px;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--app-gold-soft);
  color: #8a6a42;
  font-size: 10.5px;
  text-align: center;
}

.demo-main {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}

.demo-main b {
  font-size: 12.5px;
  color: var(--app-ink);
  font-weight: 600;
  letter-spacing: 0.03em;
}

.demo-main small {
  color: #a2988a;
  font-size: 10.5px;
}

.demo-arrow {
  margin-left: auto;
  color: #c3b6a5;
  font-size: 13px;
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
  color: var(--app-ink);
  font-weight: 600;
  letter-spacing: 1px;
}

@media (max-width: 900px) {
  .login-page {
    padding: 18px;
  }

  .login-shell {
    grid-template-columns: 1fr;
    width: min(480px, 100%);
  }

  .brand-panel {
    display: none;
  }

  .form-panel {
    padding: 32px 26px;
  }
}
</style>
