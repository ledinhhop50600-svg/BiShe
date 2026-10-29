"""与主系统之间的接口模型（对应 docs/设计文档/Agent接口契约-v1.md）。

字段名使用 camelCase，与契约和 Java 侧的 JSON 完全一致 ——
虽然这不是 Python 的命名习惯，但可以省掉一整层字段映射，也避免映射写错。
"""

from typing import Literal

from pydantic import BaseModel, Field


# ======================================================================
# 请求
# ======================================================================

class RuleItem(BaseModel):
    """主系统下发的单条审核规则。"""

    code: str
    name: str
    category: str
    content: str
    source: str | None = None
    suggestedLevel: int | None = None
    # 规则适用平台标识：为空表示通用规则（适用于所有平台）。
    # 阶段 6 的适配接口一次可适配多个平台，智能体靠这个字段给每个平台挑出
    # "通用规则 + 该平台专属规则"，不会把小红的规则拿去检查微博。
    platformKey: str | None = None


class PlatformInfo(BaseModel):
    """目标平台的格式约束（阶段 5/6 使用）。"""

    platformKey: str
    platformName: str
    titleMaxLen: int | None = None
    contentMaxLen: int | None = None
    tagRule: str | None = None
    styleDesc: str | None = None


TriggerType = Literal["PRE_CHECK", "POST_AUDIT", "REPORT_REVIEW", "ADAPT_CHECK"]


class AuditRequest(BaseModel):
    requestId: str = Field(min_length=1)
    articleId: int
    triggerType: TriggerType
    targetPlatformKey: str | None = None
    title: str = ""
    content: str = ""
    platform: PlatformInfo | None = None
    rules: list[RuleItem] = Field(default_factory=list)

    # 仅供对比实验使用：强制开启/关闭规则检索。
    # 为空时按服务端配置（.env 的 RAG_ENABLED）；实验脚本用它把同一批样本跑成
    # 「RAG」与「全量规则」两组，而不必反复改配置重启服务。
    useRag: bool | None = None

    # 仅供对比实验使用：规则检索策略。
    # legacy = 原行为（关键词命中全部优先，top_k 直接截断）；compact = C1（关键词限流+阈值+去重+紧凑规则卡片）。
    ragProfile: Literal["legacy", "compact"] = "legacy"
    ragTopK: int | None = None
    ragMinScore: float | None = None
    compactRules: bool = False
    catalogRules: bool = False

    # 仅供对比实验使用：开启「关键词定位」——先把长文聚焦到命中了规则示例词的段落，再送模型。
    # 一段都没命中时会自动回退全文（否则会退化成为关键词漏判）。
    localize: bool | None = None

    # 敏感词库（由主系统下发）。用途：作为规则检索与关键词定位的**词面来源**。
    # 规则里的示例词常是完整短语（"加我微信领资料"），正文往往写成"加我微信xxx领取"，
    # 而敏感词库里的短词（"加我微信"）能兜住这种情况。
    sensitiveWords: list[dict] | None = None

    # 仅供速度实验使用：覆盖 .env 的 REASONING_EFFORT（none/low/high），对比思考模式的代价。
    reasoningEffort: str | None = None


# ======================================================================
# 响应
# ======================================================================

class HitRule(BaseModel):
    code: str
    name: str
    category: str
    source: str | None = None


class Violation(BaseModel):
    """违规片段 + 问题 + 修改建议（反馈给创作者的核心内容）。"""

    fragment: str
    issue: str
    suggestion: str


class Usage(BaseModel):
    promptTokens: int = 0
    completionTokens: int = 0


class TraceStep(BaseModel):
    step: int
    action: str
    output: str = ""
    # 该步骤耗时（毫秒）。审核链路用它做性能拆解：检索 / 定位 / 模型各占多少。
    durationMs: int = 0


class AuditResponse(BaseModel):
    contractVersion: str = "1.0"
    requestId: str
    riskLevel: int
    riskLevelText: str
    passed: bool
    reason: str
    hitRules: list[HitRule] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    suggestion: str = ""
    confidence: float | None = None
    model: str = ""
    usage: Usage = Field(default_factory=Usage)
    durationMs: int = 0
    trace: list[TraceStep] = Field(default_factory=list)
    agentFailed: bool = False
    # 是否来自回放缓存（契约之外的附加字段，便于测试时辨别；Java 侧忽略未知字段）
    replayed: bool = False


# ======================================================================
# 接口二：跨平台适配（阶段 6）
# ======================================================================

class AdaptRequest(BaseModel):
    requestId: str = Field(min_length=1)
    articleId: int
    title: str = ""
    content: str = ""
    # 目标平台顺序即返回结果的顺序（契约要求）
    targetPlatformKeys: list[str] = Field(min_length=1, max_length=5)
    platforms: list[PlatformInfo] = Field(default_factory=list)
    rules: list[RuleItem] = Field(default_factory=list)

    # 以下三个字段仅供速度实验：不影响主系统调用（不传就是生产默认值）
    # per_platform：每个平台单独一次改写（当前生产方案）
    # unified：所有平台合并成一次改写（输出更长，可能更快也可能更慢）
    # generic：每个平台单独改写，但不给平台形态提示（用于对比“分平台提示词”的价值）
    strategy: Literal["per_platform", "unified", "generic"] = "per_platform"
    parallel: bool = True
    reasoningEffort: str | None = None


class FormatCheck(BaseModel):
    """格式自检结果 —— 由程序校验，不交给模型判断（结果必须是确定性的）。"""

    passed: bool
    titleLen: int
    contentLen: int
    tagCount: int
    issues: list[str] = Field(default_factory=list)


class Compliance(BaseModel):
    """适配后按目标平台规则做的合规预检（审核结论的精简版）。"""

    riskLevel: int
    riskLevelText: str
    reason: str = ""
    hitRules: list[HitRule] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    suggestion: str = ""


class AdaptResult(BaseModel):
    platformKey: str
    platformName: str
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    # 该平台从改写、格式自检到合规预检的耗时（毫秒）
    durationMs: int = 0
    # 拆开看：改写（模型）与合规预检（模型）各花了多久
    adaptMs: int = 0
    complianceMs: int = 0
    formatCheck: FormatCheck
    compliance: Compliance


class AdaptResponse(BaseModel):
    contractVersion: str = "1.0"
    requestId: str
    results: list[AdaptResult]
    model: str = ""
    usage: Usage = Field(default_factory=Usage)
    durationMs: int = 0
    agentFailed: bool = False
    # 本次使用的策略（实验/排查用；生产默认 per_platform）
    strategy: str = "per_platform"
    parallel: bool = True
    # 契约之外的附加字段，便于测试时辨别回放；Java 侧忽略未知字段
    replayed: bool = False


# ======================================================================
# 辅助
# ======================================================================

RISK_TEXT = {
    0: "通过",
    1: "疑似",
    2: "违规",
    3: "严重",
}


def risk_text(level: int) -> str:
    return RISK_TEXT.get(level, "未知")
