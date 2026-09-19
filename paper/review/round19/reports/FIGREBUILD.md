# Figure Rebuild Report — Round 19 (R3 Major 1)

Root cause (reviewer-measured, confirmed): the pipeline assumed a 5.4 in text
block; the real elsarticle-preprint 10pt `\textwidth` is **345 pt = 4.77 in**,
so every placed figure shrank ~13% further, pushing 20–24 px CSS text to
4.6–5.5 pt printed — below Elsevier's 6 pt floor.

Fix: keep the 1500 px canvas, raise every font to ≥29 px
(29 px × 343.44 pt / 1500 px = **6.64 pt** effective), then re-render at
device-scale-factor 3 (≈600 dpi at placed width). LaTeX side: two figures whose
grown captions exceeded the text height get `height=0.7–0.8\textheight,
keepaspectratio` (width cost ≤5%, printed fonts stay >6 pt).

| Figure | Canvas | Min font (css px → pt) | Content changes | Status |
|---|---|---|---|---|
| fig_architecture | 1500 w (h auto) | 29 → 6.64 pt | none | rebuilt; LaTeX height cap 0.8 |
| fig_pipeline | 1500 w | 29 → 6.64 pt | none | rebuilt; LaTeX height cap 0.7 (12pt preprint fit) |
| fig_trace | **1050 → 1500 w** (h auto) | 29 → 6.64 pt | none (run id 202609171639066 confirmed correct) | rebuilt wider; 4500×4980 |
| fig_casestudy | 1500 w | 29 → 6.64 pt | none | rebuilt |
| fig_benchmark | 1160 w | ≥6.5 pt | none | rebuilt by agent |
| fig_calibration | 1160 w | ≥6.5 pt | none | rebuilt by agent |
| fig_tep_perfault | 1160 w | ≥6.5 pt | in-figure "(Chiang et al., 2001)" removed (caption cites) | rebuilt by agent |
| fig_forest | 1393 w | template ≥6.5 pt | none | re-rendered |
| fig_suite_matrix | 1500 w | 29 → 6.64 pt (incl. footnote block) | none | rebuilt; footnote block now legible |
| fig_consistency | 1500 w | 29 → 6.64 pt (incl. status table) | none | rebuilt |

Verification: every rebuilt PNG visually inspected at working resolution (no
clipping/overlap/reflow); PNG dimensions recorded; R3's disputed run-id finding
evidenced via `../_figtrace_top.png`.
