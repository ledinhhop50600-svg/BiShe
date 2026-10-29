<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getArticle, getMyArticles } from '@/api/article'
import { listPlatforms } from '@/api/platform'
import { adaptArticle, listAdaptations } from '@/api/adapt'
import { riskText, riskType, statusText, statusType } from '@/utils/articleStatus'

/**
 * 跨平台适配（创作者）：选一篇自己的稿件，生成多个平台的版本。
 * <p>页面只做三件事：选稿选平台、展示结果、复制/回看历史。
 * 格式自检与合规预检的结论都来自后端 —— 前端不重新算一遍，
 * 否则两处规则不一致时，用户不知道该信哪个。
 */
const route = useRoute()

const myArticles = ref([])
const platforms = ref([])
const selectedPlatforms = ref([])
const articleId = ref(null)
const article = ref(null)
const results = ref([])
const history = ref([])
const generating = ref(false)

const dialogVisible = ref(false)
const detail = ref(null)

const platformByKey = computed(() =>
  Object.fromEntries(platforms.value.map((p) => [p.platformKey, p]))
)
const selectedPlatformInfo = computed(() =>
  selectedPlatforms.value.map((k) => platformByKey.value[k]).filter(Boolean)
)

onMounted(async () => {
  const [ps, mine] = await Promise.all([
    listPlatforms(),
    getMyArticles({ pageNum: 1, pageSize: 100 }),
  ])
  platforms.value = (ps || []).filter((p) => p.status === 1 && p.platformKey !== 'local')
  myArticles.value = mine?.records || []

  // 从「我的稿件」点"跨平台适配"进来时带着 articleId
  const qid = Number(route.query.articleId)
  if (qid) {
    articleId.value = qid
    await onArticleChange()
  }
})

async function onArticleChange() {
  results.value = []
  if (!articleId.value) {
    article.value = null
    history.value = []
    return
  }
  article.value = await getArticle(articleId.value)
  await loadHistory()
}

async function loadHistory() {
  if (!articleId.value) {
    history.value = []
    return
  }
  try {
    history.value = (await listAdaptations(articleId.value)) || []
  } catch {
    history.value = []
  }
}

async function generate() {
  if (!articleId.value) {
    ElMessage.warning('请先选择稿件')
    return
  }
  if (!selectedPlatforms.value.length) {
    ElMessage.warning('请至少选择一个目标平台')
    return
  }
  generating.value = true
  try {
    const data = await adaptArticle(articleId.value, selectedPlatforms.value)
    if (data.agentFailed) {
      ElMessage.error(data.message || '智能体服务不可用，请稍后重试')
      return
    }
    results.value = data.results || []
    ElMessage.success(`已生成 ${results.value.length} 个平台版本（${(data.durationMs / 1000).toFixed(1)} 秒）`)
    await loadHistory()
  } catch {
    // 请求拦截器已统一提示错误
  } finally {
    generating.value = false
  }
}

function fullText(r) {
  return [r.title, r.content, (r.tags || []).join(' ')].filter(Boolean).join('\n\n')
}

async function copyText(text, label) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // 浏览器不允许剪贴板 API 时的兜底（例如非 HTTPS 环境）
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  ElMessage.success(`${label}已复制`)
}

function openHistory(row) {
  detail.value = row
  dialogVisible.value = true
}

function historyLevel(text) {
  return (text || '').split('｜')[0] || '未判定'
}

function historyType(text) {
  const level = historyLevel(text)
  if (level === '通过') return 'success'
  if (level === '疑似') return 'warning'
  if (level === '违规' || level === '严重') return 'danger'
  return 'info'
}

function fmtTime(t) {
  return (t || '').replace('T', ' ')
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>跨平台内容适配</b>
          <span class="hint">一篇稿件 → 多个平台的发布版本</span>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="tip">
        <template #title>
          适配结果由智能体生成，发布前请自己核对事实与平台最新规则。本系统只做适配与预检，不提供真实发布。
        </template>
      </el-alert>

      <el-form label-width="90px">
        <el-form-item label="选择稿件">
          <el-select
            v-model="articleId"
            filterable
            placeholder="选择一篇自己的稿件"
            style="width: 100%"
            @change="onArticleChange"
          >
            <el-option
              v-for="a in myArticles"
              :key="a.id"
              :label="`#${a.id} ${a.title}`"
              :value="a.id"
            >
              <span>#{{ a.id }} {{ a.title }}</span>
              <el-tag size="small" :type="statusType(a.status)" class="opt-tag">
                {{ statusText(a.status) }}
              </el-tag>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item v-if="article" label="源稿件">
          <div class="source">
            <div class="source-title">{{ article.title }}</div>
            <div class="source-content">{{ article.content }}</div>
          </div>
        </el-form-item>

        <el-form-item label="目标平台">
          <el-checkbox-group v-model="selectedPlatforms">
            <el-checkbox-button v-for="p in platforms" :key="p.platformKey" :value="p.platformKey">
              {{ p.platformName }}
            </el-checkbox-button>
          </el-checkbox-group>
          <div v-if="selectedPlatformInfo.length" class="constraints">
            <div v-for="p in selectedPlatformInfo" :key="p.platformKey" class="constraint">
              <b>{{ p.platformName }}</b>：{{ p.titleMaxLen > 0 ? `标题 ≤ ${p.titleMaxLen} 字` : '无独立标题（标题与正文合并）' }}，
              正文 ≤ {{ p.contentMaxLen }} 字；{{ p.tagRule }}
            </div>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="generating" @click="generate">
            {{ generating ? '生成中（约 5-20 秒）' : '生成适配版本' }}
          </el-button>
          <span class="hint">一次最多 5 个平台；重复生成会保留历史版本</span>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-if="results.length" id="adapt-results" class="results">
      <el-row :gutter="16">
        <el-col v-for="r in results" :key="r.platformKey" :xs="24" :lg="12">
          <el-card shadow="never" class="result-card">
            <template #header>
              <div class="card-header">
                <div>
                  <b>{{ r.platformName }}</b>
                  <el-tag :type="r.formatCheck.passed ? 'success' : 'warning'" size="small" class="ml">
                    {{ r.formatCheck.passed ? '格式通过' : '格式待调整' }}
                  </el-tag>
                  <el-tag :type="riskType(r.compliance.riskLevel)" size="small" class="ml">
                    合规：{{ riskText(r.compliance.riskLevel) }}
                  </el-tag>
                </div>
                <el-button link type="primary" @click="copyText(fullText(r), '全文')">复制全文</el-button>
              </div>
            </template>

            <div class="field-label">标题（{{ r.formatCheck.titleLen }} 字）</div>
            <div class="adapted-title">{{ r.title || '（该平台无独立标题）' }}</div>

            <div class="field-label">正文（{{ r.formatCheck.contentLen }} 字）</div>
            <div class="adapted-content">{{ r.content }}</div>

            <div class="field-label">话题标签（{{ r.formatCheck.tagCount }} 个）</div>
            <div class="tags">
              <el-tag v-for="t in r.tags" :key="t" size="small" class="tag">{{ t }}</el-tag>
              <span v-if="!r.tags.length" class="muted">无</span>
            </div>

            <el-alert v-if="!r.formatCheck.passed" type="warning" :closable="false" class="block">
              <template #title>格式自检未通过</template>
              <ul class="issues">
                <li v-for="(issue, idx) in r.formatCheck.issues" :key="idx">{{ issue }}</li>
              </ul>
            </el-alert>

            <div class="field-label">合规预检</div>
            <div class="reason">{{ r.compliance.reason }}</div>
            <div v-if="r.compliance.hitRules?.length" class="muted">
              命中规则：{{ r.compliance.hitRules.map((h) => h.code).join('、') }}
            </div>
            <div v-for="(v, idx) in r.compliance.violations" :key="idx" class="violation">
              <el-tag type="danger" size="small">{{ v.issue }}</el-tag>
              <span class="fragment">「{{ v.fragment }}」</span>
              <div class="suggestion">修改建议：{{ v.suggestion }}</div>
            </div>
            <div v-if="r.compliance.suggestion" class="suggestion">处置建议：{{ r.compliance.suggestion }}</div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-card v-if="history.length" shadow="never" class="history-card">
      <template #header>
        <div class="card-header">
          <b>适配历史</b>
          <span class="hint">同一平台每生成一次，版本号 +1</span>
        </div>
      </template>
      <el-table :data="history" border>
        <el-table-column label="版本" width="70">
          <template #default="{ row }">v{{ row.version }}</template>
        </el-table-column>
        <el-table-column prop="platformName" label="平台" width="110" />
        <el-table-column prop="formatCheck" label="格式自检" min-width="210" show-overflow-tooltip />
        <el-table-column label="合规预检" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag :type="historyType(row.complianceCheck)" size="small">{{ historyLevel(row.complianceCheck) }}</el-tag>
            <span class="history-text">{{ row.complianceCheck }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.createTime) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click="openHistory(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="detail ? `${detail.platformName} · v${detail.version}` : '适配详情'" width="720px">
      <template v-if="detail">
        <div class="field-label">标题</div>
        <div class="adapted-title">{{ detail.title || '（该平台无独立标题）' }}</div>
        <div class="field-label">正文</div>
        <div class="adapted-content">{{ detail.content }}</div>
        <div class="field-label">话题标签</div>
        <div class="tags">
          <el-tag v-for="t in detail.tags" :key="t" size="small" class="tag">{{ t }}</el-tag>
          <span v-if="!detail.tags.length" class="muted">无</span>
        </div>
        <el-descriptions :column="1" border class="block">
          <el-descriptions-item label="格式自检">{{ detail.formatCheck }}</el-descriptions-item>
          <el-descriptions-item label="合规预检">{{ detail.complianceCheck }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ fmtTime(detail.createTime) }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button v-if="detail" type="primary" @click="copyText(fullText(detail), '全文')">复制全文</el-button>
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
  margin-left: 8px;
}

.tip {
  margin-bottom: 14px;
}

.opt-tag {
  float: right;
  margin-top: 7px;
}

.source {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fafafa;
}

.source-title {
  font-weight: 600;
  margin-bottom: 6px;
}

.source-content {
  color: #4b5563;
  font-size: 13px;
  line-height: 1.7;
  max-height: 140px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.constraints {
  width: 100%;
  margin-top: 8px;
}

.constraint {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.8;
}

.results {
  margin-top: 16px;
}

.result-card {
  margin-bottom: 16px;
}

.field-label {
  color: #9ca3af;
  font-size: 12px;
  margin: 12px 0 6px;
}

.adapted-title {
  font-weight: 600;
  font-size: 15px;
  line-height: 1.6;
}

.adapted-content {
  white-space: pre-wrap;
  line-height: 1.8;
  color: #1f2937;
  border-left: 3px solid #dcdfe6;
  padding-left: 10px;
  max-height: 340px;
  overflow-y: auto;
}

.tags .tag {
  margin-right: 6px;
}

.ml {
  margin-left: 6px;
}

.block {
  margin-top: 12px;
}

.issues {
  margin: 6px 0 0;
  padding-left: 18px;
  line-height: 1.8;
}

.reason {
  color: #4b5563;
  font-size: 13px;
  line-height: 1.8;
}

.violation {
  margin-top: 8px;
  padding: 8px 10px;
  background: #fef2f2;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
}

.fragment {
  margin-left: 6px;
}

.suggestion {
  color: #6b7280;
  font-size: 12px;
  margin-top: 4px;
  line-height: 1.7;
}

.muted {
  color: #9ca3af;
  font-size: 12px;
}

.history-card {
  margin-top: 16px;
}

.history-text {
  margin-left: 6px;
  color: #4b5563;
}
</style>
