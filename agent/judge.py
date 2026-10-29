"""审核判定的核心流程：检索 → 定位 → 调用模型 → 解析 → 组装结论。

抽出来的原因：阶段 6 的"适配后合规预检"必须和正式审核走**同一套判定逻辑**。
如果两个接口各写一份，迟早会出现"同一段文字，预检说通过、正式审核说违规"的矛盾，
而人机协同最忌讳的就是系统自相矛盾。
"""

import json
import logging
import time

from fastapi import HTTPException

from config import settings
from prompts import SYSTEM_PROMPT, build_user_prompt
from providers import get_provider
from providers.base import ProviderError
from rag import EmbeddingError, localize, retrieve
from schemas import AuditRequest, AuditResponse, HitRule, TraceStep, Usage, Violation, risk_text

logger = logging.getLogger(__name__)


def judge(req: AuditRequest, *, extra_terms: list[str] | None = None,
          use_rag: bool | None = None, localize_flag: bool = False) -> AuditResponse:
    """对一条内容做一次完整判定。

    @param extra_terms   词面关键词来源（敏感词库）
    @param use_rag       是否启用规则检索；None 时按服务端配置
    @param localize_flag 是否启用关键词定位（长文降本模式）
    """
    started = time.time()
    trace: list[TraceStep] = []

    # ---- 1) 规则检索（RAG）----
    rules = list(req.rules)
    retrieved = False
    rag_enabled = settings.rag_enabled if use_rag is None else use_rag
    top_k = req.ragTopK or settings.rag_top_k
    min_score = req.ragMinScore if req.ragMinScore is not None else 0.0
    if rag_enabled and len(rules) > top_k:
        started_retrieve = time.time()
        try:
            # C1 修复点：不再截到 2000 字，长文后半段也参与规则召回（内部按 300 字切块）。
            rules, detail = retrieve(rules, f"{req.title}\n{req.content}"[:6000], top_k,
                                     extra_terms=extra_terms, profile=req.ragProfile,
                                     min_score=min_score)
            retrieved = True
            trace.append(TraceStep(step=1, action="retrieve_rules", output=detail,
                                   durationMs=int((time.time() - started_retrieve) * 1000)))
        except EmbeddingError as e:
            # 检索失败不能拖垮审核：降级为全量规则，并在 trace 里如实记录
            logger.warning("规则检索失败，已降级为全量规则：%s", e)
            trace.append(TraceStep(step=1, action="retrieve_rules_failed",
                                   output=f"{e}；已降级为全量规则",
                                   durationMs=int((time.time() - started_retrieve) * 1000)))
    else:
        trace.append(TraceStep(step=1, action="load_rules", output=f"本次可用规则 {len(rules)} 条"))

    # ---- 2) 关键词定位（可选模式，用于长文降本；未命中则回退全文）----
    content_text = req.content
    if localize_flag:
        started_localize = time.time()
        content_text, loc_info = localize(req.content, rules, extra_terms=extra_terms)
        trace.append(TraceStep(step=len(trace) + 1, action="localize", output=loc_info,
                               durationMs=int((time.time() - started_localize) * 1000)))

    # ---- 3) 调用模型 ----
    started_llm = time.time()
    try:
        provider = get_provider(settings.provider)
        user_prompt = build_user_prompt(req, rules, retrieved,
                                        content_override=content_text if localize_flag else None,
                                        compact_rules=req.compactRules)
        result = provider.judge(SYSTEM_PROMPT, user_prompt,
                                reasoning_effort=req.reasoningEffort)
    except ProviderError as e:
        # 契约约定：模型不可用返回 503，由主系统降级到人工审核
        raise HTTPException(status_code=503, detail=f"model_unavailable: {e}") from e
    llm_ms = int((time.time() - started_llm) * 1000)

    # ---- 4) 解析并校验模型输出 ----
    try:
        data = json.loads(result.text)
    except json.JSONDecodeError as e:
        # 解析失败时必须留下原始输出：否则线上只能看到"422"，无从排错。
        # 常见原因：输出被 max_tokens 截断（长文+多违规）、JSON 里有未转义的引号。
        logger.error("模型输出无法解析：%s | 原始输出（前 600 字）：%s", e, result.text[:600])
        raise HTTPException(status_code=422, detail="model_output_invalid: 模型未返回合法 JSON") from e

    level = int(data.get("riskLevel", 0))
    if level not in (0, 1, 2, 3):
        raise HTTPException(status_code=422, detail=f"model_output_invalid: riskLevel 越界（{level}）")

    # 引用校验：只接受本次真正提供给模型的规则编号。
    # 模型可能编造 AD-ABSOLUTE 这类库里不存在的代码；宁可丢弃，也不要把幻觉写进审核记录。
    allowed_codes = {r.code for r in rules}
    hit_rules = [
        HitRule(
            code=str(r.get("code", "")),
            name=str(r.get("name", "")),
            category=str(r.get("category", "")),
            source=r.get("source"),
        )
        for r in (data.get("hitRules") or [])
        if str(r.get("code", "")) in allowed_codes
    ]
    violations = [
        Violation(
            fragment=str(v.get("fragment", "")),
            issue=str(v.get("issue", "")),
            suggestion=str(v.get("suggestion", "")),
        )
        for v in (data.get("violations") or [])
    ]

    trace.append(TraceStep(step=2, action="llm_judge", output=f"riskLevel={level}（{risk_text(level)}）",
                           durationMs=llm_ms))
    if violations:
        trace.append(TraceStep(step=3, action="locate_violations",
                               output=f"定位到 {len(violations)} 处违规片段"))

    return AuditResponse(
        requestId=req.requestId,
        riskLevel=level,
        riskLevelText=risk_text(level),
        passed=(level == 0),
        reason=str(data.get("reason", "")),
        hitRules=hit_rules,
        violations=violations,
        suggestion=str(data.get("suggestion", "")),
        confidence=float(data["confidence"]) if data.get("confidence") is not None else None,
        model=result.model,
        usage=Usage(promptTokens=result.prompt_tokens, completionTokens=result.completion_tokens),
        durationMs=int((time.time() - started) * 1000),
        trace=trace,
        agentFailed=False,
    )
