<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createUser,
  deleteUser,
  getUser,
  pageUsers,
  resetUserPassword,
  updateUser,
  updateUserStatus,
} from '@/api/user'
import { listRoles } from '@/api/role'
import { useUserStore } from '@/stores/user'

/**
 * 用户管理页。
 * <p>功能：分页查询（支持按账号搜索、按状态筛选）、新增、编辑、启用/禁用、重置密码、删除。
 * <p>权限：页面上每个操作按钮都带 v-perm，没有 system:user 权限的账号既看不到按钮，
 * 直接调接口也会被后端拒绝（返回 403）。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const roles = ref([])
const userStore = useUserStore()
const currentUserId = computed(() => userStore.userInfo?.id)

const query = reactive({ pageNum: 1, pageSize: 10, username: '', status: null })

const dialogVisible = ref(false)
const dialogTitle = ref('新增用户')
const formRef = ref()
const form = reactive({
  id: null,
  username: '',
  password: '',
  nickname: '',
  email: '',
  phone: '',
  status: 1,
  remark: '',
  roleIds: [],
})

const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]{3,20}$/, message: '账号为 3-20 位字母、数字或下划线', trigger: 'blur' },
  ],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  roleIds: [{ required: true, type: 'array', min: 1, message: '请至少选择一个角色', trigger: 'change' }],
}

onMounted(async () => {
  roles.value = await listRoles()
  await load()
})

async function load() {
  loading.value = true
  try {
    const data = await pageUsers(query)
    list.value = data.records
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  query.pageNum = 1
  load()
}

function resetQuery() {
  query.username = ''
  query.status = null
  query.pageNum = 1
  load()
}

function openCreate() {
  Object.assign(form, {
    id: null,
    username: '',
    password: '',
    nickname: '',
    email: '',
    phone: '',
    status: 1,
    remark: '',
    roleIds: [],
  })
  dialogTitle.value = '新增用户'
  dialogVisible.value = true
}

async function openEdit(row) {
  // 编辑时重新拉一次详情：列表里的数据不含完整字段，且角色 id 需要单独查
  const detail = await getUser(row.id)
  Object.assign(form, { ...detail, password: '' })
  dialogTitle.value = '编辑用户'
  dialogVisible.value = true
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (form.id) {
    await updateUser(form)
    ElMessage.success('修改成功')
  } else {
    await createUser(form)
    ElMessage.success('新增成功')
  }
  dialogVisible.value = false
  await load()
}

async function onToggleStatus(row) {
  try {
    await updateUserStatus(row.id, row.status)
    ElMessage.success(row.status === 1 ? '已启用' : '已禁用')
  } catch (e) {
    // 请求失败时把开关状态改回去，避免界面与数据库不一致
    row.status = row.status === 1 ? 0 : 1
  }
}

async function onResetPassword(row) {
  const { value } = await ElMessageBox.prompt(
    `为用户「${row.nickname}」设置新密码`,
    '重置密码',
    { inputPlaceholder: '至少 6 位', inputPattern: /^.{6,}$/, inputErrorMessage: '密码至少 6 位' }
  ).catch(() => ({}))
  if (!value) {
    return
  }
  await resetUserPassword(row.id, value)
  ElMessage.success('密码已重置')
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确定删除用户「${row.nickname}」吗？`, '提示', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('删除成功')
  await load()
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="账号">
          <el-input v-model="query.username" placeholder="模糊搜索" clearable style="width: 180px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>用户列表</b>
          <el-button v-perm="'system:user'" type="primary" size="small" @click="openCreate">新增用户</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="username" label="账号" width="130" />
        <el-table-column prop="nickname" label="昵称" width="130" />
        <el-table-column label="角色" width="180">
          <template #default="{ row }">
            <el-tag v-for="name in row.roleNames" :key="name" size="small" class="tag">{{ name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              :disabled="row.id === currentUserId"
              @change="onToggleStatus(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:user'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:user'" link type="warning" @click="onResetPassword(row)">重置密码</el-button>
            <el-button v-perm="'system:user'" link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.pageNum"
        v-model:page-size="query.pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="load"
        @current-change="load"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="用于登录，3-20 位字母数字下划线" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="form.id ? '留空表示不修改密码' : '请设置初始密码（至少 6 位）'"
          />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item label="角色" prop="roleIds">
          <el-select v-model="form.roleIds" multiple placeholder="可多选" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.roleName" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status" :disabled="form.id === currentUserId">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">禁用</el-radio>
          </el-radio-group>
          <span v-if="form.id === currentUserId" class="self-hint">不能禁用当前登录账号</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-card {
  margin-top: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tag {
  margin-right: 4px;
}

.self-hint {
  margin-left: 8px;
  color: #9ca3af;
  font-size: 12px;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>
