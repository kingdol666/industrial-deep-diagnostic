# Design Direction — Gate Record

## Process followed

Direction was selected **before** implementation, per the design-direction gate.

The three candidate directions were presented to the user as a choice, and the
user selected **A · Instrument Panel — density & order**.

The selection was made against the *existing* system rather than a blank page.
This application already ships a deliberate visual identity — Fraunces serif
display against IBM Plex Mono telemetry, warm-black graphite surfaces
(`#0c0d09`), a single safety-amber accent (`#e8a33d`), hairline borders, no
blur, no gradients, no emoji. That identity is the opposite of generic AI
output, so "beautification" here means **refinement inside the existing
system**, not replacement. Every change below is traceable to that reading.

### Candidate directions offered

| # | Direction | Character | Reference |
|---|-----------|-----------|-----------|
| **A** | **Instrument Panel** — density & order | Real industrial HMI: strict grid, tabular numerals in fixed columns, rules that carry structure, status encoded by form and not colour alone. Highest information density. | Braun instrumentation, Bloomberg Terminal |
| B | Editorial Steel — editorial design | Fraunces as a genuine editorial voice: generous margins, large display numerals, asymmetric layout, data as technical monograph. Most distinctive, lowest density. | Pentagram technical reports, MIT Press |
| C | Night Shift Console — atmosphere & depth | Layered surfaces with real elevation, warm vignette, phosphor glow on live telemetry, motion that reads as live instrumentation. Most cinematic, riskiest for readability. | F1 broadcast graphics, cinema HUD |

**Selected: A.** B was rejected because this is an operator tool where scan
speed beats editorial voice; C was rejected because glow-and-depth competes with
the data it is meant to serve.

## Form derivation — five questions

Answered before any CSS was written.

**1. Narrative role.** These are *readouts*, not pages. The operator arrives with
a question ("is the model healthy?", "which run failed?") and needs the answer
before the explanation. That dictates: numbers first, prose second.

**2. Viewing distance.** 1 m — a desktop monitor in a control room or a
laboratory. Not 10 cm (phone) and not 10 m (projection). Body text can stay at
12.5px, but nothing a user must read may fall below 4.5:1 contrast.

**3. Visual temperature.** Cool-headed and authoritative. This is a tool used
when something has already gone wrong; warmth would patronise and alarm would
mislead. Hence the amber accent stays the *only* saturated colour, and the
semantic palette (green / yellow / red / cyan) is reserved strictly for state.

**4. Capacity.** The previous layout fit ~12 file rows and ~8 run rows per
screen. Real projects here carry 40+ data files and 16+ diagnostic runs. The
layout had to at least double its visible row count before anything else
mattered. Measured result: 23 file rows and 16 run rows.

**5. Visual motif.** **The instrument readout**: a labelled column of values that
compares vertically. It comes from the content — every artefact in this system
(parameters, runs, findings, signals) is a row of measured values with a status.
The motif is what justifies tables over cards, tabular figures over
proportional, and hairlines over card borders.

> Form justification: the motif is derived from the domain (sensor telemetry and
> diagnostic verdicts *are* columnar readouts), not from a style label.

## What changed

### Foundations (`app/frontend/src/styles/global.css`)

- **Contrast defect fixed.** `--text3` was `#6c6a5e` on `#14150f` — **3.4:1**,
  below the WCAG AA 4.5:1 floor, yet it carried every field label and table
  caption in the product. Moved to `#8a8676` (**5.0:1**). `--text-dim` is now
  documented as decorative-only. Contrast for all four ink levels is recorded in
  the token block so the next editor can check it without recomputing.
- **A 4px base unit and a fixed type scale.** Spacing and font sizes were ad-hoc
  per component; they are now drawn from `--u`, `--row-h`, `--fs-*`.
- **An Instrument Panel layer** of shared primitives: `.ip-table` (dense
  readout with a `--cols` template so headers and rows cannot drift), `.ip-chip`
  (status = word + dot + rail, never colour alone), `.ip-stats` (readout strip),
  `.ip-panel`, `.ip-rule`, `.ip-empty`, `.ip-scroll`, `.ip-glyph`, `.ip-seg`.
- **`font-variant-numeric: tabular-nums`** on every numeric and monospace
  surface, so columns of figures align on the digit.

### Shell (`App.vue`)

- **Header compressed** from a ~100px billboard (kicker on its own line, 34px
  display title, two-line description) to a single 52px nameplate with the title
  inline and the description demoted to one muted line. Reclaims ~48px on every
  page.
- **Engine selector restructured.** All 14 engines were rendered as a flat
  two-column wall of near-identical chips — unscannable, and the active engine
  had no prominence. Now a single readout block shows the active engine with its
  state spelled out (`ready` / `offline`), and the full roster lives behind a
  disclosure with a status dot per row.
- **Bug fixed: the History tab had disappeared.** `visibleTabs` used
  `tabs.slice(0, 5)`; adding the Ontology tab pushed History off the end, so
  users lost access to run history entirely. All tabs now render, with the
  engine-specific runs tab appended.
- **Operator badge rebuilt** — it was still carrying light-theme fallbacks
  (`#fff`, `#16233a`, `#b42323`) that never resolved against the dark tokens.
  New `sidebar.engine` / `sidebar.ready` / `sidebar.offline` keys added.

### Data page (`DataBrowser.vue`)

Sparse card grid → **dense manifest**. Each 90px card became a 30px row with
fixed columns (glyph · name · type · size · actions), a readout strip above it
(folders / data files / total size / selected), and a tabular right-aligned size
column. Emoji file icons (📁📊📋) were replaced with drawn 16px SVG glyphs —
emoji are rendered by the OS font stack, so their weight, colour and optical size
are outside the design system's control, and they read as decoration rather than
as instrument legend. The toolbar lost its gradient, shadow and
`backdrop-filter`, and gained a monospaced breadcrumb.

### Diagnose page (`TaskList.vue`)

Sparse run cards → **dense instrument table**: 任务 / 状态 / 结论 / 评分 / 时间,
with sticky group rails for active vs. historical runs, tabular scores that
colour by band (≥90 green, ≥70 amber, else red), and status chips that carry both
a word and a dot. Visible rows per screen: 8 → 16.

## Preserved deliberately

- The Fraunces / IBM Plex pairing and the warm-graphite palette — the identity is
  not the problem.
- The ontology graph's VOWL-derived encoding (shape and colour per entity class,
  dashed = inferred, width = strength). It was designed against the notation
  standard and is correct; only its surrounding chrome was aligned.
- Every existing i18n key and language-switch behaviour.

## Known boundary

The backend generates human-readable finding sentences in Chinese
(`ontology.service.mjs`). Those are now rendered client-side from the finding's
stable `code`, so they follow the active locale; the server text is the fallback
for any code a given build does not yet know. A small number of Chinese strings
remain in the frontend as **runtime matchers** — they match Chinese progress text
emitted by the backend (`p.includes('等待用户')`) and would break if translated.

## Self-critique (verification pass after the build)

Screenshots of all six pages were taken before and after
(`.runtime/ui-before-*.png`, `.runtime/ui-final-*.png`) and the result was
reviewed against the direction rather than against taste.

**Verified improvements**

| Measure | Before | After |
|---|---|---|
| File rows visible on Data | ~12 cards | 23 rows |
| Run rows visible on Diagnose | 8 cards | 16 rows |
| Header height | ~100 px | 52 px |
| Field-label contrast | 3.4:1 (fails AA) | 5.0:1 (passes AA) |
| Navigation tabs | History missing | all present + engine tab |
| Console errors across 6 pages | 0 | 0 |

**Honest weaknesses in the current state**

1. **Two stacked panels on the Data page.** The "Data Files" header and the
   readout strip are separate bordered boxes; they could be one. Left as-is
   because merging them changes the panel component's contract used elsewhere.
2. **Sparse right side on the Data manifest.** The name column takes `2.4fr`
   while actions sit far right, leaving a wide gap on a 1720px viewport. A max
   width on the table would tighten it.
3. **Chat and Reports were not restructured.** They are content-heavy and were
   already using the shared tokens, so they inherited the header compression,
   contrast fix and scrollbars but kept their own layouts. This is deliberate —
   rewriting a 60 KB message stream for visual reasons alone would risk more than
   it returns — but it does mean those two pages are visually one notch behind
   the other four.
4. **`--text-dim` is still low contrast (2.4:1)** and remains in use for
   placeholder and disabled text where WCAG does not require AA. Worth an audit
   if any of those uses turn out to be load-bearing.
5. **The graph legend is the densest element on screen** and does not collapse on
   narrow viewports; below ~1150px the three-column ontology workspace already
   stacks, but the legend itself still wraps to three lines.

None of these are correctness defects; they are the next pass.
