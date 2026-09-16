# Supplementary: FaultExplainer per-fault outcomes used in this paper (transcription provenance)

Source: Khan, A.; Nahar, R.; Chen, H.; Constante-Flores, G.E.; Li, C.
*FaultExplainer: Leveraging Large Language Models for Interpretable Fault Detection and
Diagnosis.* arXiv:2412.14492 (2024); published in *Computers & Chemical Engineering* 199
(2025) 109152, DOI 10.1016/j.compchemeng.2025.109152.

## Evaluation protocol of the baseline (as stated by FE)

- Prompt regime 1 (root-causes-included): the prompt carries the documented root-cause list;
  the model outputs a **top-3 candidate list**; a hit is scored when the true fault **or an
  alias class** appears. Alias classes: IDV1/2/8, IDV3↔IDV9, IDV4↔IDV11↔IDV14,
  IDV5↔IDV12↔IDV15. (FE Table 1 marks F2 "alias 8" and F8 "alias 1,2"; IDV2 is not in
  this paper's TEP subset, so the two-member shorthand IDV1↔IDV8 covers all scored faults.)
- FE's PCA implementation does not detect IDV3, IDV4, IDV9, IDV15 → these four are excluded
  from FE's scoring.
- Prompt regime 2 (General-Reasoning Prompt — **no candidate list**, designed to simulate
  unseen faults): correct-or-**related** cause in the **top-3**, lenient grading → **8/11 for
  both models**.

## Per-fault outcomes used in this paper (verified twice: Round-1 methodology reviewer and
final-state AEI reviewer, both against the arXiv source)

| TEP fault | FE GPT-4o | FE o1-preview | FE-scored? |
|---|---|---|---|
| IDV1 A/C feed-ratio step (Stream 4) | wrong | correct | yes |
| IDV3 D-feed temperature step (Stream 2) | unscored | unscored | no |
| IDV4 reactor cooling-water inlet temp. (step) | unscored | unscored | no |
| IDV7 C-header pressure reduced (Stream 4) | correct | correct | yes |
| IDV11 reactor cooling-water inlet temp. (random) | correct (within alias class) | correct (within alias class) | yes |
| IDV14 reactor cooling-water valve (stiction) | correct (within alias class) | correct (within alias class) | yes |

## Aggregates (verified against the FE source)

- Root-causes-included regime: **GPT-4o 7/11 = 63.6%** (Wilson 95% CI [35.4, 84.8]);
  **o1-preview 9/11 = 81.8%** ([52.3, 94.9]) on the 11 scoreable faults.
  GPT-4o correct set: {IDV2, IDV6, IDV7, IDV11, IDV12, IDV13, IDV14};
  o1-preview correct set: {IDV1, IDV2, IDV6, IDV7, IDV8, IDV11, IDV12, IDV13, IDV14}
  (IDV8 scored correct as an alias of IDV1).
- General-Reasoning regime: **8/11, both models** (top-3, "correct or related", lenient).

## Scoring asymmetry disclosure (restated)

IDD uses **no candidate list**, outputs a **single mechanism verdict**, and is scored by
**strict mechanism-keyword matching without alias acceptance** — a stricter protocol than
FE's on all three axes. Cross-system numbers are therefore descriptive (Register A), and no
significance test is claimed (scenario sets and base models also differ).
