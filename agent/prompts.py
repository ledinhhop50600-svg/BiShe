"""提示词构造。

阶段 4 的版本：把**全部规则**放进提示词，让模型直接判断。
阶段 5 会加入规则检索（RAG）：先从规则库里召回最相关的若干条再交给模型，
并在此基础上做分级策略调整（D4：先判内容性质，再定严格度）。
"""

from schemas import AuditRequest, RuleItem

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
3. 必须定位到原文中的具体片段，并给出具体、可执行的修改建议；不要说"请注意合规"这类空话。
4. 风险等级只能是 0/1/2/3 之一：0 通过、1 疑似、2 违规、3 严重。拿不准时给"疑似"。

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


def build_user_prompt(req: AuditRequest, rules: list[RuleItem], retrieved: bool = False) -> str:
    """把平台约束、规则与待审内容拼成用户提示词。

    注意两个标记：【待审核内容】与【输出要求】——
    测试用的 Mock 供应商会依据它们定位"只应检查哪一段"，避免把规则文本里的示例词当成违规。

    @param rules     本次交给模型的规则（可能是全量，也可能是检索后的一部分）
    @param retrieved 是否经过检索：为 True 时在提示词里注明"这是从规则库检索出的相关条款"，
                     让模型知道不需要自己穷举规则
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
    parts.append(f"【待审核内容】\n标题：{req.title}\n正文：{req.content}")

    # 场景说明：预检与正式审核的处置语气不同
    trigger_hint = {
        "PRE_CHECK": "本次是发布前预检：结论只用于提示创作者，不阻断发布。",
        "POST_AUDIT": "本次是发布申请的正式审核：结论将供审核员决策。",
        "REPORT_REVIEW": "本次是举报后的复审：请重点关注被举报的问题。",
        "ADAPT_CHECK": "本次是适配到目标平台后的合规检查。",
    }.get(req.triggerType, "")

    parts.append("【输出要求】\n" + (trigger_hint + "\n" if trigger_hint else "") + "只输出 JSON，结构见系统提示词。")

    return "\n\n".join(parts)
