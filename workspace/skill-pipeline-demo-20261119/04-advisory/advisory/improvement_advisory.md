## 改善建议与验证计划

**状态**：可执行建议 · 目标模式 explicit · 证据水位线 C

| KPI | 方向 | 目标值 | 容差 |
| --- | --- | --- | --- |
| energy_kwh_per_kg | min | — | 0.03 |

| 级别 | 杠杆 | 动作 | KPI | 预期收益 | 95%CI | 机理 |
| --- | --- | --- | --- | --- | --- | --- |
| B | barrel_temp_c | 下调 191.8 → 190.3 | energy_kwh_per_kg | 0.0394 | [0.02994, 0.04886] | known |

### ACT-barrel_temp_c-822（B）
- 预期收益：0.0394 · 95%CI [0.02994, 0.04886] · 方法 dose_response
- 验证：energy_kwh_per_kg · 小试 ≥3 批（同工况确认） · 目标 energy_kwh_per_kg 改善 ≥ 0.0197（点估计的 50%）视为有效
- 回滚：若调整后 barrel_temp_c 输出未按预期改善或任一受约束指标恶化，回退至 191.765（调整前中位），并复核工况前提
- 机理链：机制边 barrel_temp_c→energy_kwh_per_kg (physical)：料筒温度高于工艺最优点时,加热与保温功耗随温差单调上升(热损失主导);INFERRED — 需以剂量-响应与小试验证；声明机制方向与本次数据建议方向一致

> 本节为确定性脚本生成的咨询建议（advisory），不构成参数下发；执行须经产线审批 / optimizer-campaign 验证。
