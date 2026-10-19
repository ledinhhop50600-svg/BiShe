<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword, getProfile, updateProfile } from '@/api/profile'
import { useUserStore } from '@/stores/user'

/**
 * 个人中心：所有登录用户可用。
 * <p>账号名不可修改（登录凭据 + 历史记录里的身份标识）；昵称/邮箱/手机号可改。
 * <p>修改密码必须验证原密码；改完由后端注销当前令牌，前端清本地状态并回登录页。
 */
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const saving = ref(false)
const changing = ref(false)

const info = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  roles: [],
  createTime: '',
})

const infoRef = ref()
const pwdRef = ref()
const pwd = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

const infoRules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  phone: [{ pattern: /^$|^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }],
}

const pwdRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d).{6,64}$/, message: '至少 6 位，且同时包含字母和数字', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwd.newPassword) {
          callback(new Error('两次输入的新密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    Object.assign(info, await getProfile())
  } finally {
    loading.value = false
  }
}

async function saveInfo() {
  const valid = await infoRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  saving.value = true
  try {
    await updateProfile({
      nickname: info.nickname,
      email: info.email,
      phone: info.phone,
    })
    ElMessage.success('资料已更新')
    await userStore.fetchUserInfo()
    await load()
  } finally {
    saving.value = false
  }
}

async function savePassword() {
  const valid = await pwdRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  changing.value = true
  try {
    await changePassword(pwd)
    ElMessage.success('密码已修改，请使用新密码重新登录')
    // 后端已注销当前令牌，这里只清本地状态，避免再调登出接口报错
    userStore.logoutLocal()
    router.push('/login')
  } finally {
    changing.value = false
  }
}

function fmtTime(t) {
  return (t || '').replace('T', ' ').slice(0, 19)
}
</script>

<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <b>基本资料</b>
              <span class="hint">账号名注册后不可修改</span>
            </div>
          </template>

          <el-form ref="infoRef" :model="info" :rules="infoRules" label-width="90px">
            <el-form-item label="账号">
              <el-input :model-value="info.username" disabled />
            </el-form-item>
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="info.nickname" maxlength="50" show-word-limit />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="info.email" placeholder="选填" maxlength="100" />
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="info.phone" placeholder="选填" maxlength="11" />
            </el-form-item>
            <el-form-item label="角色">
              <el-tag v-for="r in info.roles" :key="r" size="small" class="tag">{{ r }}</el-tag>
            </el-form-item>
            <el-form-item label="注册时间">
              <span class="muted">{{ fmtTime(info.createTime) || '-' }}</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveInfo">保存资料</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <b>修改密码</b>
              <span class="hint">修改后需要重新登录</span>
            </div>
          </template>

          <el-form ref="pwdRef" :model="pwd" :rules="pwdRules" label-width="90px">
            <el-form-item label="原密码" prop="oldPassword">
              <el-input v-model="pwd.oldPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input v-model="pwd.newPassword" type="password" show-password placeholder="至少 6 位，含字母和数字" />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirmPassword">
              <el-input v-model="pwd.confirmPassword" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="changing" @click="savePassword">修改密码</el-button>
            </el-form-item>
          </el-form>

          <el-alert type="info" :closable="false">
            <template #title>
              本系统没有接入短信/邮件服务，忘记密码请联系管理员重置。
            </template>
          </el-alert>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.hint {
  color: #9ca3af;
  font-size: 12px;
}

.tag {
  margin-right: 6px;
}

.muted {
  color: #6b7280;
}
</style>
