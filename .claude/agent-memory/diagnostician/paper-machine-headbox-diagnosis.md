---
name: paper-machine-headbox-diagnosis
description: Paper machine headbox diagnosis: flow resistance increase (H1, DETERMINED, 79 conf) with retention control loop as secondary amplifier (H2, 65 conf)
metadata:
  type: project
---

# Paper Machine Headbox Diagnosis (2026-07-27)

**Scene**: paper_machine_headbox — continuous web forming with headbox pressure control and retention management

**Diagnosis type**: DETERMINED
**Confidence**: 79/100 (MEDIUM)

## Surviving Hypotheses
- **H1 (79)**: 流浆箱内部流动阻力增大(结垢/堵塞)导致压力飙升和质量连锁恶化. Pump law deviation quantifies 11x excess pressure (fan pump speed +4.1% predicts +8.4% via N², actual +93%).
- **H2 (65)**: 保留助剂反馈回路次级放大机制 (NOT competing — forms causal chain with H1).

## Eliminated Hypotheses
- **H3 (excluded 95% conf)**: Stock temperature — detrend attenuation 98.6%
- **H4 (excluded 92% conf)**: Vacuum system — r<0.03 with all quality metrics
- **H5 (excluded 95% conf)**: Fan pump speed — pump law predicts +8.4%, actual +93%

## Key Physics
- Bernoulli: v_jet = Cv × sqrt(2P/ρ)
- Pump affinity: H1/H2 = (N1/N2)²
- Darcy-Weisbach: ΔP = f·(L/D)·(ρv²/2)
- Retention-formation trade-off: r=-0.92 raw, -0.50 detrended

## Critical Insight
Three product grades (GSM80/100/120) show identical pressure drift slopes (0.156-0.211 kPa/day) differing only by baseline offset. This cross-product UNIVERSAL consistency strongly indicates a common-cause system-level issue (headbox internal fouling), not grade-specific operational changes.

## Files
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`

## Why This Matters
This was the first full physical-drive competing-hypotheses diagnosis on a paper machine dataset. The pump-law deviation calculation (expected +8.4% vs actual +93% → 11x excess proving flow resistance increase) is a reusable quantitative pattern for any centrifugal-pump system diagnosis.
