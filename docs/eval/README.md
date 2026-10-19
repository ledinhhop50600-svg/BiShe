# 评测数据目录说明

本目录存放阶段 5～8 的实验结果。**页面只读这些 JSON**，计算都在 `tools/` 的脚本里完成，
不要手工改 JSON（会导致页面与论文数据不一致）。

## 文件

| 文件 | 来源 | 说明 |
|---|---|---|
| `audit-results.json` | 由 v4 对比实验整理 | 审核实验主表（52 条、4 方案、分层、口径对照、结论） |
| `adaptation-results.json` | `tools/eval_adaptation.py --run-id paper-20261019-v2` | 适配评估论文数据（4 篇 × 3 平台） |
| `adaptation-human-sheet.csv` | 同上 | 人工评分表（留空待填，UTF-8 BOM） |
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

## 人工评分怎么填

打开 `adaptation-human-sheet.csv`（Excel 可直接打开），每行是一个适配结果，填入：

| 列 | 含义 | 分值 |
|---|---|---|
| `风格_人工(1-5)` | 是否符合目标平台的表达习惯 | 1 完全不像 / 3 一般 / 5 很像 |
| `保留_人工(1-5)` | 是否保留源文核心信息、没有编造 | 1 大量丢失或编造 / 3 一般 / 5 完整准确 |
| `可读_人工(1-5)` | 语言是否通顺、结构是否清晰 | 1 难读 / 3 一般 / 5 流畅 |
| `人工点评` | 一句话说明扣分原因（可选） | - |

填完后，用 Spearman 相关系数比较人工与 LLM 的三项评分。样本量只有 12，
相关系数波动会很大，论文里应如实说明"样本量小，仅作方向性参考"。

## 注意

- LLM 评分集中在 4-5，区分度低；**不能只报 LLM 分数**。
- 一次运行中出现过小红书长文超限（1111/1000 字），说明格式通过率不是恒定的 100%；
  论文中应报告波动与失败原因，而不是只挑一次全通过的结果。
- 演示数据（`demo/`）只用于页面展示，不作为论文数据。
