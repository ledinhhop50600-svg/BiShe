"""模型供应商抽象。

为什么要抽象：审核能力最终取决于模型，但"用哪家的模型"是会变的 ——
开发期用便宜的、预算紧时降级到免费的、论文里要对比不同模型的效果。
把"调用模型"收在一个接口里，上层（审核流程）就不用关心具体是谁。
"""

from dataclasses import dataclass
from typing import Iterator


@dataclass
class ProviderResult:
    """一次模型调用的结果。"""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ProviderError(RuntimeError):
    """模型服务不可用（网络、鉴权、余额、限流等）—— 对应契约的 HTTP 503。"""


class BaseProvider:
    """供应商接口：输入两段提示词，返回模型输出的原始文本。"""

    name: str = "base"

    def judge(self, system_prompt: str, user_prompt: str,
              reasoning_effort: str | None = None,
              max_tokens: int | None = None) -> ProviderResult:  # pragma: no cover
        raise NotImplementedError

    def adapt(self, system_prompt: str, user_prompt: str,
              reasoning_effort: str | None = None,
              max_tokens: int | None = None) -> ProviderResult:
        """跨平台适配调用。

        默认实现与 judge 完全相同 —— 两者本质都是"两段提示词 → 一段 JSON 文本"，
        区别只在提示词内容。单独留一个方法是为了让 Mock 能按适配场景返回不同结构。
        """
        return self.judge(system_prompt, user_prompt,
                          reasoning_effort=reasoning_effort, max_tokens=max_tokens)

    def judge_stream(self, system_prompt: str, user_prompt: str,
                     reasoning_effort: str | None = None,
                     max_tokens: int | None = None) -> Iterator[dict]:
        """流式判定（调试页用）。默认实现退化为一次完整调用再切片。"""
        result = self.judge(system_prompt, user_prompt,
                            reasoning_effort=reasoning_effort, max_tokens=max_tokens)
        yield {"type": "delta", "text": result.text}
        yield {"type": "usage", "promptTokens": result.prompt_tokens,
               "completionTokens": result.completion_tokens, "model": result.model}
