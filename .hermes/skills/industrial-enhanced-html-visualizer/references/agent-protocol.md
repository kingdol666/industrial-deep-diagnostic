# Enhanced HTML Visualizer Agent Protocol

You are the builder agent for `industrial-enhanced-html-visualizer`. Your job is to read `enhanced_knowledge.json` and produce a standalone `enhanced-analysis.html` with ECharts interactive charts.

## Required Reading Order

1. `enhanced_knowledge.json` — sole data source
2. This protocol

## Execution Steps

### Step 1: Load Knowledge

Read `enhanced_knowledge.json`. Extract:
- `enhancement_status` — for Hero status badge color/label
- `relationship_graph.nodes[]` — for network graph nodes
- `relationship_graph.edges[]` — for all 5 charts (network edges, heatmap rows, radar data, operability matrix, physics cards)
- `tradeoff_matrix[]` — for radar chart target indicators
- `mechanism_chains[]` — for key findings bullets
- `operability_summary` — for Hero lede text
- `open_questions[]` — for additional key findings
- `provenance` — for data governance card

### Step 2: Build Chart Data

Transform knowledge into 5 chart data structures:

1. **Network graph**: nodes filtered (exclude timestamp/product_code), edges filtered to matching nodes. Node color = operability enum color. Edge color = relationship type. Edge width = |strength| × 3.

2. **Heatmap**: rows = one per edge. Columns = global_r, detrended_r, lag_aligned_r. Color gradient: red (-1) → white (0) → green (+1).

3. **Radar**: indicators from tradeoff_matrix effects keys. One radar per parameter (max 6 displayed). Extract r value from effect strings.

4. **Operability matrix**: x_axis = target nodes, y_axis = predictor nodes. Cell = scatter point with detrended_r magnitude.

5. **Physics cards**: one card per edge with 5-dim traffic lights (direction/form/lag/magnitude/state).

### Step 3: Generate HTML

Run `scripts/html_builder.py --knowledge <PATH> --output <PATH>`.

The script:
- Builds inline JSON data blocks for all 5 chart types
- Generates `<style>` block with CSS variables (matching diagnostic-html-visualizer design system)
- Generates Hero section with status badge, key findings, operability summary
- Generates 5 chart panels in sectioned layout
- Generates data governance card from provenance
- Generates static fallback table (hidden by default, shown when ECharts unavailable)
- Embeds ECharts multi-source loader (jsdelivr → unpkg → cdnjs)
- Embeds runtime self-check script
- Writes `html_selfcheck.json`

### Step 4: Verify

Check:
- HTML ≥ 5120 bytes
- All 5 chart containers present
- 3 CDN sources present
- Runtime self-check variables present
- Static fallback table present
- Data governance card with SHA256 present

## Data Binding Rules

- All node/edge/chart data is embedded as inline JSON (`var NET_DATA = {...}`)
- Operability colors: LEVER_IDENTIFIED=#2d7d4f, CONFOUNDED=#8a6d3b, ENDOGENOUS_RESPONSE=#c2673a, NOT_IDENTIFIABLE=#c4433b
- Relationship colors: supports=#2d7d4f, contradicts=#c4433b, correlates=#1e3a54, causes=#c2673a
- Physics status colors: MATCH=#2d7d4f, PLAUSIBLE=#1e3a54, UNTESTED=#888888, REVERSES=#c4433b, IMPLAUSIBLE=#c2673a

## Fallback Rules

1. ECharts loads from any of 3 CDN sources → interactive charts
2. All 3 CDN sources fail → static table shown, degraded notice displayed
3. Individual chart failure (e.g. radar with no data) → empty container with caption
4. Missing provenance → governance card shows "unknown"
