<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createMenu, deleteMenu, getMenuTree, updateMenu } from '@/api/menu'

/**
 * 菜单管理页。
 * <p>这张表同时管理"界面菜单"（目录 M、菜单页面 C）和"按钮权限"（F）：
 *  - 目录：只作为分组，对应侧边栏里可展开的一级项
 *  - 菜单页面：对应一个具体页面，需要填前端路由地址与组件路径
 *  - 按钮权限：不出现在菜单里，只用于控制页面上按钮是否显示（如"改判""删除"）
 */
const loading = ref(false)
const menuTree = ref([])

const dialogVisible = ref(false)
const dialogTitle = ref('新增菜单')
const formRef = ref()
const form = reactive({
  id: null,
  parentId: 0,
  menuName: '',
  menuType: 'C',
  path: '',
  component: '',
  perms: '',
  icon: '',
  sort: 1,
  visible: 1,
  status: 1,
})

const rules = {
  menuName: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }],
  menuType: [{ required: true, message: '请选择类型', trigger: 'change' }],
  sort: [{ required: true, message: '请填写排序号', trigger: 'blur' }],
}

/** 上级菜单下拉的选项：在最前面加一个"顶级菜单"（id = 0），方便把菜单挂到根上 */
const parentOptions = computed(() => [{ id: 0, menuName: '顶级菜单', children: menuTree.value }])

const typeText = { M: '目录', C: '菜单', F: '按钮' }
const typeTag = { M: 'warning', C: 'success', F: 'info' }

onMounted(load)

async function load() {
  loading.value = true
  try {
    menuTree.value = await getMenuTree()
  } finally {
    loading.value = false
  }
}

function openCreate(parentId = 0) {
  Object.assign(form, {
    id: null,
    parentId,
    menuName: '',
    menuType: parentId === 0 ? 'M' : 'C',
    path: '',
    component: '',
    perms: '',
    icon: '',
    sort: 1,
    visible: 1,
    status: 1,
  })
  dialogTitle.value = '新增菜单'
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, row)
  dialogTitle.value = '编辑菜单'
  dialogVisible.value = true
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (form.id) {
    await updateMenu(form)
    ElMessage.success('修改成功')
  } else {
    await createMenu(form)
    ElMessage.success('新增成功')
  }
  dialogVisible.value = false
  await load()
}

async function onDelete(row) {
  await ElMessageBox.confirm(
    `确定删除「${row.menuName}」吗？若存在下级菜单或已分配给角色，系统会拒绝删除。`,
    '提示',
    { type: 'warning' }
  )
  await deleteMenu(row.id)
  ElMessage.success('删除成功')
  await load()
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>菜单与权限</b>
          <el-button v-perm="'system:menu'" type="primary" size="small" @click="openCreate(0)">新增顶级菜单</el-button>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="tip">
        <template #title>
          三种类型：目录（侧边栏分组）、菜单（具体页面）、按钮（只控制页面上按钮是否显示）。改动保存后，重新登录即可看到效果。
        </template>
      </el-alert>

      <el-table
        v-loading="loading"
        :data="menuTree"
        row-key="id"
        :tree-props="{ children: 'children' }"
        default-expand-all
        border
      >
        <el-table-column prop="menuName" label="菜单名称" min-width="200" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="typeTag[row.menuType]" size="small">{{ typeText[row.menuType] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路由地址" min-width="160" />
        <el-table-column prop="component" label="组件路径" min-width="170" />
        <el-table-column prop="perms" label="权限标识" min-width="150" />
        <el-table-column prop="icon" label="图标" width="110" />
        <el-table-column prop="sort" label="排序" width="70" />
        <el-table-column label="显示" width="70">
          <template #default="{ row }">
            <el-tag :type="row.visible === 1 ? 'success' : 'info'" size="small">
              {{ row.visible === 1 ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:menu'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-perm="'system:menu'"
              link
              type="success"
              :disabled="row.menuType === 'F'"
              @click="openCreate(row.id)"
            >
              新增下级
            </el-button>
            <el-button v-perm="'system:menu'" link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="上级菜单">
          <el-tree-select
            v-model="form.parentId"
            :data="parentOptions"
            :props="{ label: 'menuName', children: 'children' }"
            node-key="id"
            check-strictly
            default-expand-all
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="类型" prop="menuType">
          <el-radio-group v-model="form.menuType">
            <el-radio value="M">目录</el-radio>
            <el-radio value="C">菜单</el-radio>
            <el-radio value="F">按钮</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="菜单名称" prop="menuName">
          <el-input v-model="form.menuName" placeholder="界面上显示的文字" />
        </el-form-item>
        <el-form-item v-if="form.menuType !== 'F'" label="路由地址">
          <el-input v-model="form.path" placeholder="如 /system/user" />
        </el-form-item>
        <el-form-item v-if="form.menuType === 'C'" label="组件路径">
          <el-input v-model="form.component" placeholder="如 system/user（前端 views 下的路径）" />
        </el-form-item>
        <el-form-item v-if="form.menuType !== 'M'" label="权限标识">
          <el-input v-model="form.perms" placeholder="如 system:user，后端接口用它校验" />
        </el-form-item>
        <el-form-item v-if="form.menuType !== 'F'" label="图标">
          <el-input v-model="form.icon" placeholder="Element Plus 图标名，如 User" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" />
        </el-form-item>
        <el-form-item v-if="form.menuType !== 'F'" label="是否显示">
          <el-radio-group v-model="form.visible">
            <el-radio :value="1">显示</el-radio>
            <el-radio :value="0">隐藏</el-radio>
          </el-radio-group>
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
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tip {
  margin-bottom: 12px;
}
</style>
