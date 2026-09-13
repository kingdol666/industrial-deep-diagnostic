# Paper Support — 论文图表 ↔ 证据工件映射

> ⚠️ **2026-09-13 重写。** 旧版描述的是"32 场景 = 25 故障 + 7 对照"的早期设计
> （Top-1 25/25、CI [86.7,100]），与本仓库实际的 **12 场景 = 9 故障 + 3 对照** 不符，
> 并引用了多份**不存在**的文件（`experience/baselines/baselines.json`、
> `scripts/benchmark/author_notes_t0/t2.py`、`experience/results/tier_all.json` 等）。
> 旧版内容全部作废。审计背景见 `docs/benchmark/AUDIT-2026-09-13.md`。

论文：`paper/main.tex`（AEI 投稿）。以下为**现存可核验**工件的映射。

## 基准实际规模（一切数字的基准）

| 项 | 值 | 来源 |
|---|---|---|
| 场景总数 | 12 | `scripts/benchmark/cases/benchmark_cases.json` |
| 故障 / 对照 | 9 / 3 | 同上 |
| 分数据集 | SKAB 3（2+1）· TEP 7（6+1）· IndPenSim 2（1+1） | 同上 |
| Top-1 | 9/9，Wilson 95% CI [70.1, 100.0] | `results/benchmark/metrics.json` |
| CDR（比率） | 1.00（9/9） | `metrics.json` 的 `cdr` / `cdr_display` |
| 校准 / 过度自信 | 9/9 / 0 | `metrics.json` |
| 对照通过 / 误报 | 3/3 / 0 | `metrics.json` |
| judge 均分 | 91.0（**agent 自报，非独立评分**） | `gradings/*.json` 的 `judge_score_source` |

## 图（Figures）— `paper/figures/`

| 文件 | 论文位置 | 数据来源 |
|---|---|---|
| `fig_pipeline.png` | Fig. 1 管线 | `docs/architecture/`、`AGENTS.md` 管线定义 |
| `fig_benchmark.png` | Fig. 2 基准构成与结果 | `results/benchmark/metrics.json`（`by_dataset`）+ `gradings/*.json` |
| `fig_tep_perfault.png` | Fig. 3 逐故障对比 | `scripts/benchmark/cases/benchmark_cases.json` 的 `literature_baseline`（**引用值，非复现值**） |
| `fig_forest.png` | Fig. 4 Wilson CI 对比 | 同上 + `metrics.json` |
| `fig_calibration.png` | Fig. 5 置信校准 | `gradings/*.json` + `notes/*.note.json` 的 `confidence` |

> 生成脚本：`paper/figures-html/*.html`（若图表需重绘，先确认其数据源与上表一致）。

## 表（Tables）

| 论文表 | 内容 | 数据来源 | 状态 |
|---|---|---|---|
| Table 1 相关工作定位 | 定性对比 | `docs/benchmark/design.md` §4 + refs.bib | ✅ |
| Table 2 基准构成 | 12 = 9 + 3 | `scripts/benchmark/cases/benchmark_cases.json` | ✅ |
| Table 3 总指标 | Top-1 9/9、CDR 1.00、校准 9/9、误报 0 | `results/benchmark/metrics.json` | ⚠️ judge 分数需标注自报性质 |
| Table 4 逐故障对比 | IDV1/3/4/7/11/14 | case 文件的 `literature_baseline` + `gradings/*.json` | ⚠️ 口径不同，须声明非同指标 |
| Table 5 逐场景机理 | 9 行 | `gradings/*.json` + `briefs/*.brief.json` 的统计量 | ⚠️ 受 C1 泄漏影响，待重跑 |

## 可复现声明支撑

| 声明 | 工件 | 状态 |
|---|---|---|
| 数据指纹零漂移 | `results/benchmark/dataset_manifest.json`（153 条）+ `data/benchmark/downloads.lock.json` | ✅ 已核 |
| 12/12 执行证明 PASS | `gradings/*.json` 的 `checks.pipeline_log` + 各 run 的 `.pipeline_events.jsonl` | ✅ 已核 |
| 统计层全量执行（无降级） | `gradings/*.json` 的 `checks.statistics_engine` / `stats_degraded` / `anti_spurious_executed` | ✅ 12/12 `stats-package`、`anti_spurious_executed=true` |
| 指标重算一致 | `results/benchmark/repro_report.json`（REPRODUCIBLE） | ✅ 已核 |
| 真值隔离 | `scripts/benchmark/check-leakage.mjs` | ⚠️ **2026-09-13 才存在**；此前 5/6 TEP 场景泄漏 |
| 独立质量审计 | `scripts/benchmark/audit-structural.mjs` → `results/benchmark/structural_audit.json` | ✅ 12/12 得 100；**是地板非排名**（不能区分结论对错） |
| judge 分数谱系 | `gradings/*.json` 的 `judge_score_source: "note-self-declared"` | ⚠️ 10 维实测全为同一数字，**零判别力**（详见审计文档 D1） |
| 推理留痕 | `results/benchmark/notes/*.note.json` | ✅ 存在 |
| **delete-and-rebuild 审计** | **无实现脚本** | ❌ **论文已改写为不依赖该声明**（改为"统计层逐字节可复现 + 推理层随机"两层陈述） |
| 复现命令 | `docs/benchmark/reproduction-guide.md` | ✅ 已重写为 12 场景 |

## 不能引用的路径（旧版遗留，均已核实不存在）

- `experience/baselines/baselines.json` ❌
- `scripts/benchmark/author_notes_t0/`、`scripts/benchmark/author_notes/` ❌
- `experience/results/tier_all.json`、`tier2_main.json` ❌
- `docs/benchmark-design.md`（实际路径为 `docs/benchmark/design.md`）❌

## 期刊对标要点（AEI）

- 同源 AEI 文献：STACGG 根因定位（10.1016/j.aei.2025.103765）、因果知识图谱 RCA
  （10.1016/j.aei.2023.102057）、无标签评估（10.1016/j.aei.2024.102912）——**定性对标，数字未核实不引用**。
- **口径区别必须写明**：FaultExplainer（C&CE 2025）的 7/11、9/11 是
  **故障类别命中率**（prompt 内含候选根因清单、接受别名匹配）；
  IDD 的数字是**机制关键词严格匹配率**（无候选清单）。
  **二者不是同一个指标**，不可相减、不可作显著性检验。
- 口径 B（仅参照，不排名）：Pozdnyakov (OJIES 2024)、Hartung (arXiv 2023)、
  Iliopoulos (2023)、Vieira (MSSP 2026) —— 均为 sample-level 检测/分类指标。
