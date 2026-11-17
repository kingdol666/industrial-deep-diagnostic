> Moved verbatim from `SKILL.md` §Style Direction & Visual Grammar. Read in full before Step 4 (page assembly).

## Style Direction & Visual Grammar

> **The builder agent must read this section before writing the page.** What is defined here is not "suggestions for reference" but the mandatory visual grammar of the page design. Fallback rules are in the next section; consult them when something breaks.

### Default: Light Minimal Narrative

**`references/report-template.html` is this Skill's sole style baseline.** What the page conveys is not a "technical system feel" but "clear diagnostic persuasiveness".

### Design principles

1. **Warm white background** — `#fafaf8` + `#f4f3f0` secondary background
2. **Single ink color throughout** — `#1e3a54` as the only accent color (ink blue)
3. **Serif headings + sans-serif body** — typographic hierarchy instead of decoration
4. **Generous whitespace + hairlines** — 1px dividers instead of card shadows
5. **Body ≤640px** — controls the reading rhythm
6. **Warm orange marks anomalies** — `#c2673a` used only for warnings/anomalies/physical mechanisms

### Color system (CSS variables — from report-template.html)

```
--bg: #fafaf8        primary background — warm white
--bg-alt: #f4f3f0    secondary background
--bg-card: #ffffff   card background
--hairline: rgba(0,0,0,0.06)  finest divider
--rule: rgba(0,0,0,0.10)      section divider
--t1: #111           body black
--t2: #4a4a4a        secondary text
--t3: #888           auxiliary text
--ink: #1e3a54       ink blue — primary accent
--warm: #c2673a      warm orange — anomalies
--green: #2d7d4f     deep green — pass
--red: #c4433b       dark red — excluded
--gold: #8a6d3b      dark gold — medium
```

### Typographic hierarchy

| Class | Font | Size | Purpose |
|------|------|------|------|
| `.display` | serif | 2.8rem/600/-0.025em | Hero conclusion |
| `h1` | serif | 1.9rem/600 | Main title |
| `h2` | serif | 1.45rem/600 | Section title |
| `.body-l` | sans | 1.08rem | Lead paragraph |
| `.body` | sans | 0.9rem | Body text |
| `.caption` | sans | 0.76rem | Figure caption |
| `.mono` | mono | 0.78rem | Statistical values |

### Hero area specification

- Top 36px × 3px hairline decoration (`--ink`)
- Serif display headline with `<em>` tags emphasizing keywords (`--warm` italic)
- Lede paragraph max-width: 640px
- Metadata row: flex-wrap + gap: 32px
- 4-cell key findings: `grid-template-columns: repeat(4, 1fr)`, 1px split border frame
- Bottom caption reading guide

### Section title specification

- Section numbers in monospace + `--t3` color + `letter-spacing: 0.1em`
- h2 headings in serif

### Evidence chain three-layer visual identity

- Each layer gets its own `.evidence-layer` container
- Layer titles carry circular numbered icons (Ⅰ/Ⅱ/Ⅲ) with color coding: statistics = ink / physics = warm orange / exclusion = dark red
- Evidence articles within a layer separated by hairline bottom borders

### Evidence strength score bar

```html
<!-- Statistical evidence strength: 85/100 -->
<div class="evidence-score">
  <div class="es-bar fill" style="width:85px"></div>
  <div class="es-bar empty" style="width:15px"></div>
  <span class="es-label">Statistical evidence strength: 85/100</span>
</div>
```

### Physical causal chain

```html
<div class="physics-chain">
  <div class="pc-step"><div class="pc-title">① Non-uniform roll surface μ</div><div class="pc-detail">Oligomer deposition<br>μ_s > μ_k</div></div>
  <div class="pc-arrow">→</div>
  <!-- ... more steps ... -->
</div>
```

### Statistical emphasis label

```html
<span class="stat-callout">ρ=+0.554, p=0.014</span>
<!-- Rendered as: monospace + ink color + light ink background -->
```

### 3D container specification

- Height: 500px (desktop) / 340px (tablet) / 260px (mobile)
- Background: `#ecebe6` (warm gray, matching the white background)
- Hover: `cursor: grab` / `cursor: grabbing`
- Overlay: top-left monospace + translucent white background
- Legend: bottom-right + 5 color swatches (preheat/stretch/quench/anomaly/flow direction)

### Chart container specification

- ECharts chart height: 380px (desktop) / 280px (tablet)
- Chart titles use `.chart-panel-header` + monospace numbering
- Three-line readings use `.chart-reading` (grid: 90px + 1fr)
- The three reading labels ("What is seen / What it means / Why it matters") in monospace + ink color
- Global ECharts palette: `['#1e3a54', '#2d7d4f', '#c2673a', '#c4433b', '#8a6d3b']`

### Statistics table specification

```css
.stat-table { width:100%; border-collapse:collapse; }
.stat-table thead th { text-transform:uppercase; letter-spacing:0.08em; color:var(--t3); border-bottom:1px solid var(--rule); }
.stat-table tbody td { border-bottom:1px solid var(--hairline); }
.stat-table .num { font-family:var(--mono); text-align:right; }
.stat-table .hi { color:var(--ink); font-weight:600; }
.stat-table .lo { color:var(--t3); }
```

### Mobile adaptation (mandatory)

```css
@media (max-width: 768px) {
  .page { padding: 0 18px; }
  .hero .display { font-size: 1.7rem; }
  .key-findings { grid-template-columns: repeat(2, 1fr); }
  .threejs-stage { height: 340px; }
  .chart-canvas { height: 280px; }
  .chart-reading { grid-template-columns: 1fr; }
  .section { margin: 56px 0; }
  .reading-nav { display: none; }
  .physics-chain { flex-wrap: wrap; }
}
@media (max-width: 480px) {
  .key-findings { grid-template-columns: 1fr; }
  .threejs-stage { height: 260px; }
  .hero-meta { gap: 18px; }
}
```

### Styles to avoid

| Forbidden | Why |
|------|------|
| Dark industrial style (080d14 deep background) | Incompatible with the current template, unless the user explicitly requests it |
| Piled-up card shadows | White background uses hairline dividers; hierarchy is not built on shadows |
| Colored top decoration lines | Use a single ink color; do not invent colors |
| Purple gradients / neon glow | AI slop carrying zero brand information |
| A screen full of jumping KPI numbers | Users come to understand a conclusion, not to monitor |
| Image-wall tiling | Every chart must have a three-line reading, no exceptions |