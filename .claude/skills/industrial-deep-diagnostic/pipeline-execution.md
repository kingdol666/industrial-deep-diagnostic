# Pipeline Execution Reference

> **Load this file only during repair loops or when detailed validation rules are needed.**
> SKILL.md contains the main step-by-step protocol. This file covers: numbering systems, repair loop protocol, pipeline event logging, statistical validation framework, and common mistakes.

## Numbering Systems — Four Separate Schemes

This skill uses FOUR distinct numbering systems. Do not conflate them.

| System | Scope | Used In | Example |
|--------|-------|---------|---------|
| **Pipeline Step 0-8** | Orchestration-level workflow | SKILL.md | "Step 4: Diagnostician" |
| **Agent Phase 0-7** | Diagnostician's internal workflow | agents/diagnostician.md | "Phase 1: Data Probing" |
| **Reasoning Segment R1-R8** | Structured reasoning trace output | reasoning_chain.json | "R4: Hypothesis Generation" |
| **Method Stage 1-6** | Generic diagnostic methodology | resources/diagnosis_method.md | "Stage 3: Temporal Analysis" |

---

## Pipeline Event Log

Each agent MUST append a JSON line to `RUN_DIR/.pipeline_events.jsonl` at start and completion:

```jsonl
{"event": "agent_start", "agent": "context-builder", "timestamp": "2026-05-25T10:00:00Z"}
{"event": "agent_complete", "agent": "context-builder", "timestamp": "2026-05-25T10:02:30Z", "files_written": ["01_ontology/ontology.json"], "errors": null}
```

The main agent logs repair-loop events:

```jsonl
{"event": "repair_spawn", "iteration": 1, "source": "judge", "diag_iters_total": 1, "timestamp": "..."}
{"event": "repair_cap_reached", "diag_iters_total": 5, "reason": "Global re-diagnosis cap exceeded", "timestamp": "..."}
```

**At the start of any repair loop, count `repair_spawn` entries to restore `diag_iters`.** Do not rely on in-memory state.

---

## Repair Loop Protocol

### Judge Repair (Step 5)

```
for iter in 1..3:
  if score >= 90 → break (PASS)
  if diag_iters >= 5 → break (GLOBAL_CAP)
  diag_iters++
  log repair_spawn event
  re-spawn Diagnostician with REPAIR_INSTRUCTIONS from judge_feedback.json
```

### Reviewer Repair (Step 7.5)

```
for iter in 1..2:
  if verdict == ENDORSED → break
  if diag_iters >= 5 → break (GLOBAL_CAP)
  diag_iters++
  log repair_spawn event
  re-spawn Diagnostician with physical critique from optimizer.md
  re-run Judge (fresh counter) → Reporter → Reviewer
```

### Global Rules

- Each re-diagnosis spawn increments `diag_iters`. When `diag_iters >= 5`, stop ALL repair loops.
- Reviewer repair triggers full re-run: Diagnostician → Judge → Reporter → Reviewer.
- Judge iteration counter resets when Reviewer triggers re-diagnosis (no carryover).
- When global cap hit: present results with `[REPAIR_CAP_REACHED]` caveat.

### Counter Persistence

The `diag_iters` counter is file-persisted in `.pipeline_events.jsonl`:
1. Before Step 5: count existing `repair_spawn` entries to restore counter
2. After each re-diagnosis: append `repair_spawn` event with current total
3. On reconnection/context compaction: re-count from file

---

## Step 2.5: Clarification Gate Protocol

After Context Builder completes, check `00_input/clarification_needed.json`:

1. Read the file to understand unknown parameters
2. Group related parameters into single questions (max 4 per round)
3. Present the Context Builder's best guesses for user to confirm/correct
4. After answers: update `01_ontology/ontology.json` and `schema.json`
5. Mark resolved parameters in `clarification_needed.json`
6. Log clarification event to `.pipeline_events.jsonl`

If no CRITICAL/HIGH unknowns, skip directly to Step 3.

---

## Change-Point Segment Verification (Phase 0.5)

When `validate_report.json` detects change points with severity CRITICAL or segment_count > 5:

### Per-Segment Correlation Re-Verification

For each candidate parameter-defect pair, re-verify within regime segments:

| Pattern | |r| > 0.2 in ≥X% segments | Classification |
|---------|:-----------------------:|---------------|
| ALL_PRESENT | ≥80% | REGIME_UNIVERSAL — robust |
| MOST_PRESENT | 50-80% | REGIME_CONSISTENT — mostly preserved |
| PARTIAL | 20-50% | REGIME_SPECIFIC — specific regimes only |
| ABSENT | <20% | REGIME_SPURIOUS — aggregate artifact |

### Segment-Aware Adjustments

- REGIME_SPECIFIC: confidence -10 to -15
- REGIME_SPURIOUS: exclude from hypothesis generation
- REGIME_UNIVERSAL: confidence +5

### Cross-Reference with Product Stratification

If regime boundaries align with product transitions → stratify by product instead.
If NOT → both types of segmentation should be checked.

---

## Statistical Validation Framework

### What Each Check Catches

| Check | Tool | What It Catches |
|-------|------|----------------|
| Data sorting validation | `stats.mjs` | Lag analysis on batch-sorted data → spurious correlations |
| Simpson's Paradox | `stats.mjs` + `stats_validate.mjs` | Aggregate correlations that reverse within subgroups |
| Time-trend confounding | `stats.mjs` | Correlations driven by shared time drifts |
| Outlier sensitivity | `stats_validate.mjs` | Correlations dominated by few extreme points |
| Spearman-Pearson divergence | `stats.mjs` | Outlier or non-linear influence |
| Lag window consistency | `stats.mjs` | Isolated spikes in CCF (artifact indicators) |
| Multiple testing correction | `stats.mjs` | Chance "significant" results from many comparisons |
| Mutual Information | `stats.mjs` | Non-linear dependencies that Pearson/Spearman miss |
| Granger Causality | `stats.mjs` | Temporal predictive causality (requires time-sorted data) |
| Change Point Detection | `stats_validate.mjs` | Regime shifts invalidating stationarity |
| Interaction Effects | `stats.mjs` | Parameter combinations with synergistic effects |

### Confidence Adjustment Rules

| Validation Finding | Impact |
|--------------------|:------:|
| Data NOT time-sorted + lag used as evidence | -25 to -40 |
| Simpson's Paradox (direction reversal) | -20 to -30 |
| Simpson's Paradox (moderate attenuation) | -10 to -15 |
| Trend confounding (attenuation > 50%) | -15 to -20 |
| Outlier-driven correlation | -10 to -15 |
| Spearman-Pearson divergence > 0.15 | -5 to -10 |
| Isolated lag spike | Treat as concurrent only |
| Parameter physical meaning unknown | -15 to -25 |
| Change point detected | -10 to -20 |
| Granger contradicts correlation direction | -20 to -30 |
| INDISTINGUISHABLE competing hypotheses | Ceiling: 65 |
| No discriminating sensor | -15 to -30 |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Lag correlations on non-time-sorted data | Check `sorting_validation.time_sorted` before any lag claim |
| Missing Simpson's Paradox | Stratified analysis + `stats_validate.mjs` detect reversals |
| Confusing trend correlation with causal coupling | Check detrended correlations |
| Trusting Pearson for skewed defect data | Compare Spearman alongside |
| Stating "X caused Y" without all 4 criteria | Use [HYPOTHESIS] marker |
| Skipping `plot_manifest.json` | Data Processor MUST write it |
| Main agent holding domain context | Spawn sub-agents; main agent only orchestrates |
| Skipping physical audit (Step 7) | Always run — catches spurious correlations |
| Not validating parameter physical meaning | Use clarification gate (Step 2.5) |
| Ignoring reviewer's physical concerns | Step 7.5 repair loop |
| Picking one root cause when alternatives predict identical observables | Step C: Data Discriminability → COMPETING_SET |
| High confidence on time-colinear mechanisms | Both progress with time → ceiling 65 |
| Not checking if quality resets on component replacement | Phase 1 data probing — use transition events |
