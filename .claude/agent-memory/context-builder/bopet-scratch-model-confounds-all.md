---
name: bopet-scratch-model-confounds-all
description: Product model (grade) is the dominant confounder in BOPET scratch diagnosis — 8 models with different scratch baselines (PG22C=0.8 to FG22=460.7) cause Simpson's Paradox. Temperature-scratch r≈0.25 is entirely between-model driven.
metadata:
  type: project
---

Updated 2026-06-18 from run 202606171624539 with fresh data (149 batches, new model breakdown):

The `model` column (8+ product grades) confounds EVERY parameter-defect correlation in this dataset. Key data:

**Scratch baselines by model:**
- PG22C (n=6): scratch_mean=0.8 (near zero)
- PG32B (n=10): scratch_mean=4.2
- PG32M (n=13): scratch_mean=9.2
- PG32DS (n=9): scratch_mean=17.6
- PG31DS (n=67): scratch_mean=33.8 (MOST batches, lowest HIGH-scratch models)
- PG32D (n=16): scratch_mean=109.4
- FP21 (n=19): scratch_mean=375.5
- FG22 (n=6): scratch_mean=460.7
- FP41 (n=3): scratch_mean=395.7

**Temperature correlations: 18-roller aggregate r≈0.07-0.28 WITHIN preheat/stretch zones but driven entirely by between-model differences.**
- FG22 (highest scratch) runs hottest, PG22C (lowest scratch) runs coolest
- Within PG31DS (n=67, largest group): TH001 vs scratch r=-0.08 (reversed!)

**Speed: W1C40/W1C4B perfectly collinear (r=1.0).**
- Draw ratio = 3.08 fixed. Speed changes = grade changes.
- W1C40 vs scratch r=-0.06 overall (near zero)

**Implication:** ALL bivariate correlations must be stratified by model. The question shifts to "within same grade, does parameter variation correlate with scratch?"

Note: Model names have trailing-space variants (PG32D and PG32D_, PG32M and PG32M_) that must be cleaned before grouping.
