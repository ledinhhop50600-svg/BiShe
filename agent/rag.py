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


def _chunks(text: str, size: int = 300, max_chunks: int = 20) -> list[str]:
    """把文本切成约 size 字的块，尽量在句子边界切。

    为什么按"字数"而不是按"句子数"切：篇幅是变量。早前用 12 句上限，
    一两千字的文章会被截断（后半段直接不参与检索，那里的违规永远发现不了）。
    按字数切能保证覆盖率：20 块 × 300 字 = 6000 字，足够覆盖常规长文；
    超长内容会被截断，这一点在文档中如实说明。
    """
    parts = re.split(r"(?<=[。！？!?\n])", text or "")
    sentences = [p.strip() for p in parts if p.strip()]
    chunks: list[str] = []
    buf = ""
    for s in sentences:
        if len(buf) + len(s) <= size:
            buf += s
        else:
            if buf:
                chunks.append(buf)
            buf = s
    if buf:
        chunks.append(buf)
    if not chunks:
        chunks = [(text or "")[:size]]
    return chunks[:max_chunks]


def _all_terms(rules: list[RuleItem], extra_terms: list[str] | None = None) -> list[str]:
    """关键词来源：规则里列出的示例词 + 额外传入的词表（敏感词库）。

    为什么要把敏感词库也算进来：规则里的示例词往往是完整短语（如"加我微信领资料"），
    而正文写的是"加我微信 skincarer_note 领取" —— 短语对不上就漏了。
    敏感词库由管理员维护、词更短更通用（"加我微信"），正好补上这个缺口。
    """
    terms: list[str] = []
    for r in rules:
        terms.extend(_keyword_terms(r))
    for t in extra_terms or []:
        if t and len(t) >= 2:
            terms.append(t)
    # 去重，长词优先（长词更具体）
    return sorted(set(terms), key=len, reverse=True)


def retrieve(rules: list[RuleItem], query: str, top_k: int,
             extra_terms: list[str] | None = None,
             profile: str = "legacy", min_score: float = 0.0) -> tuple[list[RuleItem], str]:
    """从规则中召回与 query 最相关的 top_k 条。

    采用**混合检索**：词面命中优先 + 向量检索补足。
    为什么不能只用向量：实测发现，一句话里同时出现"国家级"和"三天见效"时，
    向量会被功效类语义带偏，导致"绝对化用语"（AD-001）排不进前 6 名 —— 而它明明词面命中。
    合规场景里"规则列出的示例词出现在内容中"是极强的信号，不能交给相似度去赌。
    因此：规则引号内的示例词只要在正文中出现，该规则优先入选；剩余名额按分段向量相似度补足。

    profile:
      - legacy：保留原行为（关键词命中全部优先，top_k 直接截断），用于复现 C 基线；
      - compact：C1 修复版（关键词限流+排序、向量阈值、类别去重、规则卡片）。

    @return (召回结果, 说明文字) —— 说明文字会写进 trace，便于演示与排查。
    @throws EmbeddingError 向量化失败（调用方应降级为使用全部规则）
    """
    if not rules:
        return [], "没有可用规则"
    if top_k <= 0 or top_k >= len(rules):
        return rules, f"规则数 {len(rules)} 未超过阈值，全部使用"

    # ---- 1) 策略元规则：suggestedLevel == 0 的规则是"判定口径"（如 BIZ-001 商业推广属性判定）。
    #         它跟具体内容无关，但决定整份判定的松紧（无商业属性该降级还是判违规）。
    #         实测过一次失误：检索把 BIZ-001 挤出了前 6，导致个人分享被判成违规。
    #         所以这类规则不参与检索竞争，每次必须带上。
    meta_rules = [r for r in rules if (r.suggestedLevel or 0) == 0]
    meta_codes = {r.code for r in meta_rules}

    # ---- 2) 词面兜底（只在非元规则里做）----
    # legacy 会把敏感词库也套到每条规则上；compact 只使用规则自己的示例词，
    # 且敏感词必须也出现在该规则正文里，避免"一个敏感词命中所有规则"
    # （C 基线里 M1 出现 15 条规则同时命中）。
    extra_set = {t for t in (extra_terms or []) if t}
    term_df: dict[str, int] = {}
    if profile == "compact":
        for r in rules:
            for t in set(_keyword_terms(r)):
                term_df[t] = term_df.get(t, 0) + 1
            for t in extra_set:
                if t in (r.content or ""):
                    term_df[t] = term_df.get(t, 0) + 1

    keyword_hits: list[tuple[int, RuleItem, list[str]]] = []
    for r in rules:
        if r.code in meta_codes:
            continue
        if profile == "compact":
            terms = _keyword_terms(r)
            hits = [t for t in terms if t in query]
            for t in extra_set:
                if t in query and t in (r.content or "") and t not in hits:
                    hits.append(t)
        else:
            hits = [t for t in _all_terms([r], extra_terms) if t in query]
        if hits:
            keyword_hits.append((len(hits), r, hits))

    if profile == "compact":
        # 关键词命中按“词的特异性”排序：在越少规则里出现的词，权重越高；
        # 最多保留 top_k - 元规则 条，避免十几条弱相关规则把向量结果全部挤掉。
        def kw_score(hits: list[str]) -> float:
            return sum((len(t) ** 1.5) / max(1, term_df.get(t, 1)) for t in hits)

        keyword_hits.sort(
            key=lambda item: (kw_score(item[2]), max(len(t) for t in item[2]), item[0]),
            reverse=True,
        )
        max_keyword = max(0, top_k - len(meta_rules))
        forced = meta_rules + [r for _, r, _ in keyword_hits[:max_keyword]]
    else:
        keyword_hits.sort(key=lambda item: item[0], reverse=True)
        forced = meta_rules + [r for _, r, _ in keyword_hits]
    forced_codes = {r.code for r in forced}

    # ---- 3) 分段向量检索（只对未被词面命中的规则打分）----
    queries = _chunks(query)
    candidates = [r for r in rules if r.code not in forced_codes]
    vector_ranked: list[tuple[float, RuleItem]] = []
    vector_all: list[tuple[float, RuleItem]] = []

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
            vector_all.append((best, r))
            if profile != "compact" or best >= min_score:
                vector_ranked.append((best, r))
        vector_ranked.sort(key=lambda pair: pair[0], reverse=True)
        vector_all.sort(key=lambda pair: pair[0], reverse=True)

    # ---- 4) 合并：元规则 + 词面命中 优先，向量分数补足 ----
    fallback_used = False
    if profile == "compact":
        # 类别去重：同一类别最多 2 条，避免 AD-001/002/003 占满名额；多类样本仍能覆盖多个类别。
        picked: list[RuleItem] = []
        seen: set[str] = set()
        category_count: dict[str, int] = {}
        for r in forced + [r for _, r in vector_ranked]:
            if r.code in seen:
                continue
            category = r.category or "其他"
            if category_count.get(category, 0) >= 2:
                continue
            picked.append(r)
            seen.add(r.code)
            category_count[category] = category_count.get(category, 0) + 1
            if len(picked) >= top_k:
                break

        # 召回安全阀：短评论没有词面命中时，向量分可能普遍低于阈值；
        # 如果只剩元规则，补 2 条未过阈值但分数最高的规则，避免“漏掉整类违规”。
        if len(picked) <= len(meta_rules) and vector_all:
            fallback_used = True
            for _, r in vector_all:
                if r.code in seen:
                    continue
                category = r.category or "其他"
                if category_count.get(category, 0) >= 2:
                    continue
                picked.append(r)
                seen.add(r.code)
                category_count[category] = category_count.get(category, 0) + 1
                if len(picked) >= min(top_k, len(meta_rules) + 2):
                    break
    else:
        picked = (forced + [r for _, r in vector_ranked])[:top_k]

    meta_detail = "、".join(r.code for r in meta_rules) or "无"
    kw_detail = "、".join(f"{r.code}←{'/'.join(hits[:2])}" for _, r, hits in keyword_hits) or "无"
    vec_detail = "、".join(f"{r.code}({s:.2f})" for s, r in vector_ranked[: max(0, top_k - len(forced))]) or "无"
    threshold = f" | 阈值 {min_score:.2f}" if profile == "compact" else ""
    fallback_note = " | 召回安全阀：补低分向量规则" if fallback_used else ""
    detail = (f"[{profile}] 从 {len(rules)} 条规则中召回 {len(picked)} 条{threshold}{fallback_note} | 元规则：{meta_detail} | "
              f"词面命中：{kw_detail} | 向量补足：{vec_detail} | 分段 {len(queries)} 路")
    return picked, detail


def localize(content: str, rules: list[RuleItem], max_chunks: int = 20,
             extra_terms: list[str] | None = None) -> tuple[str, str]:
    """关键词定位：把长文"聚焦"到命中了规则示例词的段落（含前后各一段上下文）。

    设计意图（来自需求提出者的思路）：长文先按关键词定位可疑段落，只把这几段送给模型，
    以降低 token 与耗时；**如果一段都没命中，必须回退全文** ——
    否则就退化成了"关键词没命中就放行"，会重现关键词方案的全量漏判。

    已知代价：分级判定（商业推广 vs 个人分享）需要看整体内容，只看片段的模型可能判偏。
    因此它只作为**可选模式**，通过 A/B 实验决定是否启用。

    @return (聚焦后的内容, 说明文字)
    """
    chunks = _chunks(content, max_chunks=max_chunks)
    if len(chunks) <= 1:
        return content, "内容较短（单段），无需定位"

    terms = _all_terms(rules, extra_terms)

    hit_idx = [i for i, c in enumerate(chunks) if any(t in c for t in terms)]
    if not hit_idx:
        return content, f"分 {len(chunks)} 段，关键词未命中任何段落 → 回退全文"

    keep: set[int] = set()
    for i in hit_idx:
        keep.update({max(0, i - 1), i, min(len(chunks) - 1, i + 1)})
    focused = "\n".join(chunks[i] for i in sorted(keep))
    return focused, (f"分 {len(chunks)} 段，命中 {len(hit_idx)} 段，"
                     f"发送 {len(keep)} 段（含前后上下文）")
