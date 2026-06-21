---
name: bopet-scratch-v4-rejudge-round2-93-pass
description: BOPET scratch diagnosis rejudge round 2, 93分 pass. COMPETING_SET正确, 温度排除correct, BETWEEN_PRODUCT_ONLY正确, 无blocking issue, 2个warning
metadata:
  type: reference
---

# BOPET MD纵拉划伤诊断v4 rejudge round 2 -- Judge 93分 pass

**Run**: 202606211028447_lekai-scratch
**Date**: 2026-06-21
**Previous score**: 91 (v4 rejudge) / 94 (prior rejudge round 1)

## 评分
- **Overall**: 93/100, verdict=pass
- **No blocking issues**
- **2 warnings**: (1) production_regime_filter FP21仅2/10稳态行未被引用到H2/H3可靠性; (2) Spearman未实际计算

## 关键通过模式
1. **COMPETING_SET正确** -- H1/H2/H3在当前数据上完全不可区分(预测变量在型号上共线)
2. **温度排除典范** -- Arrhenius一级原理量级估算(0.15C温差<2%效应) + PG31DS内验证联合排除原H3
3. **BETWEEN_PRODUCT_ONLY正确** -- 温度、速度、扭矩std全部标注为型号间差异,型号内消失
4. **无过度宣称** -- 全局|r|<0.26,所有假说标注为PLAUSIBLE,置信度上限65
5. **不确定性分解完整** -- aleatory/epistemic/model三类,附带5个具体可操作步骤

## 与之前v4 rejudge的差异
- 新run首次评审得分提升(91→93): 主要是更细致的WARNING发现(production_regime_filter引用、Spearman数值)
- 但无阻断问题,score从91提升至93反映评审更详尽

## 核心经验
- FP21的transition占比高(80%)这一信息必须显式传递到假说可靠性评估中
- SPEARMAN_RECOMMENDED标志存在时,诊断至少应提供Spearman数值(即使visual显示≈Pearson)
