<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardOverview } from '@/api/dashboard'
import { useUserStore } from '@/stores/user'
import ChartBox from '@/components/ChartBox.vue'

/**
 * 数据看板（可视化版）。
 * <p>数据由后端 /dashboard/overview 按角色聚合：管理员看全站，审核员看任务，
 * 创作者只看自己的稿件/审核/适配。页面只负责把数据画出来，不在前端重算口径。
 */
const router = useRouter()
const userStore = useUserStore()

const data = ref(null)
const loading = ref(false)

const nickname = computed(() => userStore.userInfo?.nickname || '')
const cards = computed(() => data.value?.cards || [])
const pulse = computed(() => data.value?.pulse || {})
const statusData = computed(() => data.value?.statusDistribution || [])
const riskData = computed(() => (data.value?.riskDistribution || []).filter((x) => x.value > 0))
const reviewData = computed(() => (data.value?.reviewDistribution || []).filter((x) => x.value > 0))
const trendData = computed(() => data.value?.trend || [])
const platformData = computed(() => data.value?.platformAdaptation || [])
const recentAudits = computed(() => data.value?.recentAudits || [])
const recentArticles = computed(() => data.value?.recentArticles || [])

const articleTotal = computed(() => statusData.value.reduce((s, x) => s + (x.value || 0), 0))
const reviewTotal = computed(() => reviewData.value.reduce((s, x) => s + (x.value || 0), 0))
const hasTrend = computed(() =>
  trendData.value.some((x) => x.submitted > 0 || x.published > 0)
)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayText = computed(() => {
  const d = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${week}`
})

const heroLine = computed(() => {
  if (data.value?.scope === 'admin') return '平台的稿件、审核与适配，今天都在这一屏里。'
  if (data.value?.scope === 'reviewer') return '先看待审队列，再决定今天从哪一篇开始。'
  return '你的稿件、反馈与适配记录，一眼看清。'
})

const pulseItems = computed(() => [
  { label: '智能体判定', value: pulse.value.agentRecordCount || 0, unit: '次' },
  { label: '适配生成', value: pulse.value.adaptationCount || 0, unit: '次' },
  { label: '人工改判率', value: `${pulse.value.overrideRate ?? 0}`, unit: '%' },
])

const hinted = {
  userCount: '平台上的全部账号',
  articleCount: '平台的全部内容',
  pendingCount: '等待审核员处理',
  publishedCount: '当前线上可见',
  pendingReportCount: '等待核实的举报',
  todaySubmittedCount: '今天新进来的稿件',
  todayProcessedCount: '你今天已经处理',
  myArticleCount: '你写过的全部稿件',
  myPendingCount: '正在排队等审核',
  myPublishedCount: '已经上线的内容',
  myRejectedCount: '需要你修改后重提',
}

function hintOf(key) {
  return hinted[key] || '实时统计'
}

function fmtTime(t) {
  return (t || '').replace('T', ' ').slice(0, 16)
}

function riskTagType(level) {
  if (level === 0) return 'success'
  if (level === 1) return 'warning'
  if (level >= 2) return 'danger'
  return 'info'
}

function statusTagType(status) {
  if (status === 2) return 'success'
  if (status === 1) return 'warning'
  if (status === 3 || status === 4) return 'danger'
  return 'info'
}

// ---------------- 图表配置 ----------------
const textColor = '#8b8174'
const labelStyle = { color: textColor, fontSize: 11 }
const tooltipStyle = {
  backgroundColor: '#fffdf8',
  borderColor: '#e8dfd2',
  textStyle: { color: '#26312f', fontSize: 12 },
}
const axisLine = { lineStyle: { color: '#e8dfd2' } }

const trendOption = computed(() => ({
  color: ['#1f5a54', '#b08a5a'],
  tooltip: { trigger: 'axis', ...tooltipStyle },
  legend: {
    right: 0,
    top: 0,
    itemWidth: 10,
    itemHeight: 10,
    textStyle: labelStyle,
  },
  grid: { left: 6, right: 12, top: 38, bottom: 2, containLabel: true },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: trendData.value.map((x) => x.date),
    axisLine,
    axisTick: { show: false },
    axisLabel: labelStyle,
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#f2ece2' } },
    axisLabel: labelStyle,
  },
  series: [
    {
      name: '投稿',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      data: trendData.value.map((x) => x.submitted),
      lineStyle: { width: 2.4 },
      areaStyle: { color: 'rgba(31, 90, 84, 0.10)' },
    },
    {
      name: '发布',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      data: trendData.value.map((x) => x.published),
      lineStyle: { width: 2 },
      areaStyle: { color: 'rgba(176, 138, 90, 0.08)' },
    },
  ],
}))

const statusOption = computed(() => ({
  color: ['#b9b1a5', '#b08a5a', '#1f5a54', '#bd6f58', '#8d3b32', '#5f7078'],
  tooltip: { trigger: 'item', ...tooltipStyle },
  legend: {
    bottom: 0,
    left: 'center',
    itemWidth: 8,
    itemHeight: 8,
    textStyle: labelStyle,
  },
  series: [
    {
      type: 'pie',
      radius: ['50%', '70%'],
      center: ['50%', '44%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fffdf8', borderWidth: 2 },
      label: { show: false },
      data: statusData.value,
    },
  ],
}))

const riskOption = computed(() => ({
  tooltip: { trigger: 'axis', ...tooltipStyle },
  grid: { left: 6, right: 28, top: 8, bottom: 2, containLabel: true },
  xAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#f2ece2' } },
    axisLabel: labelStyle,
  },
  yAxis: {
    type: 'category',
    data: riskData.value.map((x) => x.name),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#4b5452', fontSize: 12 },
  },
  series: [
    {
      type: 'bar',
      barWidth: 13,
      data: riskData.value.map((x, i) => ({
        value: x.value,
        itemStyle: {
          color: ['#a8a196', '#2c7068', '#b08a5a', '#bd6f58', '#8d3b32'][i % 5],
          borderRadius: [0, 7, 7, 0],
        },
      })),
      label: { show: true, position: 'right', ...labelStyle },
    },
  ],
}))

const reviewOption = computed(() => ({
  color: ['#1f5a54', '#b08a5a', '#a8a196'],
  tooltip: { trigger: 'item', ...tooltipStyle },
  legend: {
    bottom: 0,
    left: 'center',
    itemWidth: 8,
    itemHeight: 8,
    textStyle: labelStyle,
  },
  series: [
    {
      type: 'pie',
      radius: ['48%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderColor: '#fffdf8', borderWidth: 2 },
      label: { show: false },
      data: reviewData.value,
    },
  ],
}))

const platformOption = computed(() => ({
  color: ['#1f5a54'],
  tooltip: { trigger: 'axis', ...tooltipStyle },
  grid: { left: 6, right: 12, top: 14, bottom: 2, containLabel: true },
  xAxis: {
    type: 'category',
    data: platformData.value.map((x) => x.name),
    axisLine,
    axisTick: { show: false },
    axisLabel: labelStyle,
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#f2ece2' } },
    axisLabel: labelStyle,
  },
  series: [
    {
      type: 'bar',
      barWidth: 22,
      data: platformData.value.map((x, i) => ({
        value: x.value,
        itemStyle: {
          color: ['#1f5a54', '#7d9a8d', '#b08a5a', '#c7a578', '#5f7078'][i % 5],
          borderRadius: [7, 7, 0, 0],
        },
      })),
      label: { show: true, position: 'top', ...labelStyle },
    },
  ],
}))

onMounted(load)

async function load() {
  loading.value = true
  try {
    data.value = await getDashboardOverview()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-loading="loading" class="dash">
    <!-- 顶部问候 -->
    <section class="hero fade-up">
      <div class="hero-main">
        <div class="hero-kicker">
          {{ todayText }}<span class="dot">·</span>{{ data?.scopeLabel || '工作台' }}
        </div>
        <h1>{{ greeting }}，{{ nickname }}</h1>
        <p>{{ heroLine }}</p>
      </div>

      <div class="hero-side">
        <div class="pulse">
          <div v-for="p in pulseItems" :key="p.label" class="pulse-item">
            <span class="pulse-value">{{ p.value }}<small>{{ p.unit }}</small></span>
            <span class="pulse-label">{{ p.label }}</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button plain @click="router.push('/architecture')">
            <el-icon><Grid /></el-icon>
            系统架构
          </el-button>
          <el-button circle title="刷新" @click="load">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>
    </section>

    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpis">
      <el-col v-for="(c, i) in cards" :key="c.key" :xs="12" :sm="12" :lg="6">
        <el-card shadow="never" class="kpi" :class="'tone-' + c.tone">
          <div class="kpi-head">
            <span>{{ c.label }}</span>
            <span class="kpi-index">{{ String(i + 1).padStart(2, '0') }}</span>
          </div>
          <div class="kpi-value">
            {{ c.value }}<small>{{ c.unit }}</small>
          </div>
          <div class="kpi-foot">{{ hintOf(c.key) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势 + 状态 -->
    <el-row :gutter="16" class="row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-head">
              <div>
                <b>近 14 天投稿与发布</b>
                <span>每天的投稿量与上线量</span>
              </div>
              <span class="panel-note">单位：篇</span>
            </div>
          </template>
          <ChartBox v-if="hasTrend" :option="trendOption" height="300px" />
          <div v-else class="empty"><el-empty description="最近 7 天还没有投稿" :image-size="64" /></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-head">
              <div>
                <b>稿件状态</b>
                <span>内容当前分布</span>
              </div>
            </div>
          </template>
          <div v-if="articleTotal" class="donut-wrap">
            <ChartBox :option="statusOption" height="260px" />
            <div class="donut-center">
              <b>{{ articleTotal }}</b>
              <span>篇稿件</span>
            </div>
          </div>
          <div v-else class="empty"><el-empty description="还没有稿件" :image-size="64" /></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 风险 + 人工处理 + 平台适配 -->
    <el-row :gutter="16" class="row">
      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-head">
              <div>
                <b>智能体判定</b>
                <span>风险等级分布</span>
              </div>
            </div>
          </template>
          <ChartBox v-if="riskData.length" :option="riskOption" height="240px" />
          <div v-else class="empty"><el-empty description="还没有初审记录" :image-size="60" /></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-head">
              <div>
                <b>人工处理</b>
                <span>采纳 / 改判 / 人工判定</span>
              </div>
            </div>
          </template>
          <div v-if="reviewTotal" class="donut-wrap">
            <ChartBox :option="reviewOption" height="240px" />
            <div class="donut-center">
              <b>{{ reviewTotal }}</b>
              <span>次处理</span>
            </div>
          </div>
          <div v-else class="empty"><el-empty description="还没有人工处理" :image-size="60" /></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-head">
              <div>
                <b>跨平台适配</b>
                <span>各平台生成次数</span>
              </div>
            </div>
          </template>
          <ChartBox v-if="platformData.length" :option="platformOption" height="240px" />
          <div v-else class="empty"><el-empty description="还没有适配记录" :image-size="60" /></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近动态 -->
    <el-row :gutter="16" class="row">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-head">
              <div>
                <b>最近审核</b>
                <span>最新的智能体判定</span>
              </div>
              <el-button link type="primary" @click="router.push('/audit/record')">全部记录</el-button>
            </div>
          </template>
          <div v-if="recentAudits.length" class="audit-list">
            <div v-for="a in recentAudits" :key="a.id" class="audit-row">
              <span class="audit-dot" :class="'risk-' + a.riskLevel"></span>
              <div class="audit-main">
                <div class="audit-title">{{ a.articleTitle }}</div>
                <div class="audit-meta">{{ fmtTime(a.createTime) }} · {{ a.modelName || '—' }}</div>
              </div>
              <el-tag size="small" :type="riskTagType(a.riskLevel)">{{ a.riskLevelText }}</el-tag>
            </div>
          </div>
          <div v-else class="empty"><el-empty description="还没有审核记录" :image-size="60" /></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-head">
              <div>
                <b>最近稿件</b>
                <span>按更新时间排序</span>
              </div>
              <el-button link type="primary" @click="router.push('/creator/article')">我的稿件</el-button>
            </div>
          </template>
          <div v-if="recentArticles.length" class="article-list">
            <div v-for="a in recentArticles" :key="a.id" class="article-row">
              <div class="article-title">{{ a.title }}</div>
              <div class="article-meta">
                <el-tag size="small" :type="statusTagType(a.status)" effect="plain">{{ a.statusText }}</el-tag>
                <span>{{ fmtTime(a.updateTime) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty"><el-empty description="还没有稿件" :image-size="60" /></div>
        </el-card>
      </el-col>
    </el-row>

    <div class="foot-note">数据来自实时查询；进入页面时自动刷新。</div>
  </div>
</template>

<style scoped>
.dash {
  max-width: 1440px;
  margin: 0 auto;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 6px 4px 22px;
}

.hero-kicker {
  color: var(--app-muted);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-kicker .dot {
  margin: 0 8px;
  color: var(--app-gold);
}

.hero h1 {
  margin: 8px 0 6px;
  font-family: var(--app-serif);
  font-size: 30px;
  font-weight: 600;
  color: var(--app-ink);
  letter-spacing: 0.02em;
}

.hero p {
  margin: 0;
  color: var(--app-muted);
  font-size: 13.5px;
}

.hero-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 14px;
}

.pulse {
  display: flex;
  gap: 26px;
}

.pulse-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.pulse-value {
  font-family: var(--app-serif);
  font-size: 20px;
  color: var(--app-ink);
}

.pulse-value small {
  margin-left: 2px;
  font-family: var(--app-sans);
  font-size: 10px;
  color: var(--app-muted);
}

.pulse-label {
  margin-top: 1px;
  font-size: 10.5px;
  color: var(--app-muted);
}

.hero-actions {
  display: flex;
  gap: 8px;
}

.kpis {
  margin-bottom: 2px;
}

.kpi {
  position: relative;
  overflow: hidden;
  padding: 2px 0;
  border-radius: 14px;
  margin-bottom: 16px;
}

.kpi::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--kpi, var(--app-primary));
}

.tone-teal {
  --kpi: #1f5a54;
}
.tone-gold {
  --kpi: #b08a5a;
}
.tone-sage {
  --kpi: #7d9a8d;
}
.tone-terracotta {
  --kpi: #bd6f58;
}

.kpi-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--app-muted);
  font-size: 12.5px;
}

.kpi-index {
  font-family: var(--app-serif);
  font-size: 11px;
  color: #c3b6a5;
  letter-spacing: 0.08em;
}

.kpi-value {
  margin-top: 6px;
  font-family: var(--app-serif);
  font-size: 30px;
  line-height: 1.15;
  color: var(--app-ink);
}

.kpi-value small {
  margin-left: 3px;
  font-family: var(--app-sans);
  font-size: 11px;
  color: var(--app-muted);
  font-weight: 400;
}

.kpi-foot {
  margin-top: 8px;
  color: #a2988a;
  font-size: 11px;
}

.row {
  margin-bottom: 2px;
}

.panel {
  margin-bottom: 16px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-head b {
  display: block;
  font-family: var(--app-serif);
  font-size: 16px;
  font-weight: 600;
  color: var(--app-ink);
}

.panel-head span {
  display: block;
  margin-top: 3px;
  color: var(--app-muted);
  font-size: 11px;
}

.panel-head .panel-note {
  margin-top: 2px;
  color: #b3a99c;
  white-space: nowrap;
}

.donut-wrap {
  position: relative;
}

.donut-center {
  position: absolute;
  left: 50%;
  top: 44%;
  transform: translate(-50%, -50%);
  text-align: center;
  pointer-events: none;
}

.donut-center b {
  display: block;
  font-family: var(--app-serif);
  font-size: 26px;
  font-weight: 600;
  color: var(--app-ink);
}

.donut-center span {
  color: var(--app-muted);
  font-size: 10.5px;
}

.empty {
  min-height: 220px;
  display: grid;
  place-items: center;
}

.audit-list,
.article-list {
  display: flex;
  flex-direction: column;
}

.audit-row,
.article-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 2px;
  border-bottom: 1px solid #f1eae0;
}

.audit-row:last-child,
.article-row:last-child {
  border-bottom: none;
}

.audit-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #a8a196;
}

.risk--1 {
  background: #a8a196;
}
.risk-0 {
  background: #2c7068;
}
.risk-1 {
  background: #b08a5a;
}
.risk-2 {
  background: #bd6f58;
}
.risk-3 {
  background: #8d3b32;
}

.audit-main {
  min-width: 0;
  flex: 1;
}

.audit-title,
.article-title {
  color: var(--app-ink);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audit-meta,
.article-meta {
  margin-top: 3px;
  color: #a2988a;
  font-size: 11px;
}

.article-row {
  display: block;
  padding: 11px 2px;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.foot-note {
  padding: 6px 4px 4px;
  color: #b3a99c;
  font-size: 11px;
  text-align: center;
}

@media (max-width: 900px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .hero-side {
    align-items: flex-start;
    width: 100%;
  }

  .pulse {
    gap: 20px;
  }

  .hero h1 {
    font-size: 25px;
  }
}
</style>
