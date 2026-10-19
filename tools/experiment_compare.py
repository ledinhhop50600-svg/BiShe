"""对比实验：四个方案在同一批样本上的效果、成本与耗时对比。

四个方案（论文实验章节的主体）：
  A 关键词规则      —— 敏感词库匹配（传统基线，阶段 3 已实现）
  B 纯大模型        —— 不提供任何规则，模型凭常识判断
  C RAG + 大模型    —— 混合检索召回最相关规则后判断（当前实现）
  D 全量规则 + 大模型 —— 把全部规则塞进提示词（上界参照，用于量化 RAG 的代价与收益）

指标：
  - 阻断判定（riskLevel >= 2 视为阻断）的准确率 / 精确率 / 召回率 / F1
  - 违规片段有效率：模型给出的片段里，有多少是原文真实存在的连续文字
  - 平均 token、平均耗时、估算成本

用法：
    python tools/experiment_compare.py
依赖：后端 8080（取登录令牌、敏感词、规则、平台）、智能体 8001（真实模型）

⚠️ 成本提示：10 个样本 × 3 个需要调用模型的方案 = 30 次真实调用，约 0.3 元。

注意：本脚本每次运行都会**覆盖**报告里的数据章节；报告末尾的「结果分析 / 局限」是人工撰写的，
重跑后需要重新追加（或者把分析单独放到文档里）。当前 v1 报告里已包含分析，重跑请先备份。
"""

import json
import os
import time
import urllib.error
import urllib.request
import uuid

JAVA = os.environ.get("ZIMEITI_BASE", "http://localhost:8080").rstrip("/")
AGENT = os.environ.get("ZIMEITI_AGENT", "http://localhost:8001").rstrip("/")
REPORT = os.path.join(os.path.dirname(__file__), "..", "docs", "实验-对比实验-v1.md")

# deepseek-flash 空闲时段单价（元/百万 token），高峰时段翻倍。
# 实验在空闲时段跑，按此估算；报告里会注明。
PRICE_INPUT_PER_M = 1.0
PRICE_OUTPUT_PER_M = 4.0


# ======================================================================
# 样本集（先做小规模验证，正式评测集在后续补齐）
# ======================================================================
LONG_ARTICLE = """最近很多朋友问我，为什么明明很努力地护肤，皮肤状态却一直不稳定。作为一个在护肤这件事上踩过无数坑的人，我想把这几年的经验系统地整理一下，希望能帮到同样困惑的你。

先说清洁。很多人以为洗得越干净越好，其实过度清洁会破坏皮肤屏障。我现在的做法是早晚各一次：早上用清水，晚上用温和的氨基酸洁面。洗完不要用力擦，用毛巾轻轻按干就好。如果化了妆，先用卸妆产品溶解彩妆，再用洁面洗掉残留，不要指望一支洁面解决所有问题。

其次是保湿。保湿的核心是锁水而不是补水。拍完化妆水之后，一定要用含神经酰胺或者角鲨烷的产品把水分锁住，否则水拍得再多也会很快蒸发。我自己搭配的这套配方是国家级实验室研发的，用下来肤感很好，三天见效，坚持一周肤色明显提亮，痘印也淡了不少。价格也不贵，日常用完全够。

然后是防晒。这一点被严重低估了。紫外线是导致光老化的主要原因，一年四季都要防晒，阴天也不例外；室内如果靠窗，也建议涂防晒。用量要足够，一张脸大约一元硬币大小，出门前二十分钟涂好。

再说作息和饮食。熬夜对皮肤的影响比任何护肤品都大。我尽量保证十一点前睡，饮食上减少高糖和高油，多喝水，多吃深色蔬菜。运动出汗对皮肤也有好处，但运动后要及时清洁，不要让汗液长时间停留在皮肤上。

最后说心态。皮肤状态会有波动，不要因为一两天的爆痘就焦虑，也不要频繁更换产品。给皮肤一点时间适应，通常四周左右能看到变化。如果出现持续的过敏反应，应当去看皮肤科医生，而不是自己硬扛。

如果你也在护肤这条路上摸索，欢迎一起交流。我平时会整理一些产品对比和使用记录，需要的姐妹加我微信 skincarer_note 领取，备注护肤通过得快一些。""".strip()

LONG_CLEAN = """上个月请了五天年假，去了一趟云南，回来整理一下这次的经验，给准备去的朋友参考。

交通方面，建议直飞昆明或者丽江，落地后租车自驾最方便。云南的路况整体不错，但山路多弯，新手司机要谨慎。租车尽量选全险，异地还车会贵一些，看个人安排。

住宿我选的是古城边上的民宿，价格比古城内便宜三分之一，走路十分钟就能进城。旺季一定要提前两周订，临时订价格会翻倍。

行程安排上，我走的是昆明—大理—丽江这条线。大理安排两天，环洱海骑行一天，另一天在古城里闲逛。丽江安排两天，玉龙雪山一天，束河古镇一天。这个节奏比较松，不会太累。

吃的话，过桥米线、汽锅鸡、菌子火锅都值得试。七八月是菌子季，野生菌价格高但味道确实好，注意要煮透，不要自己乱采。

注意事项：云南海拔较高，丽江和香格里拉要注意高原反应，第一天不要剧烈运动，多喝水。紫外线很强，防晒霜、帽子、墨镜都要带。早晚温差大，即使夏天也要带一件外套。

费用方面，五天四晚人均三千五左右，包含机票、租车、住宿和餐饮。提前订能省不少。

整体来说，云南很适合放松，节奏慢下来才能体会到它的好。""".strip()

SAMPLES = [
    {
        "id": "S1_商业推广_极限词",
        "title": "全网最低价的美肤面膜，三天见效不是梦",
        "content": "姐妹们这波真的可以冲，我们这款面膜是全网最低价，专柜卖三百多，今天直播间只要二十九块九。配方是国家级实验室研发的，主打三天见效，坚持用一周肤色明显提亮。敏感肌也能用，零刺激零风险，先到先得，库存只剩最后两百单。",
        "block": True,
        "note": "商业推广 + 极限词 + 功效承诺",
    },
    {
        "id": "S2_个人分享_夸大",
        "title": "在家做的减脂餐，一周瘦十斤",
        "content": "跟着我这个食谱吃一周，保证瘦十斤，不运动也能掉秤。早餐两颗水煮蛋加一杯黑咖啡，午餐水煮鸡胸肉配西兰花，晚餐只喝一杯代餐奶昔。这个方法绝对有效，我身边十个朋友试了十个都成功，包治各种平台期，零风险不反弹。",
        "block": False,
        "note": "个人分享、无售卖无引流 → 按 D4 应为疑似不阻断",
    },
    {
        "id": "S3_站外引流",
        "title": "整理了 100 个收纳小窍门，需要的姐妹看过来",
        "content": "这份清单是我花了三个月整理的，从厨房到卧室一共一百条，每条都配了实拍图。因为文件比较大，平台发不全，需要的姐妹加我微信 lingqu_qingdan 领取，备注收纳我通过得快。也可以私信我拉你进群，群里每天更新一条。",
        "block": True,
        "note": "站外引流（加微信/私信）",
    },
    {
        "id": "S4_违禁品交易",
        "title": "低价转让进口处方药，量大从优",
        "content": "手上有批进口处方药，价格比药店便宜很多，需要的私聊，可以先试后付。量大从优，长期合作价格更好谈。另外还有部分保健品，具体功效私聊说，不方便公开讲。",
        "block": True,
        "note": "违禁品交易 → 严重",
    },
    {
        "id": "S5_侵权搬运",
        "title": "（转载）一篇很好的职场文章，分享给大家",
        "content": "以下内容全文转载自某公众号，没有获得作者授权，因为写得实在太好，想让更多人看到。原作者是一位资深 HR，文章讲的是如何写简历。版权归原作者所有，如有侵权请联系删除。",
        "block": True,
        "note": "未授权转载（侵权）",
    },
    {
        "id": "S6_正常分享_旅行",
        "title": "出差党的轻量行李清单",
        "content": "一年出差三十次以后，我的箱子里只剩下这些：两件速干衬衫、一条可机洗西裤、一双正装鞋、一个折叠洗衣袋、一套旅行装洗护、一个多口充电头、一根三合一数据线。衣服按卷筒法塞进压缩袋，能省一半空间。",
        "block": False,
        "note": "正常内容",
    },
    {
        "id": "S7_语境陷阱_作品名",
        "title": "最近在看的几部剧，推荐给大家",
        "content": "最近看了《最好的我们》，很推荐。节奏舒缓，演员自然，讲的是一群普通高中生的故事，看完会想起自己的学生时代。另外还看了《长安十二时辰》，服化道很用心。这两部都可以在视频平台找到。",
        "block": False,
        "note": "含「最好的我们」——关键词基线会误判，语境判断应通过",
    },
    {
        "id": "S8_正常分享_食谱",
        "title": "番茄炒蛋的正确做法",
        "content": "先把鸡蛋打散，加一点点盐，热锅凉油滑散盛出。番茄切块下锅炒出汁，加少许糖提鲜，再把鸡蛋倒回去炒匀，出锅前撒葱花。关键有两点：鸡蛋不要炒太老，番茄要炒出汁水。",
        "block": False,
        "note": "正常内容",
    },
    {
        "id": "S9_长文_中段违规",
        "title": "护肤经验分享：从清洁到心态",
        "content": LONG_ARTICLE,
        "block": True,
        "note": "约千字长文，违规集中在**中段**（国家级实验室/三天见效）与结尾（加微信）",
    },
    {
        "id": "S10_长文_正常",
        "title": "云南五日游经验分享",
        "content": LONG_CLEAN,
        "block": False,
        "note": "约八百字正常长文，用于检验长文本下的误判",
    },
]


# ======================================================================
# HTTP 工具
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
# 方案实现
# ======================================================================
def run_keyword(sample, words):
    """方案 A：敏感词匹配。命中词的最高等级 >= 2 视为阻断。"""
    text = f"{sample['title']}\n{sample['content']}"
    hits = [w for w in words if w["word"] in text]
    max_level = max([w["level"] for w in hits], default=0)
    return {
        "riskLevel": max_level if hits else 0,
        "fragments": hits and [w["word"] for w in hits] or [],
        "promptTokens": 0,
        "completionTokens": 0,
        "durationMs": 0,
        "trace": f"命中 {len(hits)} 个词",
    }


def run_agent(sample, rules, platform, use_rag):
    """方案 B/C/D：调用智能体。"""
    req = {
        "requestId": str(uuid.uuid4()),
        "articleId": 0,
        "triggerType": "POST_AUDIT",
        "targetPlatformKey": "local",
        "title": sample["title"],
        "content": sample["content"],
        "platform": platform,
        "rules": rules,
        "useRag": use_rag,
    }
    t0 = time.time()
    status, body = http_json(f"{AGENT}/api/agent/audit", "POST", req)
    elapsed_ms = int((time.time() - t0) * 1000)
    if status != 200:
        return {"error": f"HTTP {status}: {str(body)[:160]}", "durationMs": elapsed_ms}

    usage = body.get("usage") or {}
    retrieve = next((t.get("output") for t in body.get("trace") or []
                     if t.get("action") == "retrieve_rules"), "")
    return {
        "riskLevel": body.get("riskLevel"),
        "fragments": [v.get("fragment") for v in body.get("violations") or []],
        "promptTokens": usage.get("promptTokens", 0),
        "completionTokens": usage.get("completionTokens", 0),
        "durationMs": body.get("durationMs", elapsed_ms),
        "trace": retrieve,
    }


# ======================================================================
# 指标
# ======================================================================
def metrics(rows):
    """按"阻断/不阻断"二分类计算指标。"""
    tp = fp = tn = fn = 0
    for r in rows:
        pred = (r["pred_level"] or 0) >= 2
        truth = r["block"]
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
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "accuracy": acc, "precision": prec, "recall": rec, "f1": f1}


def fragment_validity(rows, samples_by_id):
    valid = total = 0
    for r in rows:
        content = samples_by_id[r["id"]]["content"] + "\n" + samples_by_id[r["id"]]["title"]
        for frag in r.get("fragments") or []:
            if not frag:
                continue
            total += 1
            if frag in content:
                valid += 1
    return valid, total


def main():
    # 用管理员账号：取敏感词库需要 audit:sensitive 权限（审核员没有，早前因此拿到空词表，
    # 导致方案 A 全部判不出来 —— 这类"静默失败"必须在脚本里显式拦住）
    token = login("admin")
    if not token:
        print("❌ 登录失败，请确认后端与账号")
        return 1
    headers = {"satoken": token}

    _, wb = http_json(f"{JAVA}/api/sensitive/page?pageNum=1&pageSize=300", headers=headers)
    words = ((wb or {}).get("data") or {}).get("records") or []
    if not words:
        print("❌ 敏感词库为空（或接口无权限），方案 A 无效，实验终止")
        return 1

    _, rb = http_json(f"{JAVA}/api/rule/list", headers=headers)
    raw_rules = (rb or {}).get("data") or []
    if not raw_rules:
        print("❌ 规则库为空（或接口无权限），实验终止")
        return 1
    rules = [{
        "code": r.get("ruleCode"), "name": r.get("ruleName"), "category": r.get("category"),
        "content": r.get("ruleContent"), "source": r.get("source"),
        "suggestedLevel": r.get("suggestedLevel"),
    } for r in raw_rules]

    _, pb = http_json(f"{JAVA}/api/platform/list", headers=headers)
    platforms = (pb or {}).get("data") or []
    local = next((p for p in platforms if p.get("platformKey") == "local"), None)
    platform = {
        "platformKey": "local", "platformName": "本平台",
        "titleMaxLen": (local or {}).get("titleMaxLen", 60),
        "contentMaxLen": (local or {}).get("contentMaxLen", 5000),
        "tagRule": (local or {}).get("tagRule"),
        "styleDesc": (local or {}).get("styleDesc"),
    }

    print(f"样本 {len(SAMPLES)} 个 | 敏感词 {len(words)} 个 | 规则 {len(rules)} 条")
    print(f"长文样本长度：S9={len(SAMPLES[8]['content'])} 字，S10={len(SAMPLES[9]['content'])} 字")

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
        for s in SAMPLES:
            r = fn(s)
            row = {"id": s["id"], "block": s["block"], "pred_level": r.get("riskLevel"),
                   "fragments": r.get("fragments") or [], "error": r.get("error"),
                   "promptTokens": r.get("promptTokens", 0), "completionTokens": r.get("completionTokens", 0),
                   "durationMs": r.get("durationMs", 0), "trace": r.get("trace", "")}
            rows.append(row)
            mark = "✓" if ((row["pred_level"] or 0) >= 2) == s["block"] else "✗"
            print(f"  {mark} {s['id']:22s} 预期={'阻断' if s['block'] else '放行'} "
                  f"实际={row['pred_level']} | {row['durationMs']}ms | tok={row['promptTokens']}+{row['completionTokens']}")
        results[name] = rows

    samples_by_id = {s["id"]: s for s in SAMPLES}

    lines = []
    lines.append("# 对比实验记录 v1\n")
    lines.append(f"- 实验时间：{time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- 样本数：{len(SAMPLES)}（其中长文 2 篇：S9 约 {len(SAMPLES[8]['content'])} 字、S10 约 {len(SAMPLES[9]['content'])} 字）")
    lines.append(f"- 规则库：{len(rules)} 条 | 敏感词库：{len(words)} 个")
    lines.append("- 模型：deepseek-flash；检索：bge-m3（top_k=6，混合检索）")
    lines.append(f"- 计价：输入 {PRICE_INPUT_PER_M} 元/百万、输出 {PRICE_OUTPUT_PER_M} 元/百万（空闲时段；高峰翻倍）")
    lines.append("- 判定口径：`riskLevel >= 2`（违规/严重）视为**阻断**；0（通过）与 1（疑似转人工）视为放行\n")

    lines.append("## 一、总体结果\n")
    lines.append("| 方案 | 准确率 | 精确率 | 召回率 | F1 | TP/FP/TN/FN | 错误数 | 平均耗时 | 平均 token | 估算成本/条 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    summary = {}
    for name, _ in schemes:
        rows = results[name]
        m = metrics(rows)
        ok_rows = [r for r in rows if not r["error"]]
        errs = len(rows) - len(ok_rows)
        avg_ms = sum(r["durationMs"] for r in ok_rows) // max(1, len(ok_rows))
        avg_tok = sum(r["promptTokens"] + r["completionTokens"] for r in rows) // max(1, len(rows))
        cost = sum(r["promptTokens"] * PRICE_INPUT_PER_M + r["completionTokens"] * PRICE_OUTPUT_PER_M
                   for r in rows) / max(1, len(rows)) / 1_000_000
        summary[name] = {"m": m, "avg_ms": avg_ms, "avg_tok": avg_tok, "cost": cost, "errs": errs}
        lines.append(f"| {name} | {m['accuracy']:.0%} | {m['precision']:.0%} | {m['recall']:.0%} | "
                     f"{m['f1']:.2f} | {m['tp']}/{m['fp']}/{m['tn']}/{m['fn']} | {errs} | "
                     f"{avg_ms}ms | {avg_tok} | {cost:.5f} 元 |")
    lines.append("\n> 口径说明：调用失败（422/503 等）按「未阻断」计入，因此对阻断类样本算作漏判 —— 这是保守口径。")

    lines.append("\n## 二、违规片段有效率\n")
    lines.append("模型给出的片段里，有多少是原文真实存在的连续文字（防止模型改写或拼接导致定位不准）。\n")
    lines.append("| 方案 | 有效片段 / 总片段 | 有效率 |")
    lines.append("|---|---|---|")
    for name, _ in schemes:
        valid, total = fragment_validity(results[name], samples_by_id)
        rate = f"{valid / total:.0%}" if total else "-"
        lines.append(f"| {name} | {valid}/{total} | {rate} |")

    lines.append("\n## 三、逐样本结果\n")
    lines.append("| 样本 | 预期 | A 关键词 | B 纯大模型 | C RAG | D 全量规则 | 说明 |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in SAMPLES:
        cells = []
        for name, _ in schemes:
            row = next(r for r in results[name] if r["id"] == s["id"])
            lvl = row["pred_level"]
            if row.get("error"):
                cells.append("错误")
            else:
                mark = "✓" if ((lvl or 0) >= 2) == s["block"] else "✗"
                cells.append(f"{mark}{lvl}" if lvl is not None else "—")
        lines.append(f"| {s['id']} | {'阻断' if s['block'] else '放行'} | " + " | ".join(cells) + f" | {s['note']} |")

    lines.append("\n## 四、检索明细（方案 C）\n")
    lines.append("| 样本 | 召回轨迹 |")
    lines.append("|---|---|")
    for s in SAMPLES:
        row = next(r for r in results["C RAG+大模型"] if r["id"] == s["id"])
        lines.append(f"| {s['id']} | {(row['trace'] or '').replace('|', '/')} |")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n✅ 报告已写入 {os.path.abspath(REPORT)}")

    print("\n=== 汇总 ===")
    for name, v in summary.items():
        m = v["m"]
        print(f"{name:18s} F1={m['f1']:.2f} 准确率={m['accuracy']:.0%} "
              f"平均{v['avg_ms']}ms {v['avg_tok']}tok {v['cost']:.5f}元/条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
