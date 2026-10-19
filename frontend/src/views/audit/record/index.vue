<script setup>
import { onMounted, reactive, ref } from 'vue'
import { pageAuditRecords } from '@/api/auditRecord'
import { riskType } from '@/utils/articleStatus'

/**
 * 审核记录（审核员/管理员）。
 * <p>用途有三：回看每次智能体判定、核对审核员是否采纳/改判、为论文提供可追溯的原始数据。
 * <p>改判率口径：改判 /（采纳 + 改判）。「人工判定」（没有可用初判）不计入分母，
 * 否则智能体失败或未运行时也会被算成"不一致"。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const detail = ref(null)
const dialogVisible = ref(false)

const query = reactive({
  pageNum: 1,
  pageSize: 10,
  triggerType: null,
  riskLevel: null,
  onlyOverride: false,
})

const triggerOptions = [
  { value: 1, label: '发布前预检' },
  { value: 2, label: '发布审核' },
  { value: 3, label: '举报复审' },
  { value: 4, label: '适配预检' },
]

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await pageAuditRecords(query)
    list.value = data.records || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

function search() {
  query.pageNum = 1
  load()
}

function openDetail(row) {
  detail.value = row
  dialogVisible.value = true
}

function fmtTime(t) {
  return (t || '').replace('T', ' ').slice(0, 19)
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="触发场景">
          <el-select v-model="query.triggerType" placeholder="全部" clearable style="width: 150px" @change="search">
            <el-option v-for="o in triggerOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="query.riskLevel" placeholder="全部" clearable style="width: 130px" @change="search">
            <el-option label="通过" :value="0" />
            <el-option label="疑似" :value="1" />
            <el-option label="违规" :value="2" />
            <el-option label="严重" :value="3" />
            <el-option label="未判定" :value="-1" />
          </el-select>
        </el-form-item>
        <el-form-item label="只看改判">
          <el-switch v-model="query.onlyOverride" @change="search" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>审核记录</b>
          <span class="hint">改判率 = 改判 /（采纳 + 改判）；人工判定不计入</span>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.createTime) }}</template>
        </el-table-column>
        <el-table-column prop="articleTitle" label="稿件" min-width="220" show-overflow-tooltip />
        <el-table-column prop="triggerText" label="触发场景" width="110" />
        <el-table-column label="智能体判定" width="100">
          <template #default="{ row }">
            <el-tag :type="riskType(row.riskLevel)" size="small">{{ row.riskLevelText }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="modelName" label="模型" width="140" />
        <el-table-column label="token（入+出）" width="130">
          <template #default="{ row }">{{ row.promptTokens || 0 }} + {{ row.completionTokens || 0 }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="90">
          <template #default="{ row }">{{ row.durationMs || 0 }}ms</template>
        </el-table-column>
        <el-table-column label="人工处理" width="150">
          <template #default="{ row }">
            <template v-if="row.reviewActionText">
              <el-tag
                :type="row.reviewAction === 2 ? 'danger' : (row.reviewAction === 1 ? 'success' : 'info')"
                size="small"
              >
                {{ row.reviewActionText }}
              </el-tag>
              <span class="final">→ {{ row.finalLevelText }}</span>
            </template>
            <span v-else class="muted">待处理</span>
          </template>
        </el-table-column>
        <el-table-column prop="reviewRemark" label="处理意见" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
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

    <el-dialog v-model="dialogVisible" title="审核记录详情" width="720px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="稿件">{{ detail.articleTitle }}</el-descriptions-item>
          <el-descriptions-item label="作者">{{ detail.authorName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="触发场景">{{ detail.triggerText }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ fmtTime(detail.createTime) }}</el-descriptions-item>
          <el-descriptions-item label="智能体判定">
            <el-tag :type="riskType(detail.riskLevel)" size="small">{{ detail.riskLevelText }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="模型 / 耗时">
            {{ detail.modelName || '-' }} / {{ detail.durationMs || 0 }}ms
          </el-descriptions-item>
          <el-descriptions-item label="命中规则" :span="2">
            {{ detail.hitRuleCodes || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="label">判定理由</div>
        <div class="reason">{{ detail.reason || '-' }}</div>

        <template v-if="detail.violations?.length">
          <div class="label">违规片段与修改建议</div>
          <div v-for="(v, idx) in detail.violations" :key="idx" class="violation">
            <el-tag type="danger" size="small">{{ v.issue }}</el-tag>
            <span class="fragment">「{{ v.fragment }}」</span>
            <div class="suggestion">修改建议：{{ v.suggestion }}</div>
          </div>
        </template>

        <div class="label">处置建议</div>
        <div class="reason">{{ detail.suggestion || '-' }}</div>

        <template v-if="detail.reviewActionText">
          <div class="label">人工处理</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="处理方式">{{ detail.reviewActionText }}</el-descriptions-item>
            <el-descriptions-item label="最终等级">{{ detail.finalLevelText }}</el-descriptions-item>
            <el-descriptions-item label="审核员">{{ detail.reviewerName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="处理时间">{{ fmtTime(detail.reviewTime) }}</el-descriptions-item>
            <el-descriptions-item label="处理意见" :span="2">{{ detail.reviewRemark || '-' }}</el-descriptions-item>
          </el-descriptions>
        </template>
      </template>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
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

.table-card {
  margin-top: 16px;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.final {
  margin-left: 4px;
  color: #6b7280;
  font-size: 12px;
}

.muted {
  color: #9ca3af;
  font-size: 12px;
}

.label {
  margin: 14px 0 6px;
  font-weight: 600;
  color: #374151;
  font-size: 13px;
}

.reason {
  color: #1f2937;
  line-height: 1.8;
  font-size: 13px;
}

.violation {
  margin-top: 8px;
  padding: 8px 10px;
  background: #fef2f2;
  border-radius: 6px;
  line-height: 1.7;
  font-size: 13px;
}

.fragment {
  color: #b91c1c;
  margin-left: 6px;
}

.suggestion {
  color: #6b7280;
  font-size: 12px;
  margin-top: 4px;
}
</style>
