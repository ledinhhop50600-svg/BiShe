# Agent 接口契约 v1

> **状态：已冻结（2026-10-16）**
> 主系统（SpringBoot）与智能体服务（Python/FastAPI）之间的 HTTP 契约。
> 冻结的含义：只要按本契约实现，主系统不需要再做任何改动。后续如需变更，必须升版本号（v2）。
>
> 为什么先定契约再写 Agent：主系统的内容流程（投稿、审核、适配）已经围绕这两个接口设计好了；
> 把契约固定下来，Agent 就能独立开发、独立测试、独立替换模型或框架，而不牵连主系统。

## 一、通用约定

| 项 | 约定 |
|---|---|
| 服务地址 | `http://localhost:8001`（见 `docs/decisions-stack.md`：8000 端口已被其他项目占用） |
| 协议 | HTTP/1.1，`Content-Type: application/json; charset=utf-8` |
| 认证 | 本地服务间调用，不计用户身份。可选增强：双方配置同一个共享口令，通过请求头 `X-Agent-Token` 校验（阶段 4 决定是否启用） |
| 超时 | 审核接口 30 秒；适配接口 60 秒 |
| 重试 | 网络错误或 5xx 时重试 1 次；仍失败则**降级**：主系统跳过智能体，直接进入人工审核，并在审计记录中标记 `agentFailed=true` |
| 字符编码 | 全程 UTF-8。中文不做转义 |
| 契约版本 | 响应体固定包含 `contractVersion: "1.0"` |
| 幂等与回放 | 请求携带 `requestId`（UUID）。智能体可据此实现「响应回放模式」：同一 requestId 返回缓存结果，用于重复评测与离线测试（不参与业务逻辑） |

### 为什么规则要"由主系统传过去"，而不是让 Agent 直连数据库

- 规则库、平台清单都在主系统里维护（管理界面在 Java 侧），**主系统是唯一数据源**；
- Agent 保持**无状态**：不连 MySQL、不持有业务数据，只做判断。这样它可以独立启动、独立测试、随时替换实现；
- 一次请求带齐所需上下文，避免 Agent 反向依赖主系统的内部接口。

## 二、接口一：审核 / 预检

`POST /api/agent/audit`

一次调用完成**分级判定**。三种触发场景共用此接口，用 `triggerType` 区分，便于后续按场景统计与评测。

### 请求体

```json
{
  "requestId": "8f3c2a1e-9b7d-4c55-a1f0-2d6e3f8a9b11",
  "articleId": 1024,
  "triggerType": "POST_AUDIT",
  "targetPlatformKey": "local",
  "title": "全网最低价的美肤面膜，三天见效不是梦",
  "content": "姐妹们这波真的可以冲……",
  "platform": {
    "platformKey": "local",
    "platformName": "本平台",
    "titleMaxLen": 60,
    "contentMaxLen": 5000,
    "tagRule": "可选，以 # 开头",
    "styleDesc": "长文，保留原始段落结构，语气平和"
  },
  "rules": [
    {
      "code": "AD-001",
      "name": "绝对化用语",
      "category": "广告法",
      "content": "内容中出现「国家级」「最高级」「最佳」「第一」「顶级」等绝对化表述……",
      "source": "《中华人民共和国广告法》第九条",
      "suggestedLevel": 2,
      "platformKey": null
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `requestId` | 是 | UUID，用于追踪与回放 |
| `articleId` | 是 | 稿件 id（仅用于日志与回放，Agent 不查库） |
| `triggerType` | 是 | `PRE_CHECK`（发布前预检，结论仅提示不阻断）<br>`POST_AUDIT`（提交发布申请后的正式审核）<br>`REPORT_REVIEW`（举报后的复审）<br>`ADAPT_CHECK`（适配后的平台合规检查） |
| `targetPlatformKey` | 否 | 为空或 `local` 表示按本平台的通用规则；其他值表示按目标平台规则检查 |
| `title` / `content` | 是 | 待判定内容 |
| `platform` | 否 | 目标平台的格式约束（来自 `audit_platform` 表），适配场景必填 |
| `rules` | 是 | **本次可用的规则全集**（主系统按 `platform_id` 过滤后下发：通用规则 + 该平台专属规则）。Agent 内部对这些规则做检索（RAG），不需要知道数据库结构。<br>**v1.1 新增**：每条规则可带 `platformKey`（为空表示通用规则）。适配接口一次请求多个平台时，Agent 靠它给每个平台挑出"通用规则 + 该平台专属规则"，避免拿小红书的规则检查微博。审核接口忽略该字段 |
| `ragProfile` | 否 | `legacy`（默认，原版检索）或 `compact`（C1 修复版）。仅用于对比实验 |
| `ragTopK` | 否 | 覆盖 top_k；C1 实验用 4 |
| `ragMinScore` | 否 | 向量相似度阈值；C1 实验用 0.55 |
| `compactRules` | 否 | 规则只以“编号/名称/类别/等级/短条件”进 prompt，不带法条依据 |
| `catalogRules` | 否 | E1 实验：规则只给编号/名称/类别/等级，供模型直接引用 |

> 引用校验：`hitRules` 只保留本次真正提供给模型的规则编号；模型编造的编号会被丢弃（E2 的归因在实验脚本侧完成）。
>
> 生产默认（2026-10-29 扩展集结论）：`useRag=false` + `catalogRules=true`（E1：只给规则目录，模型直接引用）。RAG 版本（C/C1）保留为实验与适配合规预检。

### 响应体（HTTP 200）

```json
{
  "contractVersion": "1.0",
  "requestId": "8f3c2a1e-9b7d-4c55-a1f0-2d6e3f8a9b11",
  "riskLevel": 2,
  "riskLevelText": "违规",
  "passed": false,
  "reason": "正文使用「全网最低价」作出无法核实的价格比较，并以「三天见效」承诺具体效果，同时含「国家级」绝对化表述，分别命中广告法与虚假宣传相关规则。",
  "hitRules": [
    { "code": "AD-001", "name": "绝对化用语", "category": "广告法", "source": "《中华人民共和国广告法》第九条" },
    { "code": "AD-002", "name": "无法核实的价格承诺", "category": "广告法", "source": "《中华人民共和国广告法》第八条" },
    { "code": "FB-001", "name": "功效承诺", "category": "虚假宣传", "source": "《中华人民共和国广告法》第二十八条" }
  ],
  "violations": [
    { "fragment": "全网最低价", "issue": "无法核实的价格比较", "suggestion": "改为「限时优惠」或删除价格比较表述" },
    { "fragment": "三天见效", "issue": "具体时限的效果承诺", "suggestion": "删除「三天见效」，如需说明效果应补充依据并注明因人而异" },
    { "fragment": "国家级", "issue": "绝对化用语", "suggestion": "删除「国家级」，或改为描述可核实的具体资质" }
  ],
  "suggestion": "建议驳回并要求修改：删除或替换 3 处违规表述后重新提交。",
  "confidence": 0.86,
  "model": "deepseek-flash",
  "usage": { "promptTokens": 1830, "completionTokens": 460 },
  "durationMs": 3260,
  "trace": [
    { "step": 1, "action": "retrieve_rules", "output": "召回 5 条规则：AD-001, AD-002, AD-003, FB-001, FB-002" },
    { "step": 2, "action": "llm_judge", "output": "riskLevel=2" },
    { "step": 3, "action": "locate_violations", "output": "定位 3 处违规片段" }
  ],
  "agentFailed": false
}
```

| 字段 | 说明 |
|---|---|
| `riskLevel` | **0 通过 / 1 疑似 / 2 违规 / 3 严重**（与主系统 `biz_article.risk_level`、`audit_record.risk_level` 完全一致） |
| `passed` | `riskLevel == 0` 的便捷布尔值 |
| `reason` | 判定理由。**要求：具体、可追溯，引用命中的规则编号**，不写"内容不合规"这类空话 |
| `hitRules` | 命中的规则（用于界面展示与论文的可解释性分析） |
| `violations` | **违规片段 + 问题 + 修改建议**，这是反馈给创作者的核心内容（D-A7 的要求） |
| `suggestion` | 总体处置建议（给审核员看的一句话） |
| `confidence` | 模型自评置信度，**仅供参考**（未校准，不作为自动处置依据） |
| `usage` / `durationMs` | 成本与耗时数据，直接写入 `audit_record`，作为论文对比实验的数据来源 |
| `trace` | Agent 主循环的步骤记录（工具调用、判定、定位），用于答辩演示与问题排查 |
| `agentFailed` | 恒为 `false`（失败时走 HTTP 错误，见下文） |

### 错误响应

| HTTP | 场景 | 响应体 |
|---|---|---|
| 400 | 请求参数不合法（如 `rules` 为空、`title`/`content` 都为空） | `{"error":"...","contractVersion":"1.0"}` |
| 422 | 模型返回的内容无法解析成约定结构（重试后仍失败） | `{"error":"model_output_invalid","detail":"..."}` |
| 503 | 模型服务不可用 / 鉴权失败 / 余额不足 | `{"error":"model_unavailable","detail":"..."}` |
| 500 | 其他内部错误 | `{"error":"internal_error","detail":"..."}` |

**主系统的降级策略**：任何非 200 都视为"智能体不可用" —— 不阻断业务流程，直接转人工审核，并记录一次失败的审核记录（`model_name` 标记为 `agent-failed`），便于事后统计可用率。

## 三、接口二：跨平台内容适配

`POST /api/agent/adapt`

一次请求可同时适配多个平台。每个平台独立生成一个版本，并各自做**格式自检**与**平台合规预检**。

### 请求体

```json
{
  "requestId": "c1a2b3d4-...",
  "articleId": 1030,
  "title": "家庭收纳的 5 个小技巧",
  "content": "很多人觉得家里地方小东西多……",
  "targetPlatformKeys": ["xiaohongshu", "weibo", "bilibili"],
  "platforms": [
    {
      "platformKey": "xiaohongshu",
      "platformName": "小红书",
      "titleMaxLen": 20,
      "contentMaxLen": 1000,
      "tagRule": "以 # 开头，建议 3-5 个",
      "styleDesc": "口语化、亲切，可适度使用 emoji，面向年轻读者"
    }
  ],
  "rules": [ "...同审核接口，用于适配后的平台合规预检..." ]
}
```

### 响应体（HTTP 200）

```json
{
  "contractVersion": "1.0",
  "requestId": "c1a2b3d4-...",
  "results": [
    {
      "platformKey": "xiaohongshu",
      "platformName": "小红书",
      "title": "收纳做对了，家里大一倍✨",
      "content": "姐妹们！我家 60 平也能装下所有东西🙌 …",
      "tags": ["#收纳", "#小户型", "#家居好物"],
      "formatCheck": {
        "passed": true,
        "titleLen": 18,
        "contentLen": 326,
        "issues": []
      },
      "compliance": {
        "riskLevel": 1,
        "riskLevelText": "疑似",
        "reason": "正文含「加我微信领清单」，命中该平台站外引流规则。",
        "violations": [
          { "fragment": "加我微信领清单", "issue": "站外引流", "suggestion": "删除该句，改为在平台内发布清单或引导关注账号" }
        ]
      }
    }
  ],
  "model": "deepseek-flash",
  "usage": { "promptTokens": 2600, "completionTokens": 1500 },
  "durationMs": 7800,
  "agentFailed": false
}
```

| 字段 | 说明 |
|---|---|
| `results[]` | 每个目标平台一个结果，顺序与请求的 `targetPlatformKeys` 一致 |
| `title` / `content` / `tags` | **适配产物本身**。`tags` 由 Agent 生成（须符合该平台的 `tagRule`） |
| `formatCheck` | 格式自检：字数是否超限、标签数量与格式是否符合规则。`passed=false` 时应带 `issues` 明细 |
| `compliance` | 适配后的平台合规预检结论（结构同审核接口的精简版）；`riskLevel=0` 表示无问题 |

> **格式自检的归属**：字数、标签数量这类**客观约束由程序校验**（不交给模型判断），
> 模型只负责创作内容。这样自检结果是确定性的，也是论文里"适配效果评估"的可量化指标之一。

## 四、主系统侧的数据落点

| 契约字段 | 落库位置 |
|---|---|
| `riskLevel` / `reason` / `hitRules` / `violations` / `suggestion` | `audit_record`（level / reason / hit_rule_codes / violation_fragments / suggestion） |
| `model` / `usage` / `durationMs` | `audit_record`（model_name / prompt_tokens / completion_tokens / duration_ms） |
| `triggerType` / `targetPlatformKey` | `audit_record`（trigger_type / platform_id） |
| `results[]` | `audit_adaptation`（每个平台一行） |
| 审核员的采纳/改判 | `audit_review`（阶段 7） |

## 五、尚未纳入 v1 的内容（明确留给后续版本）

| 内容 | 计划 |
|---|---|
| 多轮对话式审核（审核员追问"为什么判违规"） | 暂不实现；`reason` 与 `hitRules` 已足够解释 |
| 图片 / 视频审核 | 本期只做文本（见系统功能说明的边界说明） |
| 流式输出 | 不需要（单次判定，秒级返回） |
| Agent 侧直接执行处置（删稿、封号） | **永不由 Agent 执行**：处置一律经审核员（D-A7） |

## 六、版本变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-10-16 | 首次冻结：审核 / 预检接口、跨平台适配接口 |
| 1.1 | 2026-10-19 | 阶段 6 实现：规则增加可选 `platformKey`（用于多平台一次适配时按平台过滤）；明确格式自检由程序校验、适配后合规预检与正式审核共用同一套判定逻辑；适配结果按"稿件 + 平台"在 `audit_adaptation` 留版本 |
