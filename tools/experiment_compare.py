"""对比实验 v3：多轮运行 + 关键词定位实验组。

与 v2 的区别：
- `--rounds N`：同一配置跑 N 轮，报告均值 ± 标准差（单轮结果会被波动带偏）
- `--localize`：额外加一组「关键词定位」实验（E），验证"只把命中关键词的段落送模型"能否降本
- `--out PATH`：报告输出路径（用于不同模型 / 不同配置分别出报告）

四个基础方案：
  A 关键词规则 / B 纯大模型 / C RAG+大模型 / D 全量规则+大模型

用法：
    python tools/experiment_compare.py --rounds 3
    python tools/experiment_compare.py --localize --rounds 1 --out docs/实验-定位消融.md
    ZIMEITI_AGENT=http://localhost:8011 python tools/experiment_compare.py --rounds 1 --out docs/实验-模型对比-pro.md
"""

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.request
import uuid

JAVA = os.environ.get("ZIMEITI_BASE", "http://localhost:8080").rstrip("/")
AGENT = os.environ.get("ZIMEITI_AGENT", "http://localhost:8001").rstrip("/")

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_PATH = os.path.join(HERE, "eval_set", "samples.json")

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


def run_keyword(sample, words):
    text = f"{sample.get('title', '')}\n{sample.get('content', '')}"
    hits = [w for w in words if w["word"] in text]
    max_level = max([w["level"] for w in hits], default=0)
    return {"riskLevel": max_level if hits else 0, "fragments": [w["word"] for w in hits],
            "hit_rules": [], "promptTokens": 0, "completionTokens": 0, "durationMs": 0,
            "trace": f"命中 {len(hits)} 个词"}


def run_agent(sample, rules, platform, use_rag, localize=False, words=None):
    req = {
        "requestId": str(uuid.uuid4()), "articleId": 0, "triggerType": "POST_AUDIT",
        "targetPlatformKey": "local",
        "title": sample.get("title", ""), "content": sample.get("content", ""),
        "platform": platform, "rules": rules, "useRag": use_rag,
        # 敏感词库随请求下发（真实系统也这么做），作为词面关键词来源
        "sensitiveWords": [{"word": w["word"], "level": w.get("level"), "category": w.get("category")}
                           for w in (words or [])],
    }
    if localize:
        req["localize"] = True
    t0 = time.time()
    status, body = http_json(f"{AGENT}/api/agent/audit", "POST", req)
    elapsed = int((time.time() - t0) * 1000)
    if status != 200:
        return {"error": f"HTTP {status}: {str(body)[:120]}", "durationMs": elapsed}
    usage = body.get("usage") or {}
    trace_txt = " / ".join(t.get("output", "") for t in (body.get("trace") or [])
                           if t.get("action") in ("retrieve_rules", "localize"))
    return {
        "riskLevel": body.get("riskLevel"),
        "fragments": [v.get("fragment") for v in body.get("violations") or []],
        "hit_rules": [r.get("code") for r in body.get("hitRules") or []],
        "promptTokens": usage.get("promptTokens", 0),
        "completionTokens": usage.get("completionTokens", 0),
        "durationMs": body.get("durationMs", elapsed),
        "trace": trace_txt,
    }


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
    n = tp + fp + tn + fn
    acc = (tp + tn) / n if n else 0
    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": n,
            "accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def exact_rate(rows, samples_by_id):
    rows = [r for r in rows if not samples_by_id[r["id"]].get("binary_only")]
    if not rows:
        return None
    return sum(1 for r in rows if r["pred_level"] == samples_by_id[r["id"]]["expected_level"]) / len(rows)


def rule_recall(rows, samples_by_id):
    ratios = []
    for r in rows:
        expected = set(samples_by_id[r["id"]].get("expected_rules") or [])
        if not expected:
            continue
        ratios.append(len(expected & set(r.get("hit_rules") or [])) / len(expected))
    return sum(ratios) / len(ratios) if ratios else None


def fragment_validity(rows, samples_by_id):
    valid = total = 0
    for r in rows:
        s = samples_by_id[r["id"]]
        hay = (s.get("title") or "") + "\n" + (s.get("content") or "")
        for frag in r.get("fragments") or []:
            if frag:
                total += 1
                valid += 1 if frag in hay else 0
    return valid, total


def mean_std(vals):
    if not vals:
        return 0.0, 0.0
    m = sum(vals) / len(vals)
    if len(vals) == 1:
        return m, 0.0
    var = sum((v - m) ** 2 for v in vals) / len(vals)
    return m, math.sqrt(var)


def tier_accuracy(rows, tier):
    sub = [r for r in rows if r["tier"] == tier]
    if not sub:
        return None
    ok = sum(1 for r in sub if not r["error"] and
             ((r["pred_level"] or 0) >= 2) == (r["expected_level"] >= 2))
    return ok / len(sub)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--out", default=os.path.join(HERE, "..", "docs", "实验-对比实验-v3.md"))
    parser.add_argument("--title", default="对比实验记录", help="报告标题")
    parser.add_argument("--localize", action="store_true")
    parser.add_argument("--min-len", type=int, default=0,
                        help="只跑正文长度 >= 该值的样本（定位实验只关心长文）")
    args = parser.parse_args()
    rounds = max(1, args.rounds)

    with open(SAMPLES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    samples = [s for s in data["samples"] if len(s.get("content") or "") >= args.min_len]
    samples_by_id = {s["id"]: s for s in samples}

    token = login("admin")
    if not token:
        print("❌ 登录失败")
        return 1
    headers = {"satoken": token}
    _, wb = http_json(f"{JAVA}/api/sensitive/page?pageNum=1&pageSize=300", headers=headers)
    words = ((wb or {}).get("data") or {}).get("records") or []
    _, rb = http_json(f"{JAVA}/api/rule/list", headers=headers)
    raw_rules = (rb or {}).get("data") or []
    _, pb0 = http_json(f"{JAVA}/api/platform/list", headers=headers)
    local0 = next((p for p in ((pb0 or {}).get("data") or []) if p.get("platformKey") == "local"), None) or {}
    local_id = local0.get("id")
    # 只取"通用规则 + 本平台专属规则"，与主系统实际下发的一致
    # （不做过滤的话会把小红书/微博的专属规则也发过去，等于让模型按别的平台标准判）
    rules = [{"code": r.get("ruleCode"), "name": r.get("ruleName"), "category": r.get("category"),
              "content": r.get("ruleContent"), "source": r.get("source"),
              "suggestedLevel": r.get("suggestedLevel")}
             for r in raw_rules
             if r.get("platformId") is None or r.get("platformId") == local_id]
    if not words or not rules:
        print("❌ 敏感词或规则为空")
        return 1
    _, pb = http_json(f"{JAVA}/api/platform/list", headers=headers)
    local = next((p for p in ((pb or {}).get("data") or []) if p.get("platformKey") == "local"), None) or {}
    platform = {"platformKey": "local", "platformName": "本平台",
                "titleMaxLen": local.get("titleMaxLen", 60),
                "contentMaxLen": local.get("contentMaxLen", 5000),
                "tagRule": local.get("tagRule"), "styleDesc": local.get("styleDesc")}

    schemes = [
        ("A 关键词规则", lambda s: run_keyword(s, words)),
        ("B 纯大模型", lambda s: run_agent(s, [], platform, False, words=words)),
        ("C RAG+大模型", lambda s: run_agent(s, rules, platform, True, words=words)),
        ("D 全量规则+大模型", lambda s: run_agent(s, rules, platform, False, words=words)),
    ]
    if args.localize:
        schemes.append(("E RAG+关键词定位",
                        lambda s: run_agent(s, rules, platform, True, localize=True, words=words)))

    print(f"评测集 {len(samples)} 条 | 规则 {len(rules)} | 敏感词 {len(words)} | "
          f"轮数 {rounds} | 方案 {len(schemes)} | Agent={AGENT}")

    all_rounds = {name: [] for name, _ in schemes}
    for rnd in range(1, rounds + 1):
        print(f"\n########## 第 {rnd}/{rounds} 轮 ##########")
        for name, fn in schemes:
            print(f"--- {name} ---")
            rows = []
            for s in samples:
                r = fn(s)
                rows.append({"id": s["id"], "tier": s["tier"],
                             "expected_level": s["expected_level"],
                             "pred_level": r.get("riskLevel"), "fragments": r.get("fragments") or [],
                             "hit_rules": r.get("hit_rules") or [], "error": r.get("error"),
                             "promptTokens": r.get("promptTokens", 0),
                             "completionTokens": r.get("completionTokens", 0),
                             "durationMs": r.get("durationMs", 0), "trace": r.get("trace", "")})
            all_rounds[name].append(rows)
            m = binary_metrics(rows)
            print(f"    准确率={m['accuracy']:.0%} F1={m['f1']:.2f} "
                  f"TP/FP/TN/FN={m['tp']}/{m['fp']}/{m['tn']}/{m['fn']}")

    # ---------------- 报告 ----------------
    L = []
    L.append(f"# {args.title}\n")
    L.append(f"- 实验时间：{time.strftime('%Y-%m-%d %H:%M')}")
    L.append(f"- 评测集：{len(samples)} 条（自建 {data['stats']['self_built']} + 公开 {data['stats']['public']}）")
    L.append(f"- Agent：{AGENT} | 规则 {len(rules)} 条 | 敏感词 {len(words)} 个 | 轮数 {rounds}")
    L.append("- 模型 deepseek-flash（思考模式关闭）| 检索 bge-m3 top_k=6（元规则固定带上）")
    L.append(f"- 计价：输入 {PRICE_INPUT_PER_M} 元/百万、输出 {PRICE_OUTPUT_PER_M} 元/百万（空闲时段）")
    L.append("- 二分类口径：`riskLevel >= 2` 视为阻断；调用失败按未阻断计入（保守口径）\n")

    L.append(f"## 一、总体结果（{rounds} 轮均值 ± 标准差）\n")
    L.append("| 方案 | 准确率 | F1 | 平均 token | 成本/条 | 平均耗时 | 错误数 |")
    L.append("|---|---|---|---|---|---|---|")
    for name, _ in schemes:
        accs, f1s, toks, costs, durs, errs = [], [], [], [], [], []
        for rows in all_rounds[name]:
            m = binary_metrics(rows)
            accs.append(m["accuracy"])
            f1s.append(m["f1"])
            toks.append(sum(r["promptTokens"] + r["completionTokens"] for r in rows) / len(rows))
            costs.append(sum(r["promptTokens"] * PRICE_INPUT_PER_M + r["completionTokens"] * PRICE_OUTPUT_PER_M
                             for r in rows) / len(rows) / 1_000_000)
            durs.append(sum(r["durationMs"] for r in rows if not r["error"]) /
                        max(1, sum(1 for r in rows if not r["error"])))
            errs.append(sum(1 for r in rows if r["error"]))
        am, asd = mean_std(accs)
        fm, fsd = mean_std(f1s)
        tm, _ = mean_std(toks)
        cm, _ = mean_std(costs)
        dm, _ = mean_std(durs)
        if rounds > 1:
            L.append(f"| {name} | {am:.0%} ± {asd:.1%} | {fm:.2f} ± {fsd:.2f} | {tm:.0f} | "
                     f"{cm:.5f} 元 | {dm:.0f}ms | {max(errs)} |")
        else:
            L.append(f"| {name} | {am:.0%} | {fm:.2f} | {tm:.0f} | {cm:.5f} 元 | {dm:.0f}ms | {max(errs)} |")

    L.append("\n## 二、分层准确率（各轮均值）\n")
    L.append("| 层级 | " + " | ".join(n.split(" ")[0] for n, _ in schemes) + " |")
    L.append("|---|" + "---|" * len(schemes))
    for tier in ["easy", "trap", "blind", "pair", "multi", "long", "clean", "public"]:
        cells = []
        for name, _ in schemes:
            vals = [tier_accuracy(rows, tier) for rows in all_rounds[name]]
            vals = [v for v in vals if v is not None]
            cells.append(f"{sum(vals) / len(vals):.0%}" if vals else "-")
        L.append(f"| {TIER_LABELS.get(tier, tier)} | " + " | ".join(cells) + " |")

    last = {name: rows[-1] for name, rows in all_rounds.items()}

    L.append("\n## 三、四级精确匹配（最后一轮，仅自建样本）\n")
    L.append("| 方案 | 一致率 |")
    L.append("|---|---|")
    for name, _ in schemes:
        e = exact_rate(last[name], samples_by_id)
        L.append(f"| {name} | {e:.0%} |" if e is not None else f"| {name} | - |")

    L.append("\n## 四、规则召回（最后一轮，仅自建、期望规则非空）\n")
    L.append("| 方案 | 召回率 |")
    L.append("|---|---|")
    for name, _ in schemes:
        rr = rule_recall(last[name], samples_by_id)
        L.append(f"| {name} | {rr:.0%} |" if rr is not None else f"| {name} | - |")

    L.append("\n## 五、违规片段有效率（最后一轮）\n")
    L.append("| 方案 | 有效/总数 | 有效率 |")
    L.append("|---|---|---|")
    for name, _ in schemes:
        v, t = fragment_validity(last[name], samples_by_id)
        L.append(f"| {name} | {v}/{t} | {(v / t):.0%} |" if t else f"| {name} | 0/0 | - |")

    L.append("\n## 六、逐样本结果（最后一轮）\n")
    L.append("> `✓等级` 判定正确，`✗等级` 判定错误，`错误` 调用失败。\n")
    L.append("| 样本 | 层级 | 期望 | " + " | ".join(n.split(" ")[0] for n, _ in schemes) + " |")
    L.append("|---|---|---|" + "---|" * len(schemes))
    for s in samples:
        cells = []
        for name, _ in schemes:
            row = next(r for r in last[name] if r["id"] == s["id"])
            if row["error"]:
                cells.append("错误")
            else:
                mark = "✓" if ((row["pred_level"] or 0) >= 2) == (s["expected_level"] >= 2) else "✗"
                cells.append(f"{mark}{row['pred_level']}")
        L.append(f"| {s['id']} | {s['tier']} | {s['expected_level']} | " + " | ".join(cells) + " |")

    if args.localize:
        L.append("\n## 七、关键词定位效果（E vs C）\n")
        L.append("E 方案 = 检索 + 关键词定位：先把长文聚焦到命中规则示例词的段落（含前后各一段），再送给模型；\n"
                 "一段都没命中时自动回退全文。用来验证「先定位再判断」能否降本、代价是什么。\n")
        L.append("| 样本 | 定位说明（E） | C 等级 | E 等级 |")
        L.append("|---|---|---|---|")
        for s in samples:
            if len(s.get("content") or "") < 300:
                continue
            e_row = next(r for r in last["E RAG+关键词定位"] if r["id"] == s["id"])
            c_row = next(r for r in last["C RAG+大模型"] if r["id"] == s["id"])
            loc = next((t for t in (e_row["trace"] or "").split(" / ") if t.startswith("分 ")), "")
            L.append(f"| {s['id']} | {loc} | {c_row['pred_level']} | {e_row['pred_level']} |")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"\n✅ 报告：{os.path.abspath(args.out)}")

    print("\n=== 汇总 ===")
    for name, _ in schemes:
        accs = [binary_metrics(rows)["accuracy"] for rows in all_rounds[name]]
        f1s = [binary_metrics(rows)["f1"] for rows in all_rounds[name]]
        am, asd = mean_std(accs)
        fm, fsd = mean_std(f1s)
        print(f"{name:22s} 准确率 {am:.0%} ± {asd:.1%} | F1 {fm:.2f} ± {fsd:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
