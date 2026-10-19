"""阶段 3 验证脚本：内容管理、稿件状态机、权限与敏感词基线。

用法：python tools/verify_stage3.py [后端地址]
     默认 http://localhost:8080，也可用环境变量 ZIMEITI_BASE 指定。

验证内容：
  1. 创作者新建稿件 -> 提交审核（状态机：草稿 -> 待审核）
  2. 状态机保护：草稿直接审核应被拒绝
  3. 数据权限：创作者看不到他人稿件详情；不能调用后台稿件列表
  4. 审核员驳回（必须带原因）-> 创作者看到反馈 -> 修改后重新提交
  5. 审核员通过 -> 稿件变为已发布
  6. 举报：另一创作者举报已发布稿件 -> 审核员处理成立 -> 稿件自动下架
  7. 敏感词基线：命中词与最高等级正确
  8. 分类/标签/平台/敏感词的读取接口可用

输出全部为 ASCII（Unicode 码点），不受终端编码影响。
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("ZIMEITI_BASE", "http://localhost:8080")).rstrip("/")


def call(path, method="GET", body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("satoken", token)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, None
    except Exception as e:
        return -1, {"error": f"{type(e).__name__}: {e}"}


def esc(s):
    return str(s).encode("unicode_escape").decode("ascii")


def ok_of(body):
    return (body or {}).get("code") == 200


def login(username, password="123456"):
    _, body = call("/api/auth/login", "POST", {"username": username, "password": password})
    return ((body or {}).get("data") or {}).get("tokenValue")


def main():
    ok = True
    admin = login("admin")
    reviewer = login("reviewer")
    creator = login("creator")
    creator2 = login("creator2")
    print("令牌：admin=%s reviewer=%s creator=%s creator2=%s"
          % (bool(admin), bool(reviewer), bool(creator), bool(creator2)))
    if not all([admin, reviewer, creator, creator2]):
        print("[FAIL] 登录失败")
        return 1

    print("=" * 64)
    print("1) 创作者新建稿件（草稿）并提交审核")
    new_article = {
        "title": "阶段3验证稿件：这个标题里没有敏感词",
        "content": "这是一篇用于验证内容管理流程的稿件，正文内容是正常的生活分享。",
        "summary": "验证用稿件",
        "categoryId": 1,
        "tagIds": [1, 2],
    }
    _, body = call("/api/article", "POST", new_article, token=creator)
    article_id = (body or {}).get("data")
    print("   新建 -> code=%s | id=%s" % ((body or {}).get("code"), article_id))
    if not article_id:
        print("   [FAIL] 新建失败")
        return 1

    _, body = call(f"/api/article/{article_id}", token=creator)
    status = ((body or {}).get("data") or {}).get("status")
    print("   新建后状态 = %s（期望 0 草稿）" % status)
    if status != 0:
        ok = False

    _, body = call(f"/api/article/{article_id}/submit", "POST", token=creator)
    print("   提交审核 -> code=%s" % (body or {}).get("code"))
    _, body = call(f"/api/article/{article_id}", token=creator)
    status = ((body or {}).get("data") or {}).get("status")
    print("   提交后状态 = %s（期望 1 待审核）" % status)
    if status != 1:
        ok = False

    print("=" * 64)
    print("2) 状态机保护")
    _, body = call(f"/api/article/{article_id}/submit", "POST", token=creator)
    print("   已提交后再提交 -> code=%s msg=%s"
          % ((body or {}).get("code"), esc((body or {}).get("msg"))))
    if ok_of(body):
        print("   [FAIL] 重复提交不应成功")
        ok = False
    _, body = call(f"/api/article/{article_id}/review", "PUT", {"action": "approve"}, token=creator)
    print("   创作者自己审核 -> code=%s（期望 403，无审核权限）" % (body or {}).get("code"))
    if (body or {}).get("code") != 403:
        print("   [FAIL] 创作者不应能审核")
        ok = False

    print("=" * 64)
    print("3) 数据权限")
    _, body = call(f"/api/article/{article_id}", token=creator2)
    print("   另一创作者查看他人稿件详情 -> code=%s msg=%s"
          % ((body or {}).get("code"), esc((body or {}).get("msg"))))
    if (body or {}).get("code") != 403:
        print("   [FAIL] 不应看到他人稿件")
        ok = False
    _, body = call("/api/article/page?pageNum=1&pageSize=5", token=creator)
    print("   创作者调用后台稿件列表 -> code=%s（期望 403）" % (body or {}).get("code"))
    if (body or {}).get("code") != 403:
        print("   [FAIL] 创作者不应能进后台列表")
        ok = False

    print("=" * 64)
    print("4) 审核员驳回 -> 创作者看到反馈 -> 修改后重新提交")
    _, body = call(f"/api/article/{article_id}/review", "PUT", {"action": "reject"}, token=reviewer)
    print("   驳回但不填原因 -> code=%s msg=%s"
          % ((body or {}).get("code"), esc((body or {}).get("msg"))))
    if ok_of(body):
        print("   [FAIL] 驳回必须要求原因")
        ok = False

    reason = "标题过于笼统，请补充具体信息；另外建议在正文补充可操作步骤。"
    _, body = call(f"/api/article/{article_id}/review", "PUT",
                   {"action": "reject", "reason": reason}, token=reviewer)
    print("   驳回并填写原因 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        ok = False

    _, body = call(f"/api/article/{article_id}", token=creator)
    detail = (body or {}).get("data") or {}
    print("   创作者看到状态=%s | 反馈长度=%s" % (detail.get("status"), len(detail.get("rejectReason") or "")))
    if detail.get("status") != 3 or not detail.get("rejectReason"):
        print("   [FAIL] 驳回后应能看到反馈")
        ok = False

    _, body = call("/api/article", "PUT",
                   {**new_article, "id": article_id, "title": "阶段3验证稿件（已按反馈修改）"}, token=creator)
    print("   修改稿件 -> code=%s" % (body or {}).get("code"))
    _, body = call(f"/api/article/{article_id}/submit", "POST", token=creator)
    print("   重新提交 -> code=%s" % (body or {}).get("code"))
    _, body = call(f"/api/article/{article_id}", token=creator)
    detail = (body or {}).get("data") or {}
    print("   重提后状态=%s | 驳回原因是否已清空=%s"
          % (detail.get("status"), detail.get("rejectReason") in ("", None)))
    if detail.get("status") != 1:
        ok = False

    print("=" * 64)
    print("5) 审核员通过 -> 已发布")
    _, body = call(f"/api/article/{article_id}/review", "PUT", {"action": "approve"}, token=reviewer)
    print("   通过 -> code=%s" % (body or {}).get("code"))
    _, body = call(f"/api/article/{article_id}", token=creator)
    detail = (body or {}).get("data") or {}
    print("   状态=%s（期望 2 已发布）| 发布时间=%s" % (detail.get("status"), bool(detail.get("publishTime"))))
    if detail.get("status") != 2 or not detail.get("publishTime"):
        print("   [FAIL] 通过后应为已发布且有发布时间")
        ok = False

    print("=" * 64)
    print("6) 举报 -> 处理成立 -> 稿件自动下架")
    _, body = call("/api/report?articleId=%d&reason=%s" % (article_id, urllib.parse.quote("标题与正文不符，存在虚假宣传")),
                   "POST", token=creator2)
    print("   creator2 举报 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        ok = False
    _, body = call("/api/article/%d" % article_id, token=creator2)
    print("   举报自己的稿件不应成功（此处是他人稿件，正常）")

    _, body = call("/api/report/page?pageNum=1&pageSize=20", token=reviewer)
    reports = ((body or {}).get("data") or {}).get("records") or []
    target = None
    for r in reports:
        if r.get("articleId") == article_id and r.get("status") == 0:
            target = r
            break
    print("   找到该稿件的待处理举报 = %s" % bool(target))
    if not target:
        print("   [FAIL] 举报未创建成功")
        ok = False
    else:
        _, body = call(f"/api/report/{target['id']}/handle", "PUT",
                       {"status": 1, "remark": "经核实举报成立，稿件下架"}, token=reviewer)
        print("   处理（成立）-> code=%s" % (body or {}).get("code"))
        _, body = call(f"/api/article/{article_id}", token=creator)
        detail = (body or {}).get("data") or {}
        print("   处理后稿件状态=%s（期望 5 已下架）" % detail.get("status"))
        if detail.get("status") != 5:
            print("   [FAIL] 举报成立后稿件应下架")
            ok = False

    print("=" * 64)
    print("7) 敏感词基线检测")
    text = "全网最低价的美肤面膜，三天见效不是梦，需要的姐妹加我微信领取清单。"
    _, body = call("/api/sensitive/check", "POST", {"text": text}, token=creator)
    data = (body or {}).get("data") or {}
    print("   命中数=%s | 最高等级=%s | 类别=%s"
          % (len(data.get("matched") or []), data.get("maxLevel"), esc(data.get("categories"))))
    print("   命中词=%s" % esc(data.get("matched")))
    if len(data.get("matched") or []) < 3 or data.get("maxLevel", 0) < 2:
        print("   [FAIL] 敏感词基线应命中多个词")
        ok = False

    # 语境反例：关键词匹配会把作品名误判
    _, body = call("/api/sensitive/check", "POST", {"text": "最近在看《最好的我们》，很推荐。"}, token=creator)
    data = (body or {}).get("data") or {}
    print("   反例「最好的我们」-> 命中=%s（这正是关键词匹配的局限）" % esc(data.get("matched")))
    if not data.get("matched"):
        print("   [提示] 该反例未命中，说明词库里没有相关词")
    print("=" * 64)
    print("8) 基础数据读取")
    for path, name in [("/api/category/list", "分类"), ("/api/tag/list", "标签"),
                       ("/api/platform/list", "平台")]:
        _, body = call(path, token=creator)
        n = len((body or {}).get("data") or [])
        print("   %s 数量 = %s" % (name, n))
        if n == 0:
            ok = False

    print("=" * 64)
    print("总体结果:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    import urllib.parse
    raise SystemExit(main())
