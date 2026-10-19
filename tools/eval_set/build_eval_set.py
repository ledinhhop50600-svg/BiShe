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
OUT_PATH = os.path.join(HERE, "samples.json")

PUBLIC_PER_CLASS = 12   # toxic / non-toxic 各抽多少条
SEED = 42               # 固定随机种子，保证抽样可复现


def load_self_built():
    with open(SELF_PATH, encoding="utf-8") as f:
        data = json.load(f)
    samples = data["samples"]
    for s in samples:
        s.setdefault("source", "自建")
        s["binary_only"] = False
    return samples


def load_toxicn():
    if not os.path.exists(TOXICN_PATH):
        print("⚠️ 未找到 ToxiCN，跳过公开数据集部分")
        return []

    with open(TOXICN_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        # 第一列表头带 BOM，统一清理
        rows = [{ (k or "").lstrip("\ufeff"): v for k, v in r.items() } for r in reader]

    toxic = [r for r in rows if (r.get("toxic") or "").strip() == "1" and (r.get("content") or "").strip()]
    clean = [r for r in rows if (r.get("toxic") or "").strip() == "0" and (r.get("content") or "").strip()]

    rnd = random.Random(SEED)
    out = []
    for label, pool, tag in ((1, toxic, "toxic"), (0, clean, "clean")):
        picks = rnd.sample(pool, min(PUBLIC_PER_CLASS, len(pool)))
        for i, r in enumerate(picks):
            out.append({
                "id": f"PUB_{tag}_{i + 1:02d}",
                "tier": "public",
                "category": "公开数据集·辱骂仇恨" if label else "公开数据集·正常",
                # ToxiCN 是评论语料，没有标题；留空，让模型直接判断正文
                "title": "",
                "content": (r.get("content") or "").strip(),
                "expected_level": 2 if label else 0,
                "expected_rules": ["VL-002"] if label else [],
                # 公开集只有 toxic 0/1，没有我们定义的四级标签 → 只参与二分类指标
                "binary_only": True,
                "source": "ToxiCN (ACL 2023, CC BY-NC-ND 4.0)",
                "note": "公开数据集样本；仅用于二分类阻断指标",
            })
    return out


def main():
    self_built = load_self_built()
    public = load_toxicn()
    samples = self_built + public

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "由 build_eval_set.py 生成，请勿手工编辑；改自建样本请改 self_built.json",
            "stats": {
                "total": len(samples),
                "self_built": len(self_built),
                "public": len(public),
                "block": sum(1 for s in samples if s["expected_level"] >= 2),
                "pass": sum(1 for s in samples if s["expected_level"] < 2),
            },
            "samples": samples,
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 已生成 {OUT_PATH}")
    print(f"   合计 {len(samples)} 条：自建 {len(self_built)} + 公开 {len(public)}")
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
