<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { agentAudit, getAuditFeedback, pageArticles, reviewArticle } from '@/api/article'
import { checkText } from '@/api/sensitive'
import { riskText, riskType } from '@/utils/articleStatus'

/**
 * 审核工作台（审核员视角）。
 * <p>人机协同流程：运行智能体初审 → 查看等级/理由/违规片段 → 采纳或改判。
 * <p>三条口径（前后端一致）：
 *  - 智能体说通过/疑似，人驳回或阻断 → 改判；
 *  - 智能体说违规/严重，人却通过 → 改判；
 *  - 智能体说疑似 → 本来就是交给人决定，通过或驳回都不算改判。
 * 改判必须填原因，原因会作为真实标注数据留存（阶段 8 的评测素材）。
 */
const loading = ref(false)
const pending = ref([])
const selected = ref(null)
const sensitive = ref(null)
const checking = ref(false)
const submitting = ref(false)
const agentLoading = ref(false)
const feedback = ref(null)

const form = reactive({ action: 'approve', reason: '' })

const record = computed(() => feedback.value?.record || null)

/** 当前是否有可用的智能体初判（失败/过期/人工补录都不算） */
const agentLevel = computed(() => {
  const r = record.value
  if (!r || r.stale || r.riskLevel == null || r.riskLevel < 0) return null
  if (['agent-failed', 'no-agent', 'content-changed'].includes(r.modelName)) return null
  return r.riskLevel
})

const isOverride = computed(() => {
  const level = agentLevel.value
  if (level === null) return false
  if (form.action === 'approve') return level >= 2
  return level === 0
})

const relationText = computed(() => {
  if (agentLevel.value === null) return '无可用智能体初判，本次为人工判定'
  if (agentLevel.value === 1) return '智能体判「疑似」，按流程转人工决定'
  return isOverride.value ? '改判：与智能体建议不一致，原因必填' : '采纳智能体建议'
})

const relationType = computed(() => {
  if (agentLevel.value === null) return 'info'
  if (agentLevel.value === 1) return 'warning'
  return isOverride.value ? 'danger' : 'success'
})

const hitRuleList = computed(() => {
  const codes = record.value?.hitRuleCodes
  return codes ? codes.split(',').map((c) => c.trim()).filter(Boolean) : []
})

onMounted(loadPending)

async function loadPending() {
  loading.value = true
  try {
    const data = await pageArticles({ pageNum: 1, pageSize: 50, status: 1 })
    pending.value = data.records
    if (!data.records.length) {
      selected.value = null
      sensitive.value = null
      feedback.value = null
    }
  } finally {
    loading.value = false
  }
}

async function select(row) {
  selected.value = row
  sensitive.value = null
  feedback.value = null
  form.action = 'approve'
  form.reason = ''
  checking.value = true
  try {
    sensitive.value = await checkText(`${row.title}\n${row.content || ''}`)
  } finally {
    checking.value = false
  }
  await loadFeedback(row.id, true)
}

async function loadFeedback(articleId, setDefault = false) {
  try {
    feedback.value = await getAuditFeedback(articleId)
    if (setDefault) {
      applyDefaultAction(feedback.value?.record)
    }
  } catch {
    feedback.value = null
  }
}

/** 按智能体建议预选处理动作（审核员仍可改） */
function applyDefaultAction(r) {
  if (!r || r.stale || r.riskLevel == null || r.riskLevel < 0) {
    return
  }
  if (r.riskLevel >= 3) {
    form.action = 'block'
  } else if (r.riskLevel === 2) {
    form.action = 'reject'
  } else {
    form.action = 'approve'
  }
}

async function runAgent() {
  if (!selected.value) {
    return
  }
  agentLoading.value = true
  try {
    const result = await agentAudit(selected.value.id, 'POST_AUDIT')
    if (result?.agentFailed) {
      ElMessage.error(result.message || '智能体不可用，请人工审核')
    } else {
      ElMessage.success('智能体初审完成')
    }
    await loadFeedback(selected.value.id, true)
  } catch {
    // 请求拦截器已统一提示
  } finally {
    agentLoading.value = false
  }
}

async function submit() {
  if (!selected.value) {
    return
  }
  if ((form.action === 'reject' || form.action === 'block') && !form.reason.trim()) {
    ElMessage.warning('驳回或阻断时请填写原因，创作者需要知道怎么改')
    return
  }
  if (isOverride.value && !form.reason.trim()) {
    ElMessage.warning('改判必须填写原因：请说明为什么不采纳智能体的判定')
    return
  }
  submitting.value = true
  try {
    await reviewArticle(selected.value.id, { action: form.action, reason: form.reason })
    ElMessage.success('审核完成')
    selected.value = null
    sensitive.value = null
    feedback.value = null
    await loadPending()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <el-alert type="info" :closable="false" class="tip">
      <template #title>
        待审稿件 {{ pending.length }} 篇。先运行智能体初审，再由审核员终审；改判必须填写原因。
      </template>
    </el-alert>

    <el-row :gutter="16">
      <el-col :span="7">
        <el-card shadow="never" class="list-card">
          <template #header>
            <div class="card-header">
              <b>待审队列</b>
              <el-button size="small" @click="loadPending">刷新</el-button>
            </div>
          </template>
          <div v-loading="loading" class="queue">
            <el-empty v-if="!pending.length" description="暂无待审稿件" :image-size="80" />
            <div
              v-for="item in pending"
              :key="item.id"
              class="queue-item"
              :class="{ active: selected?.id === item.id }"
              @click="select(item)"
            >
              <div class="queue-title">{{ item.title }}</div>
              <div class="queue-meta">
                <span>{{ item.authorName }}</span>
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
              <b>{{ selected.title }}</b>
              <el-tag type="warning" size="small">待审核</el-tag>
            </div>
            <b v-else>稿件详情</b>
          </template>

          <template v-if="selected">
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="作者">{{ selected.authorName }}</el-descriptions-item>
              <el-descriptions-item label="分类">{{ selected.categoryName || '-' }}</el-descriptions-item>
              <el-descriptions-item label="标签">
                {{ selected.tagNames?.length ? selected.tagNames.join('、') : '-' }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="content-box">{{ selected.content }}</div>

            <!-- 智能体初审 -->
            <el-card shadow="never" class="block" v-loading="agentLoading">
              <template #header>
                <div class="card-header">
                  <div class="title-line">
                    <b>智能体初审</b>
                    <el-tag v-if="record" :type="riskType(record.riskLevel)" size="small" class="ml">
                      {{ record.riskLevelText }}
                    </el-tag>
                    <el-tag v-if="record?.stale" type="warning" size="small" class="ml">结论已过期</el-tag>
                    <el-tag v-if="record?.modelName === 'agent-failed'" type="danger" size="small" class="ml">
                      调用失败
                    </el-tag>
                    <el-tag v-if="record && agentLevel !== null" size="small" effect="plain" class="ml">
                      {{ record.modelName }}
                    </el-tag>
                  </div>
                  <el-button type="primary" size="small" :loading="agentLoading" @click="runAgent">
                    {{ record ? '重新初审' : '运行初审' }}
                  </el-button>
                </div>
              </template>

              <el-empty v-if="!record" description="尚未运行智能体初审" :image-size="60" />

              <template v-else>
                <el-alert v-if="record.modelName === 'agent-failed'" type="error" :closable="false">
                  <template #title>{{ record.reason }}</template>
                </el-alert>

                <el-alert v-if="record.stale" type="warning" :closable="false" class="inner">
                  <template #title>
                    稿件在初审后被修改过，这条结论不再对应当前内容；请重新运行初审后再做采纳/改判。
                  </template>
                </el-alert>

                <template v-if="record.modelName !== 'agent-failed'">
                  <div class="line reason">{{ record.reason }}</div>
                  <div v-if="hitRuleList.length" class="line">
                    命中规则：
                    <el-tag v-for="code in hitRuleList" :key="code" type="warning" size="small" class="tag">
                      {{ code }}
                    </el-tag>
                  </div>
                  <div v-for="(v, idx) in record.violations" :key="idx" class="violation">
                    <div class="violation-head">
                      <el-tag type="danger" size="small">{{ v.issue }}</el-tag>
                      <span class="fragment">「{{ v.fragment }}」</span>
                    </div>
                    <div class="suggestion">修改建议：{{ v.suggestion }}</div>
                  </div>
                  <div v-if="record.suggestion" class="line advice">处置建议：{{ record.suggestion }}</div>
                  <div class="meta">
                    {{ record.modelName || '-' }} ·
                    {{ record.promptTokens || 0 }} + {{ record.completionTokens || 0 }} tokens ·
                    {{ record.durationMs || 0 }}ms ·
                    {{ record.createTime?.replace('T', ' ').slice(0, 19) }}
                  </div>
                </template>
              </template>
            </el-card>

            <el-card shadow="never" class="block" v-loading="checking">
              <template #header><b>敏感词检测（关键词基线，供对照）</b></template>
              <template v-if="sensitive">
                <div class="line">
                  <el-tag :type="sensitive.passed ? 'success' : 'danger'" size="small">
                    {{ sensitive.passed ? '未命中敏感词' : '命中敏感词' }}
                  </el-tag>
                  <span class="msg">{{ sensitive.message }}</span>
                </div>
                <div v-if="!sensitive.passed" class="line">
                  <el-tag v-for="w in sensitive.matched" :key="w" type="danger" size="small" class="tag">{{ w }}</el-tag>
                </div>
              </template>
            </el-card>

            <el-divider content-position="left">审核处理（人工终审）</el-divider>

            <el-form label-width="100px">
              <el-form-item label="处理结果">
                <el-radio-group v-model="form.action">
                  <el-radio value="approve">通过并发布</el-radio>
                  <el-radio value="reject">驳回修改</el-radio>
                  <el-radio value="block">阻断（严重违规）</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="与智能体关系">
                <el-tag :type="relationType" size="small">{{ relationText }}</el-tag>
              </el-form-item>
              <el-form-item label="意见/原因">
                <el-input
                  v-model="form.reason"
                  type="textarea"
                  :rows="3"
                  :placeholder="isOverride
                    ? '改判必填：请具体说明为什么不采纳智能体的判定'
                    : (form.action === 'approve' ? '可留空' : '必填：请具体说明问题与修改建议，创作者会看到这段话')"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="submitting" @click="submit">提交审核结果</el-button>
              </el-form-item>
            </el-form>
          </template>

          <el-empty v-else description="从左侧选择一篇待审稿件" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.tip {
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.title-line {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.queue {
  max-height: 620px;
  overflow: auto;
}

.queue-item {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.queue-item:hover {
  border-color: #409eff;
  background: #f5f9ff;
}

.queue-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.queue-title {
  font-size: 14px;
  color: #1f2937;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #9ca3af;
}

.detail-card {
  min-height: 420px;
}

.content-box {
  margin-top: 12px;
  padding: 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.7;
  max-height: 220px;
  overflow: auto;
}

.block {
  margin-top: 12px;
}

.inner {
  margin-bottom: 10px;
}

.line {
  margin-bottom: 8px;
}

.reason {
  color: #1f2937;
  line-height: 1.8;
}

.advice {
  color: #4b5563;
  font-size: 13px;
  line-height: 1.8;
}

.msg {
  color: #4b5563;
  margin-left: 6px;
}

.tag {
  margin-right: 4px;
}

.ml {
  margin-left: 2px;
}

.violation {
  margin-top: 8px;
  padding: 8px 10px;
  background: #fef2f2;
  border-radius: 6px;
  line-height: 1.7;
}

.violation-head {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.fragment {
  color: #b91c1c;
}

.suggestion {
  color: #6b7280;
  font-size: 12px;
  margin-top: 4px;
}

.meta {
  margin-top: 10px;
  color: #9ca3af;
  font-size: 12px;
}
</style>
