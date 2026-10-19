"""提示词构造。

阶段 4 的版本：把**全部规则**放进提示词，让模型直接判断。
阶段 5 会加入规则检索（RAG）：先从规则库里召回最相关的若干条再交给模型，
并在此基础上做分级策略调整（D4：先判内容性质，再定严格度）。
"""

from schemas import AdaptRequest, AuditRequest, PlatformInfo, RuleItem

SYSTEM_PROMPT = """你是一名专业的内容审核员，负责判断自媒体内容是否违反平台规则。

【分级策略（最重要，必须遵守）】
1. **先判断内容是否具有商业推广属性**：是否在销售商品或服务、是否包含价格/优惠/库存/直播间等交易信息、
   是否引导私下交易或留下联系方式。
2. 广告法类规则（绝对化用语、价格承诺、医疗功效宣称）**只对具有商业推广属性的内容**按建议等级判定。
3. 对**无商业属性的个人经验分享**（生活记录、使用感受、测评心得）：即使出现"最好""一周瘦十斤"这类夸大表述，
   也只判为「疑似（1）」并在理由中说明"属于个人分享，建议人工复核"，**不要直接判「违规」**。
4. 站外引流、违禁品交易、明显侵权**不受此放宽**，仍按规则判定。
5. 严重（3）只用于：违禁品交易、违法违禁行为引导、极端有害内容。

【判定要求】
1. 严格依据提供的规则条目判断，不要凭空发明规则；命中的规则必须给出规则编号。
2. 必须结合语境。例如作品名《最好的我们》中的"最好"不构成绝对化用语，
   而商品宣传里的"全网最好的产品"才可能构成。
3. **长文必须逐段检查**：正文较长时，开头、中段、结尾都要看。不要因为篇幅长就只看开头，
   也不要因为没有在前几段发现问题就判定通过。中段夹带的违规是最容易漏的。
4. 必须定位到原文中的具体片段，并给出具体、可执行的修改建议；不要说"请注意合规"这类空话。
   **片段必须是原文中真实存在的连续文字**，不要改写或拼接。
5. 风险等级只能是 0/1/2/3 之一：0 通过、1 疑似、2 违规、3 严重。拿不准时给"疑似"。
6. **violations 最多列出 8 处**（按严重程度取最靠前的）。理由：长文可能命中很多处，
   输出过长会被截断导致 JSON 不完整；同时审核员真正会处理的是最严重的那几处。

只输出 JSON，不要输出任何解释文字。JSON 结构如下：
{
  "riskLevel": 0,
  "reason": "判定理由（中文，引用规则编号，说明内容性质是商业推广还是个人分享）",
  "hitRules": [{"code": "规则编号", "name": "规则名", "category": "类别"}],
  "violations": [{"fragment": "原文片段", "issue": "问题", "suggestion": "具体修改建议"}],
  "suggestion": "总体处置建议",
  "confidence": 0.0
}
未发现违规时：riskLevel 为 0，hitRules 与 violations 为空数组。
"""


def build_user_prompt(req: AuditRequest, rules: list[RuleItem], retrieved: bool = False,
                      content_override: str | None = None) -> str:
    """把平台约束、规则与待审内容拼成用户提示词。

    注意两个标记：【待审核内容】与【输出要求】——
    测试用的 Mock 供应商会依据它们定位"只应检查哪一段"，避免把规则文本里的示例词当成违规。

    @param rules            本次交给模型的规则（可能是全量，也可能是检索后的一部分）
    @param retrieved        是否经过检索：为 True 时注明"这是从规则库检索出的相关条款"
    @param content_override 关键词定位后的内容（节选）；为 None 时用原文
    """
    parts: list[str] = []

    # 目标平台与格式约束
    if req.platform:
        p = req.platform
        parts.append(
            "【目标平台】\n"
            f"{p.platformName}（{p.platformKey}）："
            f"标题上限 {p.titleMaxLen} 字，正文上限 {p.contentMaxLen} 字。\n"
            f"话题标签规则：{p.tagRule or '无'}\n"
            f"内容风格：{p.styleDesc or '无'}"
        )

    # 规则清单
    rule_lines = []
    for r in rules:
        line = f"- [{r.code}] {r.name}（类别：{r.category}，建议等级：{r.suggestedLevel}）：{r.content}"
        if r.source:
            line += f"\n  依据：{r.source}"
        rule_lines.append(line)
    header = "【审核规则】"
    if retrieved:
        header += f"\n（以下 {len(rules)} 条是从规则库中检索出的与本文最相关的条款，请依据它们判断）"
    parts.append(header + "\n" + ("\n".join(rule_lines) if rule_lines else "（本次未提供规则）"))

    # 待审内容（Mock 依赖此标记定位）
    body_text = req.content if content_override is None else content_override
    excerpt = "" if content_override is None else "（以下为文章的节选，仅供定位违规片段参考）\n"
    parts.append(f"【待审核内容】\n{excerpt}标题：{req.title}\n正文：{body_text}")

    # 场景说明：预检与正式审核的处置语气不同
    trigger_hint = {
        "PRE_CHECK": "本次是发布前预检：结论只用于提示创作者，不阻断发布。",
        "POST_AUDIT": "本次是发布申请的正式审核：结论将供审核员决策。",
        "REPORT_REVIEW": "本次是举报后的复审：请重点关注被举报的问题。",
        "ADAPT_CHECK": "本次是适配到目标平台后的合规检查。",
    }.get(req.triggerType, "")

    parts.append("【输出要求】\n" + (trigger_hint + "\n" if trigger_hint else "") + "只输出 JSON，结构见系统提示词。")

    return "\n\n".join(parts)


# ======================================================================
# 跨平台适配（阶段 6）
# ======================================================================

ADAPT_SYSTEM_PROMPT = """你是一名跨平台内容改编编辑，负责把同一个作者的一篇源文章，
改写成适合指定平台发布的版本。

【最重要的约束：不编造】
1. 只能使用源文章中出现的事实、数据、观点、步骤和产品信息。
2. 不得新增原文没有的数据、价格、功效承诺、用户评价、个人经历或身份。
3. 不得把"个人体验"改写成"确定效果"，不得为了吸引眼球夸大原文。
   改写的目标是**换一种更适合平台的表达**，不是重新创作一篇更夸张的内容。

【合规约束】
4. 不得保留或引入：绝对化用语（最好、第一、国家级等）、无法核实的价格承诺、
   具体时限的功效承诺、站外引流（微信/QQ/二维码/私信领资料）、违禁品交易、低俗暗示、未授权转载。
5. 原文里的风险表述要改写成合规表达；无法在不改变事实的前提下改写时，直接删掉该句。

【内容要求】
6. 必须保留原文的核心信息与关键步骤，不能只写一句空话；删减时优先删次要细节。
7. 遵守目标平台的标题/正文字数上限和标签规则。接近上限时先精简，不要硬凑字数。
   即使平台允许很长的正文，适配结果也请控制在 3000 字以内 —— 跨平台改写的目标是保留核心信息，
   不是把原文原样搬过去。
8. 按目标平台的风格改写（口语/正式/口播脚本等）；emoji 只在平台风格允许时使用。
9. 标题要具体，能让人知道这篇讲什么，不要用"震惊""必看"这类空泛标题。
10. **话题标签只放在 tags 字段里，不要写进正文**。正文结尾不要再列一遍标签 ——
    主系统会把 tags 拼在正文末尾用于发布，重复写会出现两遍。

只输出 JSON，不要输出任何解释文字。JSON 结构：
{"title": "标题", "content": "正文", "tags": ["#话题1", "#话题2"]}
不需要话题标签时 tags 返回空数组。
"""

# 每个平台的改写要点。和数据库里的 style_desc 是互补关系：
# style_desc 是管理员可改的"风格要求"，这里是程序内置的"平台形态"（决定输出长什么样）。
PLATFORM_HINTS = {
    "xiaohongshu": "小红书笔记形态：开头一句钩子（读者的痛点或结果），正文短句分段、口语化，"
                   "可以用少量 emoji；准备 3-5 个 #话题放进 tags 字段（不要写进正文，系统会在发布时拼到末尾）。"
                   "标题不超过平台上限，越短越好。",
    "weibo": "微博形态：没有独立标题（title 返回空字符串），正文第一句就是重点；"
             "信息流只展示前 140 字，所以要在前 140 字内说清结论，整体尽量控制在 300 字内；"
             "准备 1-2 个 #话题# 放进 tags 字段（不要写进正文）。",
    "wechat": "公众号形态：正式长文，保留原文的段落层次，可用小标题组织内容；"
              "开头交代背景，结尾给结论或行动建议；不使用话题标签。",
    "bilibili": "B站视频投稿形态：标题口语化但说清主题；正文是视频简介，先一句话概括看点，"
                "再用短段落列出内容要点或时间线；准备 3-5 个标签放进 tags 字段（不要写进正文）。",
    "douyin": "抖音口播脚本形态：标题短、有钩子；正文按【画面】和【口播】分段写，"
              "前三秒必须抛出冲突或结果；句子短、适合念出来；准备 3-5 个话题放进 tags 字段（不要写进正文）。",
}


def build_adapt_prompt(req: AdaptRequest, platform: PlatformInfo) -> str:
    """把源文章与目标平台约束拼成一条适配请求。"""
    title_max = platform.titleMaxLen or 0
    if title_max > 0:
        title_line = f"- 标题上限：{title_max} 字（含标点）"
    else:
        title_line = "- 该平台没有独立标题，title 必须返回空字符串"

    hint = PLATFORM_HINTS.get(platform.platformKey, "")
    parts = [
        "【目标平台】\n"
        f"{platform.platformName}（{platform.platformKey}）\n"
        f"{title_line}\n"
        f"- 正文上限：{platform.contentMaxLen or 0} 字\n"
        f"- 话题标签规则：{platform.tagRule or '无'}\n"
        f"- 内容风格：{platform.styleDesc or '无'}"
        + (f"\n- 改写要点：{hint}" if hint else ""),
        f"【源文章】\n标题：{req.title}\n正文：{req.content}",
        "【输出要求】\n只输出 JSON："
        '{"title": "标题", "content": "正文", "tags": ["#话题1", "#话题2"]}',
    ]
    return "\n\n".join(parts)
