<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteArticle, getAuditFeedback, getMyArticles, submitArticle, withdrawArticle } from '@/api/article'
import { ARTICLE_STATUS, riskText, riskType, statusText, statusType } from '@/utils/articleStatus'

/**
 * 我的稿件（创作者）：管理自己的稿件。
 * <p>页面上的按钮按稿件状态显示 —— 这个"按状态出按钮"的规则，
 * 与后端的稿件状态机是同一套约束（后端会拒绝非法流转，前端只是提前把非法操作藏起来）。
 */
const router = useRouter()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 10, status: null })

const feedbackVisible = ref(false)
const feedback = ref(null)
const auditFeedback = ref(null)
const feedbackLoading = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await getMyArticles(query)
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

function openEdit(row) {
  router.push({ path: '/creator/submit', query: { id: row.id } })
}

/** 带着稿件 id 跳到适配页，用户不用再选一次稿 */
function openAdapt(row) {
  router.push({ path: '/creator/adapt', query: { articleId: row.id } })
}

/**
 * 已发布/已下架稿件：编辑即"改后重审"（D3 方案 B）。
 * 保存后稿件立刻回到待审核，审核通过前不再对外展示 —— 绝不能让线上内容未经审核就改掉。
 */
async function openResubmit(row) {
  await ElMessageBox.confirm(
    `《${row.title}》${row.status === 2 ? '已发布' : '已下架'}。编辑保存后将进入待审核，审核通过前内容不再对外展示。`,
    '编辑并重新送审',
    { type: 'warning', confirmButtonText: '去编辑' }
  )
  router.push({ path: '/creator/submit', query: { id: row.id } })
}

async function onSubmit(row) {
  await ElMessageBox.confirm(`确定提交《${row.title}》进入审核吗？`, '提示', { type: 'info' })
  await submitArticle(row.id)
  ElMessage.success('已提交，等待审核')
  await load()
}

async function onWithdraw(row) {
  await ElMessageBox.confirm(`确定撤回《${row.title}》的审核申请吗？`, '提示', { type: 'warning' })
  await withdrawArticle(row.id)
  ElMessage.success('已撤回')
  await load()
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确定删除草稿《${row.title}》吗？`, '提示', { type: 'warning' })
  await deleteArticle(row.id)
  ElMessage.success('已删除')
  await load()
}

async function openFeedback(row) {
  feedback.value = row
  feedbackVisible.value = true
  auditFeedback.value = null
  feedbackLoading.value = true
  try {
    auditFeedback.value = await getAuditFeedback(row.id)
  } catch {
    auditFeedback.value = null
  } finally {
    feedbackLoading.value = false
  }
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 140px" @change="search">
            <el-option v-for="(v, k) in ARTICLE_STATUS" :key="k" :label="v.text" :value="Number(k)" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <b>我的稿件</b>
          <el-button type="primary" size="small" @click="router.push('/creator/submit')">去投稿</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
        <el-table-column prop="categoryName" label="分类" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险" width="90">
          <template #default="{ row }">
            <el-tag :type="riskType(row.riskLevel)" size="small" effect="plain">{{ riskText(row.riskLevel) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="viewCount" label="阅读" width="80" />
        <el-table-column prop="updateTime" label="更新时间" width="170" />
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 0 || row.status === 3" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.status === 0 || row.status === 3" link type="success" @click="onSubmit(row)">提交审核</el-button>
            <el-button v-if="row.status === 1" link type="warning" @click="onWithdraw(row)">撤回</el-button>
            <el-button v-if="row.status === 3 || row.status === 4" link type="danger" @click="openFeedback(row)">查看反馈</el-button>
            <el-button v-if="row.status === 2 || row.status === 5" link type="primary" @click="openResubmit(row)">编辑并重审</el-button>
            <el-button link type="primary" @click="openAdapt(row)">跨平台适配</el-button>
            <el-button v-if="row.status === 0" link type="danger" @click="onDelete(row)">删除</el-button>
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

    <el-dialog v-model="feedbackVisible" title="审核反馈" width="640px">
      <template v-if="feedback">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="稿件">{{ feedback.title }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(feedback.status)" size="small">{{ statusText(feedback.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="feedback-label">审核意见</div>
        <el-alert type="error" :closable="false">
          <template #title>{{ feedback.rejectReason || '（未填写原因）' }}</template>
        </el-alert>

        <div v-loading="feedbackLoading" class="agent-feedback">
          <template v-if="auditFeedback?.record">
            <div class="feedback-label">
              智能体初审
              <el-tag :type="riskType(auditFeedback.record.riskLevel)" size="small" class="ml">
                {{ auditFeedback.record.riskLevelText }}
              </el-tag>
              <el-tag v-if="auditFeedback.record.modelName === 'agent-failed'" type="danger" size="small" class="ml">
                调用失败
              </el-tag>
            </div>
            <div class="reason-line">{{ auditFeedback.record.reason }}</div>

            <div v-for="(v, idx) in auditFeedback.record.violations" :key="idx" class="violation">
              <el-tag type="danger" size="small">{{ v.issue }}</el-tag>
              <span class="fragment">「{{ v.fragment }}」</span>
              <div class="suggestion">修改建议：{{ v.suggestion }}</div>
            </div>
            <div v-if="auditFeedback.record.suggestion" class="suggestion">
              处置建议：{{ auditFeedback.record.suggestion }}
            </div>

            <div v-if="auditFeedback.review" class="review-line">
              审核员 {{ auditFeedback.review.reviewerName }} ·
              {{ auditFeedback.review.actionText }}（最终：{{ auditFeedback.review.finalLevelText }}）
            </div>
          </template>
          <el-alert v-else-if="!feedbackLoading" type="info" :closable="false" class="block">
            <template #title>本轮没有智能体初审记录，以上为审核员的处理意见。</template>
          </el-alert>
        </div>

        <el-alert type="info" :closable="false" class="block">
          <template #title>
            修改后可以重新提交；重新提交后，智能体会对修改后的内容重新初审。
          </template>
        </el-alert>
      </template>
      <template #footer>
        <el-button @click="feedbackVisible = false">关闭</el-button>
        <el-button v-if="feedback" type="primary" @click="openEdit(feedback)">去修改</el-button>
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

.block {
  margin-top: 12px;
}

.feedback-label {
  margin: 14px 0 8px;
  font-weight: 600;
  color: #374151;
  font-size: 13px;
}

.agent-feedback {
  min-height: 40px;
}

.reason-line {
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
  line-height: 1.7;
}

.review-line {
  margin-top: 10px;
  color: #6b7280;
  font-size: 12px;
}

.ml {
  margin-left: 6px;
}
</style>
