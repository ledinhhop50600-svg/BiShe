"""阶段 1 验证脚本：登录认证与角色菜单。

用法：python tools/verify_stage1.py [后端地址]
     默认后端地址为 http://localhost:8080，也可用环境变量 ZIMEITI_BASE 指定。

作用：不依赖浏览器，直接在命令行把认证链路走一遍，输出全部用 Unicode 码点表示，
      因此不受终端编码影响（终端编码经常变，肉眼看中文容易误判）。

验证内容：
  1. 未登录访问受保护接口 -> 应返回 401
  2. 账号密码错误 -> 应返回失败提示
  3. 三种角色分别登录 -> 应拿到令牌，且菜单/权限各不相同
  4. 带令牌访问 /api/auth/me -> 应返回该用户信息
  5. 登出后令牌失效 -> 再访问应返回 401
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("ZIMEITI_BASE", "http://localhost:8080")).rstrip("/")


def call(path, method="GET", body=None, token=None):
    """发一个请求，返回 (http状态, 解析后的JSON或None)。"""
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


def main():
    ok = True

    print("=" * 60)
    print("1) 未登录访问受保护接口（期望 401）")
    status, body = call("/api/auth/me")
    print("   HTTP =", status, "| code =", (body or {}).get("code"))
    if (body or {}).get("code") != 401:
        print("   [FAIL] 未登录应被拦截")
        ok = False
    else:
        print("   [PASS] 未登录被正确拦截")

    print("=" * 60)
    print("2) 密码错误（期望失败提示）")
    status, body = call("/api/auth/login", "POST", {"username": "admin", "password": "wrong-password"})
    print("   HTTP =", status, "| code =", (body or {}).get("code"), "| msg =", esc((body or {}).get("msg")))
    if (body or {}).get("code") == 200:
        print("   [FAIL] 错误密码不应登录成功")
        ok = False
    else:
        print("   [PASS] 错误密码被拒绝")

    print("=" * 60)
    print("3) 三种角色登录并对比菜单与权限")
    tokens = {}
    for username, expect_role, expect_menu in [
        ("admin", "admin", "系统管理"),
        ("reviewer", "reviewer", "审核工作台"),
        ("creator", "creator", "创作中心"),
    ]:
        status, body = call("/api/auth/login", "POST", {"username": username, "password": "123456"})
        data = (body or {}).get("data") or {}
        info = data.get("userInfo") or {}
        token = data.get("tokenValue")
        role_keys = info.get("roleKeys") or []
        perms = info.get("permissions") or []
        menus = info.get("menus") or []
        menu_names = flatten_names(menus)

        print(f"   {username:9s} 令牌={'有' if token else '无'} | 角色={esc(role_keys)} | 权限数={len(perms)} | 顶级菜单={esc(menu_names)}")
        if token:
            tokens[username] = token
        if expect_role not in role_keys:
            print(f"   [FAIL] {username} 的角色标识不含 {expect_role}")
            ok = False
        if not any(expect_menu in n for n in menu_names):
            print(f"   [FAIL] {username} 的菜单里找不到「{expect_menu}」")
            ok = False

    print("   --- 三种角色的权限数量应当不同，且互不越界 ---")
    admin_perms = set(get_perms("admin"))
    reviewer_perms = set(get_perms("reviewer"))
    creator_perms = set(get_perms("creator"))
    print("   admin 独有 :", esc(sorted(admin_perms - reviewer_perms - creator_perms))[:200])
    print("   reviewer 独有:", esc(sorted(reviewer_perms - creator_perms))[:200])
    print("   creator 独有 :", esc(sorted(creator_perms - admin_perms))[:200])
    if "system:user" in creator_perms or "system:user" in reviewer_perms:
        print("   [FAIL] 非管理员不应拥有 system:user 权限")
        ok = False
    else:
        print("   [PASS] 权限未越界（非管理员没有系统管理权限）")

    print("=" * 60)
    print("4) 带令牌访问 /api/auth/me")
    status, body = call("/api/auth/me", token=tokens.get("reviewer"))
    info = (body or {}).get("data") or {}
    print("   code =", (body or {}).get("code"), "| 昵称 =", esc(info.get("nickname")), "| 角色 =", esc(info.get("roles")))
    if (body or {}).get("code") != 200 or not info.get("nickname"):
        print("   [FAIL] 带令牌应能取到用户信息")
        ok = False
    else:
        print("   [PASS] 令牌有效，用户信息正确")

    print("=" * 60)
    print("5) 登出后令牌失效（期望 401）")
    call("/api/auth/logout", "POST", token=tokens.get("reviewer"))
    status, body = call("/api/auth/me", token=tokens.get("reviewer"))
    print("   HTTP =", status, "| code =", (body or {}).get("code"))
    if (body or {}).get("code") != 401:
        print("   [FAIL] 登出后令牌应失效")
        ok = False
    else:
        print("   [PASS] 登出后令牌已失效")

    print("=" * 60)
    print("总体结果:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


_CACHE = {}


def get_perms(username):
    """取某用户登录后的权限列表（带缓存，避免重复登录）。"""
    if username in _CACHE:
        return _CACHE[username]
    _, body = call("/api/auth/login", "POST", {"username": username, "password": "123456"})
    perms = ((body or {}).get("data") or {}).get("userInfo", {}).get("permissions") or []
    _CACHE[username] = perms
    return perms


def flatten_names(menus):
    names = []
    for m in menus:
        names.append(m.get("menuName") or "")
        for c in (m.get("children") or []):
            names.append(c.get("menuName") or "")
    return names


if __name__ == "__main__":
    raise SystemExit(main())
