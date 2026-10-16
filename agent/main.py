"""智能体服务骨架。

阶段 0 只做最小可运行版本：提供一个健康检查接口，用来验证 Python 环境是否就绪。
阶段 4 会在此基础上加入：模型 Provider 抽象、审核接口、适配接口。
阶段 5/6 再加入：工具注册表、规则库检索（RAG）、分级判定与跨平台适配。

启动方式（在 agent 目录下）：
    .venv\\Scripts\\python.exe -m uvicorn main:app --port 8001

端口说明：本项目智能体服务固定使用 **8001**。
（8000 端口在这台机器上已被另一个项目「设备故障诊断 Agent」占用，避开它以免冲突。）
"""

from fastapi import FastAPI

app = FastAPI(
    title="自媒体平台 · 智能体服务",
    description="内容审核与跨平台适配的智能体服务，供 Spring Boot 主系统通过 HTTP 调用",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    """健康检查接口。

    用途有两个：主系统在调用审核前可先探测服务是否存活；
    一键启动脚本用它确认智能体服务是否已经起来。
    """
    return {
        "status": "ok",
        "service": "zimeiti-agent",
        "stage": "阶段 0 骨架（仅健康检查）",
    }
