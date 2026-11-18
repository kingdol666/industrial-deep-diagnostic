# Round 41 — Editor-Screening Simulation + Citation Integrity + Submission Package (2026-09-26)

Loop restart after user's explicit request ("保证达成目标：真正发表到 AEI"). Iteration content
upgraded: text re-review alone had reached steady state (rounds 38-40), so this round pairs two
NEW review tastes with closing the concrete submission-materials gap.

## Seat 1 — AEI Editor-in-Chief screening simulation: **SendToReview**

Pass 1 (30-second skim): title accurate/no over-claim; highlights sell; figures professional
(Fig 3 "the best artifact in the paper"); abstract's contribution lands. Pass 2: the framing
survives, but the paper "invites" the one-line kill (9/9-vs-4/9) without the counterfactual in
the abstract; disclosure accumulation reads as defensiveness, especially in the Conclusion.
Top-3 fixes: ① reframe the ablation as an operating point (move the forced-commitment 6/9
counterfactual into abstract + contribution 2, risk–coverage language the paper already cites);
② execute a density audit (one canonical statement per caveat, back-references elsewhere);
③ put the industrial deployment hook on page 1.

### Applied
- **Abstract rewritten** (242 words ≤ 250; all six keywords verified back on page 1 after a
  258-word over-trim intermediate state): ablation now = operating-point framing with the
  6/9-with-three-wrong counterfactual; "disclosed identifier channel" replaced by its
  in-place definition "(run-directory labels can name the documented mechanism)"; the
  duplicated "names the measurement" clause consolidated into the ablation sentence.
- **Contribution 2** gains the computed cap cost clause (→ Section ablation).
- **Introduction** gains the deployment-regime hook (episodic high-consequence investigation;
  the engineer-facing deliverable; pointer to Section anatomy) — as a Section pointer, NOT a
  Fig 3 citation (an early Fig-3 cite would violate figure numbering order; editor's original
  suggestion adjusted for that).
- **Density audit executed** (7 consolidations): identifier restatement trimmed from
  contribution 4; §7.2 hit-semantics sentence and re-run mention gain Section pointers;
  baseline single-execution clause, §7.1 and §9 ablation parentheticals "(9/9 versus 4/9
  resolved)" removed (canonical statements kept at §7.3/abstract); Conclusion de-duplicated
  (three full restatements → back-references; the recall-possible reading terminology verified
  to exist at §9 before use).

### Applied with adjustments / rejected (documented)
- D3 (§7.2 one-blind-control shortening) REJECTED: the seat's own analysis marks the topic
  "already efficiently disclosed; no further consolidation possible without weakening" — and
  round-39's content seat explicitly required the explicit qualifier there.
- "Trustworthy"-paragraph mirror of the operating-point framing SKIPPED: it would have added
  new redundancy one paragraph away from §7.3's canonical Chow/conformal statement, working
  against the same round's density goal.

## Seat 2 — citation integrity audit (76 entries vs Crossref/arXiv/DataCite): **8 CORRECTIONS**

All 76 entries refer to real works; usage bidirectionally clean. Corrections (all verified
against primary sources; the two arXiv-ID fixes independently re-verified via arxiv.org/abs
before applying):
1. panickssery2024selfpref: arXiv id was **2404.13096** (an unrelated paper) → **2404.13076** (+DOI)
2. glm2024chatglm: arXiv id was **2406.18871** (an unrelated speech-LM paper) → **2406.12793** (+DOI)
3. cemri2025mast: 4th author "MacNeil, Emily" does not exist on arXiv 2503.13657 in any version
   → full verified 13-author list (Agrawal 4th)
4. zhou2019beatgan: pages 2775–2781 → **4433–4439** (IJCAI registered DOI)
5. alcala2009reconstruction: pages 1594 → **1593**–1600
6. sheridan1978human: "Verplanck" → **Verplank** (Crossref/DTIC record)
7. yoon2001statistical: "Seungjin" → **Seongkyu** (Crossref/Wiley)
8. constantinides2025failuresensoriq: "and others" hid the 6th author → **Kalagnanam, Jayant**
Plus optional: choudhury2008diagnosis gained its Springer book DOI. Both wrong-ID cases were
transpositions onto unrelated papers — precisely the desk-reject class; found only because the
audit fetched every id.

## Submission package (new: paper/submission/)

- `cover_letter.md` — full draft (scope fit, contribution, honesty-as-rigor, declarations;
  author personalizes salutation).
- `highlights.txt` — separate editable highlights file (5 bullets, ≤85 chars each).
- `SUPPLEMENTARY_MANIFEST.md` + `build_supplementary.py` + built
  **supplementary_artifact_layer.zip: 789 files, 27 MB** — 13 canonical run dirs (59 MB source;
  2026-09-18 interrupted batch excluded per statement), full results/benchmark layer,
  verify-fe.mjs (the §8.3 21-check gate the citation round required to be auditable),
  pipeline scripts + frozen benchmark_cases.json, FE transcription. Verified: key artifacts
  present, zero .mimosa residue. (build script's safe_path uses two confinement roots: repo +
  D:/codes/idd-run-archive junction target.)
- `SUBMISSION_README.md` — EM upload mapping + author-only items (ORCID, name confirmation,
  preprint declaration, declaration tool).

## Build state after round41

main.pdf: **60 pages, 0 errors / 0 Overfull / 0 Float-too-large / 0 ref-warnings / 0 undefined,
bibtex 0 skipping; abstract 242 words; keywords on page 1**; corrected arXiv ids verified in the
PDF text layer. main_preprint.pdf regenerated (75 pp, 0 errors; the 3 known 12pt float
overhangs remain — scheduled for round42).

## Loop state

Package: COMPLETE (author-only items documented). Round41 had must-fix findings (citations),
so the two-clean-rounds stopping rule restarts: round42 = fresh consistency seat over the
round41 text surgery + preprint float fixes; hard cap round44.
