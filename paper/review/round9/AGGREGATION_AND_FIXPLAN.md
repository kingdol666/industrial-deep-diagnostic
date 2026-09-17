# Round 9 — Aggregated Verdicts & Fix Plan

## Verdicts: R13/R14/R15/R16 all MINOR. Must-fix lists shrank to one-liner precision fixes + float repack.

## Lead-verified facts for this round's fixes
1. **C1 ordering (R13#1)**: journal tep_d01: 09-15 04:06:33 (+0800) top1=False with old set → 04:09:48 top1=True with calibrated set → canonical executions 04:53–04:54 → commit 221d061 19:20 → released gradings 09-16. So the calibration PRECEDED the final executions (working tree), the commit followed. Paper's "executions precede calibration" must be inverted.
2. **revival_condition optional in diagnosis_schema.json** (R13#3): required = hypothesis_id/exclusion_type/specific_evidence; revival_condition is a property, not required → move to agent-applied clause.
3. **agent-protocol.md missing in 5/18 packages** (R14#1) — scope claim to the 8 dispatched sub-agent packages.
4. **VLM is a nested Agent() dispatch inside data-processor** (R14#2, skill wording) — "not a separate orchestrator dispatch".
5. **"the controls pass everywhere" → covered controls** (R16#1; baselines.json note).
6. Headline 6/9 needs pre-revision qualifier at abstract/contributions/table/conclusion (R13#2).
7. "four numbering schemes" enumerate once (R16#2): Step 0–9 / agent Phase 0–7 / reasoning segments R1–R8 / method stages 1–6.
8. Float pages to repack: p-69 (Table A1 27%), p-17 (Table 3 36%), p-39 (Fig 4 ~40%), p-41 (Fig 5 ~46%), p-70 (A2 50%), p-15 text stop 62% (R15).
9. Figures: Fig 6 caption colour key missing; Fig 4 green=IndPenSim undeclared; Fig 8 col-1 green→IDD blue (R15).
10. Cheap textual: "single-character tokens" → over-generic tokens (温度 is two-char; 阀 retained in skab set); 0.65/0.50 agent-documented-only clause; T3 det-precision/Top-1 non-independence note; T7 IDV1 R2 = (superseded run, canonical run); §3.2 fallback list name the four runs; VLM 3+3.3 alias footnote (R13/R14 SHOULD, cheap ones only).
11. Declined: DOI timing (external), 72pp shortening & §5 split & repair-counts-in-grading (production-stage edits, record in response letter), Fig3b marker reshapes, Fig 8 ramp recolour (caption already declares).

## Execution: Fixer-Tex-4 (main.tex items), Fixer-Fig-4 (make_figures: Fig8 col-1 blue; Fig4 caption-supporting check), then lead recompiles/renders, Round 10.
