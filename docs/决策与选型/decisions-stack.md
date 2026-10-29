# 技术选型决策记录（主题：stack）

## D-S1 选定方案：A —— 全手写 · 保守栈

- **结论**（最终技术栈）：

| 层 | 选型 | 版本/说明 |
|---|---|---|
| 后端框架 | Spring Boot | **4.1.1**（JDK 17） |
| 数据持久层 | MyBatis-Plus | ≥ 3.5.15，用 `mybatis-plus-spring-boot4-starter` |
| 认证授权 | Sa-Token | 1.46.0，用 `sa-token-spring-boot4-starter` |
| 数据库 | MySQL | 8.0.46（本机已装） |
| 前端框架 | Vue 3 + Vite | JavaScript（**不上 TypeScript**） |
| 前端组件与状态 | Element Plus 2.14.x + Pinia + Vue Router + Axios | |
| 智能体服务 | Python 3.11 + FastAPI + openai 官方 SDK | 独立 HTTP 服务，无状态 |
| 智能体内核 | 自研轻量 Agent 主循环 + 工具注册表 + 内存向量检索 | 不引入 LangGraph/LangChain 作为核心 |
| 大模型 | DeepSeek `deepseek-flash` 为主 | 月预算 ≤50 元绰绰有余 |
| 向量化（embedding） | 硅基流动 `BAAI/bge-m3`（免费，1024 维） | 退路：本地 CPU 推理或关键词检索 |
| 启动方式 | Windows `.bat` 一键脚本 | 不引入 Docker，无 Redis、无服务器 |

- **现查的版本依据（2026-10-16）**：
  - Spring Boot **3.5 的 OSS 支持已于 2026-06-30 结束**，4.0 将于 2026-12-31 结束；[start.spring.io](https://start.spring.io) 当前仅提供 4.0.8 与 **4.1.1（默认）**。因此选 4.1.1。
  - Spring Boot 4.1.1 最低要求 **Java 17**、Maven 3.6.3+（[官方系统要求](https://docs.spring.io/spring-boot/system-requirements.html)）——本机 JDK 17.0.20.1、Maven 3.9.16 均满足。
  - MyBatis-Plus 自 3.5.13 起提供 Spring Boot 4 专用 starter；Sa-Token 1.46.0 提供 `sa-token-spring-boot4-starter`。
  - [硅基流动](https://cloud.siliconflow.cn) `BAAI/bge-m3` 标价 ￥0/百万 tokens（接入前需到控制台实测，有反馈称账户余额为 0 时可能被拒）。

- **起决定作用的一条理由**：本项目的成功标准是「答辩讲得清 + Agent 部分能在面试里讲」，不是「组件最多」。方案 A 组件最少、可解释性最高、运维面最小；它唯一的代价是代码量更大 —— 而代码由 AI 编写，代价不落在用户身上。

- **已排除的方案**：
  - **方案 B 若依（RuoYi v3.9.2）脚手架改造**：① 雷同风险 —— 若依系在高校毕设中极为普遍，答辩极可能被追问「哪些是你自己做的」，而这恰是脚手架项目最难答的问题；② 其后端自带 Redis 依赖（登录态与缓存），与 D-P5「不引入 Redis」直接冲突。
  - **方案 C 企业级对齐栈**（Spring Security + Redis + TypeScript + Docker）：① 与 D-P5 直接冲突；② 组件越多，答辩被追问的面越大；③ 对「Agent 应用开发」岗位的求职帮助有限，堆 Java 组件堆不出该方向的竞争力。

- **关键组件选择理由**：
  - **Sa-Token 而非 Spring Security**：登录一行 `StpUtil.login()`、注解式鉴权，答辩可用一句话讲清权限实现；Spring Security 需讲过滤器链，超出用户知识准备范围。
  - **MyBatis-Plus 而非 Spring Data JPA**：贴近 SQL、单表 CRUD 免写 SQL、中文资料充足，便于用户理解「它在替我生成 SQL」。
  - **前端不上 TypeScript**：降低出错面与解释成本（用户不投前端岗）。
  - **不引入向量数据库**：规则库规模仅数百条，内存余弦相似度即可；少一个组件就少一层运维与解释成本。若语料显著增长，再换 Chroma/FAISS。
  - **Agent 服务无状态、不直连业务数据库**：规则库由 Java 侧管理并下发，稿件内容随调用传入 —— 边界清晰、可独立测试、可随时替换实现。

- **遗留风险与对策**：
  1. Sprint Boot 4.x 较新（Jackson 3 包名由 `com.fasterxml` 迁至 `tools.jackson` 等破坏性变更；市面教程与语料多为 3.x）→ **阶段 0 已实测：编译通过、启动成功、数据库联通正常，确认不退回 3.5.16**。实测中还修正了一处版本号问题：start.spring.io 生成的 `4.1.1.RELEASE` 在仓库中不存在，真实坐标是 **`4.1.1`**。
  2. 硅基流动免费额度可能受账户状态影响 → 阶段 5 接入前实测；退路为本地 CPU 推理 bge-m3 或降级为关键词检索。

- **阶段 0 实测确认的版本组合（2026-10-16）**：Spring Boot 4.1.1 + JDK 17.0.20.1 + Maven 3.9.16 + MyBatis-Plus 3.5.17（`mybatis-plus-spring-boot4-starter`）+ Sa-Token 1.46.0（`sa-token-spring-boot4-starter`）+ MySQL 8.0.46 + Vue 3.5.42 / Vite 8.2.2 / Pinia 4.0.3 / Vue Router 5.3.1 / Element Plus 2.14 + Node.js 24.21.0。**前后端与数据库的最小链路已跑通（见 `docs/开发笔记/阶段0-开发笔记.md`）。**
- **附带发现**：Spring 官方的 `mybatis-spring-boot-starter` 目前仅声明支持到 `4.1.0.M1`（不支持 4.1.x）；本项目使用 MyBatis-Plus 自带的 boot4 starter，因此不受影响。

- **日期**：2026-10-16
