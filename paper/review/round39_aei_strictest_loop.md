# Round 39 — AEI Strictest-Bar Loop, Iteration 1 (2026-09-26)

Trigger: user-launched `$loop` — check AEI journal requirements, review content + figures,
revise, recompile, loop until the paper truly meets AEI's strictest submission bar.
Method: fresh AEI Guide-for-Authors fetch (ScienceDirect, 2026-09-26) + clean rebuild health gate
+ three independent seats (compliance / content / visual), then a full fix pass and re-verification.

## Baseline verified before changes

- Clean rebuild from scratch (aux/bbl/blg/log deleted, fresh bibtex): **0 errors, 0 Overfull,
  0 Float-too-large, 0 citation/reference warnings, 0 undefined refs, bibtex 0 skipping,
  59 pages** — identical byte size to the round-38 build. Build health confirmed.
- Mechanical audit: abstract 219 words (≤250 ✓), 6 keywords ✓, highlights 5×≤85 chars ✓,
  all five Elsevier declarations present before the reference list ✓.
- Note (tooling): `grep` silently returns nothing on main.log and pdftotext output on this
  machine (binary detection from high-byte/form-feed content) — always use `grep -a`.

## Seat A — GfA compliance audit: NON-COMPLIANT, 4 must-fix (all fixed)

| # | Finding | Fix |
|---|---------|-----|
| A1 | 3 arXiv preprints rendered without the word "preprint" (`constantinides2025failuresensoriq`, `wei2026agentrca`, `wu2023autogen` were `@misc`+eprint while 5 sibling entries use `@article`+`journal={arXiv preprint arXiv:…}`) | Converted all three to the sibling style; bbl now renders 8/8 "arXiv preprint" |
| A2 | 14 BrE tokens in AmE text: catalogue ×6, computerised ×2, grey ×6 (captions) | catalogue→catalog, computerised→computerized, grey→gray (targeted caption edits; `iddgrey` color identifier untouched; figure-internal text has no rendered "grey" — only JS comments/variable names) |
| A3 | `\ref{sec:overall}` inside the abstract breaks standalone extraction | Section pointer removed from the abstract sentence |
| A4 | Generative-AI declaration did not name the specific tool ("GLM-based agent CLI … and editor-level writing assistants") | Rewritten: "ZCode, an agentic command-line coding assistant powered by the GLM model family (Z.ai)"; the unnamable "editor-level writing assistants" dropped |

Advisories accepted (no action): PNGs carry no pHYs dpi tag (765–928 dpi effective at textwidth,
above the 500-dpi combination-art bar); els-cas "encouraged" only — elsarticle qualifies.

## Seat B — fresh content review: Major Revision, 4 majors + 14 minors

Number audit: **24/25 exact matches** against metrics.json/gradings (all Wilson CIs recomputed
by the seat); the single mismatch was a rounding slip (fixed, see B-minor-1).

- **M1 (identifier-channel prominence)**: abstract/conclusion headline numbers now carry the
  qualifier at the claim itself — abstract: "a provisional upper-bound reading under a disclosed
  identifier channel" attached to 4/9; conclusion: same qualifier attached to Top-1. (Executing the
  pre-registered neutralized-identifier re-run remains an author decision, ~16 h; the
  conditional-claims structure was accepted by rounds 33/34/38 — not re-litigated.)
- **M2 abstract precision**: (a) top-k claim now says "at the keyword instrument's family level";
  (b) zero-false-alarm claim now carries "(one of the three blind)"; (c) the 9/9-vs-4/9 metric
  mixing fixed — now "commits a correct mechanism in all nine fault scenarios where the pipeline
  resolves four and caps five—family-level scoring rates both arms 9/9"; (d) determinism claim now
  says "exactly with timestamps excluded"; (e) internal \ref removed. Abstract 219→240 words (≤250).
- **M3 (Fig 3 truncated mid-Step-9)** — CONFIRMED, see Seat C.
- **M4 (disclosure density, condense ~25%)**: NOT executed this round — deliberate decision.
  Disclosure prominence was litigated across rounds 19–22 with seats demanding MORE surface
  disclosure; wholesale condensation risks regressing accepted framing. Deferred to a dedicated
  pass with a fresh editorial seat; individual double-claims fixed where concrete.
- Minors fixed: 96.2→96.3 (1155/12=96.25); contribution-4 parentheticals split (identity-strict
  3/8 moved to the Top-1 claim, one-of-three-blind stays with false alarms); Table 1 caption no
  longer first-cites Table 9 (points to Section 6 instead); §6.5 double-claim stabilized
  (resolution framing); Table A2 caption gains the row-wise contamination caveat; baseline-arm
  recording order stated (released reply records 2026-09-18T06:42 postdate the 2026-09-17
  pipeline batch; arms read only blind briefs); judge supersession sentence added (IDV11 entry =
  canonical re-execution's record); Table 3 caption labels the Controls row (SKAB/TEP/IndPenSim);
  Fig 7 vs text σ mismatch resolved **from artifacts** (causal_evidence_map.json: XMV_3 +18.5σ,
  XMEAS_1 +18.7σ — figure was right, text now says +18.5/+18.7σ in Table 3 and §6.4); IDV3
  round-1 judge record pointer added (`05_review/judge_feedback_round1.json`, verified to exist);
  chen2023 software-RCA scoping softened ("which we do not survey here").
- Minors verified-not-fixed (no action needed): AgentRCA 40.0/61.5, Vieira 15.3pp, FE alias
  transcription — all verified against primary sources in rounds 21/22 with archived records
  (`paper/review/round2*`); bib key cosmetics (yoon2001/khan2024) — keys don't render.

## Seat C — visual gate (10 figure pages): 3 FAIL → all repaired, 6/6 PASS on re-check

- Fig 1 (p-09) FAIL: "packages ship JSON Schemas…" card overhung its panel by 20 svg-px
  (s4 x=1150 w=330 → right 1480 vs panel right 1460). Fixed in `fig_architecture.drawio`
  (s1–s4 → w=320 at x=70/420/770/1120, gaps preserved, s4 right edge 1440), re-rendered via
  `drawio_render.py --all`. Re-check: card fully inside, ~12px margin.
- Fig 3 (p-24) FAIL: bottom of Step-9 row sliced (viewport 1500×2050 too short; trim left 6570
  of content 6607). Fixed: re-export at 1500×2400 → 4416×6607, Step-9 row complete incl. bottom
  border; LaTeX height cap 0.72→0.75\textheight to keep in-figure text ≥6pt at print.
- Fig 6 (p-31) FAIL: quantization callout box (bottom y=130) struck the "flow-plateau window ·
  rows 621–927" label (glyph top ≈129) and overpainted "927" (paint order). Fixed: box shrunk to
  3 lines (h=100, w=560) with clean wording ("Pressure quantized at 0.327 bar: ≈10× the expected
  head change, so head direction is masked (text only)"), 19px+ clearance.
- Fig 2 (p-11): "(Table 3)" removed from the raster (fig_pipeline.drawio note cell; caption now
  carries "mechanical predicates are listed in Table~\ref{tab:checkpoints}"); amber repair-path
  annotations darkened (#A35C17→#7A4210), bolded, 23/22→26/25 px.
- Fig 4 (p-27): KPI sublabels 25→28px; x-domain 60→55 (batch-1 marker 65 off the frame edge);
  axis line redrawn at the new left edge; controls legend swatch now visible (#e8ecf0/#8f9aa5).
- Fig 10 (p-42): panel fonts 20→26, 24→28, 25→28px (all ≥6pt print after reflow; re-export
  viewport 1500×1410; bottom footnote verified complete).
- Re-verification: 6/6 pages PASS, 0 must-fix (pixel-evidenced; pagepng_r39b/).

## Post-fix build gate (current authoritative state)

- main.pdf: **60 pages, 0 errors, 0 Overfull, 0 Float-too-large, 0 ref/citation warnings,
  0 undefined, bibtex 0 skipping**; abstract 240 words; bbl renders 8/8 "arXiv preprint";
  text-layer checks 9/9 (qualifiers, timestamps-excluded, 96.3, +18.5/+18.7 ×2, no BrE leftovers,
  no broken refs).
- main_preprint.pdf regenerated (12pt): 75 pages, 0 errors/warnings, but **3 pre-existing float
  overhangs at 12pt** (Table 2 +122.8pt, fig_casestudy +21.3pt, Table A2 +182.8pt — structural to
  the 12pt variant, not introduced this round; the 10pt submission build is clean). TO DO at
  submission prep: per-float `\baselinestretch`/size fix in the variant.

## Open items for next iterations

1. Iteration 2: fresh-taste re-review of the revised text (regression check on the abstract
   rewrite + seats that have not yet seen round-39 text). Stopping rule: two consecutive
   iterations with zero new must-fix findings → goal-state declared with evidence.
2. M4 condensation pass (dedicated editorial seat) — optional, judgment reserved.
3. Preprint-variant float overhangs (submission-prep task).
4. Standing pre-registered experiments unchanged (neutral-ID rerun, k≥3 repeats, expert blind
   test) — author decisions, not text defects.
