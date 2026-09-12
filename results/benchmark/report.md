# Benchmark 报告 — 多场景根因诊断（Tier-0 冒烟）

> 生成：2026-09-12T08:02:58.976Z · 执行模式：ZCode 直接作业（无 OMP/Claude Code，agent 按 skill 协议执行 Step 0–9）

## 1. 总体指标

| 指标 | 值 |
|---|---|
| 执行 cases | 32/32 |
| Top-1 命中（故障组） | 25/25 = 100.0% |
| Top-k 命中 | 25/25 = 100.0% |
| CDR（Top-1 且 DETERMINED） | 1 |
| 三态校准正确率 | 25/25 |
| 过度自信（DETERMINED 且错） | 0 |
| 正常控制组通过 / 误报 | 7/7 · 误报 0 |

## 2. 分数据集

| 数据集 | cases | Top-1 | Top-k | 控制组通过 |
|---|---|---|---|---|
| skab | 17 | 15 | 15 | 2/2 |
| tep | 8 | 6 | 6 | 2/2 |
| indpensim | 7 | 4 | 4 | 3/3 |

## 3. 逐 case 明细

| case | 结论类型 | Top-1 | Top-k | 校准 | judge | finalize |
|---|---|---|---|---|---|---|
| skab_valve1_1 | DETERMINED | true | true | true | 93 | true |
| skab_cavitation_13 | DETERMINED | true | true | true | 92 | true |
| skab_normal_control | DETERMINED | null | null | null | 91 | true |
| tep_d01_ac_feed_ratio | DETERMINED | true | true | true | 90 | true |
| tep_d03_hard | DETERMINED | true | true | true | 90 | true |
| tep_d00_normal_control | DETERMINED | null | null | null | 91 | true |
| indpensim_batch091 | DETERMINED | true | true | true | 90 | true |
| indpensim_batch093 | DETERMINED | true | true | true | 90 | true |
| indpensim_batch001_control | DETERMINED | null | null | null | 92 | true |
| skab2_valve1_1 | DETERMINED | true | true | true | 93 | true |
| skab2_valve1_7 | DETERMINED | true | true | true | 90 | true |
| skab2_valve1_12 | DETERMINED | true | true | true | 90 | true |
| skab2_valve2_0 | DETERMINED | true | true | true | 91 | true |
| skab2_valve2_2 | DETERMINED | true | true | true | 91 | true |
| skab2_other_13 | DETERMINED | true | true | true | 92 | true |
| skab2_other_12 | DETERMINED | true | true | true | 91 | true |
| skab2_other_5 | DETERMINED | true | true | true | 91 | true |
| skab2_other_6 | DETERMINED | true | true | true | 90 | true |
| skab2_other_8 | DETERMINED | true | true | true | 92 | true |
| skab2_other_1 | DETERMINED | true | true | true | 90 | true |
| skab2_other_11 | DETERMINED | true | true | true | 90 | true |
| skab2_other_14 | DETERMINED | true | true | true | 92 | true |
| skab2_normal_control | DETERMINED | null | null | null | 91 | true |
| tep2_d04 | DETERMINED | true | true | true | 91 | true |
| tep2_d07 | DETERMINED | true | true | true | 90 | true |
| tep2_d11 | DETERMINED | true | true | true | 90 | true |
| tep2_d14 | DETERMINED | true | true | true | 90 | true |
| tep2_d00_control | DETERMINED | null | null | null | 91 | true |
| ips2_batch_091 | DETERMINED | true | true | true | 90 | true |
| ips2_batch_093 | DETERMINED | true | true | true | 90 | true |
| ips2_batch_001 | DETERMINED | null | null | null | 92 | true |
| ips2_batch_002 | DETERMINED | null | null | null | 91 | true |

## 4. 与已发表论文对比

| 方法 | 数据/口径 | 报告数字 | 来源 |
|---|---|---|---|
| FaultExplainer（C&CE 2025）— GPT-4o | TEP 11 个 PCA 可检故障 | 7/11 = 63.6% | 引用（论文表） |
| FaultExplainer（C&CE 2025）— o1-preview | TEP 11 个 PCA 可检故障 | 9/11 = 81.8% | 引用（论文表） |
| Gong et al.（JII 2026）多代理框架 | FailureSensorIQ MCQA（Llama3.1-8B） | 36.5% → 54.6%（框架开关） | 引用（论文表） |
| SKAB leaderboard — Conv-AE / MSET / PCA | SKAB 检测任务（非根因） | F1 ≈ 0.76–0.78 | 引用（waico/skab README） |
| PCA 经典结论（Chiang et al. 2001） | TEP 21 故障 | IDV 3/9/15 难检 | 本地复现：pca_baseline.py（Tier-1） |

> 口径声明：FaultExplainer 只在 11 个 PCA 可检故障上评测且根因清单在 prompt 内；本基准为"无真值注入"通用推理口径，数字不可直接横比，仅方向性参照。

## 5. 复现信息

- case 定义：scripts\benchmark\cases\tier_all.json
- 逐 run 产物：workspace/diagnostic-runs/*_bench_<case_id>/（含 .pipeline_events.jsonl 完整事件日志）
- 评分：results/benchmark/gradings/*.json；执行日志：results/benchmark/journal.jsonl
