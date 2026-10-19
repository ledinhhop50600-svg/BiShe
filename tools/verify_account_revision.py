"""待办收尾验证：D1 注册/个人中心 + D3 已发布稿件编辑后重审。

用法：python tools/verify_account_revision.py [后端地址]
     前置条件：后端在运行；注册/改密不需要智能体，D3 的审核也不需要调用模型。

覆盖：
  1. 验证码（算式）：正确通过、错误被拒、一次性使用
  2. 注册：默认创作者角色、重复账号被拒、两次密码不一致被拒
  3. 个人中心：资料修改、非法邮箱被拒
  4. 改密：原密码错误被拒；正确后旧令牌失效、新密码可登录
  5. D3：已发布稿件编辑后回到待审核，审核期间从内容广场消失；下架稿件同样可编辑重审
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("ZIMEITI_BASE", "http://localhost:8080")).rstrip("/")


def call(path, method="GET", body=None, token=None, timeout=60):
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


def new_captcha():
    _, body = call("/api/auth/captcha")
    data = (body or {}).get("data") or {}
    m = re.search(r"(\d+)\s*\+\s*(\d+)", data.get("question", ""))
    if not m:
        return None, None
    return data.get("captchaId"), str(int(m.group(1)) + int(m.group(2)))


def register_payload(username, answer, password="abc12345", confirm=None, nickname="验证用户"):
    return {
        "username": username,
        "password": password,
        "confirmPassword": confirm if confirm is not None else password,
        "nickname": nickname,
        "captchaId": None,  # 由调用方填
        "captchaAnswer": answer,
    }


def main():
    ok = True
    suffix = str(int(time.time() * 1000))[-8:]
    username = f"qa{suffix}"
    print("测试账号：", username)

    print("=" * 64)
    print("1) 验证码")
    cid, answer = new_captcha()
    print("   题目答案应为：", answer, "| captchaId 存在：", bool(cid))
    if not cid:
        print("   [FAIL] 无法获取验证码")
        return 1

    # 先用错误答案注册（会消耗验证码）
    payload = register_payload(username, "9999")
    payload["captchaId"] = cid
    _, body = call("/api/auth/register", "POST", payload)
    print("   错误验证码注册 -> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 错误验证码不应通过")
        ok = False

    # 验证码是一次性的：同一 id 再用正确答案也应失败
    payload = register_payload(username, answer)
    payload["captchaId"] = cid
    _, body = call("/api/auth/register", "POST", payload)
    print("   同一验证码复用 -> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 验证码应一次性使用")
        ok = False

    print("=" * 64)
    print("2) 注册（正确验证码）")
    cid, answer = new_captcha()
    payload = register_payload(username, answer)
    payload["captchaId"] = cid
    _, body = call("/api/auth/register", "POST", payload)
    data = (body or {}).get("data") or {}
    token = data.get("tokenValue")
    roles = ((data.get("userInfo") or {}).get("roleKeys")) or []
    print("   code=%s 注册后直接登录=%s 角色=%s"
          % ((body or {}).get("code"), bool(token), roles))
    if not ok_of(body) or not token:
        print("   [FAIL] 注册失败：%s" % body)
        return 1
    if "creator" not in roles:
        print("   [FAIL] 注册应固定分配创作者角色")
        ok = False

    # 重复账号
    cid, answer = new_captcha()
    payload = register_payload(username, answer)
    payload["captchaId"] = cid
    _, body = call("/api/auth/register", "POST", payload)
    print("   重复账号注册 -> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 重复账号应被拒绝")
        ok = False

    # 两次密码不一致
    cid, answer = new_captcha()
    payload = register_payload("qa" + suffix + "b", answer, confirm="other123")
    payload["captchaId"] = cid
    _, body = call("/api/auth/register", "POST", payload)
    print("   两次密码不一致 -> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 密码不一致应被拒绝")
        ok = False

    print("=" * 64)
    print("3) 登录与个人资料")
    _, body = call("/api/auth/login", "POST", {"username": username, "password": "abc12345"})
    token = ((body or {}).get("data") or {}).get("tokenValue")
    print("   新账号登录 -> %s" % bool(token))
    if not token:
        print("   [FAIL] 新账号无法登录")
        ok = False

    _, body = call("/api/profile", token=token)
    profile = (body or {}).get("data") or {}
    print("   资料：username=%s nickname=%s roles=%s"
          % (profile.get("username"), profile.get("nickname"), profile.get("roles")))
    if profile.get("username") != username:
        print("   [FAIL] 个人资料读取异常")
        ok = False

    _, body = call("/api/profile", "PUT",
                   {"nickname": "验证昵称", "email": "qa@example.com", "phone": "13800138000"},
                   token=token)
    print("   修改资料 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        print("   [FAIL] 修改资料失败")
        ok = False
    _, body = call("/api/profile", token=token)
    p = (body or {}).get("data") or {}
    print("   修改后：nickname=%s email=%s phone=%s"
          % (p.get("nickname"), p.get("email"), p.get("phone")))
    if p.get("nickname") != "验证昵称" or p.get("email") != "qa@example.com":
        print("   [FAIL] 资料未更新")
        ok = False

    _, body = call("/api/profile", "PUT",
                   {"nickname": "验证昵称", "email": "not-an-email", "phone": ""}, token=token)
    print("   非法邮箱 -> code=%s" % (body or {}).get("code"))
    if ok_of(body):
        print("   [FAIL] 非法邮箱应被拒绝")
        ok = False

    print("=" * 64)
    print("4) 修改密码")
    _, body = call("/api/profile/password", "PUT",
                   {"oldPassword": "wrong999", "newPassword": "xyz12345",
                    "confirmPassword": "xyz12345"}, token=token)
    print("   原密码错误 -> code=%s msg=%s" % ((body or {}).get("code"), (body or {}).get("msg")))
    if ok_of(body):
        print("   [FAIL] 原密码错误不应通过")
        ok = False

    _, body = call("/api/profile/password", "PUT",
                   {"oldPassword": "abc12345", "newPassword": "xyz12345",
                    "confirmPassword": "xyz12345"}, token=token)
    print("   正确改密 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        print("   [FAIL] 改密失败")
        ok = False

    _, body = call("/api/profile", token=token)
    print("   改密后旧令牌访问 -> code=%s（期望 401）" % (body or {}).get("code"))
    if (body or {}).get("code") != 401:
        print("   [FAIL] 旧令牌应失效")
        ok = False

    new_token = login(username, "xyz12345")
    old_token = login(username, "abc12345")
    print("   新密码登录=%s 旧密码登录=%s" % (bool(new_token), bool(old_token)))
    if not new_token or old_token:
        print("   [FAIL] 改密后登录行为不正确")
        ok = False

    print("=" * 64)
    print("5) D3：已发布稿件编辑后重审")
    creator = login("creator")
    reviewer = login("reviewer")
    admin = login("admin")
    if not all([creator, reviewer, admin]):
        print("   [FAIL] 演示账号登录失败")
        return 1

    title = "待办验证：已发布稿件编辑重审 " + suffix
    _, body = call("/api/article", "POST", {
        "title": title,
        "content": "这是一篇用于验证已发布稿件编辑重审流程的正常生活分享内容。",
        "summary": "D3 验证", "categoryId": 1, "tagIds": [1],
    }, token=creator)
    aid = (body or {}).get("data")
    _, body = call(f"/api/article/{aid}/submit", "POST", token=creator)
    _, body = call(f"/api/article/{aid}/review", "PUT", {"action": "approve", "reason": ""},
                   token=reviewer)
    print("   创建并发布 -> id=%s review code=%s" % (aid, (body or {}).get("code")))
    _, body = call(f"/api/article/{aid}", token=creator)
    print("   发布后状态 = %s（期望 2）" % ((body or {}).get("data") or {}).get("status"))
    if ((body or {}).get("data") or {}).get("status") != 2:
        print("   [FAIL] 稿件未发布")
        ok = False

    # 内容广场应能看到
    _, body = call(f"/api/article/plaza?pageNum=1&pageSize=50&title={urllib.parse.quote(title)}",
                   token=creator)
    visible = len(((body or {}).get("data") or {}).get("records") or [])
    print("   编辑前广场可见 = %d（期望 1）" % visible)
    if visible != 1:
        print("   [FAIL] 已发布稿件应出现在广场")
        ok = False

    # 编辑已发布稿件
    _, body = call("/api/article", "PUT", {
        "id": aid,
        "title": title,
        "content": "这是编辑后的内容：补充了一段说明，保存后应回到待审核。",
        "summary": "D3 验证（编辑后）", "categoryId": 1, "tagIds": [1],
    }, token=creator)
    print("   编辑已发布稿件 -> code=%s" % (body or {}).get("code"))
    if not ok_of(body):
        print("   [FAIL] 编辑已发布稿件失败：%s" % body)
        ok = False
    _, body = call(f"/api/article/{aid}", token=creator)
    a = (body or {}).get("data") or {}
    print("   编辑后状态 = %s（期望 1）风险 = %s（期望 -1）" % (a.get("status"), a.get("riskLevel")))
    if a.get("status") != 1 or a.get("riskLevel") != -1:
        print("   [FAIL] 编辑后应回到待审核且风险重置")
        ok = False

    _, body = call(f"/api/article/plaza?pageNum=1&pageSize=50&title={urllib.parse.quote(title)}",
                   token=creator)
    visible = len(((body or {}).get("data") or {}).get("records") or [])
    print("   编辑后广场可见 = %d（期望 0，审核期间不展示）" % visible)
    if visible != 0:
        print("   [FAIL] 待审核内容不应出现在广场")
        ok = False

    # 重新审核通过
    _, body = call(f"/api/article/{aid}/review", "PUT", {"action": "approve", "reason": ""},
                   token=reviewer)
    print("   重新通过 -> code=%s" % (body or {}).get("code"))
    _, body = call(f"/api/article/{aid}", token=creator)
    print("   重新发布后状态 = %s（期望 2）" % ((body or {}).get("data") or {}).get("status"))

    # 下架稿件也可编辑重审
    _, body = call(f"/api/article/{aid}/offline", "PUT", token=admin)
    print("   管理员下架 -> code=%s" % (body or {}).get("code"))
    _, body = call(f"/api/article/{aid}", token=creator)
    print("   下架后状态 = %s（期望 5）" % ((body or {}).get("data") or {}).get("status"))
    _, body = call("/api/article", "PUT", {
        "id": aid, "title": title, "content": "下架后编辑的内容。",
        "summary": "D3 下架重审", "categoryId": 1, "tagIds": [1],
    }, token=creator)
    print("   编辑已下架稿件 -> code=%s" % (body or {}).get("code"))
    _, body = call(f"/api/article/{aid}", token=creator)
    print("   编辑后状态 = %s（期望 1）" % ((body or {}).get("data") or {}).get("status"))
    if ((body or {}).get("data") or {}).get("status") != 1:
        print("   [FAIL] 下架稿件编辑后应回到待审核")
        ok = False

    print("=" * 64)
    print("6) 未登录访问个人中心")
    _, body = call("/api/profile")
    print("   code=%s（期望 401）" % (body or {}).get("code"))
    if (body or {}).get("code") != 401:
        print("   [FAIL] 未登录不应访问个人中心")
        ok = False

    print("=" * 64)
    print("结论：%s" % ("全部通过" if ok else "存在失败项，见上方 [FAIL]"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
