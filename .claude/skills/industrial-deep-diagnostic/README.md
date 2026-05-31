# Industrial Deep Diagnostic

A production-grade, evidence-first industrial time-series analysis and diagnostic Skill for Claude Code.

## Features

- **Ontology-guided analysis**: Builds or uses industrial process ontologies to structure understanding
- **Multi-source evidence**: Combines data, local documents, web research, and statistical analysis
- **Self-correcting pipeline**: Judge agent reviews every conclusion with a repair loop (max 3 iters); physical-truth auditor provides independent reality check
- **Full artifact persistence**: Timestamped run directories with all intermediate outputs
- **Statistical validation**: Built-in Simpson's Paradox, trend confounding, change-point detection
- **Physical dual-drive engine**: Automated `physics_check.py` pre-computes thermal, vibration, and kinetic checks
- **Anti-speculation enforcement**: Evidence hierarchy + STOP checklist + confidence ceilings

## Quick Start

```bash
# Start a diagnostic session
/industrial-deep-diagnostic

# Analyze with specific data
/industrial-deep-diagnostic analyze --data-path ./sensor_data.csv

# Run pipeline steps individually (after initial intake)
/industrial-deep-diagnostic review    # Re-run judge
/industrial-deep-diagnostic report    # Regenerate report
/industrial-deep-diagnostic audit     # Physical-truth audit only
```

## Input Formats

Supported: **CSV, XLSX, Parquet, JSON, Feather** — any columnar time-series with at least one quality/defect target column.

## Skill Structure

```
.claude/skills/industrial-deep-diagnostic/
├── SKILL.md                 ←  Pipeline orchestration (entry point)
├── CLAUDE.md                ←  Developer notes (SKILL.md is authoritative)
├── README.md                ←  This file — quick start guide
├── agents/                  ←  6 sub-agent instructions
│   ├── context-builder.md
│   ├── data-processor.md
│   ├── diagnostician.md
│   ├── judge.md
│   ├── reporter.md
│   └── report-reviewer.md
├── schemas/                 ←  14 JSON Schemas for output validation
├── scripts/                 ←  Pipeline scripts (Node.js + Python/uv)
├── references/              ←  Domain knowledge base
├── templates/               ←  Output templates (report, diagnosis, judge)
├── evals/                   ←  5 formal test scenarios with assertions
├── tests/                   ←  Quality checklists
└── assets/                  ←  Shared resources (icons, watermark templates)
```

## Configuration Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `data_path` | Yes | Path to time-series data |
| `ontology_path` | No | Pre-defined ontology JSON |
| `reference_dir` | No | Reference documents directory |
| `process_description` | No | Process description text |
| `interaction_mode` | No | `auto` / `interactive` / `minimal` (default: `auto`) |
| `user_objective` | No | Analysis objective |
| `known_faults` | No | Known fault patterns |
| `analysis_constraints` | No | Analysis constraints |

## Example Scenarios

- BOPET film thickness anomaly analysis
- Reactor temperature runaway diagnosis
- CNC spindle bearing spalling
- Fan vibration analysis
- Heat exchanger fouling progression
- PVA optical film defect analysis

## License

MIT
