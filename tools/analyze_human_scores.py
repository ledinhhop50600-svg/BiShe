"""分析人工评分与 LLM 评分的一致性。

用法（项目根目录）：
    python tools/analyze_human_scores.py

输入：
    docs/eval/adaptation-results.json      适配评估结果（含 LLM 评分）
    docs/eval/adaptation-human-scores.csv  评分页面导出的 CSV

输出：
    docs/eval/adaptation-human-eval.md     人工评分结果与一致性报告
    同时把 human / humanSummary / consistency 写回 adaptation-results.json

指标：
  - 两项均值、平均绝对差（MAD）、完全一致条数；
  - Spearman 秩相关（手工实现，不依赖 scipy）；
  - 若某一侧方差为 0（例如人工全给 5 分），秩相关**无定义**，如实返回 None。
"""
import csv
import json
import os
import sys
from statistics import mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "docs", "eval", "adaptation-results.json")
HUMAN_CSV = os.path.join(ROOT, "docs", "eval", "adaptation-human-scores.csv")
OUT_MD = os.path.join(ROOT, "docs", "eval", "adaptation-human-eval.md")

NAME_TO_KEY = {"小红书": "xiaohongshu", "微信公众号": "wechat", "抖音": "douyin",
               "微博": "weibo", "B站": "bilibili"}
DIMS = [("style", "风格符合度", "风格_人工(1-5)"),
        ("retention", "信息保留度", "保留_人工(1-5)"),
        ("readability", "可读性", "可读_人工(1-5)")]


def ranks(values):
    """平均秩（处理并列），用于 Spearman。"""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(xs, ys):
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None  # 某一侧无方差，秩相关无定义
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def main():
    if not os.path.exists(RESULTS):
        print("[FAIL] 找不到 adaptation-results.json")
        return 1
    if not os.path.exists(HUMAN_CSV):
        print(f"[FAIL] 找不到 {HUMAN_CSV}")
        print("请先在 docs/eval/adaptation-review.html 里评分并导出 CSV，放到 docs/eval/。")
        return 1

    data = json.load(open(RESULTS, encoding="utf-8"))
    rows = data.get("results") or []

    human = {}
    for row in csv.DictReader(open(HUMAN_CSV, encoding="utf-8-sig")):
        key = (int(row["稿件ID"]), NAME_TO_KEY.get(row["目标平台"], row["目标平台"]))
        human[key] = {
            "style": int(row["风格_人工(1-5)"]),
            "retention": int(row["保留_人工(1-5)"]),
            "readability": int(row["可读_人工(1-5)"]),
            "comment": (row.get("人工点评") or "").strip(),
        }

    joined = []
    for r in rows:
        if "error" in r:
            continue
        key = (r["articleId"], r["platformKey"])
        if key not in human:
            continue
        r["human"] = human[key]
        joined.append(r)

    if not joined:
        print("[FAIL] 结果与人工评分没有匹配上（检查稿件 id / 平台名）")
        return 1

    summary = {"filled": len(joined), "total": len([r for r in rows if "error" not in r]),
               "dims": {}}
    lines = ["# 人工评分与 LLM 一致性\n"]
    lines.append(f"- 人工评分条数：{len(joined)} / {summary['total']}（来自 `adaptation-human-scores.csv`）")
    lines.append(f"- LLM 模型：{data.get('model')}　批次：`{data.get('runId')}`\n")
    lines.append("## 一、逐项对比\n")
    lines.append("| 维度 | 人工均分 | LLM 均分 | 平均绝对差 | 完全一致 | Spearman |")
    lines.append("|---|---|---|---|---|---|")

    for dim, label, _ in DIMS:
        hs = [r["human"][dim] for r in joined]
        ls = [r["llm"][dim] for r in joined if isinstance(r.get("llm"), dict)
              and isinstance(r["llm"].get(dim), int)]
        if not ls:
            continue
        mad = round(mean(abs(a - b) for a, b in zip(hs, ls)), 2)
        exact = sum(1 for a, b in zip(hs, ls) if a == b)
        rho = spearman(hs, ls)
        summary["dims"][dim] = {
            "humanMean": round(mean(hs), 2),
            "llmMean": round(mean(ls), 2),
            "mad": mad,
            "exact": exact,
            "n": len(hs),
            "humanStd": round((sum((x - mean(hs)) ** 2 for x in hs) / len(hs)) ** 0.5, 3),
            "spearman": rho,
        }
        rho_text = "无定义" if rho is None else f"{rho:.3f}"
        lines.append(f"| {label} | {mean(hs):.2f} | {mean(ls):.2f} | {mad:.2f} | "
                     f"{exact}/{len(hs)} | {rho_text} |")

    summary["filled"] = len(joined)
    data["humanSummary"] = summary["dims"]
    data["consistency"] = summary
    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    lines.append("\n## 二、怎么读这些数字\n")
    lines.append("- **平均绝对差（MAD）**：人工与 LLM 分数差多少，越小越接近；它不是相关系数。")
    lines.append("- **完全一致**：两边分数完全相同的条数。")
    lines.append("- **Spearman**：排序一致性；某一侧所有分数相同（方差为 0）时**无定义**，不能强行算。")
    some_zero = any(v["humanStd"] == 0 for v in summary["dims"].values())
    if some_zero:
        lines.append("\n> 本次人工评分存在全员同分（标准差为 0），因此 Spearman 无法计算。"
                     "这只能说明“人工认为这些结果都达到了可发布水平”，"
                     "不能用来验证 LLM 是否能区分优劣。若论文需要秩相关，"
                     "需要至少若干条低于 5 分的评分。")
    else:
        lines.append("\n> 样本量只有 12，秩相关波动大，论文中应说明仅作方向性参考。")

    lines.append("\n## 三、局限\n")
    lines.append("1. 人工评分只有 1 人，且没有独立的第二评分者；")
    lines.append("2. 样本量 12 条，统计显著性有限；")
    lines.append("3. LLM 评委偏宽松（分数集中在 4-5），人工评分若也集中，区分度不足；")
    lines.append("4. 评分为整体印象，未做逐句对齐。\n")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"已分析 {len(joined)} 条，写入 {os.path.relpath(OUT_MD, ROOT)}")
    for dim, label, _ in DIMS:
        s = summary["dims"].get(dim)
        if s:
            rho = "无定义" if s["spearman"] is None else s["spearman"]
            print(f"  {label}: 人工 {s['humanMean']:.2f} / LLM {s['llmMean']:.2f} / "
                  f"MAD {s['mad']:.2f} / 完全一致 {s['exact']}/{s['n']} / Spearman {rho}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
