# Round 22 — P2 Presentation Verification Report (blind)

Reviewer: P2 (presentation), Advanced Engineering Informatics — independent verification pass after MINOR revision.
Artifacts inspected: `paper/main.pdf` via freshly rendered `paper/pagepng/p-01..59.png` (110 dpi), source `paper/main.tex`, figure sources `paper/figures-html/`. Prior-round reports NOT read (blindness rule respected). Verification date: 2026-09-25.

---

## Condition 1 — Abstract self-contained: **PARTIAL FAIL (one string remains)**

Verified from p-01.png at 2.2x–3.5x zoom, cross-checked against `main.tex` lines 53–55 (exact match).

- Word count: **219** (target ≤250) — PASS. Counted from the rendered page; programmatically confirmed on the source line (219 tokens after LaTeX stripping).
- Reading-structure strings:
  - "identity-strict" — absent. PASS
  - "branch-localized" — absent. PASS
  - "keyword instrument" — absent. PASS
  - "one of three blind" — absent. PASS
  - "byte-identically" — **STILL PRESENT. FAIL**
    Printed sentence (p.1, verified at 3.5x zoom): *"One seeded re-execution reproduced a scenario's verdict state and mechanism class; the deterministic suite arms reproduce 45 recorded run outputs **byte-identically**."*
- Pointer sentence on worst-case bounds: exactly one, ending "…explicit worst-case bounds under the disclosed identifier-recall channel (Section 7.2)…" — PASS.
- Parentheticals: 3 total — "(LLM)", "(IDD)", "(Section 7.2)". Target was "~2"; two are unavoidable acronym introductions and one is the permitted pointer. Acceptable under the "~" in my reading (noted, not failed).
- Keywords: exactly **6** ("Fault root-cause analysis / Reproducible benchmark / Large language models / Multi-agent systems / Competing hypotheses / Process ontology", `main.tex` lines 57–59) — PASS.
- Keyword block placement: p-01 ends with "ontology"; p-02 begins with "1. Introduction". No page-1→2 split — PASS.

## Condition 2 — Appendix table legibility: **PASS** (with notes)

- **No resizebox**: `main.tex` resizebox instances are at lines 104, 158, 184, 297, 340, 396, 448, 537, 610 — none inside Table A1 (`tab:perfault`, line ~675) or Table A2 (`tab:baselinedetail`, line ~709). PASS.
- **Type size**: measured cap heights at 110 dpi — body normalsize text = 11 px; A1 header/cells = 8 px; A2 header/cells = 8–9 px; both table captions = 8 px. 8 px ≈ 8 pt cap height at 110 dpi → both tables print at **footnotesize**, matching the caption size. PASS.
- **No mid-word hyphenation** (zoomed 2.6x on both table bodies): A1 wraps only at spaces/compound hyphens ("feed-ratio", "cooling-water", "heat-removal", "top-ranked"); A2 shows "SKAB inlet-valve / throttling" with "throttling" intact and "bubble formation and collapse" with "collapse" intact. No "throt-tling", no "col-lapse". Columns are ragged-right. PASS.
- **A1 caption**: single paragraph, definitional (~6 printed lines). No multi-paragraph analysis. PASS.
- **A2 caption**: single paragraph, but long (~13 printed lines) — mostly an abbreviations legend (Fh/Q/Fc/Fs/Fb, XMEAS/XMV channel names) plus provenance pointers. Literally satisfies "no multi-paragraph analysis"; noted as still dense.
- **Table 6 caption** (p.26): contains the required rounding clause verbatim — *"Wilson 95% intervals at z=1.96 (**bounds rounded half-up to one decimal**), matching the released scorer"* — and is a single paragraph. PASS. (Note: the caption still carries the "(upper-bound, identity-strict, branch-localized)" parenthetical; this was abstract-scoped in the promise, so not failed, but the machinery vocabulary remains on p.26.)

## Condition 3 — Two caption errors fixed: **PASS**

- **(a) Fig. 10 (p.42)**: printed caption reads *"…grey open diamonds controls (**the asterisk marks the mechanism-blind fault scenario SKAB cav\*, whose brief omits the mechanism label**)"*. Cross-checked against the drawing at 3.2x zoom: the asterisk is the superscript on the x-axis label "SKAB cav*", and its marker is a **sky filled square** (capped COMPETING_SET fault verdict) at 0.60 — not a grey open diamond control (controls sit at "ctrl SKAB" 0.86, "ctrl TEP" 0.90, "ctrl IPS" 0.93). Caption and drawing agree. PASS.
- **(b) Fig. 3 (p.24)**: printed caption reads *"Grey chips mark the script-dominated endpoints—Step 0/1 (main agent plus scripts) and Step 9 (a deterministic script)—blue chips the agent-executed stages, including hybrid Step 3 (data-processor plus scripts)"*. Cross-checked against the drawing at 4x zoom: chip column shows **grey** chips on Step 0/1 and Step 9 only; Steps 2, 3, 3.5, 4, 5a-5b, 6, 7, 8/8.5 are **blue**. Caption and drawing agree. PASS.

## Condition 4 — Spelling consistency: **PASS on the stated checks; leftover found in figure assets**

- `grep -c "quantised|quantisation|synchronised|itemised|synthesised|anonymised|defence|localised"` on `main.tex` → **0 matches**. PASS.
- Fig. 7 (p.35), IDV3 evidence cell at 4.5x zoom: "**localized** to the stripper steam loop (variance ×2.1–2.7)". PASS.
- Fig. 6 (p.31): in-panel annotation reads "**Quantization: 0.327 bar**" (bold header, z-spelling); legend reads "flow channel (**Volume Flow Rate RMS**, L/min · left axis)" with the space. PASS.
- **Leftover (new finding, same defect class)**: the rendered figures still contain "quantised" in two places:
  - Fig. 5 (p.30), IDV14 y-axis annotation: "quantised stepping, lag 1→5" (verified at 5x zoom). Source: `figures-html/fig_calibration.html`.
  - Fig. 7 (p.35), IDV14 evidence cell: "quantised stepping 633/800; lag tightens 1→5" (verified at 4.5x zoom). Source: `figures-html/fig_tep_perfault.html`.
  The stated condition scoped spelling to `main.tex` plus the two named figure strings (both fixed), so the condition as written passes — but the spelling sweep is incomplete across the figure sources, which are rendered assets shipped with the paper. These two strings need the same z-spelling fix and a figure re-render.

## Condition 5 — Figure re-render quality: **PASS**

- **Fig. 3 (p.24)**: re-rendered trace clean at 2.6x zoom on the densest rows (Step 4): no overflow, no clipped labels, chips/badges (CP-5 ✓) clear of the text cards.
- **Fig. 6 (p.31)**: annotation box "Quantization: 0.327 bar…" fits inside its frame; in-plot annotations ("flow-plateau window…", "current co-drop…", "vibration RMS…") are legible over the amber band; x-axis ticks 1…1145 all visible, "1145" not clipped; axis titles intact. No overlap artifacts introduced.
- Quick pass over p-09 (Fig. 1 architecture), p-11 (Fig. 2 pipeline flow), p-27 (Fig. 4 benchmark outcomes), p-30 (Fig. 5 per-scenario confidence), p-35 (Fig. 7 per-fault), p-36 (Fig. 8 forest), p-40 (Fig. 9 matrix), p-42 (Fig. 10 consistency): all render with no clipped labels, no overlapping elements, no overflow. PASS.

---

## Summary

| # | Condition | Verdict |
|---|-----------|---------|
| 1 | Abstract self-contained | **FAIL** — "byte-identically" still in abstract (all other sub-checks pass) |
| 2 | Appendix table legibility | PASS (A2 caption still long but single-paragraph) |
| 3 | Fig. 10 + Fig. 3 caption fixes | PASS |
| 4 | Spelling consistency | PASS as scoped; "quantised" leftover in Figs. 5 & 7 assets |
| 5 | Figure re-render quality | PASS |

## Remaining issues

1. **Abstract (p.1)**: "byte-identically" remains in the sentence "…the deterministic suite arms reproduce 45 recorded run outputs byte-identically." This is one of the five strings whose removal was the stated satisfaction condition. One-word fix (e.g., drop to "identically" or delete the clause).
2. **Figure assets (non-blocking for the stated conditions, but should be fixed before submission)**: "quantised" survives in `figures-html/fig_calibration.html` (Fig. 5, IDV14 row annotation) and `figures-html/fig_tep_perfault.html` (Fig. 7, IDV14 evidence cell), both visible in the rendered build on p.30 and p.35 — inconsistent with the American spelling enforced in `main.tex` and Fig. 6.

Minor notes (no action strictly required): abstract carries 3 parentheticals vs "~2" (two are acronym intros); Table 6 caption retains the "identity-strict, branch-localized" vocabulary outside the abstract; cosmetic gap after the underscore in "XMEAS_21"-type cells of Table A2 (font metric of the escaped underscore, consistent throughout).

VERDICT: REMAINING-ISSUES
