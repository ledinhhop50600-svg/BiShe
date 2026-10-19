"""响应回放：按 requestId 把响应缓存到磁盘。

用途（对应契约的"响应回放模式"）：
- **重复评测不重复花钱**：同一批样本跑多次，命中缓存后不再调用模型；
- **离线回归测试**：没有网络或没有 Key 时，仍能验证主系统侧的解析与展示；
- **演示保底**：万一现场网络不稳，可以切到回放模式完成演示。

注意：它是测试设施，不参与业务判断。默认开启，可在 .env 里关闭。
"""

import json
import os
import re

from config import settings

_SAFE = re.compile(r"[^a-zA-Z0-9_-]")


def _path(request_id: str) -> str:
    safe = _SAFE.sub("_", request_id)[:80]
    return os.path.join(settings.replay_dir, f"{safe}.json")


def load(request_id: str) -> dict | None:
    if not settings.replay_enabled:
        return None
    path = _path(request_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 - 缓存损坏时当作未命中，不影响主流程
        return None


def save(request_id: str, payload: dict) -> None:
    if not settings.replay_enabled:
        return
    os.makedirs(settings.replay_dir, exist_ok=True)
    path = _path(request_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001 - 缓存写失败不影响本次返回
        pass
