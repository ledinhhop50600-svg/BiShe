"""本地调试控制台：把一次审核的检索、提示词、模型流式输出和解析过程实时展示出来。

只允许本机访问；它不是业务接口，不参与正式审核，也不替代 Java 侧的 audit_record。
打开方式：Agent 启动后访问 http://localhost:8001/debug
"""

import json
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config import settings
from prompts import SYSTEM_PROMPT, build_user_prompt
from rag import EmbeddingError, retrieve
from schemas import AuditRequest, RuleItem
from providers import get_provider
from providers.base import ProviderError

router = APIRouter(tags=["debug"])

_HERE = Path(__file__).resolve().parent.parent
_RULES_PATH = _HERE / "debug_rules.json"
_HTML_PATH = _HERE / "debug_console.html"


class DebugRequest(BaseModel):
    title: str = ""
    content: str = ""
    mode: Literal["e1", "rag", "b"] = "e1"
    reasoningEffort: str | None = None


def _local_only(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="debug console is local-only")


def _rules() -> list[RuleItem]:
    if not _RULES_PATH.exists():
        return []
    data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return [RuleItem(**item) for item in data]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/debug", include_in_schema=False)
def debug_page(request: Request):
    _local_only(request)
    if not _HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="debug console not found")
    return FileResponse(_HTML_PATH, media_type="text/html")


@router.post("/api/agent/debug/stream", include_in_schema=False)
def debug_stream(req: DebugRequest, request: Request):
    _local_only(request)

    def stream():
        started = time.time()
        yield _sse("stage", {"stage": "request", "message": "收到调试请求",
                             "title": req.title, "contentLen": len(req.content)})

        all_rules = _rules()
        selected = list(all_rules)
        retrieved = False
        detail = "E1 · 使用全量最小规则目录"
        if req.mode == "b":
            selected = []
            detail = "B · 纯大模型，不提供规则"
        elif req.mode == "rag":
            try:
                selected, detail = retrieve(
                    all_rules, f"{req.title}\n{req.content}"[:6000], 4,
                    profile="compact", min_score=0.55)
                retrieved = True
            except EmbeddingError as e:
                detail = f"向量检索失败，回退全量规则：{e}"
            except Exception as e:  # noqa: BLE001
                detail = f"检索异常，回退全量规则：{type(e).__name__}: {e}"

        yield _sse("stage", {
            "stage": "rules",
            "message": detail,
            "mode": req.mode,
            "rules": [{"code": r.code, "name": r.name, "category": r.category,
                       "level": r.suggestedLevel} for r in selected],
        })

        audit_req = AuditRequest(
            requestId=f"debug-{int(time.time() * 1000)}",
            articleId=0,
            triggerType="POST_AUDIT",
            targetPlatformKey="local",
            title=req.title,
            content=req.content,
            rules=selected,
            reasoningEffort=req.reasoningEffort,
            compactRules=(req.mode == "rag"),
            catalogRules=(req.mode == "e1"),
        )
        user_prompt = build_user_prompt(
            audit_req, selected, retrieved=retrieved,
            compact_rules=(req.mode == "rag"),
            catalog_rules=(req.mode == "e1"),
        )
        yield _sse("stage", {
            "stage": "prompt",
            "message": f"提示词已组装：system {len(SYSTEM_PROMPT)} 字 + user {len(user_prompt)} 字",
            "system": SYSTEM_PROMPT,
            "user": user_prompt,
        })

        yield _sse("stage", {
            "stage": "model_start",
            "message": f"开始调用模型 {settings.model}（{settings.provider}，reasoning={req.reasoningEffort or settings.reasoning_effort}）",
            "model": settings.model,
            "provider": settings.provider,
        })

        text_parts: list[str] = []
        usage = {"promptTokens": 0, "completionTokens": 0, "model": settings.model}
        try:
            provider = get_provider(settings.provider)
            for event in provider.judge_stream(
                    SYSTEM_PROMPT, user_prompt,
                    reasoning_effort=req.reasoningEffort):
                if event.get("type") == "delta":
                    text_parts.append(event.get("text", ""))
                    yield _sse("delta", {"text": event.get("text", "")})
                elif event.get("type") == "usage":
                    usage = event
                    yield _sse("usage", event)
        except ProviderError as e:
            yield _sse("error", {"message": str(e), "elapsedMs": int((time.time() - started) * 1000)})
            return
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": f"{type(e).__name__}: {e}",
                                 "elapsedMs": int((time.time() - started) * 1000)})
            return

        raw = "".join(text_parts)
        yield _sse("stage", {"stage": "parse", "message": "模型输出结束，开始解析 JSON",
                             "elapsedMs": int((time.time() - started) * 1000)})
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            yield _sse("error", {"message": f"JSON 解析失败：{e}", "raw": raw,
                                 "elapsedMs": int((time.time() - started) * 1000)})
            return

        yield _sse("result", {
            "data": data,
            "usage": usage,
            "durationMs": int((time.time() - started) * 1000),
            "mode": req.mode,
            "ruleCount": len(selected),
            "raw": raw,
        })
        yield _sse("done", {"elapsedMs": int((time.time() - started) * 1000)})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
