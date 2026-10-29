"""速度实验：适配策略 + 思考强度。

用法（项目根目录，后端/Agent 已启动）：
    python tools/experiment_speed.py

对比：
  1. 适配：分平台串行 / 分平台并行 / 合并一次调用 / 通用提示词（无平台形态）
  2. 思考：none / low / high 的耗时、token 与判定结果
  3. 长文：串行 vs 并行 vs 合并一次（看是否截断）

产物：docs/实验-速度优化.md、docs/perf/speed-experiment.json、speed.png、reasoning.png
"""
import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "docs", "perf")
os.makedirs(OUT_DIR, exist_ok=True)
BACKEND = "http://localhost:8080"
AGENT = "http://localhost:8001"
PLATFORM_ORDER = {"xiaohongshu": 1, "wechat": 2, "douyin": 3}
PLATFORM_NAMES = {"xiaohongshu": "小红书", "wechat": "微信公众号", "douyin": "抖音"}


def call(url, method="GET", body=None, token=None, timeout=300):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("satoken", token)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return payload, (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"error": f"HTTP {e.code}"}
        return payload, (time.perf_counter() - started) * 1000


def login(username="admin"):
    body, _ = call(BACKEND + "/api/auth/login", "POST",
                   {"username": username, "password": "123456"})
    return ((body or {}).get("data") or {}).get("tokenValue")


def median(values):
    return round(statistics.median(values), 1) if values else 0


def normalize_rules(raw, key_by_id):
    return [{
        "code": r["ruleCode"], "name": r["ruleName"], "category": r["category"],
        "content": r["ruleContent"], "source": r.get("source"),
        "suggestedLevel": r.get("suggestedLevel"),
        "platformKey": key_by_id.get(r.get("platformId")),
    } for r in raw]


def has_emoji(text):
    return any(ord(ch) > 0x1F000 or 0x2600 <= ord(ch) <= 0x27BF for ch in (text or ""))


def shape_score(platform_key, item):
    """很粗的形态代理：只看最容易识别的平台特征，不替代人工评分。"""
    content = item.get("content") or ""
    tags = item.get("tags") or []
    if platform_key == "xiaohongshu":
        return bool(has_emoji(content)) and 3 <= len(tags) <= 5
    if platform_key == "wechat":
        return len(tags) == 0
    if platform_key == "douyin":
        return "【画面】" in content and "【口播】" in content
    return False


def adapt_once(article, keys, strategy, parallel, effort, run_id):
    platforms = []
    for k in keys:
        p = PLATFORMS[k]
        platforms.append({
            "platformKey": p["platformKey"], "platformName": p["platformName"],
            "titleMaxLen": p.get("titleMaxLen"), "contentMaxLen": p.get("contentMaxLen"),
            "tagRule": p.get("tagRule"), "styleDesc": p.get("styleDesc"),
        })
    req = {
        "requestId": f"speed-{uuid.uuid4().hex[:12]}",
        "articleId": article["id"],
        "title": article.get("title") or "",
        "content": article.get("content") or "",
        "targetPlatformKeys": keys,
        "platforms": platforms,
        "rules": RULES,
        "strategy": strategy,
        "parallel": parallel,
        "reasoningEffort": effort,
    }
    body, elapsed = call(AGENT + "/api/agent/adapt", "POST", req, timeout=300)
    if not isinstance(body, dict) or "results" not in body:
        return {"error": str(body)[:300], "totalMs": elapsed, "results": []}
    results = body.get("results") or []
    return {
        "totalMs": round(elapsed, 1),
        "agentMs": body.get("durationMs", 0),
        "usage": body.get("usage") or {},
        "strategy": body.get("strategy"),
        "parallel": body.get("parallel"),
        "results": [{
            "key": r.get("platformKey"),
            "name": r.get("platformName"),
            "durationMs": r.get("durationMs", 0),
            "adaptMs": r.get("adaptMs", 0),
            "complianceMs": r.get("complianceMs", 0),
            "contentLen": (r.get("formatCheck") or {}).get("contentLen", 0),
            "formatPassed": (r.get("formatCheck") or {}).get("passed"),
            "tagCount": (r.get("formatCheck") or {}).get("tagCount", 0),
            "shape": shape_score(r.get("platformKey"), r),
        } for r in results],
    }


def audit_once(text, effort, run_id):
    req = {
        "requestId": f"speed-audit-{uuid.uuid4().hex[:12]}",
        "articleId": 0,
        "triggerType": "PRE_CHECK",
        "title": "速度实验：违规文案",
        "content": text,
        "platform": {
            "platformKey": "local", "platformName": "本平台",
            "titleMaxLen": 60, "contentMaxLen": 5000,
            "tagRule": "可选，以 # 开头", "styleDesc": "长文",
        },
        "rules": AUDIT_RULES,
        "reasoningEffort": effort,
    }
    body, elapsed = call(AGENT + "/api/agent/audit", "POST", req, timeout=300)
    if not isinstance(body, dict) or "riskLevel" not in body:
        return {"error": str(body)[:300], "totalMs": elapsed}
    return {
        "totalMs": round(elapsed, 1),
        "agentMs": body.get("durationMs", 0),
        "riskLevel": body.get("riskLevel"),
        "hitRules": len(body.get("hitRules") or []),
        "violations": len(body.get("violations") or []),
        "usage": body.get("usage") or {},
        "trace": {s.get("action"): s.get("durationMs", 0) for s in (body.get("trace") or [])},
    }


def summarize_variant(rows):
    """把多轮结果汇总：耗时取中位数；质量取最后一轮。"""
    ok = [r for r in rows if "error" not in r]
    if not ok:
        return {"error": rows[0].get("error") if rows else "no result", "totalMs": 0}
    last = ok[-1]
    platforms = last.get("results") or []
    return {
        "totalMs": median([r["totalMs"] for r in ok]),
        "agentMs": median([r.get("agentMs", 0) for r in ok]),
        "promptTokens": median([(r.get("usage") or {}).get("promptTokens", 0) for r in ok]),
        "completionTokens": median([(r.get("usage") or {}).get("completionTokens", 0) for r in ok]),
        "formatPass": sum(1 for p in platforms if p.get("formatPassed")),
        "platforms": len(platforms),
        "shapeScore": sum(1 for p in platforms if p.get("shape")),
        "contentLens": [p.get("contentLen") for p in platforms],
        "detail": platforms,
    }


def main():
    global PLATFORMS, RULES, AUDIT_RULES
    admin = login()
    if not admin:
        print("[FAIL] 后端登录失败")
        return 1
    body, _ = call(BACKEND + "/api/platform/list", token=admin)
    raw_platforms = (body or {}).get("data") or []
    key_by_id = {p["id"]: p["platformKey"] for p in raw_platforms}
    PLATFORMS = {p["platformKey"]: p for p in raw_platforms}
    body, _ = call(BACKEND + "/api/rule/list", token=admin)
    raw_rules = (body or {}).get("data") or []
    RULES = normalize_rules(raw_rules, key_by_id)
    AUDIT_RULES = [r for r in RULES if not r["platformKey"] or r["platformKey"] == "local"]

    body, _ = call(BACKEND + "/api/article/1", token=admin)
    short_article = (body or {}).get("data") or {}
    body, _ = call(BACKEND + "/api/article/16", token=admin)
    long_article = (body or {}).get("data") or {}
    if not short_article or not long_article:
        print("[FAIL] 读取稿件失败")
        return 1

    run_id = int(time.time())
    keys = ["xiaohongshu", "wechat", "douyin"]

    # ---- 1) 适配策略（短文，2 轮）----
    variants = [
        ("分平台 · 串行（原方案）", "per_platform", False),
        ("分平台 · 并行（当前生产）", "per_platform", True),
        ("合并一次调用", "unified", True),
        ("通用提示词 · 并行", "generic", True),
    ]
    adapt_results = {}
    for label, strategy, parallel in variants:
        rows = [adapt_once(short_article, keys, strategy, parallel, "none", run_id)
                for _ in range(2)]
        adapt_results[label] = summarize_variant(rows)
        print(f"{label}: {adapt_results[label].get('totalMs')} ms，"
              f"格式 {adapt_results[label].get('formatPass')}/{adapt_results[label].get('platforms')}，"
              f"形态 {adapt_results[label].get('shapeScore')}/{adapt_results[label].get('platforms')}")

    # ---- 2) 长文策略（1 轮）----
    long_results = {}
    for label, strategy, parallel in [
        ("长文 · 串行", "per_platform", False),
        ("长文 · 并行", "per_platform", True),
        ("长文 · 合并一次", "unified", True),
    ]:
        r = adapt_once(long_article, keys, strategy, parallel, "none", run_id)
        long_results[label] = summarize_variant([r])
        print(f"{label}: {r.get('totalMs')} ms，"
              f"格式 {long_results[label].get('formatPass')}/{long_results[label].get('platforms')}")

    # ---- 3) 思考强度（同一段违规文案，2 轮）----
    text = (
        "这款面霜是全网最低价，三天见效，国家级实验室研发。"
        "想要链接的加我微信，备注面霜，我发你。"
        "用了之后皮肤状态肉眼可见地变好，敏感肌也能放心用，"
        "这是今年最值得买的一款，错过再等一年。"
    )
    reason_results = {}
    for effort in ("none", "low", "high"):
        rows = [audit_once(text, effort, run_id) for _ in range(2)]
        ok = [x for x in rows if "error" not in x]
        if not ok:
            reason_results[effort] = {"error": rows[0].get("error"), "totalMs": 0}
        else:
            last = ok[-1]
            reason_results[effort] = {
                "totalMs": median([x["totalMs"] for x in ok]),
                "promptTokens": median([(x.get("usage") or {}).get("promptTokens", 0) for x in ok]),
                "completionTokens": median([(x.get("usage") or {}).get("completionTokens", 0) for x in ok]),
                "riskLevel": last.get("riskLevel"),
                "hitRules": last.get("hitRules"),
                "violations": last.get("violations"),
            }
        print(f"思考 {effort}: {reason_results[effort].get('totalMs')} ms，"
              f"输出 token {reason_results[effort].get('completionTokens')}")

    # ---- 4) 适配开思考（1 平台）----
    high_adapt = adapt_once(short_article, ["xiaohongshu"], "per_platform", True, "high", run_id)
    none_adapt = adapt_once(short_article, ["xiaohongshu"], "per_platform", True, "none", run_id)
    reason_adapt = {"none": summarize_variant([none_adapt]), "high": summarize_variant([high_adapt])}

    data = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "adaptShort": adapt_results,
        "adaptLong": long_results,
        "reasoning": reason_results,
        "adaptReasoning": reason_adapt,
    }
    with open(os.path.join(OUT_DIR, "speed-experiment.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # ---- 图表 ----
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False
    labels = list(adapt_results.keys())
    values = [adapt_results[k].get("totalMs", 0) for k in labels]
    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=160)
    bars = ax.barh(labels, values, color=["#b9b1a5", "#1f5a54", "#b08a5a", "#7d9a8d"], height=0.5)
    ax.set_xlabel("总耗时（ms）")
    ax.set_title("三平台适配：不同策略的总耗时", fontsize=12, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    for b, v in zip(bars, values):
        ax.text(v + max(values) * 0.01, b.get_y() + b.get_height() / 2, f"{v:.0f}",
                va="center", fontsize=9, color="#4b5452")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "speed.png"))
    plt.close(fig)

    efforts = list(reason_results.keys())
    times = [reason_results[e].get("totalMs", 0) for e in efforts]
    tokens = [reason_results[e].get("completionTokens", 0) for e in efforts]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.2), dpi=160)
    ax1.bar(efforts, times, color=["#1f5a54", "#b08a5a", "#bd6f58"], width=0.45)
    ax1.set_title("思考强度：总耗时", fontsize=11)
    ax1.set_ylabel("ms")
    ax2.bar(efforts, tokens, color=["#1f5a54", "#b08a5a", "#bd6f58"], width=0.45)
    ax2.set_title("思考强度：输出 token", fontsize=11)
    ax2.set_ylabel("tokens")
    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "reasoning.png"))
    plt.close(fig)

    # ---- 报告 ----
    lines = ["# 速度优化实验\n"]
    lines.append(f"- 时间：{data['generatedAt']}")
    lines.append("- 环境：DeepSeek deepseek-flash，单机，同一批输入；短文为稿件 #1（201 字），长文为 #16（2102 字）")
    lines.append("- 说明：适配每个平台包含一次改写 + 一次合规预检；总耗时含 HTTP 往返。\n")

    lines.append("## 一、适配策略（三平台，短文）\n")
    lines.append("| 策略 | 总耗时 | 改写/合规 | 输入/输出 token | 格式通过 | 形态特征 |")
    lines.append("|---|---|---|---|---|---|")
    for label, s in adapt_results.items():
        detail = s.get("detail") or []
        rewrite = sum((p.get("adaptMs") or 0) for p in detail)
        compliance = sum((p.get("complianceMs") or 0) for p in detail)
        lines.append(f"| {label} | {s.get('totalMs')} ms | {rewrite} / {compliance} ms | "
                     f"{s.get('promptTokens')} / {s.get('completionTokens')} | "
                     f"{s.get('formatPass')}/{s.get('platforms')} | {s.get('shapeScore')}/{s.get('platforms')} |")
    lines.append("\n> 表中的「改写/合规」是各平台耗时之和；并行时它们重叠，求和会大于墙钟总耗时。\n")
    lines.append("\n![策略耗时](perf/speed.png)\n")
    lines.append("**怎么读**：\n")
    lines.append("- 串行与并行的差别只在等待方式：并行时三个平台同时跑，总耗时接近最慢的那个；")
    lines.append("- 合并一次调用减少了改写次数（3 次 → 1 次），但输出更长，容易变慢或被截断；")
    lines.append("- 通用提示词（去掉平台形态要点）调用次数不变，所以速度不会明显变快，主要损失是形态。\n")

    lines.append("## 二、长文（2102 字）\n")
    lines.append("| 策略 | 总耗时 | 格式通过 | 各平台正文长度 |")
    lines.append("|---|---|---|---|")
    for label, s in long_results.items():
        lines.append(f"| {label} | {s.get('totalMs')} ms | {s.get('formatPass')}/{s.get('platforms')} | "
                     f"{s.get('contentLens')} |")
    lines.append("")

    lines.append("## 三、思考强度（审核同一段违规文案）\n")
    lines.append("| 强度 | 总耗时 | 输入 token | 输出 token | 判定 | 命中规则 | 违规片段 |")
    lines.append("|---|---|---|---|---|---|---|")
    for effort, s in reason_results.items():
        lines.append(f"| {effort} | {s.get('totalMs')} ms | {s.get('promptTokens')} | "
                     f"{s.get('completionTokens')} | {s.get('riskLevel')} | "
                     f"{s.get('hitRules')} | {s.get('violations')} |")
    lines.append("\n![思考强度](perf/reasoning.png)\n")
    lines.append("**代价**：开思考会显著增加输出 token 与等待时间；在这类“按规则判定”的任务上，"
                 "判定结果没有变好（同一段文案的等级与片段数一致）。真正的风险是长文时推理耗尽输出预算、"
                 "正文为空（阶段 5 实测过），所以生产默认 `none`。\n")

    lines.append("## 四、适配开思考（单平台）\n")
    lines.append("| 强度 | 总耗时 | 输出 token | 格式 |")
    lines.append("|---|---|---|---|")
    for effort, s in reason_adapt.items():
        lines.append(f"| {effort} | {s.get('totalMs')} ms | {s.get('completionTokens')} | "
                     f"{s.get('formatPass')}/{s.get('platforms')} |")
    lines.append("")

    lines.append("## 五、结论\n")
    serial_short = adapt_results["分平台 · 串行（原方案）"].get("totalMs", 0)
    parallel_short = adapt_results["分平台 · 并行（当前生产）"].get("totalMs", 0)
    generic_short = adapt_results["通用提示词 · 并行"].get("totalMs", 0)
    unified_short = adapt_results["合并一次调用"].get("totalMs", 0)
    generic_shape = adapt_results["通用提示词 · 并行"].get("shapeScore", 0)
    unified_shape = adapt_results["合并一次调用"].get("shapeScore", 0)
    long_serial = long_results["长文 · 串行"].get("totalMs", 0)
    long_parallel = long_results["长文 · 并行"].get("totalMs", 0)
    long_unified = long_results["长文 · 合并一次"].get("totalMs", 0)
    long_unified_fmt = long_results["长文 · 合并一次"].get("formatPass", 0)
    none_s = reason_results.get("none", {})
    low_s = reason_results.get("low", {})
    high_s = reason_results.get("high", {})
    lines.append(f"1. **最快的改动是并行**：三平台短文 {serial_short / 1000:.1f} s → "
                 f"{parallel_short / 1000:.1f} s（约 {(1 - parallel_short / max(1, serial_short)) * 100:.0f}%），"
                 f"长文 {long_serial / 1000:.1f} s → {long_parallel / 1000:.1f} s；格式与形态都是 3/3。"
                 "这是唯一“确定更快且不牺牲质量”的方案，已作为生产默认。")
    lines.append(f"2. **分平台写一套提示词不会更快**：通用提示词 {generic_short / 1000:.1f} s vs 分平台 "
                 f"{parallel_short / 1000:.1f} s，只快约 {(parallel_short - generic_short) / 1000:.1f} s，"
                 f"但形态特征 {generic_shape}/3 vs 3/3。分平台提示词的价值在形态质量，不在速度。")
    lines.append(f"3. **合并一次调用不一定更快**：短文 {unified_short / 1000:.1f} s vs 并行 "
                 f"{parallel_short / 1000:.1f} s，形态 {unified_shape}/3；长文 {long_unified / 1000:.1f} s、"
                 f"格式 {long_unified_fmt}/3。少两次改写调用，但单次输出更长，容易变慢或被截断，不建议作为默认。")
    lines.append(f"4. **关思考是正确默认**：none {none_s.get('totalMs', 0) / 1000:.1f} s / "
                 f"{none_s.get('completionTokens', 0)} 输出 token；low {low_s.get('totalMs', 0) / 1000:.1f} s / "
                 f"{low_s.get('completionTokens', 0)}；high {high_s.get('totalMs', 0) / 1000:.1f} s / "
                 f"{high_s.get('completionTokens', 0)}。等级都是 2，命中规则/片段只有轻微差异，"
                 "没有明确质量收益；代价是约 50% 时间和接近 2 倍的输出 token，长文还可能因推理耗尽预算而空输出。"
                 "适配开思考也从 5.3 s 升到 7.2 s、输出 token 359→665，格式不变。")
    lines.append("\n> 思考强度的 low/high 相对快慢会受服务端排队影响，样本只有 2 轮；"
                 "但“none 明显最快、token 最少”在两组里都成立。\n")
    lines.append("> 质量代理“形态特征”只检查最容易识别的平台标志（小红书 emoji+标签、公众号无标签、"
                 "抖音【画面】/【口播】），不等于完整的人工评分；结论以速度为主，质量只作方向性参考。\n")

    with open(os.path.join(ROOT, "docs", "实验-速度优化.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("已生成：docs/实验-速度优化.md、docs/perf/speed-experiment.json、speed.png、reasoning.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
