# Experience — 基准实验资料库（全库对照实验，tier0+tier2 = 32 场景）

本目录是诊断系统 benchmark 实验的**自包含资料库**：输入数据、运行结果、真值对照、
文献 baseline、以及出版级 HTML 汇总报告。所有数字可回溯、可复现。

## 目录结构

| 路径 | 内容 |
|---|---|
| `benchmark-report.html` | **汇总报告 v2**（32 场景：指标总览+Wilson CI / 5 图 / 机理类别细分 / 口径 A+B 文献对比含区间 / AEI 对标 / 局限声明 / 15 条参考文献）— 浏览器直接打开 |
| `data/inputs_manifest.json` | tier0 场景输入清单（tier2 输入直接引用 prepared 源，见 `results/tier2_main.json`） |
| `data/<case_id>/input.csv` + `case_meta.json` | tier0 场景的标准输入副本与元数据 |
| `results/metrics.json` | 全库聚合指标（32 场景） |
| `results/gradings/<case_id>.json` | 32 份逐场景评分（真值对照 + 门禁检查） |
| `results/journal.jsonl` | 运行日志（追加式） |
| `results/report.md` | Markdown 版结果报告 |
| `results/repro_report.json` | 可复现性门禁（32/32 全绿） |
| `results/dataset_manifest.json` | 数据集指纹（153 条 sha256） |
| `results/tier0_smoke.json` / `tier2_main.json` / `tier_all.json` | case 定义（tier_all = 合并全库） |
| `baselines/baselines.json` | 文献 baseline 数据（口径 A 直比 / 口径 B 参照 / AEI 定性对标） |

## 全库结果（2026-09-12，32 场景 = 25 故障 + 7 对照）

| 指标 | 值 |
|---|---|
| 故障场景 Top-1 / Top-k | **25/25 (100%) / 25/25** |
| **Top-1 Wilson 95% CI** | **[86.7%, 100%]** |
| CDR（Top-1 且 DETERMINED） | **1.00** |
| 正常对照通过 / 误报 | **7/7 / 0** |
| 置信校准 / 过度自信 | **25/25 / 0** |
| 管线门禁（pipeline-finalize） | **32/32 PASS** |
| 可复现门禁 | **REPRODUCIBLE**（153 指纹 / 32 覆盖 / 指标零漂移 / 32 执行证明） |

分数据集故障命中：SKAB 15/15 · TEP 6/6（含难检 d03、粘滞阀 d14）· IndPenSim 4/4。
机理类别 10 类全部命中（入口阀 4、出口阀 2、气蚀 3、不平衡 3、泄漏/水量/高温 3、TEP 组成/压头 2、TEP 冷却水系 4、IPS pH/执行 4）。

## 复现入口

```bash
node scripts/benchmark/author_notes_t0.py && python scripts/benchmark/author_notes_t2.py
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs prepare --tier scripts/benchmark/cases/tier0_smoke.json
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs prepare --tier scripts/benchmark/cases/tier2_main.json
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs commit --tier scripts/benchmark/cases/tier0_smoke.json
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs commit --tier scripts/benchmark/cases/tier2_main.json
python scripts/benchmark/make_tier2.py
node scripts/benchmark/aggregate.mjs --tier-file scripts/benchmark/cases/tier_all.json
node .claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs --tier scripts/benchmark/cases/tier_all.json
```

详细协议与文献对比口径见 `docs/benchmark-design.md`；执行计划见 `docs/benchmark-plan.md`。
