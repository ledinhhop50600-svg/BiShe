"""与主系统之间的接口模型（对应 docs/Agent接口契约-v1.md）。

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

    # 仅供对比实验使用：开启「关键词定位」——先把长文聚焦到命中了规则示例词的段落，再送模型。
    # 一段都没命中时会自动回退全文（否则会退化成为关键词漏判）。
    localize: bool | None = None

    # 敏感词库（由主系统下发）。用途：作为规则检索与关键词定位的**词面来源**。
    # 规则里的示例词常是完整短语（"加我微信领资料"），正文往往写成"加我微信xxx领取"，
    # 而敏感词库里的短词（"加我微信"）能兜住这种情况。
    sensitiveWords: list[dict] | None = None


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
