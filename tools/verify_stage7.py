"""阶段 7 验证脚本：人机协同闭环。

用法：python tools/verify_stage7.py [后端地址]
     前置条件：后端、智能体服务都在运行。

验证内容：
  1. 创作者投稿 → 审核员运行智能体初审（落 audit_record）
  2. 智能体判违规 → 审核员驳回（采纳）→ 创作者看到违规片段与建议
  3. 创作者修改后重提 → 旧结论被标记为过期
  4. 重新初审判通过 → 审核员改判驳回（必须填原因）→ audit_review 记为改判
  5. 无原因改判被拒绝
  6. 审核记录页返回记录与人工处理；统计的改判率 > 0
  7. 权限：创作者不能看审核记录页，也不能看他人稿件的审核反馈
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("ZIMEITI_BASE", "http://localhost:8080")).rstrip("/")


def call(path, method="GET", body=None, token=None, timeout=120):
    url = BASE + path
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
    _, body = call("/api/auth/login", "POST", {"username": username, "password": password})
    return ((body or {}).get("data") or {}).get("tokenValue")


def ok_of(body):
    return (body or {}).get("code") == 200


def create_and_submit(token, title, content):
    _, body = call("/api/article", "POST", {
        "title": title, "content": content, "summary": "阶段7验证",
        "categoryId": 1, "tagIds": [1],
    }, token=token)
    aid = (body or {}).get("data")
    if not aid:
        print("   [FAIL] 新建稿件失败：%s" % body)
        return None
    _, body = call(f"/api/article/{aid}/submit", "POST", token=token)
    if not ok_of(body):
        print("   [FAIL] 提交审核失败：%s" % body)
        return None
    return aid


def run_agent(token, aid):
    _, body = call(f"/api/article/{aid}/agent-audit?triggerType=POST_AUDIT", "POST",
                   token=token, timeout=90)
    return body or {}, (body or {}).get("data") or {}


def main():
    ok = True
    creator = login("creator")
    reviewer = login("reviewer")
    admin = login("admin")
    creator2 = login("creator2")
    print("令牌：creator=%s reviewer=%s admin=%s creator2=%s"
          % (bool(creator), bool(reviewer), bool(admin), bool(creator2)))
    if not all([creator, reviewer, admin, creator2]):
        print("[FAIL] 登录失败")
        return 1

    print("=" * 64)
    print("1) 创作者投一篇明确违规的稿件")
    aid = create_and_submit(
        creator, "阶段7验证：全网最低价的护肤霜（违规样本）",
        "这款护肤霜是全网最低价，三天见效，国家级实验室研发。想要的姐妹加我微信，备注护肤，我发你链接。")
    if not aid:
        return 1
    print("   稿件 id=%s，状态应为待审核" % aid)

    print("=" * 64)
    print("2) 审核员查看反馈（初审前）")
    _, body = call(f"/api/article/{aid}/audit-feedback", token=reviewer)
    data = (body or {}).get("data") or {}
    print("   初审前 record=%s" % (data.get("record") is not None))
    if data.get("record") is not None:
        print("   [FAIL] 尚未运行初审，不应有记录")
        ok = False

    print("=" * 64)
    print("3) 运行智能体初审")
    raw, result = run_agent(reviewer, aid)
    print("   agentFailed=%s riskLevel=%s（%s）recordId=%s"
          % (result.get("agentFailed"), result.get("riskLevel"),
             result.get("riskLevelText"), result.get("auditRecordId")))
    if result.get("agentFailed") or result.get("auditRecordId") is None:
        print("   [FAIL] 初审失败：%s" % (result.get("message") or raw))
        return 1
    if (result.get("riskLevel") or 0) < 2:
        print("   [FAIL] 明确违规样本应判违规及以上")
        ok = False
    violations = result.get("violations") or []
    print("   违规片段 %d 处：%s" % (len(violations), [v.get("fragment") for v in violations]))
    if not violations:
        print("   [FAIL] 应有违规片段")
        ok = False

    _, body = call(f"/api/article/{aid}/audit-feedback", token=reviewer)
    data = (body or {}).get("data") or {}
    record = data.get("record") or {}
    print("   反馈读取：risk=%s stale=%s violations=%d"
          % (record.get("riskLevel"), record.get("stale"), len(record.get("violations") or [])))
    if record.get("id") is None or record.get("stale") is not False:
        print("   [FAIL] 初审记录读取异常")
        ok = False

    print("=" * 64)
    print("4) 审核员驳回（与智能体建议一致 → 采纳）")
    _, body = call(f"/api/article/{aid}/review", "PUT",
                   {"action": "reject", "reason": "命中绝对化用语、功效承诺与站外引流，请删除后重提。"},
                   token=reviewer)
    print("   review -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        print("   [FAIL] 驳回失败")
        ok = False

    _, body = call(f"/api/article/{aid}/audit-feedback", token=creator)
    data = (body or {}).get("data") or {}
    review = data.get("review") or {}
    print("   创作者看到的处理：%s（最终 %s）%s"
          % (review.get("actionText"), review.get("finalLevelText"), review.get("remark")))
    if review.get("actionText") != "采纳":
        print("   [FAIL] 智能体判违规 + 审核员驳回，应记为采纳")
        ok = False

    print("=" * 64)
    print("5) 创作者修改后重新提交")
    _, body = call(f"/api/article/{aid}", token=creator)
    article = (body or {}).get("data") or {}
    clean = ("周末去公园走了走，看到很多人在放风筝。春天的风不大不小，正好适合。"
             "回家路上买了两斤草莓，洗干净放在玻璃碗里，孩子一口气吃了半碗。"
             "普通的一天，记录下来。")
    _, body = call("/api/article", "PUT", {
        "id": aid, "title": "阶段7验证：修改后的正常生活记录",
        "content": clean, "summary": "修改后重提", "categoryId": 1, "tagIds": [1],
    }, token=creator)
    print("   修改 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        print("   [FAIL] 修改失败")
        ok = False
    _, body = call(f"/api/article/{aid}/submit", "POST", token=creator)
    print("   重提 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        print("   [FAIL] 重提失败")
        ok = False

    _, body = call(f"/api/article/{aid}/audit-feedback", token=reviewer)
    data = (body or {}).get("data") or {}
    record = data.get("record") or {}
    print("   重提后旧记录 stale=%s，旧审核意见已隐藏=%s"
          % (record.get("stale"), data.get("review") is None))
    if record.get("stale") is not True:
        print("   [FAIL] 稿件修改后旧结论应标记过期")
        ok = False

    print("=" * 64)
    print("6) 重新初审（修改后的正常内容）")
    raw, result = run_agent(reviewer, aid)
    level = result.get("riskLevel")
    print("   agentFailed=%s riskLevel=%s（%s）"
          % (result.get("agentFailed"), level, result.get("riskLevelText")))
    if result.get("agentFailed"):
        print("   [FAIL] 重新初审失败")
        return 1
    if level != 0:
        print("   [WARN] 正常内容未判通过（level=%s），继续验证改判流程" % level)

    print("=" * 64)
    print("7) 改判：智能体说通过，审核员驳回（原因必填）")
    _, body = call(f"/api/article/{aid}/review", "PUT",
                   {"action": "reject", "reason": ""}, token=reviewer)
    print("   无原因改判 -> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 无原因改判不应成功")
        ok = False

    _, body = call(f"/api/article/{aid}/review", "PUT",
                   {"action": "reject", "reason": "智能体认为通过，但人工判断内容与标题不符，退回修改。"},
                   token=reviewer)
    print("   带原因改判 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        print("   [FAIL] 带原因改判应成功")
        ok = False

    _, body = call(f"/api/article/{aid}/audit-feedback", token=reviewer)
    data = (body or {}).get("data") or {}
    review = data.get("review") or {}
    print("   处理记录：%s（最终 %s）" % (review.get("actionText"), review.get("finalLevelText")))
    if review.get("actionText") != "改判":
        print("   [FAIL] 应记为改判")
        ok = False

    print("=" * 64)
    print("8) 审核记录页与统计")
    _, body = call("/api/audit-record/page?pageNum=1&pageSize=10", token=admin)
    page = (body or {}).get("data") or {}
    rows = page.get("records") or []
    print("   管理员看到 %d 条记录，示例：%s | %s | %s"
          % (len(rows), rows[0].get("articleTitle") if rows else "-",
             rows[0].get("riskLevelText") if rows else "-",
             rows[0].get("reviewActionText") if rows else "-"))
    if not rows:
        print("   [FAIL] 审核记录页应有数据")
        ok = False
    if not any(r.get("reviewActionText") == "改判" for r in rows):
        print("   [FAIL] 记录页应能看到改判记录")
        ok = False

    _, body = call("/api/audit-record/page?pageNum=1&pageSize=10&onlyOverride=true", token=reviewer)
    overrides = ((body or {}).get("data") or {}).get("records") or []
    print("   只看改判：%d 条" % len(overrides))
    if not overrides:
        print("   [FAIL] 只看改判应有数据")
        ok = False

    _, body = call("/api/audit-record/stats", token=reviewer)
    stats = (body or {}).get("data") or {}
    print("   统计：记录 %s，采纳 %s，改判 %s，人工 %s，改判率 %s%%"
          % (stats.get("recordCount"), stats.get("adoptCount"), stats.get("overrideCount"),
             stats.get("manualCount"), stats.get("overrideRate")))
    if (stats.get("overrideCount") or 0) < 1 or (stats.get("overrideRate") or 0) <= 0:
        print("   [FAIL] 改判统计不正确")
        ok = False

    print("=" * 64)
    print("9) 权限")
    _, body = call("/api/audit-record/page", token=creator)
    print("   创作者看审核记录页 -> code=%s（期望 403）" % (body or {}).get("code"))
    if (body or {}).get("code") != 403:
        print("   [FAIL] 创作者不应能看审核记录")
        ok = False
    _, body = call(f"/api/article/{aid}/audit-feedback", token=creator2)
    print("   他人看审核反馈 -> code=%s（期望 403）" % (body or {}).get("code"))
    if (body or {}).get("code") != 403:
        print("   [FAIL] 不应能看他人稿件的反馈")
        ok = False

    print("=" * 64)
    print("结论：%s" % ("全部通过" if ok else "存在失败项，见上方 [FAIL]"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
