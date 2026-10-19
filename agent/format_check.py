"""格式自检：字数、标签数量与格式。

为什么这部分不交给模型：**客观约束必须由程序算**。
模型可能"觉得自己没超"，但长度是可以精确计算的；把可计算的规则交给模型，
既浪费 token，又会让结论随模型状态波动。模型只负责写内容，程序负责验收。
"""

import re

from schemas import FormatCheck, PlatformInfo

# "3-5 个" / "1~2 个" / "3 到 5 个"
_RANGE = re.compile(r"(\d+)\s*[-~至到]\s*(\d+)\s*个")
# "3 个"
_SINGLE = re.compile(r"(\d+)\s*个")


def parse_tag_range(tag_rule: str | None) -> tuple[int | None, int | None]:
    """从标签规则文本里解析数量区间。

    数据库里的 tag_rule 是管理员填的一句话（如"以 # 开头，建议 3-5 个"），
    没有单独的数量字段。这里按约定格式解析：
      - 含"不使用" -> 0 个；
      - 含"N-M 个" -> N..M；
      - 含"N 个"   -> N..N；
      - 其他（如"可选，以 # 开头"）-> 不检查数量。
    解析不出来时宁可不检查，也不误报 —— 格式自检的误报会直接损害可信度。
    """
    if not tag_rule:
        return None, None
    if "不使用" in tag_rule:
        return 0, 0
    m = _RANGE.search(tag_rule)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _SINGLE.search(tag_rule)
    if m:
        n = int(m.group(1))
        return n, n
    return None, None


def _require_hash_prefix(tag_rule: str | None) -> bool:
    if not tag_rule:
        return False
    return "以 # 开头" in tag_rule or "#话题#" in tag_rule


def check_format(platform: PlatformInfo, title: str, content: str,
                 tags: list[str]) -> FormatCheck:
    """对适配产物做确定性校验。返回的 issues 直接展示给用户。"""
    issues: list[str] = []
    title_len = len(title)
    content_len = len(content)
    title_max = platform.titleMaxLen or 0
    content_max = platform.contentMaxLen or 0

    # 微博等平台 titleMaxLen=0 表示"没有独立标题"，此时不校验标题
    if title_max > 0:
        if not title.strip():
            issues.append("标题为空")
        elif title_len > title_max:
            issues.append(f"标题 {title_len} 字，超过上限 {title_max} 字")

    if not content.strip():
        issues.append("正文为空")
    elif content_max > 0 and content_len > content_max:
        issues.append(f"正文 {content_len} 字，超过上限 {content_max} 字")

    lo, hi = parse_tag_range(platform.tagRule)
    if hi is not None and len(tags) > hi:
        issues.append(f"标签 {len(tags)} 个，超过上限 {hi} 个")
    if lo is not None and len(tags) < lo:
        issues.append(f"标签 {len(tags)} 个，少于要求的 {lo} 个")

    if _require_hash_prefix(platform.tagRule):
        missing = [t for t in tags if not t.startswith("#")]
        if missing:
            issues.append("标签需以 # 开头：" + "、".join(missing))

    for t in tags:
        if not t.strip():
            issues.append("存在空标签")
        elif re.search(r"\s", t):
            issues.append(f"标签「{t}」含空格，平台可能无法识别")
    if len(set(tags)) != len(tags):
        issues.append("存在重复标签")

    return FormatCheck(
        passed=not issues,
        titleLen=title_len,
        contentLen=content_len,
        tagCount=len(tags),
        issues=issues,
    )
