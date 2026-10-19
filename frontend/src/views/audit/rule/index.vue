<script setup>
import { computed, onMounted, ref } from 'vue'
import { listRules } from '@/api/rule'
import { listPlatforms } from '@/api/platform'
import { riskType } from '@/utils/articleStatus'

/**
 * 审核规则库（管理员，只读）。
 * <p>规则是智能体判定的依据，也是答辩时"这条规则凭什么"的溯源材料。
 * 本期只读：规则的增删改涉及策略调整，放到后续版本；当前通过数据库维护。
 */
const loading = ref(false)
const rules = ref([])
const platforms = ref([])
const query = ref({ category: null, platform: null, keyword: '' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [rs, ps] = await Promise.all([listRules(), listPlatforms()])
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

function platformName(r) {
  return r.platformId ? (platformNameById.value[r.platformId] || `平台 #${r.platformId}`) : '通用（所有平台）'
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
            <div class="metric-label">通用规则</div>
            <div class="metric-value">{{ generalCount }}</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="6">
          <el-card shadow="hover">
            <div class="metric-label">平台专属规则</div>
            <div class="metric-value">{{ specificCount }}</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="6">
          <el-card shadow="hover">
            <div class="metric-label">规则类别</div>
            <div class="metric-value">{{ categories.length }}</div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>审核规则库</b>
          <span class="hint">本期只读；规则来源用于答辩溯源</span>
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
        <el-table-column prop="ruleContent" label="规则内容" min-width="300" show-overflow-tooltip />
        <el-table-column prop="source" label="依据来源" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
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

.hint {
  color: #9ca3af;
  font-size: 12px;
}
</style>
