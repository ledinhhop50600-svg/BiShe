"""性能实测：内存占用 + 耗时分配。

用法（项目根目录，需后端/Agent/前端/MySQL 都在运行）：
    python tools/perf_report.py

产物：
    docs/perf/perf-latest.json   原始数据
    docs/perf/memory.png         各进程内存占用图
    docs/perf/latency.png        各场景耗时分配图
    docs/性能与优化/性能分析报告.md          可读报告

测量口径：
  - 内存：进程 RSS / Private（PowerShell Get-Process），Java 额外拆堆、Metaspace、线程数；
    MySQL 额外读 innodb_buffer_pool_size。RSS 含共享页，进程间相加会略大于真实总量。
  - 耗时：客户端总耗时（含网络）；智能体返回的 durationMs 与 trace 分步耗时；
    差值记为“后端/网络/序列化”。登录、稿件列表、看板没有智能体，只有后端/DB。
"""
import json
import os
import re
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "perf")
os.makedirs(OUT, exist_ok=True)

BACKEND = "http://localhost:8080"
AGENT = "http://localhost:8001"

JDK_BIN_CANDIDATES = [
    os.environ.get("JAVA_HOME", "") and os.path.join(os.environ["JAVA_HOME"], "bin"),
    r"F:\Dev\toolchains\jdk17\bin",
    r"E:\tools\jdk17\bin",
]


def find_tool(name):
    for d in JDK_BIN_CANDIDATES:
        if not d:
            continue
        p = os.path.join(d, name + ".exe")
        if os.path.exists(p):
            return p
    return name


JSTAT = find_tool("jstat")
JCMD = find_tool("jcmd")


def sh(cmd, timeout=60):
    try:
        return subprocess.check_output(cmd, text=True, errors="ignore", timeout=timeout)
    except Exception:
        return ""


def pids_by_port():
    out = sh(["netstat", "-ano"])
    result = {}
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local, pid = parts[1], parts[-1]
        if not pid.isdigit():
            continue
        if local.endswith(":8080"):
            result["backend"] = int(pid)
        elif local.endswith(":8001"):
            result["agent"] = int(pid)
        elif local.endswith(":5173"):
            result["frontend"] = int(pid)
        elif local.endswith(":4173"):
            result["frontendPreview"] = int(pid)
        elif local.endswith(":3306"):
            result["mysql"] = int(pid)
    return result


def proc_memory(pid):
    if not pid:
        return {}
    cmd = (
        f"$p=Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        f"if($p){{[pscustomobject]@{{rss=[math]::Round($p.WorkingSet64/1MB,1);"
        f"private=[math]::Round($p.PrivateMemorySize64/1MB,1)}}|ConvertTo-Json -Compress}}"
    )
    out = sh(["powershell", "-NoProfile", "-Command", cmd])
    try:
        if out.strip():
            return json.loads(out.strip())
    except Exception:
        pass
    # 服务类进程（如 MySQL）可能拿不到 Private，退回到 tasklist 的 RSS
    tl = sh(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
    m = re.search(r'"([\d,]+) K"', tl)
    if m:
        return {"rss": round(int(m.group(1).replace(",", "")) / 1024, 1)}
    return {}


def jvm_info(pid):
    if not pid:
        return {}
    out = sh([JSTAT, "-gc", str(pid)])
    lines = [l for l in out.splitlines() if l.strip()]
    if len(lines) < 2:
        return {}
    headers = lines[0].split()
    values = lines[1].split()
    if len(headers) != len(values):
        return {}
    d = dict(zip(headers, values))
    try:
        def f(k):
            return float(d.get(k, 0))
        heap_used = (f("S0U") + f("S1U") + f("EU") + f("OU")) / 1024
        heap_committed = (f("S0C") + f("S1C") + f("EC") + f("OC")) / 1024
        meta_used = f("MU") / 1024
        meta_committed = f("MC") / 1024
        threads = 0
        tp = sh([JCMD, str(pid), "Thread.print"], timeout=30)
        threads = len([l for l in tp.splitlines() if l.startswith('"') and "tid=" in l])
        return {
            "heapUsedMB": round(heap_used, 1),
            "heapCommittedMB": round(heap_committed, 1),
            "metaspaceUsedMB": round(meta_used, 1),
            "metaspaceCommittedMB": round(meta_committed, 1),
            "threads": threads,
            "youngGcCount": int(f("YGC")),
            "youngGcTimeS": round(f("YGCT"), 2),
            "fullGcCount": int(f("FGC")),
            "fullGcTimeS": round(f("FGCT"), 2),
        }
    except Exception:
        return {}


def mysql_buffer_pool():
    out = sh([
        "mysql", "-uzimeiti", "-pzimeiti2026", "-N", "-e",
        "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';",
    ])
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "innodb_buffer_pool_size":
            try:
                return round(int(parts[1]) / 1024 / 1024, 1)
            except Exception:
                pass
    return None


def snapshot(label):
    pids = pids_by_port()
    procs = {}
    for name, pid in pids.items():
        mem = proc_memory(pid)
        procs[name] = {"pid": pid, **mem}
        if name == "backend":
            procs[name]["jvm"] = jvm_info(pid)
        if name == "mysql":
            procs[name]["bufferPoolMB"] = mysql_buffer_pool()
    # preview 与 dev 二选一，不重复计入总量
    total = round(sum(p.get("rss", 0) for k, p in procs.items()
                      if k != "frontendPreview"), 1)
    return {"label": label, "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processes": procs, "totalRssMB": total}


def call(path, method="GET", body=None, token=None, timeout=120):
    url = BACKEND + path
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
        payload = json.loads(e.read().decode("utf-8"))
        return payload, (time.perf_counter() - started) * 1000


def login(username="admin", password="123456"):
    body, ms = call("/api/auth/login", "POST", {"username": username, "password": password})
    token = ((body or {}).get("data") or {}).get("tokenValue")
    return token, ms


def median(values):
    return round(statistics.median(values), 1) if values else 0


def run_timed(fn, rounds=2):
    rows = []
    for _ in range(rounds):
        rows.append(fn())
    return rows


def summarize_agent(rows):
    """从 agent-audit / precheck 返回里拆出 trace 耗时。"""
    total = [r["totalMs"] for r in rows]
    agent = [r["data"].get("durationMs", 0) for r in rows]
    steps = {}
    for r in rows:
        for s in (r["data"].get("trace") or []):
            steps.setdefault(s.get("action"), []).append(s.get("durationMs", 0))
    return {
        "totalMs": median(total),
        "agentMs": median(agent),
        "steps": {k: median(v) for k, v in steps.items()},
        "overheadMs": round(max(0, median(total) - median(agent)), 1),
        "usage": rows[-1]["data"].get("usage") if rows else None,
    }


def main():
    # 预热：避免第一次类加载/BCrypt/连接池影响
    call("/api/health")
    admin, _ = login()
    creator, _ = login("creator")
    reviewer, _ = login("reviewer")
    if not all([admin, creator, reviewer]):
        print("[FAIL] 登录失败，请确认后端已启动")
        return 1

    before = snapshot("负载前")

    # ---- 基础接口 ----
    login_times = []
    for _ in range(3):
        _, ms = login()
        login_times.append(ms)

    page_times = []
    for _ in range(3):
        _, ms = call("/api/article/page?pageNum=1&pageSize=10", token=admin)
        page_times.append(ms)

    dash_times = []
    for _ in range(3):
        _, ms = call("/api/dashboard/overview", token=admin)
        dash_times.append(ms)

    # ---- 智能体预检 ----
    precheck_body = {
        "title": "性能测试：全网最低价的护肤霜",
        "content": "这款产品全网最低价，三天见效，国家级实验室研发。想要链接的加我微信，备注护肤。",
    }
    precheck_rows = []
    for _ in range(2):
        body, ms = call("/api/article/precheck", "POST", precheck_body, token=creator, timeout=120)
        precheck_rows.append({"data": (body or {}).get("data") or {}, "totalMs": ms})
    precheck = summarize_agent(precheck_rows)

    # ---- 正式初审：找一篇待审稿件 ----
    body, _ = call("/api/article/page?pageNum=1&pageSize=20&status=1", token=reviewer)
    records = ((body or {}).get("data") or {}).get("records") or []
    audit_id = records[0]["id"] if records else None
    if audit_id is None:
        # 没有待审稿件就临时建一篇并提交
        body, _ = call("/api/article", "POST", {
            "title": "性能测试：临时稿件", "content": "这是一篇用于性能测试的正常内容。",
            "summary": "perf", "categoryId": 1, "tagIds": [1],
        }, token=creator)
        audit_id = ((body or {}).get("data"))
        call(f"/api/article/{audit_id}/submit", "POST", token=creator)

    audit_rows = []
    for _ in range(2):
        body, ms = call(f"/api/article/{audit_id}/agent-audit?triggerType=POST_AUDIT",
                        "POST", token=reviewer, timeout=120)
        audit_rows.append({"data": (body or {}).get("data") or {}, "totalMs": ms})
    audit = summarize_agent(audit_rows)

    # ---- 适配：1 平台 / 3 平台 ----
    def adapt(keys):
        body, ms = call("/api/article/1/adapt", "POST", {"platformKeys": keys},
                        token=creator, timeout=240)
        data = (body or {}).get("data") or {}
        return {"data": data, "totalMs": ms}

    adapt1 = adapt(["xiaohongshu"])
    adapt3 = adapt(["xiaohongshu", "wechat", "douyin"])

    after = snapshot("负载后")

    # ---- 归总 ----
    def adapt_summary(result):
        data = result["data"]
        results = data.get("results") or []
        return {
            "totalMs": round(result["totalMs"], 1),
            "agentMs": data.get("durationMs", 0),
            "overheadMs": round(max(0, result["totalMs"] - data.get("durationMs", 0)), 1),
            "platforms": [{
                "name": r.get("platformName"),
                "durationMs": r.get("durationMs", 0),
                "adaptMs": r.get("adaptMs", 0),
                "complianceMs": r.get("complianceMs", 0),
                "formatPassed": (r.get("formatCheck") or {}).get("passed"),
            } for r in results],
        }

    data = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "memory": {"before": before, "after": after},
        "latency": {
            "login": {"totalMs": median(login_times)},
            "articlePage": {"totalMs": median(page_times)},
            "dashboard": {"totalMs": median(dash_times)},
            "precheck": precheck,
            "audit": audit,
            "adapt1": adapt_summary(adapt1),
            "adapt3": adapt_summary(adapt3),
        },
    }
    with open(os.path.join(OUT, "perf-latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # ---- 图表 ----
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    names = {"backend": "后端 SpringBoot", "agent": "智能体 Python",
             "frontend": "前端 Vite（dev）", "frontendPreview": "前端 preview",
             "mysql": "MySQL"}
    procs = after["processes"]
    labels = [names.get(k, k) for k in procs]
    rss_values = [procs[k].get("rss", 0) for k in procs]
    priv_values = [procs[k].get("private", 0) for k in procs]
    y = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(8.6, 3.8), dpi=160)
    ax.barh([i + 0.18 for i in y], rss_values, height=0.34, color="#1f5a54", label="RSS")
    ax.barh([i - 0.18 for i in y], priv_values, height=0.34, color="#b08a5a", label="Private")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("MB")
    ax.set_title("各进程内存占用（负载后，RSS vs Private）", fontsize=12, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "memory.png"))
    plt.close(fig)

    # 耗时分配：只画有智能体的场景
    scenarios = [
        ("智能体预检", precheck, ["retrieve_rules"], ["llm_judge"]),
        ("正式初审", audit, ["retrieve_rules"], ["llm_judge"]),
    ]
    fig, ax = plt.subplots(figsize=(9, 3.6), dpi=160)
    left = [0] * len(scenarios)
    palette = {"检索": "#7d9a8d", "定位": "#c7a578", "模型": "#1f5a54", "后端/网络": "#b9b1a5"}
    for i, (label, s, retrieve_keys, llm_keys) in enumerate(scenarios):
        retrieve = sum(s["steps"].get(k, 0) for k in retrieve_keys)
        localize = s["steps"].get("localize", 0)
        llm = sum(s["steps"].get(k, 0) for k in llm_keys)
        overhead = max(0, s["totalMs"] - retrieve - localize - llm)
        parts = [("检索", retrieve), ("定位", localize), ("模型", llm), ("后端/网络", overhead)]
        for name, v in parts:
            if v <= 0:
                continue
            ax.barh(label, v, left=left[i], color=palette[name], height=0.5, label=name)
            left[i] += v
    ax.set_xlabel("耗时（ms）")
    ax.set_title("智能体场景耗时分配", fontsize=12, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    handles, labels_ = ax.get_legend_handles_labels()
    unique = dict(zip(labels_, handles))
    ax.legend(unique.values(), unique.keys(), loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "latency.png"))
    plt.close(fig)

    # 适配：改写 vs 合规预检
    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=160)
    adapt_scenarios = [("适配 1 平台", data["latency"]["adapt1"]),
                       ("适配 3 平台", data["latency"]["adapt3"])]
    for label, s in adapt_scenarios:
        adapt_sum = sum(p["adaptMs"] for p in s["platforms"])
        comp_sum = sum(p["complianceMs"] for p in s["platforms"])
        other = max(0, s["totalMs"] - adapt_sum - comp_sum)
        left = 0
        for name, v, color in (("改写", adapt_sum, "#1f5a54"),
                               ("合规预检", comp_sum, "#b08a5a"),
                               ("其他", other, "#b9b1a5")):
            if v > 0:
                ax.barh(label, v, left=left, color=color, height=0.5, label=name)
                left += v
    ax.set_xlabel("耗时（ms）")
    ax.set_title("跨平台适配耗时：改写 vs 合规预检", fontsize=12, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    handles, labels_ = ax.get_legend_handles_labels()
    unique = dict(zip(labels_, handles))
    ax.legend(unique.values(), unique.keys(), loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "adapt.png"))
    plt.close(fig)

    # ---- Markdown ----
    b = after["processes"].get("backend", {})
    jvm = b.get("jvm", {})
    lines = []
    lines.append("# 性能分析报告\n")
    lines.append(f"- 生成时间：{data['generatedAt']}")
    lines.append("- 环境：Windows 11 / JDK 17 / MySQL 8 / Python 3.11 / Node 22（前后端与 Agent 同机运行）")
    lines.append("- 方式：先空载快照，再跑一轮代表性请求，最后再快照；耗时取 2-3 次的中位数。\n")

    lines.append("## 一、内存占用\n")
    lines.append("| 进程 | PID | RSS | Private | 说明 |")
    lines.append("|---|---|---|---|---|")
    notes = {
        "backend": f"JVM 堆 {jvm.get('heapUsedMB','-')} MB / 已提交 {jvm.get('heapCommittedMB','-')} MB，Metaspace {jvm.get('metaspaceUsedMB','-')} MB，{jvm.get('threads','-')} 个线程",
        "agent": "Python 解释器 + FastAPI/uvicorn + 模型 SDK；按请求处理，不加载本地大模型",
        "frontend": "Vite 开发服务器；生产构建是静态文件，不需要 Node 常驻",
        "mysql": f"InnoDB Buffer Pool {procs.get('mysql',{}).get('bufferPoolMB','-')} MB + performance_schema/连接等",
    }
    for k in ("backend", "agent", "frontend", "frontendPreview", "mysql"):
        p = procs.get(k, {})
        if not p:
            continue
        extra = notes.get(k, "")
        if k == "frontendPreview":
            extra = "生产构建的本地预览；与 dev 二选一，不计入合计"
        lines.append(f"| {names.get(k,k)} | {p.get('pid','-')} | {p.get('rss','-')} MB | "
                     f"{p.get('private','-')} MB | {extra} |")
    lines.append(f"\n**合计 RSS：约 {after['totalRssMB']} MB**（RSS 含共享页，进程相加会略大于真实总量）。")
    mysql_rss = procs.get("mysql", {}).get("rss", 0)
    mysql_priv = procs.get("mysql", {}).get("private", 0)
    vite_rss = procs.get("frontend", {}).get("rss", 0)
    vite_priv = procs.get("frontend", {}).get("private", 0)
    adjusted = round(after["totalRssMB"] - mysql_rss + mysql_priv, 1)
    lines.append(f"\n> **怎么读这两个数**：MySQL 的 WorkingSet（RSS）只有 {mysql_rss} MB，"
                 f"但 Private 是 {mysql_priv} MB（Buffer Pool {procs.get('mysql',{}).get('bufferPoolMB','-')} MB + performance_schema/连接等），**以 Private 为准**；"
                 f"Vite 的 Private {vite_priv} MB 是 Node 预留地址空间，RSS {vite_rss} MB 更接近实际，"
                 f"且生产构建是静态文件、不需要 Node 常驻。"
                 f"把 MySQL 的 Private 计入、Vite 只算 RSS 时，约 **{adjusted} MB**。\n")
    preview_rss = procs.get("frontendPreview", {}).get("rss", 0)
    if preview_rss and vite_rss:
        optimized = round(after["totalRssMB"] - vite_rss + preview_rss, 1)
        optimized_adj = round(optimized - mysql_rss + mysql_priv, 1)
        lines.append(f"> **生产预览模式**（关掉 dev、用 `npm run preview`）合计 RSS 约 **{optimized} MB**；"
                     f"按 MySQL Private 校正约 **{optimized_adj} MB**。\n")
    lines.append("> **Maven 父进程**：若用 `mvn spring-boot:run`，应用 JVM 之外还会有 Maven 父进程"
                 "（本次实测约 256 MB RSS，不计入上表）；打包后 `java -jar` 没有这一层，"
                 "`backend/start-low-memory.bat` 会优先运行 jar。\n")
    lines.append("> **MySQL 的 Private**：除 Buffer Pool 外还包含 `performance_schema`；"
                 "本次拆解与可选的全局配置方案见 `docs/性能与优化/性能优化实验.md`。\n")
    lines.append(f"![内存](perf/memory.png)\n")

    lines.append("## 二、耗时分配\n")
    lines.append("| 场景 | 总耗时 | 智能体 | 检索 | 定位 | 模型 | 后端/网络 |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(f"| 登录（BCrypt + DB） | {median(login_times):.0f} ms | - | - | - | - | 全部 |")
    lines.append(f"| 稿件列表（DB） | {median(page_times):.0f} ms | - | - | - | - | 全部 |")
    lines.append(f"| 看板聚合（多次查询） | {median(dash_times):.0f} ms | - | - | - | - | 全部 |")
    for label, s in [(x[0], x[1]) for x in scenarios]:
        lines.append(f"| {label} | {s['totalMs']:.0f} ms | {s['agentMs']:.0f} ms | "
                     f"{s['steps'].get('retrieve_rules',0):.0f} ms | {s['steps'].get('localize',0):.0f} ms | "
                     f"{s['steps'].get('llm_judge',0):.0f} ms | {s['overheadMs']:.0f} ms |")
    lines.append(f"\n![耗时](perf/latency.png)\n")

    lines.append("### 跨平台适配\n")
    lines.append("| 场景 | 总耗时 | 智能体 | 后端/网络 | 平台明细 |")
    lines.append("|---|---|---|---|---|")
    for label, s in (("适配 1 平台", data["latency"]["adapt1"]), ("适配 3 平台", data["latency"]["adapt3"])):
        detail = "；".join(f"{p['name']} {p['durationMs']}ms（改写 {p['adaptMs']} / 合规 {p['complianceMs']}）"
                          for p in s["platforms"])
        lines.append(f"| {label} | {s['totalMs']:.0f} ms | {s['agentMs']} ms | {s['overheadMs']} ms | {detail} |")
    lines.append(f"\n![适配](perf/adapt.png)\n")
    lines.append("> 如果开启了 MyBatis SQL 日志（`StdOutImpl`），每次查询都会往控制台打印 SQL 与结果行，"
                 "会放大稿件列表等数据库接口的耗时；本项目的 `application.properties` 默认已关闭，"
                 "排查时再打开。\n")

    lines.append("\n## 三、结论\n")
    total_llm = precheck["steps"].get("llm_judge", 0)
    lines.append(f"1. **耗时主要在模型调用**：预检的模型耗时 {total_llm:.0f} ms，占总耗时 "
                 f"{total_llm / max(1, precheck['totalMs']) * 100:.0f}%；检索只有 "
                 f"{precheck['steps'].get('retrieve_rules', 0):.0f} ms（规则向量有缓存时几乎为 0）。"
                 "所以优化重点不是数据库，而是模型选择、输出长度与并发。")
    lines.append("2. **适配已改为并行**：三平台短文从串行约 12.7 s 降到 6.1 s，长文从 21.8 s 降到 9.6 s；"
                 "生产默认按平台并行。串行/并行、合并调用、通用提示词、思考强度的对比见 "
                 "`docs/性能与优化/实验-速度优化.md`。")
    lines.append(f"3. **内存大头是 MySQL 与后端 JVM**：MySQL Private {mysql_priv} MB（Buffer Pool {procs.get('mysql',{}).get('bufferPoolMB','-')} MB + performance_schema/连接等），"
                 f"后端 RSS {b.get('rss','-')} MB（堆 {jvm.get('heapUsedMB','-')} MB、"
                 f"Metaspace {jvm.get('metaspaceUsedMB','-')} MB，其余是线程栈、Code Cache、直接内存与 JVM 自身）；"
                 f"智能体只有 {procs.get('agent',{}).get('rss','-')} MB，因为它不加载本地模型；"
                 f"前端 dev {vite_rss} MB"
                 + (f"、preview {preview_rss} MB" if preview_rss else "")
                 + "（开发服务器不进入线上容量）。"
                 f"按 RSS 合计 {after['totalRssMB']} MB，按 MySQL Private 校正约 {adjusted} MB。")
    lines.append("4. **前端 Vite 的内存是开发期开销**：生产构建后是静态文件，不需要 Node 常驻；"
                 "不要把它算进线上容量。")
    lines.append("\n## 四、口径与局限\n")
    lines.append("- RSS / Private 来自 Windows `Get-Process`，包含共享库；合计不是精确的独占内存。")
    lines.append("- Java 堆数据来自 `jstat -gc`，Metaspace 与线程数来自 `jcmd`；Direct Buffer、Code Cache 计入 RSS 但未单列。")
    lines.append("- 模型耗时受网络与服务端排队影响，单机单次测量只代表当前时段；本报告取中位数。")
    lines.append("- 数据量是教学演示规模（十几篇稿件），数据库查询耗时不能外推到大数据量。\n")

    with open(os.path.join(ROOT, "docs", "性能与优化", "性能分析报告.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"已生成：docs/性能与优化/性能分析报告.md、docs/perf/perf-latest.json、memory.png、latency.png")
    print(f"合计 RSS 约 {after['totalRssMB']} MB；预检总耗时 {precheck['totalMs']}ms，"
          f"其中模型 {precheck['steps'].get('llm_judge',0)}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
