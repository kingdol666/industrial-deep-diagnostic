## 改善建议与验证计划

**状态**：仅方向参考 · 目标模式 explicit · 证据水位线 B

| KPI | 方向 | 目标值 | 容差 |
| --- | --- | --- | --- |
| coat_weight_gsm | target | 4 | 0.2 |

| 级别 | 杠杆 | 动作 | KPI | 预期收益 | 95%CI | 机理 |
| --- | --- | --- | --- | --- | --- | --- |
| C | oven1_temp_c | 下调 90 → 85.84 | coat_weight_gsm | — | 不可估（effect=null） | same_domain |
| C | solid_content_pct | 下调 60 → 57.92 | coat_weight_gsm | — | 不可估（effect=null） | same_domain |
| C | tension_n | 下调 350 → 329.2 | coat_weight_gsm | — | 不可估（effect=null） | same_domain |

### ACT-oven1_temp_c-064（C）
- 预期收益：— · 95%CI 不可估（effect=null） · 方法 none
- 验证：coat_weight_gsm · 在线连续 ≥24h 对比基线窗 · 方向验证：监控目标 KPI 变化方向，连续 3 批同向视为初步有效
- 回滚：若调整后 oven1_temp_c 输出未按预期改善或任一受约束指标恶化，回退至 90.0（调整前中位），并复核工况前提
- 机理链：杠杆 oven1_temp_c 的物理含义：oven1_temp_c（由分析上下文声明；未提供独立物理机理描述）；目标 KPI coat_weight_gsm 的物理含义：coat_weight_gsm（由分析上下文声明；未提供独立物理机理描述）；无方向声明：机制为同域先验（不构成因果边）

### ACT-solid_content_pct-270（C）
- 预期收益：— · 95%CI 不可估（effect=null） · 方法 none
- 验证：coat_weight_gsm · 在线连续 ≥24h 对比基线窗 · 方向验证：监控目标 KPI 变化方向，连续 3 批同向视为初步有效
- 回滚：若调整后 solid_content_pct 输出未按预期改善或任一受约束指标恶化，回退至 60.0（调整前中位），并复核工况前提
- 机理链：杠杆 solid_content_pct 的物理含义：solid_content_pct（由分析上下文声明；未提供独立物理机理描述）；目标 KPI coat_weight_gsm 的物理含义：coat_weight_gsm（由分析上下文声明；未提供独立物理机理描述）；无方向声明：机制为同域先验（不构成因果边）

### ACT-tension_n-462（C）
- 预期收益：— · 95%CI 不可估（effect=null） · 方法 none
- 验证：coat_weight_gsm · 在线连续 ≥24h 对比基线窗 · 方向验证：监控目标 KPI 变化方向，连续 3 批同向视为初步有效
- 回滚：若调整后 tension_n 输出未按预期改善或任一受约束指标恶化，回退至 350.0（调整前中位），并复核工况前提
- 机理链：杠杆 tension_n 的物理含义：tension_n（由分析上下文声明；未提供独立物理机理描述）；目标 KPI coat_weight_gsm 的物理含义：coat_weight_gsm（由分析上下文声明；未提供独立物理机理描述）；无方向声明：机制为同域先验（不构成因果边）

> 本节为确定性脚本生成的咨询建议（advisory），不构成参数下发；执行须经产线审批 / optimizer-campaign 验证。
