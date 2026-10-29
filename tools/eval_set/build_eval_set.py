"""构建统一评测集：自建样本 + 公开数据集抽样。

输入：
  tools/eval_set/self_built.json     自建样本（按区分度分层设计）
  tools/eval_set/raw/ToxiCN_1.0.csv  公开数据集（辱骂/仇恨，12k 条）
输出：
  tools/eval_set/samples.json        统一格式，供 experiment_compare.py 使用

为什么这样组合：
- 公开数据集提供**真实用户文本**与**第三方标注**，可信度高；但它只覆盖"辱骂/仇恨"一类；
- 自建样本补齐其余五类，并专门设计**能拉开方案差距**的样本（语境陷阱、词表盲区、分级边界、长文）；
- 二者合并后，既能对外证明"用了真实数据"，又能对内检验各方案的能力差异。

用法：python tools/eval_set/build_eval_set.py
"""

import csv
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SELF_PATH = os.path.join(HERE, "self_built.json")
TOXICN_PATH = os.path.join(HERE, "raw", "ToxiCN_1.0.csv")
COLD_PATH = os.path.join(HERE, "raw", "COLD_test.csv")
OUT_PATH = os.path.join(HERE, "samples.json")

TOXICN_PER_CLASS = 100  # ToxiCN toxic / non-toxic 各抽多少条
COLD_PER_CLASS = 100    # COLD offensive / non-offensive 各抽多少条
SEED = 42               # 固定随机种子，保证抽样可复现


def load_self_built():
    with open(SELF_PATH, encoding="utf-8") as f:
        data = json.load(f)
    samples = data["samples"]
    for s in samples:
        s.setdefault("source", "自建")
        s["binary_only"] = False
    return samples


def _pick_with_keep(pool, per_class, base_count, seed):
    """先保留旧版抽到的 base_count 条，再补足到 per_class 条，保证历史样本不漂移。"""
    rnd = random.Random(seed)
    base = rnd.sample(pool, min(base_count, len(pool)))
    base_texts = {(r.get("content") or "").strip() for r in base}
    remaining = [r for r in pool if (r.get("content") or "").strip() not in base_texts]
    extra = rnd.sample(remaining, min(max(0, per_class - len(base)), len(remaining)))
    return base + extra


def load_toxicn():
    if not os.path.exists(TOXICN_PATH):
        print("⚠️ 未找到 ToxiCN，跳过公开数据集部分")
        return []

    with open(TOXICN_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        # 第一列表头带 BOM，统一清理
        rows = [{ (k or "").lstrip("﻿"): v for k, v in r.items()} for r in reader]

    toxic = [r for r in rows if (r.get("toxic") or "").strip() == "1" and (r.get("content") or "").strip()]
    clean = [r for r in rows if (r.get("toxic") or "").strip() == "0" and (r.get("content") or "").strip()]

    out = []
    for label, pool, tag in ((1, toxic, "toxic"), (0, clean, "clean")):
        picks = _pick_with_keep(pool, TOXICN_PER_CLASS, 12, SEED)
        for i, r in enumerate(picks):
            out.append({
                "id": f"PUB_toxic_{i + 1:02d}" if label else f"PUB_clean_{i + 1:02d}",
                "tier": "public",
                "category": "公开数据集·辱骂仇恨" if label else "公开数据集·正常",
                # ToxiCN 是评论语料，没有标题；留空，让模型直接判断正文
                "title": "",
                "content": (r.get("content") or "").strip(),
                "expected_level": 2 if label else 0,
                "expected_rules": [],
                # 公开集只有 toxic 0/1，没有我们定义的四级标签 → 只参与二分类指标
                "binary_only": True,
                "source": "ToxiCN (ACL 2023, CC BY-NC-ND 4.0)",
                "note": "公开数据集样本；仅用于二分类阻断指标",
            })
    return out


def load_cold():
    """COLD（EMNLP 2022）冒犯/歧视二分类，作为 ToxiCN 之外的第二来源。"""
    if not os.path.exists(COLD_PATH):
        print("⚠️ 未找到 COLD，跳过该公开数据部分")
        return []
    with open(COLD_PATH, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.DictReader(f))
    def texts(label):
        out = []
        for r in rows:
            if (r.get("label") or "").strip() != str(label):
                continue
            t = (r.get("TEXT") or "").strip()
            if 5 <= len(t) <= 300:
                out.append({"content": t, "topic": (r.get("topic") or "").strip()})
        return out
    offensive, clean = texts(1), texts(0)
    out = []
    for label, pool, tag in ((1, offensive, "toxic"), (0, clean, "clean")):
        picks = _pick_with_keep(pool, COLD_PER_CLASS, 0, SEED + 1)
        for i, r in enumerate(picks):
            out.append({
                "id": f"PUB_cold_{tag}_{i + 1:02d}",
                "tier": "public",
                "category": "公开数据集·冒犯歧视" if label else "公开数据集·正常",
                "title": "",
                "content": r["content"],
                "expected_level": 2 if label else 0,
                "expected_rules": [],
                "binary_only": True,
                "source": "COLD (EMNLP 2022, Apache-2.0)",
                "note": "COLD 冒犯/歧视二分类样本；仅用于二分类阻断指标",
            })
    return out


def main():
    self_built = load_self_built()
    toxicn = load_toxicn()
    cold = load_cold()
    # 去重：同一句内容只保留第一次出现（ToxiCN 优先）
    seen = set()
    public = []
    for s in toxicn + cold:
        key = (s.get("content") or "").strip()
        if key in seen:
            continue
        seen.add(key)
        public.append(s)
    samples = self_built + public

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "由 build_eval_set.py 生成，请勿手工编辑；改自建样本请改 self_built.json",
            "stats": {
                "total": len(samples),
                "self_built": len(self_built),
                "public": len(public),
                "toxicn": len(toxicn),
                "cold": len(cold),
                "block": sum(1 for s in samples if s["expected_level"] >= 2),
                "pass": sum(1 for s in samples if s["expected_level"] < 2),
            },
            "samples": samples,
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 已生成 {OUT_PATH}")
    print(f"   合计 {len(samples)} 条：自建 {len(self_built)} + ToxiCN {len(toxicn)} + COLD {len(cold)}")
    print(f"   预期阻断 {sum(1 for s in samples if s['expected_level'] >= 2)} 条 / "
          f"放行 {sum(1 for s in samples if s['expected_level'] < 2)} 条")

    # 分层的样本数（这是"能不能拉开差距"的关键）
    from collections import Counter
    tiers = Counter(s["tier"] for s in samples)
    print("   分层：", dict(tiers))
    cats = Counter(s["category"] for s in samples)
    print("   类别：", dict(cats))

    lengths = sorted(len(s["content"]) for s in samples)
    print(f"   正文长度：最短 {lengths[0]} 字 / 中位 {lengths[len(lengths)//2]} 字 / 最长 {lengths[-1]} 字")


if __name__ == "__main__":
    main()
