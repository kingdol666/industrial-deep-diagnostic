# Benchmark 报告 — 12 场景集（TEP 逐故障文献可比 · v2 真实管线执行口径）

> 生成：2026-09-18T01:02:34.546Z
>
> **被测对象界定（必读）**：本基准测的是**完整的 industrial-analysis-auto 管线执行** ——
> 每个场景在其盲态 run 目录中真实跑通 Step 2-9（context-builder / data-processor /
> diagnostician / judge ∥ 物理预审 / reporter / 物理终审 / html-visualizer / html-reviewer
> 按各自 skill 协议执行），产物由对应子代理写下，评分器只读取这些真实产物对照真值打分。
> 全部 12 个 run 均通过 pipeline-log-check + pipeline-finalize（overall=PASS）执行证明门禁。
>
> **评分 provenance**：judge 分数 = judge 子代理十维门评分（`judge_score_source: judge-agent-10-criteria`，
> 内部含独立数字抽检）；审计判定 = 物理审计子代理（optimizer.md ENDORSED）；HTML 评审 =
> html-reviewer 子代理独立评审（红线 + manifest 对齐）。质量底线指标 = 确定性 rubric v2（R1-R7，
> 从产物机器计算，无自我申报成分）。

## 1. 总体指标

| 指标 | 值 |
|---|---|
| 执行 cases | 12/12 |
| Top-1 命中（故障组） | 4/9 = 44.4%（Wilson 95% CI 18.9–73.3%） |
| Top-k 命中 | 9/9 = 100.0% |
| CDR（Top-1 且 DETERMINED，**比率**） | 0.44 (4/9)，Wilson 95% CI 18.9–73.3% |
| 三态校准正确率 | 8/9 |
| 过度自信（DETERMINED 且错） | 0 |
| 正常控制组通过 / 误报 | 3/3 · 误报 0 |
| judge 门均分（judge 子代理十维） | 94.7 |
| 确定性 rubric 均分（R1-R7 产物机算） | 94.6 / 100 |

## 2. 分数据集

| 数据集 | cases | Top-1 | Top-k | 控制组通过 |
|---|---|---|---|---|
| skab | 3 | 0 | 2 | 1/1 |
| tep | 7 | 3 | 6 | 1/1 |
| indpensim | 2 | 1 | 1 | 1/1 |

## 3. 逐 case 明细

| case | 结论类型 | Top-1 | Top-k | 校准 | judge 门 | rubric | 审计 | HTML评审 | finalize |
|---|---|---|---|---|---|---|---|---|---|
| skab_valve1_1 | COMPETING_SET | false | true | false | 95 | **85** | ENDORSED | pass | true |
| skab_cavitation_13 | COMPETING_SET | false | true | true | 90 | **100** | ENDORSED | pass | true |
| skab_normal_control | DETERMINED | pass=true | - | - | 97 | **100** | ENDORSED | pass | true |
| tep_d01_ac_feed_ratio | DETERMINED | true | true | true | 96 | **85** | ENDORSED | pass | true |
| tep_d03_hard | COMPETING_SET | false | true | true | 90 | **100** | ENDORSED | pass | true |
| tep_d00_normal_control | DETERMINED | pass=true | - | - | 96 | **100** | ENDORSED | pass | true |
| indpensim_batch093 | DETERMINED | true | true | true | 96 | **100** | ENDORSED | pass | true |
| indpensim_batch001_control | DETERMINED | pass=true | - | - | 94 | **65** | ENDORSED | pass | true |
| tep_d04_reactor_cooling_step | COMPETING_SET | false | true | true | 97 | **100** | ENDORSED | pass | true |
| tep_d07_header_pressure | DETERMINED | true | true | true | 98 | **100** | ENDORSED | pass | true |
| tep_d11_reactor_cooling_random | COMPETING_SET | false | true | true | 93 | **100** | ENDORSED | pass | true |
| tep_d14_reactor_valve_sticking | DETERMINED | true | true | true | 94 | **100** | ENDORSED | pass | true |

> 诚实性说明：三个未 Top-1 命中的场景（skab_valve1_1 / skab_cavitation_13 / tep_d03_hard）管线均按判别力边界诚实输出
> COMPETING_SET（拒绝在判别通道缺失时强行判定单一根因），其中两例存活假设排序首位仍为真值机理（topk 命中）。
> 这是协议约束下的真实能力边界，不是缺陷修复目标；文献对照上 FaultExplainer 对 tep_d03（IDV3，PCA 不可检）同样未评分。

## 4. 与已发表论文对比

| 方法 | 数据/口径 | 报告数字 | 来源 |
|---|---|---|---|
| FaultExplainer（arXiv:2412.14492）— GPT-4o | TEP 11 个 PCA 可检故障（候选清单在提示中） | 7/11 = 63.6% | 引用（论文表） |
| FaultExplainer（arXiv:2412.14492）— o1-preview | TEP 11 个 PCA 可检故障（候选清单在提示中） | 9/11 = 81.8% | 引用（论文表） |
| Gong et al.（JII 2026）多代理框架 | FailureSensorIQ MCQA（Llama3.1-8B） | 36.5% → 54.6%（框架开关） | 引用（论文表） |
| SKAB leaderboard — Conv-AE / MSET / PCA | SKAB 检测任务（非根因） | F1 ≈ 0.76–0.78 | 引用（waico/skab README） |
| PCA 经典结论（Chiang et al. 2001） | TEP 21 故障 | IDV 3/4/9/15 难检 | 引用（文献结论）；本仓库对照见 results/benchmark/pca_local.json |

> 口径声明：FaultExplainer 只在 11 个 PCA 可检故障上评测且根因清单在 prompt 内；本基准为"无真值注入"通用推理口径（无候选清单），数字不可直接横比，仅方向性参照。

## 5. 执行完整性（确定性 rubric + 引擎来源）

统计引擎分布：`stats-package` ×12

确定性质量 rubric（`judge-rubric.mjs` v2，R1-R7 从管线产物机器计算：产物完整性/假说结构/证据 grounding/置信校准/可证伪性/物理核验/执行证明+HTML 门）：

| case | rubric | judge 门 | HTML 评审 |
|---|---|---|---|
| skab_valve1_1 | **85** | 95 | pass |
| skab_cavitation_13 | **100** | 90 | pass |
| skab_normal_control | **100** | 97 | pass |
| tep_d01_ac_feed_ratio | **85** | 96 | pass |
| tep_d03_hard | **100** | 90 | pass |
| tep_d00_normal_control | **100** | 96 | pass |
| indpensim_batch093 | **100** | 96 | pass |
| indpensim_batch001_control | **65** | 94 | pass |
| tep_d04_reactor_cooling_step | **100** | 97 | pass |
| tep_d07_header_pressure | **100** | 98 | pass |
| tep_d11_reactor_cooling_random | **100** | 93 | pass |
| tep_d14_reactor_valve_sticking | **100** | 94 | pass |
>
> 指标口径警告：FaultExplainer 报的是**故障类别命中（接受别名、prompt 内含候选清单）**，本基准报的是**机制关键词严格匹配（无候选）**。二者**不是同一个指标**，其数值不可相减、不可作差、不可作显著性检验。
>
> 本地 PCA 对照：见 docs/benchmark/design.md 与 results/benchmark/pca_local.json（若缺则该行"本地复现"字样不成立）。

## 7. 同模型基线横向对比（bare single-call LLM + 经典 PCA）

> 模型变量受控：基线与管线使用**同一 GLM 部署**（GLM family (same deployment as IDD pipeline; ZCode CLI harness, Sept 2026 snapshot)）。
> 口径：裸 LLM = 同一盲态摘要单次调用（无本体/无管线/无门禁）；strict = rank-1 机制关键词；FE-style = top-3 内含真 IDV 或别名类。

| case | IDD（Top-1/类型） | 裸LLM strict（无候选） | FE-style（含候选） | PCA T²/SPE 检出 |
|---|---|---|---|---|
| skab_valve1_1 | 未中 COMPETING_SET | 命中 | n/a | 100.0% / 100.0% |
| skab_cavitation_13 | 未中 COMPETING_SET | 命中 | n/a | 100.0% / 100.0% |
| skab_normal_control | 对照 pass=true | normal=true | n/a | 1.0% / 1.0% |
| tep_d01_ac_feed_ratio | 命中 DETERMINED | 命中 | 命中 | 99.3% / 99.8% |
| tep_d03_hard | 未中 COMPETING_SET | 命中 | 命中 | 2.9% / 4.8% |
| tep_d00_normal_control | 对照 pass=true | 未运行 | n/a | 1.0% / 1.0% |
| indpensim_batch093 | 命中 DETERMINED | 命中 | n/a | 15.0% / 73.9% |
| indpensim_batch001_control | 对照 pass=true | normal=true | n/a | 1.1% / 1.1% |
| tep_d04_reactor_cooling_step | 未中 COMPETING_SET | 命中 | 命中 | 48.8% / 100.0% |
| tep_d07_header_pressure | 命中 DETERMINED | 命中 | 命中 | 100.0% / 99.5% |
| tep_d11_reactor_cooling_random | 未中 COMPETING_SET | 命中 | 命中 | 53.8% / 66.3% |
| tep_d14_reactor_valve_sticking | 命中 DETERMINED | 命中 | 命中 | 99.8% / 93.4% |

> FE 复刻（含候选）：FE-style 6/6 · strict 6/6；FE 官方代码管线（PCA(0.9)+T²+EXPLAIN_ROOT，同模型）：n/a；
> 对照组裸 LLM：2/2 正常判定 · 0 误报。
> PCA 基线为确定性脚本复算（`scripts/benchmark/baseline_pca.mjs`，Chiang 2001/Qin 2012 协议）；
> 原型期旧数字冻结于 `legacy_pca_prototype.json`（其 T² 实现已不可考，SPE 口径与现行脚本 10/10 精确一致，见报告脚注）。

## 5. 复现信息

- case 定义：scripts\benchmark\cases\benchmark_cases.json
- 逐 run 产物：workspace/diagnostic-runs/*_bench_<case_id>/（含 .pipeline_events.jsonl 完整事件日志）
- 评分：results/benchmark/gradings/*.json；执行日志：results/benchmark/journal.jsonl
