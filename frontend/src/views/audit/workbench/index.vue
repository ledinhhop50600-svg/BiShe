<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { pageArticles, reviewArticle } from '@/api/article'
import { checkText } from '@/api/sensitive'

/**
 * 审核工作台（审核员视角）。
 * <p>布局：左边待审队列，右边选中稿件的详情与审核操作。
 * <p>阶段 3 的判定依据是"人工阅读 + 敏感词基线"；
 * 阶段 5 起，右侧会多出一块"智能体判定"面板（风险等级、判定理由、违规片段、处置建议），
 * 阶段 7 再把审核员的采纳/改判记录沉淀为评测数据 —— 这个页面的结构就是为那时留的。
 */
const loading = ref(false)
const pending = ref([])
const selected = ref(null)
const sensitive = ref(null)
const checking = ref(false)
const submitting = ref(false)

const form = reactive({ action: 'approve', reason: '' })

onMounted(loadPending)

async function loadPending() {
  loading.value = true
  try {
    const data = await pageArticles({ pageNum: 1, pageSize: 50, status: 1 })
    pending.value = data.records
    if (!data.records.length) {
      selected.value = null
      sensitive.value = null
    }
  } finally {
    loading.value = false
  }
}

async function select(row) {
  selected.value = row
  sensitive.value = null
  form.action = 'approve'
  form.reason = ''
  checking.value = true
  try {
    sensitive.value = await checkText(`${row.title}\n${row.content || ''}`)
  } finally {
    checking.value = false
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
  submitting.value = true
  try {
    await reviewArticle(selected.value.id, { action: form.action, reason: form.reason })
    ElMessage.success('审核完成')
    selected.value = null
    sensitive.value = null
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
        待审稿件 {{ pending.length }} 篇。当前依据"人工阅读 + 敏感词基线"审核；智能体的分级初判将在后续阶段接入本页。
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

            <el-card shadow="never" class="block" v-loading="checking">
              <template #header><b>敏感词检测（关键词基线）</b></template>
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

            <el-alert type="info" :closable="false" class="block">
              <template #title>
                智能体接入后，这里会显示：风险等级（通过 / 疑似 / 违规 / 严重）、判定理由、命中的规则、违规片段与修改建议。
              </template>
            </el-alert>

            <el-divider content-position="left">审核处理</el-divider>

            <el-form label-width="90px">
              <el-form-item label="处理结果">
                <el-radio-group v-model="form.action">
                  <el-radio value="approve">通过并发布</el-radio>
                  <el-radio value="reject">驳回修改</el-radio>
                  <el-radio value="block">阻断（严重违规）</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="意见/原因">
                <el-input
                  v-model="form.reason"
                  type="textarea"
                  :rows="3"
                  :placeholder="form.action === 'approve' ? '可留空' : '必填：请具体说明问题与修改建议，创作者会看到这段话'"
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
  max-height: 240px;
  overflow: auto;
}

.block {
  margin-top: 12px;
}

.line {
  margin-bottom: 8px;
}

.msg {
  color: #4b5563;
  margin-left: 6px;
}

.tag {
  margin-right: 4px;
}
</style>
