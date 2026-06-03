---
name: cross-model-consistency-is-not-causal
description: Cross-model sign consistency (H2's 4 models all showing negative r) is the SAME between-model pattern as H1's false alarm — not causal evidence
metadata:
  type: project
---

**Pattern discovered**: The diagnostician applied different standards to H1 and H2. H1 was excluded as BETWEEN_PRODUCT_ONLY because all within-model correlations were near-zero. But H2's "cross-model sign consistency" (4 models all showing negative W1C8C-scratch r) was treated as positive evidence (+5 confidence). 

**Why this is wrong**: Both patterns share the same logical structure: different products have different parameter baselines AND different defect baselines. When these baselines align directionally, a false cross-model correlation emerges. H1's PG22C (low torque_std + low scratch) vs PG31DS (high torque_std + high scratch) created a false positive r=0.49. H2's PG22C (high W1C8C=42.5Nm + low scratch=0.8) vs PG32B (negative W1C8C=-1.4Nm + higher scratch) created a false negative r=-0.22.

**Detection heuristic**: If a parameter's mean varies by >50% across models (e.g., W1C8C from -7.4Nm to +46.2Nm), cross-model sign consistency is likely between-model baseline alignment, not causal.

**How to apply**:
- Cross-model sign consistency only counts as evidence if: (1) within-model correlations are individually significant, AND (2) removing any single model doesn't collapse the global r
- For H2, removing PG22C collapsed global r from -0.22 to -0.128 — this is the same pattern that killed H1
- Never use cross-model consistency as positive evidence without ruling out between-model baseline confound first
