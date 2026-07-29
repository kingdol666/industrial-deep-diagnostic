---
name: darwin-skill
description: "Darwin evolutionary skill evaluation tracker — tracks skill quality scores across dimensions over time. Used for internal skill fitness assessment and evolution tracking. Trigger: skill fitness, 技能评估, skill quality, evolutionary tracking, 技能进化."
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

## Usage

```bash
# View evaluation history
cat .claude/skills/darwin-skill/results.tsv

# Append a new evaluation
echo "$(date -Iseconds)	<commit>	<skill-name>	<old>	<new>	<status>	<dim>	<note>	dry_run" >> .claude/skills/darwin-skill/results.tsv
```

## Integration

This skill is used by the OMP harness to track skill quality trends. Not part of the industrial diagnostic pipeline — it's a meta-skill for OMP skill governance.
