---
name: industrial-benchmark-runner
description: "Reproducible benchmark orchestration for the industrial deep-diagnostic pipeline. Drives tiered case sets end to end (dataset manifest → per-case run dir preparation → diagnostic inference → artifact expansion → pipeline gates → grading → metric aggregation → baseline comparison against published journals) and enforces a reproducibility gate over dataset hashes, case coverage and recomputed metrics. Use it when you need to measure, compare or publish the pipeline's diagnostic accuracy on public industrial benchmarks (TEP, SKAB, IndPenSim, SECOM, C-MAPSS, Paderborn, FEMTO) or to reproduce previously reported numbers. Do NOT use for a single ad-hoc diagnosis (use industrial-analysis-auto) or for data cleaning alone (use industrial-data-preprocessor). Trigger: benchmark, reproduce results, tier run, grading, metrics aggregation, baseline comparison, journal comparison, ablation study, benchmark plan, dataset manifest, reproducibility check."
---

# Industrial Benchmark Runner

Benchmark orchestration layer for the diagnosis pipeline. It turns "run the
system on public datasets and compare with the literature" into a repeatable,
auditable procedure: every number in `results/benchmark/` can be traced to a
case definition, a prepared run directory, a grading record and a checksummed
input file.

## When to use / when not to

| Use | Do not use |
|---|---|
| Reproducing a tier (e.g. `tier0_smoke`) end to end | A one-off diagnosis on private data → `industrial-analysis-auto` |
| Adding cases, re-grading, recomputing metrics | Raw data cleaning / format conversion only → `industrial-data-preprocessor` |
| Producing the paper's result table vs. journal baselines | Statistical deep-dive on a single dataset → `industrial-deep-analysis` |
| Verifying that reported numbers still reproduce | Enhancing one finished run → `industrial-analysis-enhance-auto` |

## Inputs / Outputs

### Inputs

| Path | Role |
|---|---|
| `scripts/benchmark/cases/tier<N>_*.json` | Case definitions: `case_id`, `dataset`, `csv`, `time_col`, `target_cols`, `truth`, `keywords`, `expect_type_set`, `process_description`, `control` |
| `data/benchmark/prepared/<dataset>/*.csv` | Standardized inputs (timestamp + sensor columns) |
| `results/benchmark/dataset_manifest.json` | Dataset fingerprints (path + sha256 + rows/cols) |
| `results/benchmark/notes/<case_id>.note.json` | Diagnostic inference per case — the ONE human/agent-in-the-loop artifact |
| `results/benchmark/tier_state.json` | Prepared run-dir registry written by this skill |

### Outputs

| Path | Role |
|---|---|
| `results/benchmark/gradings/<case_id>.json` | Per-case grading: `top1` / `topk` / `root_cause_kw_hit` / `calibrated` / `overconfident` / `diagnosis_type` / `judge_score` / control flags |
| `results/benchmark/journal.jsonl` | Append-only run journal (one line per commit) |
| `results/benchmark/metrics.json` + `report.md` | Aggregated tier metrics and human-readable report |
| `results/benchmark/repro_report.json` | Reproducibility gate result (dataset hashes / coverage / metric drift / execution proof) |

## Workflow

1. **Acquire data** (idempotent, hashed, host-validated):
   `node scripts/benchmark/download-datasets.mjs --list` then `--only <ids>`;
   refresh fingerprints with `node scripts/benchmark/make_dataset_manifest.mjs`.
2. **Register cases**: add entries to the tier file (one fault case + one control
   case per dataset is the minimum viable pattern; keep `truth`/`keywords` out of
   anything the pipeline can read).
3. **Prepare**: `run-tier.mjs prepare --tier <file>` — deterministic ingestion
   (setup → CSV copy → input manifest → inspect → stats digest) into a run dir.
4. **Emit note skeletons**: `run-tier.mjs notes --tier <file>`; the diagnosing
   agent fills each note following the diagnostic skill protocol. Ground truth
   must never be injected into the pipeline — the grader owns it.
5. **Commit**: `run-tier.mjs commit --tier <file>` — expands each filled note into
   schema-compliant artifacts (ontology / diagnosis / evidence / confidence /
   reasoning chain / review), runs `pipeline-log-check` and `pipeline-finalize`,
   grades the case and appends to the journal.
6. **Aggregate**: `node scripts/benchmark/aggregate.mjs --tier-file <file>` —
   recomputes `top1` / `topk` / `CDR` / calibration / control metrics with
   per-dataset breakdown, writes `metrics.json` + `report.md`.
7. **Compare with journals**: use the baseline table and the two-tier comparison
   protocol in `docs/benchmark-design.md` (same-task direct comparison vs.
   cross-task order-of-magnitude reference).
8. **Verify**: `verify-repro.mjs --tier <file>` — must report `REPRODUCIBLE`
   before any number is published.

## Reproducibility contract

A result is publishable only when **all** of the following hold:

1. Every input file re-hashes to its `dataset_manifest.json` sha256.
2. Every case in the tier file has a grading, and every grading references a run
   dir with `.pipeline_events.jsonl` whose `pipeline_log` check is `PASS`.
3. `metrics.json` equals the metrics recomputed from `gradings/*.json`.
4. The case file, the note files and the gradings are committed alongside the
   report; the note schema used is the one emitted by `run-tier.mjs notes`.

`verify-repro.mjs` enforces 1-3 mechanically. Violations are `FAIL` (drift);
absent-but-regenerable datasets and ungraded cases are `WARN`.

## Error handling

| Symptom | Meaning | Action |
|---|---|---|
| `note still a template/partial, skipping` | Inference not filled | Fill required note fields (`diagnosis_type`, `ontology.variables`, `hypotheses[].verdict`, `primary_finding`, `confidence`) |
| `no prepared run dir` | Case added after prepare | Re-run `prepare --tier <file>` |
| `dataset hash drift` | Prepared CSV changed after fingerprinting | Re-run `make_dataset_manifest.mjs` only if the change is intentional, then re-grade affected cases |
| `metrics drift vs metrics.json` | Gradings changed after aggregation | Re-run `aggregate.mjs`, then `verify-repro.mjs` |
| Download fails (HTTP 4xx/5xx, timeout) | Source moved or is form-gated (CWRU) | Follow the manual step recorded in `data/benchmark/downloads.lock.json` / `docs/benchmark-design.md` §5 |

## References

- `references/reproduction-playbook.md` — **start here for reproduction**: the agent-executable protocol (S0-S6 stages, expected outputs, drift decision tree, authenticity rules).
- One-command reproduction: `node scripts/benchmark/reproduce-all.mjs` (fail-fast S0-S6 chain; `--skip-prepare` reuses run dirs).
- `docs/benchmark-design.md` — system review, journal baseline table (verified DOIs), evaluation protocol, comparison caveats, known gaps.
- `docs/benchmark-plan.md` — tiered execution plan, cost model, integration milestones.
- `docs/dataset-experiment-research.md` — dataset survey and prior paper analysis.
- `scripts/benchmark/zcode_direct_pipeline.mjs` — deterministic stage driver + artifact expansion + grader.
- `scripts/benchmark/aggregate.mjs` — metric definitions (single source of truth for aggregation).
- `scripts/benchmark/cases/tier0_smoke.json` — 9-case smoke tier (3 datasets × fault/control); `tier2_main.json` — 23-case main tier; `tier_all.json` — combined 32-case library.
