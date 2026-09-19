# Industrial Deep Diagnostic (IDD) — Diagnosis Benchmark Report

> **Generated:** 2026-09-18 14:49:24 UTC · **Generator:** `scripts/benchmark/build-english-benchmark-report.mjs` (derived from on-disk artifacts; zero hard-coded verdicts)
> **System under test:** IDD full diagnosis pipeline `industrial-analysis-auto` Steps 2–9 (context-builder → data-processor → diagnostician → judge ∥ pre-audit → reporter → final audit → html-visualizer → html-reviewer → finalize)
> **Latest canonical run batch:** 20260917 · **Baseline model:** GLM family (same deployment as IDD pipeline; ZCode CLI harness, Sept 2026 snapshot)

> ⚠️ **TRUTH-CONTAINING ARTIFACT (grader-side).** Appendix A lists ground truth. Do not expose this file to a diagnosing agent — it would break the blind protocol.

## 1. Scope and object of evaluation

The unit under evaluation is **one complete industrial diagnosis run**, not a per-sample label. Each scenario is executed end-to-end by the pipeline and scored by an independent grader that reads the artifacts the sub-agents actually wrote.

| Dimension | What is measured |
|---|---|
| Correctness | Top-1 / Top-k root-cause hit against documented ground truth |
| Calibration | Whether the declared three-state verdict (DETERMINED / COMPETING_SET / NEEDS_DATA) matches the achievable discriminability |
| Control behaviour | False-alarm rate on three anomaly-free control scenarios |
| Process quality | Deterministic rubric R1–R7 computed from artifacts, plus judge and audit gates |
| Repeatability | Verdict and mechanism agreement across independent re-executions |
| Reproducibility | Artifact-level execution proofs and dataset fingerprint stability |

## 2. Benchmark protocol

```
S0 environment    fail-fast contract checks + truth-leakage sentinel
S1 prepare        deterministic statistics per scenario (same data + same code => byte-identical digest)
S2 brief          blind evidence pack (statistics + process description only; no truth)
S3 pipeline       REAL industrial-analysis-auto Steps 2-9 per scenario, sub-agents per their skill protocols
S4 grade          independent scorer reads agent-authored artifacts, compares against truth + deterministic rubric
S5 aggregate      metrics.json + reproducibility gate (must report REPRODUCIBLE)
S6 report         scoring report build
```

The four-step agent-executable test pipeline is documented in `docs/benchmark/benchmark-pipeline-runbook.md`:
(1) run the pipeline on the scenario data, (2) run the baseline/LLM replication suite on the same data, (3) draw a scenario **at random** and re-run it for consistency, (4) regenerate this report.

## 3. Scenario suite

**12 scenarios** — 9 fault cases + 3 anomaly-free controls. TEP faults carry per-fault literature baselines (FaultExplainer, arXiv:2412.14492 Table 1) and PCA detectability annotations (Chiang et al. 2001).

| # | Scenario | Dataset | Role | Expected verdict type |
|---|---|---|---|---|
| 1 | `skab_valve1_1` | skab | fault | DETERMINED |
| 2 | `skab_cavitation_13` | skab | fault | COMPETING_SET / NEEDS_DATA / DETERMINED |
| 3 | `skab_normal_control` | skab | control | NORMAL |
| 4 | `tep_d01_ac_feed_ratio` | tep | fault | DETERMINED / COMPETING_SET |
| 5 | `tep_d03_hard` | tep | fault | DETERMINED / COMPETING_SET / NEEDS_DATA |
| 6 | `tep_d00_normal_control` | tep | control | NORMAL |
| 7 | `indpensim_batch093` | indpensim | fault | DETERMINED / COMPETING_SET |
| 8 | `indpensim_batch001_control` | indpensim | control | NORMAL |
| 9 | `tep_d04_reactor_cooling_step` | tep | fault | DETERMINED / COMPETING_SET / NEEDS_DATA |
| 10 | `tep_d07_header_pressure` | tep | fault | DETERMINED / COMPETING_SET |
| 11 | `tep_d11_reactor_cooling_random` | tep | fault | DETERMINED / COMPETING_SET / NEEDS_DATA |
| 12 | `tep_d14_reactor_valve_sticking` | tep | fault | DETERMINED / COMPETING_SET / NEEDS_DATA |

Ground truth for every scenario is isolated in `scripts/benchmark/cases/benchmark_cases.json` and is never written into any pipeline-visible input, brief, or run directory.

## 4. Primary results

| Metric | Value |
|---|---|
| Scenarios executed | 12/12 |
| Top-1 hit (fault group) | 4/9 = 44.4% (Wilson 95% CI 18.9–73.3%) |
| Top-k hit (fault group) | 9/9 = 100.0% |
| Correct-delivery rate (Top-1 ∧ DETERMINED) | 0.44 (4/9) |
| Three-state calibration correct | 8/9 |
| Overconfident verdicts (DETERMINED ∧ wrong) | 0 |
| Controls passed | 3/3 |
| Control false alarms | 0 |
| Mean deterministic rubric (R1–R7) | 94.6/100 |

### 4.1 By dataset

| Dataset | Cases | Top-1 | Top-k | Controls passed |
|---|---|---|---|---|
| skab | 3 | 0 | 2 | 1/1 |
| tep | 7 | 3 | 6 | 1/1 |
| indpensim | 2 | 1 | 1 | 1/1 |

> Reported as measured. No metric floor is asserted — a threshold would create an incentive to dress up results to clear the gate.

## 5. Per-scenario results

| Scenario | Role | IDD verdict | Bare-LLM strict | FE-style top-3 | Suite PCA T² / SPE | Suite FE | Judge | Rubric | Finalized |
|---|---|---|---|---|---|---|---|---|---|
| `skab_valve1_1` | fault | miss · COMPETING_SET · conf 60 | HIT | n/a | 100.0% / 100.0% | — | 95 | 85 | PASS |
| `skab_cavitation_13` | fault | miss · COMPETING_SET · conf 60 | HIT | n/a | 100.0% / 100.0% | — | 90 | 100 | PASS |
| `skab_normal_control` | control | control_pass = true | normal ✓ | n/a | 1.0% / 1.0% | — | 97 | 100 | PASS |
| `tep_d01_ac_feed_ratio` | fault | HIT · DETERMINED · conf 91 | HIT | HIT | 99.3% / 99.8% | detected (XMEAS_25) | 96 | 85 | PASS |
| `tep_d03_hard` | fault | miss · COMPETING_SET · conf 55 | HIT | HIT | 2.9% / 4.8% | not detected | 90 | 100 | PASS |
| `tep_d00_normal_control` | control | control_pass = true | not run | n/a | 1.0% / 1.0% | not detected | 96 | 100 | PASS |
| `indpensim_batch093` | fault | HIT · DETERMINED · conf 82 | HIT | n/a | 15.0% / 73.9% | — | 96 | 100 | PASS |
| `indpensim_batch001_control` | control | control_pass = true | normal ✓ | n/a | 1.1% / 1.1% | — | 94 | 65 | PASS |
| `tep_d04_reactor_cooling_step` | fault | miss · COMPETING_SET · conf 63 | HIT | HIT | 48.8% / 100.0% | detected (XMV_10) | 97 | 100 | PASS |
| `tep_d07_header_pressure` | fault | HIT · DETERMINED · conf 78 | HIT | HIT | 100.0% / 99.5% | detected (XMEAS_4) | 98 | 100 | PASS |
| `tep_d11_reactor_cooling_random` | fault | miss · COMPETING_SET · conf 60 | HIT | HIT | 53.8% / 66.3% | detected (XMEAS_9) | 93 | 100 | PASS |
| `tep_d14_reactor_valve_sticking` | fault | HIT · DETERMINED · conf 80 | HIT | HIT | 99.8% / 93.4% | detected (XMV_10) | 94 | 100 | PASS |

Reading the table: `IDD verdict` is the truth-compared outcome of the full pipeline (hit/miss, three-state type, confidence). `Bare-LLM strict` is the same-model single-call baseline scored on mechanism keywords. `Suite PCA / FE` are the replicated classical baselines recomputed live by the baseline suite on the same prepared data.

## 6. Baseline arms

Three comparison arms are executed on the identical prepared data, with the model variable held constant (same deployment as the pipeline):

| Arm | Method | Provenance |
|---|---|---|
| PCA | Classic PCA monitoring: reference training / 95% variance / T² + Q / 99th-percentile alarm / SPE top-3 | Chiang et al. 2001; Qin 2012 — deterministic reimplementation |
| FE protocol | PCA(0.9) + T² (α=0.01 F-limit) + 6-consecutive trigger + per-sample top-6 T² contributions + EXPLAIN_ROOT | li-group/FaultExplainer |
| Bare LLM | Single blind call per scenario, three regimes (no candidates / with candidates / FE official prompt) | GLM family (same deployment as IDD pipeline; ZCode CLI harness, Sept 2026 snapshot) |

Suite statistics as recorded in `results/benchmark/baselines.json`:

- TEP subset, FE-protocol regime with candidate list — FE-style top-3 hit: **6/6**
- TEP subset, FE-protocol regime, no candidates: **strict single-verdict 6/6**
- FE official prompts, strict: **5/6**
- Same-digest bare-LLM ablation: strict single-verdict: TEP 6/6, non-TEP 3/3 (all 9/9 faults hit)
- Controls: 2/2 normal verdicts, 0 false alarms

> Same-model bare single-call LLM matches or exceeds the full pipeline on keyword-scored accuracy (see counts above, 0 control false alarms). The pipeline adds no accuracy on documented public faults; its margins are process qualities: auditability, execution proofs, ceiling compliance, and honest capped verdicts where signature data cannot discriminate mechanisms.

Suite executions on disk: **45** run files across 12 scenarios, each written by the Nuxt replication suite at `baselines/baseline-suite/runs/`.

## 7. Consistency (repeatability)

### 7.1 Random re-test draw

The re-tested scenario was selected by a uniform draw over the 9-scenario pool using a recorded seed, so the choice cannot be hand-picked after seeing results:

| Field | Value |
|---|---|
| Draw round | 1 |
| RNG | mulberry32 |
| Seed | `1003818694` |
| Uniform draw u | 0.846792349 |
| Pool size / filter | 9 / faults-only |
| **Selected scenario** | **`tep_d11_reactor_cooling_random`** (tep) |

Replay the identical draw: `node scripts/benchmark/select-retest-case.mjs --seed 1003818694`.

**Outcome** — 2 proven execution(s) in the current era (2 on disk across all eras), canonical era v2, audit status **CONSISTENT**.

| Against run | Verdict | Type (canonical = re-run) | Primary tag | Mechanism class | Confidence Δ |
|---|---|---|---|---|---|
| `202609171639527_bench_tep_d11_reactor_cooling_random` | CONSISTENT | COMPETING_SET = COMPETING_SET | XMV10 = XMV10 | ENVIRONMENT = ENVIRONMENT | 2 |

### 7.2 Consistency across all scenarios

Structured mechanism signature comparison (diagnosis type + primary equipment tag + mechanism class), era-aware:

| Metric | Value |
|---|---|
| Re-tested cases with ≥2 proven runs (same era) | 1 |
| Verdict-stable | 1 consistent, 0 weak |
| Divergent (within era) | 0 |
| Awaiting a second in-era execution | 11 |
| Within-era verdict agreement | **1/1** |

Cross-era pairs excluded from the headline: 0 (run-dir prefix < 20260914 is the pre-discipline system revision — a documented version change, not run-to-run instability).

| Scenario | Canonical era | Proven in era / total | Status | Types observed (in era) | Confidence range (in era) |
|---|---|---|---|---|---|
| `tep_d11_reactor_cooling_random` | v2 | 2 / 2 | CONSISTENT | COMPETING_SET | 60–62 |

Status is decided **within the canonical era**; the "total" column includes the earlier-era executions, which are not counted toward consistency.

### 7.3 Baseline suite determinism

The baseline suite was executed and its outputs compared file-by-file against the prior execution (timestamps excluded):

| Metric | Value |
|---|---|
| Run files compared | 45 |
| Byte-identical (timestamp-stripped) | 45 |
| Differing | 0 |
| Verdict | **DETERMINISTIC** |

## 8. Reproducibility and execution proofs

| Check | Result |
|---|---|
| Dataset fingerprint integrity | 153/153 verified, 0 mismatched |
| Scenario coverage | 12 prepared, 12 graded, 0 missing |
| Metric recomputation drift | 0 drifting field(s) |
| Execution proofs | 12/12 pipeline-log PASS, 12/12 finalize PASS |
| **Gate verdict** | **REPRODUCIBLE** |

Every graded run carries `.pipeline_events.jsonl` plus a `pipeline_finalize_report.json` with `overall = PASS`. A run without that proof is never counted, never rated.

## 9. Limitations and scope gaps

1. **Sample size.** 9 fault scenarios is a small evaluation set; the Wilson interval on Top-1 spans 18.9–73.3%. Treat point estimates as indicative.
2. **Indistinguishable-signature scenarios.** Where the recorded data cannot separate competing mechanisms, the pipeline returns `COMPETING_SET` rather than forcing a single root cause. These count as Top-1 misses but are protocol-conformant, and confidence is capped ≤65.
3. **Baseline LLM arm.** Without a configured live endpoint the suite replays archived raw replies of the same deployment; each response is labelled `recorded`. One control (tep_d00) has no archived bare-LLM triple — a declared protocol gap, not a fabricated result.
4. **In-era repetition.** Only the cases listed in §7.2 currently hold ≥2 proven executions in the current era; the rest carry an explicit re-run contract rather than an assumed stability claim.
5. **No accuracy advantage claimed.** On documented public faults a single same-model LLM call matches or exceeds the pipeline on keyword-scored accuracy. The pipeline's contribution is process quality: auditability, execution proofs, ceiling compliance, and honest capped verdicts where the data cannot discriminate.

## 10. Artifact index and provenance

| Artifact | Content |
|---|---|
| `results/benchmark/metrics.json` | Aggregate metrics + per-case rows |
| `results/benchmark/gradings/<case>.json` | Per-case truth-compared verdict + gate results |
| `results/benchmark/baselines.json` | Scored PCA / FE-protocol / bare-LLM arms |
| `baselines/baseline-suite/runs/<case>.<arm>.json` | Suite's own live executions (45 files) |
| `results/benchmark/consistency_audit.json` | Run-over-run consistency audit |
| `results/benchmark/retest_selection.json` | Random re-test draw (seed + pool + case) |
| `results/benchmark/suite_determinism.json` | Suite double-run byte diff |
| `results/benchmark/repro_report.json` | Reproducibility gate verdict |
| `results/benchmark/journal.jsonl` | Append-only scoring journal |
| `scripts/benchmark/cases/benchmark_cases.json` | Scenario definitions + ground truth (grader-side only) |

## Appendix A — Ground truth (grader-side)

> ⚠️ Truth-bearing. Never expose to a diagnosing agent.

| Scenario | Ground truth root cause | Keyword set | Expected verdict type |
|---|---|---|---|
| `skab_valve1_1` | 泵吸入侧阀门受限（供给不足）导致叶轮入流失稳，表现为振动爆发+回路压力脉动，电气参数正常。来源：SKAB 官方 valve1 实验组标签文件（措辞已改写，避免与数据集自带说明逐字重合）。 | valve, 阀, 节流, 受限, throttl, 阀阻, 吸入侧 | DETERMINED |
| `skab_cavitation_13` | 泵吸入侧两相流供给引发的气蚀。来源：SKAB ``other`` 实验组标签文件。 | cavitation, 气蚀, 空化, 两相流, 汽蚀 | COMPETING_SET / NEEDS_DATA / DETERMINED |
| `skab_normal_control` | 正常工况（anomaly-free baseline，无故障） |  | NORMAL |
| `tep_d01_ac_feed_ratio` | IDV(1)：A/C 进料比阶跃、B 成分不变（Stream 4） | a/c feed, feed ratio, 进料比, 进料配比, 配比, a:c, stream 4, a and c, 成分 | DETERMINED / COMPETING_SET |
| `tep_d03_hard` | IDV(3)：D 进料温度阶跃（文献公认难检故障） | d feed, d 进料, d进料, 进料温度, d 温度, stream 2 | DETERMINED / COMPETING_SET / NEEDS_DATA |
| `tep_d00_normal_control` | 正常工况（d00 无故障基线） |  | NORMAL |
| `indpensim_batch093` | 批次93工艺偏差：pH 与温度控制执行侧多执行器同步越限（酸流加、加热水），被控量 pH 与底物浓度出带。来源：IndPenSim 故障批次标记。 | ph 控制, ph（, ph(, ph=, ph , 酸, 加热, 越限, 执行器, deviation, 偏差 | DETERMINED / COMPETING_SET |
| `indpensim_batch001_control` | 正常批次（batch 1，recipe 驱动正常批） |  | NORMAL |
| `tep_d04_reactor_cooling_step` | IDV(4)：反应器冷却水入口温度阶跃（PCA 不可检集，FaultExplainer 表未评分） | 反应器冷却, reactor cooling, 冷却水, cooling water | DETERMINED / COMPETING_SET / NEEDS_DATA |
| `tep_d07_header_pressure` | IDV(7)：流股4 C 集管压力降低（逐步可用；FaultExplainer：GPT-4o 与 o1-preview 均正确） | c header, header, 集管, c feed, c 进料, c集管, stream 4 | DETERMINED / COMPETING_SET |
| `tep_d11_reactor_cooling_random` | IDV(11)：反应器冷却水入口温度随机变化（FaultExplainer：两模型经别名判正确） | 反应器冷却, reactor cooling, 冷却水, 随机, random | DETERMINED / COMPETING_SET / NEEDS_DATA |
| `tep_d14_reactor_valve_sticking` | IDV(14)：反应器冷却水阀粘滞（FaultExplainer：两模型经别名判正确） | 反应器冷却, reactor cooling, 冷却水阀, 阀粘滞, 粘滞, sticking | DETERMINED / COMPETING_SET / NEEDS_DATA |

---

_Generated by `scripts/benchmark/build-english-benchmark-report.mjs` from artifacts on disk. Regenerate with `node scripts/benchmark/run-benchmark-pipeline.mjs --step 4`._
