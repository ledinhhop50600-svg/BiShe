<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteArticle, getMyArticles, submitArticle, withdrawArticle } from '@/api/article'
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

function openFeedback(row) {
  feedback.value = row
  feedbackVisible.value = true
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
        <el-table-column prop="updateTime" label="更新时间" width="170" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 0 || row.status === 3" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.status === 0 || row.status === 3" link type="success" @click="onSubmit(row)">提交审核</el-button>
            <el-button v-if="row.status === 1" link type="warning" @click="onWithdraw(row)">撤回</el-button>
            <el-button v-if="row.status === 3 || row.status === 4" link type="danger" @click="openFeedback(row)">查看反馈</el-button>
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

    <el-dialog v-model="feedbackVisible" title="审核反馈" width="560px">
      <template v-if="feedback">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="稿件">{{ feedback.title }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(feedback.status)" size="small">{{ statusText(feedback.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert type="error" :closable="false" class="block">
          <template #title>{{ feedback.rejectReason || '（未填写原因）' }}</template>
        </el-alert>
        <el-alert type="info" :closable="false" class="block">
          <template #title>
            修改后可以重新提交。智能体接入后，这里的反馈会包含"具体违规片段"与"逐条修改建议"。
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
</style>
