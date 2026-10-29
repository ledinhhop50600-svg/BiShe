<script setup>
import { ref } from 'vue'

/**
 * 需求与功能设计（静态说明页）。
 * 从“角色 × 功能”到“子模块 × 接口 × 代码”，把每个功能落到可指认的位置。
 * 内容与仓库当前实现保持一致；点击模块卡片可打开详细设计抽屉。
 */
const drawer = ref(false)
const activeModule = ref(null)

const roles = [
  { key: 'admin', name: '管理员', desc: '平台治理、全量数据与评测' },
  { key: 'reviewer', name: '审核员', desc: '审核、举报、规则与敏感词' },
  { key: 'creator', name: '创作者', desc: '创作、预检、适配与广场' },
]

const moduleGroups = [
  {
    title: '账号与治理',
    desc: '先把“谁能进来、能做什么”定清楚，后面的业务才有边界。',
    modules: [
      {
        key: 'auth',
        no: '01',
        name: '认证与个人中心',
        short: '认证/个人',
        subtitle: '登录、注册、资料与改密',
        access: { admin: 'full', reviewer: 'full', creator: 'full' },
        sub: ['账号密码登录', '算式验证码注册', '个人资料', '修改密码', '登出', '当前用户'],
        summary: '登录成功后一次返回角色、权限和菜单树；前端不再二次拼装，也没有把权限写死在前端。',
        flow: ['按账号查用户', 'BCrypt 校验密码', '检查账号状态', 'Sa-Token 签发令牌', '组装角色/权限/菜单'],
        apis: ['POST /api/auth/login', 'POST /api/auth/register', 'GET /api/auth/captcha', 'GET /api/auth/me', 'PUT /api/profile', 'PUT /api/profile/password'],
        code: ['AuthController / AuthServiceImpl', 'ProfileController / ProfileServiceImpl', 'StpInterfaceImpl', 'Login.vue / profile/index.vue'],
        tables: ['sys_user', 'sys_role', 'sys_user_role', 'sys_role_menu', 'sys_menu'],
        snippet: `StpUtil.login(user.getId());
return new LoginVO(
    StpUtil.getTokenName(),
    StpUtil.getTokenValue(),
    buildUserInfo(user)
);`,
        notes: ['账号不存在与密码错误返回同一句提示，避免枚举账号', '注册固定分配创作者角色，不能自选角色', '改密后当前令牌立即失效，强制重新登录'],
      },
      {
        key: 'system',
        no: '02',
        name: '用户与权限',
        short: '用户/权限',
        subtitle: '用户、角色、菜单与按钮权限',
        access: { admin: 'full', reviewer: 'none', creator: 'none' },
        sub: ['用户管理', '角色管理', '菜单管理', '角色-菜单授权', '按钮权限标识', '数据权限'],
        summary: '用户-角色-菜单三张关联表驱动权限；接口注解是真正的边界，前端守卫与 v-perm 只是体验层。',
        flow: ['管理员配置菜单/按钮', '给角色分配菜单', '给用户分配角色', '登录时汇总权限', '接口注解/前端指令校验'],
        apis: ['/api/user/**', '/api/role/**', '/api/menu/**'],
        code: ['UserController / RoleController / MenuController', 'SaTokenConfig / StpInterfaceImpl', 'system/user|role|menu'],
        tables: ['sys_user', 'sys_role', 'sys_menu', 'sys_user_role', 'sys_role_menu'],
        snippet: `@SaCheckPermission("system:user")
@GetMapping("/page")
public Result<PageResult<SysUser>> page(...) {
    return Result.ok(userService.page(...));
}`,
        notes: ['权限三层：路由守卫（页面）→ v-perm（按钮）→ @SaCheckPermission（接口）', '菜单类型 F 只参与权限校验，不进入导航', '改权限只改数据，不用改代码或重新部署'],
      },
    ],
  },
  {
    title: '内容与审核',
    desc: '系统的核心业务：稿件从创作到发布，智能体在提交与发布前介入，人保留终审权。',
    modules: [
      {
        key: 'content',
        no: '03',
        name: '内容创作',
        short: '内容/稿件',
        subtitle: '稿件状态机、投稿、广场',
        access: { admin: 'full', reviewer: 'part', creator: 'full' },
        sub: ['我的稿件', '投稿/保存草稿', '编辑并重审', '提交/撤回', '删除草稿', '内容广场'],
        summary: '稿件状态为 0 草稿 / 1 待审 / 2 已发布 / 3 驳回 / 4 屏蔽 / 5 下架；已发布或已下架编辑后立即回到待审，避免绕过审核改线上内容。',
        flow: ['保存草稿（0）', '提交审核（1）', '审核通过（2）/ 驳回（3）', '编辑已发布 → 回到待审（1）', '下架（5）或屏蔽（4）'],
        apis: ['GET /api/article/my', 'POST /api/article', 'PUT /api/article', 'POST /api/article/{id}/submit', 'POST /api/article/{id}/withdraw', 'GET /api/article/plaza'],
        code: ['ArticleController / ArticleServiceImpl', 'creator/article|submit|plaza'],
        tables: ['biz_article', 'biz_article_tag', 'biz_tag', 'biz_category'],
        snippet: `boolean resubmit = article.getStatus() == STATUS_PUBLISHED
        || article.getStatus() == STATUS_OFFLINE;
if (resubmit) {
    update.setStatus(STATUS_PENDING);
    update.setRiskLevel(-1);
    update.setRejectReason("");
}`,
        notes: ['新建稿件一律是草稿，不能直接发布', '删除只允许草稿（管理员例外）', '待审稿件要先撤回才能编辑', '编辑已发布清空旧风险等级，旧结论按内容哈希判定过期'],
      },
      {
        key: 'audit',
        no: '04',
        name: '智能审核与人机协同',
        short: '审核',
        subtitle: '初审、采纳/改判、规则库',
        access: { admin: 'full', reviewer: 'full', creator: 'none' },
        sub: ['待审队列', 'Agent 初审', '采纳建议', '改判', '审核记录', '规则库', '敏感词库'],
        summary: '智能体只做初判并给出依据，审核员终审；采纳/改判/人工三条路径都留痕，改判原因必填。',
        flow: ['工作台拉待审', '组装稿件 + 平台 + 规则 + 敏感词', '调用 Agent', '落 audit_record', '审核员采纳/改判', '更新稿件状态'],
        apis: ['GET /api/article/page?status=1', 'POST /api/article/{id}/agent-audit', 'PUT /api/article/{id}/review', 'GET /api/audit/records', '/api/rule/**', '/api/sensitive/**'],
        code: ['AuditAgentService', 'AuditRecordServiceImpl', 'ArticleServiceImpl.review', 'agent/judge.py', 'audit/workbench'],
        tables: ['audit_record', 'audit_review', 'audit_rule', 'audit_sensitive_word', 'biz_article'],
        snippet: `Map<String, Object> result = agentClient.audit(request);
if (AuditTriggerType.of(triggerType) == AuditTriggerType.POST_AUDIT) {
    Long recordId = auditRecordService.saveAgentResult(
        article.getId(), triggerType, null, contentHash, result, false, null);
    result.put("auditRecordId", recordId);
}`,
        notes: ['Agent 不可用时写 agent-failed 记录并转人工，不阻断业务', '审核员不能审核自己投稿的稿件', '发布前预检不落库，避免污染审核记录', '内容修改后旧结论按 content_hash 标记过期'],
      },
      {
        key: 'report',
        no: '05',
        name: '举报处理',
        short: '举报',
        subtitle: '广场举报与下架兜底',
        access: { admin: 'full', reviewer: 'full', creator: 'part' },
        sub: ['提交举报', '举报列表', '正文核实', '成立/驳回', '处理备注', '稿件下架'],
        summary: '创作者在内容广场举报已发布稿件；审核员看到正文与敏感词检测结果后判断，举报成立会自动把稿件改为已下架。',
        flow: ['广场打开全文', '填写举报理由', '审核员核实正文', '成立（1）/ 不成立（2）', '成立时稿件下架（5）'],
        apis: ['POST /api/report', 'GET /api/report/page', 'PUT /api/report/{id}/handle'],
        code: ['ReportController / ReportServiceImpl', 'creator/plaza', 'content/report'],
        tables: ['biz_report', 'biz_article'],
        snippet: `if (dto.getStatus() == REPORT_VALID) {
    BizArticle article = articleMapper.selectById(report.getArticleId());
    if (article != null && article.getStatus() == ARTICLE_PUBLISHED) {
        articleUpdate.setStatus(ARTICLE_OFFLINE);
    }
}`,
        notes: ['只能举报已发布稿件，不能举报自己的稿件', '同一人对同一篇只能有一条待处理举报', '举报成立是发布后的最后一道兜底'],
      },
    ],
  },
  {
    title: '创作与适配',
    desc: '同一篇内容按目标平台改写，并用目标平台规则做一次合规预检。',
    modules: [
      {
        key: 'adapt',
        no: '06',
        name: '跨平台内容适配',
        short: '适配',
        subtitle: '小红书/公众号/微博/B站/抖音',
        access: { admin: 'part', reviewer: 'full', creator: 'full' },
        sub: ['平台约束管理', '选择目标平台', '并行改写', '格式自检', '合规预检', '历史版本/复制'],
        summary: '每个平台一次改写 + 一次合规预检；默认按平台并行，响应里保留每个平台的改写/合规耗时。',
        flow: ['选择稿件与平台', '组装平台约束 + 适用规则', '按平台并行改写', '程序格式自检', '目标平台合规预检', '落库留版本'],
        apis: ['POST /api/article/{id}/adapt', 'GET /api/article/{id}/adaptations', 'GET/PUT /api/platform/**'],
        code: ['AdaptController / AdaptServiceImpl', 'agent/api/adapt.py', 'agent/prompts.py', 'agent/format_check.py', 'creator/adapt'],
        tables: ['audit_adaptation', 'audit_platform', 'audit_rule', 'biz_article'],
        snippet: `with ThreadPoolExecutor(max_workers=min(4, len(keys))) as ex:
    outputs = list(ex.map(task, keys))

# task: 改写 → 清理重复标签 → 截断 → 格式自检 → 合规预检`,
        notes: ['一次最多 5 个平台；本平台不是适配目标', '格式自检是程序算的，不交给模型', '一个平台失败会让整个请求失败，未做部分成功', '并行更吃并发，限流时更容易 429'],
      },
    ],
  },
  {
    title: '数据与评测',
    desc: '把业务数据变成可读的趋势，把实验结果变成可复现的证据。',
    modules: [
      {
        key: 'dashboard',
        no: '07',
        name: '数据看板',
        short: '看板',
        subtitle: '角色化 KPI 与趋势',
        access: { admin: 'full', reviewer: 'full', creator: 'full' },
        sub: ['角色 KPI', '14 天投稿/发布趋势', '状态/风险/处理分布', '平台适配次数', '最近审核/稿件', '脉搏指标'],
        summary: '同一个接口按角色返回不同 scope：管理员看全站，审核员看任务，创作者只看自己的稿件。',
        flow: ['登录角色', '后端按 scope 聚合', '前端 ECharts 渲染', '不重算指标'],
        apis: ['GET /api/dashboard/overview'],
        code: ['DashboardController / DashboardServiceImpl', 'dashboard/index.vue', 'ChartBox.vue'],
        tables: ['biz_article', 'audit_record', 'audit_review', 'audit_adaptation'],
        snippet: `// DashboardServiceImpl：按当前用户角色决定 scope 与卡片
Map<String, Object> out = new LinkedHashMap<>();
out.put("scope", scope);
out.put("cards", cards);
out.put("trend", trend);`,
        notes: ['创作者看不到全站用户数/稿件数', '14 天窗口是为了让演示数据也能看出趋势', '看板只展示，不重算指标'],
      },
      {
        key: 'eval',
        no: '08',
        name: '评测与优化中心',
        short: '评测',
        subtitle: '对比实验、适配质量、性能优化',
        access: { admin: 'full', reviewer: 'none', creator: 'none' },
        sub: ['审核方案对比', '分层准确率曲线', '适配质量雷达', '性能/速度优化', '演示运行', '数据明细'],
        summary: '数据来自 docs/ 下的实验产物；页面只展示与对比，不在前端重算。演示批次写 demo 目录，不覆盖论文数据。',
        flow: ['脚本生成 JSON', 'EvalController 读取', 'ECharts 渲染', '明细收在数据页'],
        apis: ['GET /api/eval/results', 'POST /api/eval/run-adaptation'],
        code: ['EvalController', 'tools/experiment_compare.py', 'tools/eval_adaptation.py', 'eval/index.vue'],
        tables: ['docs/eval/*.json', 'docs/perf/*.json'],
        snippet: `out.put("audit", readJson("docs/eval/audit-results.json"));
out.put("adaptation", readJson("docs/eval/adaptation-results.json"));
out.put("speed", readJson("docs/perf/speed-experiment.json"));`,
        notes: ['演示运行加锁，避免并发跑两份模型调用', '固定 run-id 复用回放缓存，但不能混入论文批次', '图表与报告使用同一份数据'],
      },
    ],
  },
  {
    title: '系统说明',
    desc: '把“怎么设计、为什么这样设计”做成可以边指边讲的页面。',
    modules: [
      {
        key: 'design',
        no: '09',
        name: '需求与架构说明',
        short: '说明',
        subtitle: '需求、架构、性能基线',
        access: { admin: 'full', reviewer: 'full', creator: 'full' },
        sub: ['需求与功能设计', '架构分层与接口', '性能基线'],
        summary: '静态说明页，不查数据库；所有登录用户可看，用来支撑答辩和面试讲解。',
        flow: ['角色 × 功能矩阵', '模块 → 子模块 → 接口 → 代码', '架构分层与通讯', '实测性能'],
        apis: ['无（前端静态路由）'],
        code: ['views/design/requirements.vue', 'views/architecture/index.vue'],
        tables: [],
        snippet: `router.push('/design/requirements')
router.push('/architecture')`,
        notes: ['设计页不是业务菜单，所有登录用户可看', '页面内容与代码目录同步维护', '图表只做解释，不作为运行时依赖'],
      },
    ],
  },
]

const allModules = moduleGroups.flatMap((group) => group.modules)

const flows = [
  {
    title: '投稿 → 审核 → 发布',
    accent: 'primary',
    steps: ['创作者写稿', '发布前 AI 预检', '提交审核', '审核员工作台', 'Agent 初审', '采纳/改判', '发布或驳回'],
  },
  {
    title: '选稿 → 适配 → 合规',
    accent: 'gold',
    steps: ['选择稿件', '选择目标平台', '按平台并行改写', '程序格式自检', '目标平台合规预检', '复制/留版本'],
  },
  {
    title: '登录 → 权限 → 接口',
    accent: 'sage',
    steps: ['登录签发令牌', '后端组装权限/菜单', '路由守卫', 'v-perm 按钮', '接口注解校验'],
  },
]

const designs = [
  { title: '三层权限', desc: '页面、按钮、接口各一道；只有接口注解是真正的安全边界。' },
  { title: '稿件状态机', desc: '状态数字存库、常量表达意图；已发布编辑即回到待审。' },
  { title: '两阶段 Agent', desc: '提交时初审、发布前预检；上下文由主系统下发，智能体不连库。' },
  { title: '人机协同', desc: '采纳/改判/人工三路留痕，改判原因必填，不把终审交给模型。' },
  { title: '内容哈希过期', desc: '稿件改动后旧审核结论自动标记过期，避免拿旧结论放行新内容。' },
  { title: '失败降级', desc: 'Agent 不可用写 agent-failed 并转人工，业务不中断。' },
  { title: '并行适配', desc: '平台之间互不依赖，ThreadPoolExecutor 并行；代价是并发与限流。' },
  { title: '角色化数据', desc: '看板与列表都按角色/作者过滤，越权数据不返回。' },
]

function openModule(module) {
  activeModule.value = module
  drawer.value = true
}

function symbol(value) {
  return value === 'full' ? '●' : value === 'part' ? '◐' : '—'
}

function pad(value) {
  return String(value).padStart(2, '0')
}

function accessLabel(module, role) {
  const value = module.access[role.key]
  return `${role.name} · ${module.name}：${value === 'full' ? '完整' : value === 'part' ? '部分' : '无'}`
}
</script>

<template>
  <div class="requirements">
    <header class="req-hero">
      <div>
        <div class="kicker">REQUIREMENTS & FUNCTION DESIGN</div>
        <h1>需求与功能设计</h1>
        <p>从角色能做什么，到每个按钮落到哪个接口、哪张表、哪段代码。点击模块卡片查看详细设计。</p>
      </div>
      <div class="req-stats">
        <div><b>3</b><span>角色</span></div>
        <div><b>9</b><span>功能模块</span></div>
        <div><b>16</b><span>数据表</span></div>
        <div><b>3</b><span>进程</span></div>
      </div>
    </header>

    <!-- 角色 × 功能矩阵 -->
    <section class="req-card">
      <div class="section-head">
        <div><h2>角色 × 功能矩阵</h2><p>● 完整可用　◐ 部分能力　— 无权限；权限最终由后端接口注解校验。</p></div>
        <span class="legend">管理员 / 审核员 / 创作者</span>
      </div>
      <div class="matrix-wrap">
        <div class="matrix">
          <div class="matrix-row head">
            <span>角色</span>
            <b v-for="m in allModules" :key="m.key">{{ m.short }}</b>
          </div>
          <div v-for="role in roles" :key="role.key" class="matrix-row">
            <span class="role-name">{{ role.name }}<small>{{ role.desc }}</small></span>
            <i
              v-for="m in allModules"
              :key="m.key"
              :class="m.access[role.key]"
              :title="accessLabel(m, role)"
            >{{ symbol(m.access[role.key]) }}</i>
          </div>
        </div>
      </div>
    </section>

    <!-- 功能模块 -->
    <section v-for="group in moduleGroups" :key="group.title" class="group-block">
      <div class="section-head">
        <div><h2>{{ group.title }}</h2><p>{{ group.desc }}</p></div>
        <span class="count">{{ group.modules.length }} 个模块</span>
      </div>
      <div class="module-grid">
        <button v-for="m in group.modules" :key="m.key" class="module-card" @click="openModule(m)">
          <div class="module-top">
            <span class="module-no">{{ m.no }}</span>
            <span class="module-name">{{ m.name }}</span>
            <span class="module-arrow">↗</span>
          </div>
          <p class="module-subtitle">{{ m.subtitle }}</p>
          <div class="module-sub">
            <span v-for="s in m.sub.slice(0, 4)" :key="s">{{ s }}</span>
            <span v-if="m.sub.length > 4" class="more">+{{ m.sub.length - 4 }}</span>
          </div>
          <div class="module-roles">
            <span v-for="role in roles" :key="role.key" :class="{ on: m.access[role.key] !== 'none' }">
              {{ role.name }}
            </span>
          </div>
        </button>
      </div>
    </section>

    <!-- 核心链路 -->
    <section class="req-card flow-card">
      <div class="section-head">
        <div><h2>三条核心链路</h2><p>把功能串起来看，才能解释“为什么这样拆”。</p></div>
      </div>
      <div class="flow-list">
        <div v-for="flow in flows" :key="flow.title" class="flow-line" :class="flow.accent">
          <b class="flow-title">{{ flow.title }}</b>
          <div class="flow-steps">
            <template v-for="(step, i) in flow.steps" :key="step">
              <span class="flow-step">{{ step }}</span>
              <i v-if="i < flow.steps.length - 1">→</i>
            </template>
          </div>
        </div>
      </div>
    </section>

    <!-- 关键设计 -->
    <section class="req-card">
      <div class="section-head">
        <div><h2>关键设计判断</h2><p>答辩时最容易被追问的八个点。</p></div>
      </div>
      <div class="design-grid">
        <div v-for="(d, i) in designs" :key="d.title" class="design-item">
          <span>{{ pad(i + 1) }}</span>
          <div><b>{{ d.title }}</b><p>{{ d.desc }}</p></div>
        </div>
      </div>
    </section>

    <!-- 详细设计抽屉 -->
    <el-drawer v-model="drawer" :title="activeModule?.name" size="540px" class="module-drawer">
      <div v-if="activeModule" class="drawer-body">
        <div class="drawer-kicker">MODULE {{ activeModule.no }}</div>
        <p class="drawer-summary">{{ activeModule.summary }}</p>

        <h4>子模块</h4>
        <div class="drawer-chips">
          <span v-for="s in activeModule.sub" :key="s">{{ s }}</span>
        </div>

        <h4>关键流程</h4>
        <ol class="drawer-flow">
          <li v-for="step in activeModule.flow" :key="step">{{ step }}</li>
        </ol>

        <h4>接口</h4>
        <div class="api-list">
          <code v-for="api in activeModule.apis" :key="api">{{ api }}</code>
        </div>

        <h4>代码位置</h4>
        <div class="code-refs">
          <span v-for="c in activeModule.code" :key="c">{{ c }}</span>
        </div>

        <template v-if="activeModule.tables?.length">
          <h4>涉及数据表</h4>
          <div class="table-tags">
            <span v-for="t in activeModule.tables" :key="t">{{ t }}</span>
          </div>
        </template>

        <h4>核心实现</h4>
        <pre class="snippet">{{ activeModule.snippet }}</pre>

        <h4>边界与细节</h4>
        <ul class="drawer-notes">
          <li v-for="n in activeModule.notes" :key="n">{{ n }}</li>
        </ul>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.requirements {
  max-width: 1320px;
  margin: 0 auto;
  padding-bottom: 30px;
}

.req-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 6px 4px 22px;
}

.kicker {
  color: var(--app-gold);
  font-size: 10px;
  letter-spacing: 0.22em;
  font-weight: 700;
}

.req-hero h1 {
  margin: 8px 0 6px;
  font-family: var(--app-serif);
  font-size: 30px;
  font-weight: 600;
}

.req-hero p {
  margin: 0;
  max-width: 680px;
  color: var(--app-muted);
  font-size: 13px;
  line-height: 1.8;
}

.req-stats {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.req-stats div {
  min-width: 64px;
  padding: 9px 12px;
  border: 1px solid var(--app-line);
  border-radius: 12px;
  background: rgba(255, 253, 248, 0.72);
  text-align: center;
}

.req-stats b {
  display: block;
  color: var(--app-primary);
  font-family: var(--app-serif);
  font-size: 21px;
  line-height: 1.1;
}

.req-stats span {
  color: var(--app-muted);
  font-size: 9.5px;
}

.req-card {
  padding: 20px;
  margin-bottom: 18px;
  border: 1px solid var(--app-line);
  border-radius: 18px;
  background: var(--app-surface);
  box-shadow: 0 10px 30px rgba(38, 49, 47, 0.04);
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.section-head h2 {
  margin: 0 0 4px;
  font-family: var(--app-serif);
  font-size: 18px;
  font-weight: 600;
}

.section-head p {
  margin: 0;
  color: var(--app-muted);
  font-size: 11px;
  line-height: 1.7;
}

.legend,
.count {
  flex-shrink: 0;
  color: var(--app-muted);
  font-size: 10px;
}

.matrix-wrap {
  overflow-x: auto;
}

.matrix {
  min-width: 860px;
}

.matrix-row {
  display: grid;
  grid-template-columns: 170px repeat(9, minmax(62px, 1fr));
  align-items: center;
  gap: 4px;
  padding: 8px 6px;
  border-bottom: 1px solid #f1eae0;
}

.matrix-row.head {
  border-bottom: 1px solid var(--app-line);
  color: var(--app-muted);
  font-size: 10px;
}

.matrix-row.head span {
  font-size: 10px;
}

.matrix-row.head b {
  text-align: center;
  font-weight: 500;
  font-size: 9.5px;
  white-space: nowrap;
}

.role-name {
  display: flex;
  flex-direction: column;
  color: var(--app-ink);
  font-size: 12px;
  font-weight: 600;
}

.role-name small {
  margin-top: 2px;
  color: var(--app-muted);
  font-size: 9px;
  font-weight: 400;
}

.matrix-row i {
  justify-self: center;
  font-style: normal;
  font-size: 14px;
}

.matrix-row i.full {
  color: var(--app-primary);
}

.matrix-row i.part {
  color: var(--app-gold);
}

.matrix-row i.none {
  color: #d6cdc0;
}

.group-block {
  margin-bottom: 18px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.module-card {
  display: block;
  width: 100%;
  padding: 15px 16px 14px;
  border: 1px solid var(--app-line);
  border-radius: 14px;
  background: var(--app-surface);
  text-align: left;
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.module-card:hover {
  transform: translateY(-2px);
  border-color: #d9c9b3;
  box-shadow: 0 12px 28px rgba(38, 49, 47, 0.07);
}

.module-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.module-no {
  color: var(--app-gold);
  font-family: var(--app-serif);
  font-size: 11px;
}

.module-name {
  color: var(--app-ink);
  font-family: var(--app-serif);
  font-size: 14px;
  font-weight: 600;
}

.module-arrow {
  margin-left: auto;
  color: #c3b6a5;
  font-size: 13px;
}

.module-subtitle {
  margin: 6px 0 9px;
  color: var(--app-muted);
  font-size: 10.5px;
}

.module-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  min-height: 44px;
  align-content: flex-start;
}

.module-sub span {
  padding: 2px 7px;
  border-radius: 5px;
  background: #f7f1e7;
  color: #6d6458;
  font-size: 9.5px;
}

.module-sub .more {
  color: var(--app-muted);
  background: transparent;
}

.module-roles {
  display: flex;
  gap: 5px;
  margin-top: 9px;
}

.module-roles span {
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid #eee6da;
  color: #b9ac9b;
  font-size: 9px;
}

.module-roles span.on {
  border-color: #c9dbd2;
  background: var(--app-primary-soft);
  color: var(--app-primary);
}

.flow-card {
  padding-bottom: 16px;
}

.flow-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.flow-line {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  padding: 11px 13px;
  border-radius: 11px;
  background: #fbf7ef;
  border-left: 3px solid var(--app-primary);
}

.flow-line.gold {
  border-left-color: var(--app-gold);
}

.flow-line.sage {
  border-left-color: var(--app-sage);
}

.flow-title {
  color: var(--app-ink);
  font-size: 11.5px;
}

.flow-steps {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.flow-step {
  padding: 3px 8px;
  border-radius: 6px;
  background: #fffdf8;
  border: 1px solid #eee6da;
  color: #5f5548;
  font-size: 9.5px;
}

.flow-steps i {
  color: #c3b6a5;
  font-style: normal;
  font-size: 10px;
}

.design-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.design-item {
  display: flex;
  gap: 9px;
  padding: 12px 13px;
  border-radius: 11px;
  background: #fbf7ef;
  border: 1px solid #f0e9df;
}

.design-item > span {
  color: var(--app-gold);
  font-family: var(--app-serif);
  font-size: 11px;
}

.design-item b {
  display: block;
  margin-bottom: 3px;
  color: var(--app-ink);
  font-size: 11px;
}

.design-item p {
  margin: 0;
  color: var(--app-muted);
  font-size: 9.5px;
  line-height: 1.7;
}

.drawer-body {
  padding: 0 4px 20px;
}

.drawer-kicker {
  color: var(--app-gold);
  font-size: 9px;
  letter-spacing: 0.2em;
}

.drawer-summary {
  margin: 9px 0 16px;
  color: var(--app-ink-2);
  font-size: 12px;
  line-height: 1.9;
}

.drawer-body h4 {
  margin: 16px 0 7px;
  color: var(--app-ink);
  font-family: var(--app-serif);
  font-size: 13px;
}

.drawer-chips,
.code-refs,
.table-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.drawer-chips span,
.code-refs span,
.table-tags span {
  padding: 3px 8px;
  border-radius: 6px;
  background: #f7f1e7;
  color: #6d6458;
  font-size: 10px;
}

.code-refs span {
  background: var(--app-primary-soft);
  color: var(--app-primary);
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: 9.5px;
}

.table-tags span {
  background: #f3e8d7;
  color: #8a6a42;
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: 9.5px;
}

.drawer-flow {
  margin: 0;
  padding-left: 18px;
  color: var(--app-ink-2);
  font-size: 11px;
  line-height: 1.9;
}

.api-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.api-list code {
  display: block;
  padding: 5px 8px;
  border-radius: 5px;
  background: #f7f1e7;
  color: #5f5548;
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: 9.5px;
}

.snippet {
  margin: 0;
  padding: 12px 13px;
  border-radius: 9px;
  background: #1b302d;
  color: #dce6e1;
  font-family: "Cascadia Code", Consolas, monospace;
  font-size: 9.5px;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-x: auto;
}

.drawer-notes {
  margin: 0;
  padding-left: 18px;
  color: var(--app-muted);
  font-size: 10.5px;
  line-height: 1.9;
}

@media (max-width: 1100px) {
  .module-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .design-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 800px) {
  .req-hero {
    flex-direction: column;
    align-items: flex-start;
  }
  .module-grid,
  .design-grid {
    grid-template-columns: 1fr;
  }
  .flow-line {
    grid-template-columns: 1fr;
  }
  .req-stats {
    flex-wrap: wrap;
  }
}
</style>
