"""阶段 2 验证脚本：用户 / 角色 / 菜单管理接口 + 权限校验。

用法：python tools/verify_stage2.py [后端地址]
     默认 http://localhost:8080，也可用环境变量 ZIMEITI_BASE 指定。

验证内容：
  1. 管理员可以访问用户 / 角色 / 菜单管理接口
  2. 创作者与审核员访问用户管理接口 -> 应被拒绝（403），证明后端鉴权生效
  3. 新增用户 -> 分配角色 -> 再删除（走一遍完整写操作）
  4. 角色的菜单授权：读取 -> 修改 -> 复原
  5. 越权保护：不能禁用/删除当前登录账号；不能删除还有用户的角色

输出全部用 Unicode 码点表示，不受终端编码影响。
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
        with urllib.request.urlopen(req, timeout=15) as resp:
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


def login(username, password="123456"):
    _, body = call("/api/auth/login", "POST", {"username": username, "password": password})
    return ((body or {}).get("data") or {}).get("tokenValue")


def main():
    ok = True

    admin = login("admin")
    reviewer = login("reviewer")
    creator = login("creator")
    print("令牌获取：admin=%s reviewer=%s creator=%s" % (bool(admin), bool(reviewer), bool(creator)))
    if not (admin and reviewer and creator):
        print("[FAIL] 有账号登录失败")
        return 1

    print("=" * 62)
    print("1) 管理员访问三个管理接口（期望都成功）")
    for path, name in [("/api/user/page?pageNum=1&pageSize=5", "用户分页"),
                       ("/api/role/page?pageNum=1&pageSize=10", "角色分页"),
                       ("/api/menu/tree", "菜单树"),
                       ("/api/dashboard/stats", "看板统计")]:
        _, body = call(path, token=admin)
        code = (body or {}).get("code")
        print(f"   {name:8s} -> code={code}")
        if code != 200:
            print(f"   [FAIL] {name} 应可访问")
            ok = False

    _, body = call("/api/user/page?pageNum=1&pageSize=5", token=admin)
    users = ((body or {}).get("data") or {}).get("records") or []
    print("   用户示例：", esc([u.get("username") for u in users]), "| 角色回显：",
          esc([u.get("roleNames") for u in users][:2]))

    _, body = call("/api/dashboard/stats", token=admin)
    print("   看板统计：", {k: v for k, v in ((body or {}).get("data") or {}).items()})

    print("=" * 62)
    print("2) 越权访问（期望 403）—— 这是后端鉴权的关键证据")
    for who, token in [("审核员", reviewer), ("创作者", creator)]:
        for path, name in [("/api/user/page?pageNum=1&pageSize=5", "用户管理"),
                           ("/api/role/page?pageNum=1&pageSize=10", "角色管理"),
                           ("/api/menu/tree", "菜单管理")]:
            _, body = call(path, token=token)
            code = (body or {}).get("code")
            mark = "PASS" if code == 403 else "FAIL"
            print(f"   {who} 访问 {name:6s} -> code={code}  [{mark}]")
            if code != 403:
                ok = False

    print("=" * 62)
    print("3) 新增用户 -> 分配角色 -> 删除（完整写操作）")
    new_user = {"username": "tmp_tester", "password": "123456", "nickname": "临时测试账号",
                "status": 1, "roleIds": [3], "remark": "阶段 2 验证脚本创建，随后删除"}
    _, body = call("/api/user", "POST", new_user, token=admin)
    print("   新增 -> code=%s msg=%s" % ((body or {}).get("code"), esc((body or {}).get("msg"))))
    if (body or {}).get("code") != 200:
        ok = False

    # 找到刚创建的用户
    tmp_id = None
    _, body = call("/api/user/page?pageNum=1&pageSize=50&username=tmp_tester", token=admin)
    for u in ((body or {}).get("data") or {}).get("records") or []:
        tmp_id = u.get("id")
        print("   查询到：id=%s 昵称=%s 角色=%s" % (tmp_id, esc(u.get("nickname")), esc(u.get("roleNames"))))

    print("   重复账号新增应被拒绝 ->", end=" ")
    _, body = call("/api/user", "POST", new_user, token=admin)
    print("code=%s msg=%s" % ((body or {}).get("code"), esc((body or {}).get("msg"))))
    if (body or {}).get("code") == 200:
        print("   [FAIL] 重复账号不应创建成功")
        ok = False

    if tmp_id:
        _, body = call(f"/api/user/{tmp_id}", "DELETE", token=admin)
        print("   删除 -> code=%s" % (body or {}).get("code"))
        if (body or {}).get("code") != 200:
            ok = False
    else:
        print("   [FAIL] 未查询到新建用户")
        ok = False

    print("=" * 62)
    print("4) 角色菜单授权：读取 -> 覆盖 -> 复原")
    _, body = call("/api/role/3/menuIds", token=admin)
    original = (body or {}).get("data") or []
    print("   创作者角色原有菜单数 =", len(original), esc(original))
    # 临时加上"评测中心"(60)
    _, body = call("/api/role", "PUT",
                   {"id": 3, "roleName": "创作者", "roleKey": "creator", "sort": 3, "status": 1,
                    "description": "内容创作者", "menuIds": original + [60]}, token=admin)
    print("   增加一个菜单后保存 -> code=%s" % (body or {}).get("code"))
    _, body = call("/api/role/3/menuIds", token=admin)
    after = (body or {}).get("data") or []
    print("   保存后菜单数 =", len(after), "（应比原多 1）")
    if len(after) != len(original) + 1:
        print("   [FAIL] 授权未生效")
        ok = False
    # 复原
    call("/api/role", "PUT",
         {"id": 3, "roleName": "创作者", "roleKey": "creator", "sort": 3, "status": 1,
          "description": "内容创作者：投稿、查看审核反馈、做跨平台内容适配", "menuIds": original},
         token=admin)
    _, body = call("/api/role/3/menuIds", token=admin)
    restored = (body or {}).get("data") or []
    print("   复原后菜单数 =", len(restored), "| 与原始一致 =", set(restored) == set(original))
    if set(restored) != set(original):
        print("   [FAIL] 复原失败")
        ok = False

    print("=" * 62)
    print("5) 危险操作保护（期望被拒绝）")
    _, body = call("/api/user/1/status?status=0", "PUT", token=admin)
    print("   禁用当前登录账号 -> code=%s msg=%s" % ((body or {}).get("code"), esc((body or {}).get("msg"))))
    if (body or {}).get("code") == 200:
        print("   [FAIL] 不应允许禁用自己")
        ok = False

    _, body = call("/api/role/2", "DELETE", token=admin)
    print("   删除仍有用户的角色 -> code=%s msg=%s" % ((body or {}).get("code"), esc((body or {}).get("msg"))))
    if (body or {}).get("code") == 200:
        print("   [FAIL] 不应允许删除仍有用户的角色")
        ok = False

    print("=" * 62)
    print("总体结果:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
