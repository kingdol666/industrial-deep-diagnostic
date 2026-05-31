# CLAUDE.md — Skill Developer Notes

## Project Overview
Industrial time-series diagnostic skill. Lives in `.claude/skills/industrial-deep-diagnostic/`.

## Authoritative Source
**SKILL.md is authoritative.** If this file conflicts with SKILL.md, trust SKILL.md.

## Language Default
默认中文输出。报告、诊断结论、审计文档使用中文。Schema enum字段保持英文。

## Key Gotchas (not in SKILL.md)

| Gotcha | Details |
|--------|---------|
| `time_col` detection | `inspect.mjs` auto-detects by keyword + type. Can fail on non-standard names — verify. |
| Python path in worktrees | If running in a worktree, all paths must be absolute. `uv_env_setup.mjs` resolves correctly. |
| Repair counter persistence | `diag_iters` tracked in `.pipeline_events.jsonl` via `repair_spawn` events — DO NOT rely on in-memory state |
| Image captions fallback | `image_captions.json` is the fallback when PNG rendering fails. Never write "*Image unavailable*" if captions exist. |
| CLAUDE.md vs SKILL.md | SKILL.md is the entry point for pipeline execution. This file is developer reference only. |

## Numbering Systems (four distinct schemes)

This skill uses **four separate numbering systems by design**. Do not conflate them:

| System | Scope | Example |
|--------|-------|---------|
| Pipeline Step 0-8 | Orchestration | "Step 4: Diagnostician" |
| Agent Phase 0-6 | Diagnostician internal | "Phase 1: Data Probing" |
| Reasoning Segment R1-R8 | Reasoning_chain.json | "R4: Hypothesis Generation" |
| Method Stage 1-6 | diagnosis_method.md | "Stage 3: Temporal Analysis" |

Each numbering system is scoped to its own context (orchestration / agent logic / output artifact / reference doc). When adding new numbering, ensure it does not collide with existing systems.

## Directory Conventions

| Directory | Purpose | When to Add |
|-----------|---------|-------------|
| `templates/` | Output format templates (report, diagnosis, judge) | New output format |
| `schemas/` | JSON Schema for output validation | New structured artifact |
| `assets/` | Shared binary/media resources (watermarks, icons, cover images) | Visual assets used by templates or reports |
| `scripts/` | Executable pipeline code (Node.js + Python/uv) | Reusable deterministic logic |
| `references/` | Domain knowledge loaded on demand by sub-agents | Process-specific reference docs |
| `examples/` | Sample inputs/ontologies for common process types | Reference for context builder |

**`templates/` vs `assets/` distinction**: templates are text-based skeletons filled by reporter/agents; assets are binary/media resources referenced from those templates.

## CLI Commands
- `/industrial-deep-diagnostic` — Full pipeline (Steps 0-8)
- `/industrial-deep-diagnostic analyze` — Skip intake, run from Step 2
- `/industrial-deep-diagnostic review` — Re-run judge on existing results
- `/industrial-deep-diagnostic report` — Regenerate report
- `/industrial-deep-diagnostic audit` — Run report-reviewer only

## Python Execution
All Python scripts MUST run in `scripts/.venv/bin/python` (managed by `uv_env_setup.mjs`). Never system python3. Run `node scripts/uv_env_setup.mjs` first to get the path.
