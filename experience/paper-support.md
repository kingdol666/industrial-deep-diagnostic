# Paper Support — 论文图表 ↔ 证据工件映射

论文（`paper/main.tex`，AEI 投稿）的每个数字与图表均由本仓库工件支撑。审稿核对路径如下。

## 图（Figures）

| 论文图 | 内容 | 生成/数据来源 |
|---|---|---|
| Fig. 1 | 9 步管线 + 质量门（TikZ） | `docs/publication-strategy-report.md` §1.1 流程、`AGENTS.md` 管线定义 |
| Fig. 2 | 分数据集命中柱状 | `experience/results/metrics.json` (`by_dataset`) |
| Fig. 3 | 机理类别细分条形 | `experience/results/gradings/*.json`（32 份逐场景评分） |
| Fig. 4 | vs FaultExplainer（Wilson CI） | `experience/baselines/baselines.json`（口径 A）+ `metrics.json` |
| Fig. 5 | 置信校准散点 | 各 `gradings/<case>.json` 的 confidence + 证据级别上限 |

## 表（Tables）

| 论文表 | 内容 | 数据来源 |
|---|---|---|
| Table 1 | 相关工作定位 | `docs/benchmark-design.md` §2（可验证 DOI）+ `docs/publication-strategy-report.md` §2 |
| Table 2 | 基准构成（32 = 25 故障 + 7 对照） | `experience/results/tier_all.json` + `tier2_main.json` |
| Table 3 | 总指标（Top-1 25/25, CI [86.7,100], CDR 1.00, 校准 25/25, 误报 0） | `experience/results/metrics.json`（verify-repro 已核） |
| Table 4 | 机理类别细分（10 类，n/Top-1/指纹） | `experience/results/gradings/*` + 各 `prepare_digest.json` |
| Table 5 | 文献对比（口径 A：FaultExplainer 63.6/81.8；口径 B：Pozdnyakov/Hartung/Iliopoulos/Vieira） | `experience/baselines/baselines.json` |

## 可复现声明支撑

| 声明 | 工件 |
|---|---|
| 数据指纹 153 条零漂移 | `results/dataset_manifest.json` + `data/benchmark/downloads.lock.json` |
| 32/32 执行证明 PASS | `results/gradings/*.json` 的 `checks.pipeline_log` + 各 run 目录 `.pipeline_events.jsonl` |
| 指标重算一致 | `results/repro_report.json`（REPRODUCIBLE） |
| 真值隔离与推理留痕 | `scripts/benchmark/author_notes_t0/t2.py` + `results/benchmark/notes/*.note.json` |
| 复现命令 | `experience/README.md` §复现入口 |

## 期刊对标要点（AEI）

- 最同源 AEI 文献：STACGG 根因定位（10.1016/j.aei.2025.103765）、因果知识图谱 RCA（10.1016/j.aei.2023.102057）、无标签评估（10.1016/j.aei.2024.102912）——定性对标，数字未核实不引用。
- 口径 A 直比：FaultExplainer（C&CE 2025，7/11 与 9/11）；口径 B 参照：Pozdnyakov (OJIES 2024)、Hartung (arXiv 2023)、Iliopoulos (2023)、Vieira (MSSP 2026)。
