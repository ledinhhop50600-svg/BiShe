"""供应商工厂：按配置创建对应的实现。"""

from providers.base import BaseProvider, ProviderError
from providers.mock import MockProvider
from providers.openai_compat import OpenAICompatProvider

# 缓存实例：OpenAI 客户端内部维护连接池，每次请求新建会浪费资源
_cache: dict[str, BaseProvider] = {}


def get_provider(name: str) -> BaseProvider:
    if name in _cache:
        return _cache[name]

    if name == "mock":
        provider: BaseProvider = MockProvider()
    elif name in ("deepseek", "openai", "openai-compat"):
        provider = OpenAICompatProvider()
    else:
        raise ProviderError(f"不支持的 provider：{name}（可选 mock / deepseek）")

    _cache[name] = provider
    return provider
