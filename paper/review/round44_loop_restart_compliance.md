# Round 44 — Loop Restart Iteration 1: GfA Re-audit + Round43 Surgery Regression

Date: 2026-09-27. User re-invoked `$loop` (AEI-strictest). This round: iteration 1 of the new loop.
Two fresh blind seats in parallel + one closure gap found and fixed in the submission package.

## Closure gap found directly (not by a seat)

Fig. 1 / Fig. 2 captions promise the draw.io sources and export script "released with the paper",
but `supplementary_artifact_layer.zip` (built round41) contained only run_dirs + results layer +
scripts — no figure sources. Fixed: `build_supplementary.py` gained a `FIGURE_SOURCES` section
(16 files: 2 drawio, 10 figure HTML, aei_template.css, drawio_render.py, render_all.sh,
trim_white.py → `figure_sources/`); zip rebuilt (805 files, 27.0 MB); SUPPLEMENTARY_MANIFEST.md
inventory updated. Regression seat verified zip ↔ manifest match and byte-identity of shipped
sources vs. current re-rendered sources.

## Seat A — GfA compliance (fresh, re-fetched the official Guide for Authors today)

VERDICT FAIL → 1 must-fix, applied:
- MF-A1: The generative-AI declaration section title used the retired Elsevier template wording
  "…in the writing process". Current AEI GfA (2025 rewording) requires **"Declaration of
  generative AI and AI-assisted technologies in the manuscript preparation process"**. Title
  changed at main.tex:679 (content already compliant: names ZCode / GLM / Z.ai + the
  reviewed-and-responsibility sentence; placement before references correct).

Should-fixes: tables not first-cited in numeric order (= Seat B's MF-B2/B3, fixed, see below);
casestudy/perfault PNGs ≈488 dpi if re-placed at 190 mm full journal width — current compilation
places them at 765/869 ppi and the current GfA lists 300 dpi (photos) / 1000 dpi (pure bitmapped
line art) with no combination category → documented, not actioned (all 10 figures 761–1054 dpi
placed).

Seat A verified compliant: abstract 248 words standalone (2 words of headroom — do not edit the
abstract), 6 keywords, highlights 5×74–81 chars, all five declarations ordered before references,
0 BrE hits, 76 references (72 DOI, 4 legitimately without), arXiv entries render as preprints
with DOIs, cover letter has no stray placeholders, manifest ↔ zip exact match. GfA changes noted:
AI declaration "upon submission"; AI-manipulated research images prohibited (n/a — drawn figures
with released sources).

## Seat B — Round43 surgery regression (fresh)

VERDICT FAIL → 3 must-fixes, all applied:
- MF-B1: Fig. 3 caption said "the dashed repair edge was not triggered" — the round43 caption
  trim had dropped the original's "dashed **in Fig. 2**" qualifier, leaving the clause pointing at
  a non-existent element of Fig. 3 itself. Restored: "the bounded repair edge (dashed in
  Fig.~\ref{fig:pipeline}) was not triggered".
- MF-B2: the round42 Related-Work pointer made Table 3 first-cited before Table 2. Fix: the
  parenthetical now reads "…inter-agent misalignment → checkpoints CP-5/6" (the C4 misread stays
  defused by "contract C4, Section~\ref{sec:framework}"; the next sentence already promises
  Section~\ref{sec:arch}'s checkpoint description).
- MF-B3 (pre-existing): Table 9 first-cited at line 308, before Tables 5–8. Fix: that sentence now
  points to Section~\ref{sec:discussion} (which already cites Table 9). Post-fix rendered
  first-mention order: 1(p5), 2(p10), 3(p10), 4(p17), 5(p19), 6(p22), 7(p26), 8(p36), 9(p46) —
  strictly ordered.

Should-fixes, both applied:
- Fig. 2 caption gained "check marks record the gates the reported runs passed" (explains why
  CP-6/8/9 carry ✓ while CP-1…CP-5, CP-7 do not).
- §4.6 now states the review-repair bound explicitly: "the review-repair budget (≤2 rounds)" —
  the figure edge label's "≤2 rounds" is now sourced in the body.

Seat B's orphan audit: every fact removed from the five shortened captions survives in body/
tables/figure content (verified item by item); Fig. 6's "two lowest quantization levels" verified
against the released data_analysis_conclusion.json; the three headline statistics re-verified
against metrics.json/rubric.json.

## Gates after fixes

main.pdf 60 pages: ERR=0 / OVERFULL=0 / FLOAT=0 / REF=0 / UNDEF=0 / bibtex skipping=0;
keywords p1. main_preprint.pdf 74 pages: ERR=0 / FLOAT=0 / REF=0 / skipping=0.

## Loop disposition

Round44 had must-fixes → all fixed and verified → arm R45 (final verification round: fresh seat
checks the six round44 edits + regression scan; zero must-fix → STOP). Hard cap: R46.
