"""智能体服务入口。

职责：启动 FastAPI 应用、注册路由、提供健康检查。
具体能力在 api/ 下按契约拆分（审核/预检、跨平台适配）。

启动方式（在 agent 目录下）：
    .venv\\Scripts\\python.exe -m uvicorn main:app --port 8001
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.adapt import router as adapt_router
from api.audit import router as audit_router
from config import settings

app = FastAPI(
    title="自媒体平台 · 智能体服务",
    description="内容审核与跨平台适配的智能体服务，按 docs/Agent接口契约-v1.md 实现",
    version="0.3.0",
)

app.include_router(audit_router)
app.include_router(adapt_router)


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """参数校验失败统一返回 400。

    契约里写的是"参数不合法返回 400"，而 FastAPI 默认返回 422，
    所以在入口处统一改写，避免主系统侧按契约处理错误时对不上。
    """
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_request", "detail": str(exc), "contractVersion": "1.0"},
    )


@app.get("/health")
def health() -> dict:
    """健康检查：主系统与一键启动脚本用它判断服务是否存活。"""
    return {
        "status": "ok",
        "service": "zimeiti-agent",
        "contractVersion": "1.0",
        "provider": settings.provider,
        "model": settings.model if settings.provider != "mock" else "mock",
        "replayEnabled": settings.replay_enabled,
    }
