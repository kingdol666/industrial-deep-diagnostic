# 本体简报（profile=improvement）

- 场景: injection_energy_advisory · 构建方式: prior_knowledge · lookup: miss
- 覆盖: 0/6 列有机制先验

## 列角色与单位

| 列 | 角色 | 单位 | 机制先验 | 来源 |
|---|---|---|---|---|
| barrel_temp_c | predictor | 未声明 | unknown | auto_inferred |
| injection_pressure_bar | predictor | 未声明 | unknown | auto_inferred |
| cooling_time_s | predictor | 未声明 | unknown | auto_inferred |
| back_pressure_bar | predictor | 未声明 | unknown | auto_inferred |
| energy_kwh_per_kg | predictor | 未声明 | unknown | auto_inferred |
| reject_rate_pct | predictor | 未声明 | unknown | auto_inferred |

## 局限

- 声明先验本体：不声称已观测行为（observed_data_behavior=NOT_APPLICABLE）。
- relationships 为空 = 无方向声明，未造因果边。
- 词典 typical_ranges 是参考区间（非规格）；normal_range 仅来自用户声明。
- rag_used/web_used 恒为 false（确定性路径）。
