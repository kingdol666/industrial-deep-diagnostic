# 复现手册 — 审稿人逐步执行与核对

> 目标：审稿人（或任何无记忆的 agent）按本手册执行，在本仓库复现
> **12 场景**诊断基准的全部结果：每场景 `report.md` + `diagnostic-report.html`、
> 逐场景评分、总体指标、HTML 评分报告。
>
> ⚠️ **本手册于 2026-09-13 重写。** 旧版本描述的是"8 场景 / 5 故障"的早期设计，
> 与本仓库实际的 12 场景（9 故障 + 3 对照）不符，且其失败处置表会指引执行者
> 把场景集"恢复"成 8 场景版本——那会直接破坏论文数字。旧版内容已全部作废。
>
> 审计背景见 [AUDIT-2026-09-13.md](AUDIT-2026-09-13.md)。

---

## 0. 前置条件

```bash
node .claude/shared/scripts/uv_env_setup.mjs   # Python venv（stats 包需要）
# 数据已在仓库内：data/benchmark/prepared/{skab,tep,indpensim*}/（sha256 见 dataset_manifest）
```

## 1. 场景契约（先核对这一条，全部数字都依赖它）

```bash
node -e "const c=require('./scripts/benchmark/cases/benchmark_cases.json').cases;
console.log('cases',c.length,'fault',c.filter(x=>!x.control).length,'control',c.filter(x=>x.control).length)"
# 期望：cases 12 fault 9 control 3
```

对照表：

| 数据集 | 场景数 | 故障 | 对照 | 真值来源 |
|---|---|---|---|---|
| SKAB | 3 | 2 | 1 | 官方 `ground_truth.json` |
| TEP | 7 | 6 | 1 | Downs & Vogel / Chiang et al. 故障表（`data/benchmark/tep_braatz_classic/README.md:363-377`） |
| IndPenSim | 2 | 1 | 1 | 故障批次标记（batch 93） |
| **合计** | **12** | **9** | **3** | |

## 2. 真值隔离检查（**先跑这个**）

```bash
node scripts/benchmark/check-leakage.mjs
# 期望：RESULT: PASS — no truth leakage detected in agent-visible briefs
```

该哨兵机械校验四件事：

- **L1** 任一场景的 `truth` 文本不得出现在任何 agent 可见的 brief 中；
- **L2** 场景自身的 `process_description` 不得含故障词汇或评分关键词；
- **L3** brief 不得携带 `truth`/`keywords`/`expect_type_set`/`literature_baseline` 键；
- **L4** 关键词不得全部是通用工艺词（否则任何泛泛诊断都会命中）；
- **L5** note 不得逐字复现数据集自带的标签措辞。

> 为什么必须机械校验：2026-09-13 的审计发现，**6 个 TEP 故障场景中有 5 个**
> 的 `process_description` 直接写出了答案（其中一个直接点名 `IDV 3`），
> 而 4 个场景的评分关键词**就在题面里**。人工检查漏掉了这一点。
> 该批描述已于同日修复并重新生成 brief。

## 3. 一键复现

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

**S3 阶段会中断一次**（`N scenario(s) need on-the-spot diagnosis`）——这是设计行为：
诊断是唯一 agent-in-the-loop 环节。按 §4 完成现场诊断后**重跑同一条命令**
（已完成的阶段自动通过：prepare 复用 run 目录，note 齐全后继续 S4–S6）。

可复用已有 run 目录跳过重统计：`node scripts/benchmark/run-benchmark.mjs --skip-prepare`。

> ⚠️ **S3 不会调用任何 agent。** 它只校验 12 份 note 是否已存在且字段齐全。
> 即：基准实测的是"1 次 LLM 推理 + 预计算统计 brief"，
> **不含** context-builder / data-processor / diagnostician / judge / 物理审计的执行。
> 论文引用本基准时必须如实界定这一点（详见审计文档 C2）。

## 4. 现场诊断操作（S3，唯一人工环节）

```bash
node scripts/benchmark/run-tier.mjs notes        # 生成 12 份 note 骨架（已存在则保留）
```

然后对每个场景：

1. **只读** `results/benchmark/briefs/<case>.brief.json`（统计证据，无真值）；
2. 按 `industrial-diagnostician` 协议推理：≥3 竞争假设 → 判别/排除 → 三态结论；
3. 填写 `results/benchmark/notes/<case>.note.json`（删除 `_instructions` 键）。

**真实性红线**：证据必须引用 brief 数字；禁止读
`results/benchmark/gradings/*`、`scripts/benchmark/cases/*` 真值字段、其他 note。

> ⚠️ note 里的 `judge.score` 与 `audit.verdict` 是**诊断 agent 自己写的**，
> 基准直接采信并记入 grading（`judge_score_source: "note-self-declared"`）。
> 它**不是**独立质量门评分，不得作为证据主张。

## 5. 分步执行（与一键等价，便于定位失败）

| 步骤 | 命令 | 期望输出 |
|---|---|---|
| S1 | `node scripts/benchmark/run-tier.mjs prepare --tier scripts/benchmark/cases/benchmark_cases.json --force` | **12** 个 `workspace/diagnostic-runs/<ts>_bench_<case>/` + 各自 `prepare_digest.json` |
| S2 | `node scripts/benchmark/run-tier.mjs brief --tier …` | `results/benchmark/briefs/*.brief.json`（**12** 份） |
| S3 | 按 §4 填 **12** 份 note | `results/benchmark/notes/*.note.json` 全部填完 |
| S4 | `node scripts/benchmark/run-tier.mjs commit --tier …` | `[commit] <case> — top1=… judge=…` ×**12**，0 skipped |
| S5 | `node scripts/benchmark/aggregate.mjs --tier-file scripts/benchmark/cases/benchmark_cases.json` | `results/benchmark/metrics.json` + `report.md` |
| S5b | `node scripts/benchmark/verify-repro.mjs --tier …` | `status: REPRODUCIBLE`（退出码 0） |
| S5c | `node scripts/benchmark/audit-structural.mjs` | `results/benchmark/structural_audit.json` —— **独立于 note** 的产物结构审计（12/12 应为 100） |
| S6 | `node scripts/benchmark/build-report.mjs` | `experience/benchmark-report.html` |

状态总览：`node scripts/benchmark/run-tier.mjs status`（prepared / note / graded 三态表）。

## 6. 逐项核对清单（评审验收点）

- [ ] **场景契约**：12 = 9 故障 + 3 对照
- [ ] **真值隔离**：`check-leakage.mjs` 退出码 0
- [ ] **每场景两份报告存在**：`workspace/diagnostic-runs/<ts>_bench_<case>/report.md`
      与 `diagnostic-report.html`（run 目录见 `results/benchmark/tier_state.json`）
- [ ] **执行证明**：每个 run 的 `.pipeline_events.jsonl` 通过
      `pipeline-log-check.mjs`；grading 中 `checks.finalize_passed = true`（**12/12**）
- [ ] **独立评分可追溯**：`results/benchmark/gradings/<case>.json` 逐场景给出
      top1/topk/calibrated 判定与 run_dir；truth 只出现在
      `scripts/benchmark/cases/benchmark_cases.json`
- [ ] **总体指标**：`results/benchmark/metrics.json` —— Top-1、CDR、校准、对照组通过/误报；
      HTML 报告中所有比例均带 Wilson 95% CI
- [ ] **CDR 口径**：`cdr` 是 **0–1 比率**（`cdr_display` 形如 `1.00 (9/9)`）；
      它**不是**计数，不可与 Top-1 计数并排相减
- [ ] **复现门禁**：`results/benchmark/repro_report.json` status = REPRODUCIBLE
      （数据 sha256 重哈希、场景覆盖、指标零漂移、执行证明四查全过）
- [ ] **评分器判别力**：`experience/results/scorer-discrimination-test.json`
      —— 注入"plausible-but-wrong"诊断被评分器判伪（top1=false）
- [ ] **盲诊协议**：`check-leakage.mjs` 的 L1/L2/L3/L5 全过

## 7. 漂移决策树（失败时）

| 症状 | 诊断 | 处置 |
|---|---|---|
| S0 报缺 venv | Python 环境未建 | `node .claude/shared/scripts/uv_env_setup.mjs` |
| S0 报 case contract | 场景集被改动 | 恢复为 **12 场景 / 9 故障 + 3 对照**（`git checkout scripts/benchmark/cases/benchmark_cases.json`）。**不要**恢复成 8 场景版本 |
| `check-leakage` 报 L2 | 有人把故障身份写回了 `process_description` | 删除故障句，只保留介质/拓扑/列语义/采样率/异常时段；重新 `run-tier.mjs brief` |
| S1 某场景统计失败 | stats 包异常（如含 NaN 列） | 属预期降级：digest 标 `driver-js-fallback`，继续；若 run 目录未建则单独重跑该 case prepare |
| S3 反复列缺 note | note 未填或仍是模板 | 检查 note 已删除 `_instructions` 且各必填字段完整（`run-tier.mjs status`） |
| S4 `skipped N` | run 目录/note 缺失 | 先 `prepare` 再 `notes`，补齐后重跑 |
| S4 某场景 finalize 非 PASS | 产物不完整或事件日志缺失 | 删该 note 重写（按 §4），重跑 commit `--only <case>` |
| S5 metrics 漂移 | 评分与聚合不一致 | 看 `results/benchmark/gradings/` 单场景 json；重跑 `aggregate.mjs` |
| S5b 非 REPRODUCIBLE | 数据/指标/证明有漂移 | `repro_report.json` 的 `failures` 数组逐条处理 |
| 重跑后结论变化 | 诊断非确定性 | S1 是确定性的；变化只可能来自 S3 note —— 检查新 note 是否偏离 brief 证据 |

## 8. 真实性保障层（以及它们的**实际边界**）

| # | 保障 | 实际强度 |
|---|---|---|
| 1 | 真值隔离 | ✅ 经 `check-leakage.mjs` 机械校验（2026-09-13 修复后） |
| 2 | 现场推理 | ⚠️ note 由 agent 依 brief 写出，但**无程序化强制**，依赖自觉 |
| 3 | 独立评分 | ⚠️ **部分**：top1/topk 由 grader 按关键词算；`judge_score` 与 `audit.verdict` 是 **note 自报**，且 10 个维度实测全为同一数字（**零判别力**）。替代品是 `audit-structural.mjs` 的独立结构审计——但它是**地板不是排名**，只能证明产物完整、证据可追溯，不能区分结论对错 |
| 4 | 执行证明 | ✅ 无 `.pipeline_events.jsonl` / finalize PASS 的 run 不计分 |
| 5 | 确定性底座 | ✅ S1 统计同一数据逐字节可复现；S5 指标可从 gradings 独立重算 |
| 6 | 阴性对照 | ⚠️ **仅 1 个场景**（`skab_cavitation_13`），未覆盖关键词边界情形；控制组判据仍是散文正则 |
| 7 | 确定性断言 | ✅ 一键入口 S5 对总体指标做硬断言，任何偏离直接失败退出 |
| 8 | 统计降级可见性 | ✅ 2026-09-13 新增：grading 记录 `statistics_engine` / `stats_degraded` / `anti_spurious_executed`；降级时 `finalize_passed=false`。此前降级会**静默通过并计分**（详见审计文档 D3） |

> **统计效力边界**：n=9 故障场景、Top-1 = 9/9 只支持"≥70.1%（95% 置信）"，
> 不支持"普遍胜任"。Wilson 区间已计入报告。
>
> **推理层的可复现性**：S1 统计层逐字节可复现；**推理层不含此保证**。
> 任何"复现"声明都必须把这两层分开陈述。

## 9. 从场景报告到论文证据

- 单场景证据链：`00_input/data.csv` → `02_processed/validate_report.json`（统计）
  → `03_figures/fig_temporal_overview.png`（视觉）→ `01_ontology/ontology.json`（机理）
  → `04_diagnostics/diagnosis.json` → `report.md` / `diagnostic-report.html`；
- 汇总证据链：`gradings/*.json` → `metrics.json` → `repro_report.json` →
  `experience/benchmark-report.html`；
- 期刊对标表与双口径声明：[design.md](design.md) §4；
- **审计与待修项**：[AUDIT-2026-09-13.md](AUDIT-2026-09-13.md)。
