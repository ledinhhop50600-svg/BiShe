<script setup>
import { onMounted, ref } from 'vue'
import { getDashboardStats } from '@/api/dashboard'
import { useUserStore } from '@/stores/user'

/**
 * 数据看板：显示平台的基础统计数字。
 * <p>数据来自后端 /api/dashboard/stats，按当前登录用户的权限过滤（需要 dashboard:view）。
 */
const userStore = useUserStore()
const loading = ref(false)
const stats = ref({})

const cards = [
  { key: 'userCount', label: '用户总数', color: '#409eff' },
  { key: 'articleCount', label: '稿件总数', color: '#67c23a' },
  { key: 'pendingCount', label: '待审核稿件', color: '#e6a23c' },
  { key: 'publishedCount', label: '已发布稿件', color: '#909399' },
]

const statusRows = [
  { key: 'draftCount', label: '草稿', type: 'info' },
  { key: 'pendingCount', label: '待审核', type: 'warning' },
  { key: 'publishedCount', label: '已发布', type: 'success' },
  { key: 'rejectedCount', label: '已驳回', type: 'danger' },
  { key: 'blockedCount', label: '已阻断', type: 'danger' },
]

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
      </div>
      <div class="hint">
        你看到的菜单与上面的统计数字，都由后端按当前账号的角色与权限下发 —— 换个角色登录，内容会不同。
      </div>
    </el-card>

    <el-row :gutter="16" class="cards">
      <el-col v-for="card in cards" :key="card.key" :span="6">
        <el-card shadow="hover">
          <div class="card-label">{{ card.label }}</div>
          <div class="card-value" :style="{ color: card.color }">{{ stats[card.key] ?? '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="section">
      <template #header><b>稿件状态分布</b></template>
      <el-table :data="statusRows" border>
        <el-table-column prop="label" label="状态" width="140" />
        <el-table-column label="数量">
          <template #default="{ row }">
            <el-tag :type="row.type" size="small">{{ stats[row.key] ?? 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="说明">
          <template #default="{ row }">
            <span v-if="row.key === 'pendingCount'">等待审核员处理的稿件，智能体上线后会自动给出初判</span>
            <span v-else-if="row.key === 'blockedCount'">严重违规被阻断的稿件</span>
            <span v-else-if="row.key === 'rejectedCount'">已驳回并给出修改建议，创作者可修改后重提</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
      <el-alert type="info" :closable="false" class="tip">
        <template #title>
          阶段 3 起，这里的统计会随内容管理模块一起完善（投稿趋势、审核通过率、人工改判率等）。
        </template>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.welcome-line {
  display: flex;
  align-items: center;
  gap: 8px;
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

.tip {
  margin-top: 12px;
}
</style>
