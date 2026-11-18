# Round 47 — Fresh Three-Seat AEI Review Panel (Real-Referee Simulation)

Date: 2026-09-27. Fifth `$loop` iteration. Three fresh blind seats playing a real AEI review panel
(methodology / domain / presentation), per the user's acceptance standard "真实符合审稿".

## Panel verdicts

| Seat | Recommendation | Must-fix count |
|---|---|---|
| R1 methodology/statistics | **Minor Revision** | 2 |
| R2 domain/industrial informatics | **Major Revision** | 3 |
| R3 presentation/quality | **Minor Revision** | 2 |

## Adjudication (verify-then-fix discipline; every accepted item verified against sources)

### Verified real → fixed (7 items)

1. **Stray closing parenthesis** (§2.2, "IDV16--20).") — introduced by the round46 AgentRCA
   sentence split (both R1 and R3 caught it). Removed.
2. **XMV_14 → XMV_10 (§8.3)** — verified against `baseline_pca_rca.json`:
   `tep_d14` top-3 = [XMEAS_21, XMEAS_2, XMV_1]; the paper's own §7.5 defines the reactor
   cooling valve as XMV_10 and the standard catalog has 12 XMVs. The prose conflated fault number
   14 with a valve number (Table A1's row was already correct). One-token fix.
3. **Data-availability timestamp label** — "the batch's first run directory carries 09:28 UTC"
   was wrong: the second batch's first directory is `202609181728292` (17:28), and prefixes share
   the UTC clock with the JSON timestamps (retest_selection 22:46:46Z ↔ dir 224700, 14 s apart).
   Fixed to 17:28 UTC; the exclusion logic (freeze 01:02 UTC < 17:28 UTC) is unchanged and now
   internally consistent.
4. **Abstract risk–coverage grounding** — "an explicit operating point on the risk–coverage
   curve" → "…on the **keyword instrument's** risk–coverage curve"; §8.3's curve sentence gained
   "and measured on this instrument alone". R1's point: on the measured instrument both arms sit
   at 9/9 coverage, so the selective-prediction framing must be scoped to the measured
   instrument; the pipeline-internal resolved-vs-forced contrast is the valid curve.
5. **Table 8 ceiling explanation scoped** — the caption's ceiling story now covers only the two
   candidate-list 6/6 rows; the candidate-free FE strict arm's 6/6 is stated to be consistent
   with literature recall of the documented TEP catalog (the section's own recall caveat).
6. **Table 1 caption** now notes AgentRCA is a contemporaneous non-peer-reviewed preprint (R2).
7. **Venkatasubramanian 2019 lineage reference added** (R2): "The promise of artificial
   intelligence in chemical engineering: Is it here, finally?", AIChE J. 65(2):466–478 — DOI
   verified via Crossref (10.1002/aic.16489; the first-guessed DOI 10.1002/aic.12468 resolved to
   a 2010 paper and was discarded — the round42 verify-before-cite discipline again). Cited at
   §2.1's sample-level-limitation sentence.

### Verified real → fixed (presentation should-fixes, 7 items)

§9's lone numbered subsection folded to a run-in paragraph; "blind" terminology unified
(mechanism-blind for SKAB cavitation in Table 7/Table A2/§9; status-blindness stays with the
control brief); "division of labour" ×2 → "labor" (the BrE sweep's escapees); six table captions
unified to sentence case; Table 6's precision interval marked descriptive (conditions on a
pipeline outcome); §7.2 rubric arithmetic spelled out (1155/12 = 96.25); pre-registrations
declared repository-internal and commit-pinned.

### Adjudicated as research-side decisions (NOT text fixes; the standing residue)

R2's three must-fixes — execute the neutralized-identifier re-run (~16 h), re-ground batch-93 by
recorded fault injection, run blinded expert adjudication — are experiments, not text edits. They
are the pre-registered contract every round has carried; R1 (the methodology referee) examined
the same disclosures and judged the paper Minor precisely because the reading-structure
qualifiers make the absences non-misleading. The genuine referee disagreement (Minor vs Major)
turns on exactly this decision, which belongs to the author. Also declined: Fig. 3's 5.6–6.0 pt
smallest text (judge-passed readable twice; documented), caveat-repetition compression
(~2–3 pages, author-voice decision).

## Gates after fixes

main.pdf 60 pages: ERR=0 / OVERFULL=0 / FLOAT=0 / REF=0 / UNDEF=0 / bibtex skipping=0; abstract
240 rendered words ≤250; keywords on p1 (one regression during editing — abstract +2 words pushed
them off — fixed by −4-word trim). Preprint 74 pages, 0 errors/floats, 2 sub-5pt invisible
overfulls.

## Loop disposition

Round47 had verified must-fixes → all fixed and gate-verified → arm R48 (final verification:
fresh seat checks the 16 R47 edits + regression scan; zero must-fix → stop; hard cap R48).

## R48 — Final verification: VERDICT PASS, zero must-fix → LOOP TERMINATED

All 16 edits verified landed and coherent: paren removed; XMV_10 correction consistent with §7.5
and Table A2 (the seat also corrected my checklist slip — the IDV14 top-3 row lives in Table A2,
not A1; the paper itself was already coherent); 17:28 UTC timestamp corroborated by
metrics.json `generated_at: 2026-09-18T01:02:34.546Z`; abstract 246 words with the keyword-
instrument qualifier and keywords on p1; §8.3 instrument-scoped curve sentence; Table 8 scoped
ceiling explanation with no stale phrasing; Table 1 preprint note; venkatasubramanian2019promise
rendered in main.bbl and cited at §2.1; labour=0; mechanism-blind unified (blind set=0,
brief-blind=0); §9 run-in paragraph; six sentence-case captions; descriptive-interval clause,
1155/12=96.25 arithmetic, repo-internal pre-registration sentence. Regression: main 60 pages all
gates zero, preprint 74 pages (2 sub-5pt invisible overfulls), zero unresolved "??", tables 1–9
and figures 1–10 first-cited ascending, headline numbers match metrics.json.

**The loop terminates here.** What remains outside the text loop is unchanged: the author's
decision on the pre-registered experiments (the neutralized-identifier re-run is the one that
separates Minor from Major verdicts), and the author-only submission metadata.
