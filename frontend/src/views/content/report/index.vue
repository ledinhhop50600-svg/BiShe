<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getArticle } from '@/api/article'
import { checkText } from '@/api/sensitive'
import { agentReviewReport, handleReport, pageReports } from '@/api/report'
import { riskType } from '@/utils/articleStatus'

/**
 * 举报处理（管理员/审核员）。
 * 布局与审核工作台一致：左侧待处理队列，右侧稿件正文 + 敏感词基线 + AI 复审 + 处理表单。
 * 举报成立会自动下架稿件；AI 复审只给参考，不自动改状态。
 */
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ pageNum: 1, pageSize: 50, status: 0 })

const selected = ref(null)
const article = ref(null)
const articleLoading = ref(false)
const sensitive = ref(null)
const checking = ref(false)

const agentLoading = ref(false)
const agentResult = ref(null)

const form = reactive({ status: 1, remark: '' })
const submitting = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await pageReports(query)
    list.value = data.records
    total.value = data.total
    if (selected.value && !list.value.some((x) => x.id === selected.value.id)) {
      clearSelection()
    }
  } finally {
    loading.value = false
  }
}

function clearSelection() {
  selected.value = null
  article.value = null
  sensitive.value = null
  agentResult.value = null
}

async function select(row) {
  selected.value = row
  article.value = null
  sensitive.value = null
  agentResult.value = null
  form.status = 1
  form.remark = ''

  articleLoading.value = true
  checking.value = true
  try {
    article.value = await getArticle(row.articleId)
    sensitive.value = await checkText(`${article.value.title}\n${article.value.content || ''}`)
  } catch {
    article.value = null
  } finally {
    articleLoading.value = false
    checking.value = false
  }
}

async function runAgentReview() {
  if (!selected.value) return
  agentLoading.value = true
  agentResult.value = null
  try {
    const result = await agentReviewReport(selected.value.id)
    agentResult.value = result
    if (result?.agentFailed) {
      ElMessage.error(result.message || '智能体不可用，请人工判断')
      return
    }
    const parts = []
    if (result.suggestion) parts.push(result.suggestion)
    for (const v of result.violations || []) {
      if (v.suggestion) parts.push(`${v.fragment ? `「${v.fragment}」` : ''}建议：${v.suggestion}`)
    }
    if (parts.length) form.remark = parts.join('\n')
    ElMessage.success('AI 复审完成，建议已填入处理意见')
  } finally {
    agentLoading.value = false
  }
}

async function submit() {
  if (!selected.value) return
  if (selected.value.status !== 0) return
  if (form.status === 1 && !form.remark.trim()) {
    ElMessage.warning('举报成立时请填写处理意见，说明依据')
    return
  }
  submitting.value = true
  try {
    await handleReport(selected.value.id, { status: form.status, remark: form.remark })
    ElMessage.success(form.status === 1 ? '举报成立，稿件已下架' : '已记录：举报不成立')
    clearSelection()
    await load()
  } finally {
    submitting.value = false
  }
}

function statusText(status) {
  return status === 0 ? '待处理' : status === 1 ? '成立' : '不成立'
}

function statusType(status) {
  return status === 0 ? 'warning' : status === 1 ? 'danger' : 'info'
}
</script>

<template>
  <div>
    <el-alert type="info" :closable="false" class="tip">
      <template #title>
        待处理举报 {{ total }} 条。左侧选择举报，右侧查看正文与敏感词基线，可先运行 AI 复审；
        举报成立会自动下架稿件，处理意见会留痕。
      </template>
    </el-alert>

    <el-row :gutter="16">
      <el-col :span="7">
        <el-card shadow="never" class="list-card">
          <template #header>
            <div class="card-header">
              <b>举报队列</b>
              <div class="head-actions">
                <el-select v-model="query.status" size="small" style="width: 104px" @change="load">
                  <el-option label="待处理" :value="0" />
                  <el-option label="全部" :value="null" />
                  <el-option label="成立" :value="1" />
                  <el-option label="不成立" :value="2" />
                </el-select>
                <el-button size="small" @click="load">刷新</el-button>
              </div>
            </div>
          </template>
          <div v-loading="loading" class="queue">
            <el-empty v-if="!list.length" description="暂无举报" :image-size="80" />
            <div
              v-for="item in list"
              :key="item.id"
              class="queue-item"
              :class="{ active: selected?.id === item.id }"
              @click="select(item)"
            >
              <div class="queue-title">{{ item.articleTitle }}</div>
              <div class="queue-reason">{{ item.reason }}</div>
              <div class="queue-meta">
                <el-tag :type="statusType(item.status)" size="small">{{ statusText(item.status) }}</el-tag>
                <span>{{ item.reporterName }}</span>
                <span>{{ item.createTime?.replace('T', ' ').slice(0, 16) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="17">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div v-if="selected" class="card-header">
              <b>{{ selected.articleTitle }}</b>
              <el-tag :type="statusType(selected.status)" size="small">{{ statusText(selected.status) }}</el-tag>
            </div>
            <b v-else>举报详情</b>
          </template>

          <template v-if="selected">
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="举报人">{{ selected.reporterName }}</el-descriptions-item>
              <el-descriptions-item label="举报时间">
                {{ selected.createTime?.replace('T', ' ').slice(0, 16) }}
              </el-descriptions-item>
              <el-descriptions-item label="处理人">{{ selected.handlerName || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div class="reason-box">
              <div class="label">举报理由</div>
              <div>{{ selected.reason }}</div>
            </div>

            <div v-loading="articleLoading" class="article-area">
              <template v-if="article">
                <img v-if="article.coverImage" :src="article.coverImage" class="cover" alt="封面" />
                <div class="article-meta">
                  {{ article.authorName }} · {{ article.categoryName || '未分类' }} · 阅读 {{ article.viewCount || 0 }}
                </div>
                <div class="content-box">{{ article.content }}</div>
              </template>
              <el-empty v-else-if="!articleLoading" description="稿件不存在或已被删除" :image-size="60" />
            </div>

            <el-card shadow="never" class="block" v-loading="checking">
              <template #header><b>敏感词检测（关键词基线，供对照）</b></template>
              <template v-if="sensitive">
                <div class="line">
                  <el-tag :type="sensitive.passed ? 'success' : 'danger'" size="small">
                    {{ sensitive.passed ? '未命中' : '命中' }}
                  </el-tag>
                  <span class="msg">{{ sensitive.message }}</span>
                </div>
                <div v-if="!sensitive.passed" class="line">
                  <el-tag v-for="w in sensitive.matched" :key="w" type="danger" size="small" class="tag">{{ w }}</el-tag>
                </div>
              </template>
            </el-card>

            <el-card shadow="never" class="block" v-loading="agentLoading">
              <template #header>
                <div class="card-header">
                  <div class="title-line">
                    <b>AI 复审</b>
                    <el-tag v-if="agentResult && !agentResult.agentFailed" :type="riskType(agentResult.riskLevel)" size="small">
                      {{ agentResult.riskLevelText || ['通过', '疑似', '违规', '严重'][agentResult.riskLevel] }}
                    </el-tag>
                  </div>
                  <el-button v-if="selected.status === 0" type="primary" size="small" :loading="agentLoading" @click="runAgentReview">
                    运行 AI 复审
                  </el-button>
                </div>
              </template>
              <template v-if="agentResult">
                <el-alert v-if="agentResult.agentFailed" type="warning" :closable="false">
                  <template #title>{{ agentResult.message || '智能体不可用，请人工判断' }}</template>
                </el-alert>
                <template v-else>
                  <div class="reason">{{ agentResult.reason }}</div>
                  <div v-if="agentResult.hitRules?.length" class="line">
                    命中规则：
                    <el-tag v-for="r in agentResult.hitRules" :key="r.code" type="warning" size="small" class="tag">{{ r.code }}</el-tag>
                  </div>
                  <div v-if="agentResult.suggestion" class="advice">处置建议：{{ agentResult.suggestion }}</div>
                </template>
              </template>
              <el-empty v-else description="尚未运行 AI 复审" :image-size="60" />
            </el-card>

            <template v-if="selected.status === 0">
              <el-divider content-position="left">处理举报</el-divider>
              <el-form label-width="92px">
                <el-form-item label="处理结果">
                  <el-radio-group v-model="form.status">
                    <el-radio :value="1">举报成立（下架稿件）</el-radio>
                    <el-radio :value="2">举报不成立</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="处理意见">
                  <el-input
                    v-model="form.remark"
                    type="textarea"
                    :rows="4"
                    maxlength="500"
                    show-word-limit
                    placeholder="说明处理依据；AI 复审完成后会自动填入建议，可直接修改"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="submitting" @click="submit">提交处理</el-button>
                </el-form-item>
              </el-form>
            </template>
            <el-alert v-else type="info" :closable="false" class="block">
              <template #title>
                已于 {{ selected.handleTime?.replace('T', ' ').slice(0, 19) }} 由
                {{ selected.handlerName || '审核员' }} 处理：{{ statusText(selected.status) }}。
                处理意见：{{ selected.handleRemark || '（未填写）' }}
              </template>
            </el-alert>
          </template>

          <el-empty v-else description="从左侧选择一条举报" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.tip {
  margin-bottom: 12px;
}

.list-card,
.detail-card {
  min-height: 620px;
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
  gap: 6px;
}

.queue {
  min-height: 120px;
  max-height: 680px;
  overflow-y: auto;
}

.queue-item {
  padding: 11px 12px;
  margin-bottom: 8px;
  border: 1px solid var(--app-line);
  border-radius: 10px;
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease;
}

.queue-item:hover {
  background: #fbf7ef;
}

.queue-item.active {
  background: var(--app-primary-soft);
  border-color: #c9dbd2;
}

.queue-title {
  margin-bottom: 5px;
  color: var(--app-ink);
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-reason {
  color: var(--app-muted);
  font-size: 11px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.queue-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 7px;
  color: #b3a99c;
  font-size: 10px;
}

.reason-box {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fbf7ef;
  color: var(--app-ink-2);
  font-size: 12px;
  line-height: 1.7;
}

.reason-box .label {
  margin-bottom: 3px;
  color: var(--app-muted);
  font-size: 10px;
}

.article-area {
  margin-top: 12px;
}

.cover {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  border-radius: 8px;
  background: #f6f1e8;
}

.article-meta {
  margin-top: 8px;
  color: var(--app-muted);
  font-size: 11px;
}

.content-box {
  margin-top: 8px;
  padding: 12px;
  max-height: 260px;
  overflow: auto;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  background: #f9fafb;
  white-space: pre-wrap;
  line-height: 1.75;
  font-size: 12px;
}

.block {
  margin-top: 12px;
}

.title-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.line {
  margin-bottom: 7px;
}

.msg {
  margin-left: 6px;
  color: #4b5563;
}

.tag {
  margin-right: 4px;
}

.reason {
  color: var(--app-ink-2);
  font-size: 12px;
  line-height: 1.8;
}

.advice {
  margin-top: 8px;
  padding: 8px 10px;
  border-left: 3px solid var(--app-gold);
  background: #fdf8ef;
  color: #6d6458;
  font-size: 11px;
  line-height: 1.7;
}
</style>
