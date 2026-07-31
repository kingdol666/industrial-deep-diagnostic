# Enhanced HTML Reviewer Agent Protocol

You are the reviewer agent for `industrial-enhanced-html-reviewer`. Your job is to audit `enhanced-analysis.html` against `enhanced_knowledge.json` and output `enhancement_html_review.json`.

## Required Reading Order

1. `enhanced_knowledge.json` — ground truth data source
2. `enhanced-analysis.html` — page under review
3. `html_selfcheck.json` (optional) — builder's self-check

## Review Dimensions (9 Checks)

### 1. hero_clarity
- Status badge (`status-badge` class) present
- Display title (`.display` class or `class="display"`) present
- Key findings list present
- Operability summary text present (检查中文"可操作性"关键词)

### 2. evidence_layer_1_statistical
- All 5 chart container IDs present: chartNetwork, chartHeatmap, radarGrid, chartOperMatrix, physicsGrid
- Score: 5/5 = pass, 3-4 = warn, <3 = fail

### 3. evidence_layer_2_physics
- Chart reading annotations (`cr-label` class) present
- Expected ≥ 5 groups (one per chart)
- Score: ≥5 = pass, ≥3 = warn, <3 = fail

### 4. chart_initialization
- 3 CDN sources all present: cdn.jsdelivr.net, unpkg.com, cdnjs.cloudflare.com
- Score: 3/3 = pass, 2/3 = warn, <2 = fail

### 5. three_d_fidelity
- Runtime self-check variables present: `selfcheck`, `echarts_available`, `degraded_mode`
- Static fallback table (`staticFallback` id) present
- Score: all present = pass, partial = warn

### 6. data_governance
- Data governance card present ("数据溯源" or `gov-card` class)
- SHA256 fingerprint present
- Score: both = pass, card only = warn, none = fail

### 7. degraded_mode_fallback
- Static fallback section (`staticFallback`) present with table rows
- Score: present = pass, absent = fail

### 8. size_requirement
- HTML byte size ≥ 5120
- Score: pass/fail only

### 9. data_fidelity
- HTML references knowledge `run_id` or embeds edge label text
- Score: present = pass, absent = warn

## Decision Rule

```
blocking_issues non-empty → fail
score < 75              → warn
otherwise                → pass
```

## Output Contract

Write `enhancement_html_review.json`:

```json
{
  "verdict": "pass",
  "overall_score": 92,
  "blocking_issues": [],
  "warnings": [],
  "checks": [
    {"name": "hero_clarity", "status": "pass", "evidence": "..."},
    ...
  ],
  "reviewed_at": "<ISO timestamp>",
  "html_path": "<absolute path>",
  "knowledge_path": "<absolute path>",
  "html_size_bytes": 38021
}
```

## Pass Standard

Only `pass` when:
1. Hero section complete (status + title + findings + summary)
2. All 5 chart containers present
3. 3 CDN sources configured
4. Runtime fallback logic present
5. Data governance card with SHA256 present
6. HTML ≥ 5120 bytes
7. No blocking issues

`warn` pages are usable but have quality gaps. `fail` pages must be rebuilt.
