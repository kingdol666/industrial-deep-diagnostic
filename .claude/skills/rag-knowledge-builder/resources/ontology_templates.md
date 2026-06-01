# Ontology Templates — Per-Scenario Extraction Schemas

> 本文件定义了每种工业场景的知识提取模板。在 Phase 3（本体构建）中使用，用于引导从知识块到本体字段的映射。

## 场景 A: CNC 加工

```yaml
template: cnc_machining
target_columns:
  - surface_roughness_Ra_um  # 主质量目标
  - thermal_deviation_mm      # 次质量目标
process_columns:
  - spindle_vibration_mm_s    # 核心退化指标
  - spindle_temp_C            # 温度感应器
  - spindle_speed_rpm         # 控制变量
  - feed_rate_mm_min          # 控制变量
  - cut_depth_mm              # 控制变量
  - tool_age_parts            # 刀具寿命代理
  - coolant_temp_C            # 冷却液温度
group_columns:
  - material                  # 关键分层列
  - tool_id                   # 换刀事件标记

extraction_rules:
  spindle_vibration_mm_s:
    - physical_meaning: "主轴振动速度 RMS"
    - source_patterns: ["ISO 10816"]
    - causal_chains: ["轴承磨损→振动↑→粗糙度↑"]
  spindle_temp_C:
    - physical_meaning: "主轴轴承温度"
    - source_patterns: ["热膨胀", "thermal expansion"]
    - causal_chains: ["摩擦↑→温度↑→热膨胀→尺寸偏差"]
```

## 场景 B: 薄膜生产

```yaml
template: continuous_film
target_columns:
  - thickness_deviation_um    # 主要问题
  - melt_spot_rate            # 缺陷率
process_columns:
  - MD_TH001 ... MD_TH012      # 机械方向温区
  - TD_TH001 ... TD_TH006      # 横向温区
  - die_gap_001 ... die_gap_005 # 模口间隙
  - line_speed_m_min           # 线速度
  - tension_N                  # 张力
group_columns:
  - product_grade              # 关键混杂：不同 product 有不同的设定值

extraction_rules:
  MD_TH003:
    - physical_meaning: "机械方向第 3 温区(拉伸区)温度设定值"
    - source_patterns: ["Tg+0-5°C", "拉伸温度"]
    - causal_chains: ["温度漂移→拉伸比波动→厚度偏差↑"]
```

## 场景 C: 反应器/批次化学

```yaml
template: batch_chemical
target_columns:
  - conversion_pct             # 转化率
  - selectivity_pct            # 选择性
process_columns:
  - reactor_temp_C             # 反应温度
  - pressure_bar               # 压力
  - h2_partial_pressure_bar    # H₂分压
  - feed_rate_L_min            # 进料速率
  - impeller_speed_rpm         # 搅拌速度
group_columns:
  - catalyst_bed_id            # 催化剂批号(关键混淆)
  - product_code

extraction_rules:
  reactor_temp_C:
    - physical_meaning: "反应温度(Arrhenius控制)"
    - source_patterns: ["Arrhenius", "活化能"]
    - causal_chains: ["温度↓→催化活性↓→转化率↓"]
```

## 场景 D: 换热器

```yaml
template: heat_exchange
target_columns:
  - heat_transfer_coefficient_W_m2K  # HTC
  - outlet_hot_temp_C                # 出口温度
process_columns:
  - inlet_hot_temp_C
  - inlet_cold_temp_C
  - flow_rate_hot_L_min
  - flow_rate_cold_L_min
  - pressure_drop_kPa
group_columns:
  - unit_id                     # 多单元操作

extraction_rules:
  heat_transfer_coefficient:
    - physical_meaning: "总传热系数 — 指示结垢程度"
    - source_patterns: ["Q = UA ΔT_LMTD", "fouling resistance"]
    - causal_chains: ["结垢→污垢热阻↑→HTC↓→出口温度↑"]
```

## 场景 E: 金属成型/冷轧

```yaml
template: metal_forming
target_columns:
  - thickness_deviation_um     # 厚度偏差
  - chatter_marks              # 振纹缺陷
process_columns:
  - roll_force_kN              # 轧制力
  - roll_speed_rpm             # 轧辊速度
  - entry_thickness_mm         # 入口厚度
  - work_roll_gap_mm           # 辊缝
  - backup_roll_vibration      # 备份辊振动
group_columns:
  - coil_id                    # 钢卷编号(换辊事件)
  - steel_grade                # 钢种

extraction_rules:
  backup_roll_vibration:
    - physical_meaning: "备份辊轴承振动(audible range)"
    - source_patterns: ["chatter", "2Hz", "轧辊旋转频率"]
    - causal_chains: ["轴承偏心→旋转不平衡→轧辊波动频率→厚度周期性偏差"]
```
