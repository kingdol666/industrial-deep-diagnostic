# 优化配方 · energy_kwh_per_kg_2f_minimize

- campaign: `OPT-20261119-001`
- 验证状态: **verified** (证据等级 E2, confidence_label=verified)

## 最终设定点（建议，不下发）

| 因子 | 值 | 建议包络 |
|---|---|---|
| barrel_temp_c | 184.980584 | [184.106, 185.856] |
| cooling_time_s | 28.609994 | [27.86, 29.36] |

## 达成指标

- energy_kwh_per_kg: mean=1.92337, sd=0.0361775, n=3 (95% CI ≈ [1.86238, 1.98436])

## 收敛判定（双门槛）

- 重复数 m ≥ 3 且全落窗: True
- 单侧 95% CI 在限内: True
- D ≥ 0.8·D_max: True (D=1.0, D_max=1.0)

> regime_key: `energy_kwh_per_kg_2f_minimize` — 同工况复用；跨工况使用前必须重新验证。
