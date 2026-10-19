<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getEvalResults, runAdaptationEval } from '@/api/eval'

/**
 * 评测中心（管理员）。
 * <p>展示两类结果：
 *  1. 审核实验（v4，52 条评测集）——论文实验章节的主表；
 *  2. 跨平台适配质量（4 篇 × 3 平台）——格式通过率 + LLM 评分 + 人工评分表。
 * <p>数据来自 `docs/eval/*.json`；页面不重算指标，避免口径分叉。
 * <p>「运行演示评测」调用真实流水线，但写入 demo 目录，不覆盖论文数据。
 */
const loading = ref(false)
const demoLoading = ref(false)
const audit = ref(null)
const adaptation = ref(null)
const demo = ref(null)

const PLATFORM_NAMES = {
  xiaohongshu: '小红书',
  wechat: '微信公众号',
  douyin: '抖音',
  weibo: '微博',
  bilibili: 'B站',
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await getEvalResults()
    audit.value = data?.audit || null
    adaptation.value = data?.adaptation || null
    demo.value = data?.demo || null
  } finally {
    loading.value = false
  }
}

function platformRows(data) {
  if (!data?.byPlatform) return []
  return Object.entries(data.byPlatform).map(([key, v]) => ({
    key,
    name: PLATFORM_NAMES[key] || key,
    ...v,
  }))
}

const adaptationRows = computed(() => platformRows(adaptation.value))
const demoRows = computed(() => platformRows(demo.value))

const adaptationFailures = computed(() =>
  (adaptation.value?.results || []).filter((r) => r.formatPassed === false && !r.error)
)

const demoFailures = computed(() =>
  (demo.value?.results || []).filter((r) => r.formatPassed === false && !r.error)
)

function fmtCost(v) {
  return Number(v || 0).toFixed(5) + ' 元'
}

async function runDemo() {
  await ElMessageBox.confirm(
    '将调用真实模型跑 12 个适配（4 篇 × 3 平台）。首次约 2-3 分钟；之后固定批次会复用回放缓存，通常几十秒。结果写入 demo 目录，不覆盖论文数据。',
    '运行演示评测',
    { type: 'warning', confirmButtonText: '开始运行' }
  )
  demoLoading.value = true
  try {
    demo.value = await runAdaptationEval()
    ElMessage.success('演示评测完成')
  } finally {
    demoLoading.value = false
  }
}
</script>

<template>
  <div v-loading="loading">
    <el-alert type="info" :closable="false" class="tip">
      <template #title>
        评测中心（管理员）。展示审核实验与跨平台适配评估结果；指标由 `docs/eval/` 下的脚本生成，
        页面不重算，保证口径只有一份。
      </template>
    </el-alert>

    <!-- 审核实验 -->
    <el-card v-if="audit" shadow="never" class="section">
      <template #header>
        <div class="card-header">
          <b>审核实验（v4，52 条评测集）</b>
          <span class="hint">生成时间：{{ audit.generatedAt }} · 模型：{{ audit.model }} · {{ audit.rounds }} 轮</span>
        </div>
      </template>

      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="评测集">{{ audit.dataset.total }} 条（自建 {{ audit.dataset.selfBuilt }} + 公开 {{ audit.dataset.public }}）</el-descriptions-item>
        <el-descriptions-item label="标注口径">{{ audit.dataset.labelPolicy }}</el-descriptions-item>
        <el-descriptions-item label="公开数据">{{ audit.dataset.publicSource }}</el-descriptions-item>
      </el-descriptions>

      <div class="sub-title">总体指标</div>
      <el-table :data="audit.schemes" border size="small">
        <el-table-column prop="name" label="方案" min-width="170" />
        <el-table-column prop="accuracy" label="准确率" width="90">
          <template #default="{ row }"><b>{{ row.accuracy }}%</b></template>
        </el-table-column>
        <el-table-column prop="f1" label="F1" width="80" />
        <el-table-column prop="exactMatch" label="四级精确匹配" width="120">
          <template #default="{ row }">{{ row.exactMatch }}%</template>
        </el-table-column>
        <el-table-column prop="ruleRecall" label="规则召回" width="100">
          <template #default="{ row }">{{ row.ruleRecall }}%</template>
        </el-table-column>
        <el-table-column prop="tokens" label="平均 token" width="110" />
        <el-table-column label="成本/条" width="110">
          <template #default="{ row }">{{ fmtCost(row.cost) }}</template>
        </el-table-column>
        <el-table-column prop="durationMs" label="平均耗时" width="100">
          <template #default="{ row }">{{ row.durationMs }}ms</template>
        </el-table-column>
      </el-table>

      <div class="sub-title">分层准确率（看方案在哪类样本上掉链子）</div>
      <el-table :data="audit.tiers" border size="small">
        <el-table-column prop="name" label="层级" min-width="220" />
        <el-table-column prop="A" label="A 关键词" width="100" />
        <el-table-column prop="B" label="B 纯大模型" width="110" />
        <el-table-column prop="C" label="C RAG" width="100" />
        <el-table-column prop="D" label="D 全量规则" width="110" />
      </el-table>

      <div class="sub-title">放宽口径前后对照</div>
      <el-table :data="audit.comparison" border size="small">
        <el-table-column prop="scheme" label="方案" min-width="170" />
        <el-table-column prop="strictV3" label="严格口径（v3）" width="140">
          <template #default="{ row }">{{ row.strictV3 }}%</template>
        </el-table-column>
        <el-table-column prop="relaxedV4" label="放宽口径（v4）" width="140">
          <template #default="{ row }">{{ row.relaxedV4 }}%</template>
        </el-table-column>
      </el-table>

      <el-alert type="warning" :closable="false" class="block">
        <template #title>结论（论文里要写清楚）</template>
        <ul class="notes">
          <li v-for="(c, i) in audit.conclusions" :key="i">{{ c }}</li>
        </ul>
      </el-alert>
    </el-card>

    <el-card v-else shadow="never" class="section">
      <el-empty description="还没有审核实验结果">
        <div class="muted">运行：python tools/experiment_compare.py --rounds 1 --out docs/实验-对比实验-v4-放宽口径.md</div>
      </el-empty>
    </el-card>

    <!-- 适配评估 -->
    <el-card v-if="adaptation" shadow="never" class="section">
      <template #header>
        <div class="card-header">
          <b>跨平台适配质量（{{ adaptation.total }} 个结果）</b>
          <span class="hint">
            生成时间：{{ adaptation.generatedAt }} · 批次：{{ adaptation.runId }} · 模型：{{ adaptation.model }}
          </span>
        </div>
      </template>

      <el-row :gutter="16">
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="metric-label">格式自检通过率</div>
            <div class="metric-value">{{ adaptation.formatPassRate }}%</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="metric-label">通过 / 总数</div>
            <div class="metric-value">{{ adaptation.formatPassed }} / {{ adaptation.total }}</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="metric-label">总耗时</div>
            <div class="metric-value">{{ adaptation.elapsedSeconds }}s</div>
          </el-card>
        </el-col>
      </el-row>

      <div class="sub-title">分平台指标</div>
      <el-table :data="adaptationRows" border size="small">
        <el-table-column prop="name" label="平台" width="120" />
        <el-table-column prop="count" label="数量" width="70" />
        <el-table-column label="格式通过率" width="110">
          <template #default="{ row }">{{ row.formatPassRate }}%</template>
        </el-table-column>
        <el-table-column prop="avgContentLen" label="平均正文长度" width="120" />
        <el-table-column label="长文压缩比" width="110">
          <template #default="{ row }">{{ row.longArticleRatio ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="LLM 风格" width="90">
          <template #default="{ row }">{{ row.llmAvg?.style ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="LLM 保留" width="90">
          <template #default="{ row }">{{ row.llmAvg?.retention ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="LLM 可读" width="90">
          <template #default="{ row }">{{ row.llmAvg?.readability ?? '-' }}</template>
        </el-table-column>
      </el-table>

      <el-alert v-if="adaptationFailures.length" type="warning" :closable="false" class="block">
        <template #title>格式未通过（{{ adaptationFailures.length }} 条）</template>
        <ul class="notes">
          <li v-for="f in adaptationFailures" :key="f.articleId + f.platformKey">
            #{{ f.articleId }} {{ f.platformName }}：{{ (f.formatIssues || []).join('；') }}
          </li>
        </ul>
      </el-alert>
      <el-alert v-else type="success" :closable="false" class="block">
        <template #title>本次所有适配结果格式自检全部通过。</template>
      </el-alert>

      <el-alert type="info" :closable="false" class="block">
        <template #title>
          LLM 评分只作参考：分数集中在 4-5，区分度低。人工评分请双击打开
          <code>docs/eval/adaptation-review.html</code>（原文 vs 适配结果 + 点选 1-5 分 + 导出 CSV），
          填完后计算与 LLM 评分的相关性。详细报告：<code>docs/eval/adaptation-eval.md</code>。
        </template>
      </el-alert>
    </el-card>

    <el-card v-else shadow="never" class="section">
      <el-empty description="还没有适配评估结果">
        <div class="muted">运行：python tools/eval_adaptation.py --run-id paper --out-dir docs/eval</div>
      </el-empty>
    </el-card>

    <!-- 演示运行 -->
    <el-card shadow="never" class="section">
      <template #header>
        <div class="card-header">
          <b>演示运行（不覆盖论文数据）</b>
          <el-button type="primary" :loading="demoLoading" @click="runDemo">
            {{ demoLoading ? '运行中（约 2-3 分钟）' : '运行演示评测' }}
          </el-button>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="block">
        <template #title>
          调用真实适配流水线（4 篇 × 3 平台），结果写入 <code>docs/eval/demo/</code>。
          首次约 2-3 分钟；固定批次会复用 Agent 回放缓存，之后通常几十秒。
        </template>
      </el-alert>

      <template v-if="demo">
        <div class="sub-title">
          最近一次演示：{{ demo.generatedAt }}（{{ demo.runId }}，通过率 {{ demo.formatPassRate }}%）
        </div>
        <el-table :data="demoRows" border size="small">
          <el-table-column prop="name" label="平台" width="120" />
          <el-table-column prop="count" label="数量" width="70" />
          <el-table-column label="格式通过率" width="110">
            <template #default="{ row }">{{ row.formatPassRate }}%</template>
          </el-table-column>
          <el-table-column prop="avgContentLen" label="平均正文长度" width="120" />
          <el-table-column label="长文压缩比" width="110">
            <template #default="{ row }">{{ row.longArticleRatio ?? '-' }}</template>
          </el-table-column>
        </el-table>
        <el-alert v-if="demoFailures.length" type="warning" :closable="false" class="block">
          <template #title>演示运行中格式未通过：{{ demoFailures.length }} 条（详情见 demo 目录）</template>
        </el-alert>
      </template>
      <el-empty v-else description="尚未运行演示评测" :image-size="70" />
    </el-card>

    <!-- 复现命令 -->
    <el-card shadow="never" class="section">
      <template #header><b>复现方式</b></template>
      <pre class="commands"># 审核对比实验（4 方案，52 条；写入 docs/）
python tools/experiment_compare.py --rounds 1 --out docs/实验-对比实验-v4-放宽口径.md

# 适配质量评估（4 篇 × 3 平台；写入 docs/eval/）
python tools/eval_adaptation.py --run-id paper --out-dir docs/eval

# 生成人工评分页面（原文 vs 适配结果）
python tools/make_human_review.py

# 人机协同 / 账号 / 改稿验证
python tools/verify_stage7.py
python tools/verify_account_revision.py</pre>
      <div class="muted">
        实验脚本依赖 Agent（8001）与后端（8080）已启动；适配评估直接调用 Agent，不写入演示库。
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.tip {
  margin-bottom: 12px;
}

.section {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.hint {
  color: #9ca3af;
  font-size: 12px;
}

.sub-title {
  margin: 16px 0 8px;
  font-weight: 600;
  color: #374151;
  font-size: 13px;
}

.metric-label {
  color: #6b7280;
  font-size: 13px;
}

.metric-value {
  margin-top: 6px;
  font-size: 26px;
  font-weight: 600;
  color: #409eff;
}

.block {
  margin-top: 14px;
}

.notes {
  margin: 6px 0 0;
  padding-left: 18px;
  line-height: 1.8;
}

.muted {
  color: #9ca3af;
  font-size: 12px;
  line-height: 1.8;
}

.commands {
  background: #0f172a;
  color: #e2e8f0;
  padding: 14px 16px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.8;
  overflow-x: auto;
}
</style>
