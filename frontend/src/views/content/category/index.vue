<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCategory,
  createTag,
  deleteCategory,
  deleteTag,
  listCategories,
  listTags,
  updateCategory,
  updateTag,
} from '@/api/category'

/**
 * 分类与标签管理（管理员）：两者同属内容分类体系，放在一个页面里。
 * <p>删除保护：分类下还有稿件时不允许删除；标签被稿件使用时删除会自动解除关联。
 */
const categories = ref([])
const tags = ref([])
const loading = ref(false)

const categoryDialog = ref(false)
const categoryFormRef = ref()
const categoryForm = reactive({ id: null, name: '', sort: 1, status: 1 })
const categoryRules = { name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }] }

const tagDialog = ref(false)
const tagFormRef = ref()
const tagForm = reactive({ id: null, name: '' })
const tagRules = { name: [{ required: true, message: '请输入标签名', trigger: 'blur' }] }

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [c, t] = await Promise.all([listCategories(), listTags()])
    categories.value = c
    tags.value = t
  } finally {
    loading.value = false
  }
}

// ---------- 分类 ----------
function openCategory(row) {
  Object.assign(categoryForm, row ? { ...row } : { id: null, name: '', sort: 1, status: 1 })
  categoryDialog.value = true
}

async function submitCategory() {
  const valid = await categoryFormRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (categoryForm.id) {
    await updateCategory(categoryForm)
    ElMessage.success('修改成功')
  } else {
    await createCategory(categoryForm)
    ElMessage.success('新增成功')
  }
  categoryDialog.value = false
  await load()
}

async function removeCategory(row) {
  await ElMessageBox.confirm(`确定删除分类「${row.name}」吗？分类下有稿件时会被拒绝。`, '提示', { type: 'warning' })
  await deleteCategory(row.id)
  ElMessage.success('删除成功')
  await load()
}

// ---------- 标签 ----------
function openTag(row) {
  Object.assign(tagForm, row ? { ...row } : { id: null, name: '' })
  tagDialog.value = true
}

async function submitTag() {
  const valid = await tagFormRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (tagForm.id) {
    await updateTag(tagForm)
    ElMessage.success('修改成功')
  } else {
    await createTag(tagForm)
    ElMessage.success('新增成功')
  }
  tagDialog.value = false
  await load()
}

async function removeTag(row) {
  await ElMessageBox.confirm(`确定删除标签「${row.name}」吗？`, '提示', { type: 'warning' })
  await deleteTag(row.id)
  ElMessage.success('删除成功')
  await load()
}
</script>

<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col :span="13">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <b>稿件分类</b>
              <el-button v-perm="'category:manage'" type="primary" size="small" @click="openCategory(null)">新增分类</el-button>
            </div>
          </template>
          <el-table :data="categories" border>
            <el-table-column prop="name" label="分类名称" />
            <el-table-column prop="sort" label="排序" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                  {{ row.status === 1 ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button v-perm="'category:manage'" link type="primary" @click="openCategory(row)">编辑</el-button>
                <el-button v-perm="'category:manage'" link type="danger" @click="removeCategory(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="11">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <b>稿件标签</b>
              <el-button v-perm="'category:manage'" type="primary" size="small" @click="openTag(null)">新增标签</el-button>
            </div>
          </template>
          <el-table :data="tags" border max-height="420">
            <el-table-column prop="name" label="标签名" />
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button v-perm="'category:manage'" link type="primary" @click="openTag(row)">编辑</el-button>
                <el-button v-perm="'category:manage'" link type="danger" @click="removeTag(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="categoryDialog" :title="categoryForm.id ? '编辑分类' : '新增分类'" width="440px">
      <el-form ref="categoryFormRef" :model="categoryForm" :rules="categoryRules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="categoryForm.name" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="categoryForm.sort" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="categoryForm.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialog = false">取消</el-button>
        <el-button type="primary" @click="submitCategory">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="tagDialog" :title="tagForm.id ? '编辑标签' : '新增标签'" width="420px">
      <el-form ref="tagFormRef" :model="tagForm" :rules="tagRules" label-width="70px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="tagForm.name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tagDialog = false">取消</el-button>
        <el-button type="primary" @click="submitTag">保存</el-button>
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
</style>
