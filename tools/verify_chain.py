"""阶段 0 链路验证脚本（编码无关，输出全部为 ASCII）。

用法：python tools/verify_chain.py
作用：请求后端 /api/ping，把返回的中文转成 Unicode 码点打印，
      这样无论终端是什么编码，都能准确判断数据库里的中文是否正确。
"""
import json
import urllib.request

API = "http://localhost:8080/api/ping"
EXPECT_FIRST = "链路已打通：这条数据来自 MySQL"


def esc(s: str) -> str:
    """把字符串转成 ASCII 安全的 unicode 转义形式，避免终端编码干扰判断。"""
    return s.encode("unicode_escape").decode("ascii")


def main() -> int:
    try:
        with urllib.request.urlopen(API, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print("FAIL: 无法请求后端接口 ->", type(e).__name__, e)
        return 1

    print("HTTP 返回 code =", body.get("code"))
    data = body.get("data") or {}
    msgs = data.get("messages") or []
    print("消息条数 =", len(msgs))
    print("source 码点 =", esc(str(data.get("source"))))

    ok = True
    for i, m in enumerate(msgs):
        text = str(m.get("message"))
        print(f"  第{i + 1}条 码点 = {esc(text)}")
    if msgs:
        first = str(msgs[0].get("message"))
        ok = first == EXPECT_FIRST
        print("第1条与预期字符串完全一致 =", ok)
        if not ok:
            print("  预期码点 =", esc(EXPECT_FIRST))

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
