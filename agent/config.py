"""智能体服务的配置。

配置全部来自环境变量或 agent/.env 文件（.env 不进版本库）。
这样做的原因：API Key 不能写死在代码里、也不能进 Git ——
换一台机器或换一个模型供应商，只改 .env，不改代码。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 模型供应商 ----
    # mock     : 不调用任何外部服务，用规则模拟判定，供无 Key 时的联调与回归测试
    # deepseek : 通过 OpenAI 兼容接口调用 DeepSeek
    provider: str = "mock"

    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"

    # 单次模型调用超时（秒）。主系统侧的超时是 30 秒，这里要略小于它，
    # 保证"Agent 先超时并自己返回错误"，而不是让主系统先断开、拿不到任何错误信息。
    timeout_seconds: float = 25.0

    # 温度：审核判定要稳定，取低值
    temperature: float = 0.2

    # ---- 响应回放（测试设施）----
    # 开启后，同一 requestId 的请求直接返回缓存结果：
    #  - 重复评测不重复花钱
    #  - 离线/断网时也能跑回归测试
    # 注意：它是测试工具，不参与业务判断
    replay_enabled: bool = True
    replay_dir: str = ".replay"

    # ---- 规则检索（RAG）----
    # 开启后：先从规则库里召回最相关的 rag_top_k 条，再交给模型判断。
    # 关闭后：把全部规则塞进提示词（规则少时也能用，但无法做论文的三方案对比）。
    rag_enabled: bool = True
    rag_top_k: int = 6

    # 向量化使用硅基流动的 bge-m3（免费、1024 维、OpenAI 兼容）
    siliconflow_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"
    embedding_timeout_seconds: float = 15.0

    # ---- 与主系统之间的可选共享口令 ----
    # 留空表示不校验。生产环境应当设置，防止本机其他程序随意调用。
    agent_token: str = ""


settings = Settings()
