# 优化配方 · impurity_pct_2f_minimize

- campaign: `OPT-20261004-001`
- 验证状态: **verified** (证据等级 E2, confidence_label=verified)

## 最终设定点（建议，不下发）

| 因子 | 值 | 建议包络 |
|---|---|---|
| Temperature | 72.039091 | [71.1641, 72.9141] |
| Concentration | 0.28382 | [0.26382, 0.30382] |

## 达成指标

- impurity_pct: mean=0.460704, sd=0.0200579, n=3 (95% CI ≈ [0.426889, 0.494518])

## 收敛判定（双门槛）

- 重复数 m ≥ 3 且全落窗: True
- 单侧 95% CI 在限内: True
- D ≥ 0.8·D_max: True (D=1.0, D_max=1.0)

> regime_key: `impurity_pct_2f_minimize` — 同工况复用；跨工况使用前必须重新验证。
