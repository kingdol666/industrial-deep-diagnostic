# 复现手册 — 审稿人逐步执行与核对

> 目标：审稿人（或任何无记忆的 agent）按本手册执行，能在本仓库复现
> 8 场景诊断基准的全部结果：每场景 `report.md` + `diagnostic-report.html`、
> 逐场景评分、总体指标、HTML 评分报告。
> 设计依据见 [design.md](design.md)，诊断 agent 作业规程见 [execution-guide.md](execution-guide.md)。

---

## 0. 前置条件

```bash
node .claude/shared/scripts/uv_env_setup.mjs   # Python venv（stats 包需要）
# 数据已在仓库内：data/benchmark/prepared/{skab,tep,indpensim*}/（sha256 见 dataset_manifest）
```

## 1. 一键复现（推荐）

```bash
node scripts/benchmark/run-benchmark.mjs
```

六阶段串行、fail-fast。成功输出：

```
IDD Diagnosis Benchmark — PASSED
Scoring report : experience/benchmark-report.html
Metrics        : results/benchmark/metrics.json
Per-scenario   : results/benchmark/gradings/*.json (truth-compared)
Exec. proofs   : per-run .pipeline_events.jsonl (gate-checked)
```

**S3 阶段会中断一次**（"N scenario(s) need on-the-spot diagnosis"）——这是设计行为：
诊断是唯一 agent-in-the-loop 环节。此时按 §2 完成现场诊断后**重跑同一条命令**
（已完成的阶段自动通过：prepare 复用 run 目录，note 齐全后继续 S4-S6）。

可复用已有 run 目录跳过重统计：`node scripts/benchmark/run-benchmark.mjs --skip-prepare`。

## 2. 现场诊断操作（S3，唯一人工环节）

```bash
node scripts/benchmark/run-tier.mjs notes        # 生成 8 份 note 骨架（已存在则保留）
```

然后对每个场景：

1. **只读** `results/benchmark/briefs/<case>.brief.json`（统计证据，无真值）；
2. 按 `industrial-diagnostician` 协议推理：≥3 竞争假设 → 判别/排除 → 三态结论；
3. 填写 `results/benchmark/notes/<case>.note.json`（删除 `_instructions` 键）。

真实性红线（详见 execution-guide §4）：证据必须引用 brief 数字；禁止读
`results/benchmark/gradings/*`、`scripts/benchmark/cases/*` 真值字段、其他 note。

## 3. 分步执行（与一键等价，便于定位失败）

| 步骤 | 命令 | 期望输出 |
|---|---|---|
| S1 | `node scripts/benchmark/run-tier.mjs prepare --tier scripts/benchmark/cases/benchmark_cases.json --force` | 8 个 `workspace/diagnostic-runs/<ts>_bench_<case>/` + 各自 `prepare_digest.json` |
| S2 | `node scripts/benchmark/run-tier.mjs brief --tier …` | `results/benchmark/briefs/*.brief.json`（8 份） |
| S3 | 按 §2 填 8 份 note | `results/benchmark/notes/*.note.json` 全部填完 |
| S4 | `node scripts/benchmark/run-tier.mjs commit --tier …` | `[commit] <case> — top1=… judge=…` ×8，0 skipped |
| S5 | `node scripts/benchmark/aggregate.mjs --tier-file scripts/benchmark/cases/benchmark_cases.json` | `results/benchmark/metrics.json` + `report.md` |
| S5b | `node scripts/benchmark/verify-repro.mjs --tier …` | `status: REPRODUCIBLE`（退出码 0） |
| S6 | `node scripts/benchmark/build-report.mjs` | `experience/benchmark-report.html` |

状态总览：`node scripts/benchmark/run-tier.mjs status`（prepared / note / graded 三态表）。

## 4. 逐项核对清单（评审验收点）

- [ ] **每场景两份报告存在**：`workspace/diagnostic-runs/<ts>_bench_<case>/report.md`
      与 `diagnostic-report.html`（run 目录见 `results/benchmark/tier_state.json`）
- [ ] **执行证明**：每个 run 的 `.pipeline_events.jsonl` 通过
      `pipeline-log-check.mjs`；grading 中 `checks.finalize_passed = true`（8/8）
- [ ] **独立评分可追溯**：`results/benchmark/gradings/<case>.json` 逐场景给出
      top1/topk/calibrated 判定与 run_dir；truth 只出现在
      `scripts/benchmark/cases/benchmark_cases.json`
- [ ] **总体指标**：`results/benchmark/metrics.json` —— Top-1、CDR、
      校准、对照组通过/误报；HTML 报告中所有比例均带 Wilson 95% CI
- [ ] **复现门禁**：`results/benchmark/repro_report.json` status = REPRODUCIBLE
      （数据 sha256 重哈希、场景覆盖、指标零漂移、执行证明四查全过）
- [ ] **评分器判别力**：`experience/results/scorer-discrimination-test.json`
      —— 注入"plausible-but-wrong"诊断被评分器判伪（top1=false）
- [ ] **盲诊协议**：briefs 目录内文件不含 truth/keywords 字段（可抽查
      `results/benchmark/briefs/*.brief.json`）

## 5. 漂移决策树（失败时）

| 症状 | 诊断 | 处置 |
|---|---|---|
| S0 报缺 venv | Python 环境未建 | `node .claude/shared/scripts/uv_env_setup.mjs` |
| S0 报 case contract | 场景集被改动 | 恢复 `scripts/benchmark/cases/benchmark_cases.json`（8 场景 / 5 故障 + 3 对照） |
| S1 某场景统计失败 | stats 包异常（如含 NaN 列） | 属预期降级：digest 标 `driver-js-fallback`，继续；若 run 目录未建则单独重跑该 case prepare |
| S3 反复列缺 note | note 未填或仍是模板 | 检查 note 已删除 `_instructions` 且各必填字段完整（`run-tier.mjs status`） |
| S4 `skipped N` | run 目录/note 缺失 | 先 `prepare` 再 `notes`，补齐后重跑 |
| S4 某场景 finalize 非 PASS | 产物不完整或事件日志缺失 | 删该 note 重写（按 execution-guide §4），重跑 commit `--only <case>` |
| S5 metrics 漂移 | 评分与聚合不一致 | 看 `results/benchmark/gradings/` 单场景 json；重跑 `aggregate.mjs` |
| S5b 非 REPRODUCIBLE | 数据/指标/证明有漂移 | `repro_report.json` 的 `failures` 数组逐条处理 |
| 重跑后结论变化 | 诊断非确定性 | S1 是确定性的；变化只可能来自 S3 note —— 检查新 note 是否偏离 brief 证据 |

## 6. 真实性保障层（为什么可以信任结果）

1. **真值隔离**：truth/keywords 仅在评分器 case 文件；brief 与管线输入无真值；
2. **现场推理**：note 由诊断 agent 依据 brief 统计证据现场写出，规则禁止接触
   真值与其他 note；
3. **独立评分**：评分器只读管线输出 + truth，不读 note（note 与 grading 分离）；
4. **执行证明**：无 `.pipeline_events.jsonl` / finalize PASS 的 run 不计分；
5. **确定性底座**：S1 统计同一数据逐字节可复现；S5 指标可从 gradings 独立重算；
6. **阴性对照**：评分器对注入错误诊断判伪（留痕见 §4 最后一项）；
7. **确定性断言**：一键入口 S5 对总体指标做硬断言（8/8、5/5、CDR=1、零误报），
   任何偏离直接失败退出——结果不达标时不会"看起来通过"。

## 7. 从场景报告到论文证据

- 单场景证据链：`00_input/data.csv` → `02_processed/validate_report.json`（统计）
  → `03_figures/fig_temporal_overview.png`（视觉）→ `01_ontology/ontology.json`（机理）
  → `04_diagnostics/diagnosis.json` → `report.md` / `diagnostic-report.html`；
- 汇总证据链：`gradings/*.json` → `metrics.json` → `repro_report.json` →
  `experience/benchmark-report.html`（含口径 A/B baseline 对比与优劣势分析）；
- 期刊对标表与双口径声明：[design.md](design.md) §4。
