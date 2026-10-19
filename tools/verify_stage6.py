"""阶段 6 验证脚本：跨平台内容适配。

用法：python tools/verify_stage6.py [后端地址]
     默认 http://localhost:8080，也可用环境变量 ZIMEITI_BASE 指定。
     前置条件：后端、智能体服务都在运行（start.bat 或手动启动）。

验证内容：
  1. 平台清单可读，外部平台可作适配目标
  2. 生成适配：一次两个平台，结果顺序与请求一致，含格式自检与合规预检
  3. 格式自检字段完整（字数、标签数、是否通过、问题列表）
  4. 适配记录落库：版本号从 1 开始，重复生成递增
  5. 数据权限：另一创作者不能适配他人稿件
  6. 参数校验：不能把「本平台」当适配目标；不能一次超过 5 个平台
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("ZIMEITI_BASE", "http://localhost:8080")).rstrip("/")


def call(path, method="GET", body=None, token=None, timeout=180):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
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
    _, body = call("/api/auth/login", "POST", {"username": username, "password": password})
    return ((body or {}).get("data") or {}).get("tokenValue")


def ok_of(body):
    return (body or {}).get("code") == 200


def main():
    ok = True
    creator = login("creator")
    creator2 = login("creator2")
    admin = login("admin")
    print("令牌：creator=%s creator2=%s admin=%s" % (bool(creator), bool(creator2), bool(admin)))
    if not all([creator, creator2, admin]):
        print("[FAIL] 登录失败")
        return 1

    print("=" * 64)
    print("1) 平台清单")
    _, body = call("/api/platform/list", token=creator)
    platforms = (body or {}).get("data") or []
    external = {p["platformKey"]: p for p in platforms if p.get("status") == 1 and p["platformKey"] != "local"}
    print("   可用外部平台：%s" % "、".join(f"{p['platformName']}({k})" for k, p in external.items()))
    if not {"xiaohongshu", "weibo"}.issubset(external):
        print("   [FAIL] 缺少小红书或微博配置")
        return 1
    for key in ("xiaohongshu", "weibo"):
        p = external[key]
        print("   %s：标题上限 %s，正文上限 %s，标签规则 %s"
              % (p["platformName"], p["titleMaxLen"], p["contentMaxLen"], p["tagRule"]))

    print("=" * 64)
    print("2) 选一篇自己的稿件")
    _, body = call("/api/article/my?pageNum=1&pageSize=50", token=creator)
    mine = ((body or {}).get("data") or {}).get("records") or []
    if not mine:
        print("[FAIL] 该账号没有稿件，无法验证适配")
        return 1
    article = next((a for a in mine if a.get("status") == 2), mine[0])
    article_id = article["id"]
    print("   稿件 id=%s 标题=%s 状态=%s" % (article_id, article["title"], article.get("status")))

    print("=" * 64)
    print("3) 参数校验与数据权限")
    _, body = call(f"/api/article/{article_id}/adapt", "POST", {"platformKeys": ["local"]}, token=creator)
    print("   目标选「本平台」-> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 本平台不应作为适配目标")
        ok = False

    _, body = call(f"/api/article/{article_id}/adapt", "POST",
                   {"platformKeys": ["xiaohongshu", "weibo", "douyin", "wechat", "bilibili", "local"]},
                   token=creator)
    print("   一次选 6 个平台 -> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 超过 5 个平台应被拒绝")
        ok = False

    _, body = call(f"/api/article/{article_id}/adapt", "POST",
                   {"platformKeys": ["xiaohongshu"]}, token=creator2)
    print("   另一创作者适配他人稿件 -> code=%s msg=%s"
          % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 不应能适配他人稿件")
        ok = False

    print("=" * 64)
    print("4) 生成适配：小红书 + 微博（会调用真实模型，约 5-15 秒）")
    targets = ["xiaohongshu", "weibo"]
    _, body = call(f"/api/article/{article_id}/adapt", "POST", {"platformKeys": targets}, token=creator)
    data = (body or {}).get("data") or {}
    print("   code=%s agentFailed=%s model=%s duration=%sms"
          % ((body or {}).get("code"), data.get("agentFailed"), data.get("model"), data.get("durationMs")))
    if not ok_of(body) or data.get("agentFailed"):
        print("   [FAIL] 适配失败：%s" % (data.get("message") or data.get("error")))
        return 1

    results = data.get("results") or []
    print("   返回 %d 个平台，顺序：%s" % (len(results), [r.get("platformKey") for r in results]))
    if [r.get("platformKey") for r in results] != targets:
        print("   [FAIL] 结果顺序与请求不一致")
        ok = False
    for r in results:
        fmt = r.get("formatCheck") or {}
        comp = r.get("compliance") or {}
        print("-" * 60)
        print("   [%s] 标题：%s" % (r.get("platformName"), r.get("title") or "（无独立标题）"))
        print("   正文（前 120 字）：%s" % (r.get("content") or "")[:120].replace("\n", " "))
        print("   标签：%s" % " ".join(r.get("tags") or []))
        print("   格式自检：passed=%s 标题 %s 字 / 正文 %s 字 / 标签 %s 个"
              % (fmt.get("passed"), fmt.get("titleLen"), fmt.get("contentLen"), fmt.get("tagCount")))
        if fmt.get("issues"):
            print("     问题：%s" % "；".join(fmt["issues"]))
        print("   合规预检：%s | %s" % (comp.get("riskLevelText"), (comp.get("reason") or "")[:160]))
        if not all(k in fmt for k in ("passed", "titleLen", "contentLen", "tagCount", "issues")):
            print("   [FAIL] 格式自检字段不完整")
            ok = False
        if "riskLevel" not in comp:
            print("   [FAIL] 合规预检缺少 riskLevel")
            ok = False

    print("=" * 64)
    print("5) 适配记录落库与版本号")
    _, body = call(f"/api/article/{article_id}/adaptations", token=creator)
    rows = (body or {}).get("data") or []
    print("   共 %d 条记录" % len(rows))
    for row in rows[:6]:
        print("   v%s | %s | %s | %s"
              % (row.get("version"), row.get("platformName"), row.get("formatCheck"),
                 (row.get("complianceCheck") or "")[:60]))
    latest = {r["platformKey"]: r["version"] for r in rows}
    if latest.get("xiaohongshu") != 1 or latest.get("weibo") != 1:
        print("   [FAIL] 首次适配的版本号应为 1")
        ok = False

    print("   再生成一次（验证版本号递增）...")
    _, body = call(f"/api/article/{article_id}/adapt", "POST", {"platformKeys": targets}, token=creator)
    if not ok_of(body):
        print("   [FAIL] 第二次生成失败")
        ok = False
    _, body = call(f"/api/article/{article_id}/adaptations", token=creator)
    rows = (body or {}).get("data") or []
    latest = {}
    for r in rows:
        latest[r["platformKey"]] = max(latest.get(r["platformKey"], 0), r.get("version") or 0)
    print("   最新版本：%s（期望小红书/微博都为 2）" % latest)
    if latest.get("xiaohongshu") != 2 or latest.get("weibo") != 2:
        print("   [FAIL] 版本号未递增")
        ok = False

    print("=" * 64)
    print("6) 管理员可适配任意稿件")
    _, body = call(f"/api/article/{article_id}/adapt", "POST",
                   {"platformKeys": ["douyin"]}, token=admin)
    print("   管理员适配 -> code=%s agentFailed=%s"
          % ((body or {}).get("code"), ((body or {}).get("data") or {}).get("agentFailed")))
    if not ok_of(body):
        print("   [FAIL] 管理员应可适配")
        ok = False

    print("=" * 64)
    print("结论：%s" % ("全部通过" if ok else "存在失败项，见上方 [FAIL]"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
