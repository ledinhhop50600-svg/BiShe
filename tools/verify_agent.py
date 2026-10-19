"""阶段 4 验证：智能体服务是否按《Agent 接口契约 v1》工作。

用法：python tools/verify_agent.py
     默认 http://localhost:8001，可用环境变量 ZIMEITI_AGENT 覆盖。

验证内容：
  1. 健康检查返回供应商信息
  2. 违规内容 -> 返回分级结论、命中规则、违规片段与修改建议（契约必需字段齐全）
  3. 正常内容 -> riskLevel=0、passed=true
  4. 同一 requestId 再次请求 -> 命中回放缓存（replayed=true）
  5. 参数不合法 -> 400（契约规定，而非 FastAPI 默认的 422）
"""

import json
import os
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("ZIMEITI_AGENT", "http://localhost:8001").rstrip("/")

RULES = [
    {"code": "AD-001", "name": "绝对化用语", "category": "广告法",
     "content": "出现「国家级」「最高级」「最佳」「第一」「顶级」等绝对化表述",
     "source": "《中华人民共和国广告法》第九条", "suggestedLevel": 2},
    {"code": "AD-002", "name": "无法核实的价格承诺", "category": "广告法",
     "content": "出现「全网最低价」「史上最低」等无法核实的价格比较",
     "source": "《中华人民共和国广告法》第八条", "suggestedLevel": 2},
    {"code": "FB-001", "name": "功效承诺", "category": "虚假宣传",
     "content": "出现「三天见效」「一周白一个度」「永久有效」等具体效果承诺",
     "source": "《中华人民共和国广告法》第二十八条", "suggestedLevel": 2},
    {"code": "DR-001", "name": "站外引流", "category": "引流诱导",
     "content": "引导用户添加私人联系方式或到平台外交易",
     "source": "平台社区规范通用要求", "suggestedLevel": 2},
]


def call(path, method="GET", body=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}
    except Exception as e:
        return -1, {"error": f"{type(e).__name__}: {e}"}


def build(request_id, title, content, rules=RULES):
    return {
        "requestId": request_id,
        "articleId": 1,
        "triggerType": "POST_AUDIT",
        "targetPlatformKey": "local",
        "title": title,
        "content": content,
        "platform": {
            "platformKey": "local", "platformName": "本平台",
            "titleMaxLen": 60, "contentMaxLen": 5000,
            "tagRule": "可选，以 # 开头", "styleDesc": "长文，语气平和",
        },
        "rules": rules,
    }


def main():
    ok = True

    print("1) 健康检查")
    status, body = call("/health")
    print("   ", json.dumps(body, ensure_ascii=False))
    if body.get("status") != "ok":
        print("   [FAIL] 服务不健康")
        ok = False

    print("2) 违规内容")
    rid = str(uuid.uuid4())
    status, body = call("/api/agent/audit", "POST", build(
        rid, "全网最低价的美肤面膜，三天见效不是梦",
        "姐妹们这波可以冲，我们这款是全网最低价，国家级实验室研发，三天见效。需要的姐妹加我微信领取试用装。"))
    print("   HTTP =", status)
    required = ["contractVersion", "requestId", "riskLevel", "riskLevelText", "passed",
                "reason", "hitRules", "violations", "suggestion", "model", "usage", "durationMs", "trace"]
    missing = [k for k in required if k not in body]
    print("   缺失字段 =", missing or "无")
    print("   riskLevel =", body.get("riskLevel"), "| hitRules =", [r.get("code") for r in body.get("hitRules") or []])
    print("   违规片段 =", [v.get("fragment") for v in body.get("violations") or []])
    print("   理由 =", (body.get("reason") or "")[:60])
    if missing or body.get("riskLevel", 0) < 2 or not body.get("violations"):
        print("   [FAIL] 违规内容应给出分级结论与违规片段")
        ok = False

    print("3) 正常内容")
    status, body = call("/api/agent/audit", "POST", build(
        str(uuid.uuid4()), "小户型收纳的 5 个实用技巧", "很多人觉得家里地方小东西多，其实关键在于把垂直空间用起来。"))
    print("   riskLevel =", body.get("riskLevel"), "| passed =", body.get("passed"))
    if body.get("riskLevel") != 0 or body.get("passed") is not True:
        print("   [FAIL] 正常内容应为 riskLevel=0")
        ok = False

    print("4) 同一 requestId 再次请求（应命中回放）")
    rid2 = str(uuid.uuid4())
    req2 = build(rid2, "全网最低价的面膜", "三天见效，加我微信领取。")
    call("/api/agent/audit", "POST", req2)
    status, body = call("/api/agent/audit", "POST", req2)
    print("   replayed =", body.get("replayed"), "| riskLevel =", body.get("riskLevel"))
    if body.get("replayed") is not True:
        print("   [FAIL] 第二次请求应命中回放缓存")
        ok = False

    print("5) 参数不合法（缺 requestId）")
    bad = build("", "标题", "正文")
    status, body = call("/api/agent/audit", "POST", bad)
    print("   HTTP =", status, "| error =", body.get("error"), "| contractVersion =", body.get("contractVersion"))
    if status != 400:
        print("   [FAIL] 参数错误应返回 400")
        ok = False

    print("=" * 60)
    print("总体结果:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
