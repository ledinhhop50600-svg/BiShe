<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ChartBox from '@/components/ChartBox.vue'
import { getEvalResults, runAdaptationEval } from '@/api/eval'

/**
 * 评测与优化中心。
 * 数据全部来自 docs/ 下的实验产物：审核对比、适配质量、演示批次、性能与速度实验。
 * 页面只做展示与对比，不在前端重算指标，保证和报告口径一致。
 */
const loading = ref(false)
const demoLoading = ref(false)
const activeTab = ref('overview')
const data = ref({})

const audit = computed(() => data.value.audit || null)
const adaptation = computed(() => data.value.adaptation || null)
const demo = computed(() => data.value.demo || null)
const speed = computed(() => data.value.speed || {})
const optimization = computed(() => data.value.optimization || FALLBACK_OPTIMIZATION)

const COLOR = {
  primary: '#1f5a54',
  gold: '#b08a5a',
  terracotta: '#bd6f58',
  sage: '#7d9a8d',
  slate: '#5f7078',
  ink: '#26312f',
  muted: '#8b8174',
  line: '#e8dfd2',
}
const SCHEME_COLORS = [COLOR.gold, COLOR.primary, COLOR.terracotta, COLOR.sage, COLOR.slate, '#8a6f4d']
const PLATFORM_NAMES = {
  xiaohongshu: '小红书',
  wechat: '微信公众号',
  douyin: '抖音',
  weibo: '微博',
  bilibili: 'B站',
}
const STRATEGY_SHORT = {
  '分平台 · 串行（原方案）': '串行',
  '分平台 · 并行（当前生产）': '并行',
  '合并一次调用': '合并一次',
  '通用提示词 · 并行': '通用提示',
}
const HUMAN_LABELS = { style: '风格符合', retention: '信息保留', readability: '可读性' }

const FALLBACK_OPTIMIZATION = {
  memory: [
    { name: '前端（dev → preview）', before: 222.4, after: 98.1 },
    { name: '后端应用 JVM', before: 209.2, after: 172.9 },
    { name: '后端启动（Maven → jar）', before: 429.5, after: 204.3 },
  ],
  mysql: {
    total: 664.4,
    items: [
      { name: 'performance_schema', value: 230.9 },
      { name: 'Buffer Pool', value: 130.8 },
      { name: '连接 / 线程 / 其他', value: 302.7 },
    ],
  },
  agent: { rss: 75.1, private: 61.1 },
  totals: { appRss: 514.6, devRss: 771.1, demoRss: 421.7 },
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    data.value = (await getEvalResults()) || {}
  } finally {
    loading.value = false
  }
}

function schemeLetter(name) {
  return (name || '').split(' ')[0] || '?'
}

function platformRows(source) {
  if (!source?.byPlatform) return []
  return Object.entries(source.byPlatform).map(([key, value]) => ({
    key,
    name: PLATFORM_NAMES[key] || key,
    ...value,
  }))
}

const auditRows = computed(() => audit.value?.schemes || [])
const schemeLetters = computed(() => auditRows.value.map((row) => schemeLetter(row.name)))
const tierRows = computed(() => audit.value?.tiers || [])
const comparisonRows = computed(() => audit.value?.comparison || [])
const adaptationRows = computed(() => platformRows(adaptation.value))
const demoRows = computed(() => platformRows(demo.value))

const bestCoreScheme = computed(() =>
  auditRows.value.reduce((best, row) => {
    const value = row.core?.accuracy ?? row.accuracy ?? 0
    const bestValue = best ? (best.core?.accuracy ?? best.accuracy ?? 0) : -1
    return value > bestValue ? row : best
  }, null)
)
const bestPublicScheme = computed(() =>
  auditRows.value.reduce((best, row) => {
    const value = row.public?.accuracy ?? 0
    const bestValue = best ? (best.public?.accuracy ?? 0) : -1
    return value > bestValue ? row : best
  }, null)
)

const datasetTotal = computed(() => audit.value?.dataset?.total ?? 0)
const selfBuilt = computed(() => audit.value?.dataset?.selfBuilt ?? 0)
const publicSet = computed(() => audit.value?.dataset?.public ?? 0)
const toxicnCount = computed(() => audit.value?.dataset?.toxicn ?? 0)
const coldCount = computed(() => audit.value?.dataset?.cold ?? 0)

const shortStrategies = computed(() =>
  Object.entries(speed.value?.adaptShort || {}).map(([name, row]) => ({ name, ...row }))
)
const parallelRow = computed(() =>
  shortStrategies.value.find((row) => row.name.includes('并行'))
)
const parallelSeconds = computed(() =>
  parallelRow.value ? (parallelRow.value.totalMs / 1000).toFixed(1) : '—'
)
const serialRow = computed(() =>
  shortStrategies.value.find((row) => row.name.includes('串行'))
)

const reasoningRows = computed(() =>
  Object.entries(speed.value?.reasoning || {}).map(([name, row]) => ({ name, ...row }))
)

const adaptationFailures = computed(() =>
  (adaptation.value?.results || []).filter((r) => r.formatPassed === false && !r.error)
)

const humanDimensions = computed(() =>
  Object.entries(adaptation.value?.humanSummary || {}).map(([key, value]) => ({
    key,
    label: HUMAN_LABELS[key] || key,
    ...value,
  }))
)

const updatedAt = computed(
  () => audit.value?.generatedAt || speed.value?.generatedAt || '—'
)

function shortTier(name) {
  const text = String(name || '')
  if (text.startsWith('易')) return '明确违规'
  if (text.includes('陷阱')) return '语境合法'
  if (text.includes('盲区')) return '无词违规'
  if (text.includes('分级边界')) return '边界'
  if (text.includes('多类')) return '混排'
  if (text.includes('长文本')) return '长文'
  if (text.includes('正常')) return '正常'
  if (text.includes('公开')) return '公开集'
  return text.length > 5 ? text.slice(0, 5) : text
}

function fmtCost(value) {
  return Number(value || 0).toFixed(5) + ' 元'
}

/* ---------------- 总览：审核方案 ---------------- */
const auditBarOption = computed(() => {
  const rows = auditRows.value
  const metrics = [
    { name: '准确率', key: 'accuracy', scale: 1 },
    { name: 'F1 ×100', key: 'f1', scale: 100 },
    { name: '四级精确匹配', key: 'exactMatch', scale: 1 },
    { name: '规则召回', key: 'ruleRecall', scale: 1 },
  ]
  return {
    color: [COLOR.primary, COLOR.gold, COLOR.terracotta, COLOR.sage],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => `${Number(value).toFixed(1)}%`,
    },
    legend: {
      top: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    grid: { left: 42, right: 14, top: 42, bottom: 26 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => schemeLetter(row.name)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COLOR.line } },
      axisLabel: { color: COLOR.ink, fontWeight: 600 },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { color: COLOR.muted, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    series: metrics.map((metric) => ({
      name: metric.name,
      type: 'bar',
      barMaxWidth: 14,
      data: rows.map((row) => Number((row[metric.key] * metric.scale).toFixed(1))),
      itemStyle: { borderRadius: [4, 4, 0, 0] },
      emphasis: { focus: 'series' },
    })),
  }
})

const ruleRecallOption = computed(() => {
  const rows = auditRows.value.filter((row) => !['A'].includes(schemeLetter(row.name)))
  const colors = {
    B: COLOR.primary,
    C: COLOR.gold,
    C1: COLOR.terracotta,
    E2: COLOR.sage,
    D: COLOR.slate,
  }
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => `${value}%`,
    },
    grid: { left: 58, right: 42, top: 12, bottom: 22 },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: { color: COLOR.muted, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map((row) => schemeLetter(row.name)),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: COLOR.ink, fontWeight: 600 },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 24,
        data: rows.map((row) => ({
          value: row.ruleRecall,
          itemStyle: {
            color: colors[schemeLetter(row.name)] || COLOR.gold,
            borderRadius: [0, 7, 7, 0],
          },
        })),
        label: {
          show: true,
          position: 'right',
          color: COLOR.ink,
          fontSize: 11,
          formatter: '{c}%',
        },
      },
    ],
  }
})

const auditScatterOption = computed(() => {  const rows = auditRows.value
  if (!rows.length) return {}
  const minAcc = Math.min(...rows.map((row) => row.accuracy))
  const maxAcc = Math.max(...rows.map((row) => row.accuracy))
  return {
    tooltip: {
      formatter: (p) =>
        `${p.data.name}<br/>平均 token：${p.data.value[0]}<br/>准确率：${p.data.value[1]}%`,
    },
    grid: { left: 48, right: 24, top: 26, bottom: 42 },
    xAxis: {
      type: 'value',
      name: '平均 token',
      nameTextStyle: { color: COLOR.muted, fontSize: 11 },
      axisLabel: { color: COLOR.muted },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    yAxis: {
      type: 'value',
      name: '准确率 %',
      min: Math.max(0, Math.floor(minAcc / 10) * 10 - 5),
      max: Math.min(100, Math.ceil(maxAcc / 10) * 10 + 5),
      nameTextStyle: { color: COLOR.muted, fontSize: 11 },
      axisLabel: { color: COLOR.muted, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    series: [
      {
        type: 'scatter',
        symbolSize: 30,
        data: rows.map((row, index) => ({
          name: row.name,
          value: [row.tokens, row.accuracy],
          itemStyle: { color: SCHEME_COLORS[index % SCHEME_COLORS.length] },
        })),
        label: {
          show: true,
          position: 'top',
          color: COLOR.ink,
          fontWeight: 600,
          formatter: (p) => schemeLetter(p.data.name),
        },
        emphasis: { scale: 1.25 },
      },
    ],
  }
})

/* ---------------- 审核分层曲线 ---------------- */
const tierOption = computed(() => {
  const rows = tierRows.value
  const letters = auditRows.value.map((row) => schemeLetter(row.name))
  return {
    color: SCHEME_COLORS,
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => (value == null ? '-' : `${value}%`),
    },
    legend: {
      top: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    grid: { left: 40, right: 18, top: 40, bottom: 50 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => shortTier(row.name)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COLOR.line } },
      axisLabel: { color: COLOR.muted, fontSize: 10, interval: 0 },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { color: COLOR.muted, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    series: letters.map((letter, index) => ({
      name: letter,
      type: 'line',
      smooth: false,
      symbol: 'circle',
      symbolSize: 5,
      data: rows.map((row) => row[letter]),
      lineStyle: { width: index === 0 ? 2 : 2.4 },
      emphasis: { focus: 'series' },
    })),
  }
})

const splitOption = computed(() => {
  const rows = auditRows.value
  return {
    color: [COLOR.primary, COLOR.gold],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (items) => {
        const index = items[0]?.dataIndex ?? 0
        const row = rows[index]
        if (!row) return ''
        return `${row.name}<br/>核心集准确率：${row.core?.accuracy ?? '-'}%（召回 ${row.core?.recall ?? '-'}%）<br/>公开集准确率：${row.public?.accuracy ?? '-'}%（召回 ${row.public?.recall ?? '-'}%）`
      },
    },
    legend: {
      top: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    grid: { left: 42, right: 16, top: 38, bottom: 30 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => schemeLetter(row.name)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COLOR.line } },
      axisLabel: { color: COLOR.ink, fontWeight: 600 },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { color: COLOR.muted, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    series: [
      {
        name: '核心集准确率',
        type: 'bar',
        barMaxWidth: 18,
        data: rows.map((row) => row.core?.accuracy ?? 0),
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '公开集准确率',
        type: 'bar',
        barMaxWidth: 18,
        data: rows.map((row) => row.public?.accuracy ?? 0),
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
})

const datasetOption = computed(() => ({
  color: [COLOR.primary, COLOR.gold, COLOR.sage],
  tooltip: { trigger: 'item', formatter: '{b}：{c} 条（{d}%）' },
  legend: {
    bottom: 0,
    itemWidth: 9,
    itemHeight: 9,
    textStyle: { color: COLOR.muted, fontSize: 11 },
  },
  series: [
    {
      type: 'pie',
      radius: ['42%', '66%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fffdf8', borderWidth: 3 },
      label: { color: COLOR.ink, fontSize: 10, formatter: '{d}%' },
      labelLine: { length: 7, length2: 5 },
      data: [
        { name: '核心自建', value: selfBuilt.value },
        { name: 'ToxiCN', value: toxicnCount.value },
        { name: 'COLD', value: coldCount.value },
      ],
    },
  ],
}))

/* ---------------- 适配质量 ---------------- */
const adaptRadarOption = computed(() => {
  const rows = adaptationRows.value
  return {
    color: SCHEME_COLORS,
    tooltip: {},
    legend: {
      bottom: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    radar: {
      indicator: [
        { name: '风格符合', max: 5 },
        { name: '信息保留', max: 5 },
        { name: '可读性', max: 5 },
      ],
      radius: '58%',
      center: ['50%', '44%'],
      axisName: { color: COLOR.muted, fontSize: 11 },
      splitLine: { lineStyle: { color: '#ece3d6' } },
      splitArea: { areaStyle: { color: ['#fffdf8', '#fbf6ed'] } },
      axisLine: { lineStyle: { color: '#ece3d6' } },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 5,
        data: rows.map((row, index) => ({
          name: row.name,
          value: [
            row.llmAvg?.style ?? 0,
            row.llmAvg?.retention ?? 0,
            row.llmAvg?.readability ?? 0,
          ],
          lineStyle: { width: 2 },
          areaStyle: { opacity: 0.08 },
          itemStyle: { color: SCHEME_COLORS[index % SCHEME_COLORS.length] },
        })),
      },
    ],
  }
})

const ratioOption = computed(() => {
  const rows = adaptationRows.value
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => `${value}%`,
    },
    grid: { left: 44, right: 20, top: 18, bottom: 32 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.name),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COLOR.line } },
      axisLabel: { color: COLOR.muted, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { color: COLOR.muted, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    series: [
      {
        name: '长文压缩比',
        type: 'bar',
        barMaxWidth: 34,
        data: rows.map((row, index) => ({
          value: Number(((row.longArticleRatio ?? 0) * 100).toFixed(1)),
          itemStyle: {
            color: SCHEME_COLORS[index % SCHEME_COLORS.length],
            borderRadius: [6, 6, 0, 0],
          },
        })),
        label: {
          show: true,
          position: 'top',
          color: COLOR.ink,
          fontSize: 11,
          formatter: '{c}%',
        },
      },
    ],
  }
})

const humanOption = computed(() => {
  const rows = humanDimensions.value
  return {
    color: [COLOR.gold, COLOR.primary],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      top: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    grid: { left: 38, right: 16, top: 38, bottom: 28 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COLOR.line } },
      axisLabel: { color: COLOR.muted, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      max: 5,
      axisLabel: { color: COLOR.muted },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    series: [
      {
        name: '人工均分',
        type: 'bar',
        barMaxWidth: 22,
        data: rows.map((row) => row.humanMean ?? 0),
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      },
      {
        name: 'LLM 均分',
        type: 'bar',
        barMaxWidth: 22,
        data: rows.map((row) => Number((row.llmMean ?? 0).toFixed(2))),
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
})

/* ---------------- 性能与优化 ---------------- */
const speedOption = computed(() => {
  const rows = shortStrategies.value
  if (!rows.length) return {}
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (items) => {
        const item = items[0]
        const row = rows[item.dataIndex]
        return `${row.name}<br/>总耗时：${(row.totalMs / 1000).toFixed(1)} s<br/>` +
          `格式：${row.formatPass}/${row.platforms} · 形态：${row.shapeScore}/${row.platforms}`
      },
    },
    grid: { left: 72, right: 58, top: 12, bottom: 22 },
    xAxis: {
      type: 'value',
      axisLabel: { color: COLOR.muted, formatter: (value) => `${value / 1000}s` },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map((row) => STRATEGY_SHORT[row.name] || row.name),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: COLOR.ink, fontSize: 12, fontWeight: 600 },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 20,
        data: rows.map((row) => ({
          value: row.totalMs,
          itemStyle: {
            color: row.name.includes('并行') ? COLOR.primary : '#d8cec0',
            borderRadius: [0, 8, 8, 0],
          },
        })),
        label: {
          show: true,
          position: 'right',
          color: COLOR.ink,
          fontSize: 11,
          formatter: (p) => `${(p.value / 1000).toFixed(1)}s`,
        },
      },
    ],
  }
})

const reasoningOption = computed(() => {
  const rows = reasoningRows.value
  return {
    color: [COLOR.primary, COLOR.gold],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      top: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    grid: { left: 44, right: 48, top: 40, bottom: 28 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.name),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: COLOR.line } },
      axisLabel: { color: COLOR.ink, fontWeight: 600 },
    },
    yAxis: [
      {
        type: 'value',
        name: '耗时 ms',
        nameTextStyle: { color: COLOR.muted, fontSize: 11 },
        axisLabel: { color: COLOR.muted },
        splitLine: { lineStyle: { color: '#f1eae0' } },
      },
      {
        type: 'value',
        name: '输出 token',
        nameTextStyle: { color: COLOR.muted, fontSize: 11 },
        axisLabel: { color: COLOR.muted },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '耗时',
        type: 'bar',
        barMaxWidth: 42,
        data: rows.map((row) => row.totalMs),
        itemStyle: { borderRadius: [6, 6, 0, 0] },
      },
      {
        name: '输出 token',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 7,
        data: rows.map((row) => row.completionTokens),
        lineStyle: { width: 2.5 },
      },
    ],
  }
})

const memoryOption = computed(() => {
  const rows = optimization.value.memory || []
  return {
    color: ['#d8cec0', COLOR.primary],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => `${value} MB`,
    },
    legend: {
      top: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    grid: { left: 116, right: 42, top: 38, bottom: 22 },
    xAxis: {
      type: 'value',
      name: 'MB',
      nameTextStyle: { color: COLOR.muted, fontSize: 10 },
      splitNumber: 4,
      axisLabel: { color: COLOR.muted, formatter: '{value}', hideOverlap: true },
      splitLine: { lineStyle: { color: '#f1eae0' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map((row) => row.name),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: COLOR.ink, fontSize: 11 },
    },
    series: [
      {
        name: '优化前',
        type: 'bar',
        barMaxWidth: 13,
        data: rows.map((row) => row.before),
        itemStyle: { borderRadius: [0, 6, 6, 0] },
      },
      {
        name: '优化后',
        type: 'bar',
        barMaxWidth: 13,
        data: rows.map((row) => row.after),
        itemStyle: { borderRadius: [0, 6, 6, 0] },
        label: {
          show: true,
          position: 'right',
          color: COLOR.ink,
          fontSize: 10,
          formatter: '{c} MB',
        },
      },
    ],
  }
})

const mysqlOption = computed(() => {
  const items = optimization.value.mysql?.items || []
  return {
    color: [COLOR.terracotta, COLOR.gold, COLOR.sage],
    tooltip: { trigger: 'item', formatter: '{b}：{c} MB（{d}%）' },
    legend: {
      bottom: 0,
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: COLOR.muted, fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['46%', '70%'],
        center: ['50%', '42%'],
        itemStyle: { borderColor: '#fffdf8', borderWidth: 3 },
        label: { color: COLOR.ink, fontSize: 10, formatter: '{b}\n{d}%' },
        data: items.map((item) => ({ name: item.name, value: item.value })),
      },
    ],
  }
})

/* ---------------- 交互 ---------------- */
async function runDemo() {
  await ElMessageBox.confirm(
    '将调用真实模型跑 12 个适配（4 篇 × 3 平台）。首次约 2-3 分钟；之后固定批次会复用回放缓存，通常几十秒。结果写入 demo 目录，不覆盖论文数据。',
    '运行演示评测',
    { type: 'warning', confirmButtonText: '开始运行' }
  )
  demoLoading.value = true
  try {
    data.value.demo = await runAdaptationEval()
    ElMessage.success('演示评测完成')
    activeTab.value = 'adapt'
  } finally {
    demoLoading.value = false
  }
}
</script>

<template>
  <div v-loading="loading" class="eval-page">
    <header class="hero">
      <div>
        <div class="eyebrow">EVALUATION & OPTIMIZATION</div>
        <h1>评测与优化中心</h1>
        <p>
          把审核方案、适配质量、模型调用速度和内存优化放在同一套口径下观察。
          图表由实验产物直接生成，明细收在「数据明细」里。
        </p>
      </div>
      <div class="hero-side">
        <el-tag effect="plain" class="stamp">最近更新 {{ updatedAt }}</el-tag>
        <el-button :loading="loading" plain @click="load">刷新数据</el-button>
      </div>
    </header>

    <section class="kpi-row">
      <div class="kpi">
        <span>评测样本</span>
        <b>{{ datasetTotal || '—' }}<small>条</small></b>
        <em>自建 {{ selfBuilt }} + ToxiCN {{ toxicnCount }} + COLD {{ coldCount }}</em>
      </div>
      <div class="kpi">
        <span>核心集最佳</span>
        <b>{{ bestCoreScheme ? Math.round(bestCoreScheme.core?.accuracy ?? bestCoreScheme.accuracy) + '%' : '—' }}</b>
        <em>
          公开集最高 {{ bestPublicScheme?.name?.split(' ')[0] || '—' }}
          {{ bestPublicScheme?.public?.accuracy ?? '—' }}%
        </em>
      </div>
      <div class="kpi">
        <span>适配格式通过</span>
        <b>{{ adaptation ? adaptation.formatPassed + '/' + adaptation.total : '—' }}</b>
        <em>{{ adaptation ? adaptation.formatPassRate + '% · 3 平台' : '等待适配评估' }}</em>
      </div>
      <div class="kpi accent">
        <span>三平台并行</span>
        <b>{{ parallelSeconds }}<small>s</small></b>
        <em v-if="serialRow">串行 {{ (serialRow.totalMs / 1000).toFixed(1) }}s → 并行</em>
        <em v-else>等待速度实验</em>
      </div>
    </section>

    <el-tabs v-model="activeTab" class="eval-tabs">
      <!-- ================= 总览 ================= -->
      <el-tab-pane label="总览" name="overview">
        <div class="grid-2">
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2>六个审核方案，谁更稳？</h2>
                <p>准确率、F1、四级精确匹配与规则召回放在同一张图里；F1 已 ×100。</p>
              </div>
              <span class="chip">{{ audit?.rounds || 1 }} 轮 · {{ audit?.model || '—' }}</span>
            </div>
            <ChartBox v-if="auditRows.length" :option="auditBarOption" height="300px" />
            <el-empty v-else description="还没有审核实验结果" :image-size="70" />
          </section>

          <section class="panel">
            <div class="panel-head">
              <div>
                <h2>质量与成本，拐点在哪？</h2>
                <p>横轴是每条样本的平均 token，纵轴是准确率；越靠左上越划算。</p>
              </div>
              <span class="chip">6 方案</span>
            </div>
            <ChartBox v-if="auditRows.length" :option="auditScatterOption" height="300px" />
            <el-empty v-else description="等待实验数据" :image-size="70" />
          </section>
        </div>

        <div class="grid-3">
          <section class="panel">
            <div class="panel-head">
              <div><h2>评测集构成</h2><p>自建样本负责区分度，公开集负责外部效度。</p></div>
            </div>
            <ChartBox v-if="audit" :option="datasetOption" height="240px" />
          </section>

          <section class="panel">
            <div class="panel-head">
              <div><h2>适配策略耗时</h2><p>并行是唯一稳定收益；通用提示只快一点，但丢形态。</p></div>
              <span class="chip green">并行默认</span>
            </div>
            <ChartBox v-if="shortStrategies.length" :option="speedOption" height="240px" />
            <el-empty v-else description="等待速度实验" :image-size="60" />
          </section>

          <section class="panel">
            <div class="panel-head">
              <div><h2>内存优化前后</h2><p>RSS；后端启动含 Maven 父进程，演示改用 jar。</p></div>
            </div>
            <ChartBox v-if="optimization.memory?.length" :option="memoryOption" height="240px" />
          </section>
        </div>

        <section v-if="audit?.conclusions?.length" class="insight-row">
          <div v-for="(item, index) in audit.conclusions" :key="index" class="insight">
            <span class="insight-index">0{{ index + 1 }}</span>
            <p>{{ item }}</p>
          </div>
        </section>
      </el-tab-pane>

      <!-- ================= 审核对比 ================= -->
      <el-tab-pane label="审核对比" name="audit">
        <section class="panel wide">
          <div class="panel-head">
            <div>
              <h2>分层准确率曲线</h2>
              <p>看方案在哪类样本上掉链子：明确违规、语境陷阱、无关键词盲区、分级边界、混排、长文、正常内容、公开集。</p>
            </div>
            <span class="chip">{{ datasetTotal }} 条 · {{ audit?.dataset?.labelPolicy || '—' }}</span>
          </div>
          <ChartBox v-if="tierRows.length" :option="tierOption" height="340px" />
          <el-empty v-else description="等待实验结果" :image-size="70" />
        </section>

        <section class="panel wide">
          <div class="panel-head">
            <div>
              <h2>核心集 vs 公开集</h2>
              <p>核心集 28 条是广告/引流/违禁/分级边界等业务硬样本；公开集 400 条是 ToxiCN + COLD 短评论，用来扩大统计量，不能替代业务分布。</p>
            </div>
            <span class="chip">核心 {{ audit?.dataset?.core ?? 28 }} · 公开 {{ publicSet }}</span>
          </div>
          <ChartBox v-if="auditRows.length" :option="splitOption" height="280px" />
        </section>

        <div class="grid-2">
          <section class="panel">
            <div class="panel-head">
              <div><h2>规则召回：可追溯性</h2><p>审核员终审需要看到“为什么”，不是只看一个等级。</p></div>
            </div>
            <ChartBox v-if="auditRows.length" :option="ruleRecallOption" height="280px" />
          </section>
          <section class="panel">
            <div class="panel-head">
              <div><h2>口径前后对照</h2><p>严格 v3 与扩展集（v5）的对照；样本变了，排序也会变，规则能力不会。</p></div>
            </div>
            <div v-if="comparisonRows.length" class="compare-list">
              <div v-for="row in comparisonRows" :key="row.scheme" class="compare-item">
                <span>{{ row.scheme }}</span>
                <div class="compare-track">
                  <i class="strict" :style="{ width: (row.strictV3 || 0) + '%' }"></i>
                  <i class="relaxed" :style="{ width: (row.relaxedV4 || 0) + '%' }"></i>
                </div>
                <b>{{ row.strictV3 ?? '—' }}% → {{ row.relaxedV4 }}%</b>
              </div>
              <div class="compare-legend"><i class="strict"></i>严格 v3 <i class="relaxed"></i>扩展集 v5</div>
            </div>
            <el-empty v-else description="没有历史口径数据" :image-size="60" />
          </section>
        </div>

        <section class="panel">
          <div class="panel-head">
            <div><h2>结论卡片</h2><p>不是“谁分数高就用谁”，而是把安全方向、可追溯性和成本放在一起。</p></div>
          </div>
          <div class="insight-row inside">
            <div v-for="(item, index) in audit?.conclusions || []" :key="index" class="insight">
              <span class="insight-index">0{{ index + 1 }}</span>
              <p>{{ item }}</p>
            </div>
          </div>
        </section>
      </el-tab-pane>

      <!-- ================= 适配质量 ================= -->
      <el-tab-pane label="适配质量" name="adapt">
        <section v-if="adaptation" class="adapt-kpis">
          <div class="mini-stat">
            <span>格式通过率</span><b>{{ adaptation.formatPassRate }}%</b>
            <em>{{ adaptation.formatPassed }} / {{ adaptation.total }}</em>
          </div>
          <div class="mini-stat">
            <span>评测批次</span><b class="small">{{ adaptation.runId }}</b>
            <em>{{ adaptation.generatedAt }}</em>
          </div>
          <div class="mini-stat">
            <span>总耗时</span><b>{{ adaptation.elapsedSeconds }}<small>s</small></b>
            <em>4 篇 × 3 平台</em>
          </div>
        </section>

        <div class="grid-2">
          <section class="panel">
            <div class="panel-head">
              <div><h2>平台形态雷达</h2><p>LLM 评分：风格、信息保留、可读性，满分 5。</p></div>
              <span class="chip">LLM 评分</span>
            </div>
            <ChartBox v-if="adaptationRows.length" :option="adaptRadarOption" height="300px" />
            <el-empty v-else description="等待适配评估" :image-size="70" />
          </section>
          <section class="panel">
            <div class="panel-head">
              <div><h2>长文压缩比</h2><p>2102 字长文压到目标平台长度后的保留比例；公众号接近 1，小红书/抖音明显压缩。</p></div>
            </div>
            <ChartBox v-if="adaptationRows.length" :option="ratioOption" height="300px" />
          </section>
        </div>

        <section class="panel">
          <div class="panel-head">
            <div><h2>人工 vs LLM</h2><p>人工评分全为 5，Spearman 无定义；这里只展示均值差，不作为排序依据。</p></div>
            <span class="chip">n = {{ adaptation?.consistency?.filled || 0 }}</span>
          </div>
          <ChartBox v-if="humanDimensions.length" :option="humanOption" height="280px" />
          <el-alert v-if="adaptation?.humanSummary" type="info" :closable="false" class="soft-alert">
            <template #title>
              人工均分全部为 5 分，方差为 0；说明接受度 100%，但不能验证 LLM 的排序能力。
              详细分析见 <code>docs/eval/adaptation-human-eval.md</code>。
            </template>
          </el-alert>
        </section>

        <div class="grid-2">
          <section class="panel">
            <div class="panel-head">
              <div><h2>格式未通过</h2><p>程序侧自检，不通过会给出具体原因，不静默放行。</p></div>
            </div>
            <el-alert v-if="adaptationFailures.length" type="warning" :closable="false">
              <template #title>{{ adaptationFailures.length }} 条未通过</template>
              <ul class="plain-list">
                <li v-for="f in adaptationFailures" :key="f.articleId + f.platformKey">
                  #{{ f.articleId }} {{ f.platformName }}：{{ (f.formatIssues || []).join('；') }}
                </li>
              </ul>
            </el-alert>
            <div v-else class="all-pass">
              <span class="pass-dot"></span>
              <div><b>全部通过</b><p>本次 {{ adaptation?.total || 0 }} 个适配结果均满足平台格式约束。</p></div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head">
              <div><h2>演示批次</h2><p>真实流水线运行，写入 demo 目录，不覆盖论文数据。</p></div>
              <el-button type="primary" :loading="demoLoading" @click="runDemo">
                {{ demoLoading ? '运行中…' : '运行演示评测' }}
              </el-button>
            </div>
            <template v-if="demo">
              <div class="demo-line">
                <span>{{ demo.generatedAt }}</span>
                <b>{{ demo.formatPassRate }}%</b>
                <span>{{ demo.runId }}</span>
              </div>
              <div class="demo-platforms">
                <span v-for="row in demoRows" :key="row.key">{{ row.name }} {{ row.formatPassRate }}%</span>
              </div>
            </template>
            <el-empty v-else description="尚未运行演示评测" :image-size="60" />
          </section>
        </div>
      </el-tab-pane>

      <!-- ================= 性能优化 ================= -->
      <el-tab-pane label="性能优化" name="perf">
        <section class="opt-grid">
          <div class="opt-card">
            <span class="opt-tag">前端</span>
            <b>−56%</b>
            <p>Vite dev 222.4 MB → preview 98.1 MB</p>
          </div>
          <div class="opt-card">
            <span class="opt-tag">后端</span>
            <b>−17%</b>
            <p>应用 209.2 → 172.9 MB；jar 模式去掉 Maven 父进程</p>
          </div>
          <div class="opt-card">
            <span class="opt-tag">MySQL</span>
            <b>664 MB</b>
            <p>performance_schema 约 231 MB，需全局配置才能降</p>
          </div>
          <div class="opt-card">
            <span class="opt-tag">智能体</span>
            <b>75 MB</b>
            <p>不加载本地模型，已接近下限，不做无谓改动</p>
          </div>
        </section>

        <div class="grid-2">
          <section class="panel">
            <div class="panel-head">
              <div><h2>适配策略：耗时对比</h2><p>三个平台、同一篇短文；并行 6.1 s，串行 12.7 s，合并一次反而更慢。</p></div>
              <span class="chip green">并行默认</span>
            </div>
            <ChartBox v-if="shortStrategies.length" :option="speedOption" height="300px" />
          </section>
          <section class="panel">
            <div class="panel-head">
              <div><h2>思考强度：时间与 token</h2><p>none 最快、token 最少；low/high 的等级并没有变好。</p></div>
              <span class="chip">默认 none</span>
            </div>
            <ChartBox v-if="reasoningRows.length" :option="reasoningOption" height="300px" />
          </section>
        </div>

        <div class="grid-2">
          <section class="panel">
            <div class="panel-head">
              <div><h2>内存：优化前后</h2><p>RSS；后端启动从 Maven 模式 429.5 MB 降到 jar 204.3 MB。</p></div>
            </div>
            <ChartBox v-if="optimization.memory?.length" :option="memoryOption" height="300px" />
          </section>
          <section class="panel">
            <div class="panel-head">
              <div><h2>MySQL 的 664 MB 去哪了</h2><p>Private 内存构成；大头是监控表，不是业务数据。</p></div>
            </div>
            <ChartBox v-if="optimization.mysql?.items?.length" :option="mysqlOption" height="300px" />
          </section>
        </div>

        <section class="panel">
          <div class="panel-head">
            <div><h2>代价与边界</h2><p>每个选择都有适用条件，不是“参数越小越好”。</p></div>
          </div>
          <div class="tradeoff-grid">
            <div><b>并行</b><p>同时占用 3 个模型请求，限流时更容易 429；当前一个平台失败会让整个请求失败。</p></div>
            <div><b>小堆</b><p>256 MB 适合单用户演示，多人并发会频繁 GC；Serial GC 不适合高吞吐。</p></div>
            <div><b>关思考</b><p>规则判定够用；复杂多步推理应临时打开并提高 max_tokens。</p></div>
            <div><b>MySQL</b><p>改 performance_schema 要重启全局实例；同机其他库会一起受影响。</p></div>
          </div>
        </section>
      </el-tab-pane>

      <!-- ================= 数据明细 ================= -->
      <el-tab-pane label="数据明细" name="raw">
        <section class="panel">
          <div class="panel-head">
            <div><h2>审核方案原始指标</h2><p>图表背后的数字，论文表格可直接引用。</p></div>
          </div>
          <el-table :data="auditRows" size="small" border>
            <el-table-column prop="name" label="方案" min-width="160" />
            <el-table-column prop="accuracy" label="准确率 %" width="100" />
            <el-table-column prop="recall" label="违规召回 %" width="105" />
            <el-table-column prop="falsePositives" label="误报数" width="90" />
            <el-table-column prop="f1" label="F1" width="80" />
            <el-table-column prop="exactMatch" label="四级精确 %" width="110" />
            <el-table-column prop="ruleRecall" label="规则召回 %" width="110" />
            <el-table-column prop="tokens" label="平均 token" width="110" />
            <el-table-column label="成本/条" width="110">
              <template #default="{ row }">{{ fmtCost(row.cost) }}</template>
            </el-table-column>
            <el-table-column prop="durationMs" label="平均耗时 ms" width="120" />
          </el-table>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div><h2>分层准确率</h2><p>每一行是一类样本，每一列是一个方案。</p></div>
          </div>
          <el-table :data="tierRows" size="small" border>
            <el-table-column prop="name" label="层级" min-width="220" />
            <el-table-column
              v-for="letter in schemeLetters"
              :key="letter"
              :prop="letter"
              :label="letter"
              width="96"
            />
          </el-table>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div><h2>适配平台指标</h2><p>格式通过率、平均长度、压缩比、LLM 三维评分。</p></div>
          </div>
          <el-table :data="adaptationRows" size="small" border>
            <el-table-column prop="name" label="平台" width="120" />
            <el-table-column prop="count" label="数量" width="70" />
            <el-table-column prop="formatPassRate" label="格式通过 %" width="110" />
            <el-table-column prop="avgContentLen" label="平均正文长度" width="120" />
            <el-table-column prop="longArticleRatio" label="长文压缩比" width="110" />
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
        </section>

        <section class="panel">
          <div class="panel-head">
            <div><h2>人工评分一致性</h2><p>人工全 5 分，Spearman 无定义；保留原始差异供论文说明。</p></div>
          </div>
          <el-table :data="humanDimensions" size="small" border>
            <el-table-column prop="label" label="维度" width="130" />
            <el-table-column prop="humanMean" label="人工均分" width="100" />
            <el-table-column prop="llmMean" label="LLM 均分" width="100" />
            <el-table-column prop="mad" label="平均绝对差" width="110" />
            <el-table-column label="完全一致" width="100">
              <template #default="{ row }">{{ row.exact }}/{{ row.n }}</template>
            </el-table-column>
            <el-table-column label="Spearman" width="110">
              <template #default="{ row }">{{ row.spearman ?? '无定义' }}</template>
            </el-table-column>
          </el-table>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div><h2>复现命令</h2><p>实验脚本依赖后端与 Agent 已启动；适配评估直接调用 Agent。</p></div>
          </div>
          <pre class="commands"># 审核对比实验（4 方案，52 条）
python tools/experiment_compare.py --rounds 1 --out docs/实验-对比实验-v4-放宽口径.md

# 适配质量评估（4 篇 × 3 平台）
python tools/eval_adaptation.py --run-id paper --out-dir docs/eval

# 速度与内存实验
python tools/experiment_speed.py
python tools/perf_report.py</pre>
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.eval-page {
  padding-bottom: 30px;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 6px 4px 22px;
}

.eyebrow {
  color: var(--app-gold);
  font-size: 10px;
  letter-spacing: 0.24em;
  font-weight: 700;
}

.hero h1 {
  margin: 7px 0 8px;
  font-size: 30px;
  letter-spacing: 0.02em;
}

.hero p {
  margin: 0;
  max-width: 700px;
  color: var(--app-muted);
  font-size: 13px;
  line-height: 1.8;
}

.hero-side {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.stamp {
  border-color: var(--app-line-strong);
  color: var(--app-muted);
  background: rgba(255, 253, 248, 0.7);
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.kpi {
  position: relative;
  overflow: hidden;
  padding: 18px 20px 16px;
  border: 1px solid var(--app-line);
  border-radius: 16px;
  background: linear-gradient(150deg, #fffdf8, #fbf5ea);
  box-shadow: 0 8px 24px rgba(38, 49, 47, 0.04);
}

.kpi::after {
  content: "";
  position: absolute;
  right: -24px;
  bottom: -34px;
  width: 90px;
  height: 90px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(176, 138, 90, 0.14), transparent 68%);
}

.kpi.accent {
  background: linear-gradient(145deg, #1f5a54, #163f3b);
  border-color: transparent;
}

.kpi span {
  color: var(--app-muted);
  font-size: 12px;
}

.kpi.accent span,
.kpi.accent em {
  color: #d9cbb7;
}

.kpi b {
  display: block;
  margin: 8px 0 4px;
  color: var(--app-ink);
  font-family: var(--app-serif);
  font-size: 30px;
  line-height: 1.1;
  font-weight: 600;
}

.kpi.accent b {
  color: #fff7ea;
}

.kpi b small {
  margin-left: 3px;
  font-family: var(--app-sans);
  font-size: 13px;
  font-weight: 400;
}

.kpi em {
  color: var(--app-muted);
  font-size: 11px;
  font-style: normal;
  line-height: 1.5;
}

.eval-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.eval-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--app-line);
}

.eval-tabs :deep(.el-tabs__item) {
  height: 42px;
  color: var(--app-muted);
  font-size: 13px;
}

.eval-tabs :deep(.el-tabs__item.is-active) {
  color: var(--app-primary);
  font-weight: 600;
}

.eval-tabs :deep(.el-tabs__active-bar) {
  background: var(--app-gold);
  height: 2px;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.panel {
  min-width: 0;
  padding: 18px 20px 16px;
  border: 1px solid var(--app-line);
  border-radius: 16px;
  background: var(--app-surface);
  box-shadow: 0 10px 28px rgba(38, 49, 47, 0.04);
}

.panel.wide {
  margin-bottom: 16px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-head h2 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
}

.panel-head p {
  margin: 0;
  color: var(--app-muted);
  font-size: 11px;
  line-height: 1.7;
}

.chip {
  flex-shrink: 0;
  padding: 4px 9px;
  border: 1px solid var(--app-line);
  border-radius: 999px;
  color: var(--app-muted);
  font-size: 10px;
  white-space: nowrap;
}

.chip.green {
  border-color: #c9dbd2;
  color: var(--app-primary);
  background: var(--app-primary-soft);
}

.insight-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.insight-row.inside {
  margin-top: 4px;
}

.insight {
  display: flex;
  gap: 12px;
  padding: 15px 16px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  background: var(--app-surface-2);
}

.insight-index {
  flex-shrink: 0;
  color: var(--app-gold);
  font-family: var(--app-serif);
  font-size: 18px;
  line-height: 1.2;
}

.insight p {
  margin: 0;
  color: var(--app-ink-2);
  font-size: 12px;
  line-height: 1.8;
}

.compare-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 6px 2px;
}

.compare-item {
  display: grid;
  grid-template-columns: 130px 1fr 96px;
  align-items: center;
  gap: 12px;
  font-size: 11px;
}

.compare-item span {
  color: var(--app-ink);
  font-weight: 600;
}

.compare-item b {
  color: var(--app-muted);
  font-size: 10px;
  text-align: right;
  font-weight: 400;
}

.compare-track {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.compare-track i {
  display: block;
  height: 6px;
  border-radius: 99px;
}

.compare-track .strict,
.compare-legend .strict {
  background: #d8cec0;
}

.compare-track .relaxed,
.compare-legend .relaxed {
  background: var(--app-gold);
}

.compare-legend {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--app-muted);
  font-size: 10px;
}

.compare-legend i {
  width: 18px;
  height: 6px;
  border-radius: 99px;
}

.adapt-kpis {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.mini-stat {
  padding: 15px 18px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  background: var(--app-surface);
}

.mini-stat span {
  display: block;
  color: var(--app-muted);
  font-size: 11px;
}

.mini-stat b {
  display: block;
  margin: 5px 0 3px;
  color: var(--app-primary);
  font-family: var(--app-serif);
  font-size: 25px;
  font-weight: 600;
}

.mini-stat b.small {
  font-family: var(--app-sans);
  font-size: 15px;
  line-height: 1.4;
}

.mini-stat b small {
  margin-left: 2px;
  font-family: var(--app-sans);
  font-size: 12px;
  font-weight: 400;
}

.mini-stat em {
  color: var(--app-muted);
  font-size: 10px;
  font-style: normal;
}

.soft-alert {
  margin-top: 8px;
  border: none;
  background: var(--app-surface-2);
}

.soft-alert :deep(.el-alert__title) {
  color: var(--app-muted);
  font-size: 11px;
  line-height: 1.7;
}

.all-pass {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 16px;
}

.pass-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #5f8f74;
  box-shadow: 0 0 0 6px #eaf2ed;
}

.all-pass b {
  font-size: 14px;
}

.all-pass p {
  margin: 4px 0 0;
  color: var(--app-muted);
  font-size: 11px;
}

.demo-line {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  color: var(--app-muted);
  font-size: 11px;
}

.demo-line b {
  color: var(--app-primary);
  font-size: 18px;
}

.demo-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.demo-platforms span {
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  font-size: 10px;
}

.opt-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.opt-card {
  padding: 16px 18px;
  border: 1px solid var(--app-line);
  border-radius: 15px;
  background: linear-gradient(160deg, #fffdf8, #faf2e6);
}

.opt-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--app-gold-soft);
  color: #8a6a42;
  font-size: 10px;
}

.opt-card b {
  display: block;
  margin: 10px 0 6px;
  color: var(--app-primary);
  font-family: var(--app-serif);
  font-size: 24px;
  font-weight: 600;
}

.opt-card p {
  margin: 0;
  color: var(--app-muted);
  font-size: 10px;
  line-height: 1.7;
}

.tradeoff-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.tradeoff-grid b {
  display: block;
  margin-bottom: 5px;
  color: var(--app-ink);
  font-size: 12px;
}

.tradeoff-grid p {
  margin: 0;
  color: var(--app-muted);
  font-size: 10px;
  line-height: 1.8;
}

.plain-list {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: 11px;
  line-height: 1.8;
}

.commands {
  margin: 0;
  padding: 14px 16px;
  border-radius: 10px;
  background: #1b302d;
  color: #e8dfd2;
  font-size: 11px;
  line-height: 1.9;
  overflow-x: auto;
}

@media (max-width: 1280px) {
  .kpi-row,
  .opt-grid,
  .tradeoff-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .grid-3 {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .grid-2,
  .grid-3,
  .kpi-row,
  .adapt-kpis,
  .opt-grid,
  .tradeoff-grid,
  .insight-row {
    grid-template-columns: 1fr;
  }
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
