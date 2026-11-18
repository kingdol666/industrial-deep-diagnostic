# Submission Package — assembly checklist (round41)

Working state: `paper/main.pdf` (60 pp, 0 errors / 0 overfull / 0 float warnings / 0 broken
refs, fresh bibtex 0 skipping) is the submission build; `paper/main_preprint.pdf` (12pt
variant) is a secondary artifact with 3 known float overhangs to fix before upload if used.

## Files to upload to Editorial Manager (editorialmanager.com/advei)

| Item | Source | Status |
|---|---|---|
| Manuscript PDF + editable .tex source | `paper/main.pdf`, `paper/main.tex`, `paper/refs.bib`, `paper/figures/*.png` (+ elsarticle cls/bst from TeX Live) | READY |
| Highlights (separate editable file) | `paper/submission/highlights.txt` (paste into the EM highlights item / Word) | READY |
| Cover letter | `paper/submission/cover_letter.md` (paste into EM or convert to .docx) | READY (author: personalize before sending) |
| Supplementary artifact layer | run `python paper/submission/build_supplementary.py` → `supplementary_artifact_layer.zip` (≈59 MB source) | READY (one command) |
| Declaration of interests | Elsevier declarations tool → generate .docx at submission | AUTHOR ACTION |
| CRediT, funding, data availability, GenAI declarations | in-manuscript (main.tex) | READY |

## Author-only items (cannot be done by an agent)

1. ORCID of the corresponding author (EM registration).
2. Confirm name split (Zhang = family name) and affiliation English form as printed.
3. Declare any prior preprint posting (arXiv/SSRN) in the submission questions.
4. Optionally: suggested reviewers (EM form).
5. Personalize the cover letter's salutation/addressee.

## At acceptance

- Return proofs within 2 days (Elsevier service level for this journal).
- Mint the Zenodo DOI (deposit = supplementary zip + pinned commit `221d061`), update the
  data availability statement's final "will be minted" phrasing at proof stage if the journal
  requires the DOI in-print.
