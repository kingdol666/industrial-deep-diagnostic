# Experience — 基准实验资料库（Tier-0 全场景对照）

本目录是诊断系统 benchmark 实验的**自包含资料库**：输入数据、运行结果、真值对照、
文献 baseline、以及出版级 HTML 汇总报告。所有数字可回溯、可复现。

## 目录结构

| 路径 | 内容 |
|---|---|
| `benchmark-report.html` | **汇总报告**（出版样式：指标总览 / 4 图 / 逐场景表 / 口径 A+B 文献对比 / AEI 对标 / 协议 / 局限 / 参考文献）— 浏览器直接打开 |
| `data/inputs_manifest.json` | 9 个场景输入清单（来源路径 + sha256 + 行列数 + 工艺描述 + 对照标记） |
| `data/<case_id>/input.csv` + `case_meta.json` | 每个场景的标准输入副本与元数据 |
| `results/metrics.json` | 聚合指标（Top-1 / Top-k / CDR / 校准 / 控制通过 / 误报） |
| `results/gradings/<case_id>.json` | 逐场景评分（真值对照结果 + 门禁检查 + 评分明细） |
| `results/journal.jsonl` | 运行日志（追加式，断点续跑依据） |
| `results/report.md` | Markdown 版结果报告 |
| `results/repro_report.json` | 可复现性门禁结论（数据指纹 / 覆盖 / 指标漂移 / 执行证明） |
| `results/dataset_manifest.json` | 数据集指纹（153 条 sha256） |
| `baselines/baselines.json` | 文献 baseline 数据（口径 A 同任务直比 / 口径 B 参照 / AEI 定性对标） |

## 本轮（2026-09-11）结果一览

| 指标 | 值 |
|---|---|
| 故障场景 Top-1 / Top-k | **6/6 (100%) / 6/6** |
| CDR（Top-1 且 DETERMINED） | **1.00** |
| 正常对照通过 / 误报 | **3/3 / 0** |
| 置信校准 / 过度自信 | **6/6 / 0** |
| 管线门禁（pipeline-finalize） | **9/9 PASS** |
| 可复现门禁 | **REPRODUCIBLE** |

## 复现入口

```bash
node scripts/benchmark/author_notes_t0.py                                            # 诊断推理记录
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs prepare \
     --tier scripts/benchmark/cases/tier0_smoke.json
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs commit \
     --tier scripts/benchmark/cases/tier0_smoke.json
node scripts/benchmark/aggregate.mjs --tier-file scripts/benchmark/cases/tier0_smoke.json
node .claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs
```

详细协议与文献对比口径见 `docs/benchmark-design.md`；执行计划见 `docs/benchmark-plan.md`。
