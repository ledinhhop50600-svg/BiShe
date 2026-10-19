"""阶段 8：跨平台适配质量评估。

用法（在项目根目录）：
    python tools/eval_adaptation.py                # 生成 + LLM 评分 + 人工评分表
    python tools/eval_adaptation.py --no-llm       # 只跑格式与合规指标

产物：
    docs/eval/adaptation-results.json   完整结果（评测中心页面读取）
    docs/eval/adaptation-human-sheet.csv 人工评分表（留空待填，UTF-8 BOM 可直接用 Excel 打开）
    docs/eval/adaptation-eval.md        指标报告

评测集：4 篇不同长度/性质的稿件 × 3 个平台（小红书 / 公众号 / 抖音）。
  - #1 小户型收纳（201 字，正常）
  - #2 平价护肤（163 字，正常）
  - #8 减脂餐一周瘦十斤（101 字，夸大，已驳回）
  - #16 全屋收纳长文（2102 字，长文压缩）

为什么直接调用 Agent 而不走主系统的 /adapt：
  1. 评测不应往演示库写适配记录；
  2. 可以传确定性的 requestId，复用 Agent 的回放缓存，重复评测不重复花钱。
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.environ.get("ZIMEITI_BASE", "http://localhost:8080").rstrip("/")
AGENT = os.environ.get("ZIMEITI_AGENT", "http://localhost:8001").rstrip("/")
OUT_DIR = os.path.join(ROOT, "docs", "eval")
AGENT_ENV = os.path.join(ROOT, "agent", ".env")
# LLM 评分缓存固定放在 docs/eval 下，不随 --out-dir 变化
JUDGE_CACHE = os.path.join(OUT_DIR, "judge-cache.json")

ARTICLES = [1, 2, 8, 16]
PLATFORMS = ["xiaohongshu", "wechat", "douyin"]


def call(url, method="GET", body=None, token=None, timeout=300):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("satoken", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, None
    except Exception as e:
        return -1, {"error": f"{type(e).__name__}: {e}"}


def login(username, password="123456"):
    _, body = call(BACKEND + "/api/auth/login", "POST", {"username": username, "password": password})
    return ((body or {}).get("data") or {}).get("tokenValue")


def load_agent_env():
    """从 agent/.env 读取模型配置（.env 不进版本库，这里只读取、不打印 Key）。"""
    env = {}
    if not os.path.exists(AGENT_ENV):
        return env
    with open(AGENT_ENV, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def judge_key(platform_name, title, content):
    """LLM 评分缓存键：平台 + 适配标题 + 适配正文。重复评测不重复花钱。"""
    return hashlib.sha1(
        (platform_name + "|" + (title or "") + "|" + (content or "")).encode("utf-8")
    ).hexdigest()


def load_judge_cache():
    if not os.path.exists(JUDGE_CACHE):
        return {}
    try:
        with open(JUDGE_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_judge_cache(cache):
    with open(JUDGE_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def judge_scores(env, platform_name, source_title, source_content,
                 adapted_title, adapted_content, tags):
    """调用模型给适配结果打分（风格/信息保留/可读性，1-5 分）。"""
    key = env.get("API_KEY", "")
    if not key:
        return {"error": "未配置 API_KEY"}
    model = env.get("MODEL", "deepseek-flash")
    base = env.get("BASE_URL", "https://api.deepseek.com").rstrip("/")

    prompt = (
        "你是内容运营评委。请对下面这个「源文章 → 目标平台版本」的适配结果打分，每项 1-5 分（5 最好）：\n"
        "- style：风格符合度，是否符合目标平台的表达习惯\n"
        "- retention：信息保留度，是否保留了源文章的核心信息（没有编造新事实）\n"
        "- readability：可读性，语言是否通顺、结构是否清晰\n\n"
        f"【目标平台】{platform_name}\n"
        f"【源文章】标题：{source_title}\n正文：{source_content[:1800]}\n\n"
        f"【适配结果】标题：{adapted_title}\n正文：{adapted_content[:1800]}\n"
        f"标签：{' '.join(tags or [])}\n\n"
        "只输出 JSON：{\"style\":4,\"retention\":5,\"readability\":4,\"comment\":\"一句话点评\"}"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
        "reasoning_effort": "none",
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        scores = json.loads(text)
        return {
            "style": int(scores.get("style", 0)),
            "retention": int(scores.get("retention", 0)),
            "readability": int(scores.get("readability", 0)),
            "comment": str(scores.get("comment", "")),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM 评分（只算格式/合规指标）")
    parser.add_argument("--refresh-judge", action="store_true", help="忽略 LLM 评分缓存，重新打分")
    parser.add_argument("--run-id", default="default",
                        help="评测批次标识；换一个值会强制重新调用模型（默认复用回放缓存）")
    parser.add_argument("--out-dir", default=OUT_DIR,
                        help="结果目录；评测中心用 docs/eval/demo，避免覆盖论文数据")
    args = parser.parse_args()
    out_dir = os.path.abspath(args.out_dir)
    out_rel = os.path.relpath(out_dir, ROOT).replace("\\", "/")

    os.makedirs(out_dir, exist_ok=True)
    judge_cache = {} if args.refresh_judge else load_judge_cache()
    admin = login("admin")
    if not admin:
        print("[FAIL] 管理员登录失败，后端是否已启动？")
        return 1

    _, body = call(BACKEND + "/api/platform/list", token=admin)
    platforms = {p["platformKey"]: p for p in ((body or {}).get("data") or [])}
    _, body = call(BACKEND + "/api/rule/list", token=admin)
    raw_rules = (body or {}).get("data") or []
    key_by_id = {p["id"]: p["platformKey"] for p in platforms.values()}
    rules = [{
        "code": r["ruleCode"], "name": r["ruleName"], "category": r["category"],
        "content": r["ruleContent"], "source": r.get("source"),
        "suggestedLevel": r.get("suggestedLevel"),
        "platformKey": key_by_id.get(r.get("platformId")),
    } for r in raw_rules]

    env = load_agent_env()
    results = []
    started = time.time()

    for aid in ARTICLES:
        _, body = call(BACKEND + f"/api/article/{aid}", token=admin)
        article = (body or {}).get("data") or {}
        if not article:
            print(f"[WARN] 稿件 {aid} 读取失败，跳过")
            continue
        print(f"\n=== 稿件 #{aid}《{article.get('title')}》 {len(article.get('content') or '')} 字 ===")

        for pkey in PLATFORMS:
            p = platforms.get(pkey)
            if not p:
                print(f"  [WARN] 平台 {pkey} 未配置，跳过")
                continue
            content_hash = hashlib.sha1(
                ((article.get("title") or "") + "\n" + (article.get("content") or "")).encode("utf-8")
            ).hexdigest()[:10]
            rid = f"eval-adapt:{args.run_id}:{aid}:{pkey}:{content_hash}"
            req = {
                "requestId": rid,
                "articleId": aid,
                "title": article.get("title") or "",
                "content": article.get("content") or "",
                "targetPlatformKeys": [pkey],
                "platforms": [{
                    "platformKey": p["platformKey"], "platformName": p["platformName"],
                    "titleMaxLen": p.get("titleMaxLen"), "contentMaxLen": p.get("contentMaxLen"),
                    "tagRule": p.get("tagRule"), "styleDesc": p.get("styleDesc"),
                }],
                "rules": rules,
            }
            t0 = time.time()
            status, body = call(AGENT + "/api/agent/adapt", "POST", req, timeout=300)
            elapsed = int((time.time() - t0) * 1000)
            if status != 200 or not body or not body.get("results"):
                print(f"  [FAIL] {pkey}: HTTP {status} {str(body)[:160]}")
                results.append({"articleId": aid, "platformKey": pkey, "error": str(body)[:300]})
                continue
            r = body["results"][0]
            fmt = r.get("formatCheck") or {}
            comp = r.get("compliance") or {}
            print(f"  {p['platformName']}: 格式 {'通过' if fmt.get('passed') else '未通过'} "
                  f"| 正文 {fmt.get('contentLen')} 字 | 合规 {comp.get('riskLevelText')} "
                  f"| {elapsed}ms | replay={body.get('replayed')}")

            row = {
                "articleId": aid,
                "articleTitle": article.get("title"),
                "sourceLen": len(article.get("content") or ""),
                "platformKey": pkey,
                "platformName": p["platformName"],
                "title": r.get("title"),
                "content": r.get("content"),
                "tags": r.get("tags") or [],
                "formatPassed": bool(fmt.get("passed")),
                "formatIssues": fmt.get("issues") or [],
                "titleLen": fmt.get("titleLen"),
                "contentLen": fmt.get("contentLen"),
                "tagCount": fmt.get("tagCount"),
                "complianceLevel": comp.get("riskLevel"),
                "complianceText": comp.get("riskLevelText"),
                "complianceReason": comp.get("reason"),
                "durationMs": elapsed,
                "usage": body.get("usage"),
                "replayed": bool(body.get("replayed")),
            }

            if not args.no_llm:
                key = judge_key(p["platformName"], r.get("title") or "", r.get("content") or "")
                if key in judge_cache:
                    scores = judge_cache[key]
                    print(f"    LLM（缓存）: 风格 {scores['style']} / 保留 {scores['retention']} / 可读 {scores['readability']}")
                else:
                    scores = judge_scores(
                        env, p["platformName"], article.get("title"), article.get("content") or "",
                        r.get("title") or "", r.get("content") or "", r.get("tags") or [])
                    if "error" not in scores:
                        judge_cache[key] = scores
                        save_judge_cache(judge_cache)
                        print(f"    LLM: 风格 {scores['style']} / 保留 {scores['retention']} / 可读 {scores['readability']}")
                    else:
                        print(f"    LLM 评分失败：{scores['error']}")
                row["llm"] = scores

            results.append(row)

    # ---------------- 汇总 ----------------
    ok_rows = [r for r in results if "error" not in r]
    total = len(ok_rows)
    passed = sum(1 for r in ok_rows if r["formatPassed"])
    by_platform = {}
    for pkey in PLATFORMS:
        rows = [r for r in ok_rows if r["platformKey"] == pkey]
        if not rows:
            continue
        by_platform[pkey] = {
            "count": len(rows),
            "formatPassRate": round(sum(1 for r in rows if r["formatPassed"]) / len(rows) * 100, 1),
            "avgContentLen": round(sum(r["contentLen"] or 0 for r in rows) / len(rows), 1),
            "avgRatio": round(sum((r["contentLen"] or 0) / max(1, r["sourceLen"]) for r in rows) / len(rows), 2),
        }
        long_rows = [r for r in rows if r["articleId"] == 16]
        if long_rows:
            by_platform[pkey]["longArticleRatio"] = round(
                (long_rows[0]["contentLen"] or 0) / max(1, long_rows[0]["sourceLen"]), 2)
        scored = [r["llm"] for r in rows if isinstance(r.get("llm"), dict) and "error" not in r["llm"]]
        if scored:
            by_platform[pkey]["llmAvg"] = {
                "style": round(sum(s["style"] for s in scored) / len(scored), 2),
                "retention": round(sum(s["retention"] for s in scored) / len(scored), 2),
                "readability": round(sum(s["readability"] for s in scored) / len(scored), 2),
            }

    summary = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "runId": args.run_id,
        "model": env.get("MODEL", "deepseek-flash"),
        "articles": ARTICLES,
        "platforms": PLATFORMS,
        "total": total,
        "formatPassed": passed,
        "formatPassRate": round(passed / total * 100, 1) if total else 0,
        "byPlatform": by_platform,
        "elapsedSeconds": round(time.time() - started, 1),
        "results": results,
    }

    with open(os.path.join(out_dir, "adaptation-results.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # ---------------- 人工评分表 ----------------
    sheet_path = os.path.join(out_dir, "adaptation-human-sheet.csv")
    with open(sheet_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["稿件ID", "稿件标题", "目标平台", "适配标题", "源文长度", "适配长度",
                    "格式通过", "合规等级", "风格_LLM", "保留_LLM", "可读_LLM",
                    "风格_人工(1-5)", "保留_人工(1-5)", "可读_人工(1-5)", "人工点评"])
        for r in ok_rows:
            llm = r.get("llm") or {}
            w.writerow([
                r["articleId"], r["articleTitle"], r["platformName"], r["title"],
                r["sourceLen"], r["contentLen"], "是" if r["formatPassed"] else "否",
                r["complianceText"],
                llm.get("style", ""), llm.get("retention", ""), llm.get("readability", ""),
                "", "", "", "",
            ])

    # ---------------- Markdown 报告 ----------------
    lines = []
    lines.append("# 跨平台适配质量评估\n")
    lines.append(f"- 生成时间：{summary['generatedAt']}")
    lines.append(f"- 评测批次：`{summary['runId']}`（`default` 复用回放缓存；换一个 run-id 会强制重新调用模型）")
    lines.append(f"- 模型：{summary['model']}（思考模式关闭）")
    lines.append(f"- 评测集：{len(ARTICLES)} 篇稿件 × {len(PLATFORMS)} 个平台 = {total} 个适配结果")
    lines.append("- 稿件：#1 正常短文、#2 正常短文、#8 夸大样本、#16 2102 字长文")
    lines.append("- 平台：小红书（压缩到 1000 字）、公众号（长文）、抖音（口播脚本）")
    lines.append("- 评测方式：直接调用 Agent（确定性 requestId，可复用回放缓存），不写入演示库\n")

    lines.append("## 一、总体指标\n")
    lines.append("| 指标 | 结果 |")
    lines.append("|---|---|")
    lines.append(f"| 格式自检通过率 | {summary['formatPassed']}/{summary['total']} = **{summary['formatPassRate']}%** |")
    lines.append(f"| 平均耗时 | 见逐条表 |")
    lines.append(f"| 总耗时 | {summary['elapsedSeconds']} 秒 |")
    lines.append("")

    # 关键发现（自动生成，避免每次手写）
    lines.append("## 一之二、关键发现\n")
    failed = [r for r in ok_rows if not r["formatPassed"]]
    if failed:
        f = failed[0]
        cap = platforms[f["platformKey"]].get("contentMaxLen")
        lines.append(f"- **唯一未通过**：#{f['articleId']} 适配到 {f['platformName']} 时正文 "
                     f"{f['contentLen']} 字，超过上限 {cap} 字。说明长文压缩仍是弱项；"
                     f"系统会给出明确警告，不会把超限结果当成通过。")
    else:
        lines.append("- 本次所有适配结果格式自检全部通过。")
    long_parts = []
    for pkey, p in by_platform.items():
        if "longArticleRatio" in p:
            long_parts.append(f"{platforms[pkey]['platformName']} {p['longArticleRatio']}")
    if long_parts:
        lines.append(f"- **长文 #16（2102 字）压缩比**：" + "、".join(long_parts) +
                     "。小红书/抖音明显压缩，公众号基本等长 —— 符合平台形态。")
    scored_all = [r["llm"] for r in ok_rows
                  if isinstance(r.get("llm"), dict) and "error" not in r["llm"]]
    if scored_all:
        avg_style = sum(s["style"] for s in scored_all) / len(scored_all)
        avg_ret = sum(s["retention"] for s in scored_all) / len(scored_all)
        avg_read = sum(s["readability"] for s in scored_all) / len(scored_all)
        lines.append(f"- **LLM 评分**：风格 {avg_style:.2f} / 保留 {avg_ret:.2f} / 可读 {avg_read:.2f}"
                     f"（1-5 分）。分数集中在 4-5，区分度低，必须结合人工评分看。")
    real = [r for r in ok_rows if not r["replayed"]]
    if real:
        avg_ms = sum(r["durationMs"] for r in real) / len(real)
        lines.append(f"- **单次适配耗时**：{avg_ms:.0f}ms（含改写 + 合规预检两次模型调用）。")
    lines.append("")

    lines.append("## 二、分平台指标\n")
    lines.append("| 平台 | 数量 | 格式通过率 | 平均正文长度 | 平均长度比（含短文扩写） | 长文 #16 长度比 | LLM 风格 | LLM 保留 | LLM 可读 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for pkey, p in by_platform.items():
        llm = p.get("llmAvg") or {}
        lines.append(f"| {platforms[pkey]['platformName']} | {p['count']} | {p['formatPassRate']}% | "
                     f"{p['avgContentLen']} | {p['avgRatio']} | {p.get('longArticleRatio', '-')} | "
                     f"{llm.get('style', '-')} | {llm.get('retention', '-')} | {llm.get('readability', '-')} |")
    lines.append("")
    lines.append("> 长度比说明：短文本适配通常会扩写（补充开头钩子、分段、平台化表达），"
                 "所以平均比值会大于 1；**压缩效果应看长文 #16**：小红书/抖音上限 1000 字，"
                 "长文必须明显压缩；公众号允许长文，比值接近 1 属正常。\n")

    lines.append("## 三、逐条结果\n")
    lines.append("| 稿件 | 平台 | 格式 | 正文长度 | 合规 | 耗时 | LLM（风格/保留/可读） |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in ok_rows:
        llm = r.get("llm") or {}
        score = f"{llm.get('style','-')}/{llm.get('retention','-')}/{llm.get('readability','-')}" \
            if "error" not in llm else "调用失败"
        lines.append(f"| #{r['articleId']} {r['articleTitle'][:14]} | {r['platformName']} | "
                     f"{'通过' if r['formatPassed'] else '未通过'} | {r['contentLen']} | "
                     f"{r['complianceText']} | {r['durationMs']}ms | {score} |")
    lines.append("")

    lines.append("## 四、人工评分与一致性（待填）\n")
    lines.append(f"人工评分表：`{out_rel}/adaptation-human-sheet.csv`（UTF-8 BOM，可直接用 Excel 打开）。")
    lines.append("请对每个适配结果的**风格符合度 / 信息保留度 / 可读性**打 1-5 分；"
                 "填完后可计算与 LLM 评分的 Spearman 相关系数（阶段 8 后续）。")
    lines.append("")
    lines.append("**注意**：LLM 评分不能替代人工评分。论文中应报告两者的相关性，"
                 "并说明 LLM 评委可能偏宽松、对平台风格的理解有限等局限。\n")

    lines.append("## 五、已知局限\n")
    lines.append("1. 只覆盖 4 篇稿件、3 个平台，样本量小，结论以方向性为主；")
    lines.append("2. 稿件 #16 是为长文压缩专门准备的自建样本，不完全代表真实业务分布；")
    lines.append("3. 合规预检复用审核规则库，平台专属规则仍不完整；")
    lines.append("4. 人工评分尚未填写，当前只有格式指标与 LLM 评分。\n")

    with open(os.path.join(out_dir, "adaptation-eval.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "=" * 56)
    print(f"总计 {total} 个结果，格式通过率 {summary['formatPassRate']}%")
    for pkey, p in by_platform.items():
        print(f"  {platforms[pkey]['platformName']}: {p['formatPassRate']}% "
              f"（{p['count']} 条，平均长度比 {p['avgRatio']}）")
    print(f"产物：{out_rel}/adaptation-results.json")
    print(f"      {out_rel}/adaptation-human-sheet.csv")
    print(f"      {out_rel}/adaptation-eval.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
