# 基准测试数据集经验库（docs/experience）

> 2026-09-10 · 基于 `docs/dataset-experiment-research.md` 调研落地：数据集拉取 → ZCode 直接作业模式全管线诊断 → benchmark 评分 → 门禁全通过。**Tier-0 冒烟已完成，9/9 run 通过 pipeline-finalize 门禁。**

## 一句话结论

TEP、SKAB、IndPenSim 三类场景共 9 个冒烟用例已用 **ZCode 直接作业模式**（无 OMP/Claude Code，agent 按 skill 协议执行 Step 0–9）跑通完整诊断管线，**全部通过 pipeline-finalize 门禁**：故障组 Top-1 命中 2/6、Top-k 命中 6/6、三态校准 6/6、过度自信 0、正常控制组 3/3 零误报。数据集层面 TEP/SKAB/IndPenSim 已本地化并可被系统分析出根因；SWaT 需 iTrust 申请；FailureSensorIQ 用于 MCQA 对标。

## 最新测试结果（results/benchmark/metrics.json，2026-09-10）

| 指标 | 数值 | 说明 |
|---|---|---|
| 执行 cases | 9/9 | 全部产出 18+ 必需产物并通过门禁 |
| Top-1（故障组） | 2/6 | SKAB 阀门关闭、TEP d01 进料配比阶跃（均 DETERMINED） |
| Top-k | **6/6 (100%)** | 真值根因均进入假设集 |
| 三态校准 | **6/6 (100%)** | 难检故障诚实输出 NEEDS_DATA/COMPETING_SET |
| 过度自信 | 0 | 无"DETERMINED 且错" |
| 正常控制组 | **3/3 通过，0 误报** | 识别出"批次非平稳+脉冲流加≠故障" |
| CDR | 33.3% | 受三态协议约束（见下"如何解读"） |
| 门禁 | **9/9 finalize PASS** | 含 schema/事件序/证据闭环/报告契约 |

**关键个案**：TEP d03（文献公认 PCA 难检）管线输出 NEEDS_DATA 而非强行归因——三态诚实性是本系统相对单 LLM 方法的核心差异点。

## 结果如何复现（一键）

```bash
cd D:/codes/myskills/industrial-deep-diagnostic
# 前置：ind-diag backend 不需要；RAG 不需要（自动降级）
# 1) 数据准备（若 data/benchmark/prepared/ 已存在可跳过；脚本见 scripts/prep_*.py 同目录）
# 2) 全量重跑（约 25 分钟，串行 9 runs）
node --check scripts/benchmark/zcode_direct_pipeline.mjs
rm -rf workspace/diagnostic-runs/*bench_* results/benchmark/journal.jsonl results/benchmark/gradings
for cid in skab_valve1_1 skab_cavitation_13 skab_normal_control tep_d01_ac_feed_ratio tep_d03_hard tep_d00_normal_control indpensim_batch091 indpensim_batch093 indpensim_batch001_control; do
  RD=$(node scripts/benchmark/zcode_direct_pipeline.mjs prepare --case-file scripts/benchmark/cases/tier0_smoke.json --case $cid 2>/dev/null | tail -1 | python -c "import json,sys; print(json.load(sys.stdin)['run_dir'])")
  node scripts/benchmark/zcode_direct_pipeline.mjs diagnose --run-dir "$RD" --case-file scripts/benchmark/cases/tier0_smoke.json --case $cid --note "results/benchmark/notes/$cid.json"
done
# 3) 汇总
node scripts/benchmark/make_dataset_manifest.mjs
node scripts/benchmark/aggregate.mjs   # → results/benchmark/{metrics.json, report.md}
```

确定性保证：数据 sha256 清单校验（dataset_manifest.json）、诊断推理以 note 文件固化（`results/benchmark/notes/*.json`，可人工审阅）、aggregate 相同输入 byte-identical、每 run 全产物+事件日志落盘 `workspace/diagnostic-runs/*_bench_*/`。

## 与其他 baseline 的对比

| 方法 | 口径 | 成绩 | 来源 |
|---|---|---|---|
| **本系统（Tier-0）** | 6 故障 + 3 正常，无真值注入通用推理 | Top-k **100%**、校准 **100%**、误报 **0%**、CDR 33.3%、过度自信 0 | 本地实测 |
| FaultExplainer GPT-4o | TEP 11 可检故障，**根因清单在 prompt 内** | 7/11 = 63.6%（CDR 口径） | 引用 |
| FaultExplainer o1-preview | 同上 | 9/11 = 81.8% | 引用 |
| Gong et al. (JII 2026) | FailureSensorIQ MCQA（非时序诊断） | Llama3.1-8B 36.5%→54.6% | 引用 |
| SKAB leaderboard（Conv-AE 等） | SKAB 检测任务（非根因） | F1 ≈ 0.76–0.78 | 引用 |
| PCA 经典结论 | TEP 难检故障 | IDV 3/9/15 难检——d03 实测复现（NEEDS_DATA） | 本地复现 |

**如何解读**：① 口径不可直接横比——FaultExplainer 把根因清单放进 prompt 且只取 11 个可检故障；本基准是无提示注入的通用推理且包含 1 个文献公认不可检故障（d03），按三态协议输出 NEEDS_DATA 记为校准正确而非失败，CDR 因此被结构性压低。② 更能反映系统价值的三个数：**Top-k 100%**（真值从不缺席）、**校准 100% + 过度自信 0**（知道自己不知道）、**误报 0%**（正常批次不误判）。③ 先验知识暴露：zcode-direct 模式下诊断 agent 对公共基准有教科书先验，分数属上限偏差；正式论文数字应换 backend CLI 模式（agent 无先验）复核。

## 目录

| 文件 | 内容 |
|---|---|
| [01-dataset-catalog.md](01-dataset-catalog.md) | 数据集文献来源/渠道/许可/真值体系 |
| [02-analyzability-assessment.md](02-analyzability-assessment.md) | 逐数据集根因可分析性评估 |
| [03-test-workflow.md](03-test-workflow.md) | backend CLI 模式测试流程（Tier-1 放量用） |
| [04-zcode-direct-mode.md](04-zcode-direct-mode.md) | ZCode 直接作业模式说明与踩坑清单 |
| [ground-truth/](ground-truth/tep-faults.md) | TEP/SKAB/IndPenSim 真值表 |
| [scripts/](scripts/prep_tep.py) | 数据准备脚本 + bench_runner 骨架 |
| `scripts/benchmark/`（仓库根） | **正式 benchmark 基础设施**（驱动/评分/汇总/清单/cases） |
| `results/benchmark/`（仓库根） | **benchmark 产物**（metrics/report/gradings/journal/notes/manifest） |

## 本地数据落点（data/benchmark/）

`tep_braatz_classic/`（30MB）、`skab/`（18MB）、`indpensim/`（2.9GB）、`failuresensoriq/`（150MB）、`prepared/`（诊断用 CSV：tep 8 个、skab 35 个、indpensim 4+100 个）。

## 复现数据拉取

```bash
git clone --depth 1 https://github.com/waico/skab.git data/benchmark/skab                    # 注意：hndrec/SKAB 已失效
git clone --depth 1 https://github.com/camaramm/tennessee-eastman-profBraatz.git data/benchmark/tep_braatz_classic
curl -L -o data/benchmark/indpensim/100_Batches_IndPenSim.zip "https://data.mendeley.com/public-files/datasets/pdnjz7zz5x/files/e7007dff-4061-494f-a9f5-16c20f457d1d/file_downloaded"
git clone --depth 1 https://github.com/IBM/FailureSensorIQ.git data/benchmark/failuresensoriq
# Reinartz TEP（143GB）与 SWaT（申请制）见 01-dataset-catalog.md
```
