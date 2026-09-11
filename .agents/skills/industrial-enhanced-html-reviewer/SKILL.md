---
name: industrial-enhanced-html-reviewer
description: >
  Enhanced HTML Reviewer — reviews enhanced-analysis.html against
  enhanced_knowledge.json. Checks hero clarity, evidence completeness,
  logic chain, chart initialization, data governance card, and runtime
  fallback mechanisms. Outputs enhancement_html_review.json with
  verdict (pass/warn/fail) and overall_score (0-100).
  Trigger: enhanced html review, enhanced review, enhanced HTML review,
  enhanced audit review, enhancement_html_review.
  Use after industrial-enhanced-html-visualizer generates enhanced-analysis.html.
---
# Industrial Enhanced HTML Reviewer

Reviews whether `enhanced-analysis.html` meets the visualization quality standards.

## Inputs

| Required | Path | Description |
|----------|------|-------------|
| P0 | `RUN_DIR/enhancement/enhanced_knowledge.json` | Enhanced knowledge fusion output |
| P0 | `RUN_DIR/enhancement/enhanced-analysis.html` | HTML page under review |
| P1 | `RUN_DIR/enhancement/html_selfcheck.json` | Build-time self-check (optional) |

## Outputs

`RUN_DIR/enhancement/enhancement_html_review.json`:

```json
{
  "verdict": "pass",
  "overall_score": 92,
  "blocking_issues": [],
  "warnings": ["Consider adding mechanism-chain drill-down"],
  "checks": [
    {"name": "hero_clarity", "status": "pass", "evidence": "..."},
    {"name": "evidence_layer_1_statistical", "status": "pass", "evidence": "..."},
    {"name": "evidence_layer_2_physics", "status": "pass", "evidence": "..."},
    {"name": "chart_initialization", "status": "pass", "evidence": "..."},
    {"name": "three_d_fidelity", "status": "pass", "evidence": "..."},
    {"name": "data_governance", "status": "pass", "evidence": "..."},
    {"name": "degraded_mode_fallback", "status": "pass", "evidence": "..."},
    {"name": "size_requirement", "status": "pass", "evidence": "..."},
    {"name": "data_fidelity", "status": "pass", "evidence": "..."}
  ]
}
```

## Review Dimensions

1. **Hero clarity** — whether the first screen contains a status badge, title, key findings, and an operability summary
2. **Evidence completeness** — whether all 5 chart containers are present
3. **Chart initialization** — whether CDN multi-source loading (jsdelivr + unpkg + cdnjs) is fully configured
4. **Runtime self-check** — whether the page contains echarts_available / degraded_mode self-check logic
5. **Data governance** — whether the data provenance card includes SHA256, row count, and source artifacts
6. **Degraded mode** — whether static-table degradation is ready
7. **Size requirement** — HTML ≥ 5120 bytes
8. **Data fidelity** — whether the HTML content references data from enhanced_knowledge.json

## Decision Rule

- `pass`: score ≥ 75, no blocking issues
- `warn`: score ≥ 50 but < 75, or non-blocking warnings
- `fail`: blocking issues exist or score < 50

## Usage

```bash
uv run --project .claude/shared/scripts python .claude/skills/industrial-enhanced-html-reviewer/scripts/html_reviewer.py \
  --knowledge <enhanced_knowledge.json> \
  --html <enhanced-analysis.html> \
  --output <DIR>/enhancement_html_review.json
```

## References

- `references/agent-protocol.md` — Reviewer agent execution protocol