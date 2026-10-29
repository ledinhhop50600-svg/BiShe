<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createRule, deleteRule, listAllRules, updateRule } from '@/api/rule'
import { listPlatforms } from '@/api/platform'
import { riskType } from '@/utils/articleStatus'

/**
 * 审核规则库（管理员）。
 * <p>规则是智能体判定的依据，也是答辩时“这条规则凭什么”的溯源材料。
 * 2026-10-29 起补上管理员的增删改；规则变更后下一次审核/预检立即生效（Agent 不缓存规则正文）。
 */
const loading = ref(false)
const rules = ref([])
const platforms = ref([])
const query = ref({ category: null, platform: null, keyword: '' })

const dialogVisible = ref(false)
const dialogTitle = ref('新增规则')
const formRef = ref()
const saving = ref(false)
const form = reactive(emptyForm())

const formRules = {
  ruleCode: [{ required: true, message: '请输入规则编号', trigger: 'blur' }],
  ruleName: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  category: [{ required: true, message: '请输入规则类别', trigger: 'blur' }],
  ruleContent: [{ required: true, message: '请输入规则内容', trigger: 'blur' }],
  suggestedLevel: [{ required: true, message: '请选择建议等级', trigger: 'change' }],
}

onMounted(load)

function emptyForm() {
  return {
    id: null,
    ruleCode: '',
    ruleName: '',
    category: '',
    platformId: null,
    ruleContent: '',
    source: '',
    suggestedLevel: 2,
    enabled: 1,
  }
}

async function load() {
  loading.value = true
  try {
    const [rs, ps] = await Promise.all([listAllRules(), listPlatforms()])
    rules.value = rs || []
    platforms.value = ps || []
  } finally {
    loading.value = false
  }
}

const platformNameById = computed(() =>
  Object.fromEntries(platforms.value.map((p) => [p.id, p.platformName]))
)

const categories = computed(() => [...new Set(rules.value.map((r) => r.category))])

const filtered = computed(() => {
  const kw = query.value.keyword.trim()
  return rules.value.filter((r) => {
    if (query.value.category && r.category !== query.value.category) return false
    if (query.value.platform === 'general' && r.platformId) return false
    if (query.value.platform === 'specific' && !r.platformId) return false
    if (kw && !(`${r.ruleCode} ${r.ruleName} ${r.ruleContent}`.includes(kw))) return false
    return true
  })
})

const generalCount = computed(() => rules.value.filter((r) => !r.platformId).length)
const specificCount = computed(() => rules.value.filter((r) => r.platformId).length)
const enabledCount = computed(() => rules.value.filter((r) => r.enabled === 1).length)

function platformName(r) {
  return r.platformId ? (platformNameById.value[r.platformId] || `平台 #${r.platformId}`) : '通用（所有平台）'
}

function openCreate() {
  Object.assign(form, emptyForm())
  dialogTitle.value = '新增规则'
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

function openEdit(row) {
  Object.assign(form, { ...row })
  dialogTitle.value = '编辑规则'
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  saving.value = true
  try {
    if (form.id) {
      await updateRule(form)
      ElMessage.success('规则已更新，下一次审核立即生效')
    } else {
      await createRule(form)
      ElMessage.success('规则已新增，下一次审核立即生效')
    }
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row) {
  await ElMessageBox.confirm(
    `确定删除规则「${row.ruleCode} ${row.ruleName}」吗？历史审核记录里的规则编号仍会保留。`,
    '删除规则',
    { type: 'warning', confirmButtonText: '删除' }
  )
  await deleteRule(row.id)
  ElMessage.success('已删除')
  await load()
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-row :gutter="12">
        <el-col :xs="24" :lg="6">
          <el-card shadow="hover">
            <div class="metric-label">规则总数</div>
            <div class="metric-value">{{ rules.length }}</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="6">
          <el-card shadow="hover">
            <div class="metric-label">启用中</div>
            <div class="metric-value">{{ enabledCount }}</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="6">
          <el-card shadow="hover">
            <div class="metric-label">通用规则</div>
            <div class="metric-value">{{ generalCount }}</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="6">
          <el-card shadow="hover">
            <div class="metric-label">平台专属</div>
            <div class="metric-value">{{ specificCount }}</div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>审核规则库</b>
          <div class="head-actions">
            <span class="hint">规则变更后下一次审核/预检立即生效</span>
            <el-button v-perm="'audit:rule'" type="primary" size="small" @click="openCreate">新增规则</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" @submit.prevent>
        <el-form-item label="类别">
          <el-select v-model="query.category" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用平台">
          <el-select v-model="query.platform" placeholder="全部" clearable style="width: 150px">
            <el-option label="通用规则" value="general" />
            <el-option label="平台专属" value="specific" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="编号/名称/内容" clearable style="width: 180px" />
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="filtered" border>
        <el-table-column prop="ruleCode" label="编号" width="100" />
        <el-table-column prop="ruleName" label="规则名称" width="170" show-overflow-tooltip />
        <el-table-column prop="category" label="类别" width="110" />
        <el-table-column label="适用平台" width="150">
          <template #default="{ row }">
            <el-tag v-if="!row.platformId" type="info" size="small">通用</el-tag>
            <span v-else>{{ platformName(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="建议等级" width="100">
          <template #default="{ row }">
            <el-tag :type="riskType(row.suggestedLevel)" size="small">
              {{ ['通过', '疑似', '违规', '严重'][row.suggestedLevel] || '未定' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled === 1 ? 'success' : 'info'" size="small">
              {{ row.enabled === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ruleContent" label="规则内容" min-width="280" show-overflow-tooltip />
        <el-table-column prop="source" label="依据来源" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button v-perm="'audit:rule'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'audit:rule'" link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="680px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="92px">
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="规则编号" prop="ruleCode">
              <el-input v-model="form.ruleCode" maxlength="30" placeholder="如 AD-001" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规则名称" prop="ruleName">
              <el-input v-model="form.ruleName" maxlength="100" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="类别" prop="category">
              <el-input v-model="form.category" maxlength="30" placeholder="如 广告法" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="适用平台">
              <el-select v-model="form.platformId" clearable placeholder="通用" style="width: 100%">
                <el-option label="通用（所有平台）" :value="null" />
                <el-option v-for="p in platforms" :key="p.id" :label="p.platformName" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="建议等级" prop="suggestedLevel">
              <el-select v-model="form.suggestedLevel" style="width: 100%">
                <el-option label="通过（0）" :value="0" />
                <el-option label="疑似（1）" :value="1" />
                <el-option label="违规（2）" :value="2" />
                <el-option label="严重（3）" :value="3" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="规则内容" prop="ruleContent">
          <el-input v-model="form.ruleContent" type="textarea" :rows="4" maxlength="1000" show-word-limit
                    placeholder="写清适用条件、示例词和不适用场景；这段会下发给智能体" />
        </el-form-item>
        <el-form-item label="依据来源">
          <el-input v-model="form.source" maxlength="300" placeholder="法规/平台规范名称与条款" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.metric-label {
  color: #6b7280;
  font-size: 13px;
}

.metric-value {
  margin-top: 6px;
  font-size: 26px;
  font-weight: 600;
  color: #409eff;
}

.table-card {
  margin-top: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hint {
  color: #9ca3af;
  font-size: 12px;
}
</style>
