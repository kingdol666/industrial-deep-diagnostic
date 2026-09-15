# Vendored upstream: FaultExplainer

This directory is a **verbatim copy** of the upstream FaultExplainer repository,
vendored (not submoduled) so that the IDD benchmark's FaultExplainer reproduction
is self-contained: `git clone` of this repository is enough to run the fidelity
gate and the supervised baselines, with no `--recursive` step.

## Provenance

| Field | Value |
|---|---|
| Upstream | https://github.com/li-group/FaultExplainer.git |
| Commit | `2fcfee975a687c350f10909eeccd1ecdd60340be` |
| Commit subject | *Update README.md* |
| Commit date | 2025-01-03 11:21:31 -0500 |
| Commit author | Can Li \<canli@purdue.edu\> |
| License | MIT (see `LICENSE`) |
| Local modifications | **none** — the tree is pristine at the pinned commit |

Paper: Khan, Nahar, Chen, Flores & Li, *FaultExplainer: Leveraging Large Language
Models for Interpretable Fault Detection and Diagnosis*, arXiv:2412.14492 (2024).

## Why vendored rather than a submodule

Two things in this tree are **load-bearing for benchmark reproducibility**, and a
submodule would make both fragile (a shallow or non-recursive clone would silently
break them):

1. `backend/data/fault0.csv` … `fault20.csv` — the labelled TEP corpus
   (21 runs × 500 samples, canonical Downs–Vogel ordering). This is the **only**
   legitimate training source for the supervised comparators
   (`xgb-gbdt`, `rf-forest`, `mlp-classifier`, `ae-reconstruction`).
2. `frontend/public/fault*.csv` — FaultExplainer's **own committed pipeline
   outputs** (`t2_stat`, `anomaly` flag, and 52 `t2_<feature>` contribution
   columns). The lab's `scripts/verify-fe.mjs` feeds the raw columns back through
   its reimplementation and compares all three quantities, which is what licenses
   calling `fe-official` a *reproduction* rather than an approximation.

## What was changed on vendoring

- Removed `.git/` (the nested repository).
- Removed `backend/.mimosa/` (local tool runtime state, not upstream content).

No other file was touched. `.gitignore` inside this directory is upstream's own.

## Not runnable as-is — this is expected

The upstream Python pipeline cannot execute here: `backend/.env` ships with an
empty `OPENAI_API_KEY`, no scikit-learn/FastAPI environment is recorded, and
`backend/results.txt` is 0 bytes (no end-to-end execution record exists upstream
either). That gap is exactly what the lab closes:

```bash
cd baseline-lab
node scripts/check-fe-scaler.mjs   # pins the StandardScaler convention (12/12 exact)
node scripts/verify-fe.mjs         # replica vs. the committed outputs (21/21, ~1e-12)
npm run dev                        # run fe-official through a real provider
```
