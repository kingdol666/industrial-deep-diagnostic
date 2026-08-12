# 增强诊断分析报告

> 自动生成于 2026-08-12 18:33:05 UTC  
> 运行标识: enhancement-deep-analysis  
> 管线状态: 就绪 (`READY`)

---

## 0. AI 可操作摘要（机器可读）

> **本节为下游 AI Agent 的主要消费接口。** 下方 JSON 块编码了分析结果的结构化摘要：
> 控制杠杆、因果路径、枢纽参数。Agent 可直接解析此 JSON 获取行动参考，
> 无需阅读全文。完整证据详见后续章节。

```json
{
  "document_type": "industrial_deep_analysis",
  "version": "2.0",
  "run_id": "enhancement-deep-analysis",
  "status": "READY",
  "parameter_count": 17,
  "relationship_count": 8,
  "physics_verification": {
    "verified": 0,
    "total_tested": 5,
    "rate": 0.0
  },
  "top_control_levers": [
    {
      "parameter": "reactor_temp",
      "physical_meaning": "反应器温度",
      "controllable": true,
      "confidence": 1.0,
      "downstream": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.9476,
          "physics_verified": false
        }
      ],
      "risks": [
        "None identified"
      ]
    },
    {
      "parameter": "cooling_flow",
      "physical_meaning": "冷却水流量",
      "controllable": true,
      "confidence": 1.0,
      "downstream": [
        {
          "target": "product_purity",
          "direction": "decrease",
          "strength": -0.8675,
          "physics_verified": false
        }
      ],
      "risks": [
        "None identified"
      ]
    },
    {
      "parameter": "catalyst_age",
      "physical_meaning": "催化剂使用时长",
      "controllable": true,
      "confidence": 1.0,
      "downstream": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.8734,
          "physics_verified": false
        }
      ],
      "risks": [
        "None identified"
      ]
    },
    {
      "parameter": "feed_rate",
      "physical_meaning": "进料流量",
      "controllable": true,
      "confidence": 0.8,
      "downstream": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.1839,
          "physics_verified": false
        }
      ],
      "risks": [
        "None identified"
      ]
    },
    {
      "parameter": "time_since_product_grade_transition",
      "physical_meaning": "",
      "controllable": false,
      "confidence": 0.2,
      "downstream": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.0293,
          "physics_verified": false
        }
      ],
      "risks": [
        "Confounder present for product_purity",
        "Interaction/moderation effect on product_purity"
      ]
    }
  ],
  "strongest_causal_pathways": [
    {
      "path": "reactor_temp → product_purity",
      "strength": 0.9476,
      "hops": 1
    },
    {
      "path": "catalyst_age → product_purity",
      "strength": 0.8734,
      "hops": 1
    },
    {
      "path": "cooling_flow → product_purity",
      "strength": 0.8675,
      "hops": 1
    },
    {
      "path": "reactor_temp → catalyst_age → product_purity",
      "strength": 0.8168,
      "hops": 2
    },
    {
      "path": "cooling_flow → catalyst_age → product_purity",
      "strength": 0.7853,
      "hops": 2
    }
  ],
  "hub_parameters": [
    {
      "parameter": "reactor_temp",
      "influence": 2.7336,
      "targets": [
        "product_purity"
      ]
    },
    {
      "parameter": "cooling_flow",
      "influence": 1.7666,
      "targets": [
        "product_purity"
      ]
    }
  ],
  "usage_instruction": "This summary encodes the analysis results for machine consumption. Each control lever lists its downstream effects on quality targets. 'direction: increase' means raising the parameter raises the target. 'physics_verified: true' means the relationship passed 5-item physics verification. Always check 'risk_factors' before acting. See full document for detailed evidence."
}
```

---

## 1. 执行摘要

本报告由工业诊断增强管线自动生成，基于对原始诊断运行的深层数据分析、衍生特征构建、条件关系分析和物理机理桥接的综合结果。

### 数据源

| 属性 | 值 |
|------|----|
| 数据文件 | `cleaned_data.csv` |
| 行数 | 200 |
| 列数 | 12 |
| SHA256 | `1484fa4ddebc41b4...` |

### 增强管线状态

管线状态为 **就绪**。

> 关系可操作性分布：
> - 已确认杠杆: 0
> - 观察性关联: 4
> - 内生响应: 0
> - 混杂: 1
> - 不可识别: 0
> - 不可控约束: 0

### 分析概览

| 维度 | 数量 |
|------|------|
| 分析变量 | 17 |
| 统计关系 | 8 |
| 多跳因果路径 | 7 |
| 控制杠杆 | 5 |
| 枢纽参数 | 2 |
| 物理机理链 | 1 |

### 上游产物

- `analysis_coverage`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\analysis_coverage.json
- `derived_features`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\derived_features.json
- `deep_data_analysis`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\deep_data_analysis.json
- `association_graph`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\association_graph.json
- `physics_bridge`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\physics_bridge.json
- `ontology`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\01_ontology\ontology.json
- `diagnosis`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\04_diagnostics\diagnosis.json

---

## 2. 控制杠杆（行动参考）

> **此节是操作优化的核心。** 每个控制杠杆列出了该参数对下游质量目标的影响方向、
> 强度、置信度和物理验证状态。下游 Agent 应基于此节制定操作策略。

### 控制杠杆总览

| 参数 | 物理含义 | 可控 | 置信度 | 下游目标 | 方向 | 强度 | 物理验证 | 风险 |
|------|----------|:----:|:------:|----------|------|------|:--------:|------|
| `reactor_temp` | 反应器温度 | ✅ | 1.00 | `product_purity` | ↑ | 0.948 | — | 无 |
| `cooling_flow` | 冷却水流量 | ✅ | 1.00 | `product_purity` | ↓ | -0.868 | — | 无 |
| `catalyst_age` | 催化剂使用时长 | ✅ | 1.00 | `product_purity` | ↑ | 0.873 | — | 无 |
| `feed_rate` | 进料流量 | ✅ | 0.80 | `product_purity` | ↑ | 0.184 | — | 无 |
| `time_since_product_grade_transition` |  | ❌ | 0.20 | `product_purity` | ↑ | 0.029 | — | Confounder present for pr |

### 控制杠杆详细分析

每条杠杆附带机器可读 JSON 块，包含完整的下游效应、风险因素和操作域信息。

### 控制杠杆 LEVER-001: `reactor_temp`

**物理含义**: 反应器温度
**单位**: °C
**当前值(中位数)**: 89.7
**可控性**: ✅ 已验证可控
**综合置信度**: 1.00/1.00
**设备工段**: reactor

| 目标参数 | 方向 | 强度(r) | 当前斜率 | 置信度 | 物理验证 | q值 | 时序方向 |
|----------|------|---------|----------|--------|:--------:|-----|----------|
| `product_purity` | ↑ 增加 | 0.948 | 0.0000 | 1.00 | — | 0.0000 | concurrent |

```json
{
  "lever_id": "LEVER-001",
  "parameter": "reactor_temp",
  "controllable": true,
  "confidence": 1.0,
  "downstream_effects": [
    {
      "target": "product_purity",
      "direction": "increase",
      "strength": 0.9476,
      "slope_at_current": 0.0,
      "confidence": 1.0,
      "physics_verified": false,
      "physics_status": "plausible",
      "causal_ceiling": "ontology_consistent",
      "q_value": 0.0,
      "n_effective": 200,
      "temporal_direction": "concurrent"
    }
  ],
  "risk_factors": [
    "None identified"
  ],
  "operability": [
    "LEVER_OBSERVATIONAL",
    "UNCLASSIFIED"
  ],
  "support_domain": {
    "p5": 80.595,
    "p25": 84.675,
    "p50": 89.7,
    "p75": 94.97500000000001,
    "p95": 100.00999999999999,
    "n": 200,
    "current_median": 89.7
  }
}
```

### 控制杠杆 LEVER-002: `cooling_flow`

**物理含义**: 冷却水流量
**单位**: L/min
**当前值(中位数)**: 45.2
**可控性**: ✅ 已验证可控
**综合置信度**: 1.00/1.00
**设备工段**: cooling

| 目标参数 | 方向 | 强度(r) | 当前斜率 | 置信度 | 物理验证 | q值 | 时序方向 |
|----------|------|---------|----------|--------|:--------:|-----|----------|
| `product_purity` | ↓ 减少 | -0.868 | 0.0000 | 1.00 | — | 0.0000 | concurrent |

```json
{
  "lever_id": "LEVER-002",
  "parameter": "cooling_flow",
  "controllable": true,
  "confidence": 1.0,
  "downstream_effects": [
    {
      "target": "product_purity",
      "direction": "decrease",
      "strength": -0.8675,
      "slope_at_current": 0.0,
      "confidence": 1.0,
      "physics_verified": false,
      "physics_status": "plausible",
      "causal_ceiling": "ontology_consistent",
      "q_value": 0.0,
      "n_effective": 200,
      "temporal_direction": "concurrent"
    }
  ],
  "risk_factors": [
    "None identified"
  ],
  "operability": [
    "LEVER_OBSERVATIONAL",
    "UNCLASSIFIED"
  ],
  "support_domain": {
    "p5": 39.985,
    "p25": 42.45,
    "p50": 45.2,
    "p75": 47.525,
    "p95": 50.705,
    "n": 200,
    "current_median": 45.2
  }
}
```

### 控制杠杆 LEVER-003: `catalyst_age`

**物理含义**: 催化剂使用时长
**单位**: h
**当前值(中位数)**: 19.95
**可控性**: ✅ 已验证可控
**综合置信度**: 1.00/1.00
**设备工段**: reactor

| 目标参数 | 方向 | 强度(r) | 当前斜率 | 置信度 | 物理验证 | q值 | 时序方向 |
|----------|------|---------|----------|--------|:--------:|-----|----------|
| `product_purity` | ↑ 增加 | 0.873 | 0.0000 | 1.00 | — | 0.0000 | concurrent |

```json
{
  "lever_id": "LEVER-003",
  "parameter": "catalyst_age",
  "controllable": true,
  "confidence": 1.0,
  "downstream_effects": [
    {
      "target": "product_purity",
      "direction": "increase",
      "strength": 0.8734,
      "slope_at_current": 0.0,
      "confidence": 1.0,
      "physics_verified": false,
      "physics_status": "plausible",
      "causal_ceiling": "ontology_consistent",
      "q_value": 0.0,
      "n_effective": 200,
      "temporal_direction": "concurrent"
    }
  ],
  "risk_factors": [
    "None identified"
  ],
  "operability": [
    "LEVER_OBSERVATIONAL"
  ],
  "support_domain": {
    "p5": 10.995000000000001,
    "p25": 14.975,
    "p50": 19.95,
    "p75": 24.924999999999997,
    "p95": 28.904999999999998,
    "n": 200,
    "current_median": 19.95
  }
}
```

### 控制杠杆 LEVER-004: `feed_rate`

**物理含义**: 进料流量
**单位**: kg/h
**当前值(中位数)**: 99.9
**可控性**: ✅ 已验证可控
**综合置信度**: 0.80/1.00
**设备工段**: feed

| 目标参数 | 方向 | 强度(r) | 当前斜率 | 置信度 | 物理验证 | q值 | 时序方向 |
|----------|------|---------|----------|--------|:--------:|-----|----------|
| `product_purity` | ↑ 增加 | 0.184 | 0.0000 | 0.80 | — | 0.0106 | x_leads_y |

```json
{
  "lever_id": "LEVER-004",
  "parameter": "feed_rate",
  "controllable": true,
  "confidence": 0.8,
  "downstream_effects": [
    {
      "target": "product_purity",
      "direction": "increase",
      "strength": 0.1839,
      "slope_at_current": 0.0,
      "confidence": 0.8,
      "physics_verified": false,
      "physics_status": "plausible",
      "causal_ceiling": "insufficient_evidence",
      "q_value": 0.010569,
      "n_effective": 198,
      "temporal_direction": "x_leads_y"
    }
  ],
  "risk_factors": [
    "None identified"
  ],
  "operability": [
    "LEVER_OBSERVATIONAL"
  ],
  "support_domain": {
    "p5": 96.0,
    "p25": 97.1,
    "p50": 99.9,
    "p75": 102.8,
    "p95": 103.905,
    "n": 200,
    "current_median": 99.9
  }
}
```

### 控制杠杆 LEVER-005: `time_since_product_grade_transition`

**物理含义**: 
**单位**: hours
**当前值(中位数)**: None
**可控性**: ⚠️ 观测性关联
**综合置信度**: 0.20/1.00
**设备工段**: 

| 目标参数 | 方向 | 强度(r) | 当前斜率 | 置信度 | 物理验证 | q值 | 时序方向 |
|----------|------|---------|----------|--------|:--------:|-----|----------|
| `product_purity` | ↑ 增加 | 0.029 | 0.0000 | 0.20 | — | 0.6798 | x_leads_y |

**⚠️ 风险因素**:
- Confounder present for product_purity
- Interaction/moderation effect on product_purity

```json
{
  "lever_id": "LEVER-005",
  "parameter": "time_since_product_grade_transition",
  "controllable": false,
  "confidence": 0.2,
  "downstream_effects": [
    {
      "target": "product_purity",
      "direction": "increase",
      "strength": 0.0293,
      "slope_at_current": 0.0,
      "confidence": 0.2,
      "physics_verified": false,
      "physics_status": "plausible",
      "causal_ceiling": "insufficient_evidence",
      "q_value": 0.679795,
      "n_effective": 198,
      "temporal_direction": "x_leads_y"
    }
  ],
  "risk_factors": [
    "Confounder present for product_purity",
    "Interaction/moderation effect on product_purity"
  ],
  "operability": [
    "CONFOUNDED"
  ],
  "support_domain": {}
}
```


---

## 3. 参数影响矩阵

> 参数对质量目标的影响矩阵。颜色编码：🟢强正相关(≥0.5) 🟡中等正相关(0.3-0.5)
> ⚫弱相关(0.1-0.3) · 极弱/无关 | 🔴🟠 负相关同级别 | ✓ 物理验证通过。

| 参数 | `product_purity` |
|------|---:|
| `catalyst_age` | 🟢+0.87 |
| `catalyst_age_dev` | — |
| `cooling_flow` | 🔴-0.87 |
| `cooling_flow_dev` | — |
| `cumulative_exposure` | — |
| `feed_rate` | ⚫+0.18 |
| `lag_aligned_feature` | — |
| `product_grade` | — |
| `product_purity_dev` | — |
| `reactor_temp` | 🟢+0.95 |
| `reactor_temp_dev` | — |
| `regime_steady` | — |
| `regime_transition` | — |
| `time_hours` | — |
| `time_since_product_g` | ·+0.03 |
| `timestamp` | — |

**图例**: 🟢强正相关(≥0.5) 🟡中等正相关(0.3-0.5) ⚫弱相关(0.1-0.3) · 极弱/无关 | 🔴🔴🟠 负相关同级别 | ✓ 物理验证通过

---

## 4. 多跳因果路径

> 从过程参数到质量目标的多跳因果传导路径。路径强度 = 各边 |r| 的乘积。
> 最小置信度 = 路径上所有边的最低置信度。共 7 条路径。

### 因果路径 PATH-001: `reactor_temp` → `product_purity`

**跳数**: 1
**路径强度** (边强度乘积): 0.9476
**最小置信度**: 1.00

**路径上的每条边**:

| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |
|-------------|----------|------|--------|:--------:|
| `reactor_temp` → `product_purity` | supports | 0.948 | 1.00 | — |

**物理链条解读**:
- `reactor_temp`: 反应器温度
- `product_purity`: 产品纯度

### 因果路径 PATH-002: `catalyst_age` → `product_purity`

**跳数**: 1
**路径强度** (边强度乘积): 0.8734
**最小置信度**: 1.00

**路径上的每条边**:

| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |
|-------------|----------|------|--------|:--------:|
| `catalyst_age` → `product_purity` | supports | 0.873 | 1.00 | — |

**物理链条解读**:
- `catalyst_age`: 催化剂使用时长
- `product_purity`: 产品纯度

### 因果路径 PATH-003: `cooling_flow` → `product_purity`

**跳数**: 1
**路径强度** (边强度乘积): 0.8675
**最小置信度**: 1.00

**路径上的每条边**:

| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |
|-------------|----------|------|--------|:--------:|
| `cooling_flow` → `product_purity` | inhibits | -0.867 | 1.00 | — |

**物理链条解读**:
- `cooling_flow`: 冷却水流量
- `product_purity`: 产品纯度

### 因果路径 PATH-004: `reactor_temp` → `catalyst_age` → `product_purity`

**跳数**: 2
**路径强度** (边强度乘积): 0.8168
**最小置信度**: 0.60

**路径上的每条边**:

| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |
|-------------|----------|------|--------|:--------:|
| `reactor_temp` → `catalyst_age` | supports | 0.935 | 0.60 | — |
| `catalyst_age` → `product_purity` | supports | 0.873 | 1.00 | — |

**物理链条解读**:
- `reactor_temp`: 反应器温度
- `catalyst_age`: 催化剂使用时长
- `product_purity`: 产品纯度

### 因果路径 PATH-005: `cooling_flow` → `catalyst_age` → `product_purity`

**跳数**: 2
**路径强度** (边强度乘积): 0.7853
**最小置信度**: 0.60

**路径上的每条边**:

| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |
|-------------|----------|------|--------|:--------:|
| `cooling_flow` → `catalyst_age` | inhibits | -0.899 | 0.60 | — |
| `catalyst_age` → `product_purity` | supports | 0.873 | 1.00 | — |

**物理链条解读**:
- `cooling_flow`: 冷却水流量
- `catalyst_age`: 催化剂使用时长
- `product_purity`: 产品纯度

### 因果路径 PATH-006: `reactor_temp` → `cooling_flow` → `product_purity`

**跳数**: 2
**路径强度** (边强度乘积): 0.7381
**最小置信度**: 0.60

**路径上的每条边**:

| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |
|-------------|----------|------|--------|:--------:|
| `reactor_temp` → `cooling_flow` | inhibits | -0.851 | 0.60 | — |
| `cooling_flow` → `product_purity` | inhibits | -0.867 | 1.00 | — |

**物理链条解读**:
- `reactor_temp`: 反应器温度
- `cooling_flow`: 冷却水流量
- `product_purity`: 产品纯度

### 因果路径 PATH-007: `reactor_temp` → `cooling_flow` → `catalyst_age` → `product_purity`

**跳数**: 3
**路径强度** (边强度乘积): 0.6682
**最小置信度**: 0.60

**路径上的每条边**:

| 起点 → 终点 | 关系类型 | 强度 | 置信度 | 物理验证 |
|-------------|----------|------|--------|:--------:|
| `reactor_temp` → `cooling_flow` | inhibits | -0.851 | 0.60 | — |
| `cooling_flow` → `catalyst_age` | inhibits | -0.899 | 0.60 | — |
| `catalyst_age` → `product_purity` | supports | 0.873 | 1.00 | — |

**物理链条解读**:
- `reactor_temp`: 反应器温度
- `cooling_flow`: 冷却水流量
- `catalyst_age`: 催化剂使用时长
- `product_purity`: 产品纯度


---

## 5. 参数网络中心性

> 每个参数在网络中的影响力评估。出度 = 该参数影响多少其他参数；
> 影响力分 = 所有出边强度之和；枢纽参数(⭐) = 出度≥3或影响力≥1.0。

| 参数 | 角色 | 出度 | 入度 | 影响力分 | 枢纽? | 下游质量目标 | 物理参考 |
|------|------|:----:|:----:|:--------:|:-----:|-------------|----------|
| `reactor_temp` | predictor | 3 | 0 | 2.734 | ⭐ | `product_purity` | NOT_APPLICABLE |
| `cooling_flow` | predictor | 2 | 1 | 1.767 | ⭐ | `product_purity` | NOT_APPLICABLE |
| `catalyst_age` | predictor | 1 | 2 | 0.873 |  | `product_purity` | NOT_APPLICABLE |
| `feed_rate` | predictor | 1 | 0 | 0.184 |  | `product_purity` | NOT_APPLICABLE |
| `time_since_product_grade_transition` | derived_feature | 1 | 0 | 0.029 |  | `product_purity` |  |
| `timestamp` | unknown | 0 | 0 | 0.000 |  | — | NOT_APPLICABLE |
| `product_purity` | target | 0 | 5 | 0.000 |  | — | NOT_APPLICABLE |
| `product_grade` | unknown | 0 | 0 | 0.000 |  | — | NOT_APPLICABLE |
| `reactor_temp_dev` | derived_deviation | 0 | 0 | 0.000 |  | — | NOT_APPLICABLE |
| `cooling_flow_dev` | derived_deviation | 0 | 0 | 0.000 |  | — | NOT_APPLICABLE |
| `catalyst_age_dev` | derived_deviation | 0 | 0 | 0.000 |  | — | NOT_APPLICABLE |
| `product_purity_dev` | derived_deviation | 0 | 0 | 0.000 |  | — | NOT_APPLICABLE |
| `time_hours` | derived_time | 0 | 0 | 0.000 |  | — | NOT_APPLICABLE |
| `cumulative_exposure` | derived_feature | 0 | 0 | 0.000 |  | — |  |
| `regime_steady` | derived_feature | 0 | 0 | 0.000 |  | — |  |
| `regime_transition` | derived_feature | 0 | 0 | 0.000 |  | — |  |
| `lag_aligned_feature` | derived_feature | 0 | 0 | 0.000 |  | — |  |

---

## 6. 物理上下文映射

> 每个参数在本体模型中的物理含义、单位、角色和控制方程。
> 此表建立了数据列名与物理量之间的映射。

| 参数 | 物理含义 | 单位 | 角色 | 控制方程/预期行为 | 设备工段 |
|------|----------|------|------|-------------------|----------|
| `catalyst_age` | 催化剂使用时长 | h | process_parameter |  | reactor |
| `catalyst_age_dev` | NOT_APPLICABLE | metadata | derived_deviation |  |  |
| `cooling_flow` | 冷却水流量 | L/min | process_parameter | Q=m·c·ΔT | cooling |
| `cooling_flow_dev` | NOT_APPLICABLE | metadata | derived_deviation |  |  |
| `feed_rate` | 进料流量 | kg/h | process_parameter |  | feed |
| `product_grade` | 产品等级 | category | grouping |  |  |
| `product_purity` | 产品纯度 | % | quality_target |  |  |
| `product_purity_dev` | NOT_APPLICABLE | metadata | derived_deviation |  |  |
| `reactor_temp` | 反应器温度 | °C | process_parameter | Arrhenius: k=A·exp(-Ea/RT) | reactor |
| `reactor_temp_dev` | NOT_APPLICABLE | metadata | derived_deviation |  |  |
| `time_hours` | NOT_APPLICABLE | metadata | derived_time |  |  |
| `timestamp` | 时间戳 | datetime | metadata |  |  |

---

## 7. 管线溯源与覆盖范围

### 输入产物清单

本增强管线消费了以下基线诊断产物：

- `analysis_coverage`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\analysis_coverage.json
- `derived_features`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\derived_features.json
- `deep_data_analysis`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\deep_data_analysis.json
- `association_graph`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\association_graph.json
- `physics_bridge`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\enhancement\physics_bridge.json
- `ontology`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\01_ontology\ontology.json
- `diagnosis`: D:\codes\industrial-deep-diagnostic\workspace\e2e-test\run\04_diagnostics\diagnosis.json

### 变量覆盖

分析覆盖 17 个变量，构建 8 条统计关系。

| 节点ID | 类型 | 单位 | 角色 | 覆盖状态 |
|--------|------|------|------|----------|
| `timestamp` | parameter | metadata | unknown | not_applicable |
| `reactor_temp` | parameter | dimensionless | predictor | covered_primary |
| `feed_rate` | parameter | dimensionless | predictor | covered_primary |
| `cooling_flow` | parameter | dimensionless | predictor | covered_primary |
| `catalyst_age` | parameter | dimensionless | predictor | covered_primary |
| `product_purity` | target | dimensionless | target | covered_primary |
| `product_grade` | parameter | metadata | unknown | not_applicable |
| `reactor_temp_dev` | parameter | metadata | derived_deviation | derived_and_used |
| `cooling_flow_dev` | parameter | metadata | derived_deviation | derived_and_used |
| `catalyst_age_dev` | parameter | metadata | derived_deviation | derived_and_used |
| `product_purity_dev` | parameter | metadata | derived_deviation | derived_and_used |
| `time_hours` | parameter | metadata | derived_time | not_applicable |
| `cumulative_exposure` | derived | dimensionless*time | derived_feature |  |
| `time_since_product_grade_transition` | derived | hours | derived_feature |  |
| `regime_steady` | derived | binary | derived_feature |  |
| `regime_transition` | derived | binary | derived_feature |  |
| `lag_aligned_feature` | derived | same_as_source | derived_feature |  |

---

## 8. 关系图谱与统计证据

以下各节展示每条预测变量与目标变量之间的关系、统计证据和可操作性评估。每条核心结论附带机器可读的 JSON 证据块。

### 关联网络总览（数据驱动推理）

以下统计来自全变量两两扫描 + 推理引擎（时序领先、条件独立、变点同步、留一杠杆）：

| 维度 | 统计 |
|------|------|
| 边总数 | 8 |
| 正关联 (supports) | 5 |
| 负关联 (inhibits) | 3 |
| 因果边 (causes) | 0 |
| 矛盾边 (contradicts) | 0 |
| 直接关联（条件独立成立） | 3 |
| 间接关联（经中介传导） | 0 |
| 本体方向矛盾 | 0 |
| 时序领先 (temporal_precedence) | 0 |
| 条件独立支持 (conditional_independence_supported) | 0 |
| 本体一致 (ontology_consistent) | 3 |

### 中介传导通道

未识别出间接传导通道。

### 本体矛盾警示

无。数据方向与本体校验方向一致。

### 可操作性分布

| 可操作性 | 数量 | 占比 |
|----------|------|------|
| 观察性关联（暂非杠杆） | 4 | 50% |
| 混杂（Simpson/群组逆转或时间混淆） | 1 | 12% |

---

### 关系 REL-001: reactor_temp → product_purity

**原始列**: `reactor_temp` → `product_purity`
**可操作性**: 观察性关联（暂非杠杆） (`LEVER_OBSERVATIONAL`)
**关系类型**: supports

| 指标 | 值 |
|------|----|
| 全局相关系数 r | 0.948 |
| 偏相关系数（全阶条件独立） | 0.849 |
| 有效样本量 n | 200 |
| q 值 (BH校正) | 0.0000 |
| 函数形式匹配 |  |
| 因果上限 | 本体一致（物理方向吻合） (`ontology_consistent`) |
| 证据置信度 | 1.00/1.00 |
| LOO 稳定性 | 1.00 |
| 方向验证 | MATCH |
| 物理状态 | plausible |

```json
{
  "claim_id": "REL-001",
  "status": "LEVER_OBSERVATIONAL",
  "source": "reactor_temp->product_purity",
  "mask": "finite + steady (n_eff=200)",
  "n": 200,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": 0.947574,
    "partial_r": 0.849403,
    "slope_at_current": 0.0,
    "lag_aligned_r": 0.944962
  },
  "causal_ceiling": "ontology_consistent",
  "confidence": 1.0,
  "temporal_direction": "concurrent",
  "optimal_lag_steps": 0,
  "direct_association": true,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```

### 关系 REL-002: reactor_temp → catalyst_age

**原始列**: `reactor_temp` → `catalyst_age`
**可操作性**: UNCLASSIFIED (`UNCLASSIFIED`)
**关系类型**: supports

| 指标 | 值 |
|------|----|
| 全局相关系数 r | 0.935 |
| 偏相关系数（全阶条件独立） | 0.00 |
| 有效样本量 n | 200 |
| q 值 (BH校正) | 0.0000 |
| 函数形式匹配 |  |
| 因果上限 | 同期相关 (`contemporaneous_correlation`) |
| 证据置信度 | 0.60/1.00 |

```json
{
  "claim_id": "REL-002",
  "status": "UNCLASSIFIED",
  "source": "reactor_temp->catalyst_age",
  "mask": "finite + steady (n_eff=200)",
  "n": 200,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": 0.93512,
    "partial_r": 0.0,
    "slope_at_current": 0.0,
    "lag_aligned_r": 0.0
  },
  "causal_ceiling": "contemporaneous_correlation",
  "confidence": 0.6,
  "temporal_direction": "concurrent",
  "optimal_lag_steps": 0,
  "direct_association": false,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```

### 关系 REL-003: cooling_flow → catalyst_age

**原始列**: `cooling_flow` → `catalyst_age`
**可操作性**: UNCLASSIFIED (`UNCLASSIFIED`)
**关系类型**: inhibits

| 指标 | 值 |
|------|----|
| 全局相关系数 r | -0.899 |
| 偏相关系数（全阶条件独立） | 0.00 |
| 有效样本量 n | 200 |
| q 值 (BH校正) | 0.0000 |
| 函数形式匹配 |  |
| 因果上限 | 同期相关 (`contemporaneous_correlation`) |
| 证据置信度 | 0.60/1.00 |

```json
{
  "claim_id": "REL-003",
  "status": "UNCLASSIFIED",
  "source": "cooling_flow->catalyst_age",
  "mask": "finite + steady (n_eff=200)",
  "n": 200,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": -0.899113,
    "partial_r": 0.0,
    "slope_at_current": 0.0,
    "lag_aligned_r": 0.0
  },
  "causal_ceiling": "contemporaneous_correlation",
  "confidence": 0.6,
  "temporal_direction": "concurrent",
  "optimal_lag_steps": 0,
  "direct_association": false,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```

### 关系 REL-004: catalyst_age → product_purity

**原始列**: `catalyst_age` → `product_purity`
**可操作性**: 观察性关联（暂非杠杆） (`LEVER_OBSERVATIONAL`)
**关系类型**: supports

| 指标 | 值 |
|------|----|
| 全局相关系数 r | 0.873 |
| 偏相关系数（全阶条件独立） | -0.364 |
| 有效样本量 n | 200 |
| q 值 (BH校正) | 0.0000 |
| 函数形式匹配 |  |
| 因果上限 | 本体一致（物理方向吻合） (`ontology_consistent`) |
| 证据置信度 | 1.00/1.00 |
| LOO 稳定性 | 1.00 |
| 方向验证 | MATCH |
| 物理状态 | plausible |

```json
{
  "claim_id": "REL-004",
  "status": "LEVER_OBSERVATIONAL",
  "source": "catalyst_age->product_purity",
  "mask": "finite + steady (n_eff=200)",
  "n": 200,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": 0.873427,
    "partial_r": -0.363744,
    "slope_at_current": 0.0,
    "lag_aligned_r": 0.87062
  },
  "causal_ceiling": "ontology_consistent",
  "confidence": 1.0,
  "temporal_direction": "concurrent",
  "optimal_lag_steps": 0,
  "direct_association": false,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```

### 关系 REL-005: cooling_flow → product_purity

**原始列**: `cooling_flow` → `product_purity`
**可操作性**: 观察性关联（暂非杠杆） (`LEVER_OBSERVATIONAL`)
**关系类型**: inhibits

| 指标 | 值 |
|------|----|
| 全局相关系数 r | -0.867 |
| 偏相关系数（全阶条件独立） | -0.630 |
| 有效样本量 n | 200 |
| q 值 (BH校正) | 0.0000 |
| 函数形式匹配 |  |
| 因果上限 | 本体一致（物理方向吻合） (`ontology_consistent`) |
| 证据置信度 | 1.00/1.00 |
| LOO 稳定性 | 1.00 |
| 方向验证 | MATCH |
| 物理状态 | plausible |

```json
{
  "claim_id": "REL-005",
  "status": "LEVER_OBSERVATIONAL",
  "source": "cooling_flow->product_purity",
  "mask": "finite + steady (n_eff=200)",
  "n": 200,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": -0.86745,
    "partial_r": -0.629726,
    "slope_at_current": 0.0,
    "lag_aligned_r": -0.863561
  },
  "causal_ceiling": "ontology_consistent",
  "confidence": 1.0,
  "temporal_direction": "concurrent",
  "optimal_lag_steps": 0,
  "direct_association": true,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```

### 关系 REL-006: reactor_temp → cooling_flow

**原始列**: `reactor_temp` → `cooling_flow`
**可操作性**: UNCLASSIFIED (`UNCLASSIFIED`)
**关系类型**: inhibits

| 指标 | 值 |
|------|----|
| 全局相关系数 r | -0.851 |
| 偏相关系数（全阶条件独立） | 0.00 |
| 有效样本量 n | 200 |
| q 值 (BH校正) | 0.0000 |
| 函数形式匹配 |  |
| 因果上限 | 同期相关 (`contemporaneous_correlation`) |
| 证据置信度 | 0.60/1.00 |

```json
{
  "claim_id": "REL-006",
  "status": "UNCLASSIFIED",
  "source": "reactor_temp->cooling_flow",
  "mask": "finite + steady (n_eff=200)",
  "n": 200,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": -0.85091,
    "partial_r": 0.0,
    "slope_at_current": 0.0,
    "lag_aligned_r": 0.0
  },
  "causal_ceiling": "contemporaneous_correlation",
  "confidence": 0.6,
  "temporal_direction": "concurrent",
  "optimal_lag_steps": 0,
  "direct_association": false,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```

### 关系 REL-007: feed_rate → product_purity

**原始列**: `feed_rate` → `product_purity`
**可操作性**: 观察性关联（暂非杠杆） (`LEVER_OBSERVATIONAL`)
**关系类型**: supports

| 指标 | 值 |
|------|----|
| 全局相关系数 r | 0.184 |
| 偏相关系数（全阶条件独立） | 0.00 |
| 有效样本量 n | 198 |
| q 值 (BH校正) | 0.0106 |
| 函数形式匹配 | quadratic curvature detected (R² improvement 0.055); expected: positive_monotonic |
| 因果上限 | 证据不足 (`insufficient_evidence`) |
| 证据置信度 | 0.80/1.00 |
| 时序方向 | 预测变量领先目标变量（最优时滞 3 步, CCF r=-0.261） |
| LOO 稳定性 | 0.99 |
| 方向验证 | MATCH |
| 物理状态 | plausible |

```json
{
  "claim_id": "REL-007",
  "status": "LEVER_OBSERVATIONAL",
  "source": "feed_rate->product_purity",
  "mask": "finite + steady (n_eff=198)",
  "n": 198,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": 0.183948,
    "partial_r": 0.0,
    "slope_at_current": 0.0,
    "lag_aligned_r": -0.250173
  },
  "causal_ceiling": "insufficient_evidence",
  "confidence": 0.8,
  "temporal_direction": "x_leads_y",
  "optimal_lag_steps": 3,
  "direct_association": true,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```

### 关系 REL-008: time_since_product_grade_transition → product_purity

**原始列**: `time_since_product_grade_transition` → `product_purity`
**可操作性**: 混杂（Simpson/群组逆转或时间混淆） (`CONFOUNDED`)
**关系类型**: supports

| 指标 | 值 |
|------|----|
| 全局相关系数 r | 0.029 |
| 偏相关系数（全阶条件独立） | 0.00 |
| 有效样本量 n | 198 |
| q 值 (BH校正) | 0.6798 |
| 函数形式匹配 | no detectable linear relationship; possible nonlinear or delayed_response |
| 因果上限 | 证据不足 (`insufficient_evidence`) |
| 证据置信度 | 0.20/1.00 |
| 时序方向 | 预测变量领先目标变量（最优时滞 1 步, CCF r=0.152） |
| LOO 稳定性 | 0.99 |
| 调节效应 | 关联在分组/工况间方向或强度分歧，不可外推为全局杠杆 |
| 方向验证 | UNTESTED |
| 物理状态 | plausible |

```json
{
  "claim_id": "REL-008",
  "status": "CONFOUNDED",
  "source": "time_since_product_grade_transition->product_purity",
  "mask": "finite + steady (n_eff=198)",
  "n": 198,
  "method": "Pearson r (global; detrended; partial; lag-aligned), q-value BH-corrected; inference: lag-CCF precedence, full-order conditional independence, change-point co-movement, LOO leverage",
  "effect": {
    "global_r": 0.02932,
    "partial_r": 0.0,
    "slope_at_current": 0.0,
    "lag_aligned_r": 0.167119
  },
  "causal_ceiling": "insufficient_evidence",
  "confidence": 0.2,
  "temporal_direction": "x_leads_y",
  "optimal_lag_steps": 1,
  "direct_association": false,
  "indirect_association": false,
  "mediator_candidates": [],
  "ontology_contradiction": false,
  "not_for": "直接因果推断（无随机对照实验）"
}
```


---

## 9. 物理机理链

从诊断推理中提取并通过物理桥接验证的机理链，共 1 条。

### MC-001

**主张**: : 

**置信度**: 证据强度=未知, 函数形态验证=未知, 方向验证=未知



---

## 10. 参数权衡矩阵

共 5 个参数在多目标间的权衡关系。

### 参数: catalyst_age

- **可控性**: directly controllable via process setpoint adjustment
- **可操作性**: 观察性关联（暂非杠杆）
- **支持域**: p5=11.00, p95=28.90, current=26.70, n=200
- **对各目标的影响**:
  - catalyst_age: positive effect on product_purity (r=0.873)

### 参数: cooling_flow

- **可控性**: directly controllable via process setpoint adjustment
- **可操作性**: 观察性关联（暂非杠杆）
- **支持域**: p5=39.98, p95=50.70, current=43.50, n=200
- **对各目标的影响**:
  - cooling_flow: negative effect on product_purity (r=-0.867)

### 参数: feed_rate

- **可控性**: directly controllable via process setpoint adjustment
- **可操作性**: 观察性关联（暂非杠杆）
- **支持域**: p5=96.00, p95=103.91, current=102.80, n=200
- **对各目标的影响**:
  - feed_rate: positive effect on product_purity (r=0.184)

### 参数: reactor_temp

- **可控性**: directly controllable via process setpoint adjustment
- **可操作性**: 观察性关联（暂非杠杆）
- **支持域**: p5=80.59, p95=100.01, current=96.50, n=200
- **对各目标的影响**:
  - reactor_temp: positive effect on product_purity (r=0.948)

### 参数: time_since_product_grade_transition

- **可控性**: directly controllable via process setpoint adjustment
- **可操作性**: 混杂（Simpson/群组逆转或时间混淆）
- **支持域**: p5=21.00, p95=630.00, current=663.00, n=200
- **对各目标的影响**:
  - time_since_product_grade_transition: positive effect on product_purity (r=0.029)


---

## 11. 可操作性综合评估

1 个关系受混杂因素影响（Simpson/群组逆转或未解决的时间混淆）。

### 详细分布

| 可操作性 | 数量 | 占比 |
|----------|------|------|
| 观察性关联（暂非杠杆） | 4 | 50% |
| 混杂（Simpson/群组逆转或时间混淆） | 1 | 12% |

---

## 12. 待解决问题

当前分析阶段未解决的关键问题，共 3 项。

- **Q1** [minor]: 建议在投入运行前做进一步机制验证。
  - 潜在影响: Informs parameter optimization strategy
- **Q2** [minor]: 存在混杂：因果识别需分层分析或受控实验。
  - 潜在影响: Informs parameter optimization strategy
- **Q3** [minor]: 调节效应：product_purity 关联在 product_grade 分组间方向相反，关联随工况/分组改变，不可外推为全局杠杆。
  - 潜在影响: Informs parameter optimization strategy

---

## 13. 证据缺口

当前证据体系中识别出的缺口，共 ${n_evidence_gaps} 项。

无证据缺口。

---

## 14. 附录：增强知识概要

以下为 `enhanced_knowledge.json` 的压缩视图，包含本文档中所有数据的机器可读表示。

```json
{
  "run_id": "enhancement-deep-analysis",
  "enhancement_status": "READY",
  "relationship_graph": {
    "nodes": [
      {
        "id": "timestamp",
        "label": "timestamp",
        "type": "parameter",
        "unit": "metadata",
        "role": "unknown",
        "coverage_status": "not_applicable",
        "support_domain": {
          "p5": 0.0,
          "p25": 0.0,
          "p50": 0.0,
          "p75": 0.0,
          "p95": 0.0,
          "n": 1,
          "current_median": 0.0
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "reactor_temp",
        "label": "reactor_temp",
        "type": "parameter",
        "unit": "dimensionless",
        "role": "predictor",
        "coverage_status": "covered_primary",
        "support_domain": {
          "p5": 80.595,
          "p25": 84.675,
          "p50": 89.7,
          "p75": 94.97500000000001,
          "p95": 100.00999999999999,
          "n": 200,
          "current_median": 89.7
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "feed_rate",
        "label": "feed_rate",
        "type": "parameter",
        "unit": "dimensionless",
        "role": "predictor",
        "coverage_status": "covered_primary",
        "support_domain": {
          "p5": 96.0,
          "p25": 97.1,
          "p50": 99.9,
          "p75": 102.8,
          "p95": 103.905,
          "n": 200,
          "current_median": 99.9
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "cooling_flow",
        "label": "cooling_flow",
        "type": "parameter",
        "unit": "dimensionless",
        "role": "predictor",
        "coverage_status": "covered_primary",
        "support_domain": {
          "p5": 39.985,
          "p25": 42.45,
          "p50": 45.2,
          "p75": 47.525,
          "p95": 50.705,
          "n": 200,
          "current_median": 45.2
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "catalyst_age",
        "label": "catalyst_age",
        "type": "parameter",
        "unit": "dimensionless",
        "role": "predictor",
        "coverage_status": "covered_primary",
        "support_domain": {
          "p5": 10.995000000000001,
          "p25": 14.975,
          "p50": 19.95,
          "p75": 24.924999999999997,
          "p95": 28.904999999999998,
          "n": 200,
          "current_median": 19.95
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "product_purity",
        "label": "product_purity",
        "type": "target",
        "unit": "dimensionless",
        "role": "target",
        "coverage_status": "covered_primary",
        "support_domain": {
          "p5": 95.226,
          "p25": 96.8925,
          "p50": 98.98,
          "p75": 100.9475,
          "p95": 102.755,
          "n": 200,
          "current_median": 98.98
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "product_grade",
        "label": "product_grade",
        "type": "parameter",
        "unit": "metadata",
        "role": "unknown",
        "coverage_status": "not_applicable",
        "support_domain": {
          "p5": 0.0,
          "p25": 0.0,
          "p50": 0.0,
          "p75": 0.0,
          "p95": 0.0,
          "n": 1,
          "current_median": 0.0
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "reactor_temp_dev",
        "label": "reactor_temp_dev",
        "type": "parameter",
        "unit": "metadata",
        "role": "derived_deviation",
        "coverage_status": "derived_and_used",
        "support_domain": {
          "p5": 0.0,
          "p25": 0.0,
          "p50": 0.0,
          "p75": 0.0,
          "p95": 0.0,
          "n": 1,
          "current_median": 0.0
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "cooling_flow_dev",
        "label": "cooling_flow_dev",
        "type": "parameter",
        "unit": "metadata",
        "role": "derived_deviation",
        "coverage_status": "derived_and_used",
        "support_domain": {
          "p5": 0.0,
          "p25": 0.0,
          "p50": 0.0,
          "p75": 0.0,
          "p95": 0.0,
          "n": 1,
          "current_median": 0.0
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "catalyst_age_dev",
        "label": "catalyst_age_dev",
        "type": "parameter",
        "unit": "metadata",
        "role": "derived_deviation",
        "coverage_status": "derived_and_used",
        "support_domain": {
          "p5": 0.0,
          "p25": 0.0,
          "p50": 0.0,
          "p75": 0.0,
          "p95": 0.0,
          "n": 1,
          "current_median": 0.0
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "product_purity_dev",
        "label": "product_purity_dev",
        "type": "parameter",
        "unit": "metadata",
        "role": "derived_deviation",
        "coverage_status": "derived_and_used",
        "support_domain": {
          "p5": 0.0,
          "p25": 0.0,
          "p50": 0.0,
          "p75": 0.0,
          "p95": 0.0,
          "n": 1,
          "current_median": 0.0
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "time_hours",
        "label": "time_hours",
        "type": "parameter",
        "unit": "metadata",
        "role": "derived_time",
        "coverage_status": "not_applicable",
        "support_domain": {
          "p5": 0.0,
          "p25": 0.0,
          "p50": 0.0,
          "p75": 0.0,
          "p95": 0.0,
          "n": 1,
          "current_median": 0.0
        },
        "physics_ref": "NOT_APPLICABLE"
      },
      {
        "id": "cumulative_exposure",
        "label": "cumulative_exposure",
        "type": "derived",
        "unit": "dimensionless*time",
        "role": "derived_feature",
        "formula": "∫ C dt over sorted time",
        "source_columns": [
          "(none — no driver column detected)"
        ],
        "status": "not_applicable"
      },
      {
        "id": "time_since_product_grade_transition",
        "label": "time_since_product_grade_transition",
        "type": "derived",
        "unit": "hours",
        "role": "derived_feature",
        "formula": "time since product_grade group transition (hours)",
        "source_columns": [
          "product_grade",
          "timestamp"
        ],
        "status": "computed"
      },
      {
        "id": "regime_steady",
        "label": "regime_steady",
        "type": "derived",
        "unit": "binary",
        "role": "derived_feature",
        "formula": "indicator(steady) from production_regime_filter",
        "source_columns": [
          "production_regime_filter.per_row_labels"
        ],
        "status": "computed"
      },
      {
        "id": "regime_transition",
        "label": "regime_transition",
        "type": "derived",
        "unit": "binary",
        "role": "derived_feature",
        "formula": "indicator(transition) from production_regime_filter",
        "source_columns": [
          "production_regime_filter.per_row_labels"
        ],
        "status": "computed"
      },
      {
        "id": "lag_aligned_feature",
        "label": "lag_aligned_feature",
        "type": "derived",
        "unit": "same_as_source",
        "role": "derived_feature",
        "formula": "predictor shifted by optimal_lag_steps",
        "source_columns": [],
        "status": "not_applicable"
      }
    ],
    "edges": [
      {
        "source": "reactor_temp",
        "target": "product_purity",
        "relationship": "supports",
        "strength": 0.947574,
        "sign": 1,
        "confidence": 1.0,
        "causal_ceiling": "ontology_consistent",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": 0.947574,
          "p_value": 1e-300,
          "p_floor_hit": true,
          "detrended_r": 0.0,
          "partial_r": 0.849403,
          "partial_method": "full_order_ridge",
          "temporal_direction": "concurrent",
          "optimal_lag_steps": 0,
          "ccf_peak_r": 0.948481,
          "lag_aligned_r": 0.944962,
          "direct_association": true,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.998888,
          "interaction_flagged": false,
          "slope_at_current": 0.0,
          "form_match": "",
          "q_value": 0.0,
          "n_effective": 200
        },
        "physics_verification": {
          "direction": "MATCH",
          "functional_form": "MATCH",
          "time_lag": "MATCH",
          "magnitude": "UNTESTED",
          "state_dependence": "STABLE",
          "overall_status": "plausible"
        },
        "operability": "LEVER_OBSERVATIONAL",
        "evidence_ref": "deep_data.reactor_temp_to_product_purity.global_r=0.9476, deep_data.reactor_temp_to_product_purity.detrended_r=0.9495, deep_data.reactor_temp_to_product_purity.form_match: consistent with linear/monotonic; expected: positive_monotonic",
        "validity_flags": {
          "simpson_paradox_checked": true,
          "confounding_checked": true,
          "trend_confounding_checked": true,
          "change_point_tested": true,
          "batch_effect_tested": true,
          "lag_significant": false,
          "outlier_influence_checked": true,
          "insufficient_data": false
        }
      },
      {
        "source": "reactor_temp",
        "target": "catalyst_age",
        "relationship": "supports",
        "strength": 0.93512,
        "sign": 1,
        "confidence": 0.6,
        "causal_ceiling": "contemporaneous_correlation",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": 0.93512,
          "p_value": 1e-300,
          "p_floor_hit": true,
          "detrended_r": 0.0,
          "partial_r": 0.0,
          "partial_method": "",
          "temporal_direction": "concurrent",
          "optimal_lag_steps": 0,
          "ccf_peak_r": 0.0,
          "lag_aligned_r": 0.0,
          "direct_association": false,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.0,
          "interaction_flagged": false,
          "slope_at_current": 0.0,
          "form_match": "",
          "q_value": 0.0,
          "n_effective": 200
        },
        "physics_verification": {},
        "operability": "UNCLASSIFIED",
        "evidence_ref": "",
        "validity_flags": {}
      },
      {
        "source": "cooling_flow",
        "target": "catalyst_age",
        "relationship": "inhibits",
        "strength": -0.899113,
        "sign": -1,
        "confidence": 0.6,
        "causal_ceiling": "contemporaneous_correlation",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": -0.899113,
          "p_value": 1.0738750122918625e-183,
          "p_floor_hit": false,
          "detrended_r": 0.0,
          "partial_r": 0.0,
          "partial_method": "",
          "temporal_direction": "concurrent",
          "optimal_lag_steps": 0,
          "ccf_peak_r": 0.0,
          "lag_aligned_r": 0.0,
          "direct_association": false,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.0,
          "interaction_flagged": false,
          "slope_at_current": 0.0,
          "form_match": "",
          "q_value": 0.0,
          "n_effective": 200
        },
        "physics_verification": {},
        "operability": "UNCLASSIFIED",
        "evidence_ref": "",
        "validity_flags": {}
      },
      {
        "source": "catalyst_age",
        "target": "product_purity",
        "relationship": "supports",
        "strength": 0.873427,
        "sign": 1,
        "confidence": 1.0,
        "causal_ceiling": "ontology_consistent",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": 0.873427,
          "p_value": 1.5013857780947227e-140,
          "p_floor_hit": false,
          "detrended_r": 0.0,
          "partial_r": -0.363744,
          "partial_method": "full_order_ridge",
          "temporal_direction": "concurrent",
          "optimal_lag_steps": 0,
          "ccf_peak_r": 0.874541,
          "lag_aligned_r": 0.87062,
          "direct_association": false,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.997444,
          "interaction_flagged": false,
          "slope_at_current": 0.0,
          "form_match": "",
          "q_value": 0.0,
          "n_effective": 200
        },
        "physics_verification": {
          "direction": "MATCH",
          "functional_form": "MATCH",
          "time_lag": "MATCH",
          "magnitude": "UNTESTED",
          "state_dependence": "STABLE",
          "overall_status": "plausible"
        },
        "operability": "LEVER_OBSERVATIONAL",
        "evidence_ref": "deep_data.catalyst_age_to_product_purity.global_r=0.8734, deep_data.catalyst_age_to_product_purity.detrended_r=0.8764, deep_data.catalyst_age_to_product_purity.form_match: consistent with linear/monotonic; expected: negative_monotonic",
        "validity_flags": {
          "simpson_paradox_checked": true,
          "confounding_checked": true,
          "trend_confounding_checked": true,
          "change_point_tested": true,
          "batch_effect_tested": true,
          "lag_significant": false,
          "outlier_influence_checked": true,
          "insufficient_data": false
        }
      },
      {
        "source": "cooling_flow",
        "target": "product_purity",
        "relationship": "inhibits",
        "strength": -0.86745,
        "sign": -1,
        "confidence": 1.0,
        "causal_ceiling": "ontology_consistent",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": -0.86745,
          "p_value": 6.466056739280218e-133,
          "p_floor_hit": false,
          "detrended_r": 0.0,
          "partial_r": -0.629726,
          "partial_method": "full_order_ridge",
          "temporal_direction": "concurrent",
          "optimal_lag_steps": 0,
          "ccf_peak_r": -0.867749,
          "lag_aligned_r": -0.863561,
          "direct_association": true,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.997336,
          "interaction_flagged": false,
          "slope_at_current": 0.0,
          "form_match": "",
          "q_value": 0.0,
          "n_effective": 200
        },
        "physics_verification": {
          "direction": "MATCH",
          "functional_form": "MATCH",
          "time_lag": "MATCH",
          "magnitude": "UNTESTED",
          "state_dependence": "STABLE",
          "overall_status": "plausible"
        },
        "operability": "LEVER_OBSERVATIONAL",
        "evidence_ref": "deep_data.cooling_flow_to_product_purity.global_r=-0.8675, deep_data.cooling_flow_to_product_purity.detrended_r=-0.8791, deep_data.cooling_flow_to_product_purity.form_match: consistent with linear/monotonic; expected: negative_monotonic",
        "validity_flags": {
          "simpson_paradox_checked": true,
          "confounding_checked": true,
          "trend_confounding_checked": true,
          "change_point_tested": true,
          "batch_effect_tested": true,
          "lag_significant": false,
          "outlier_influence_checked": true,
          "insufficient_data": false
        }
      },
      {
        "source": "reactor_temp",
        "target": "cooling_flow",
        "relationship": "inhibits",
        "strength": -0.85091,
        "sign": -1,
        "confidence": 0.6,
        "causal_ceiling": "contemporaneous_correlation",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": -0.85091,
          "p_value": 5.398129626160644e-115,
          "p_floor_hit": false,
          "detrended_r": 0.0,
          "partial_r": 0.0,
          "partial_method": "",
          "temporal_direction": "concurrent",
          "optimal_lag_steps": 0,
          "ccf_peak_r": 0.0,
          "lag_aligned_r": 0.0,
          "direct_association": false,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.0,
          "interaction_flagged": false,
          "slope_at_current": 0.0,
          "form_match": "",
          "q_value": 0.0,
          "n_effective": 200
        },
        "physics_verification": {},
        "operability": "UNCLASSIFIED",
        "evidence_ref": "",
        "validity_flags": {}
      },
      {
        "source": "feed_rate",
        "target": "product_purity",
        "relationship": "supports",
        "strength": 0.183948,
        "sign": 1,
        "confidence": 0.8,
        "causal_ceiling": "insufficient_evidence",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": 0.183948,
          "p_value": 0.008455567344463906,
          "p_floor_hit": false,
          "detrended_r": 0.146866,
          "partial_r": 0.0,
          "partial_method": "full_order_ridge",
          "temporal_direction": "x_leads_y",
          "optimal_lag_steps": 3,
          "ccf_peak_r": -0.26129,
          "lag_aligned_r": -0.250173,
          "direct_association": true,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.98893,
          "interaction_flagged": false,
          "slope_at_current": 0.0,
          "form_match": "quadratic curvature detected (R² improvement 0.055); expected: positive_monotonic",
          "q_value": 0.010569,
          "n_effective": 198
        },
        "physics_verification": {
          "direction": "MATCH",
          "functional_form": "MATCH",
          "time_lag": "MISMATCH",
          "magnitude": "UNTESTED",
          "state_dependence": "STABLE",
          "overall_status": "plausible"
        },
        "operability": "LEVER_OBSERVATIONAL",
        "evidence_ref": "deep_data.feed_rate_to_product_purity.global_r=0.1839, deep_data.feed_rate_to_product_purity.detrended_r=0.1469, deep_data.feed_rate_to_product_purity.form_match: quadratic curvature detected (R² improvement 0.055); expected: positive_monotonic",
        "validity_flags": {
          "simpson_paradox_checked": true,
          "confounding_checked": true,
          "trend_confounding_checked": true,
          "change_point_tested": true,
          "batch_effect_tested": true,
          "lag_significant": true,
          "outlier_influence_checked": true,
          "insufficient_data": false
        }
      },
      {
        "source": "time_since_product_grade_transition",
        "target": "product_purity",
        "relationship": "supports",
        "strength": 0.02932,
        "sign": 1,
        "confidence": 0.2,
        "causal_ceiling": "insufficient_evidence",
        "ontology_contradiction": false,
        "statistical_evidence": {
          "global_r": 0.02932,
          "p_value": 0.6797947973333875,
          "p_floor_hit": false,
          "detrended_r": 0.069859,
          "partial_r": 0.0,
          "partial_method": "full_order_ridge",
          "temporal_direction": "x_leads_y",
          "optimal_lag_steps": 1,
          "ccf_peak_r": 0.151584,
          "lag_aligned_r": 0.167119,
          "direct_association": false,
          "indirect_association": false,
          "mediator_candidates": [],
          "change_point_co_movement": 0.0,
          "loo_stability": 0.988271,
          "interaction_flagged": true,
          "slope_at_current": 0.0,
          "form_match": "no detectable linear relationship; possible nonlinear or delayed_response",
          "q_value": 0.679795,
          "n_effective": 198
        },
        "physics_verification": {
          "direction": "UNTESTED",
          "functional_form": "UNTESTED",
          "time_lag": "UNTESTED",
          "magnitude": "UNTESTED",
          "state_dependence": "REVERSES",
          "overall_status": "plausible"
        },
        "operability": "CONFOUNDED",
        "evidence_ref": "deep_data.time_since_product_grade_transition_to_product_purity.global_r=0.0293, deep_data.time_since_product_grade_transition_to_product_purity.detrended_r=0.0699, deep_data.time_since_product_grade_transition_to_product_purity.form_match: no detectable linear relationship; possible nonlinear or delayed_response",
        "validity_flags": {
          "simpson_paradox_checked": true,
          "confounding_checked": true,
          "trend_confounding_checked": true,
          "change_point_tested": true,
          "batch_effect_tested": true,
          "lag_significant": true,
          "outlier_influence_checked": true,
          "insufficient_data": false
        }
      }
    ]
  },
  "causal_pathways": [
    {
      "path": [
        "reactor_temp",
        "product_purity"
      ],
      "start": "reactor_temp",
      "end": "product_purity",
      "path_length": 1,
      "total_strength": 0.9476,
      "min_confidence": 1.0,
      "edges": [
        {
          "from": "reactor_temp",
          "to": "product_purity",
          "strength": 0.947574,
          "relationship": "supports",
          "confidence": 1.0,
          "physics_verified": false
        }
      ]
    },
    {
      "path": [
        "catalyst_age",
        "product_purity"
      ],
      "start": "catalyst_age",
      "end": "product_purity",
      "path_length": 1,
      "total_strength": 0.8734,
      "min_confidence": 1.0,
      "edges": [
        {
          "from": "catalyst_age",
          "to": "product_purity",
          "strength": 0.873427,
          "relationship": "supports",
          "confidence": 1.0,
          "physics_verified": false
        }
      ]
    },
    {
      "path": [
        "cooling_flow",
        "product_purity"
      ],
      "start": "cooling_flow",
      "end": "product_purity",
      "path_length": 1,
      "total_strength": 0.8675,
      "min_confidence": 1.0,
      "edges": [
        {
          "from": "cooling_flow",
          "to": "product_purity",
          "strength": -0.86745,
          "relationship": "inhibits",
          "confidence": 1.0,
          "physics_verified": false
        }
      ]
    },
    {
      "path": [
        "reactor_temp",
        "catalyst_age",
        "product_purity"
      ],
      "start": "reactor_temp",
      "end": "product_purity",
      "path_length": 2,
      "total_strength": 0.8168,
      "min_confidence": 0.6,
      "edges": [
        {
          "from": "reactor_temp",
          "to": "catalyst_age",
          "strength": 0.93512,
          "relationship": "supports",
          "confidence": 0.6,
          "physics_verified": false
        },
        {
          "from": "catalyst_age",
          "to": "product_purity",
          "strength": 0.873427,
          "relationship": "supports",
          "confidence": 1.0,
          "physics_verified": false
        }
      ]
    },
    {
      "path": [
        "cooling_flow",
        "catalyst_age",
        "product_purity"
      ],
      "start": "cooling_flow",
      "end": "product_purity",
      "path_length": 2,
      "total_strength": 0.7853,
      "min_confidence": 0.6,
      "edges": [
        {
          "from": "cooling_flow",
          "to": "catalyst_age",
          "strength": -0.899113,
          "relationship": "inhibits",
          "confidence": 0.6,
          "physics_verified": false
        },
        {
          "from": "catalyst_age",
          "to": "product_purity",
          "strength": 0.873427,
          "relationship": "supports",
          "confidence": 1.0,
          "physics_verified": false
        }
      ]
    },
    {
      "path": [
        "reactor_temp",
        "cooling_flow",
        "product_purity"
      ],
      "start": "reactor_temp",
      "end": "product_purity",
      "path_length": 2,
      "total_strength": 0.7381,
      "min_confidence": 0.6,
      "edges": [
        {
          "from": "reactor_temp",
          "to": "cooling_flow",
          "strength": -0.85091,
          "relationship": "inhibits",
          "confidence": 0.6,
          "physics_verified": false
        },
        {
          "from": "cooling_flow",
          "to": "product_purity",
          "strength": -0.86745,
          "relationship": "inhibits",
          "confidence": 1.0,
          "physics_verified": false
        }
      ]
    },
    {
      "path": [
        "reactor_temp",
        "cooling_flow",
        "catalyst_age",
        "product_purity"
      ],
      "start": "reactor_temp",
      "end": "product_purity",
      "path_length": 3,
      "total_strength": 0.6682,
      "min_confidence": 0.6,
      "edges": [
        {
          "from": "reactor_temp",
          "to": "cooling_flow",
          "strength": -0.85091,
          "relationship": "inhibits",
          "confidence": 0.6,
          "physics_verified": false
        },
        {
          "from": "cooling_flow",
          "to": "catalyst_age",
          "strength": -0.899113,
          "relationship": "inhibits",
          "confidence": 0.6,
          "physics_verified": false
        },
        {
          "from": "catalyst_age",
          "to": "product_purity",
          "strength": 0.873427,
          "relationship": "supports",
          "confidence": 1.0,
          "physics_verified": false
        }
      ]
    }
  ],
  "parameter_centrality": [
    {
      "parameter": "reactor_temp",
      "role": "predictor",
      "type": "parameter",
      "out_degree": 3,
      "in_degree": 0,
      "influence_score": 2.7336,
      "is_hub": true,
      "downstream_targets": [
        "product_purity"
      ],
      "unit": "dimensionless",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "cooling_flow",
      "role": "predictor",
      "type": "parameter",
      "out_degree": 2,
      "in_degree": 1,
      "influence_score": 1.7666,
      "is_hub": true,
      "downstream_targets": [
        "product_purity"
      ],
      "unit": "dimensionless",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "catalyst_age",
      "role": "predictor",
      "type": "parameter",
      "out_degree": 1,
      "in_degree": 2,
      "influence_score": 0.8734,
      "is_hub": false,
      "downstream_targets": [
        "product_purity"
      ],
      "unit": "dimensionless",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "feed_rate",
      "role": "predictor",
      "type": "parameter",
      "out_degree": 1,
      "in_degree": 0,
      "influence_score": 0.1839,
      "is_hub": false,
      "downstream_targets": [
        "product_purity"
      ],
      "unit": "dimensionless",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "time_since_product_grade_transition",
      "role": "derived_feature",
      "type": "derived",
      "out_degree": 1,
      "in_degree": 0,
      "influence_score": 0.0293,
      "is_hub": false,
      "downstream_targets": [
        "product_purity"
      ],
      "unit": "hours",
      "physics_ref": ""
    },
    {
      "parameter": "timestamp",
      "role": "unknown",
      "type": "parameter",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "metadata",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "product_purity",
      "role": "target",
      "type": "target",
      "out_degree": 0,
      "in_degree": 5,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "dimensionless",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "product_grade",
      "role": "unknown",
      "type": "parameter",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "metadata",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "reactor_temp_dev",
      "role": "derived_deviation",
      "type": "parameter",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "metadata",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "cooling_flow_dev",
      "role": "derived_deviation",
      "type": "parameter",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "metadata",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "catalyst_age_dev",
      "role": "derived_deviation",
      "type": "parameter",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "metadata",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "product_purity_dev",
      "role": "derived_deviation",
      "type": "parameter",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "metadata",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "time_hours",
      "role": "derived_time",
      "type": "parameter",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "metadata",
      "physics_ref": "NOT_APPLICABLE"
    },
    {
      "parameter": "cumulative_exposure",
      "role": "derived_feature",
      "type": "derived",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "dimensionless*time",
      "physics_ref": ""
    },
    {
      "parameter": "regime_steady",
      "role": "derived_feature",
      "type": "derived",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "binary",
      "physics_ref": ""
    },
    {
      "parameter": "regime_transition",
      "role": "derived_feature",
      "type": "derived",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "binary",
      "physics_ref": ""
    },
    {
      "parameter": "lag_aligned_feature",
      "role": "derived_feature",
      "type": "derived",
      "out_degree": 0,
      "in_degree": 0,
      "influence_score": 0,
      "is_hub": false,
      "downstream_targets": [],
      "unit": "same_as_source",
      "physics_ref": ""
    }
  ],
  "control_levers": [
    {
      "parameter": "reactor_temp",
      "physical_meaning": "反应器温度",
      "unit": "°C",
      "current_value": 89.7,
      "support_domain": {
        "p5": 80.595,
        "p25": 84.675,
        "p50": 89.7,
        "p75": 94.97500000000001,
        "p95": 100.00999999999999,
        "n": 200,
        "current_median": 89.7
      },
      "controllable": true,
      "operability": [
        "LEVER_OBSERVATIONAL",
        "UNCLASSIFIED"
      ],
      "downstream_effects": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.9476,
          "slope_at_current": 0.0,
          "confidence": 1.0,
          "physics_verified": false,
          "physics_status": "plausible",
          "causal_ceiling": "ontology_consistent",
          "q_value": 0.0,
          "n_effective": 200,
          "temporal_direction": "concurrent"
        }
      ],
      "overall_confidence": 1.0,
      "risk_factors": [
        "None identified"
      ],
      "equipment_stage": "reactor"
    },
    {
      "parameter": "cooling_flow",
      "physical_meaning": "冷却水流量",
      "unit": "L/min",
      "current_value": 45.2,
      "support_domain": {
        "p5": 39.985,
        "p25": 42.45,
        "p50": 45.2,
        "p75": 47.525,
        "p95": 50.705,
        "n": 200,
        "current_median": 45.2
      },
      "controllable": true,
      "operability": [
        "LEVER_OBSERVATIONAL",
        "UNCLASSIFIED"
      ],
      "downstream_effects": [
        {
          "target": "product_purity",
          "direction": "decrease",
          "strength": -0.8675,
          "slope_at_current": 0.0,
          "confidence": 1.0,
          "physics_verified": false,
          "physics_status": "plausible",
          "causal_ceiling": "ontology_consistent",
          "q_value": 0.0,
          "n_effective": 200,
          "temporal_direction": "concurrent"
        }
      ],
      "overall_confidence": 1.0,
      "risk_factors": [
        "None identified"
      ],
      "equipment_stage": "cooling"
    },
    {
      "parameter": "catalyst_age",
      "physical_meaning": "催化剂使用时长",
      "unit": "h",
      "current_value": 19.95,
      "support_domain": {
        "p5": 10.995000000000001,
        "p25": 14.975,
        "p50": 19.95,
        "p75": 24.924999999999997,
        "p95": 28.904999999999998,
        "n": 200,
        "current_median": 19.95
      },
      "controllable": true,
      "operability": [
        "LEVER_OBSERVATIONAL"
      ],
      "downstream_effects": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.8734,
          "slope_at_current": 0.0,
          "confidence": 1.0,
          "physics_verified": false,
          "physics_status": "plausible",
          "causal_ceiling": "ontology_consistent",
          "q_value": 0.0,
          "n_effective": 200,
          "temporal_direction": "concurrent"
        }
      ],
      "overall_confidence": 1.0,
      "risk_factors": [
        "None identified"
      ],
      "equipment_stage": "reactor"
    },
    {
      "parameter": "feed_rate",
      "physical_meaning": "进料流量",
      "unit": "kg/h",
      "current_value": 99.9,
      "support_domain": {
        "p5": 96.0,
        "p25": 97.1,
        "p50": 99.9,
        "p75": 102.8,
        "p95": 103.905,
        "n": 200,
        "current_median": 99.9
      },
      "controllable": true,
      "operability": [
        "LEVER_OBSERVATIONAL"
      ],
      "downstream_effects": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.1839,
          "slope_at_current": 0.0,
          "confidence": 0.8,
          "physics_verified": false,
          "physics_status": "plausible",
          "causal_ceiling": "insufficient_evidence",
          "q_value": 0.010569,
          "n_effective": 198,
          "temporal_direction": "x_leads_y"
        }
      ],
      "overall_confidence": 0.8,
      "risk_factors": [
        "None identified"
      ],
      "equipment_stage": "feed"
    },
    {
      "parameter": "time_since_product_grade_transition",
      "physical_meaning": "",
      "unit": "hours",
      "current_value": null,
      "support_domain": {},
      "controllable": false,
      "operability": [
        "CONFOUNDED"
      ],
      "downstream_effects": [
        {
          "target": "product_purity",
          "direction": "increase",
          "strength": 0.0293,
          "slope_at_current": 0.0,
          "confidence": 0.2,
          "physics_verified": false,
          "physics_status": "plausible",
          "causal_ceiling": "insufficient_evidence",
          "q_value": 0.679795,
          "n_effective": 198,
          "temporal_direction": "x_leads_y"
        }
      ],
      "overall_confidence": 0.2,
      "risk_factors": [
        "Confounder present for product_purity",
        "Interaction/moderation effect on product_purity"
      ],
      "equipment_stage": ""
    }
  ],
  "physical_context": {
    "timestamp": {
      "physical_meaning": "时间戳",
      "unit": "datetime",
      "role": "metadata",
      "equipment_stage": "",
      "governing_law": "",
      "expected_behavior": "",
      "controllable": false
    },
    "reactor_temp": {
      "physical_meaning": "反应器温度",
      "unit": "°C",
      "role": "process_parameter",
      "equipment_stage": "reactor",
      "governing_law": "Arrhenius: k=A·exp(-Ea/RT)",
      "expected_behavior": "",
      "controllable": true
    },
    "feed_rate": {
      "physical_meaning": "进料流量",
      "unit": "kg/h",
      "role": "process_parameter",
      "equipment_stage": "feed",
      "governing_law": "",
      "expected_behavior": "",
      "controllable": true
    },
    "cooling_flow": {
      "physical_meaning": "冷却水流量",
      "unit": "L/min",
      "role": "process_parameter",
      "equipment_stage": "cooling",
      "governing_law": "Q=m·c·ΔT",
      "expected_behavior": "",
      "controllable": true
    },
    "catalyst_age": {
      "physical_meaning": "催化剂使用时长",
      "unit": "h",
      "role": "process_parameter",
      "equipment_stage": "reactor",
      "governing_law": "",
      "expected_behavior": "",
      "controllable": false
    },
    "product_purity": {
      "physical_meaning": "产品纯度",
      "unit": "%",
      "role": "quality_target",
      "equipment_stage": "",
      "governing_law": "",
      "expected_behavior": "",
      "controllable": false
    },
    "product_grade": {
      "physical_meaning": "产品等级",
      "unit": "category",
      "role": "grouping",
      "equipment_stage": "",
      "governing_law": "",
      "expected_behavior": "",
      "controllable": false
    },
    "reactor_temp_dev": {
      "physical_meaning": "NOT_APPLICABLE",
      "unit": "metadata",
      "role": "derived_deviation",
      "support_domain": {
        "p5": 0.0,
        "p25": 0.0,
        "p50": 0.0,
        "p75": 0.0,
        "p95": 0.0,
        "n": 1,
        "current_median": 0.0
      }
    },
    "cooling_flow_dev": {
      "physical_meaning": "NOT_APPLICABLE",
      "unit": "metadata",
      "role": "derived_deviation",
      "support_domain": {
        "p5": 0.0,
        "p25": 0.0,
        "p50": 0.0,
        "p75": 0.0,
        "p95": 0.0,
        "n": 1,
        "current_median": 0.0
      }
    },
    "catalyst_age_dev": {
      "physical_meaning": "NOT_APPLICABLE",
      "unit": "metadata",
      "role": "derived_deviation",
      "support_domain": {
        "p5": 0.0,
        "p25": 0.0,
        "p50": 0.0,
        "p75": 0.0,
        "p95": 0.0,
        "n": 1,
        "current_median": 0.0
      }
    },
    "product_purity_dev": {
      "physical_meaning": "NOT_APPLICABLE",
      "unit": "metadata",
      "role": "derived_deviation",
      "support_domain": {
        "p5": 0.0,
        "p25": 0.0,
        "p50": 0.0,
        "p75": 0.0,
        "p95": 0.0,
        "n": 1,
        "current_median": 0.0
      }
    },
    "time_hours": {
      "physical_meaning": "NOT_APPLICABLE",
      "unit": "metadata",
      "role": "derived_time",
      "support_domain": {
        "p5": 0.0,
        "p25": 0.0,
        "p50": 0.0,
        "p75": 0.0,
        "p95": 0.0,
        "n": 1,
        "current_median": 0.0
      }
    }
  },
  "mechanism_chains": [
    {
      "chain_id": "MC-001",
      "claim": ": ",
      "confidence": "证据强度=未知, 函数形态验证=未知, 方向验证=未知",
      "evidence_refs": []
    }
  ],
  "tradeoff_matrix": [
    {
      "parameter": "catalyst_age",
      "controllability": "directly controllable via process setpoint adjustment",
      "operability": "LEVER_OBSERVATIONAL",
      "effects": {
        "catalyst_age": "positive effect on product_purity (r=0.873)"
      },
      "support_domain": "p5=11.00, p95=28.90, current=26.70, n=200"
    },
    {
      "parameter": "cooling_flow",
      "controllability": "directly controllable via process setpoint adjustment",
      "operability": "LEVER_OBSERVATIONAL",
      "effects": {
        "cooling_flow": "negative effect on product_purity (r=-0.867)"
      },
      "support_domain": "p5=39.98, p95=50.70, current=43.50, n=200"
    },
    {
      "parameter": "feed_rate",
      "controllability": "directly controllable via process setpoint adjustment",
      "operability": "LEVER_OBSERVATIONAL",
      "effects": {
        "feed_rate": "positive effect on product_purity (r=0.184)"
      },
      "support_domain": "p5=96.00, p95=103.91, current=102.80, n=200"
    },
    {
      "parameter": "reactor_temp",
      "controllability": "directly controllable via process setpoint adjustment",
      "operability": "LEVER_OBSERVATIONAL",
      "effects": {
        "reactor_temp": "positive effect on product_purity (r=0.948)"
      },
      "support_domain": "p5=80.59, p95=100.01, current=96.50, n=200"
    },
    {
      "parameter": "time_since_product_grade_transition",
      "controllability": "directly controllable via process setpoint adjustment",
      "operability": "CONFOUNDED",
      "effects": {
        "time_since_product_grade_transition": "positive effect on product_purity (r=0.029)"
      },
      "support_domain": "p5=21.00, p95=630.00, current=663.00, n=200"
    }
  ],
  "operability_summary": "1 个关系受混杂因素影响（Simpson/群组逆转或未解决的时间混淆）。",
  "open_questions": [
    {
      "question": "建议在投入运行前做进一步机制验证。",
      "severity": "minor",
      "potential_impact": "Informs parameter optimization strategy"
    },
    {
      "question": "存在混杂：因果识别需分层分析或受控实验。",
      "severity": "minor",
      "potential_impact": "Informs parameter optimization strategy"
    },
    {
      "question": "调节效应：product_purity 关联在 product_grade 分组间方向相反，关联随工况/分组改变，不可外推为全局杠杆。",
      "severity": "minor",
      "potential_impact": "Informs parameter optimization strategy"
    }
  ],
  "evidence_gaps": [],
  "provenance": {
    "source_artifacts": {
      "analysis_coverage": "D:\\codes\\industrial-deep-diagnostic\\workspace\\e2e-test\\run\\enhancement\\analysis_coverage.json",
      "derived_features": "D:\\codes\\industrial-deep-diagnostic\\workspace\\e2e-test\\run\\enhancement\\derived_features.json",
      "deep_data_analysis": "D:\\codes\\industrial-deep-diagnostic\\workspace\\e2e-test\\run\\enhancement\\deep_data_analysis.json",
      "association_graph": "D:\\codes\\industrial-deep-diagnostic\\workspace\\e2e-test\\run\\enhancement\\association_graph.json",
      "physics_bridge": "D:\\codes\\industrial-deep-diagnostic\\workspace\\e2e-test\\run\\enhancement\\physics_bridge.json",
      "ontology": "D:\\codes\\industrial-deep-diagnostic\\workspace\\e2e-test\\run\\01_ontology\\ontology.json",
      "diagnosis": "D:\\codes\\industrial-deep-diagnostic\\workspace\\e2e-test\\run\\04_diagnostics\\diagnosis.json"
    },
    "data_source": {
      "file": "cleaned_data.csv",
      "sha256": "1484fa4ddebc41b46699a565cc15f95270140b51274759bf8957d9031ef54f7f",
      "rows": 200,
      "cols": 12
    }
  }
}
```
