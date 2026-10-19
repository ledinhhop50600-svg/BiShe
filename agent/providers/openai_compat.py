"""OpenAI 兼容接口供应商：通过官方 openai SDK 调用 DeepSeek。

为什么用 openai SDK 而不是 DeepSeek 专用库：DeepSeek 提供 OpenAI 兼容接口，
用同一套代码就能切换到硅基流动、智谱等兼容供应商 —— 换模型只改 .env。
"""

import time

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from config import settings
from providers.base import BaseProvider, ProviderError, ProviderResult


class OpenAICompatProvider(BaseProvider):
    name = "openai-compat"

    def __init__(self) -> None:
        if not settings.api_key:
            raise ProviderError("未配置 API Key（.env 中的 API_KEY）")
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
        )

    def judge(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        started = time.time()
        try:
            # response_format={"type": "json_object"} 要求模型只输出 JSON，
            # 大幅减少"输出里夹着解释文字导致解析失败"的情况（DeepSeek 支持该参数）
            resp = self._client.chat.completions.create(
                model=settings.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.temperature,
                response_format={"type": "json_object"},
                # 关闭思考模式（默认是 high）：审核不需要长推理，开启会让长文请求既慢又贵，
                # 更严重的是推理可能耗尽输出预算，导致 content 为空、JSON 解析失败（实测踩过）。
                reasoning_effort=settings.reasoning_effort,
                # 显式限制输出长度：长文可能命中多处违规，JSON 会变长；
                # 不设上限时若被截断，JSON 解析会直接失败（契约里对应 422）。
                max_tokens=settings.max_output_tokens,
                timeout=settings.timeout_seconds,
            )
        except APITimeoutError as e:
            raise ProviderError(f"模型调用超时（{settings.timeout_seconds} 秒）") from e
        except APIConnectionError as e:
            raise ProviderError(f"无法连接模型服务：{e}") from e
        except APIStatusError as e:
            # 401 鉴权失败、402 余额不足、429 限流都属于这一类
            raise ProviderError(f"模型服务返回错误（HTTP {e.status_code}）：{e.message}") from e
        except Exception as e:  # noqa: BLE001 - 兜底，统一转成 503
            raise ProviderError(f"模型调用失败：{type(e).__name__}: {e}") from e

        choice = resp.choices[0]
        text = choice.message.content or ""
        finish = choice.finish_reason

        # 空内容 / 被截断必须显式报错，不能把空串丢给上层去"解析失败"——那样只能看到一个 422，
        # 无从判断是模型没输出、还是输出被截断。
        if not text.strip():
            raise ProviderError(
                f"模型返回空内容（finish_reason={finish}）。常见原因：思考过程耗尽了输出预算，"
                f"或 max_tokens 设置过小"
            )
        if finish == "length":
            raise ProviderError(
                f"模型输出被截断（finish_reason=length，max_tokens={settings.max_output_tokens}），"
                f"JSON 不完整"
            )

        usage = resp.usage
        return ProviderResult(
            text=text,
            model=settings.model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        )
