# Industrial Deep Diagnostic

A production-grade, evidence-first industrial time-series analysis and diagnostic Skill for Claude Code.

## Features

- **Ontology-guided analysis**: Builds or uses industrial process ontologies to structure understanding
- **Multi-source evidence**: Combines data, local documents, web research, and statistical analysis
- **Self-correcting**: Judge agent reviews every conclusion with a repair loop
- **Full artifact persistence**: Timestamped run directories with all intermediate outputs
- **Publication-quality visualizations**: Engineering-standard plots with anomaly markers
- **Evidence hierarchy**: Every conclusion ranked by evidence reliability
- **Anti-speculation enforcement**: Strict rules against unsupported causal claims

## Quick Start

```bash
# Start a diagnostic session
/industrial-deep-diagnostic

# Analyze with specific data
/industrial-deep-diagnostic analyze --data-path ./sensor_data.csv

# Review existing results
/industrial-deep-diagnostic review

# Regenerate report
/industrial-deep-diagnostic report

# Compare two runs
/industrial-deep-diagnostic compare
```

## Input Formats

Supported data formats: CSV, XLSX, Parquet, JSON, Feather

## Workflow

1. **Intake** — Validate data, ask clarification questions
2. **Reference search** — Extract knowledge from user-provided documents
3. **Web research** — Fill domain knowledge gaps (optional)
4. **Ontology** — Build process ontology
5. **Schema** — Normalize columns and units
6. **Classification** — Separate inspection, process, control, event signals
7. **Data engineering** — Clean, resample, preprocess
8. **Alignment** — Synchronize on common time axis
9. **Features** — Compute statistical features
10. **Visualization** — Generate engineering plots
11. **Diagnosis** — Identify anomalies with evidence
12. **Judge** — Verify conclusions (iterate until score >= 90)
13. **Report** — Generate professional Markdown report
14. **Persist** — Save all artifacts

## Configuration

| Parameter | Required | Description |
|-----------|----------|-------------|
| `data_path` | Yes | Path to time-series data |
| `ontology_path` | No | Pre-defined ontology JSON |
| `reference_dir` | No | Reference documents directory |
| `process_description` | No | Process description text |
| `scene_name` | No | Scene identifier |
| `batch_id` | No | Batch identifier |
| `output_dir` | No | Output directory override |
| `user_objective` | No | Analysis objective |
| `known_faults` | No | Known fault patterns |
| `analysis_constraints` | No | Analysis constraints |

## Output

All outputs are saved to `~/.claude/industrial-deep-diagnostic/runs/<timestamp>_<batch_id>/`:

```
run_root/
├── input_manifest.json      # Input configuration
├── user_context.json        # User-provided context
├── ontology.json            # Process ontology
├── schema.json              # Normalized schema
├── references/              # Extracted reference knowledge
├── research/                # Web research findings
├── processed/               # Cleaned and aligned data
├── figures/                 # Generated plots
├── diagnostics/             # Diagnosis results
├── review/                  # Judge feedback
├── report.md                # Final report
└── run_summary.json         # Run metadata
```

## Example Scenarios

- BOPET film thickness anomaly analysis
- Reactor temperature runaway diagnosis
- Fan vibration analysis
- Boiler combustion instability
- Extrusion melt pressure fluctuation
- PVA optical film defect analysis

## Evidence Standards

Every conclusion is backed by ranked evidence:

1. Direct measurements (highest confidence)
2. User-provided documentation
3. Statistical analysis
4. Visual evidence
5. Process logic
6. External references
7. Hypotheses (lowest confidence, always labeled)

## License

MIT
