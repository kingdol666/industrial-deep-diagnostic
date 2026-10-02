# 优化配方 · yield_pct_2f_target

- campaign: `OPT-20261001-001`
- 验证状态: **verified** (证据等级 E2, confidence_label=verified)

## 最终设定点（建议，不下发）

| 因子 | 值 | 建议包络 |
|---|---|---|
| temp | 82.0 | [82, 82.15] |
| press | 0.559759 | [0.557259, 0.562259] |

## 达成指标

- yield_pct: mean=98.949, sd=0.153788, n=3 (95% CI ≈ [98.6897, 99.2082])

## 收敛判定（双门槛）

- 重复数 m ≥ 3 且全落窗: True
- 单侧 95% CI 在限内: True
- D ≥ 0.8·D_max: True (D=0.862697, D_max=0.995182)

> regime_key: `yield_pct_2f_target` — 同工况复用；跨工况使用前必须重新验证。
