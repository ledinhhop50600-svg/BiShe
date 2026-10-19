"""对比实验 v2：在统一评测集上比较四个方案。

样本来自 tools/eval_set/samples.json（由 build_eval_set.py 生成）：
  - 自建样本：按「区分度层级」设计（easy / trap / blind / pair / multi / long / clean）
  - 公开数据集 ToxiCN 抽样（辱骂/仇恨），只参与二分类指标（公开集没有四级标签）

四个方案：
  A 关键词规则      —— 敏感词库匹配（传统基线）
  B 纯大模型        —— 不提供任何规则
  C RAG + 大模型    —— 混合检索召回规则（当前实现）
  D 全量规则 + 大模型 —— 上界参照

指标（从粗到细，专门用来拉开差距）：
  1. 整体二分类（阻断 / 放行）准确率、精确率、召回率、F1
  2. **分层的准确率矩阵** —— 哪个方案在哪类样本上掉链子
  3. **四级精确匹配**（0/1/2/3 完全一致，仅自建样本）—— 区分"疑似 vs 违规"这类细微差别
  4. **规则召回**（是否引用了应命中的规则编号，仅自建违规样本）
  5. 违规片段有效率（片段是否为原文真实文字）
  6. 成本与耗时

用法：python tools/experiment_compare.py
前置：后端 8080、智能体 8001（真实模型）均在运行。
成本：52 条 × 3 个调用模型的方案 ≈ 156 次调用，约 1 元。
"""

import json
import os
import time
import urllib.error
import urllib.request
import uuid

JAVA = os.environ.get("ZIMEITI_BASE", "http://localhost:8080").rstrip("/")
AGENT = os.environ.get("ZIMEITI_AGENT", "http://localhost:8001").rstrip("/")

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_PATH = os.path.join(HERE, "eval_set", "samples.json")
REPORT = os.path.join(HERE, "..", "docs", "实验-对比实验-v2.md")

PRICE_INPUT_PER_M = 1.0
PRICE_OUTPUT_PER_M = 4.0

TIER_LABELS = {
    "easy": "易：明确的商业违规",
    "trap": "陷阱：含违禁词但语境合法",
    "blind": "盲区：无关键词但实际违规",
    "pair": "分级边界：个人分享 vs 商业推广",
    "multi": "多类/多违规混排",
    "long": "长文本（含千字级）",
    "clean": "正常内容",
    "public": "公开数据集（ToxiCN）",
}


# ======================================================================
# HTTP
# ======================================================================
def http_json(url, method="GET", body=None, headers=None, timeout=120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:300]}
    except Exception as e:
        return -1, {"error": f"{type(e).__name__}: {e}"}


def login(username, password="123456"):
    _, body = http_json(f"{JAVA}/api/auth/login", "POST", {"username": username, "password": password})
    return ((body or {}).get("data") or {}).get("tokenValue")


# ======================================================================
# 方案
# ======================================================================
def run_keyword(sample, words):
    text = f"{sample.get('title', '')}\n{sample.get('content', '')}"
    hits = [w for w in words if w["word"] in text]
    max_level = max([w["level"] for w in hits], default=0)
    return {
        "riskLevel": max_level if hits else 0,
        "fragments": [w["word"] for w in hits],
        "hit_rules": [],
        "promptTokens": 0,
        "completionTokens": 0,
        "durationMs": 0,
        "trace": f"命中 {len(hits)} 个词",
    }


def run_agent(sample, rules, platform, use_rag):
    req = {
        "requestId": str(uuid.uuid4()),
        "articleId": 0,
        "triggerType": "POST_AUDIT",
        "targetPlatformKey": "local",
        "title": sample.get("title", ""),
        "content": sample.get("content", ""),
        "platform": platform,
        "rules": rules,
        "useRag": use_rag,
    }
    t0 = time.time()
    status, body = http_json(f"{AGENT}/api/agent/audit", "POST", req)
    elapsed = int((time.time() - t0) * 1000)
    if status != 200:
        return {"error": f"HTTP {status}: {str(body)[:120]}", "durationMs": elapsed}

    usage = body.get("usage") or {}
    retrieve = next((t.get("output") for t in body.get("trace") or []
                     if t.get("action") in ("retrieve_rules", "retrieve_rules_failed")), "")
    return {
        "riskLevel": body.get("riskLevel"),
        "fragments": [v.get("fragment") for v in body.get("violations") or []],
        "hit_rules": [r.get("code") for r in body.get("hitRules") or []],
        "promptTokens": usage.get("promptTokens", 0),
        "completionTokens": usage.get("completionTokens", 0),
        "durationMs": body.get("durationMs", elapsed),
        "trace": retrieve,
    }


# ======================================================================
# 指标
# ======================================================================
def binary_metrics(rows):
    tp = fp = tn = fn = 0
    for r in rows:
        pred = (r["pred_level"] or 0) >= 2
        truth = r["expected_level"] >= 2
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
        elif not pred and not truth:
            tn += 1
        else:
            fn += 1
    total = tp + fp + tn + fn
    acc = (tp + tn) / total if total else 0
    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": total,
            "accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def exact_metrics(rows, samples_by_id):
    """四级精确匹配：只看非公开样本（公开集没有四级标签）。"""
    rows = [r for r in rows if not samples_by_id[r["id"]].get("binary_only")]
    if not rows:
        return None
    ok = sum(1 for r in rows if r["pred_level"] == samples_by_id[r["id"]]["expected_level"])
    return {"ok": ok, "n": len(rows), "rate": ok / len(rows)}


def rule_recall(rows, samples_by_id):
    """规则召回：应命中的规则里，被引用了多少（只统计期望规则非空的样本）。"""
    ratios = []
    for r in rows:
        expected = set(samples_by_id[r["id"]].get("expected_rules") or [])
        if not expected:
            continue
        cited = set(r.get("hit_rules") or [])
        ratios.append(len(expected & cited) / len(expected))
    if not ratios:
        return None
    return {"mean": sum(ratios) / len(ratios), "n": len(ratios)}


def fragment_validity(rows, samples_by_id):
    valid = total = 0
    for r in rows:
        s = samples_by_id[r["id"]]
        hay = (s.get("title") or "") + "\n" + (s.get("content") or "")
        for frag in r.get("fragments") or []:
            if not frag:
                continue
            total += 1
            if frag in hay:
                valid += 1
    return valid, total


# ======================================================================
# 主流程
# ======================================================================
def main():
    if not os.path.exists(SAMPLES_PATH):
        print("❌ 未找到评测集，请先运行 python tools/eval_set/build_eval_set.py")
        return 1
    with open(SAMPLES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    samples = data["samples"]
    samples_by_id = {s["id"]: s for s in samples}

    token = login("admin")   # 取敏感词库需要管理员权限
    if not token:
        print("❌ 登录失败")
        return 1
    headers = {"satoken": token}

    _, wb = http_json(f"{JAVA}/api/sensitive/page?pageNum=1&pageSize=300", headers=headers)
    words = ((wb or {}).get("data") or {}).get("records") or []
    if not words:
        print("❌ 敏感词库为空（或接口无权限），方案 A 无效")
        return 1

    _, rb = http_json(f"{JAVA}/api/rule/list", headers=headers)
    rules = [{
        "code": r.get("ruleCode"), "name": r.get("ruleName"), "category": r.get("category"),
        "content": r.get("ruleContent"), "source": r.get("source"),
        "suggestedLevel": r.get("suggestedLevel"),
    } for r in ((rb or {}).get("data") or [])]
    if not rules:
        print("❌ 规则库为空")
        return 1

    _, pb = http_json(f"{JAVA}/api/platform/list", headers=headers)
    local = next((p for p in ((pb or {}).get("data") or [])
                  if p.get("platformKey") == "local"), None) or {}
    platform = {
        "platformKey": "local", "platformName": "本平台",
        "titleMaxLen": local.get("titleMaxLen", 60),
        "contentMaxLen": local.get("contentMaxLen", 5000),
        "tagRule": local.get("tagRule"), "styleDesc": local.get("styleDesc"),
    }

    print(f"评测集：{len(samples)} 条（自建 {data['stats']['self_built']} + 公开 {data['stats']['public']}）"
          f" | 规则 {len(rules)} 条 | 敏感词 {len(words)} 个")

    schemes = [
        ("A 关键词规则", lambda s: run_keyword(s, words)),
        ("B 纯大模型", lambda s: run_agent(s, [], platform, False)),
        ("C RAG+大模型", lambda s: run_agent(s, rules, platform, True)),
        ("D 全量规则+大模型", lambda s: run_agent(s, rules, platform, False)),
    ]

    results = {}
    for name, fn in schemes:
        print(f"\n=== {name} ===")
        rows = []
        for s in samples:
            r = fn(s)
            rows.append({
                "id": s["id"], "tier": s["tier"], "expected_level": s["expected_level"],
                "pred_level": r.get("riskLevel"), "fragments": r.get("fragments") or [],
                "hit_rules": r.get("hit_rules") or [], "error": r.get("error"),
                "promptTokens": r.get("promptTokens", 0), "completionTokens": r.get("completionTokens", 0),
                "durationMs": r.get("durationMs", 0), "trace": r.get("trace", ""),
            })
            ok = "错误" if r.get("error") else (
                "✓" if ((r.get("riskLevel") or 0) >= 2) == (s["expected_level"] >= 2) else "✗")
            print(f"  {ok:3s} {s['id']:24s} 期望{s['expected_level']} 实际{r.get('riskLevel')} "
                  f"| {r.get('durationMs', 0)}ms")
        results[name] = rows

    # ---------------- 生成报告 ----------------
    lines = []
    lines.append("# 对比实验记录 v2（统一评测集）\n")
    lines.append(f"- 实验时间：{time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- 评测集：**{len(samples)} 条** = 自建 {data['stats']['self_built']} + 公开数据集 {data['stats']['public']}")
    tiers = {}
    for s in samples:
        tiers[s["tier"]] = tiers.get(s["tier"], 0) + 1
    lines.append("- 分层构成：" + "、".join(f"{TIER_LABELS.get(k, k)} {v} 条" for k, v in tiers.items()))
    lines.append(f"- 规则库 {len(rules)} 条 | 敏感词 {len(words)} 个 | 模型 deepseek-flash | 检索 bge-m3(top_k=6, 混合检索)")
    lines.append(f"- 计价：输入 {PRICE_INPUT_PER_M} 元/百万、输出 {PRICE_OUTPUT_PER_M} 元/百万（空闲时段）")
    lines.append("- 二分类口径：`riskLevel >= 2` 视为阻断；调用失败按「未阻断」计入（保守口径）\n")

    lines.append("## 一、总体结果（二分类）\n")
    lines.append("| 方案 | 准确率 | 精确率 | 召回率 | F1 | TP/FP/TN/FN | 错误 | 平均耗时 | 平均 token | 成本/条 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for name, _ in schemes:
        rows = results[name]
        m = binary_metrics(rows)
        errs = sum(1 for r in rows if r["error"])
        ok_rows = [r for r in rows if not r["error"]]
        avg_ms = sum(r["durationMs"] for r in ok_rows) // max(1, len(ok_rows))
        avg_tok = sum(r["promptTokens"] + r["completionTokens"] for r in rows) // max(1, len(rows))
        cost = sum(r["promptTokens"] * PRICE_INPUT_PER_M + r["completionTokens"] * PRICE_OUTPUT_PER_M
                   for r in rows) / max(1, len(rows)) / 1_000_000
        lines.append(f"| {name} | {m['accuracy']:.0%} | {m['precision']:.0%} | {m['recall']:.0%} | "
                     f"{m['f1']:.2f} | {m['tp']}/{m['fp']}/{m['tn']}/{m['fn']} | {errs} | {avg_ms}ms | {avg_tok} | {cost:.5f} 元 |")

    lines.append("\n## 二、分层准确率矩阵（关键：看方案在哪类样本上掉链子）\n")
    lines.append("| 层级 | " + " | ".join(n for n, _ in schemes) + " |")
    lines.append("|---|" + "---|" * len(schemes))
    for tier in ["easy", "trap", "blind", "pair", "multi", "long", "clean", "public"]:
        cells = []
        for name, _ in schemes:
            rows = [r for r in results[name] if r["tier"] == tier]
            if not rows:
                cells.append("-")
                continue
            okn = sum(1 for r in rows if not r["error"] and
                      ((r["pred_level"] or 0) >= 2) == (r["expected_level"] >= 2))
            cells.append(f"{okn}/{len(rows)}")
        lines.append(f"| {TIER_LABELS.get(tier, tier)} | " + " | ".join(cells) + " |")

    lines.append("\n## 三、四级精确匹配（仅自建样本）\n")
    lines.append("判定等级与期望等级完全一致（0/1/2/3），比只看「阻断与否」更严格 —— 可以区分「疑似」与「违规」的混淆。\n")
    lines.append("| 方案 | 完全一致 / 总数 | 一致率 |")
    lines.append("|---|---|---|")
    for name, _ in schemes:
        e = exact_metrics(results[name], samples_by_id)
        if e:
            lines.append(f"| {name} | {e['ok']}/{e['n']} | {e['rate']:.0%} |")

    lines.append("\n## 四、规则召回（仅自建、期望规则非空的样本）\n")
    lines.append("「应命中的规则」中被实际引用了多少 —— 检验判定依据是否完整，而不只是结论对不对。\n")
    lines.append("| 方案 | 规则召回率 | 样本数 |")
    lines.append("|---|---|---|")
    for name, _ in schemes:
        rr = rule_recall(results[name], samples_by_id)
        lines.append(f"| {name} | {rr['mean']:.0%} | {rr['n']} |" if rr else f"| {name} | - | - |")

    lines.append("\n## 五、违规片段有效率\n")
    lines.append("| 方案 | 有效片段 / 总片段 | 有效率 |")
    lines.append("|---|---|---|")
    for name, _ in schemes:
        valid, total = fragment_validity(results[name], samples_by_id)
        lines.append(f"| {name} | {valid}/{total} | {(valid / total):.0%} |" if total else f"| {name} | 0/0 | - |")

    lines.append("\n## 六、逐样本结果\n")
    lines.append("> 单元格含义：`✓等级` 正确、`✗等级` 错误、`错误` 调用失败。\n")
    lines.append("| 样本 | 层级 | 期望 | " + " | ".join(n.split(" ")[0] for n, _ in schemes) + " |")
    lines.append("|---|---|---|" + "---|" * len(schemes))
    for s in samples:
        cells = []
        for name, _ in schemes:
            row = next(r for r in results[name] if r["id"] == s["id"])
            if row["error"]:
                cells.append("错误")
            else:
                mark = "✓" if ((row["pred_level"] or 0) >= 2) == (s["expected_level"] >= 2) else "✗"
                cells.append(f"{mark}{row['pred_level']}")
        lines.append(f"| {s['id']} | {s['tier']} | {s['expected_level']} | " + " | ".join(cells) + " |")

    lines.append("\n## 七、检索明细（方案 C，仅自建违规样本）\n")
    lines.append("| 样本 | 召回轨迹 |")
    lines.append("|---|---|")
    for s in samples:
        if s.get("binary_only") or not (s.get("expected_rules") or []):
            continue
        row = next(r for r in results["C RAG+大模型"] if r["id"] == s["id"])
        lines.append(f"| {s['id']} | {(row['trace'] or '').replace('|', '/')} |")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n✅ 报告已写入 {os.path.abspath(REPORT)}")

    print("\n=== 汇总 ===")
    for name, _ in schemes:
        m = binary_metrics(results[name])
        print(f"{name:18s} 准确率={m['accuracy']:.0%} F1={m['f1']:.2f} "
              f"TP/FP/TN/FN={m['tp']}/{m['fp']}/{m['tn']}/{m['fn']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
