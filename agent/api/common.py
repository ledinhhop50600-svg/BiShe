"""接口层的公共逻辑。"""

from fastapi import HTTPException

from config import settings


def check_token(token: str) -> None:
    """可选的共享口令校验：配置了 AGENT_TOKEN 才校验。

    用途：本机演示时防止其他进程随手调用；不配置则完全开放（默认）。
    """
    if settings.agent_token and token != settings.agent_token:
        raise HTTPException(status_code=401, detail="invalid agent token")
