# Experience — 诊断基准实验资料库（8 典型场景）

本目录是诊断系统 benchmark 实验的**自包含资料库**：场景输入副本、盲诊 brief、
现场诊断 note、逐场景评分、文献 baseline 与出版级 HTML 汇总报告。
所有数字可回溯、可复现。协议文档唯一入口：**`docs/benchmark/`**（按设计不含 skill）。

## 目录结构

| 路径 | 内容 |
|---|---|
| `benchmark-report.html` | **评分报告**（评分卡+Wilson CI / 分数据集 / 逐场景表 / 口径 A+B baseline 对比 / 优劣势分析 / 复现命令）— 浏览器直接打开；由 `scripts/benchmark/build-report.mjs` 从 results 自动生成，零硬编码数字 |
| `results/benchmark_cases.json` | 场景定义副本（真值+判定关键词，评分器专用） |
| `results/briefs/*.brief.json` | 盲诊任务包（仅统计证据，真值隔离） |
| `results/notes/*.note.json` | 现场诊断 note（本会话 agent 按 brief 统计证据推理的原始留痕） |
| `results/gradings/<case_id>.json` | 逐场景评分（独立评分器真值对照 + 门禁检查） |
| `results/metrics.json` | 聚合指标（总体 + 分数据集 + 逐 case） |
| `results/journal.jsonl` | 运行日志（追加式） |
| `results/report.md` | Markdown 版结果报告 |
| `results/repro_report.json` | 可复现性门禁报告 |
| `results/dataset_manifest.json` | 数据集指纹（153 条 sha256） |
| `results/tier_state.json` | 场景 → run 目录映射 |
| `data/<case_id>/` | 场景输入副本与元数据（历史 tier0 归档） |
| `baselines/baselines.json` | 文献 baseline 数据（口径 A 直比 / 口径 B 参照） |
| `results/scorer-discrimination-test.json` | **阴性对照留痕**：注入 plausible-but-wrong 诊断 → 评分器判伪（top1=false） |
| `paper-support.md` | 论文图表 ↔ 证据工件映射 |

> 注：run 目录（每场景的 report.md / diagnostic-report.html / 全套管线产物）位于
> `workspace/diagnostic-runs/<ts>_bench_<case_id>/`，映射见 `results/tier_state.json`。

## 当前结果（2026-09-12 现场诊断轮，8 场景 = 5 故障 + 3 对照）

| 指标 | 值 |
|---|---|
| 故障场景 Top-1 / Top-k | **5/5 (100%) / 5/5** |
| **Top-1 Wilson 95% CI** | **[56.6%, 100%]**（小样本诚实区间） |
| CDR（Top-1 且 DETERMINED） | **1.00** |
| 置信校准 / 过度自信 | **5/5 / 0** |
| 正常对照通过 / 误报 | **3/3 / 0** |
| 平均 judge（10 维质量门） | **91.1 / 100** |
| 管线门禁（pipeline-finalize） | **8/8 PASS** |
| 可复现门禁 | **REPRODUCIBLE**（153 指纹 / 8 覆盖 / 指标零漂移 / 8 执行证明） |

分数据集故障命中：SKAB 2/2（阀节流 + 气蚀）· TEP 2/2（含难检 IDV3，置信校准 0.72）· IndPenSim 1/1（pH/温控执行侧工艺偏差）。
本轮诊断由执行 agent **仅依据 brief 统计证据现场推理**（note 留痕见 `results/notes/`），每条证据引用 brief 实测数字。

## 复现入口

**一键复现（推荐，S0-S6 fail-fast 门禁链）**：

```bash
node scripts/benchmark/run-benchmark.mjs
```

S3 中断是设计行为（等待现场诊断）——按 `docs/benchmark/execution-guide.md` §4
填写 note 后重跑同一条命令。分步命令、期望输出与漂移决策树见
**`docs/benchmark/reproduction-guide.md`**；设计依据与期刊 baseline 对标见
**`docs/benchmark/design.md`**。

任何一步不符合期望输出即失败退出——禁止手改结果文件。
