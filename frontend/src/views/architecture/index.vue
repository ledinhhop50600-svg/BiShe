<script setup>
import { useRouter } from 'vue-router'

/**
 * 系统架构（静态说明页）。
 * <p>用一张拓扑图 + 分层卡片 + 代码地图，把"谁调用谁、谁负责什么"讲清楚。
 * 页面不查数据库，内容与代码目录保持一致；面试/答辩时可以边指边讲。
 */
const router = useRouter()

const layers = [
  {
    no: '01',
    title: '展示层',
    desc: '浏览器里的页面与交互，负责把事实画成图和表。',
    modules: ['登录与权限守卫', '角色化菜单', '数据看板', '审核工作台', '适配与评测', '设计说明页'],
    tags: ['Vue 3', 'Element Plus', 'ECharts', 'Pinia', 'Vue Router'],
  },
  {
    no: '02',
    title: '接口层',
    desc: '统一入口：登录校验、权限注解、参数校验、异常转换。',
    modules: ['REST Controller', 'Sa-Token 拦截器', '@SaCheckPermission', '统一 Result', '全局异常处理', 'Agent HTTP 客户端'],
    tags: ['Spring MVC', 'Sa-Token', '参数校验', '异常转换'],
  },
  {
    no: '03',
    title: '业务层',
    desc: '管状态机、管数据权限、管 Agent 编排与结果落库。',
    modules: ['稿件状态机', '审核编排', '适配编排', '人机协同', '看板聚合', '评测读取'],
    tags: ['稿件状态机', '审核编排', '适配编排', '看板聚合'],
  },
  {
    no: '04',
    title: '数据层',
    desc: '16 张表存人、内容、规则、审核与适配记录。',
    modules: ['MyBatis-Plus Mapper', '逻辑删除', '内容哈希', '审核记录', '适配版本', '数据权限过滤'],
    tags: ['MyBatis-Plus', 'MySQL 8', 'Hikari', '事务'],
  },
  {
    no: '05',
    title: '智能体层',
    desc: '独立 Python 服务：检索、定位、判定、格式检查。',
    modules: ['规则检索 RAG', '关键词定位', '结构化判定', '格式自检', '平台适配', '回放与降级'],
    tags: ['FastAPI', 'judge', 'RAG', 'format_check', 'Provider'],
  },
  {
    no: '06',
    title: '外部服务',
    desc: '语言模型与向量模型，按需调用、失败可降级。',
    modules: ['DeepSeek 对话', 'bge-m3 向量', 'OpenAI 兼容层', '超时与重试', 'Mock 供应商', '回放缓存'],
    tags: ['DeepSeek', 'SiliconFlow bge-m3', '回放缓存'],
  },
]

const zoomLevels = [
  { level: 'L1', title: '系统拓扑', desc: '浏览器、主系统、智能体、模型四段' },
  { level: 'L2', title: '六层结构', desc: '每层职责与边界' },
  { level: 'L3', title: '层内模块', desc: '每层包含的关键模块' },
  { level: 'L4', title: '代码地图', desc: '目录与文件的落地位置' },
]

const interfaces = [
  {
    from: '浏览器',
    to: '主系统',
    protocol: 'HTTP / JSON',
    detail: 'REST `/api/**`；Sa-Token 请求头；Vite 代理转发；页面级权限由后端菜单下发。',
    timeout: '30s / 适配 120s',
    code: 'frontend/src/api/request.js → SpringBoot Controller',
  },
  {
    from: '主系统',
    to: '智能体',
    protocol: 'HTTP / JSON',
    detail: '`POST /api/agent/audit`、`/precheck`、`/adapt`；`X-Agent-Token` 共享令牌；结构化 JSON 返回。',
    timeout: '审核 30s / 适配 120s',
    code: 'backend config/AgentClient → agent/api/*.py',
  },
  {
    from: '智能体',
    to: '语言模型',
    protocol: 'HTTPS / JSON',
    detail: 'OpenAI 兼容 Chat Completions；DeepSeek 主供应商，失败可切 Mock；思考模式按请求覆盖。',
    timeout: '60–90s',
    code: 'agent/providers/openai_compat.py',
  },
  {
    from: '智能体',
    to: '向量模型',
    protocol: 'HTTPS / JSON',
    detail: 'bge-m3 生成规则切片向量；检索结果缓存；不可用时降级为元规则 + 关键词。',
    timeout: '30s',
    code: 'agent/rag.py',
  },
  {
    from: '主系统',
    to: 'MySQL',
    protocol: 'JDBC / SQL',
    detail: 'MyBatis-Plus Mapper；Hikari 连接池；逻辑删除；状态与内容哈希落库。',
    timeout: '连接池 5',
    code: 'backend/mapper + service',
  },
  {
    from: '浏览器',
    to: '图表',
    protocol: '本地渲染',
    detail: 'ECharts 按需引入，数据由 REST 接口返回；图表不改变业务口径。',
    timeout: '无网络请求',
    code: 'frontend/utils/echarts.js',
  },
]

const flow = [
  { no: '1', title: '组装上下文', desc: '稿件 + 平台约束 + 规则 + 敏感词' },
  { no: '2', title: '检索与定位', desc: '相关规则 + 原文里的具体片段' },
  { no: '3', title: '模型判定', desc: '等级 / 理由 / 命中规则 / 修改建议' },
  { no: '4', title: '落库与终审', desc: 'audit_record → 工作台 → audit_review' },
]

const codeMap = [
  {
    title: 'frontend / 展示与交互',
    items: [
      'views/        20+ 页面：看板、内容、审核、适配、评测',
      'api/          axios 封装与接口',
      'stores/user   登录态、角色、权限、菜单',
      'router/       静态路由 + 权限守卫',
      'styles/       暖纸底主题与组件覆盖',
      'components/   图表容器等通用组件',
    ],
  },
  {
    title: 'backend / 业务与数据',
    items: [
      'controller/   14 个接口类',
      'service/      业务服务 + Agent 编排',
      'entity/ mapper 16 张表的映射',
      'config/       Sa-Token、MyBatis、HTTP 客户端',
      'common/       Result、异常、状态/等级常量',
      'dto/ vo/      入参与出参对象',
    ],
  },
  {
    title: 'agent / 智能体',
    items: [
      'api/audit.py     审核 / 预检接口',
      'api/adapt.py     跨平台适配接口',
      'judge.py         检索 → 定位 → 判定',
      'rag.py           混合检索与关键词定位',
      'prompts.py       分级策略与平台形态',
      'format_check.py  程序侧格式自检',
      'providers/       mock / OpenAI 兼容供应商',
    ],
  },
]

const principles = [
  '契约先行',
  '确定性编排',
  '程序校验客观约束',
  '人机协同终审',
  '失败降级',
  '内容哈希过期',
  '回放缓存',
]
</script>

<template>
  <div class="arch">
    <section class="arch-hero fade-up">
      <div>
        <div class="kicker">SYSTEM ARCHITECTURE</div>
        <h1>架构设计</h1>
        <p>从浏览器到模型，一共六层；调用自上而下，信任自下而上。</p>
      </div>
      <el-button plain @click="router.push('/dashboard')">
        <el-icon><Back /></el-icon>
        返回看板
      </el-button>
    </section>

    <!-- 从整体到局部 -->
    <section class="zoom-strip fade-up">
      <div v-for="(z, i) in zoomLevels" :key="z.level" class="zoom-item">
        <span>{{ z.level }}</span>
        <b>{{ z.title }}</b>
        <p>{{ z.desc }}</p>
        <i v-if="i < zoomLevels.length - 1">→</i>
      </div>
    </section>

    <!-- 拓扑图 -->
    <section class="topology arch-card fade-up">
      <div class="node">
        <span class="node-kicker">BROWSER</span>
        <b>浏览器</b>
        <p>Vue 3 · Element Plus · ECharts</p>
        <small>页面、图表、交互</small>
      </div>
      <div class="arrow">→</div>
      <div class="node node-main">
        <span class="node-kicker">MAIN SYSTEM</span>
        <b>主系统</b>
        <p>SpringBoot 4 · Sa-Token · MyBatis-Plus</p>
        <small>业务、权限、状态机</small>
        <div class="data-chip">MySQL 8 · 16 张表</div>
      </div>
      <div class="arrow">→</div>
      <div class="node node-agent">
        <span class="node-kicker">AGENT SERVICE</span>
        <b>智能体</b>
        <p>FastAPI · 规则检索 · 结构化判定</p>
        <small>审核、预检、适配</small>
      </div>
      <div class="arrow">→</div>
      <div class="node node-model">
        <span class="node-kicker">MODELS</span>
        <b>外部服务</b>
        <p>DeepSeek · bge-m3</p>
        <small>语言模型、向量模型</small>
      </div>
    </section>

    <!-- 请求流程 -->
    <section class="flow-section arch-card fade-up">
      <div class="section-head">
        <b>一次审核请求怎么走</b>
        <span>以「提交审核 → 智能体初审」为例</span>
      </div>
      <div class="flow">
        <template v-for="(f, i) in flow" :key="f.no">
          <div class="flow-step">
            <span class="flow-no">{{ f.no }}</span>
            <b>{{ f.title }}</b>
            <p>{{ f.desc }}</p>
          </div>
          <div v-if="i < flow.length - 1" class="flow-arrow">→</div>
        </template>
      </div>
      <div class="quote">
        调用顺序：前端 → 主系统 → 智能体 → 模型；
        信任顺序：模型只是表达，规则、原文与数据库才是事实。
      </div>
    </section>

    <!-- 分层 -->
    <section class="layer-section">
      <div class="section-head">
        <b>六层分工</b>
        <span>每层只做一件事，不跳过下层直接干活</span>
      </div>
      <div class="layer-grid">
        <div v-for="l in layers" :key="l.no" class="layer-card">
          <div class="layer-top">
            <span class="layer-no">{{ l.no }}</span>
            <b>{{ l.title }}</b>
          </div>
          <p>{{ l.desc }}</p>
          <div class="module-list">
            <span v-for="m in l.modules" :key="m">{{ m }}</span>
          </div>
          <div class="tags">
            <span v-for="t in l.tags" :key="t">{{ t }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 层间接口与通讯 -->
    <section class="interface-section arch-card fade-up">
      <div class="section-head">
        <b>层间接口与通讯方式</b>
        <span>每一层只通过明确的接口调用下一层，不跨层拿数据库或模型</span>
      </div>
      <div class="interface-list">
        <div v-for="it in interfaces" :key="it.from + it.to" class="interface-row">
          <div class="if-endpoints">
            <b>{{ it.from }}</b>
            <span class="if-arrow">→</span>
            <b>{{ it.to }}</b>
          </div>
          <span class="if-protocol">{{ it.protocol }}</span>
          <p>{{ it.detail }}</p>
          <div class="if-meta">
            <span>{{ it.timeout }}</span>
            <code>{{ it.code }}</code>
          </div>
        </div>
      </div>
    </section>

    <!-- 代码地图 -->
    <section class="code-section">
      <div class="section-head">
        <b>代码地图</b>
        <span>三个进程、三套目录，通过 HTTP 契约连接</span>
      </div>
      <div class="code-grid">
        <div v-for="c in codeMap" :key="c.title" class="code-card">
          <b>{{ c.title }}</b>
          <pre>{{ c.items.join('\n') }}</pre>
        </div>
      </div>
    </section>

    <!-- 关键原则 -->
    <section class="arch-card principle-card fade-up">
      <div class="section-head">
        <b>几条不越界的规矩</b>
        <span>也是面试时最能讲清设计判断的地方</span>
      </div>
      <div class="principles">
        <span v-for="p in principles" :key="p">{{ p }}</span>
      </div>
      <p class="principle-note">
        AI 不直接拍板：它给初判与依据，审核员终审并可改判；字数、标签这类客观约束由程序算，
        模型不可用时转人工，不阻断业务。
      </p>
    </section>

    <!-- 性能实测 -->
    <section class="arch-card perf-card fade-up">
      <div class="section-head">
        <b>性能实测</b>
        <span>单机演示环境 · 2026-10-29 · 详见 docs/性能与优化/性能优化实验.md</span>
      </div>
      <div class="perf-grid">
        <div class="perf-item">
          <b>3.2s</b>
          <span>单次预检</span>
          <small>模型调用占 98%</small>
        </div>
        <div class="perf-item">
          <b>4–5s</b>
          <span>三平台适配</span>
          <small>按平台并行；串行 12.7s</small>
        </div>
        <div class="perf-item">
          <b>≈1.0GB</b>
          <span>演示模式内存</span>
          <small>jar + preview + MySQL Private</small>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.arch {
  max-width: 1280px;
  margin: 0 auto;
}

.arch-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 6px 4px 22px;
}

.kicker {
  color: var(--app-muted);
  font-size: 10px;
  letter-spacing: 0.22em;
}

.arch-hero h1 {
  margin: 8px 0 6px;
  font-family: var(--app-serif);
  font-size: 30px;
  font-weight: 600;
}

.arch-hero p {
  margin: 0;
  color: var(--app-muted);
  font-size: 13.5px;
}

.arch-card {
  background: var(--app-surface);
  border: 1px solid var(--app-line);
  border-radius: 18px;
  box-shadow: 0 10px 30px rgba(38, 49, 47, 0.045);
}

.zoom-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.zoom-item {
  position: relative;
  padding: 13px 15px;
  border-radius: 13px;
  border: 1px solid var(--app-line);
  background: rgba(255, 253, 248, 0.72);
}

.zoom-item span {
  color: var(--app-gold);
  font-family: var(--app-serif);
  font-size: 11px;
  letter-spacing: 0.08em;
}

.zoom-item b {
  display: block;
  margin: 4px 0 3px;
  font-family: var(--app-serif);
  font-size: 13px;
}

.zoom-item p {
  margin: 0;
  color: var(--app-muted);
  font-size: 10.5px;
  line-height: 1.6;
}

.zoom-item i {
  position: absolute;
  right: -11px;
  top: 50%;
  transform: translateY(-50%);
  color: #c3b6a5;
  font-style: normal;
  z-index: 1;
}

.topology {
  display: flex;
  align-items: stretch;
  gap: 8px;
  padding: 20px;
}

.node {
  flex: 1;
  min-width: 0;
  position: relative;
  padding: 16px 16px 14px;
  border-radius: 14px;
  background: #fbf7ef;
  border: 1px solid #eee6da;
}

.node-main {
  background: linear-gradient(160deg, #1f5a54, #17433e);
  border-color: #1f5a54;
  color: #f4e8d6;
}

.node-agent {
  background: #f3e8d7;
  border-color: #e6d2b4;
}

.node-model {
  background: #f7f3ec;
}

.node-kicker {
  display: block;
  color: #a2988a;
  font-size: 8.5px;
  letter-spacing: 0.18em;
  margin-bottom: 6px;
}

.node-main .node-kicker {
  color: #a9c0b9;
}

.node b {
  display: block;
  font-family: var(--app-serif);
  font-size: 16px;
  font-weight: 600;
}

.node p {
  margin: 5px 0 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: #6d6458;
}

.node-main p,
.node-main small {
  color: #cfe0db;
}

.node small {
  display: block;
  margin-top: 6px;
  color: #a2988a;
  font-size: 10.5px;
}

.data-chip {
  margin-top: 10px;
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  color: #f3e8d7;
  font-size: 10px;
}

.arrow {
  align-self: center;
  color: #b08a5a;
  font-size: 18px;
  flex-shrink: 0;
}

.flow-section {
  margin-top: 16px;
  padding: 20px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head b {
  font-family: var(--app-serif);
  font-size: 17px;
  font-weight: 600;
}

.section-head span {
  color: var(--app-muted);
  font-size: 11.5px;
}

.flow {
  display: flex;
  align-items: stretch;
  gap: 8px;
}

.flow-step {
  flex: 1;
  min-width: 0;
  padding: 14px 14px 12px;
  border-radius: 12px;
  background: #fbf7ef;
  border: 1px solid #f0e9df;
}

.flow-no {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--app-gold-soft);
  color: #8a6a42;
  font-family: var(--app-serif);
  font-size: 12px;
  margin-bottom: 8px;
}

.flow-step b {
  display: block;
  font-size: 13px;
}

.flow-step p {
  margin: 4px 0 0;
  color: var(--app-muted);
  font-size: 11px;
  line-height: 1.6;
}

.flow-arrow {
  align-self: center;
  color: #c3b6a5;
}

.quote {
  margin-top: 14px;
  padding: 10px 14px;
  border-left: 3px solid var(--app-gold);
  background: #fdf8ef;
  color: #6d6458;
  font-size: 12px;
  line-height: 1.8;
}

.layer-section,
.code-section {
  margin-top: 22px;
}

.layer-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.layer-card {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--app-line);
  background: var(--app-surface);
  box-shadow: 0 8px 22px rgba(38, 49, 47, 0.035);
}

.layer-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.layer-no {
  font-family: var(--app-serif);
  color: #c3b6a5;
  font-size: 11px;
}

.layer-top b {
  font-family: var(--app-serif);
  font-size: 15px;
  font-weight: 600;
}

.layer-card p {
  margin: 7px 0 10px;
  color: var(--app-muted);
  font-size: 11.5px;
  line-height: 1.7;
}

.module-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 9px;
}

.module-list span {
  padding: 3px 8px;
  border-radius: 6px;
  background: #fffdf8;
  border: 1px solid #eee6da;
  color: #5f5548;
  font-size: 10px;
}

.interface-section {
  margin-top: 22px;
  padding: 20px;
}

.interface-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.interface-row {
  display: grid;
  grid-template-columns: 190px 120px minmax(0, 1fr) 230px;
  align-items: center;
  gap: 12px;
  padding: 11px 13px;
  border-radius: 11px;
  background: #fbf7ef;
  border: 1px solid #f0e9df;
}

.if-endpoints {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--app-ink);
  font-size: 11.5px;
}

.if-arrow {
  color: var(--app-gold);
}

.if-protocol {
  justify-self: start;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  font-size: 9.5px;
  white-space: nowrap;
}

.interface-row p {
  margin: 0;
  color: var(--app-muted);
  font-size: 10.5px;
  line-height: 1.7;
}

.if-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--app-muted);
  font-size: 9.5px;
  text-align: right;
}

.if-meta code {
  color: #8a7a66;
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: 9px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tags span {
  padding: 2px 8px;
  border-radius: 999px;
  background: #f4eee4;
  color: #7a6f61;
  font-size: 10px;
}

.code-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.code-card {
  padding: 16px;
  border-radius: 14px;
  background: #1b302d;
  color: #dce6e1;
  border: 1px solid #243b37;
}

.code-card b {
  font-family: var(--app-serif);
  font-size: 13.5px;
  color: #f4e8d6;
}

.code-card pre {
  margin: 10px 0 0;
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: 10.5px;
  line-height: 1.9;
  color: #b9c9c3;
  white-space: pre-wrap;
}

.principle-card {
  margin-top: 22px;
  padding: 20px;
}

.principles {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.principles span {
  padding: 5px 12px;
  border-radius: 999px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  font-size: 11.5px;
}

.principle-note {
  margin: 14px 0 0;
  color: var(--app-muted);
  font-size: 12px;
  line-height: 1.9;
}

.perf-card {
  margin-top: 22px;
  padding: 20px;
}

.perf-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.perf-item {
  display: flex;
  flex-direction: column;
  padding: 15px 16px;
  border-radius: 12px;
  background: #fbf7ef;
  border: 1px solid #f0e9df;
}

.perf-item b {
  font-family: var(--app-serif);
  font-size: 26px;
  font-weight: 600;
  color: var(--app-primary);
}

.perf-item span {
  margin-top: 4px;
  color: var(--app-ink);
  font-size: 12px;
}

.perf-item small {
  margin-top: 2px;
  color: var(--app-muted);
  font-size: 10.5px;
}

@media (max-width: 1000px) {
  .topology {
    flex-direction: column;
  }

  .arrow {
    transform: rotate(90deg);
    align-self: flex-start;
    margin-left: 20px;
  }

  .flow {
    flex-direction: column;
  }

  .flow-arrow {
    transform: rotate(90deg);
    align-self: flex-start;
    margin-left: 16px;
  }

  .layer-grid,
  .code-grid {
    grid-template-columns: 1fr;
  }

  .zoom-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .interface-row {
    grid-template-columns: 1fr;
    gap: 7px;
  }

  .if-meta {
    text-align: left;
  }

  .perf-grid {
    grid-template-columns: 1fr;
  }
}
</style>
