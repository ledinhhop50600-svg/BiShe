"""规则检索（RAG）：把规则和目标内容都向量化，召回最相关的若干条规则。

为什么需要它：
- 规则库会增长。全量塞进提示词既费 token、也会干扰模型判断（无关规则是噪声）；
- 论文需要「RAG + 大模型」这一组对比方案（关键词规则 / 纯大模型 / RAG+大模型）。

实现选择：硅基流动的免费 bge-m3（1024 维，OpenAI 兼容接口）。
关键优化：**规则向量按「编号 + 内容哈希」缓存在内存里** ——
同一批规则只向量化一次，之后每次请求只需要向量化查询文本（一次小请求）。
规则内容一旦修改，哈希变化，会自动重新向量化（不会用到过期向量）。
"""

import hashlib
import math
import re

from openai import OpenAI

from config import settings
from schemas import RuleItem

_client: OpenAI | None = None
_rule_cache: dict[str, list[float]] = {}

# 规则文本里用双引号列出的示例词，例如：出现"国家级""最高级"等绝对化表述
_QUOTED = re.compile(r'"([^"]{2,15})"')


def _keyword_terms(rule: RuleItem) -> list[str]:
    """抽取规则中列出的示例词（引号内的词），作为词面匹配的依据。"""
    return _QUOTED.findall(rule.content or "")


class EmbeddingError(RuntimeError):
    """向量化服务不可用。调用方应降级为"使用全部规则"。"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.siliconflow_api_key:
            raise EmbeddingError("未配置 SILICONFLOW_API_KEY")
        _client = OpenAI(
            api_key=settings.siliconflow_api_key,
            base_url=settings.embedding_base_url,
            timeout=settings.embedding_timeout_seconds,
        )
    return _client


def _embed(texts: list[str]) -> list[list[float]]:
    try:
        resp = _get_client().embeddings.create(model=settings.embedding_model, input=texts)
    except Exception as e:  # noqa: BLE001 - 统一转成 EmbeddingError，由调用方降级
        raise EmbeddingError(f"{type(e).__name__}: {e}") from e
    # 按 index 排序，保证返回顺序与输入顺序一致
    data = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in data]


def _rule_key(rule: RuleItem) -> str:
    """缓存键：规则编号 + 内容哈希（内容改了就会重新向量化）"""
    digest = hashlib.sha1(rule.content.encode("utf-8")).hexdigest()[:10]
    return f"{rule.code}:{digest}"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _sentences(text: str, limit: int = 12) -> list[str]:
    """把内容切成句子，作为多路查询。

    为什么要分段检索：一篇内容往往同时涉及多个方面（价格、功效、引流……）。
    如果把整篇当成一个查询向量，向量会被"平均"掉，与某一条规则高度相关的句子会被稀释，
    导致该规则排不进前 K 名（实测就漏掉过"国家级"对应的绝对化用语规则）。
    分段后每条规则取"与最相关句子的最高分"，召回明显更稳。
    """
    parts = re.split(r"[。！？!?\n]+", text or "")
    out = [p.strip() for p in parts if len(p.strip()) >= 4]
    if not out:
        out = [(text or "")[:500]]
    return out[:limit]


def retrieve(rules: list[RuleItem], query: str, top_k: int) -> tuple[list[RuleItem], str]:
    """从规则中召回与 query 最相关的 top_k 条。

    采用**混合检索**：词面命中优先 + 向量检索补足。
    为什么不能只用向量：实测发现，一句话里同时出现"国家级"和"三天见效"时，
    向量会被功效类语义带偏，导致"绝对化用语"（AD-001）排不进前 6 名 —— 而它明明词面命中。
    合规场景里"规则列出的示例词出现在内容中"是极强的信号，不能交给相似度去赌。
    因此：规则引号内的示例词只要在正文中出现，该规则优先入选；剩余名额按分段向量相似度补足。

    @return (召回结果, 说明文字) —— 说明文字会写进 trace，便于演示与排查。
    @throws EmbeddingError 向量化失败（调用方应降级为使用全部规则）
    """
    if not rules:
        return [], "没有可用规则"
    if top_k <= 0 or top_k >= len(rules):
        return rules, f"规则数 {len(rules)} 未超过阈值，全部使用"

    # ---- 1) 词面兜底 ----
    keyword_hits: list[tuple[int, RuleItem, list[str]]] = []
    for r in rules:
        hits = [t for t in _keyword_terms(r) if t in query]
        if hits:
            keyword_hits.append((len(hits), r, hits))
    keyword_hits.sort(key=lambda item: item[0], reverse=True)
    forced = [r for _, r, _ in keyword_hits]
    forced_codes = {r.code for r in forced}

    # ---- 2) 分段向量检索（只对未被词面命中的规则打分）----
    queries = _sentences(query)
    candidates = [r for r in rules if r.code not in forced_codes]
    vector_ranked: list[tuple[float, RuleItem]] = []

    if candidates and len(forced) < top_k:
        missing = [r for r in candidates if _rule_key(r) not in _rule_cache]
        texts = queries + [f"{r.name}：{r.content}" for r in missing]
        vectors = _embed(texts)
        query_vecs = vectors[: len(queries)]
        for r, vec in zip(missing, vectors[len(queries):]):
            _rule_cache[_rule_key(r)] = vec

        for r in candidates:
            rv = _rule_cache[_rule_key(r)]
            best = max(_cosine(qv, rv) for qv in query_vecs)
            vector_ranked.append((best, r))
        vector_ranked.sort(key=lambda pair: pair[0], reverse=True)

    # ---- 3) 合并：词面命中优先，向量分数补足 ----
    picked = (forced + [r for _, r in vector_ranked])[:top_k]

    kw_detail = "、".join(f"{r.code}←{'/'.join(hits[:2])}" for _, r, hits in keyword_hits) or "无"
    vec_detail = "、".join(f"{r.code}({s:.2f})" for s, r in vector_ranked[: max(0, top_k - len(forced))]) or "无"
    detail = (f"从 {len(rules)} 条规则中召回 {len(picked)} 条 | 词面命中：{kw_detail} | "
              f"向量补足：{vec_detail} | 分段 {len(queries)} 路")
    return picked, detail
