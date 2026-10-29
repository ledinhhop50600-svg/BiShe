"""判定与归因分离（E2 原型）：不把规则全文塞进 prompt，先让模型判断并给出违规片段，
再把片段映射回规则库。

为什么单独做：
  - 纯大模型（B）准确率不低，但没有规则引用，模型还会编造 AD-ABSOLUTE 这类库里不存在的编号；
  - RAG（C）把规则塞进 prompt，能引用，但规则噪声会拉低准确率、增加 token；
  - 这里让模型只负责“判不判、哪里违规”，规则引用由确定性的词面 + 字符重合度匹配完成，
    引用编号再回库校验。判断质量不被规则噪声干扰，引用也可以追溯。

注意：这是“关联规则”，不是法律意义上的唯一依据；匹配不到时必须显示未匹配并转人工。
"""

import re

_QUOTED = re.compile(r'"([^"]{2,15})"')
_PUNCT = re.compile(r"[\s，。！？、；：,.!?;:\"'“”‘’（）()\[\]【】]+")

# 规则正文里的“业务关键词”。不是分词器，只是把审核场景最常用的触发词显式列出，
# 避免规则只写“处方药”但没加引号时，后置归因完全匹配不到。
_KEYWORDS = [
    "处方药", "违禁", "烟草", "野生动物", "管制器具", "代购", "销售", "转让",
    "微信", "QQ", "手机号", "私下交易", "站外", "私聊", "链接", "二维码",
    "评论区", "主页", "置顶", "橱窗", "领取", "私信", "偏见", "地域", "歧视",
    "国家级", "最高级", "最佳", "第一", "顶级", "绝对化", "绝对安全",
    "功效", "治疗", "疗效", "虚假", "夸大", "侵权", "抄袭", "转载", "低俗",
    "色情", "歧视", "辱骂", "仇恨", "诈骗", "赌博", "毒品", "枪支", "假货",
]


def _bigrams(text: str) -> set[str]:
    clean = _PUNCT.sub("", text or "")
    return {clean[i:i + 2] for i in range(max(0, len(clean) - 1))}


def _field(rule, key: str, default=None):
    """同时支持 RuleItem 对象与 experiment_compare 里的 dict。"""
    if isinstance(rule, dict):
        return rule.get(key, default)
    return getattr(rule, key, default)


def _rule_terms(rule) -> list[str]:
    terms = _QUOTED.findall(_field(rule, "content", "") or "")
    # 规则名本身也是线索（如“站外引流”“违禁品交易”）
    name = (_field(rule, "name", "") or "").strip()
    content = _field(rule, "content", "") or ""
    if name:
        terms.append(name)
    terms.extend(k for k in _KEYWORDS if k in content or k in name)
    return [t for t in dict.fromkeys(terms) if len(t) >= 2]


def attribute_fragment(fragment: str, rules: list, top_n: int = 2,
                       min_overlap: float = 0.18) -> list[dict]:
    """把一段违规原文映射到最可能的规则。

    评分 = 规则示例词/规则名的命中的长度 + 2-gram 重合度（仅作补充）。
    只返回超过阈值的 top_n 条；没有命中就返回空列表，不硬凑。
    """
    text = (fragment or "").strip()
    if not text or not rules:
        return []
    frag_grams = _bigrams(text)
    if not frag_grams:
        return []

    scored = []
    for rule in rules:
        terms = _rule_terms(rule)
        exact = [t for t in terms if t in text]
        exact_score = sum(len(t) for t in exact)
        rule_grams = _bigrams(f"{_field(rule, 'name', '')} {_field(rule, 'content', '')}")
        overlap = len(frag_grams & rule_grams) / max(1, len(frag_grams))
        # 只有词面命中或足够的字符重合才算候选，避免“每个片段都匹配所有规则”
        if exact_score == 0 and overlap < min_overlap:
            continue
        score = exact_score + overlap * 3
        scored.append({
            "code": _field(rule, "code", ""),
            "name": _field(rule, "name", ""),
            "category": _field(rule, "category", ""),
            "source": _field(rule, "source", None),
            "score": round(score, 2),
            "matchedTerms": exact[:3],
            "overlap": round(overlap, 2),
        })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_n]


def attach_citations(result: dict, rules: list, max_rules: int = 5) -> dict:
    """给 B 的结果补上规则引用；返回新的 result，不修改模型原始判断。"""
    risk = int(result.get("riskLevel") or 0)
    out = dict(result)
    if risk < 2:
        out["hitRules"] = []
        out["ruleCitations"] = []
        return out

    fragments = [str(v.get("fragment") or "") for v in (result.get("violations") or [])]
    if not fragments:
        # 模型给了阻断结论但没给片段：用整段原文做一次保守映射，并标注低置信
        fragments = [str(result.get("_content") or "")]
        out["citationFallback"] = True

    by_code = {}
    for fragment in fragments:
        for candidate in attribute_fragment(fragment, rules):
            code = candidate["code"]
            if not code:
                continue
            previous = by_code.get(code)
            if previous is None or candidate["score"] > previous["score"]:
                by_code[code] = candidate

    # 片段级没有匹配时，再用整段原文做一次保守映射；只在完全为空时兜底，避免到处乱引用。
    if not by_code:
        for candidate in attribute_fragment(str(result.get("_content") or ""), rules, top_n=max_rules):
            by_code[candidate["code"]] = candidate

    citations = sorted(by_code.values(), key=lambda item: item["score"], reverse=True)[:max_rules]
    out["hitRules"] = [
        {"code": c["code"], "name": c["name"], "category": c["category"], "source": c["source"]}
        for c in citations
    ]
    out["ruleCitations"] = citations
    return out
