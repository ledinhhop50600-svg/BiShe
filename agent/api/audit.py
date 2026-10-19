"""接口层：审核 / 预检（对应 docs/Agent接口契约-v1.md 的接口一）。"""

import json
import logging
import time

from fastapi import APIRouter, Header, HTTPException

from config import settings
from prompts import SYSTEM_PROMPT, build_user_prompt
from providers import get_provider
from providers.base import ProviderError
from rag import EmbeddingError, retrieve
from replay import load as replay_load
from replay import save as replay_save
from schemas import AuditRequest, AuditResponse, HitRule, TraceStep, Usage, Violation, risk_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _check_token(token: str) -> None:
    """可选的共享口令校验：配置了 AGENT_TOKEN 才校验。"""
    if settings.agent_token and token != settings.agent_token:
        raise HTTPException(status_code=401, detail="invalid agent token")


@router.post("/audit", response_model=AuditResponse)
def audit(req: AuditRequest, x_agent_token: str = Header(default="")) -> AuditResponse:
    _check_token(x_agent_token)

    # ---- 1) 回放：同一 requestId 直接命中缓存 ----
    cached = replay_load(req.requestId)
    if cached is not None:
        cached["replayed"] = True
        return AuditResponse(**cached)

    started = time.time()
    trace: list[TraceStep] = []

    # ---- 2) 规则检索（RAG）----
    rules = list(req.rules)
    retrieved = False
    rag_enabled = settings.rag_enabled if req.useRag is None else req.useRag
    if rag_enabled and len(rules) > settings.rag_top_k:
        try:
            rules, detail = retrieve(rules, f"{req.title}\n{req.content}"[:2000], settings.rag_top_k)
            retrieved = True
            trace.append(TraceStep(step=1, action="retrieve_rules", output=detail))
        except EmbeddingError as e:
            # 检索失败不能拖垮审核：降级为全量规则，并在 trace 里如实记录
            logger.warning("规则检索失败，已降级为全量规则：%s", e)
            trace.append(TraceStep(step=1, action="retrieve_rules_failed",
                                   output=f"{e}；已降级为全量规则"))
    else:
        trace.append(TraceStep(step=1, action="load_rules", output=f"本次可用规则 {len(rules)} 条"))

    # ---- 3) 调用模型 ----
    try:
        provider = get_provider(settings.provider)
        user_prompt = build_user_prompt(req, rules, retrieved)
        result = provider.judge(SYSTEM_PROMPT, user_prompt)
    except ProviderError as e:
        # 契约约定：模型不可用返回 503，由主系统降级到人工审核
        raise HTTPException(status_code=503, detail=f"model_unavailable: {e}") from e

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

    hit_rules = [
        HitRule(
            code=str(r.get("code", "")),
            name=str(r.get("name", "")),
            category=str(r.get("category", "")),
            source=r.get("source"),
        )
        for r in (data.get("hitRules") or [])
    ]
    violations = [
        Violation(
            fragment=str(v.get("fragment", "")),
            issue=str(v.get("issue", "")),
            suggestion=str(v.get("suggestion", "")),
        )
        for v in (data.get("violations") or [])
    ]

    trace.append(TraceStep(step=2, action="llm_judge", output=f"riskLevel={level}（{risk_text(level)}）"))
    if violations:
        trace.append(TraceStep(step=3, action="locate_violations", output=f"定位到 {len(violations)} 处违规片段"))

    response = AuditResponse(
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

    # ---- 5) 写入回放缓存（之后再调同一 requestId 会直接命中）----
    replay_save(req.requestId, response.model_dump())

    return response
