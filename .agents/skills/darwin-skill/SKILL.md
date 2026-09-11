---
name: darwin-skill
description: "Darwin evolutionary skill evaluation tracker — tracks skill quality scores across dimensions over time. Used for internal skill fitness assessment and evolution tracking. Trigger: skill fitness, skill evaluation, skill quality, evolutionary tracking, skill evolution."
---

# Darwin Skill — Evolutionary Skill Quality Tracker

Tracks skill quality scores across evaluation dimensions over commit history. Used for internal OMP skill fitness monitoring.

## Overview

This skill provides evolutionary fitness tracking for OMP skills. It records baseline evaluations and score changes across skill versions, enabling data-driven skill improvement.

## Data

Evaluation results are stored in `results.tsv`:

| Column | Description |
|--------|-------------|
| timestamp | Evaluation date/time |
| commit | Git commit reference |
| skill | Skill being evaluated |
| old_score | Previous score (or `-` for baseline) |
| new_score | Current evaluation score |
| status | baseline / improved / regressed |
| dimension | Evaluation dimension affected |
| note | Free-text evaluation notes |
| eval_mode | dry_run / live |

## Data Truth Mandate

**Every number written into JSON/reports must be recomputable from the raw data.**
|Rule|Requirement|
|---|---|
|Number traceability|Every number must state its data source (cleaned/raw), row range, and computation method|
|Derived-value marking|Inferred/derived values must be explicitly marked `"derived": true` or `"inferred": true`|
|Cleaning audit trail|cleaning_integrity records all cleaning operations|
|Visualization traceability|Every data point in every figure must be traceable to specific dataset rows|
|Unavailable marking|Values that cannot be computed from the data → write NOT_APPLICABLE + reason|

## Counterfactual Reasoning — Exclusion Constraints

|Constraint|Description|
|---|---|
|Four conditions|Temporal precedence + statistical significance + physical mechanism + no contradiction|
|Exclusion criterion|Any unmet condition → mark as an exclusion candidate with quantitative justification|
|Physics boundary|Exclusions must be supported by first principles or governing equations|
|Confidence threshold|Exclusion confidence < 80 → mark `[WEAK_EXCLUSION]`|

## Assumptions & Limitations

|Category|Requirement|
|---|---|
|Data limitations|Sampling rate / noise / missing extremes / range limits|
|Model assumptions|Linear approximation / steady-state assumption / distribution assumptions|
|Uncontrolled confounders|Explicitly list potential confounding variables that cannot be controlled|
|Conclusion confidence intervals|Each conclusion annotated with confidence ± error margin|

## Efficiency — Parallel Execution

- No data dependency with upstream/downstream agents → parallelize proactively
- Use deterministic scripts instead of LLM reasoning for predictable results
- Large-file sampling strategy: systematic sampling for >100K rows
- Agent stall >600s → inspect existing artifacts; proceed with partially usable outputs

## Usage

```bash
# View evaluation history
cat .claude/skills/darwin-skill/results.tsv

# Append a new evaluation
echo "$(date -Iseconds)\t<commit>\t<skill-name>\t<old>\t<new>\t<status>\t<dim>\t<note>\tdry_run" >> .claude/skills/darwin-skill/results.tsv
```

## Integration

This skill is used by the OMP harness to track skill quality trends. Not part of the industrial diagnostic pipeline — it's a meta-skill for OMP skill governance.