# CLAUDE.md — Industrial Deep Diagnostic Skill

## Project Overview

Claude Code Skill for evidence-first industrial time-series analysis and root cause diagnostic.
Lives in `.claude/skills/industrial-deep-diagnostic/`.

## Architecture Notes

- **Orchestration**: `SKILL.md` defines the workflow. Main agent only orchestrates — never holds domain context.
- **Agent prompts**: `agents/*.md` — each defines one sub-agent's instructions and output contract.
- **Agent decoupling**: Agents communicate exclusively through workspace files (see SKILL.md for the file chain).
- **Script philosophy**: Node.js for fixed operations (zero-dep, always works). Python as adaptive toolkit (agent selects primitives by data dimension).

## File Organization

```
SKILL.md              — Skill definition, workflow, commands (authoritative source)
CLAUDE.md             — This file: developer notes, conventions, gotchas
agents/               — Sub-agent prompt files (context-builder, data-processor, diagnostician, judge, reporter)
scripts/              — Node.js utils (inspect.mjs, stats.mjs, setup.mjs) + Python toolkit (template_visualize.py, template_preprocess.py)
resources/            — Reference docs loaded by agents (evidence_rules, diagnosis_method, process_knowledge_base)
schemas/              — JSON Schema draft-07 for ontology, signals, analysis, run_config, report
templates/            — Output templates (report, diagnosis, judge, input_manifest, run_summary)
tests/                — Checklists (per-agent QA) + fixtures (sample CSV, config)
examples/             — Domain-specific sample ontologies (reactor, BOPET film)
```

## Key Conventions

- **Evidence hierarchy**: 7 ranks (1=direct data → 7=hypothesis). Every conclusion cites its rank.
- **Anti-speculation**: 4 criteria required for causation (temporal precedence, statistical evidence, physical mechanism, no contradictions). Missing any → [HYPOTHESIS].
- **Judge quality gate**: Score >= 90 required before report generation. Max 3 repair iterations.
- **Workspace persistence**: All outputs go to `./workspace/diagnostic-runs/<timestamp>_<name>/`.

## Visualization Toolkit (`scripts/template_visualize.py`)

- NOT a fixed script. A library of ~16 composable primitives covering 5 data dimension patterns.
- Agent calls `detect_data_pattern()` to classify data, then selects primitives by pattern.
- Each primitive returns generation metadata → feeds `plot_manifest.json`.
- Dependencies: matplotlib, pandas, numpy only (NO scipy — STFT is numpy-only implementation).

## Gotchas

- **CLAUDE.md vs SKILL.md**: SKILL.md is authoritative. This file is developer reference only. If they conflict, trust SKILL.md.
- **Agent output paths**: Each agent's prompt specifies exact output paths under `RUN_DIR/`. The main agent must pass `RUN_DIR` correctly when spawning.
- **Python execution**: Always try `python3` first, fall back to `python3.11`. If matplotlib missing: `pip3 install matplotlib numpy pandas`.
- **time_col detection**: `inspect.mjs` auto-detects time columns by keyword + type inference. Can fail on non-standard column names — the main agent should verify and override.
- **stats.mjs requires JSON input**: The main agent must convert CSV to JSON via Node one-liner before calling stats.mjs (see data-processor.md Step 2).
- **Worktree isolation**: If the skill runs in a worktree, `RUN_DIR` will be inside the worktree. All paths must be absolute.
