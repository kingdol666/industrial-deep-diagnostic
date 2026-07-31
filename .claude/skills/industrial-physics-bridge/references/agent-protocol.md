# Agent Protocol: Physics Bridge Builder

## Agent Identity

The physics-bridge agent runs the `physics_bridge_builder.py` script to produce `physics_bridge.json`. It is a deterministic, zero-LLM execution agent.

## Preconditions

All files must exist in the RUN_DIR:
- `01_ontology/ontology.json`
- `02_processed/physics_check.json`
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `03_figures/visual_analysis.json`
- `enhancement/deep_data_analysis.json`

## Execution

1. **Load SKILL.md.** Read `.claude/skills/industrial-physics-bridge/SKILL.md`.
2. **Run the script.** Execute `python .claude/skills/industrial-physics-bridge/scripts/physics_bridge_builder.py --run-dir <RUN_DIR>`.
3. **Validate output.** Run `node .claude/shared/scripts/validate.mjs .claude/shared/schemas/physics_bridge_schema.json <RUN_DIR>/enhancement/physics_bridge.json`.
4. **Check AC-2 (scene-agnostic).** For every relationship whose ontology marks `data_direction_validated=false`, verify `direction=MISMATCH` and `overall_status=inconsistent` in the output.
5. **Verify counts.** Assert ≥1 mechanism_chain, ≥1 competing_explanation, ≥2 evidence_gaps.
6. **Write report.** Record results to `.superpowers/sdd/doe-enhance-plan/task-4-report.md`.

## Error Handling

| Condition | Action |
|-----------|--------|
| `--run-dir` not found | Exit code 1 with error message |
| Missing required input file | Exit code 1 listing missing files |
| Schema validation fails | Report validation errors, do not proceed |
| AC-2 assertion fails | Report mismatch, do not proceed |
| Number of mechanism_chains = 0 | Report error, diagnose missing surviving hypotheses |

## Constraints

- Never modify files outside `enhancement/` or the skill directory.
- Use only Python standard library for the script.
- Do not run formatters, linters, or project-wide test suites.
