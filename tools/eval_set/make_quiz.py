"""生成「人类标注复核」问卷。

背景：评测集的期望等级由本人单独标注，这是方法学上最大的弱点。
本脚本把**存在争议的样本**（语境陷阱 / 词表盲区 / 分级边界 / 多类混排）抽出来，
去掉原始编号（编号里含有层级提示）与我的标注，让你独立判断；
之后把结果与我的标注对比，算一致率，并在论文里如实报告分歧。

用法：python tools/eval_set/make_quiz.py
输出：docs/评测与标注/标注复核问卷-v1.md
"""

import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples.json")
OUT = os.path.join(HERE, "..", "..", "docs", "评测与标注", "标注复核问卷-v1.md")

TARGET_TIERS = ("trap", "blind", "pair", "multi")
SEED = 7


def main():
    with open(SAMPLES, encoding="utf-8") as f:
        samples = json.load(f)["samples"]
    picks = [s for s in samples if s["tier"] in TARGET_TIERS]
    rnd = random.Random(SEED)
    rnd.shuffle(picks)

    lines = []
    lines.append("# 标注复核问卷 v1\n")
    lines.append("> 目的：评测集的期望等级目前由 AI 单独标注，需要你独立判断一批样本，"
                 "用来计算「人类标注一致性」。\n"
                 "> 做法：逐题给出你的判断，不要参考任何「标准答案」（这里没有）。\n"
                 "> 你只需填数字：**0 通过 / 1 疑似 / 2 违规 / 3 严重**。\n")
    lines.append("## 判定口径（请按这个来）\n")
    lines.append("| 等级 | 含义 |")
    lines.append("|---|---|")
    lines.append("| **0 通过** | 正常内容；或虽然出现敏感词，但语境合法（作品名、引用法规、新闻报道转述、"
                 "「最后一步」这类普通用法） |")
    lines.append("| **1 疑似** | 有夸大/绝对化表述，但**没有卖货、没有引导交易、没有违法引导**（个人经验分享）"
                 "—— 应交人工复核，默认倾向放行 |")
    lines.append("| **2 违规** | 有商业推广/带货/交易引导**并且**含虚假承诺；或站外引流（引导加联系方式）；"
                 "或明显侵权（未授权转载）；或低俗擦边 |")
    lines.append("| **3 严重** | 违禁品交易（如处方药）；歧视性言论；违法违禁引导 |")
    lines.append("\n> 一句话记法：**先看它是不是在卖东西、在拉人到站外；是 → 严；不是 → 看夸大程度给 0 或 1。**\n")
    lines.append("---\n")

    key = []
    for i, s in enumerate(picks, start=1):
        qid = f"Q{i:02d}"
        key.append({"qid": qid, "sample_id": s["id"], "my_level": s["expected_level"], "note": s.get("note", "")})
        lines.append(f"## {qid}\n")
        if s.get("title"):
            lines.append(f"**标题**：{s['title']}\n")
        body = s.get("content") or ""
        # 长文只展示前 400 字 + 结尾 200 字，避免问卷过长（原文长度在括号里标注）
        if len(body) > 700:
            shown = body[:400] + "\n……（中间省略）……\n" + body[-200:]
            lines.append(f"**正文**（全文 {len(body)} 字，此处节选）：\n\n{shown}\n")
        else:
            lines.append(f"**正文**：\n\n{body}\n")
        lines.append(f"> 👉 **你的判断（填 0/1/2/3）**：`____`\n")
        lines.append("---\n")

    lines.append("## 作答汇总表（方便我对比）\n")
    lines.append("| 题号 | 你的判断 | 备注（可选） |")
    lines.append("|---|---|---|")
    for i in range(1, len(picks) + 1):
        lines.append(f"| Q{i:02d} |  |  |")

    lines.append("\n---\n")
    lines.append("> 说明：共 %d 题，预计 10–15 分钟。你填完后告诉我，我会计算「你的判断 vs 我的标注」的一致率，"
                 "并把分歧逐条列出来讨论（分歧本身也是论文里「标注一致性」部分的素材）。" % len(picks))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # 对照答案单独保存（不写进问卷，供脚本比对）
    with open(os.path.join(HERE, "_quiz_key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f, ensure_ascii=False, indent=2)

    print(f"✅ 问卷：{os.path.abspath(OUT)}（{len(picks)} 题）")
    print(f"   对照答案：tools/eval_set/_quiz_key.json（不要给被试看）")


if __name__ == "__main__":
    main()
