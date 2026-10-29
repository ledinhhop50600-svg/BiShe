"""接口二：跨平台内容适配（对应契约的 /api/agent/adapt）。

一次请求适配多个平台，每个平台做三件事：
  1. 按平台形态改写（模型）；
  2. 格式自检（程序算字数 / 标签，确定性）；
  3. 用目标平台的规则做一次合规预检（复用 judge 的同一套判定逻辑）。

为什么每个平台单独调用模型，而不是让模型一次输出所有平台：
  - 单个平台的输出更短，不容易被 max_tokens 截断（多平台合并输出曾导致 JSON 不完整）；
  - 一个平台失败不会污染其他平台的结果，提示词也能写得更具体。
代价是耗时随平台数线性增长，所以主系统把目标平台限制在 5 个以内。
"""

import json
import logging
import re
import time

from fastapi import APIRouter, Header, HTTPException

from api.common import check_token
from config import settings
from format_check import check_format
from judge import judge
from prompts import ADAPT_SYSTEM_PROMPT, build_adapt_prompt
from providers import get_provider
from providers.base import ProviderError
from replay import load as replay_load
from replay import save as replay_save
from schemas import (AdaptRequest, AdaptResponse, AdaptResult, AuditRequest,
                     Compliance, Usage)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# 适配接口的正文建议上限。即使目标平台允许更长（如公众号 2 万字），
# 适配产物也只需要保留核心信息 —— 这样既控制输出 token，避免 JSON 被截断，
# 也符合"跨平台改写"的定位（不是把原文原样搬过去）。
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

    cache_key = f"{req.requestId}:adapt:{','.join(keys)}"
    cached = replay_load(cache_key)
    if cached is not None:
        cached["replayed"] = True
        return AdaptResponse(**cached)

    started = time.time()
    provider = get_provider(settings.provider)
    results: list[AdaptResult] = []
    prompt_tokens = completion_tokens = 0
    model = ""

    for key in keys:
        platform = platform_map[key]
        applicable = _rules_for_platform(req, key)
        started_platform = time.time()

        # ---- 1) 改写 ----
        started_adapt = time.time()
        try:
            adapted = provider.adapt(ADAPT_SYSTEM_PROMPT, build_adapt_prompt(req, platform))
        except ProviderError as e:
            raise HTTPException(status_code=503, detail=f"model_unavailable: [{key}] {e}") from e
        adapt_ms = int((time.time() - started_adapt) * 1000)
        prompt_tokens += adapted.prompt_tokens
        completion_tokens += adapted.completion_tokens
        model = adapted.model or model

        title, content, tags = _parse_adapt_output(adapted.text, key)
        # 模型有时仍会把标签重复写在正文末尾（平台习惯很强）。只要末尾那行全是
        # 已出现在 tags 字段里的标签，就删掉这一行 —— 否则界面上会显示两遍，
        # 复制全文时也会重复。只删"完全是标签"的行，不碰正文内容。
        content = _strip_duplicate_tags(content, tags)
        # 超过建议上限时按句截断，但**必须如实记入 issues** —— 静默吞掉内容比截断更糟
        truncated_from = len(content) if len(content) > ADAPT_CONTENT_SOFT_CAP else 0
        if truncated_from:
            content = _truncate(content, ADAPT_CONTENT_SOFT_CAP)

        # ---- 2) 格式自检（程序算，结果确定）----
        fmt = check_format(platform, title, content, tags)
        if truncated_from:
            fmt.issues.append(
                f"正文 {truncated_from} 字，超过适配建议上限 {ADAPT_CONTENT_SOFT_CAP} 字，已按句截断")
            fmt.passed = False

        # ---- 3) 适配后合规预检（与正式审核同一套逻辑）----
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
        )
        try:
            started_compliance = time.time()
            verdict = judge(audit_req, use_rag=True)
            compliance_ms = int((time.time() - started_compliance) * 1000)
        except HTTPException as e:
            # 把平台带进错误信息，否则多平台请求失败时不知道是哪个平台
            raise HTTPException(status_code=e.status_code, detail=f"[{key}] {e.detail}") from e
        prompt_tokens += verdict.usage.promptTokens
        completion_tokens += verdict.usage.completionTokens

        results.append(AdaptResult(
            platformKey=key,
            platformName=platform.platformName,
            title=title,
            content=content,
            tags=tags,
            durationMs=int((time.time() - started_platform) * 1000),
            adaptMs=adapt_ms,
            complianceMs=compliance_ms,
            formatCheck=fmt,
            compliance=Compliance(
                riskLevel=verdict.riskLevel,
                riskLevelText=verdict.riskLevelText,
                reason=verdict.reason,
                hitRules=verdict.hitRules,
                violations=verdict.violations,
                suggestion=verdict.suggestion,
            ),
        ))

    response = AdaptResponse(
        requestId=req.requestId,
        results=results,
        model=model,
        usage=Usage(promptTokens=prompt_tokens, completionTokens=completion_tokens),
        durationMs=int((time.time() - started) * 1000),
        agentFailed=False,
    )
    replay_save(cache_key, response.model_dump())
    return response


def _rules_for_platform(req: AdaptRequest, platform_key: str) -> list:
    """取出适用于某个平台的规则：通用规则 + 该平台专属规则。

    这里**必须有兜底**：如果规则全被过滤掉，模型会在没有任何依据的情况下给出"通过"，
    这比报错更危险。所以按"平台规则 → 通用规则 → 全部规则"逐级回退。
    """
    applicable = [r for r in req.rules if not r.platformKey or r.platformKey == platform_key]
    if applicable:
        return applicable
    general = [r for r in req.rules if not r.platformKey]
    return general or list(req.rules)


def _parse_adapt_output(text: str, platform_key: str) -> tuple[str, str, list[str]]:
    """解析模型输出。格式错误返回 422，并保留原始输出便于排查。"""
    raw = text.strip()
    # 容忍部分供应商在 JSON 外包 ```json 代码块（DeepSeek 的 json_object 模式不会加，
    # 但切换到其他兼容供应商时可能会）
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("适配输出无法解析（%s）：%s | 原始输出（前 600 字）：%s",
                     platform_key, e, text[:600])
        raise HTTPException(status_code=422,
                            detail=f"model_output_invalid: [{platform_key}] 适配结果不是合法 JSON") from e

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
