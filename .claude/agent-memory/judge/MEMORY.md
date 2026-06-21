# Judge Agent Memory Index

- [BOPET诊断评审v3](bopet-diagnosis-judge-v3.md) — BOPET划伤诊断第3轮评审，96分通过，关键模式：BETWEEN_PRODUCT_ONLY、COMPETING_SET、第一性原理量级校验
- [BOPET划伤诊断v4 (scratch)](bopet-scratch-diagnosis-v4.md) — BOPET MD纵拉划伤诊断lekai数据，92分通过，模型混杂90-111%, PG31DS内CV=187%, COMPETING_SET(38/100)
- [BOPET划伤诊断v4 rejudge (94分)](bopet-scratch-diagnosis-v4-rejudge.md) — BOPET MD纵拉划伤诊断repair round 1评审，94分通过，修复4项问题: PG31DS参数变异修正、多重检验标注、W1C88-W1C7C互相关、阶跃变化标注
- [BOPET划伤诊断v4 rejudge round 2 (96分)](bopet-scratch-diagnosis-v4-rejudge-round2.md) — 第2轮rejudge, 修复preflight 2个阻断问题: outlier-driven Pearson伪相关 + 时间趋势混杂, 全工艺参数排除后H3(时间累积)置信度25
- [BOPET划伤诊断v4新run Judge (86分 needs_repair)](bopet-scratch-diagnosis-v4-judge-86-needs-repair.md) — Lekai scratch新run首次评审86分, 无阻断, 3项warning: proof_strength降级、time_lag引用、regime_filter引用。COMPETING_SET(H1=62), FP21方向反转已隐含处理
- [BOPET划伤诊断v4 rejudge round 2 Judge (93分 pass)](bopet-scratch-v4-rejudge-round2-judge-93-pass.md) — Lekai scratch v4 rejudge round 2评审93分pass, COMPETING_SET正确, 2项warning: production_regime_filter FP21过渡数据未引用, Spearman未计算
