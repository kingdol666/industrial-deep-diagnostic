# IDD 诊断基准（Benchmark）— 文档入口

> 本目录是诊断基准协议的**唯一文档入口**。按设计，基准编排脚本全部位于
> `scripts/benchmark/`（不做成 skill——基准是评测协议，不是作业技能；
> 被评测对象才是 skill 管线 `industrial-analysis-auto`）。

## 1. 基准测什么

被评测对象是 **一次完整的工业诊断 run**（`industrial-analysis-auto` 管线 Step 0-9），
而非逐样本标签。每个场景走完整管线，产出：

- `report.md` — MD 诊断报告（金字塔结构，Step 6 reporter）
- `diagnostic-report.html` — HTML 诊断报告（Step 8/8.5 可视化 + 审校）
- `04_diagnostics/diagnosis.json` 等全套产物 + `.pipeline_events.jsonl` 执行证明

然后由**独立评分器**读取管线输出，与标准答案（truth，仅存在于评分器侧）对照打分。

## 2. 场景集（8 个典型场景）

| case_id | 数据集 | 角色 | 难点设计 |
|---|---|---|---|
| `skab_valve1_1` | SKAB 水循环试验台 | 故障 | 阀门类机理判别 |
| `skab_cavitation_13` | SKAB（other 组，故障类型不下发） | 故障 | 隐蔽故障，允许三态结论 |
| `skab_normal_control` | SKAB anomaly-free | **对照** | 误报检验 |
| `tep_d01_ac_feed_ratio` | Tennessee Eastman d01 | 故障 | 进料比阶跃（文献可比 IDV1） |
| `tep_d03_hard` | Tennessee Eastman d03 | 故障 | **文献公认难检故障 IDV3**，允许 NEEDS_DATA |
| `tep_d00_normal_control` | Tennessee Eastman d00 | **对照** | 误报检验 |
| `indpensim_batch093` | IndPenSim 青霉素发酵 batch 93 | 故障 | 批过程工艺偏差 |
| `indpensim_batch001_control` | IndPenSim batch 1 | **对照** | 误报检验 |

构成：5 故障 + 3 对照，覆盖连续化工 / 泵阀试验台 / 批式发酵三类工艺。
**真值隔离**：故障场景的标准答案（truth + 判定关键词）只存在于评分器使用的
`scripts/benchmark/cases/benchmark_cases.json`，不在任何管线可见输入、
brief 或本文档中出现。对照场景在上表已明示（这是评分协议的一部分）。

## 3. 快速开始（审稿人 / 复现者）

```bash
node scripts/benchmark/run-benchmark.mjs
```

一键执行 S0→S6 六阶段（环境检查 → 确定性统计 → 盲诊任务包 → 现场诊断 →
门禁+评分 → 聚合+复现门禁 → HTML 报告）。任一阶段偏离期望输出即失败退出。
分步操作与每阶段期望输出见 [reproduction-guide.md](reproduction-guide.md)；
诊断 agent 的现场作业规程见 [execution-guide.md](execution-guide.md)。

## 4. 文件地图

| 文件 / 目录 | 内容 |
|---|---|
| [design.md](design.md) | 设计依据：任务口径、指标定义、期刊 baseline 对标（可验证 DOI）、双口径声明、已知缺口、路线图 |
| [execution-guide.md](execution-guide.md) | 管线执行规程：prepare → brief → 现场诊断（note 规程）→ commit → 门禁 → 评分 |
| [reproduction-guide.md](reproduction-guide.md) | 复现手册：逐步命令、期望输出、漂移决策树、真实性保障层 |
| `scripts/benchmark/run-benchmark.mjs` | 审稿人一键入口（S0-S6 fail-fast） |
| `scripts/benchmark/run-tier.mjs` | 分步编排（prepare / notes / brief / commit / status / archive） |
| `scripts/benchmark/zcode_direct_pipeline.mjs` | 管线驱动：prepare（确定性统计）+ diagnose（note → 全套产物 + 门禁 + 评分） |
| `scripts/benchmark/aggregate.mjs` | 指标聚合 → `results/benchmark/metrics.json` + `report.md` |
| `scripts/benchmark/verify-repro.mjs` | 复现性门禁（数据指纹 / 覆盖 / 指标零漂移 / 执行证明） |
| `scripts/benchmark/build-report.mjs` | HTML 评分报告生成（零硬编码数字，派生自 results） |
| `scripts/benchmark/cases/benchmark_cases.json` | 场景定义 + 标准答案（**评分器专用**） |
| `results/benchmark/` | 运行产物：briefs / notes / gradings / journal / metrics / repro_report |
| `experience/benchmark-report.html` | 最终评分报告（自动生成） |
| `experience/results/scorer-discrimination-test.json` | 阴性对照留痕：注入错误诊断 → 评分器判伪 |

## 5. 文档阅读顺序

1. 本 README → 2. [design.md](design.md)（为什么这样评）→
3. [execution-guide.md](execution-guide.md)（怎么跑管线）→
4. [reproduction-guide.md](reproduction-guide.md)（怎么复现与核对）
