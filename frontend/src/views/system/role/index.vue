<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createRole, deleteRole, getRoleMenuIds, pageRoles, updateRole } from '@/api/role'
import { getMenuTree } from '@/api/menu'

/**
 * 角色管理页。
 * <p>功能：角色的增删改，以及**给角色分配菜单与按钮权限** —— 这是动态菜单的源头。
 * <p>分配权限的实现：弹窗里是一棵带复选框的菜单树，勾选后把选了哪些菜单 id 存进 sys_role_menu。
 * 该角色的用户下次登录时，看到的菜单就变了（刷新页面即可生效，不用改代码、不用重启）。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 10, roleName: '' })

const dialogVisible = ref(false)
const dialogTitle = ref('新增角色')
const formRef = ref()
const form = reactive({ id: null, roleName: '', roleKey: '', description: '', sort: 1, status: 1 })

const rules = {
  roleName: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  roleKey: [
    { required: true, message: '请输入角色标识', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含字母、数字和下划线', trigger: 'blur' },
  ],
  sort: [{ required: true, message: '请填写排序号', trigger: 'blur' }],
}

// 分配权限弹窗
const permVisible = ref(false)
const permRole = ref(null)
const menuTree = ref([])
const treeRef = ref()
const pendingChecked = ref([])
const treeKey = ref(0)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await pageRoles(query)
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

function openCreate() {
  Object.assign(form, { id: null, roleName: '', roleKey: '', description: '', sort: 1, status: 1 })
  dialogTitle.value = '新增角色'
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, row)
  dialogTitle.value = '编辑角色'
  dialogVisible.value = true
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (form.id) {
    await updateRole(form)
    ElMessage.success('修改成功')
  } else {
    await createRole(form)
    ElMessage.success('新增成功')
  }
  dialogVisible.value = false
  await load()
}

async function openPermission(row) {
  permRole.value = row
  if (menuTree.value.length === 0) {
    menuTree.value = await getMenuTree()
  }
  // 取该角色已有的菜单 id，作为树的初始勾选状态（default-checked-keys）
  pendingChecked.value = await getRoleMenuIds(row.id)
  // 关键：改变 key 让 el-tree 重新创建。因为 default-checked-keys 只在创建时生效，
  // 若复用同一个树实例，切换角色时勾选状态不会更新（早期版本就踩过这个坑：
  // 弹窗打开时勾选是空的，管理员一保存就把该角色的权限清空了）。
  treeKey.value += 1
  permVisible.value = true
}

async function savePermission() {
  // 关键细节：除了勾选的节点，还要把"半选"的父节点一起保存。
  // 否则父级目录不会被记录为该角色的菜单，重新登录后侧边栏就没有这个目录了。
  const checked = treeRef.value.getCheckedKeys()
  const halfChecked = treeRef.value.getHalfCheckedKeys()
  const menuIds = [...new Set([...checked, ...halfChecked])]

  await updateRole({
    id: permRole.value.id,
    roleName: permRole.value.roleName,
    roleKey: permRole.value.roleKey,
    description: permRole.value.description,
    sort: permRole.value.sort,
    status: permRole.value.status,
    menuIds,
  })
  ElMessage.success('权限已保存，该角色的用户重新登录后生效')
  permVisible.value = false
  await load()
}

async function onDelete(row) {
  await ElMessageBox.confirm(
    `确定删除角色「${row.roleName}」吗？若该角色下还有用户，系统会拒绝删除。`,
    '提示',
    { type: 'warning' }
  )
  await deleteRole(row.id)
  ElMessage.success('删除成功')
  await load()
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="角色名称">
          <el-input v-model="query.roleName" placeholder="模糊搜索" clearable style="width: 180px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>角色列表</b>
          <el-button v-perm="'system:role'" type="primary" size="small" @click="openCreate">新增角色</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="roleName" label="角色名称" width="140" />
        <el-table-column prop="roleKey" label="角色标识" width="140" />
        <el-table-column prop="description" label="说明" min-width="260" show-overflow-tooltip />
        <el-table-column prop="sort" label="排序" width="80" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button v-perm="'system:role'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:role'" link type="success" @click="openPermission(row)">分配权限</el-button>
            <el-button v-perm="'system:role'" link type="danger" @click="onDelete(row)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="角色名称" prop="roleName">
          <el-input v-model="form.roleName" placeholder="如：审核员" />
        </el-form-item>
        <el-form-item label="角色标识" prop="roleKey">
          <el-input v-model="form.roleKey" placeholder="程序判断用，如 reviewer" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="permVisible" :title="`分配权限：${permRole?.roleName || ''}`" width="560px">
      <el-alert type="info" :closable="false" class="perm-tip">
        <template #title>
          勾选该角色可以访问的菜单；勾选到按钮级别时，页面上的对应按钮才会显示。保存后该角色用户重新登录生效。
        </template>
      </el-alert>
      <el-tree
        :key="treeKey"
        ref="treeRef"
        :data="menuTree"
        :props="{ label: 'menuName', children: 'children' }"
        node-key="id"
        show-checkbox
        default-expand-all
        :default-checked-keys="pendingChecked"
        class="perm-tree"
      />
      <template #footer>
        <el-button @click="permVisible = false">取消</el-button>
        <el-button type="primary" @click="savePermission">保存</el-button>
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

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.perm-tip {
  margin-bottom: 12px;
}

.perm-tree {
  max-height: 420px;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 8px;
}
</style>
