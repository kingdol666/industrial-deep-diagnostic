# Benchmark 报告 — 12 场景集（TEP 逐故障文献可比）

> 生成：2026-09-13T16:20:53.203Z
>
> ⚠️ **被测对象界定（必读）**：本基准测的是**推理层** —— 由 1 次 LLM 推理消费预计算的统计 brief
> 并产出一份符合诊断协议的 note，随后由模板展开为完整产物集。它**不包含**
> context-builder / data-processor / diagnostician / judge / 物理审计 等 14 个 agent 的编排执行。
> 因此本报告的数字**不是**"14-agent 管线整体"的性能，引用时必须保留此界定。
>
> ⚠️ **judge 分数不是判断**：展开步骤把所有 10 个维度都设为 `Math.round(note.judge.score/10)`
> （`zcode_direct_pipeline.mjs:503`），实测 12 次运行中每个维度都恰好是 9，
> 即"10 维质量门"不携带任何判别信息。请改看第 5 节的**独立结构审计**分数。

## 1. 总体指标

| 指标 | 值 |
|---|---|
| 执行 cases | 12/12 |
| Top-1 命中（故障组） | 9/9 = 100.0%（Wilson 95% CI 70.1–100.0%） |
| Top-k 命中 | 9/9 = 100.0% |
| CDR（Top-1 且 DETERMINED，**比率**） | 1.00 (9/9)，Wilson 95% CI 70.1–100.0% |
| 三态校准正确率 | 9/9 |
| 过度自信（DETERMINED 且错） | 0 |
| 正常控制组通过 / 误报 | 3/3 · 误报 0 |
| judge 分数 | **agent 自报（note.judge.score），非独立评分；10 维全为同一数字，无判别力** —— mean 91.0 |
| 独立结构审计均分 | 100（覆盖 12/12；越低表示产物越不完整） |

## 2. 分数据集

| 数据集 | cases | Top-1 | Top-k | 控制组通过 |
|---|---|---|---|---|
| skab | 3 | 2 | 2 | 1/1 |
| tep | 7 | 6 | 6 | 1/1 |
| indpensim | 2 | 1 | 1 | 1/1 |

## 3. 逐 case 明细

| case | 结论类型 | Top-1 | Top-k | 校准 | judge（自报，无判别力） | **独立结构审计** | 未达项 | finalize |
|---|---|---|---|---|---|---|---|---|
| skab_valve1_1 | DETERMINED | true | true | true | 92 | **100** | 0 | true |
| skab_cavitation_13 | DETERMINED | true | true | true | 92 | **100** | 0 | true |
| skab_normal_control | DETERMINED | null | null | null | 91 | **100** | 0 | true |
| tep_d01_ac_feed_ratio | DETERMINED | true | true | true | 92 | **100** | 0 | true |
| tep_d03_hard | DETERMINED | true | true | true | 90 | **100** | 0 | true |
| tep_d00_normal_control | DETERMINED | null | null | null | 91 | **100** | 0 | true |
| indpensim_batch093 | DETERMINED | true | true | true | 91 | **100** | 0 | true |
| indpensim_batch001_control | DETERMINED | null | null | null | 90 | **100** | 0 | true |
| tep_d04_reactor_cooling_step | DETERMINED | true | true | true | 92 | **100** | 0 | true |
| tep_d07_header_pressure | DETERMINED | true | true | true | 91 | **100** | 0 | true |
| tep_d11_reactor_cooling_random | DETERMINED | true | true | true | 90 | **100** | 0 | true |
| tep_d14_reactor_valve_sticking | DETERMINED | true | true | true | 90 | **100** | 0 | true |

## 4. 与已发表论文对比

| 方法 | 数据/口径 | 报告数字 | 来源 |
|---|---|---|---|
| FaultExplainer（C&CE 2025）— GPT-4o | TEP 11 个 PCA 可检故障 | 7/11 = 63.6% | 引用（论文表） |
| FaultExplainer（C&CE 2025）— o1-preview | TEP 11 个 PCA 可检故障 | 9/11 = 81.8% | 引用（论文表） |
| Gong et al.（JII 2026）多代理框架 | FailureSensorIQ MCQA（Llama3.1-8B） | 36.5% → 54.6%（框架开关） | 引用（论文表） |
| SKAB leaderboard — Conv-AE / MSET / PCA | SKAB 检测任务（非根因） | F1 ≈ 0.76–0.78 | 引用（waico/skab README） |
| PCA 经典结论（Chiang et al. 2001） | TEP 21 故障 | IDV 3/4/9/15 难检 | 引用（文献结论）；本仓库对照见 results/benchmark/pca_local.json |

> 口径声明：FaultExplainer 只在 11 个 PCA 可检故障上评测且根因清单在 prompt 内；本基准为"无真值注入"通用推理口径，数字不可直接横比，仅方向性参照。

## 5. 执行完整性（独立结构审计 + 引擎来源）

统计引擎分布：`stats-package` ×12

独立结构审计（`audit-structural.mjs`，10 维加权，越低表示产物越不完整）替代了无判别力的自报 judge 分数：

| case | 结构审计 | 自报 judge | 未达项数 |
|---|---|---|---|
| skab_valve1_1 | **100** | 92 | 0 |
| skab_cavitation_13 | **100** | 92 | 0 |
| skab_normal_control | **100** | 91 | 0 |
| tep_d01_ac_feed_ratio | **100** | 92 | 0 |
| tep_d03_hard | **100** | 90 | 0 |
| tep_d00_normal_control | **100** | 91 | 0 |
| indpensim_batch093 | **100** | 91 | 0 |
| indpensim_batch001_control | **100** | 90 | 0 |
| tep_d04_reactor_cooling_step | **100** | 92 | 0 |
| tep_d07_header_pressure | **100** | 91 | 0 |
| tep_d11_reactor_cooling_random | **100** | 90 | 0 |
| tep_d14_reactor_valve_sticking | **100** | 90 | 0 |
>
> 指标口径警告：FaultExplainer 报的是**故障类别命中（接受别名、prompt 内含候选清单）**，本基准报的是**机制关键词严格匹配（无候选）**。二者**不是同一个指标**，其数值不可相减、不可作差、不可作显著性检验。
>
> 本地 PCA 对照：见 docs/benchmark/design.md 与 results/benchmark/pca_local.json（若缺则该行"本地复现"字样不成立）。

## 5. 复现信息

- case 定义：scripts\benchmark\cases\benchmark_cases.json
- 逐 run 产物：workspace/diagnostic-runs/*_bench_<case_id>/（含 .pipeline_events.jsonl 完整事件日志）
- 评分：results/benchmark/gradings/*.json；执行日志：results/benchmark/journal.jsonl
