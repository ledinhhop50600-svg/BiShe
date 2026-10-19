"""生成「适配结果人工评分」页面。

用法（项目根目录）：
    python tools/make_human_review.py

输入：docs/eval/adaptation-results.json（由 eval_adaptation.py 生成）
输出：
    docs/eval/adaptation-review.html   可交互评分页面（推荐）
    docs/eval/adaptation-human-review.md  纯文字版（不想开浏览器时看）

设计原则：
  1. **先看原文，再看适配结果**，最后打分 —— 不让人对着空白表格猜；
  2. 每项都有 1-5 分的锚点说明（1 是什么、3 是什么、5 是什么）；
  3. **默认隐藏 LLM 评分**，避免先看 AI 分数被带偏；评完可切换显示作对照；
  4. 评分保存在浏览器本地，导出 CSV 后可交回项目继续算一致性。
"""
import html
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "docs", "eval", "adaptation-results.json")
OUT_HTML = os.path.join(ROOT, "docs", "eval", "adaptation-review.html")
OUT_MD = os.path.join(ROOT, "docs", "eval", "adaptation-human-review.md")
BACKEND = os.environ.get("ZIMEITI_BASE", "http://localhost:8080").rstrip("/")

PLATFORM_ORDER = {"xiaohongshu": 1, "wechat": 2, "douyin": 3}
PLATFORM_NAMES = {
    "xiaohongshu": "小红书", "wechat": "微信公众号", "douyin": "抖音",
    "weibo": "微博", "bilibili": "B站",
}


def call(path, method="GET", body=None, token=None, timeout=30):
    req = urllib.request.Request(
        BACKEND + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("satoken", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
    except Exception:
        return None


def login():
    body = call("/api/auth/login", "POST", {"username": "admin", "password": "123456"})
    return ((body or {}).get("data") or {}).get("tokenValue")


def fetch_sources(items):
    """结果 JSON 没带原文时，从后端补（只读，管理员）。"""
    need = {it["articleId"] for it in items
            if not it.get("sourceContent")}
    if not need:
        return
    token = login()
    if not token:
        print("[WARN] 后端未启动，无法补原文；页面会提示对照源文")
        return
    for aid in need:
        body = call(f"/api/article/{aid}", token=token)
        article = (body or {}).get("data") or {}
        for it in items:
            if it["articleId"] == aid:
                it["sourceTitle"] = it.get("sourceTitle") or article.get("title") or ""
                it["sourceContent"] = article.get("content") or ""
                it["sourceLen"] = len(it["sourceContent"])


HTML_SHELL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>适配结果人工评分</title>
<style>
  :root {
    --bg: #f5f7fb; --card: #ffffff; --line: #e5e7eb;
    --text: #1f2937; --muted: #6b7280; --primary: #2563eb;
    --ok-bg: #ecfdf5; --ok: #047857; --warn-bg: #fffbeb; --warn: #b45309;
    --bad-bg: #fef2f2; --bad: #b91c1c;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    line-height: 1.6;
  }
  header { max-width: 1240px; margin: 0 auto; padding: 28px 20px 8px; }
  h1 { margin: 0 0 6px; font-size: 26px; }
  .sub { margin: 0 0 14px; color: var(--muted); }
  .rubric {
    background: var(--card); border: 1px solid var(--line); border-radius: 10px;
    padding: 12px 16px; margin-bottom: 14px;
  }
  .rubric summary { cursor: pointer; font-weight: 600; color: var(--primary); }
  .rubric table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
  .rubric th, .rubric td { border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; }
  .rubric th { background: #f8fafc; }
  .toolbar {
    display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
    background: var(--card); border: 1px solid var(--line); border-radius: 10px;
    padding: 10px 16px; margin-bottom: 18px; font-size: 14px;
  }
  .toolbar label { display: flex; align-items: center; gap: 6px; color: var(--muted); }
  .toolbar .progress { margin-left: auto; font-weight: 600; color: var(--primary); }
  .toolbar button, .sticky button {
    border: 1px solid var(--line); background: #fff; border-radius: 8px;
    padding: 7px 14px; cursor: pointer; font-size: 14px;
  }
  .toolbar button:hover, .sticky button:hover { border-color: var(--primary); color: var(--primary); }
  main { max-width: 1240px; margin: 0 auto; padding: 0 20px 110px; }
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 18px 20px; margin-bottom: 18px;
  }
  .card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .card-title { font-size: 16px; font-weight: 600; }
  .badge {
    display: inline-block; background: #eff6ff; color: #1d4ed8; border-radius: 999px;
    padding: 2px 10px; font-size: 12px; margin-left: 6px;
  }
  .status { font-size: 12px; }
  .status .ok { color: var(--ok); background: var(--ok-bg); padding: 2px 8px; border-radius: 999px; }
  .status .warn { color: var(--warn); background: var(--warn-bg); padding: 2px 8px; border-radius: 999px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
  .pane h3 { margin: 0 0 6px; font-size: 13px; color: var(--muted); font-weight: 600; }
  .content {
    white-space: pre-wrap; word-break: break-word; font-size: 14px; line-height: 1.75;
    background: #f9fafb; border: 1px solid var(--line); border-radius: 8px;
    padding: 12px; max-height: 300px; overflow: auto;
  }
  .content.adapted { background: #f8fbff; }
  .adapted-title { font-weight: 600; margin-bottom: 8px; }
  .tag-list { margin-top: 8px; font-size: 12px; color: #4b5563; }
  .tag-list span { display: inline-block; background: #f1f5f9; border-radius: 6px; padding: 2px 8px; margin: 2px 4px 2px 0; }
  .scores { margin-top: 16px; border-top: 1px dashed var(--line); padding-top: 12px; }
  .score-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
  .score-label { width: 96px; font-size: 13px; font-weight: 600; }
  .radio-group { display: flex; gap: 6px; }
  .radio-group label {
    display: flex; align-items: center; justify-content: center; gap: 4px;
    min-width: 44px; border: 1px solid var(--line); border-radius: 8px;
    padding: 5px 9px; cursor: pointer; font-size: 13px; background: #fff;
  }
  .radio-group label:hover { border-color: var(--primary); }
  .radio-group input { margin: 0; }
  .anchor { color: var(--muted); font-size: 12px; }
  textarea {
    width: 100%; border: 1px solid var(--line); border-radius: 8px;
    padding: 9px 11px; font-size: 13px; font-family: inherit; margin-top: 6px;
    resize: vertical; min-height: 54px;
  }
  .llm {
    margin-top: 10px; font-size: 12px; color: var(--muted);
    background: #f8fafc; border: 1px dashed var(--line); border-radius: 8px; padding: 7px 10px;
  }
  .hidden { display: none; }
  .sticky {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 10;
    background: rgba(255,255,255,.96); border-top: 1px solid var(--line);
    box-shadow: 0 -4px 14px rgba(15,23,42,.06);
  }
  .sticky-inner {
    max-width: 1240px; margin: 0 auto; padding: 12px 20px;
    display: flex; align-items: center; gap: 16px;
  }
  .sticky .progress { color: var(--primary); font-weight: 600; }
  .sticky button.primary {
    margin-left: auto; background: var(--primary); color: #fff; border-color: var(--primary);
    padding: 9px 22px; font-weight: 600;
  }
  .sticky button.primary:hover { background: #1d4ed8; color: #fff; }
  .hint { color: var(--muted); font-size: 12px; }
  @media (max-width: 900px) {
    .grid { grid-template-columns: 1fr; }
    .score-label { width: 100%; }
  }
  @media print {
    body { background: #fff; }
    .toolbar, .sticky { display: none; }
    .card { break-inside: avoid; page-break-inside: avoid; }
  }
</style>
</head>
<body>
<header>
  <h1>适配结果人工评分</h1>
  <p class="sub">
    共 <b id="total">__TOTAL__</b> 条。每条先看「原文」，再看「适配结果」，然后凭第一印象给三项打 1-5 分。
    大约 10-15 分钟；不需要懂技术。
  </p>

  <details class="rubric" open>
    <summary>评分标准（先看这里）</summary>
    <table>
      <thead>
        <tr><th>分数</th><th>风格符合度</th><th>信息保留度</th><th>可读性</th></tr>
      </thead>
      <tbody>
        <tr><td><b>1</b></td><td>完全不像这个平台（比如公众号版本写得像微博）</td><td>大量信息丢失，或编造了原文没有的事实</td><td>语句不通、结构混乱，很难读</td></tr>
        <tr><td><b>2</b></td><td>明显不像，只有零星平台特征</td><td>丢了关键信息，或有明显编造</td><td>多处别扭，需要反复读</td></tr>
        <tr><td><b>3</b></td><td>一般，能看出是给这个平台写的，但不出彩</td><td>主要信息在，次要信息有出入</td><td>基本能读，偶尔卡顿</td></tr>
        <tr><td><b>4</b></td><td>比较像，符合平台习惯</td><td>核心信息完整，细节有小差异</td><td>通顺，结构清楚</td></tr>
        <tr><td><b>5</b></td><td>很像，可以直接发到这个平台</td><td>完整准确，没有编造</td><td>流畅、好读，段落/节奏合适</td></tr>
      </tbody>
    </table>
    <p class="hint">
      三条判断线：<b>像不像这个平台</b>（风格）、<b>有没有丢/编造信息</b>（保留）、
      <b>读起来顺不顺</b>（可读）。拿不准就给 3 分，不需要纠结。
    </p>
  </details>

  <div class="toolbar">
    <label><input type="checkbox" id="showLlm"> 显示 LLM 评分（建议全部评完再看，避免被带偏）</label>
    <button id="clear">清空重评</button>
    <span class="progress" id="progress">已完成 0 / __TOTAL__</span>
  </div>
</header>

<main id="cards"></main>

<footer class="sticky">
  <div class="sticky-inner">
    <span class="progress" id="progress2">已完成 0 / __TOTAL__</span>
    <span class="hint">评分自动保存在本浏览器；导出后把 CSV 放回 docs/eval/ 即可</span>
    <button class="primary" id="export">导出评分 CSV</button>
  </div>
</footer>

<script>
const DATA = __DATA__;
const STORAGE_KEY = 'adaptation-human-review-v1';
let state = {};
try { state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') || {}; } catch (e) { state = {}; }

function h(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined && text !== null) el.textContent = text;
  return el;
}

function itemKey(it) { return it.articleId + ':' + it.platformKey; }

function current(it) {
  return state[itemKey(it)] || { style: null, retention: null, readability: null, comment: '' };
}

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  updateProgress();
}

function complete(it) {
  const s = current(it);
  return s.style && s.retention && s.readability;
}

function updateProgress() {
  const done = DATA.items.filter(complete).length;
  const total = DATA.items.length;
  document.getElementById('progress').textContent = '已完成 ' + done + ' / ' + total;
  document.getElementById('progress2').textContent = '已完成 ' + done + ' / ' + total;
}

function makeRadioRow(it, field, label, low, high) {
  const row = h('div', 'score-row');
  row.appendChild(h('span', 'score-label', label));
  const group = h('div', 'radio-group');
  for (let v = 1; v <= 5; v++) {
    const lab = h('label');
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = field + '-' + itemKey(it);
    input.value = String(v);
    const s = current(it);
    if (s[field] === v) input.checked = true;
    input.addEventListener('change', () => {
      const next = current(it);
      next[field] = v;
      state[itemKey(it)] = next;
      save();
    });
    lab.appendChild(input);
    lab.appendChild(document.createTextNode(String(v)));
    group.appendChild(lab);
  }
  row.appendChild(group);
  row.appendChild(h('span', 'anchor', low + ' · ' + high));
  return row;
}

function render() {
  const root = document.getElementById('cards');
  root.innerHTML = '';
  DATA.items.forEach((it, idx) => {
    const s = current(it);
    const card = h('section', 'card');
    card.id = 'card-' + itemKey(it);

    const head = h('div', 'card-head');
    const left = h('div');
    const title = h('div', 'card-title');
    title.appendChild(document.createTextNode((idx + 1) + '/' + DATA.items.length + '  '));
    title.appendChild(document.createTextNode(it.articleTitle || ('稿件 #' + it.articleId)));
    title.appendChild(h('span', 'badge', it.platformName));
    left.appendChild(title);
    head.appendChild(left);

    const status = h('div', 'status');
    const f = h('span', it.formatPassed ? 'ok' : 'warn',
      it.formatPassed ? '格式自检：通过' : '格式自检：未通过');
    status.appendChild(f);
    status.appendChild(document.createTextNode(' '));
    status.appendChild(h('span', 'ok', '合规预检：' + (it.complianceText || '未判定')));
    head.appendChild(status);
    card.appendChild(head);

    const grid = h('div', 'grid');

    const p1 = h('div', 'pane');
    p1.appendChild(h('h3', null, '原文（' + (it.sourceLen || 0) + ' 字）'));
    p1.appendChild(h('div', 'content', it.sourceContent || '（原文未嵌入，请对照源文）'));
    grid.appendChild(p1);

    const p2 = h('div', 'pane');
    p2.appendChild(h('h3', null, '适配结果：' + it.platformName));
    p2.appendChild(h('div', 'adapted-title', it.title || '（无独立标题）'));
    p2.appendChild(h('div', 'content adapted', it.content || ''));
    const tagList = h('div', 'tag-list');
    (it.tags || []).forEach(t => tagList.appendChild(h('span', null, t)));
    if (!(it.tags || []).length) tagList.appendChild(h('span', null, '无话题标签'));
    p2.appendChild(tagList);
    if (it.formatIssues && it.formatIssues.length) {
      const issue = h('div', 'hint', '格式问题：' + it.formatIssues.join('；'));
      p2.appendChild(issue);
    }
    grid.appendChild(p2);
    card.appendChild(grid);

    const scores = h('div', 'scores');
    scores.appendChild(makeRadioRow(it, 'style', '风格符合度', '1 完全不像', '5 很像'));
    scores.appendChild(makeRadioRow(it, 'retention', '信息保留度', '1 大量丢失/编造', '5 完整准确'));
    scores.appendChild(makeRadioRow(it, 'readability', '可读性', '1 很难读', '5 流畅'));
    const ta = document.createElement('textarea');
    ta.placeholder = '点评（可选）：哪里扣分？比如"标题太夸张""漏了第 3 步"';
    ta.value = s.comment || '';
    ta.addEventListener('input', () => {
      const next = current(it);
      next.comment = ta.value;
      state[itemKey(it)] = next;
      save();
    });
    scores.appendChild(ta);
    card.appendChild(scores);

    if (it.llm && !it.llm.error) {
      const llm = h('div', 'llm hidden',
        'LLM 评分：风格 ' + it.llm.style + ' / 保留 ' + it.llm.retention + ' / 可读 ' + it.llm.readability +
        (it.llm.comment ? '｜' + it.llm.comment : ''));
      llm.dataset.llm = '1';
      card.appendChild(llm);
    }

    root.appendChild(card);
  });
  updateProgress();
  syncLlmVisibility();
}

function syncLlmVisibility() {
  const show = document.getElementById('showLlm').checked;
  document.querySelectorAll('[data-llm]').forEach(el => {
    el.classList.toggle('hidden', !show);
  });
}

function csvCell(v) {
  const s = String(v === null || v === undefined ? '' : v);
  if (/[",\r\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function exportCsv() {
  const missing = DATA.items.filter(it => !complete(it));
  if (missing.length) {
    alert('还有 ' + missing.length + ' 条没有打完整（三项都要选）。已跳到第一条未完成。');
    const el = document.getElementById('card-' + itemKey(missing[0]));
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  const header = ['稿件ID', '稿件标题', '目标平台', '风格_人工(1-5)', '保留_人工(1-5)',
    '可读_人工(1-5)', '人工点评', '评分时间'];
  const now = new Date().toLocaleString();
  const rows = DATA.items.map(it => {
    const s = current(it);
    return [it.articleId, it.articleTitle, it.platformName,
      s.style, s.retention, s.readability, s.comment || '', now];
  });
  const csv = '\ufeff' + [header, ...rows]
    .map(r => r.map(csvCell).join(',')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'adaptation-human-scores.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

document.getElementById('showLlm').addEventListener('change', syncLlmVisibility);
document.getElementById('export').addEventListener('click', exportCsv);
document.getElementById('clear').addEventListener('click', () => {
  if (!confirm('确定清空所有已填评分吗？')) return;
  state = {};
  localStorage.removeItem(STORAGE_KEY);
  render();
});

render();
</script>
</body>
</html>
"""


def build_md(items, meta):
    lines = []
    lines.append("# 适配结果人工评分（文字版）\n")
    lines.append(f"- 生成时间：{meta.get('generatedAt')}　批次：`{meta.get('runId')}`　模型：{meta.get('model')}")
    lines.append(f"- 共 {len(items)} 条；交互评分页面：`docs/eval/adaptation-review.html`\n")
    lines.append("## 评分标准\n")
    lines.append("| 分数 | 风格符合度 | 信息保留度 | 可读性 |")
    lines.append("|---|---|---|---|")
    lines.append("| 1 | 完全不像这个平台 | 大量信息丢失或编造 | 很难读 |")
    lines.append("| 2 | 明显不像 | 丢了关键信息/明显编造 | 多处别扭 |")
    lines.append("| 3 | 一般 | 主要信息在，次要信息有出入 | 基本能读 |")
    lines.append("| 4 | 比较像 | 核心信息完整，细节有小差异 | 通顺 |")
    lines.append("| 5 | 很像，可直接发 | 完整准确，无编造 | 流畅 |")
    lines.append("\n> 拿不准就给 3 分。**先评完再看 LLM 分数**（文末），避免被带偏。\n")

    for idx, it in enumerate(items, 1):
        lines.append(f"\n---\n\n## {idx}. #{it['articleId']} {it['articleTitle']} → {it['platformName']}\n")
        lines.append(f"**格式自检**：{'通过' if it['formatPassed'] else '未通过'}"
                     f"　**合规预检**：{it.get('complianceText') or '未判定'}\n")
        lines.append(f"### 原文（{it.get('sourceLen', 0)} 字）\n")
        lines.append(f"> {it.get('sourceTitle') or it['articleTitle']}\n")
        source = (it.get('sourceContent') or '（原文未嵌入）').replace("\n", "\n> ")
        lines.append("> " + source + "\n")
        lines.append("### 适配结果\n")
        lines.append(f"**标题**：{it.get('title') or '（无独立标题）'}\n")
        lines.append("**正文**：\n")
        body = (it.get('content') or '').strip()
        lines.append("\n".join("> " + line if line else ">" for line in body.split("\n")) + "\n")
        tags = " ".join(it.get("tags") or []) or "无"
        lines.append(f"**话题标签**：{tags}\n")
        if it.get("formatIssues"):
            lines.append(f"**格式问题**：{'；'.join(it['formatIssues'])}\n")
        lines.append("**我的评分**：风格 ____ / 信息保留 ____ / 可读性 ____　点评：________________\n")

    lines.append("\n---\n\n## LLM 评分（评完再看）\n")
    lines.append("| 稿件 | 平台 | 风格 | 保留 | 可读 | 点评 |")
    lines.append("|---|---|---|---|---|---|")
    for it in items:
        llm = it.get("llm") or {}
        if "error" in llm:
            lines.append(f"| #{it['articleId']} | {it['platformName']} | 调用失败 | - | - | - |")
        else:
            lines.append(f"| #{it['articleId']} | {it['platformName']} | {llm.get('style','-')} | "
                         f"{llm.get('retention','-')} | {llm.get('readability','-')} | "
                         f"{html.escape(str(llm.get('comment','')))} |")
    return "\n".join(lines)


def main():
    if not os.path.exists(RESULTS):
        print(f"[FAIL] 找不到 {RESULTS}，请先运行 tools/eval_adaptation.py")
        return 1
    with open(RESULTS, encoding="utf-8") as f:
        data = json.load(f)

    rows = [r for r in (data.get("results") or []) if "error" not in r]
    rows.sort(key=lambda r: (r["articleId"], PLATFORM_ORDER.get(r["platformKey"], 99)))
    fetch_sources(rows)

    items = []
    for r in rows:
        items.append({
            "articleId": r["articleId"],
            "articleTitle": r.get("articleTitle") or (r.get("sourceTitle") or ""),
            "sourceTitle": r.get("sourceTitle") or r.get("articleTitle") or "",
            "sourceContent": r.get("sourceContent") or "",
            "sourceLen": r.get("sourceLen") or len(r.get("sourceContent") or ""),
            "platformKey": r["platformKey"],
            "platformName": r.get("platformName") or PLATFORM_NAMES.get(r["platformKey"], r["platformKey"]),
            "title": r.get("title") or "",
            "content": r.get("content") or "",
            "tags": r.get("tags") or [],
            "formatPassed": bool(r.get("formatPassed")),
            "formatIssues": r.get("formatIssues") or [],
            "complianceText": r.get("complianceText") or "",
            "llm": r.get("llm"),
        })

    payload = {
        "meta": {
            "generatedAt": data.get("generatedAt"),
            "runId": data.get("runId"),
            "model": data.get("model"),
        },
        "items": items,
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html_text = (HTML_SHELL
                 .replace("__TOTAL__", str(len(items)))
                 .replace("__DATA__", data_json))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_text)

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(build_md(items, data))

    print(f"已生成：{os.path.relpath(OUT_HTML, ROOT)}（推荐用浏览器打开）")
    print(f"已生成：{os.path.relpath(OUT_MD, ROOT)}")
    print(f"共 {len(items)} 条。评分后点「导出评分 CSV」，把文件放回 docs/eval/。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
