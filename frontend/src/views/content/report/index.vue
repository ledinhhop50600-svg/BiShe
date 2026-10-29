<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getArticle } from '@/api/article'
import { checkText } from '@/api/sensitive'
import { agentReviewReport, handleReport, pageReports } from '@/api/report'

/**
 * 举报处理（管理员/审核员）：处理创作者对已发布稿件的举报。
 * <p>举报成立时，后端会自动把被举报稿件改为"已下架" —— 这是内容发布后的兜底机制。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 10, status: null })

const dialogVisible = ref(false)
const current = ref(null)
const form = reactive({ status: 1, remark: '' })
const submitting = ref(false)
const agentLoading = ref(false)
const agentVisible = ref(false)
const agentResult = ref(null)
const agentTarget = ref(null)

// 被举报稿件的详情（审核员需要看到正文才能判断举报是否成立）
const detailVisible = ref(false)
const detail = ref(null)
const sensitive = ref(null)
const detailLoading = ref(false)

async function openArticle(row) {
  if (!row.articleId) {
    return
  }
  detailVisible.value = true
  detail.value = null
  sensitive.value = null
  detailLoading.value = true
  try {
    detail.value = await getArticle(row.articleId)
    // 顺带跑一次敏感词基线，给审核员一个参考
    sensitive.value = await checkText(`${detail.value.title}\n${detail.value.content || ''}`)
  } finally {
    detailLoading.value = false
  }
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await pageReports(query)
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

function openHandle(row) {
  current.value = row
  form.status = 1
  form.remark = ''
  dialogVisible.value = true
}

async function runAgentReview(row) {
  agentTarget.value = row
  agentResult.value = null
  agentVisible.value = true
  agentLoading.value = true
  try {
    agentResult.value = await agentReviewReport(row.id)
  } finally {
    agentLoading.value = false
  }
}

async function submit() {
  submitting.value = true
  try {
    await handleReport(current.value.id, form)
    ElMessage.success(form.status === 1 ? '已处理：举报成立，稿件已下架' : '已处理：举报不成立')
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="处理状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 140px" @change="search">
            <el-option label="待处理" :value="0" />
            <el-option label="举报成立" :value="1" />
            <el-option label="举报不成立" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header><b>举报列表</b></template>
      <el-table v-loading="loading" :data="list" border>
        <el-table-column label="被举报稿件" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openArticle(row)">{{ row.articleTitle }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="reporterName" label="举报人" width="110" />
        <el-table-column prop="reason" label="举报理由" min-width="240" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.status === 0" type="warning" size="small">待处理</el-tag>
            <el-tag v-else-if="row.status === 1" type="danger" size="small">成立</el-tag>
            <el-tag v-else type="info" size="small">不成立</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="handlerName" label="处理人" width="110" />
        <el-table-column prop="handleTime" label="处理时间" width="170" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 0" v-perm="'report:handle'" link type="warning" @click="runAgentReview(row)">AI 复审</el-button>
            <el-button v-if="row.status === 0" v-perm="'report:handle'" link type="primary" @click="openHandle(row)">处理</el-button>
            <el-button v-else link type="info" disabled>已处理</el-button>
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

    <el-dialog v-model="dialogVisible" title="处理举报" width="560px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="被举报稿件">{{ current?.articleTitle }}</el-descriptions-item>
        <el-descriptions-item label="举报人">{{ current?.reporterName }}</el-descriptions-item>
        <el-descriptions-item label="举报理由">{{ current?.reason }}</el-descriptions-item>
      </el-descriptions>

      <el-form label-width="90px" class="block">
        <el-form-item label="处理结果">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">举报成立（下架稿件）</el-radio>
            <el-radio :value="2">举报不成立</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理意见">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="说明处理依据，便于后续追溯" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交处理</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="agentVisible" title="举报稿件 AI 复审" width="640px">
      <div v-loading="agentLoading">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="被举报稿件">{{ agentTarget?.articleTitle }}</el-descriptions-item>
          <el-descriptions-item label="举报理由">{{ agentTarget?.reason }}</el-descriptions-item>
        </el-descriptions>
        <el-alert v-if="agentResult?.agentFailed" type="warning" :closable="false" class="block">
          <template #title>{{ agentResult.message || '智能体不可用，请改为人工判断' }}</template>
        </el-alert>
        <template v-else-if="agentResult">
          <div class="agent-line">
            判定：<el-tag :type="agentResult.riskLevel >= 2 ? 'danger' : 'success'" size="small">
              {{ agentResult.riskLevelText || ['通过', '疑似', '违规', '严重'][agentResult.riskLevel] }}
            </el-tag>
            <span class="agent-reason">{{ agentResult.reason }}</span>
          </div>
          <div v-if="agentResult.hitRules?.length" class="agent-line">
            命中规则：<el-tag v-for="r in agentResult.hitRules" :key="r.code" type="warning" size="small" class="tag">{{ r.code }}</el-tag>
          </div>
          <el-alert type="info" :closable="false" class="block">
            <template #title>复审只供参考，是否下架仍由你上面的“处理举报”决定；本次复审已写入审核记录。</template>
          </el-alert>
        </template>
        <el-empty v-else-if="!agentLoading" description="智能体未返回结果" />
      </div>
      <template #footer><el-button @click="agentVisible = false">关闭</el-button></template>
    </el-dialog>

    <!-- 稿件详情：审核员需要看到正文，才能判断举报是否成立 -->
    <el-dialog v-model="detailVisible" title="被举报稿件详情" width="720px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="标题" :span="2">{{ detail.title }}</el-descriptions-item>
            <el-descriptions-item label="作者">{{ detail.authorName }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ detail.categoryName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="风险等级">{{ detail.riskLevel }}</el-descriptions-item>
            <el-descriptions-item label="当前状态">{{ detail.status }}</el-descriptions-item>
          </el-descriptions>

          <div class="content-box">{{ detail.content }}</div>

          <el-card v-if="sensitive" shadow="never" class="block">
            <template #header><b>敏感词检测（关键词基线）</b></template>
            <div class="line">
              <el-tag :type="sensitive.passed ? 'success' : 'danger'" size="small">
                {{ sensitive.passed ? '未命中' : '命中' }}
              </el-tag>
              <span class="msg">{{ sensitive.message }}</span>
            </div>
            <div v-if="!sensitive.passed" class="line">
              <el-tag v-for="w in sensitive.matched" :key="w" type="danger" size="small" class="tag">{{ w }}</el-tag>
            </div>
          </el-card>
        </template>
        <el-empty v-else-if="!detailLoading" description="稿件不存在或已被删除" />
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="current" type="primary" @click="detailVisible = false; dialogVisible = true">
          回到处理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-card {
  margin-top: 16px;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

.block {
  margin-top: 16px;
}

.content-box {
  margin-top: 12px;
  padding: 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.7;
  max-height: 240px;
  overflow: auto;
}

.line {
  margin-bottom: 8px;
}

.agent-line {
  margin-top: 12px;
  line-height: 1.8;
  font-size: 13px;
}

.agent-reason {
  margin-left: 6px;
  color: #4b5563;
}

.msg {
  color: #4b5563;
  margin-left: 6px;
}

.tag {
  margin-right: 4px;
}
</style>
