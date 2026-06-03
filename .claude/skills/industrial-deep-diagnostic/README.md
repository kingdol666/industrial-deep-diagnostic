# Industrial Deep Diagnostic

A production-grade, evidence-first industrial time-series analysis and diagnostic Skill for Claude Code.

## Features

- **Ontology-guided analysis**: Builds or uses industrial process ontologies to structure understanding
- **Multi-source evidence**: Combines data, local documents, web research, and statistical analysis
- **Self-correcting pipeline**: Judge agent reviews every conclusion with a repair loop (max 3 iters); physical-truth auditor provides independent reality check
- **Full artifact persistence**: Timestamped run directories with all intermediate outputs
- **Statistical validation**: Built-in Simpson's Paradox, trend confounding, change-point detection
- **Expert data-analysis handoff**: Fixed baseline scripts plus focused custom scripts produce `02_processed/data_analysis_conclusion.json`
- **Physical dual-drive engine**: Combines process-parameter fluctuation analysis with inspection/quality anomalies and physics checks
- **Anti-speculation enforcement**: Evidence hierarchy + STOP checklist + confidence ceilings
- **Execution-proof logging**: `.pipeline_events.jsonl` plus `run_manifest.json` now jointly prove step order, retries, and declared outputs
- **Evidence-closure proof**: `evidence_closure_report.json` proves the run closed the loop from process evidence to dual-drive diagnosis to final report

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
├── agents/                  ←  7 sub-agent instructions
│   ├── context-builder.md
│   ├── data-processor.md
│   ├── diagnostician.md
│   ├── judge.md
│   ├── reporter.md
│   ├── report-reviewer.md
│   └── vlm-visual-analyzer.md
├── schemas/                 ←  12 JSON Schemas for output validation
├── scripts/                 ←  Pipeline scripts (Node.js + Python/uv)
├── resources/               ←  Domain knowledge base and execution references
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

## Required Execution Outputs

The full pipeline is strict: every step must run or record a documented not-applicable condition. Key outputs include:

- `02_processed/analysis_plan.md` — Data Processor's plan before running scripts
- `00_input/run_config.json` — standardized run contract; must be updated with actual data path and execution constraints
- `02_processed/data_analysis_conclusion.json` — expert handoff with baseline results, custom analysis, ontology interpretation, and caveats
- `03_figures/fig_master_time_aligned_overlay.png` — generated when a valid time column exists
- `03_figures/visual_analysis.json` — structured visual/VLM evidence from generated plots
- `04_diagnostics/diagnosis.json` — final physics-grounded diagnosis with competing hypotheses
- `.pipeline_events.jsonl` — execution proof that the agents actually ran in pipeline order and respected repair-loop limits
- `evidence_closure_report.json` — machine-readable proof that pure-process evidence, dual-drive evidence, ontology/physics interpretation, diagnosis, and report handoff are coherently connected

Validate a completed run with:

```bash
node .claude/skills/industrial-deep-diagnostic/scripts/finalize-run-artifacts.mjs <run_dir> .claude/skills/industrial-deep-diagnostic
node .claude/skills/industrial-deep-diagnostic/scripts/artifact-check.mjs <run_dir> .claude/skills/industrial-deep-diagnostic
```

`finalize-run-artifacts.mjs` now also writes `evidence_closure_report.json`, and `artifact-check.mjs` now treats both execution-proof integrity and evidence-closure integrity as first-class final gates.

## Eval Compatibility

`evals/evals.json` is maintained in a dual-compatible form:

- `expectations` supports the standard `skill-creator` grading / benchmark flow
- `assertions` keeps the richer JSON-path-based checks used by this diagnostic skill

This lets the skill preserve domain-specific checks while still fitting the broader skill improvement toolchain.

Programmatic assertion grading is available via:

```bash
node .claude/skills/industrial-deep-diagnostic/scripts/eval-assertions.mjs \
  .claude/skills/industrial-deep-diagnostic/evals/evals.json \
  1 \
  <run_dir> \
  --write-grading
```

This evaluates the domain-specific `assertions` against run artifacts and writes skill-creator-compatible `grading.json`.

## Example Scenarios

- BOPET film thickness anomaly analysis
- Reactor temperature runaway diagnosis
- CNC spindle bearing spalling
- Fan vibration analysis
- Heat exchanger fouling progression
- PVA optical film defect analysis

## Online Integration

This skill can be integrated into an online system that pulls data from databases / historians / MES / quality systems on demand. The recommended insertion points are documented in `resources/online_integration_entrypoints.md:1`.

## License

MIT

## Engineering Acceptance

For a run to be considered deployable, it must satisfy the contract in `resources/engineering_delivery_contract.md`.
