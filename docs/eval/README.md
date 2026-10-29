# 评测数据目录说明

本目录存放阶段 5～8 的实验结果。**页面只读这些 JSON**，计算都在 `tools/` 的脚本里完成，
不要手工改 JSON（会导致页面与论文数据不一致）。

## 文件

| 文件 | 来源 | 说明 |
|---|---|---|
| `audit-results.json` | `tools/experiment_compare.py --workers 10`（2026-10-29 扩展集 v5） | 审核实验主表（428 条、6 方案、分层、核心/公开拆分、结论） |
| `adaptation-results.json` | `tools/eval_adaptation.py --run-id paper-20261019-v2` | 适配评估论文数据（4 篇 × 3 平台） |
| `adaptation-review.html` | `tools/make_human_review.py` | **人工评分页面（推荐）**：原文 vs 适配结果 + 1-5 分评分 + 导出 CSV |
| `adaptation-human-review.md` | 同上 | 纯文字版（不想开浏览器时看） |
| `adaptation-human-scores.csv` | 评分页面导出 | 人工评分原始数据（当前 12 条已填） |
| `adaptation-human-eval.md` | `tools/analyze_human_scores.py` | 人工 vs LLM 对比（MAD / 完全一致 / Spearman） |
| `adaptation-human-sheet.csv` | 评估脚本生成 | 空白评分表（旧格式，可不用；优先用 HTML 页面） |
| `adaptation-eval.md` | 同上 | 适配评估报告（指标、逐条结果、局限） |
| `judge-cache.json` | 评估脚本自动维护 | LLM 评分缓存（按内容哈希；避免重复花钱） |
| `demo/` | 评测中心「运行演示评测」 | 页面演示结果，**不覆盖论文数据** |

## 复现

在项目根目录执行（需后端 8080、Agent 8001 已启动）：

```bash
# 适配评估（论文数据）
python tools/eval_adaptation.py --run-id paper --out-dir docs/eval

# 只算格式/合规，不调用 LLM 评委
python tools/eval_adaptation.py --run-id paper --out-dir docs/eval --no-llm

# 忽略评分缓存，重新打分
python tools/eval_adaptation.py --run-id paper --out-dir docs/eval --refresh-judge
```

> `--run-id` 换一个值会强制重新调用模型（不复用回放缓存）；同一 run-id 重跑会走回放，
> **耗时数字会变成回放时间**，不要拿它当模型性能数据。

## 人工评分怎么填（推荐用评分页面）

**双击打开 `docs/eval/adaptation-review.html`**（或拖进浏览器）。页面已经排好每条：

1. 上半部分：**原文**；右半部分：**适配结果**（标题/正文/标签）+ 格式与合规结论；
2. 下方三项评分，点 1-5 即可：
   - **风格符合度**：像不像这个平台（1 完全不像 / 5 很像，可直接发）
   - **信息保留度**：有没有丢信息或编造（1 大量丢失/编造 / 5 完整准确）
   - **可读性**：读起来顺不顺（1 很难读 / 5 流畅）
3. 不确定就给 3 分；页面顶部有完整评分标准；
4. 评分自动保存在浏览器里，随时可以关掉再打开；全部填完后点右下角 **「导出评分 CSV」**；
5. 把下载的 `adaptation-human-scores.csv` 放回 `docs/eval/`，然后运行：
   `python tools/analyze_human_scores.py`，会生成 `adaptation-human-eval.md` 并更新结果 JSON。

> **当前状态（2026-10-19）**：12 条已填，三项全部为 5 分。人工评分方差为 0，
> Spearman 无定义，只能说明人工接受度为 100%，不能验证 LLM 的排序能力。
> 详情见 `adaptation-human-eval.md`。若论文需要秩相关，需要对部分结果给出低于 5 分的评分。

> **建议全部评完再看 LLM 分数**：页面默认隐藏，评完可勾选「显示 LLM 评分」对照，避免先看 AI 分数被带偏。
> 如果不想用浏览器，`adaptation-human-review.md` 是同样的内容（纯文字版），可以直接在编辑器里看。

三项评分都填完后，用 Spearman 相关系数比较人工与 LLM 评分。样本量只有 12，
相关系数波动会很大，论文里应如实说明"样本量小，仅作方向性参考"。

## 注意

- LLM 评分集中在 4-5，区分度低；**不能只报 LLM 分数**。
- 一次运行中出现过小红书长文超限（1111/1000 字），说明格式通过率不是恒定的 100%；
  论文中应报告波动与失败原因，而不是只挑一次全通过的结果。
- 演示数据（`demo/`）只用于页面展示，不作为论文数据。
