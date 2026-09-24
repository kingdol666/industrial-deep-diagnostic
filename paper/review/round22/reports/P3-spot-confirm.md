# P3 Spot Confirmation Report (round22)

Reviewer: P3 (blind, scoped confirmation — no other round reports read)
Date: 2026-09-25
Build checked: current `paper/main.pdf` (59 pages, rendered at 110 dpi to `paper/pagepng/p-01.png … p-59.png`), `paper/main.tex`, `paper/refs.bib`.
Method: direct zoomed reading of the printed page PNGs (crops in `paper/review/round22/tmp/`), plus source-level cross-checks in `main.tex` / `refs.bib` and a pdftotext sweep of all 59 pages.

## Fact 1 — Abstract sentence (p-01.png)

**PASS.** Zoomed crop of the abstract tail (`tmp/p01_abstract_tail.png`) shows the abstract's
second-to-last sentence reads exactly:

> "One seeded re-execution reproduced a scenario's verdict state and mechanism class; re-running the deterministic suite arms reproduces all 45 recorded run outputs exactly."

The term "byte-identically" does NOT appear anywhere in the abstract (verified both visually on
p-01.png and at source level: the `abstract` block in `main.tex` contains no occurrence of "byte" at
all). The full abstract was read line by line from the page image; no "byte-identically" present.

## Fact 2 — Figure spellings

**(a) Fig. 5, p-30.png — PASS.** Zoomed crop (`tmp/p30_idv14_row.png`) shows the TEP IDV14 row label:

> "TEP IDV14 valve stiction / quantized stepping, lag 1→5"

American spelling "quantized" confirmed; "lag 1→5" confirmed (arrow glyph renders correctly).

**(b) Fig. 7, p-35.png — PASS.** Zoomed crop (`tmp/p35_idv14_cell.png`) shows the IDV14
"IDD decisive evidence" cell text:

> "actuator limit cycle: variance ×189/116/222 with frozen means; quantized stepping 633/800; lag tightens 1→5"

The required phrase "quantized stepping 633/800" is present verbatim.

## Fact 3 — Bibliography title (refs.bib + printed references)

**PASS.**

- Source (`paper/refs.bib`, lines 239-246): `wei2026agentrca` title is exactly
  `Agentic Root Cause Analysis through Evidence-Grounded Reasoning` — no "AgentRCA:" prefix.
- Printed bibliography: References section starts on p-50; entry [39] on **p-54.png** (zoom crop
  `tmp/p54_ref39.png`) reads:

  > "[39] A. Wei, O. Fink, Agentic root cause analysis through evidence-grounded reasoning (2026). arXiv:2607.22385, doi:10.48550/arXiv.2607.22385."

  (Sentence-case rendering of the title is the bibliography style's downcasing; the decisive check —
  absence of the "AgentRCA:" prefix — holds in both source and print.)
- Citation resolution: a binary-safe pdftotext sweep of **all 59 pages** found **zero** occurrences
  of the literal "[?]" — no unresolved citations on the reference pages or anywhere else in the PDF.

## Summary

| # | Fact | Page/Evidence | Result |
|---|------|---------------|--------|
| 1 | Abstract second-to-last sentence, no "byte-identically" | p-01.png + main.tex abstract block | PASS |
| 2a | Fig. 5 IDV14 "quantized stepping, lag 1→5" (US spelling) | p-30.png | PASS |
| 2b | Fig. 7 IDV14 evidence "quantized stepping 633/800" | p-35.png | PASS |
| 3 | wei2026agentrca title without "AgentRCA:" prefix, in bib and print; no [?] | refs.bib L241, p-54.png, full-PDF sweep | PASS |

All three scoped facts confirmed on the current build.

VERDICT: CONFIRMED
