"""Mock 供应商：不调用任何外部模型，按关键词给出确定性结果。

它的用途有两个：
1. **没有 API Key 时也能联调**：整条链路（主系统 → Agent → 结构化结论 → 落库）可以先跑通；
2. **回归测试**：结论是确定的，测试不会因为模型"今天心情不同"而波动。

它**不是**审核能力本身 —— 真正的判定在阶段 5 由大模型 + 规则检索完成。
这里刻意保持简单：只做关键词匹配，结果固定。
"""

import json
import re

from format_check import parse_tag_range
from providers.base import BaseProvider, ProviderResult

# 关键词 -> (规则编号, 规则名, 类别, 问题描述)
KEYWORDS = [
    ("国家级", "AD-001", "绝对化用语", "广告法", "绝对化用语"),
    ("最高级", "AD-001", "绝对化用语", "广告法", "绝对化用语"),
    ("全网最低价", "AD-002", "无法核实的价格承诺", "广告法", "无法核实的价格比较"),
    ("三天见效", "FB-001", "功效承诺", "虚假宣传", "具体时限的效果承诺"),
    ("加我微信", "DR-001", "站外引流", "引流诱导", "站外引流"),
    ("处方药", "PB-001", "违禁品交易", "违禁品", "违禁品交易"),
    ("包治", "AD-003", "医疗功效宣称", "广告法", "医疗功效宣称"),
]

# 提示词里"待审核内容"部分的起止标记，见 prompts.py
CONTENT_START = "【待审核内容】"
CONTENT_END = "【输出要求】"


class MockProvider(BaseProvider):
    name = "mock"

    def judge(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        article = _extract_article(user_prompt)
        hits = []
        for word, code, name, category, issue in KEYWORDS:
            if word in article:
                hits.append({"word": word, "code": code, "name": name, "category": category, "issue": issue})

        if not hits:
            payload = {
                "riskLevel": 0,
                "reason": "（Mock 判定）未匹配到预设的违规关键词。",
                "hitRules": [],
                "violations": [],
                "suggestion": "可以发布。",
                "confidence": 0.5,
            }
        else:
            max_level = 3 if any(h["code"] == "PB-001" for h in hits) else 2
            # 去重命中的规则
            seen, hit_rules = set(), []
            for h in hits:
                if h["code"] not in seen:
                    seen.add(h["code"])
                    hit_rules.append({"code": h["code"], "name": h["name"], "category": h["category"]})
            violations = [
                {"fragment": h["word"], "issue": h["issue"], "suggestion": f"删除或替换「{h['word']}」"}
                for h in hits
            ]
            payload = {
                "riskLevel": max_level,
                "reason": "（Mock 判定）内容中出现 " + "、".join(f"「{h['word']}」" for h in hits) + " 等表述，命中规则库中的相关条目。",
                "hitRules": hit_rules,
                "violations": violations,
                "suggestion": "建议修改上述片段后重新提交。",
                "confidence": 0.6,
            }

        return ProviderResult(
            text=json.dumps(payload, ensure_ascii=False),
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
        )

    def adapt(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        """无 Key 时的确定性适配：截断到平台上限 + 生成固定数量的标签。

        它不追求"改写得像人"，只保证整条链路（格式自检、合规预检、落库、界面）
        在没有网络、没有 Key 的情况下也能跑通。
        """
        platform_name = _search(user_prompt, r"【目标平台】\n(.+?)（", "目标平台")
        title_max = int(_search(user_prompt, r"标题上限：(\d+) 字", "0"))
        content_max = int(_search(user_prompt, r"正文上限：(\d+) 字", "1000"))
        tag_rule = _search(user_prompt, r"话题标签规则：([^\n]+)", "")
        src_title = _search(user_prompt, r"【源文章】\n标题：([^\n]+)", "")
        src_content = _search(user_prompt, r"正文：(.+?)\n\n【输出要求】", "")

        title = src_title if title_max > 0 else ""
        if title_max > 0:
            title = title[:title_max]

        prefix = f"（Mock 适配·{platform_name}）"
        body = prefix + src_content
        if content_max > 0:
            body = body[:content_max]

        lo, hi = parse_tag_range(tag_rule)
        if hi == 0:
            tags = []
        else:
            n = max(lo or 0, min(hi or 3, 3))
            tags = ["#测试", "#跨平台适配", "#内容运营"][:n]

        payload = {"title": title, "content": body, "tags": tags}
        return ProviderResult(
            text=json.dumps(payload, ensure_ascii=False),
            model="mock",
            prompt_tokens=0,
            completion_tokens=0,
        )


def _search(text: str, pattern: str, default: str) -> str:
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else default


def _extract_article(user_prompt: str) -> str:
    """从完整的提示词里只取出"待审核内容"部分。

    必须这么做：规则文本里本身就包含"国家级"这类词，如果在整段提示词里匹配，
    规则会被自己命中，得出假阳性。
    """
    start = user_prompt.find(CONTENT_START)
    end = user_prompt.find(CONTENT_END)
    if start == -1:
        return user_prompt
    start += len(CONTENT_START)
    return user_prompt[start:end] if end != -1 else user_prompt[start:]
