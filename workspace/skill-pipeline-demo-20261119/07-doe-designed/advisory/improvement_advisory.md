## 改善建议与验证计划

**状态**：仅方向参考 · 目标模式 explicit · 证据水位线 B

| KPI | 方向 | 目标值 | 容差 |
| --- | --- | --- | --- |
| energy_kwh_per_kg | target | 0.66 | 0.075 |

| 级别 | 杠杆 | 动作 | KPI | 预期收益 | 95%CI | 机理 |
| --- | --- | --- | --- | --- | --- | --- |
| C | barrel_temp_c | 上调 190 → 191.7 | energy_kwh_per_kg | — | 不可估（effect=null） | same_domain |

### ACT-barrel_temp_c-822（C）
- 预期收益：— · 95%CI 不可估（effect=null） · 方法 none
- 验证：energy_kwh_per_kg · 在线连续 ≥24h 对比基线窗 · 方向验证：监控目标 KPI 变化方向，连续 3 批同向视为初步有效
- 回滚：若调整后 barrel_temp_c 输出未按预期改善或任一受约束指标恶化，回退至 190.0（调整前中位），并复核工况前提
- 机理链：杠杆 barrel_temp_c 的物理含义：barrel_temp_c（由分析上下文声明；未提供独立物理机理描述）；目标 KPI energy_kwh_per_kg 的物理含义：energy_kwh_per_kg（由分析上下文声明；未提供独立物理机理描述）；无方向声明：机制为同域先验（不构成因果边）

> 本节为确定性脚本生成的咨询建议（advisory），不构成参数下发；执行须经产线审批 / optimizer-campaign 验证。
