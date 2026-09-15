---
name: industrial-analysis-enhance-auto
description: >
  Industrial Analysis Enhancement Auto — fully automated enhanced-diagnostic pipeline orchestration.
  Orchestrates E0 readiness check through E8 finalization: launches E1-E4 deep analysis scripts,
  E5 physics bridge, E6 knowledge fusion, E7a markdown publishing, E7b HTML visualization, E7c HTML review.
  Reads an existing diagnostic RUN_DIR; writes only to RUN_DIR/enhancement/.
  Use as the CLI entry point for the full enhancement pipeline, whenever a completed diagnostic run
  needs automated deep enhancement, or when new data must be taken through the baseline pipeline
  plus the E0-E8 enhancement stages in one call.
  Trigger: enhance auto, enhanced auto, enhancement orchestration, E1-E8 pipeline,
  full-auto enhancement, auto enhance, enhance pipeline.
---

# Industrial Analysis Enhancement Auto

Fully automated enhancement pipeline for industrial diagnostics. Starting from an existing diagnostic `RUN_DIR`, it executes in sequence:

| Stage | Script | Function |
|------|------|------|
| E-1 | `data_preprocessor.py` (data-preprocessor) | Adaptive data preprocessing: any format/directory → `00_input/preprocessed_data.csv` + report |
| E0 | `enhance_orchestrator.mjs` | Baseline readiness check, sha256 verification, manifest generation |
| E1 | `coverage_builder.py` (deep-analysis) | Full-column coverage analysis → `analysis_coverage.json` |
| E2 | `derived_feature_builder.py` (deep-analysis) | Physical derived-feature construction → `derived_features.json` |
| E3 | `conditional_analysis.py` (deep-analysis) | Conditional relationship analysis + actionability + reasoning evidence → `deep_data_analysis.json` |
| E3.5 | `association_graph_builder.py` (deep-analysis) | Full-variable association network + temporal/conditional-independence/mediation/change-point/leverage inference → `association_graph.json` |
| E5 | `physics_bridge_builder.py` (physics-bridge) | Physical mechanism bridging → `physics_bridge.json` |
| E6 | `knowledge_fusion.py` | Knowledge fusion → `enhanced_knowledge.json` |
| E7a | `markdown_publisher.py` | Markdown publishing → `enhanced_analysis.md` |
| E7b | `html_builder.py` (enhanced-html-visualizer) | ECharts HTML visualization → `enhanced-analysis.html` |
| E7c | `html_reviewer.py` (enhanced-html-reviewer) | HTML review → `enhancement_html_review.json` |
| E8 | `enhance_orchestrator.mjs` (finalize) | Status writing, summary output |

## Inputs (read-only)

All inputs are read from `RUN_DIR` and never modified:

- `01_ontology/ontology.json`
- `02_processed/cleaned_data.csv`
- `02_processed/feature_summary.json`
- `02_processed/analysis_parameter_selection.json`
- `02_processed/validate_report.json`
- `02_processed/data_analysis_conclusion.json`
- `02_processed/production_regime_filter.json` (optional)
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `03_figures/plot_manifest.json`
- `03_figures/visual_analysis.json`

## Outputs (write only)

All outputs are written to `RUN_DIR/enhancement/`:

| File | Stage | Description |
|------|------|------|
| `enhancement_manifest.json` | E0 | Runtime manifest |
| `analysis_coverage.json` | E1 | Column coverage analysis |
| `derived_features.json` | E2 | Derived features |
| `deep_data_analysis.json` | E3 | Deep data analysis |
| `physics_bridge.json` | E5 | Physics bridge |
| `enhanced_knowledge.json` | E6 | Enhanced knowledge integration |
| `enhanced_analysis.md` | E7a | Markdown report |
| `enhanced-analysis.html` | E7b | ECharts visualization page |
| `html_selfcheck.json` | E7b | Page runtime self-check |
| `enhancement_html_review.json` | E7c | HTML review result |
| `enhancement_status.json` | E8 | Final status |

## Usage

### Two Modes

| Mode | Invocation | Behavior |
|------|---------|------|
| **Mode A: integrated auto full pipeline (new data)** | `--data-path <data> --name <run_name>` or pass `DATA_PATH` to the agent | (1) Automatically initialize RUN_DIR (setup + inspect + manifest) → (2) Execute the auto Step 0-9 baseline (agent orchestration) → (3) E0-E8 deep enhancement. One invocation completes the whole flow |
| **Mode B: build on an existing RUN_DIR (deep analysis)** | `--run-dir <RUN_DIR>` | Skip the baseline and run E0-E8 directly (E0 verifies baseline artifacts; BLOCKED if missing) |

**Mode A is a complete closed loop**: the CLI performs deterministic initialization (`entry_a_init.mjs`); the LLM baseline steps (ontology building / data processing / competing-hypothesis diagnosis / report / HTML) are dispatched in sequence by the enhance-orchestrator agent following the Step 0-9 order of `skill://industrial-analysis-auto`; once the baseline `optimizer.md` contains ENDORSED, E0-E8 starts automatically.

### Mode A: new-data full pipeline (CLI initialization + agent baseline + enhancement)

```bash
# CLI initialization (deterministic parts: setup + inspect + manifest + baseline detection)
node .claude/skills/industrial-analysis-enhance-auto/scripts/entry_a_init.mjs \
  --data-path data/<file>.csv --name <run_name>

# Or trigger directly via the orchestrator (equivalent)
node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs \
  --data-path data/<file>.csv --name <run_name>
```

If the baseline is incomplete after initialization, the output contains `BASELINE_PENDING` + the list of missing items + the agent dispatch order required. For **full automation**, pass `DATA_PATH` to the enhance-orchestrator agent: the agent dispatches context-builder → data-processor → diagnostician → judge/pre-audit → reporter → final-audit → html-visualizer → html-reviewer in order, then executes E0-E8.

### Mode B: deep analysis on an existing RUN_DIR

```bash
node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs \
  --run-dir workspace/diagnostic-runs/<RUN_DIR>
```

Prints status JSON to stdout. Exit code 0 on success, 1 if BLOCKED or FAILED.

## Enhancement Status Logic

| Condition | Status |
|------|------|
| All relationships actionable, no confounding >30% | `READY` |
| >30% of relationships CONFOUNDED or NOT_IDENTIFIABLE | `READY_WITH_WARNINGS` |
| P0 baseline files missing (Mode B) | `BLOCKED` |
| Mode A baseline incomplete | `BASELINE_PENDING` |
| Any enhancement script returns a non-zero exit code | `FAILED` |

## Operability Enum Values

Consistent with `deep_data_analysis_schema.json`:

1. `LEVER_IDENTIFIED` — confirmed actionable lever
2. `LEVER_OBSERVATIONAL` — observational association (not currently a lever)
3. `ENDOGENOUS_RESPONSE` — endogenous response (direction contradicts physics)
4. `CONFOUNDED` — confounded (Simpson/group reversal or temporal confounding)
5. `NOT_IDENTIFIABLE` — not identifiable
6. `CONSTRAINT_UNCONTROLLABLE` — uncontrollable constraint condition

## Markdown Contract

- 15 sections (`## 0.` through `## 14.`), report in Chinese; §0 = AI-actionable summary (machine-readable JSON block; the primary consumption interface for downstream agents)
- Each core relationship conclusion embeds a ```json block (claim_id, status, source, mask, n, method, effect, causal_ceiling, not_for)
- §2 control levers, §3 influence matrix, §4 multi-hop causal paths, §5 parameter centrality, §6 physical context mapping are new sections added for AI deep analysis
- Zero hardcoded numbers — everything is template-substituted from `enhanced_knowledge.json`
- Every numeric value carries a unit
- JSON enums in English, prose in Chinese
- Do not use raw JSON field names such as `dY_dX_linear` or `partial_r`

## Verification

```bash
# Full pipeline on any RUN_DIR (example: CSTR catalyst run)
node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs \
  --run-dir <RUN_DIR>

# Validate enhanced_knowledge.json
node .claude/shared/scripts/validate.mjs \
  .claude/shared/schemas/enhanced_knowledge_schema.json \
  <RUN_DIR>/enhancement/enhanced_knowledge.json

# Reproduce markdown standalone
uv run --project "$SHARED_PATH/scripts" python .claude/skills/industrial-analysis-enhance-auto/scripts/markdown_publisher.py \
  --knowledge <RUN_DIR>/enhancement/enhanced_knowledge.json \
  --template .claude/skills/industrial-analysis-enhance-auto/templates/enhanced_analysis.md.tmpl \
  --output <RUN_DIR>/enhancement/enhanced_analysis_v2.md

# Check for hardcoded numbers, raw field names, section count
uv run --project "$SHARED_PATH/scripts" python -c "
import json, re
# Section count
with open('<RUN_DIR>/enhancement/enhanced_analysis.md') as f:
    md = f.read()
sections = re.findall(r'^## \d+\.', md, re.MULTILINE)
print(f'## sections: {len(sections)}')
# Embedded JSON blocks
json_blocks = re.findall(r'\x60\x60\x60json\n(.*?)\n\x60\x60\x60', md, re.DOTALL)
print(f'JSON claim blocks: {len(json_blocks)}')
# No raw field names in PROSE (machine-readable regions — the embedded ```json
# claim blocks and the §9 appendix — intentionally contain raw JSON by contract)
md_prose = md.split('## 9.')[0]
md_prose = re.sub(r'```json\n.*?\n```', '', md_prose, flags=re.DOTALL)
bad = ['dY_dX_linear', 'partial_r', 'detrended_r']
for b in bad:
    if b in md_prose:
        print(f'WARN: raw field name {b!r} found in prose')
    else:
        print(f'OK: no {b!r} in prose')
# No hardcoded numbers (check in non-code non-table context)
# Status check
print('Status:', 'READY_WITH_WARNINGS' in md)
"
```

## References

- `references/orchestration-protocol.md` — detailed description of the E0-E8 stage protocol
