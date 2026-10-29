<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createPlatform, deletePlatform, listPlatforms, updatePlatform } from '@/api/platform'

/**
 * 目标平台管理（管理员）：维护各平台的格式约束与风格要求。
 * <p>这些数据在阶段 5/6 会被智能体用来做"按平台规则审核"与"跨平台适配"，
 * 所以平台标识（platformKey）是契约的一部分，改动会影响智能体，需要谨慎。
 */
const loading = ref(false)
const list = ref([])

const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  platformKey: '',
  platformName: '',
  titleMaxLen: 30,
  contentMaxLen: 1000,
  tagRule: '',
  styleDesc: '',
  sort: 10,
  status: 1,
})
const rules = {
  platformKey: [
    { required: true, message: '请输入平台标识', trigger: 'blur' },
    { pattern: /^[a-z0-9_]+$/, message: '只用小写字母、数字和下划线', trigger: 'blur' },
  ],
  platformName: [{ required: true, message: '请输入平台名称', trigger: 'blur' }],
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    list.value = await listPlatforms()
  } finally {
    loading.value = false
  }
}

function openForm(row) {
  Object.assign(
    form,
    row
      ? { ...row }
      : {
          id: null,
          platformKey: '',
          platformName: '',
          titleMaxLen: 30,
          contentMaxLen: 1000,
          tagRule: '',
          styleDesc: '',
          sort: 10,
          status: 1,
        }
  )
  dialogVisible.value = true
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (form.id) {
    await updatePlatform(form)
    ElMessage.success('修改成功')
  } else {
    await createPlatform(form)
    ElMessage.success('新增成功')
  }
  dialogVisible.value = false
  await load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除平台「${row.platformName}」吗？「本平台」不可删除。`, '提示', { type: 'warning' })
  await deletePlatform(row.id)
  ElMessage.success('删除成功')
  await load()
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>目标平台清单</b>
          <el-button v-perm="'platform:manage'" type="primary" size="small" @click="openForm(null)">新增平台</el-button>
        </div>
      </template>

      <el-alert type="warning" :closable="false" class="tip">
        <template #title>
          格式约束数值应以各平台公开的创作规范为准。当前数值为常用参考值，正式做适配前需要逐个核对。
        </template>
      </el-alert>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="platformName" label="平台" width="140" />
        <el-table-column prop="platformKey" label="标识" width="130" />
        <el-table-column prop="titleMaxLen" label="标题上限" width="100" />
        <el-table-column prop="contentMaxLen" label="正文上限" width="100" />
        <el-table-column prop="tagRule" label="话题标签规则" min-width="180" show-overflow-tooltip />
        <el-table-column prop="styleDesc" label="内容风格" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button v-perm="'platform:manage'" link type="primary" @click="openForm(row)">编辑</el-button>
            <el-button v-perm="'platform:manage'" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑平台' : '新增平台'" width="620px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="平台标识" prop="platformKey">
              <el-input v-model="form.platformKey" placeholder="如 xiaohongshu" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="平台名称" prop="platformName">
              <el-input v-model="form.platformName" placeholder="如 小红书" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="标题字数上限">
              <el-input-number v-model="form.titleMaxLen" :min="0" :max="500" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="正文字数上限">
              <el-input-number v-model="form.contentMaxLen" :min="0" :max="100000" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="话题标签规则">
          <el-input v-model="form.tagRule" placeholder="如 以 # 开头，建议 3-5 个" />
        </el-form-item>
        <el-form-item label="内容风格">
          <el-input v-model="form.styleDesc" type="textarea" :rows="2" placeholder="如 口语化、亲切，可适度使用 emoji" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.sort" :min="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-radio-group v-model="form.status">
                <el-radio :value="1">启用</el-radio>
                <el-radio :value="0">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
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
