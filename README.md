# 自媒体平台管理系统（SpringBoot + Vue + 单智能体）

> 一个面向多平台内容创作、**智能审核**与**跨平台适配**的管理系统。
> 毕业设计项目：把"单智能体"真正接进业务流程 —— 不是聊天框，而是参与审核、预检与内容改写。

---

## 一、它能做什么

系统有三种角色，各自看到不同的菜单与数据：

| 角色 | 能做什么 |
|---|---|
| **创作者** | 注册/登录、写稿、**发布前 AI 预检**、提交审核、看违规片段与修改建议、修改重提、**跨平台适配**（小红书/公众号/微博/B站/抖音）、查看适配历史 |
| **审核员** | 待审队列、**智能体初审**（等级/理由/命中规则/违规片段/建议）、采纳或改判（改判原因必填）、审核记录、举报处理 |
| **管理员** | 用户/角色/菜单、稿件/分类/举报、平台约束、审核规则库、数据看板、**评测中心** |

### 创新点（答辩主线）

1. **智能审核 Agent**：六类规则（广告法/虚假宣传/低俗/引流/违禁品/侵权）、四级分级
   （通过/疑似/违规/严重）、规则目录与引用校验（E1）、按平台规则预检、**人机协同终审**；
2. **跨平台内容适配**：同一篇稿件按目标平台改写（小红书短笔记、公众号长文、抖音口播脚本等），
   **程序做格式自检**（字数/标签），**复用审核规则做平台合规预检**，结果可复制、按版本留痕；
3. **可复现的实验**：428 条审核评测集（核心 28 + ToxiCN 200 + COLD 200）、七方案对比
   （关键词/纯大模型/原版 RAG/C1 紧凑 RAG/E2 后置归因/E1 最小规则目录/全量规则）、
   适配质量评估（格式满足率 + LLM 评分 + 人工评分），系统内有评测中心。

**明确不做**：不向真实平台发布（个人开发者拿不到各平台发布接口）、不做图片/视频审核、
没有短信/邮件服务。边界与理由见 `docs/decisions-multiplatform.md`、`docs/decisions-agent.md`。

### 界面与可视化（2026-10-29 优化）

- **视觉主题**：暖纸底 + 深青主色 + 铜金点缀；登录页左右分栏，侧边栏深青渐变，卡片/表格统一；
- **数据看板**：近 14 天投稿与发布趋势、稿件状态环图、智能体风险分布、人工处理分布、
  各平台适配次数、最近审核/稿件动态；按角色返回不同数据；
- **系统架构页** `/architecture`：拓扑图、一次审核的四步链路、六层分工、层间接口与通讯方式、代码地图、性能卡片；
- **需求设计页** `/design/requirements`：角色 × 功能矩阵、9 个模块/子模块、关键链路，点击模块可看接口、代码与实现细节；
- **评测与优化中心** `/eval`：审核对比（柱状/散点/分层曲线）、适配质量（雷达/压缩比/人工对照）、
  性能优化（并行耗时/思考强度/内存构成）与数据明细，全部用图表而不是表格堆砌；
- **性能报告** `docs/性能分析报告.md`：内存与耗时的实测拆分（模型调用占 98% 以上）；
- **优化实验** `docs/性能优化实验.md`：内存四个方向（前端/后端/MySQL/Agent）与适配并行、思考强度的代价。

---

## 二、技术栈

| 层 | 技术 |
|---|---|
| 后端 | Spring Boot 4.1.1、JDK 17、MyBatis-Plus 3.5.17（boot4 starter）、Sa-Token 1.46.0、BCrypt、MySQL 8.0 |
| 前端 | Vue 3.5、Vite 8、Element Plus 2.14、Pinia、Vue Router（JavaScript，非 TypeScript） |
| 智能体 | Python 3.11、FastAPI、uvicorn、openai SDK（OpenAI 兼容接口）、DeepSeek（可切换硅基流动/智谱） |
| 数据 | MySQL 8（16 张表）、Agent 侧无数据库（上下文由主系统下发） |
| 实验 | Python 脚本 + Agent 回放缓存；结果落在 `docs/eval/` 与 `docs/实验-*.md` |

> 选型理由、版本核对与替代方案见 `docs/decisions-stack.md`、`docs/技术栈白话说明.md`。

---

## 三、目录结构

```
.
├─ backend/                 SpringBoot 后端（端口 8080）
│  └─ src/main/java/com/zimeiti/
│     ├─ controller/        接口层
│     ├─ service/           业务与 Agent 编排
│     ├─ entity/ mapper/    数据访问
│     ├─ config/            Sa-Token、MyBatis-Plus、Agent HTTP 客户端
│     └─ common/            统一返回、异常、状态/等级常量
├─ frontend/                Vue 前端（端口 5173）
│  └─ src/
│     ├─ views/             登录、看板、系统、内容、审核、适配、评测、设计说明
│     ├─ api/               接口封装
│     ├─ stores/            Pinia 登录状态
│     ├─ directives/        v-perm 按钮权限
│     └─ router/            静态路由 + 权限守卫
├─ agent/                   智能体服务（FastAPI，端口 8001）
│  ├─ api/audit.py          审核 / 预检
│  ├─ api/adapt.py          跨平台适配
│  ├─ judge.py              判定核心（审核与适配预检共用）
│  ├─ rag.py                规则检索 / 关键词定位
│  ├─ prompts.py            系统提示词与平台形态
│  └─ format_check.py       程序侧格式自检
├─ db/                      建库、建表、种子数据、增量脚本
├─ docs/                    决策、设计、实验、测试、答辩材料
├─ tools/                   验证脚本、评测脚本、人工评分页生成
├─ start.bat                Windows 一键启动（GBK + CRLF）
└─ 文件/                    学校材料（开题报告等）
```

---

## 四、环境要求

| 依赖 | 版本 | 检查命令 |
|---|---|---|
| JDK | 17 | `java -version` |
| Maven | 3.9+ | `mvn -v` |
| MySQL | 8.0+ | `mysql --version` |
| Node.js | 22.18+ / 24.12+ | `node -v` |
| Python | 3.11 | `python --version` |

需要联网（调用 DeepSeek API）与一个 API Key。预算参考：审核约 0.002 元/条、
适配约 0.005-0.01 元/次（长文三平台约 0.03 元）。

---

## 五、快速启动

### 方式 A：一键启动（推荐）

1. 确认 MySQL 已启动（3306）；
2. 首次使用先初始化数据库（见下）；
3. 在 `agent/` 下准备好 `.venv` 与 `.env`（见下）；
4. **双击 `start.bat`**。脚本会检查 MySQL、启动后端/前端/Agent，等待约 25 秒后做健康检查，
   并打开 `http://localhost:5173/`。

> `start.bat` 使用 GBK + CRLF（cmd.exe 要求）。不要用编辑器另存为 UTF-8，否则中文会乱码。
> 本机 JDK17 / Maven 在 `F:\Dev\toolchains`，脚本顶部会自动检测并设置 `JAVA_HOME` / `PATH`；
> 换机器时改那两行，或把 `bin` 加入系统 PATH（系统默认的 Java 8 跑不了 Spring Boot 4）。
>
> **更低内存的启动方式**：先在 `backend/` 执行 `mvn -DskipTests package`，`start-low-memory.bat`
> 会优先运行打包好的 jar，不再保留 Maven 父进程（省约 225 MB）；没有 jar 时才退回 `mvn spring-boot:run`。
> 改完后端代码后要重新 `package`，脚本不会自动重编译。
> 前端演示可以在 `frontend/` 执行 `npm run build && npm run preview`（4173，约 98 MB，替代 222 MB 的 dev server）。

### 方式 B：手动启动

```bash
# 1) 数据库（首次）
mysql -u root -p < db/00_create_database.sql
mysql -u zimeiti -pzimeiti2026 --default-character-set=utf8mb4 zimeiti < db/02_schema.sql
mysql -u zimeiti -pzimeiti2026 --default-character-set=utf8mb4 zimeiti < db/03_seed.sql

# 2) 智能体（新开窗口）
cd agent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
#   编辑 .env，填 API_KEY；PROVIDER=deepseek 或 mock
.venv\Scripts\python -m uvicorn main:app --port 8001

# 3) 后端（新开窗口）
cd backend
mvn spring-boot:run

# 4) 前端（新开窗口）
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173/`。

> 已经是旧库时，再执行 `db/04_phase6.sql`、`db/05_phase7.sql` 两个增量脚本
> （新装环境不需要，`02_schema.sql` 已包含）。

### 演示账号（密码均为 `123456`）

| 账号 | 角色 |
|---|---|
| `admin` | 超级管理员 |
| `reviewer` | 审核员 |
| `creator` | 创作者 |
| `creator2` | 第二位创作者（举报/数据权限场景） |

也可以直接在登录页「立即注册」创建新的创作者账号（算式验证码，注册后自动登录）。

---

## 六、配置说明

### 后端 `backend/src/main/resources/application.properties`

- `spring.datasource.*`：数据库连接（默认 `zimeiti` / `zimeiti2026`）；
- `server.tomcat.threads.*` / `spring.datasource.hikari.*`：本地演示的低内存默认值（20/5 与 5/2）；
  多人并发或上生产时要按负载调大，不要直接沿用；
- `agent.base-url`：Agent 地址（默认 `http://localhost:8001`）；
- `agent.timeout-seconds`：审核读超时（30 秒）；适配用独立的 120 秒客户端；
- `eval.project-root`：评测中心读取 `docs/eval` 的根目录（默认 `..`，即从 `backend/` 启动）。

### Agent `agent/.env`（**不进版本库**）

```ini
PROVIDER=deepseek
API_KEY=sk-你的Key
BASE_URL=https://api.deepseek.com
MODEL=deepseek-flash
REASONING_EFFORT=none     # 必须关闭思考模式，否则长文可能输出为空
RAG_ENABLED=true
SILICONFLOW_API_KEY=      # bge-m3 向量检索用（可选；没有时降级为全量规则）
REPLAY_ENABLED=true       # 回放缓存，评测与断网演示用
```

> `.env.example` 只是模板，**真实 Key 只能放 `.env`**。仓库已忽略 `.env` 与 `.replay/`。

---

## 七、演示流程（5-8 分钟）

完整脚本见 `docs/答辩演示脚本.md`，主线：

1. 创作者登录 → 写一段"明显违规"的文案 → **发布前 AI 预检**（等级/规则/片段/建议）；
2. 修改后提交 → 审核员工作台 → **运行智能体初审** → 查看依据 → 采纳或改判（改判填原因）；
3. 创作者看反馈（片段高亮 + 修改建议）→ 修改重提 → 旧结论自动标记过期；
4. 创作者「跨平台适配」→ 选小红书/公众号/抖音 → 生成 → 格式自检 + 合规预检 → 复制；
5. 管理员看板（改判率、判定分布）→ 审核记录 → 评测中心（审核实验 + 适配评估）。

> 断网/无 Key 保底：把 `agent/.env` 的 `PROVIDER` 改为 `mock`，重启 Agent，
> 整条界面流程仍可走通（判定变为关键词模拟，适配返回截断版本）。

---

## 八、验证与实验

```bash
# 功能验证（需后端/Agent 已启动）
python tools/verify_stage7.py
python tools/verify_account_revision.py
python tools/verify_stage6.py

# 审核对比实验（428 条，7 方案；并发 10 约 15-20 分钟）
python tools/experiment_compare.py --rounds 1 --workers 10 --out docs/实验-对比实验-v5-扩展集.md

# 适配质量评估（4 篇 × 3 平台；约 2-3 分钟）
python tools/eval_adaptation.py --run-id paper --out-dir docs/eval

# 生成人工评分页面
python tools/make_human_review.py

# 人工评分一致性
python tools/analyze_human_scores.py

# 内存 / 耗时基线（需三端 + MySQL 运行）
python tools/perf_report.py

# 适配策略与思考强度对照（真实调用模型，约 1-2 分钟）
python tools/experiment_speed.py
```

实验结论与文件索引见 `docs/实验-总览.md`。

### 性能基线（2026-10-29 实测）

| 场景 | 总耗时 | 说明 |
|---|---|---|
| 智能体预检 | 3.2 s | 模型调用占 98%，检索命中缓存时接近 0 |
| 正式初审 | 4.5 s | 模型 + 落库 |
| 适配 1 / 3 平台 | 2.9 s / 4.4–4.8 s | 三平台按平台并行；串行时 12.7 s |
| 后端应用 JVM | RSS 173 MB | 小堆 + 串行 GC；`mvn spring-boot:run` 另有 Maven 父进程 256 MB |
| 前端 | dev 222 MB / preview 98 MB | 生产构建不需要 Vite dev server |
| 智能体 / MySQL | 75 MB / Private 664 MB | MySQL 的 `performance_schema` 约 231 MB，需全局配置才能降 |

应用口径常驻 RSS 约 515 MB；含 Maven 父进程约 771 MB；改用 jar + preview 的演示模式约 422 MB
（MySQL 按 Private 校正后约 1.0–1.4 GB）。完整拆分、四个方向与代价见
`docs/性能优化实验.md`，原始数据见 `docs/性能分析报告.md`。

---

## 九、文档索引

| 文档 | 内容 |
|---|---|
| `docs/系统功能说明.md` | 系统到底做什么、三种角色、场景 |
| `docs/数据库设计文档.md` | 16 张表、关系与设计取舍 |
| `docs/Agent接口契约-v1.md` | 审核/适配接口字段与错误码（v1.1） |
| `docs/人机协同设计说明.md` | 初审/采纳/改判/过期/统计口径 |
| `docs/适配规则与提示词设计说明.md` | 平台约束、提示词、格式自检 |
| `docs/decisions-*.md` | 关键决策与理由（多平台、技术栈、工作方式） |
| `docs/实验-总览.md` | 审核/适配实验结论汇总 |
| `docs/实验-对比实验-v5-扩展集.md` | 428 条扩展集、七方案原始结果 |
| `docs/实验-扩展集-C1-E2分析.md` | E1 规则目录 / C1 紧凑 RAG / E2 后置归因的取舍与核心/公开集拆分 |
| `docs/实验-速度优化.md` | 适配策略（串行/并行/统一/通用）与思考强度的原始数据 |
| `docs/性能分析报告.md` | 内存占用与耗时分配的实测报告 |
| `docs/性能优化实验.md` | 内存四个方向的尝试、并行适配与思考强度的代价 |
| `docs/测试用例与执行记录.md` | 测试用例与执行结果 |
| `docs/答辩问答-20问.md` | 高频问题与回答 |
| `docs/答辩演示脚本.md` | 演示顺序、话术、保底方案 |
| `docs/notes/阶段*-开发笔记.md` | 每个阶段的开发记录与踩坑 |
| `docs/notes/优化-界面与性能.md` | 视觉主题、看板、架构页与性能实测的记录 |
| `docs/notes/优化-评测与设计页.md` | 评测中心可视化、需求/架构设计页与对比实验复测记录 |

---

## 十、常见问题

**Q：启动后页面空白 / 接口 401？**
检查后端 8080 与前端 5173 是否都在运行；刷新页面会重新拉取用户信息，令牌失效会跳登录页。

**Q：智能体不可用怎么办？**
业务不会中断：预检会提示稍后重试，审核会写一条 `agent-failed` 记录并转人工。
检查 8001 是否在运行、`.env` 的 Key 是否有效；也可以切 `PROVIDER=mock` 做离线演示。

**Q：MySQL 连接失败？**
确认 3306 已启动、`zimeiti` 账号存在（`db/00_create_database.sql` 创建），
以及 `application.properties` 的密码正确。

**Q：端口被占用？**
关掉对应的旧窗口，或改 `server.port` / Vite 端口；`start.bat` 会跳过已在运行的服务。

**Q：C 盘空间不足？**
Maven/npm 缓存已指向 E 盘（见 `docs/decisions-*`）；如在新机器上，先设置
`MAVEN_OPTS`/`.m2/settings.xml` 与 `npm config set cache`。

**Q：想重置演示数据？**
重新执行 `db/02_schema.sql` + `db/03_seed.sql` 会重建全部表并恢复种子数据
（**会清空你新建的账号/稿件/审核记录**）。只想清测试稿件时，按 id 删除对应
`biz_article` / `audit_record` / `audit_review` / `audit_adaptation` 记录。

---

## 十一、安全与边界

- 密码使用 BCrypt 哈希；`SysUser.password` 带 `@JsonIgnore`，不会出现在接口返回里；
- 权限三层：路由守卫（页面）、`v-perm`（按钮）、`@SaCheckPermission`（接口，真正的边界）；
- 数据权限：创作者只能操作自己的稿件；审核员不能审自己的稿件；
- 注册固定分配创作者角色，验证码一次性、5 分钟过期；
- **这是本地演示项目**：没有 HTTPS、没有部署加固、没有短信/邮件、没有真实支付/发布；
  生产化需要补鉴权加固、限流、审计、异步任务、监控与平台合规评估。

---

## 十二、许可与致谢

- 公开评测数据：ToxiCN（ACL 2023，CC BY-NC-ND），仅用于学术评测，不进入演示流程；
- 规则来源：广告法、反不正当竞争法、网络信息内容生态治理规定及各平台公开社区规范，
  具体条款见规则库 `source` 字段；
- 本项目为毕业设计，代码与文档用于学习与答辩。
