<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats } from '@/api/dashboard'
import { useUserStore } from '@/stores/user'

/**
 * 数据看板。
 * <p>同一个页面，三种角色看到的是三套指标（由后端按角色返回，前端只按 scope 渲染）：
 *  - 管理员：平台全局（用户数、稿件数、状态分布）
 *  - 审核员：任务量（待审队列、待处理举报、今日新增投稿）
 *  - 创作者：个人数据（我的稿件、我的待审/已发布/被驳回）
 * <p>为什么不让创作者看"用户总数"：对他没有任何决策价值，而且属于平台级数据，不该暴露。
 */
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const stats = ref({})

const scope = computed(() => stats.value.scope || 'creator')

const adminCards = [
  { key: 'userCount', label: '用户总数', color: '#409eff' },
  { key: 'articleCount', label: '稿件总数', color: '#67c23a' },
  { key: 'pendingCount', label: '待审核稿件', color: '#e6a23c' },
  { key: 'publishedCount', label: '已发布稿件', color: '#909399' },
]

const reviewerCards = [
  { key: 'pendingCount', label: '待审核稿件', color: '#e6a23c' },
  { key: 'pendingReportCount', label: '待处理举报', color: '#f56c6c' },
  { key: 'todaySubmittedCount', label: '今日新增投稿', color: '#409eff' },
]

const creatorCards = [
  { key: 'myArticleCount', label: '我的稿件', color: '#409eff' },
  { key: 'myPendingCount', label: '我的待审核', color: '#e6a23c' },
  { key: 'myPublishedCount', label: '我的已发布', color: '#67c23a' },
  { key: 'myRejectedCount', label: '我的被驳回', color: '#f56c6c' },
]

const cards = computed(() => {
  if (scope.value === 'admin') return adminCards
  if (scope.value === 'reviewer') return reviewerCards
  return creatorCards
})

/** 状态分布表：管理员看全站，创作者看自己的；审核员没有这张表 */
const statusRows = computed(() => {
  if (scope.value === 'admin') {
    return [
      { key: 'draftCount', label: '草稿' },
      { key: 'pendingCount', label: '待审核' },
      { key: 'publishedCount', label: '已发布' },
      { key: 'rejectedCount', label: '已驳回' },
      { key: 'blockedCount', label: '已阻断' },
    ]
  }
  if (scope.value === 'creator') {
    return [
      { key: 'myDraftCount', label: '草稿' },
      { key: 'myPendingCount', label: '待审核' },
      { key: 'myPublishedCount', label: '已发布' },
      { key: 'myRejectedCount', label: '已驳回' },
    ]
  }
  return []
})

const scopeHint = computed(() => {
  if (scope.value === 'admin') return '平台全局数据'
  if (scope.value === 'reviewer') return '你的审核任务量'
  return '你的创作数据'
})

onMounted(loadStats)

async function loadStats() {
  loading.value = true
  try {
    stats.value = await getDashboardStats()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-loading="loading">
    <el-card shadow="never" class="welcome">
      <div class="welcome-line">
        <span class="hello">你好，{{ userStore.userInfo?.nickname }}</span>
        <el-tag v-for="r in userStore.roleNames" :key="r" size="small" type="info">{{ r }}</el-tag>
        <el-tag size="small" type="warning" effect="plain">{{ scopeHint }}</el-tag>
      </div>
      <div class="hint">
        菜单与统计数字都由后端按当前账号的角色下发 —— 换个角色登录，看到的内容会不同。
      </div>
    </el-card>

    <el-row :gutter="16" class="cards">
      <el-col v-for="card in cards" :key="card.key" :span="24 / cards.length">
        <el-card shadow="hover">
          <div class="card-label">{{ card.label }}</div>
          <div class="card-value" :style="{ color: card.color }">{{ stats[card.key] ?? '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="statusRows.length" shadow="never" class="section">
      <template #header><b>稿件状态分布</b></template>
      <el-table :data="statusRows" border>
        <el-table-column prop="label" label="状态" width="140" />
        <el-table-column label="数量" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ stats[row.key] ?? 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="说明">
          <template #default="{ row }">
            <span v-if="row.key.includes('pending')">等待审核员处理的稿件，智能体上线后会自动给出初判</span>
            <span v-else-if="row.key.includes('blocked')">严重违规被阻断的稿件</span>
            <span v-else-if="row.key.includes('rejected')">已驳回并给出修改建议，可修改后重新提交</span>
            <span v-else-if="row.key.includes('draft')">尚未提交审核的草稿</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 审核员没有状态分布表，给一个直达工作台的入口 -->
    <el-card v-if="scope === 'reviewer'" shadow="never" class="section">
      <template #header><b>待办</b></template>
      <div class="shortcut">
        <span>待审核稿件 {{ stats.pendingCount ?? 0 }} 篇、待处理举报 {{ stats.pendingReportCount ?? 0 }} 条</span>
        <el-button type="primary" @click="router.push('/audit/workbench')">进入审核工作台</el-button>
      </div>
    </el-card>

    <el-card v-if="scope === 'creator'" shadow="never" class="section">
      <template #header><b>快捷入口</b></template>
      <div class="shortcut">
        <span>写一篇新内容，或者看看别人在发什么</span>
        <div>
          <el-button type="primary" @click="router.push('/creator/submit')">去投稿</el-button>
          <el-button @click="router.push('/creator/plaza')">内容广场</el-button>
        </div>
      </div>
    </el-card>

    <el-alert type="info" :closable="false" class="section">
      <template #title>
        智能体接入后，看板会增加"智能体判定分布"与"人工改判率"——用来量化人机协同的效果。
      </template>
    </el-alert>
  </div>
</template>

<style scoped>
.welcome-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hello {
  font-size: 18px;
  font-weight: 600;
}

.hint {
  margin-top: 8px;
  color: #6b7280;
  font-size: 13px;
}

.cards {
  margin-top: 16px;
}

.card-label {
  color: #6b7280;
  font-size: 13px;
}

.card-value {
  margin-top: 6px;
  font-size: 28px;
  font-weight: 600;
}

.section {
  margin-top: 16px;
}

.shortcut {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #4b5563;
}
</style>
