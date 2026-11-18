---
name: industrial-enhanced-html-reviewer
description: >
  Enhanced HTML Reviewer — reviews the enhanced ECharts page (enhanced-analysis.html) against
  enhanced_knowledge.json via the deterministic scripts/html_reviewer.py. Checks hero clarity,
  evidence completeness, chart initialization, runtime self-check/fallback, data governance card,
  size requirement, and data fidelity. Outputs enhancement_html_review.json with
  verdict (pass/warn/fail) and overall_score (0-100).
  Trigger: enhanced html review, enhanced review, enhanced HTML review,
  enhanced audit review, enhancement_html_review.
  Review-only and enhanced-mode-only: never builds or edits the page (→ industrial-enhanced-html-visualizer),
  does not review the standard diagnostic-report.html (→ industrial-html-reviewer), and never performs
  the analysis itself (→ industrial-analysis-enhance-auto / industrial-diagnostician).
---

# Industrial Enhanced HTML Reviewer

Reviews whether `<RUN_DIR>/enhancement/enhanced-analysis.html` meets the visualization quality standards, by
running the deterministic reviewer script against `enhanced_knowledge.json`. **Enhanced mode review** — the
plain-page review protocol (six objectives, red-line blacklist, `html_review.json`) belongs to
`industrial-html-reviewer` and is defined once in the authority's `review-checklist.md`; this skill reviews the
enhanced page with its own script-authored checks.

## Shared protocol & checklists (read these; do not restate)

- Mode-specific execution checklist (reading order, per-dimension rules, pass standard):
  `references/agent-protocol.md`
- Mode matrix (enhanced vs plain; build vs review): `.claude/skills/diagnostic-html-visualizer/references/family-routing.md`
- Shared format rules (language, Data Truth Mandate, artifact minimums): `.claude/skills/diagnostic-html-visualizer/references/format-rules.md`
- Script (the single implementation of the 9 checks; do not modify): `.claude/skills/industrial-enhanced-html-reviewer/scripts/html_reviewer.py`

## Inputs / Outputs

| Required | Path | Description |
|----------|------|-------------|
| P0 | `<RUN_DIR>/enhancement/enhanced_knowledge.json` | Ground-truth data source |
| P0 | `<RUN_DIR>/enhancement/enhanced-analysis.html` | Page under review |
| P1 | `<RUN_DIR>/enhancement/html_selfcheck.json` | Build-time self-check (optional input) |

Output: `<RUN_DIR>/enhancement/enhancement_html_review.json`

```json
{
  "verdict": "pass",
  "overall_score": 92,
  "blocking_issues": [],
  "warnings": ["..."],
  "checks": [
    {"name": "hero_clarity", "status": "pass", "evidence": "..."}
  ],
  "reviewed_at": "<ISO timestamp>",
  "html_path": "<absolute path>",
  "knowledge_path": "<absolute path>",
  "html_size_bytes": 38021
}
```

`blocking_issues` MUST be an array of strings (never objects).

## Review Dimensions (9 checks, implemented in the script)

1. **hero_clarity** — status badge + display title + key findings + operability summary
2. **evidence_layer_1_statistical** — all 5 chart containers present (5/5 pass, 3-4 warn, <3 fail)
3. **evidence_layer_2_physics** — chart reading annotations (`cr-label`) ≥ 5 (one per chart)
4. **chart_initialization** — 3 CDN sources configured (jsdelivr + unpkg + cdnjs)
5. **three_d_fidelity** — runtime self-check variables + static fallback table present
6. **data_governance** — governance card ("数据溯源" / `gov-card`) + SHA256 fingerprint
7. **degraded_mode_fallback** — static fallback section with table rows
8. **size_requirement** — HTML ≥ 5120 bytes
9. **data_fidelity** — HTML references the knowledge `run_id` / edge labels

## Decision Rule

- `pass`: score ≥ 75, no blocking issues
- `warn`: score ≥ 50 but < 75 (fix the warnings, re-run, re-review)
- `fail`: blocking issues exist or score < 50 (rebuild)

## Usage

```bash
uv run --project .claude/shared/scripts python .claude/skills/industrial-enhanced-html-reviewer/scripts/html_reviewer.py \
  --knowledge <enhanced_knowledge.json> \
  --html <enhanced-analysis.html> \
  --output <DIR>/enhancement_html_review.json
```

## Quality Gate

```bash
node .claude/skills/industrial-enhanced-html-reviewer/scripts/quality_gate.mjs --run-dir <RUN_DIR>
# Runs html_reviewer.py on enhancement/enhanced_knowledge.json + enhanced-analysis.html and maps its verdict:
# exit 0 = verdict pass  |  exit 3 = verdict warn or fail (gate-fail: fix warnings/blockers and re-review)
# exit 2 = required input artifact absent (build has not run)  |  exit 1 = hard error (script/python failure)
# --no-run   consume an existing enhancement_html_review.json instead of re-running the script
# --allow-warn  treat verdict warn as exit 0 (informational use only)
# Tests: python .claude/skills/industrial-enhanced-html-reviewer/tests/run_tests.py
```
