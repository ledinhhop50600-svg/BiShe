"""接口二：跨平台内容适配（对应契约的 /api/agent/adapt）。

默认生产策略：逐平台、并行改写（每个平台一次改写 + 一次合规预检）。
实验开关（请求里可选，主系统不传）：
  - strategy=per_platform / unified / generic
  - parallel=true/false
  - reasoningEffort=none/low/high
用于对比"分平台提示词 vs 合并一次调用""串行 vs 并行""关思考 vs 开思考"的速度与质量。
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Header, HTTPException

from api.common import check_token
from config import settings
from format_check import check_format
from judge import judge
from prompts import (ADAPT_SYSTEM_PROMPT, ADAPT_UNIFIED_SYSTEM_PROMPT,
                     build_adapt_prompt, build_unified_adapt_prompt)
from providers import get_provider
from providers.base import ProviderError
from replay import load as replay_load
from replay import save as replay_save
from schemas import (AdaptRequest, AdaptResponse, AdaptResult, AuditRequest,
                     Compliance, Usage)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

ADAPT_CONTENT_SOFT_CAP = 3000


@router.post("/adapt", response_model=AdaptResponse)
def adapt(req: AdaptRequest, x_agent_token: str = Header(default="")) -> AdaptResponse:
    check_token(x_agent_token)

    # 去重但保留请求顺序（结果顺序必须与 targetPlatformKeys 一致）
    keys = list(dict.fromkeys(req.targetPlatformKeys))
    platform_map = {p.platformKey: p for p in req.platforms}
    missing = [k for k in keys if k not in platform_map]
    if missing:
        raise HTTPException(status_code=400, detail=f"invalid_request: 缺少平台信息 {missing}")
    if not req.title.strip() and not req.content.strip():
        raise HTTPException(status_code=400, detail="invalid_request: title 与 content 不能都为空")

    # 缓存键要把实验开关也算进去，否则实验会命中生产缓存
    cache_key = (f"{req.requestId}:adapt:{req.strategy}:{int(req.parallel)}:"
                 f"{req.reasoningEffort or 'default'}:{','.join(keys)}")
    cached = replay_load(cache_key)
    if cached is not None:
        cached["replayed"] = True
        return AdaptResponse(**cached)

    started = time.time()
    provider = get_provider(settings.provider)

    if req.strategy == "unified":
        results, prompt_tokens, completion_tokens, model = _run_unified(
            provider, req, keys, platform_map)
    else:
        def task(key):
            return _run_platform(provider, req, key, platform_map[key], req.strategy)

        if req.parallel and len(keys) > 1:
            with ThreadPoolExecutor(max_workers=min(4, len(keys))) as ex:
                outputs = list(ex.map(task, keys))
        else:
            outputs = [task(k) for k in keys]

        results = [o[0] for o in outputs]
        prompt_tokens = sum(o[1] for o in outputs)
        completion_tokens = sum(o[2] for o in outputs)
        model = next((o[3] for o in outputs if o[3]), "")

    response = AdaptResponse(
        requestId=req.requestId,
        results=results,
        model=model,
        usage=Usage(promptTokens=prompt_tokens, completionTokens=completion_tokens),
        durationMs=int((time.time() - started) * 1000),
        agentFailed=False,
        strategy=req.strategy,
        parallel=req.parallel,
    )
    replay_save(cache_key, response.model_dump())
    return response


# ----------------------------------------------------------------------
# 单平台：改写 → 清理 → 格式自检 → 合规预检
# ----------------------------------------------------------------------

def _run_platform(provider, req: AdaptRequest, key: str, platform,
                  strategy: str) -> tuple[AdaptResult, int, int, str]:
    started_platform = time.time()
    applicable = _rules_for_platform(req, key)

    started_adapt = time.time()
    try:
        adapted = provider.adapt(
            ADAPT_SYSTEM_PROMPT,
            build_adapt_prompt(req, platform, include_hint=(strategy != "generic")),
            reasoning_effort=req.reasoningEffort,
        )
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=f"model_unavailable: [{key}] {e}") from e
    adapt_ms = int((time.time() - started_adapt) * 1000)

    title, content, tags = _parse_single(adapted.text, key)
    content = _strip_duplicate_tags(content, tags)
    truncated_from = len(content) if len(content) > ADAPT_CONTENT_SOFT_CAP else 0
    if truncated_from:
        content = _truncate(content, ADAPT_CONTENT_SOFT_CAP)

    fmt = check_format(platform, title, content, tags)
    if truncated_from:
        fmt.issues.append(
            f"正文 {truncated_from} 字，超过适配建议上限 {ADAPT_CONTENT_SOFT_CAP} 字，已按句截断")
        fmt.passed = False

    compliance, c_prompt, c_completion, compliance_ms = _compliance(
        req, key, platform, applicable, title, content, tags)

    result = AdaptResult(
        platformKey=key,
        platformName=platform.platformName,
        title=title,
        content=content,
        tags=tags,
        durationMs=int((time.time() - started_platform) * 1000),
        adaptMs=adapt_ms,
        complianceMs=compliance_ms,
        formatCheck=fmt,
        compliance=compliance,
    )
    return (result, adapted.prompt_tokens + c_prompt,
            adapted.completion_tokens + c_completion, adapted.model)


# ----------------------------------------------------------------------
# 合并一次调用（实验用）：一次改写所有平台，再逐平台做格式/合规
# ----------------------------------------------------------------------

def _run_unified(provider, req: AdaptRequest, keys: list[str], platform_map
                 ) -> tuple[list[AdaptResult], int, int, str]:
    platforms = [platform_map[k] for k in keys]
    started = time.time()
    try:
        adapted = provider.adapt(
            ADAPT_UNIFIED_SYSTEM_PROMPT,
            build_unified_adapt_prompt(req, platforms),
            reasoning_effort=req.reasoningEffort,
        )
    except ProviderError as e:
        raise HTTPException(status_code=503, detail=f"model_unavailable: [unified] {e}") from e
    adapt_ms = int((time.time() - started) * 1000)

    data = _load_json(adapted.text)
    items = data.get("results") if isinstance(data, dict) else None
    if not isinstance(items, list):
        logger.error("统一适配输出缺少 results：%s", adapted.text[:400])
        raise HTTPException(status_code=422,
                            detail="model_output_invalid: 统一适配结果缺少 results 数组")
    by_key = {}
    for item in items:
        if isinstance(item, dict):
            by_key[str(item.get("platformKey", ""))] = item
    missing = [k for k in keys if k not in by_key]
    if missing:
        raise HTTPException(status_code=422,
                            detail=f"model_output_invalid: 统一适配缺少平台 {missing}")

    prepared = []
    for key in keys:
        platform = platform_map[key]
        title, content, tags = _parse_single(json.dumps(by_key[key], ensure_ascii=False), key)
        content = _strip_duplicate_tags(content, tags)
        truncated_from = len(content) if len(content) > ADAPT_CONTENT_SOFT_CAP else 0
        if truncated_from:
            content = _truncate(content, ADAPT_CONTENT_SOFT_CAP)
        fmt = check_format(platform, title, content, tags)
        if truncated_from:
            fmt.issues.append(
                f"正文 {truncated_from} 字，超过适配建议上限 {ADAPT_CONTENT_SOFT_CAP} 字，已按句截断")
            fmt.passed = False
        prepared.append({
            "key": key, "platform": platform, "applicable": _rules_for_platform(req, key),
            "title": title, "content": content, "tags": tags, "fmt": fmt,
        })

    def comp_task(p):
        return _compliance(req, p["key"], p["platform"], p["applicable"],
                           p["title"], p["content"], p["tags"])

    if req.parallel and len(prepared) > 1:
        with ThreadPoolExecutor(max_workers=min(4, len(prepared))) as ex:
            comps = list(ex.map(comp_task, prepared))
    else:
        comps = [comp_task(p) for p in prepared]

    results = []
    c_prompt = c_completion = 0
    for p, (compliance, cp, cc, c_ms) in zip(prepared, comps):
        c_prompt += cp
        c_completion += cc
        results.append(AdaptResult(
            platformKey=p["key"],
            platformName=p["platform"].platformName,
            title=p["title"],
            content=p["content"],
            tags=p["tags"],
            # 改写是共享的一次调用；这里只记该平台的合规耗时，总耗时看响应
            durationMs=c_ms,
            adaptMs=0,
            complianceMs=c_ms,
            formatCheck=p["fmt"],
            compliance=compliance,
        ))
    logger.info("统一适配：改写 %dms，共享一次调用", adapt_ms)
    return (results, adapted.prompt_tokens + c_prompt,
            adapted.completion_tokens + c_completion, adapted.model)


# ----------------------------------------------------------------------
# 公共：合规预检、解析、清理
# ----------------------------------------------------------------------

def _compliance(req: AdaptRequest, key: str, platform, applicable,
                title: str, content: str, tags: list[str]):
    # 话题标签也是发布内容的一部分，可能夹带引流词（如 #加微信），必须一起送检。
    check_content = content + (f"\n\n【话题标签】{' '.join(tags)}" if tags else "")
    audit_req = AuditRequest(
        requestId=f"{req.requestId}:chk:{key}",
        articleId=req.articleId,
        triggerType="ADAPT_CHECK",
        targetPlatformKey=key,
        title=title,
        content=check_content,
        platform=platform,
        rules=applicable,
        reasoningEffort=req.reasoningEffort,
    )
    started = time.time()
    try:
        verdict = judge(audit_req, use_rag=True)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=f"[{key}] {e.detail}") from e
    compliance = Compliance(
        riskLevel=verdict.riskLevel,
        riskLevelText=verdict.riskLevelText,
        reason=verdict.reason,
        hitRules=verdict.hitRules,
        violations=verdict.violations,
        suggestion=verdict.suggestion,
    )
    return (compliance, verdict.usage.promptTokens, verdict.usage.completionTokens,
            int((time.time() - started) * 1000))


def _rules_for_platform(req: AdaptRequest, platform_key: str) -> list:
    """通用规则 + 该平台专属规则；没有时按"平台 → 通用 → 全部"逐级回退。

    绝不能出现"没有规则 → 直接通过"，那比报错更危险。
    """
    applicable = [r for r in req.rules if not r.platformKey or r.platformKey == platform_key]
    if applicable:
        return applicable
    general = [r for r in req.rules if not r.platformKey]
    return general or list(req.rules)


def _load_json(text: str):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("适配输出无法解析：%s | 原始输出（前 600 字）：%s", e, text[:600])
        raise HTTPException(status_code=422, detail="model_output_invalid: 适配结果不是合法 JSON") from e


def _parse_single(text: str, platform_key: str) -> tuple[str, str, list[str]]:
    data = _load_json(text)
    if not isinstance(data, dict):
        raise HTTPException(status_code=422,
                            detail=f"model_output_invalid: [{platform_key}] 适配结果不是对象")
    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or "").strip()
    tags = _normalize_tags(data.get("tags"))
    if not content:
        logger.error("适配输出正文为空（%s）：%s", platform_key, text[:300])
        raise HTTPException(status_code=422,
                            detail=f"model_output_invalid: [{platform_key}] 适配结果正文为空")
    return title, content, tags


def _normalize_tags(raw) -> list[str]:
    """标签统一成字符串列表：兼容模型返回数组、字符串或用逗号/空格分隔的字符串。"""
    if raw is None:
        return []
    if isinstance(raw, str):
        items = re.split(r"[,，\s]+", raw)
    elif isinstance(raw, list):
        items = [str(x) for x in raw]
    else:
        items = [str(raw)]
    tags = []
    for t in items:
        t = t.strip()
        if t:
            tags.append(t)
    return tags


def _truncate(text: str, limit: int) -> str:
    """按句号/换行截断，尽量不把一句话砍半。"""
    head = text[:limit]
    for mark in ("。", "！", "？", "\n"):
        idx = head.rfind(mark)
        if idx >= limit * 0.7:
            return head[:idx + 1]
    return head


def _strip_duplicate_tags(content: str, tags: list[str]) -> str:
    """删掉正文末尾"整行都是标签"的重复行。

    只在这一行的每个词都是 tags 里已有的标签时才删；只要有一个陌生标签就保留，
    避免把模型真正写在正文里的内容误删。
    """
    if not tags:
        return content
    lines = content.rstrip().split("\n")
    if len(lines) < 2:
        return content
    last = lines[-1].strip()
    tokens = re.split(r"[\s,，]+", last)
    if not tokens or not all(t.startswith("#") for t in tokens):
        return content
    known = {t.strip("#") for t in tags}
    if {t.strip("#") for t in tokens} <= known:
        return "\n".join(lines[:-1]).rstrip()
    return content
