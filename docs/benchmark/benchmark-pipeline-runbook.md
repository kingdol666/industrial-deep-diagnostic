# IDD Benchmark Test Pipeline — Agent Runbook

> **Audience:** an executing agent (human or LLM) with no prior session memory.
> **Goal:** run the four-step benchmark test pipeline on this repository's already-downloaded
> scenario data, obtain real test results, and regenerate the English benchmark-standard report.
>
> Everything in this document is executable as written. No step requires information that is not
> in the repository.

---

## 0. What the pipeline does

| Step | Question it answers | Output |
|---|---|---|
| **1** | Does the current IDD diagnosis pipeline actually diagnose the scenario data? | Per-scenario pipeline artifacts, `gradings/*.json`, `metrics.json`, reproducibility verdict |
| **2** | How does the LLM-replication baseline project perform on the **same** data? | 45 suite run files, `suite_determinism.json` |
| **3** | Is the diagnosis **consistent** when the same scenario is diagnosed again, drawn **at random**? | `retest_selection.json`, `consistency_audit.json` |
| **4** | What is the benchmark-standard English report? | `benchmark_report_en.md` + `benchmark_report_en.html` |

Single entry point:

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs
```

Run one step: `--step 1` … `--step 4`. Run several: `--steps 2,4`.
Reproduce a specific random draw: `--seed <n>`. Report gaps without failing: `--allow-gaps`.

Exit code is **1** whenever a stage is incomplete. An incomplete stage always prints an
**EXECUTION CONTRACT** naming exactly what an agent must still do. Read that block — it is the
work order.

---

## 1. Prerequisites (one-time)

| Item | Location | Check |
|---|---|---|
| Scenario data (12 prepared CSVs, 153 fingerprinted files) | `data/benchmark/prepared/{skab,tep,indpensim*}/` | `node scripts/benchmark/verify-repro.mjs` → dataset integrity 153/153 |
| Python venv (deterministic stats package) | `.claude/shared/scripts/.venv/` | `node .claude/shared/scripts/uv_env_setup.mjs` |
| Baseline suite deps | `baselines/baseline-suite/node_modules/` | `cd baselines/baseline-suite && npm install` |
| Baseline suite deps present ⇒ port 5181 free or reachable | `http://localhost:5181/api/scenarios` | returns a 12-element JSON array |

The suite is started automatically by Step 2 if it is not already serving. If port 5181 is busy
with something else, Nuxt falls back to another port and the runner detects it from the log
(`results/benchmark/.suite-dev.log`).

---

## 2. Step 1 — Run the IDD diagnosis pipeline on the scenario data

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs --step 1
# equivalent manual chain:
#   node scripts/benchmark/check-leakage.mjs --tier scripts/benchmark/cases/benchmark_cases.json
#   node scripts/benchmark/run-tier.mjs prepare --tier scripts/benchmark/cases/benchmark_cases.json
#   node scripts/benchmark/run-tier.mjs brief   --tier scripts/benchmark/cases/benchmark_cases.json
#   node scripts/benchmark/run-tier.mjs pipeline --tier scripts/benchmark/cases/benchmark_cases.json
#   node scripts/benchmark/run-tier.mjs commit  --tier scripts/benchmark/cases/benchmark_cases.json
#   node scripts/benchmark/judge-rubric.mjs --tier scripts/benchmark/cases/benchmark_cases.json
#   node scripts/benchmark/aggregate.mjs --tier-file scripts/benchmark/cases/benchmark_cases.json
#   node scripts/benchmark/verify-repro.mjs --tier scripts/benchmark/cases/benchmark_cases.json
```

Phases, in order:

| Phase | What happens | Gate |
|---|---|---|
| 1.0 | Contract checks + truth-leakage sentinel | sentinel must print `PASS` |
| 1.1 | `prepare` — deterministic statistics into each run dir (`workspace/diagnostic-runs/<ts>_bench_<case>/`) | reuse is the default; `--force` destroys pipeline artifacts |
| 1.2 | `brief` — blind evidence pack per scenario | no truth inside |
| 1.3 | `pipeline` — verify the **full Step 2-9 artifact set** per run dir | every scenario must report `COMPLETE` |
| 1.4 | `commit` + `judge-rubric` — score from agent-authored artifacts | 12 graded, 0 skipped |
| 1.5 | `aggregate` + `verify-repro` | reproducibility gate must report `REPRODUCIBLE` |

### 2.1 If phase 1.3 reports `INCOMPLETE`

A script may **verify and score** pipeline artifacts; it may **never author** them. When artifacts
are missing, the runner prints an execution contract and exits 1. Execute the real pipeline:

For **each** incomplete scenario, in its run directory
`workspace/diagnostic-runs/<ts>_bench_<case_id>/`, run
`skill://industrial-analysis-auto` **Steps 2-9**, dispatching each sub-agent per its own skill
protocol (the main agent only dispatches, waits and aggregates):

| Step | Sub-agent | Skill | Key artifacts |
|---|---|---|---|
| 2 | context-builder | `industrial-ontology-builder` | `01_ontology/ontology.json` (+ CP-2/CP-3) |
| 3 | data-processor | `industrial-data-processor` | `02_processed/data_analysis_conclusion.json` (+ CP-4) |
| 4 | diagnostician | `industrial-diagnostician` | `04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json` (CP-5) |
| 5a ∥ 5b | judge ∥ report-reviewer | `industrial-judge` ∥ `industrial-physical-auditor` | `05_review/judge_feedback.json` + `optimizer_preflight.md` |
| 6 | reporter | `industrial-reporter` | `report.md` + `run_summary.json` (CP-7) |
| 7 | report-reviewer (final audit) | `industrial-physical-auditor` | `optimizer.md` containing `ENDORSED` (CP-8) |
| 8 | html-visualizer | `industrial-html-visualizer` | `render_manifest.json` **first** → `diagnostic-report.html` → `html_selfcheck.json` |
| 8.5 | html-reviewer | `industrial-html-reviewer` | `05_review/html_review.json` with `verdict = pass` |
| 9 | finalize | — | `pipeline_finalize_report.json` (`overall = PASS`) + `evidence_closure_report.json` |

Red lines — violating any of them invalidates the run:

- **Truth isolation.** No sub-agent may read `results/benchmark/` (except `legacy_note_era/`) or
  `scripts/benchmark/cases/`.
- **No ghost-writing.** The orchestrating agent must not author a sub-agent's artifacts.
- **No visual fabrication.** In a non-VLM environment, Step 3 Phase 5.5 emits the script-signed
  metadata skeleton (`visual_analysis.py`); never invent visual observations.
- **HTML must go through the manifest.** `render_manifest.json` first, then the page; the page's
  element counts must match the manifest one-to-one. `05_review/html_review.json` may only be
  written by the html-reviewer.

Then re-run `--step 1`; phase 1.3 must report `COMPLETE` for all scenarios.

---

## 3. Step 2 — Run the LLM-replication baseline suite on the same data

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs --step 2
# equivalent:
#   cd baselines/baseline-suite && node node_modules/nuxt/bin/nuxt.mjs dev --port 5181   # http://localhost:5181
#   node baselines/baseline-suite/scripts/run-all.mjs --base http://localhost:5181
```

Arms (all computed on `data/benchmark/prepared/`, truth-free by contract):

| Arm | Method | Execution |
|---|---|---|
| `pca` | Classic PCA monitoring: reference training / 95% variance / T² + Q / 99th-percentile alarm / SPE top-3 | deterministic in-suite engine (pure-JS Jacobi) |
| `fe` | FaultExplainer protocol: PCA(0.9) + T² (α=0.01 F-limit) + 6-consecutive trigger + per-sample top-6 T² contributions + EXPLAIN_ROOT | deterministic in-suite engine |
| `llm` | Same-model bare single-call, three regimes (`no_candidates` / `with_candidates` / `fe_official`) | **live** when `BASELINE_LLM_BASE_URL` + `BASELINE_LLM_API_KEY` are set (OpenAI-compatible; host validated before any request, private/loopback hosts refused); otherwise **recorded** replay of the archived raw replies of the same deployment, each response labelled `mode: "recorded"` |

Results land as `baselines/baseline-suite/runs/<case>.<arm>[_<regime>].json`. Expected total: **45**
runs over 12 scenarios (the `tep_d00` control has no archived bare-LLM triple — a declared protocol
gap, marked `unavailable`, never fabricated).

Determinism check (phase 2.3): the runner snapshots the prior run files, re-executes everything, and
diffs each file with `executed_at` excluded. Deterministic arms must be **byte-identical**; a
`recorded` arm differing means the archived answers were edited. Verdict written to
`results/benchmark/suite_determinism.json`.

---

## 4. Step 3 — Draw a scenario at random and audit consistency

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs --step 3
# equivalent:
#   node scripts/benchmark/select-retest-case.mjs --faults-only
#   node scripts/benchmark/consistency-audit.mjs
#   node scripts/benchmark/consistency-audit.mjs --case <drawn_case_id>
```

**The draw.** `select-retest-case.mjs` picks one scenario by a uniform draw over the declared pool
using a `mulberry32` RNG with a **recorded seed**. The draw is written to
`results/benchmark/retest_selection.json` (append-only, one entry per round) together with the pool,
the raw uniform value `u` and the resulting index — so a reviewer can verify the draw was uniform
and replay it exactly:

```bash
node scripts/benchmark/select-retest-case.mjs --seed <recorded_seed>
node scripts/benchmark/select-retest-case.mjs --peek      # show the last draw
```

The scenario is **not** hand-picked. (The earlier flow hard-coded `tep_d14` and even hard-coded its
run-dir timestamps inside the report generator — that is selection bias, and it has been replaced.)

**The audit.** `consistency-audit.mjs` treats every `workspace/diagnostic-runs/*_bench_<case>` as one
independent execution and compares executions **against each other** (truth-free, so it is safe
inside the blind protocol). It compares a structured mechanism signature:

- `diagnosis_type` — DETERMINED / COMPETING_SET / NEEDS_DATA
- `primary_tag` — the equipment tag the verdict pivots on (actuator `XMV_*` > measurement `XMEAS_*` > fault id `IDV*`)
- `mechanism_class` — WEAR / OPERATION / SENSOR / …
- `cause_tokens` — token overlap of cause + class + hypothesis name

| Verdict | Rule |
|---|---|
| `CONSISTENT` | same `diagnosis_type` **and** (same `primary_tag` **or** same `mechanism_class` with ≥ 0.35 cause-token overlap) |
| `WEAK` | same `diagnosis_type`, weaker structural agreement |
| `DIVERGENT` | different `diagnosis_type`, or unrelated mechanism |
| `UNPROVEN` | no finalize execution proof — listed but never counted |

**Era discipline.** A run-dir timestamp prefix `< 20260914` is the v1 era (before the
anti-oscillation / confidence-cap / missing-discriminating-channel discipline). Cross-era verdict
flips are a documented **system revision**, not run-to-run instability, so the headline metric is
**within-era** agreement and cross-era pairs are reported separately.

**If the drawn scenario has fewer than 2 proven in-era executions**, the runner prints an execution
contract. Execute it:

1. The run dir is already prepared — do not re-prepare.
2. In `workspace/diagnostic-runs/<new_ts>_bench_<case>/`, run `skill://industrial-analysis-auto`
   Steps 2-9 exactly as in §2.1, in a **fresh session**.
3. `node scripts/benchmark/run-tier.mjs commit --tier scripts/benchmark/cases/benchmark_cases.json --only <case>`
4. `node scripts/benchmark/consistency-audit.mjs --case <case>`
5. `node scripts/benchmark/run-benchmark-pipeline.mjs --step 4`

Never copy artifacts between run dirs, never re-use the canonical run dir as a source, never edit a
result JSON by hand. A run counts only if `pipeline_finalize_report.json` has `overall = PASS` and
`.pipeline_events.jsonl` exists.

---

## 5. Step 4 — Generate the English benchmark-standard report

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs --step 4
# equivalent:
#   node scripts/benchmark/build-english-benchmark-report.mjs
```

Output — both English, both derived exclusively from on-disk artifacts (zero hard-coded verdicts):

- `results/benchmark/benchmark_report_en.md`
- `results/benchmark/benchmark_report_en.html`

Sections: scope and object of evaluation · benchmark protocol · scenario suite · primary results
(with Wilson 95% CI) · per-scenario results (IDD × bare-LLM × FE-style × suite PCA/FE) · baseline
arms and provenance · consistency (random draw + audit + suite determinism) · reproducibility and
execution proofs · limitations and scope gaps · artifact index · **Appendix A: ground truth
(grader-side)**.

> Appendix A contains ground truth. **Do not expose this report to a diagnosing agent** — it would
> break the blind protocol. The banner in the report says so.

---

## 6. Expected end state

| Artifact | Expected |
|---|---|
| `results/benchmark/metrics.json` | `executed = 12`, reproducibility gate `REPRODUCIBLE` |
| `results/benchmark/gradings/*.json` | 12 files, each with `checks.finalize_passed = true` |
| `baselines/baseline-suite/runs/*.json` | 45 files |
| `results/benchmark/suite_determinism.json` | `verdict = DETERMINISTIC` (det. arms byte-identical) |
| `results/benchmark/retest_selection.json` | ≥ 1 round with a recorded seed |
| `results/benchmark/consistency_audit.json` | `divergent = 0` within era |
| `results/benchmark/benchmark_report_en.md` / `.html` | regenerated, non-empty |
| `results/benchmark/repro_report.json` | `status = REPRODUCIBLE` |

A stage is complete only when its artifact exists **and** its gate passes. `--allow-gaps` reports
gaps without failing the run — use it when you intend to hand the outstanding contracts to another
agent, never to declare success.

---

## 7. Drift decision tree

| Symptom | Action |
|---|---|
| Phase 1.3 reports `INCOMPLETE` | Execute the §2.1 contract for the named scenarios. Never `--force-prepare` to "fix" it — that destroys completed artifacts. |
| Step 2 reports `FAIL` | Read the HTTP error body. Missing data file → check the sha256 in `results/benchmark/dataset_manifest.json`. |
| LLM arm reports `unavailable` | No live endpoint configured and no archived answer (currently only the `tep_d00` control). Configure `BASELINE_LLM_BASE_URL` / `BASELINE_LLM_API_KEY` and re-run to go live. |
| Deterministic suite arm differs on re-run | The suite code changed. Cross-check against `scripts/benchmark/baseline_pca.mjs` (same protocol). |
| `recorded` suite arm differs on re-run | The archived answers under `results/benchmark/baseline_fe_answers/` were edited — this violates the protocol. |
| Consistency audit reports `DIVERGENT` within era | Follow §4: check whether the two runs disagree on `primary_tag` / `mechanism_class`. If the data genuinely cannot discriminate, `COMPETING_SET` is the correct honest verdict and the cap applies. |
| Report numbers disagree with `gradings/` | The report is a derived artifact. Re-run `run-tier.mjs commit` → `aggregate.mjs` → `build-english-benchmark-report.mjs`. |

---

## 8. Anti-fabrication rules (the reason this pipeline is trustworthy)

1. Scripts verify and score; they never author pipeline artifacts or agent events.
2. A scenario counts only when the finalize gate and the execution-proof log both pass.
3. The re-tested scenario is drawn at random with a recorded seed — never hand-picked.
4. Missing coverage is reported as an explicit gap or an execution contract, never filled with
   invented answers.
5. Cross-era differences are attributed to the documented system revision, not silently averaged away.

---

## 9. File map

| Path | Role |
|---|---|
| `scripts/benchmark/run-benchmark-pipeline.mjs` | **four-step entry point** |
| `scripts/benchmark/select-retest-case.mjs` | random scenario draw (seeded, recorded) |
| `scripts/benchmark/consistency-audit.mjs` | run-over-run consistency audit |
| `scripts/benchmark/build-english-benchmark-report.mjs` | English benchmark-standard report (MD + HTML) |
| `scripts/benchmark/run-benchmark.mjs` | S0-S6 scoring benchmark (reviewer entry point) |
| `scripts/benchmark/run-tier.mjs` | stage orchestration (prepare / brief / pipeline / commit / stability / baselines) |
| `scripts/benchmark/aggregate.mjs`, `verify-repro.mjs`, `judge-rubric.mjs` | metrics, reproducibility gate, deterministic rubric |
| `baselines/baseline-suite/` | Nuxt replication suite (PCA / FE protocol / bare LLM) |
| `baselines/FaultExplainer/` | vendored upstream baseline (li-group/FaultExplainer @ 2fcfee9, MIT) |
| `docs/benchmark/` | design, execution guide, reproduction guide, this runbook |
| `results/benchmark/` | all derived outputs (correctness, consistency, determinism, report) |
