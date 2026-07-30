# 工业深度诊断 Skill 强化规划 — 最终版

> **文档定位**: 自包含的完整落地规划。涵盖架构设计、5 个 Phase 详细实施、Schema 定义、脚本接口、最终报告格式、DOE 集成接口。DOE 研发专家和开发工程师均可直接使用。
>
> **版本**: FINAL | 2026-07-30
> **整合**: V1 初版 + V2 专家认证 + V3 盲区修复 + 互联网调研 + 4 位专家独立意见
> **状态**: ✅ 可直接进入开发

---

## 目录

- [一、系统定位与团队架构](#一系统定位与团队架构)
- [二、当前能力盘点与差距分析](#二当前能力盘点与差距分析)
- [三、互联网调研与专家共识](#三互联网调研与专家共识)
- [四、强化设计总览](#四强化设计总览)
- [五、Phase 1: 深层因果分析引擎](#五phase-1-深层因果分析引擎)
- [六、Phase 2: 工艺参数关系图谱](#六phase-2-工艺参数关系图谱)
- [七、Phase 3: 优化洞察注入诊断](#七phase-3-优化洞察注入诊断)
- [八、Phase 4: 工艺知识库构建](#八phase-4-工艺知识库构建)
- [九、Phase 5: DOE Agent 集成闭环](#九phase-5-doe-agent-集成闭环)
- [十、最终报告格式: process_analysis_report.md](#十最终报告格式)
- [十一、Schema 完整定义](#十一schema-完整定义)
- [十二、实施时间线](#十二实施时间线)
- [十三、风险与缓解](#十三风险与缓解)

---

## 一、系统定位与团队架构

### 1.1 系统在优化团队中的位置

```
┌─────────────────────────────────────────────────────────────────────┐
│                       工艺优化闭环系统                                   │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 查询知识库 + 派发实验
                              │
┌─────────────────────────────┴──────────────────────────────────────┐
│                     DOE 决策大脑 (Agent)                                │
│                                                                       │
│  ① READ    读 process_knowledge.db → 理解全局参数关系                    │
│  ② ANALYZE 按 dY/dX × evidence × regime × risk 排序杠杆点               │
│  ③ DESIGN  生成 doe_plan.json → 选 screen/factorial/RSM 设计            │
│  ④ DISPATCH 写 dispatch_manifest.json → 派发工艺专家 Agent              │
│  ⑤ COLLECT 新数据流入 → 诊断系统重跑 → 贝叶斯更新知识库                   │
│                                                                       │
│  ⚠️ 红线: 不直接写 DCS / 不绕过 SIS / 超规程需 MOC 审批                   │
│  ⚠️ 必查: 安全预检/多目标/交互安全/外推标记/回退方案/监控计划/成本/MOC     │
└───────────────┬───────────────────────────────┬─────────────────────┘
                │                               │
    ┌───────────▼──────────┐     ┌──────────────▼──────────────┐
    │  工艺知识库            │     │  执行 Agent 团队              │
    │  (SQLite WAL + JSONL) │     │  (1 Generalist 编排 +          │
    │                       │     │   N Specialist 动态装配)       │
    │  · kg_nodes 参数节点   │     │  · 按 ontology.parameter_groups │
    │  · kg_edges 因果边    │     │    自动分组                    │
    │  · safe_windows       │     │  · 强交互参数合并为联合 specialist│
    │  · doe_decisions      │     │  · 文件信号协调 (非 RPC)       │
    │  · 贝叶斯 posterior   │     │                               │
    └───────┬───────────────┘     └──────────────┬──────────────┘
            │                                    │
            │                                    ▼
            │                            ┌───────────────┐
            │                            │   产线 DCS      │
            │                            │  (只读推荐模式)  │
            │                            └───────┬───────┘
            │                                    │
    ┌───────▼────────────────────────────────────▼───────┐
    │              新数据流入 (CSV/Parquet)                  │
    └───────────────────────┬────────────────────────────┘
                            │
    ╔═══════════════════════▼═══════════════════════╗
    ║          数据诊断 Skill (本系统强化对象)           ║
    ║                                               ║
    ║  Step 0-1:  数据接入 + 清洗 + 传感器一致性预检   ║  已完成
    ║  Step 2:    工艺本体构建                        ║  已完成
    ║  Step 3:    统计分析 + 反伪相关                 ║  已完成
    ║  Step 3.5:  深层因果分析 (新增 ★)               ║  本次核心
    ║  Step 4:    物理诊断                           ║  已完成
    ║  Step 4.5:  优化洞察 + 操作点评估 (新增 ★)      ║  本次核心
    ║  Step 5:    质量门审计                         ║  已完成
    ║  Step 5.5:  知识库构建 + 贝叶斯更新 (新增 ★)    ║  本次核心
    ║  Step 6+:   报告 + 可视化 + 交接班诊断卡 (新增)  ║  本次强化
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
```

### 1.2 系统的三重角色

| 角色 | 对象 | 核心交付 |
|------|------|---------|
| **诊断医生** (现有) | 异常根因 | diagnosis.json + report.md |
| **工艺翻译官** (新增) | 数据→知识 | parameter_relationship_graph.json |
| **DOE 顾问** (新增) | 优化方向 | optimization_levers.json + process_analysis_report.md |

### 1.3 部署路线（工艺工程师认证）

| 阶段 | 定位 | 部署约束 | 时间 |
|------|------|---------|------|
| Phase 0 当前 | 离线事件分析顾问 | 无安全风险，可重型 ML | 已完成 |
| Phase 1 近期 | 定期巡检顾问 | 每日/每周批处理自动预警 | 6-12 月 |
| Phase 2 中期 | 在线只读辅助 | DCS 旁路只读，操作屏推荐，需安全评估 | 12-24 月 |
| Phase 3 远期 | 闭环优化 | 需 SIL 认证 + 冗余，多数工厂永不走到 | — |

> **系统定位**: "工艺工程师的超级助手"，不是"取代工艺工程师的 AI"。最大价值是把 3 天排查压缩到 3 小时、从凭经验猜到有数据支撑。输出必须可审计、可追溯、可解释。

---

## 二、当前能力盘点与差距分析

### 2.1 已有能力（DOE 知识库的原材料）

| 能力 | 当前实现 | 产出文件 | DOE 价值 |
|------|---------|---------|---------|
| 工艺本体 | ontology.json: 参数角色 + 控制方程 + 物理关系 | `01_ontology/ontology.json` | 参数语义基础 |
| 多维相关 | Pearson r + Spearman ρ + 去趋势 r | `02_processed/validate_report.json` | 哪些参数实际相关 |
| 反伪相关 | Simpson 检测 + leave-one-out + 趋势混淆 | `validate_report.json` anti_spurious | 排除伪因果 |
| 时滞分析 | CCF 时滞补偿 + Granger 因果 | `data_analysis_conclusion.json` | 因果延迟 |
| 竞争假设 | 物理审计验证的因果链 + 排除逻辑 | `04_diagnostics/diagnosis.json` | 不该动哪些参数 |
| 物理约束 | 控制方程验证: Arrhenius/Fourier/Darcy | `physics_check.json` | 物理极限在哪里 |
| 事件标记 | 泵维护/酸洗/风扇故障等自然实验 | `anomaly_report.json` | 历史干预结果 |
| 操作补偿 | 泵速补偿识别（果非因） | `diagnosis.json` | 哪些参数是果不是因 |

### 2.2 DOE 专家的 5 个核心痛点（当前无法回答）

| 优先级 | DOE 痛点 | 当前状态 | 强化后产出 |
|:------:|---------|:--------:|-----------|
| **P0** | "调 1°C 影响几个点？" | ❌ | `marginal_effects.json` (dY/dX + CI + 曲率) |
| **P1** | "安全操作范围是多少？" | ❌ | `safe_operating_windows.json` (5 层 + 动态) |
| **P2** | "温度和压力有交互吗？" | ❌ | `interaction_topology.json` (类型 + simple slopes) |
| **P3** | "哪些参数值得调？哪些已到顶？" | ❌ | `leverage_risk_regime_matrix` (三维) |
| **P4** | "这些结论有多可信？需要做实验验证吗？" | ❌ | `causal_confidence_bounds.json` (L2-L5) |

### 2.3 数据资产盘点

| 场景 | 行数 | 列数 | 工艺类型 | DOE 价值 |
|------|:----:|:----:|---------|---------|
| CSTR 反应器 | 1440 | 16 | 连续化工催化 | 化工反应优化 |
| 换热器结垢 | 2160 | 16 | 热交换设备 | 清洗周期+水质优化 |
| BOPET 薄膜 | 2501 | 39 | 挤出成型 | 多区温度协调 |
| CNC 主轴磨损 | 1051 | 14 | 机械加工 | 切削参数优化 |
| 钢冷轧 | 2501 | 18 | 金属加工 | 轧制力+张力优化 |
| 水泥球磨 | 64801 | 16 | 粉磨工艺 | 研磨体级配 |
| 造纸流浆箱 | 64801 | 15 | 造纸工艺 | 流量+压力平衡 |
| 乐凯涂布 | 150 | 187 | 涂布工艺 | 多变量配方 |

---

## 三、互联网调研与专家共识

### 3.1 互联网调研发现（5 个借鉴方向）

| # | 发现 | 来源 | 对本系统的影响 |
|:-:|------|------|--------------|
| 1 | **Causal SHAP 局限**：SHAP 假设特征独立，多共线性时误导 | [arxiv 2509.00846](https://arxiv.org/html/2509.00846v1) | 放弃 Causal SHAP；用偏相关+OLS 替代 |
| 2 | **ML-DOE**：Gaussian process surrogate + acquisition function，减少 30-50% 实验数 | [Atinary SDLabs](https://atinary.com/applications/ai-experimental-design-platform), [Tridiagonal.ai](https://tridiagonal.ai/blogs/machine-learning-driven-design-of-experiments-ml-doe-the-efficient-experimentation) | DOE Agent 用信息增益排序实验优先级 |
| 3 | **Self-Driving Labs**：Bayesian Optimization 闭环，个位数实验找最优 | [Nature Synthesis 2026](https://www.nature.com/articles/s44160-026-01053-0) | 远期目标：诊断+BO=自主优化闭环 |
| 4 | **Digital Twin Knowledge Graph**：参数为节点，语义关系为边 | [Cambridge Universal Digital Twin](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/FD25CDFF886CD2ED33D1FDFC13F6BEAB/S2632673621000101a.pdf) | 关系图谱设计依据 |
| 5 | **PIML**：将控制方程嵌入 ML loss function | [ASM Computing Engineering 2025](https://asmedigitalcollection.asme.org/computingengineering/article/25/12/120804/1225302/Physics-Informed-Machine-Learning-in-Design-and) | ontology governing_law 作物理约束 |

### 3.2 专家团队共识（4 方一致）

| # | 共识 | 依据 |
|:-:|------|------|
| 1 | **偏相关 + OLS 边际效应 > Causal SHAP** | 数据科学家：SHAP 解释链长、DOE 不认；DOE 专家：partial_r 是学术用的，dY/dX 才是决策用的 |
| 2 | **嵌入式新增 Phase（非独立 skill）** | 架构师：因果证据即算即用避免快照过期 |
| 3 | **SQLite(WAL) + JSONL 审计镜像（非 Neo4j）** | 架构师：零新依赖；工艺工程师：可审计是红线 |
| 4 | **优化建议是"决策包"非"一个数字"** | DOE 专家：收益/风险/成本/前提/回退缺一不可 |
| 5 | **观测数据因果推断有天花板（L3）** | DOE 专家：未观测混淆是根本限制 |

### 3.3 V3 审查修复的 5 个盲区

| # | V2 盲区 | 后果 | V3 修复 |
|:-:|---------|------|---------|
| 1 | OLS 纯线性用在非线性工艺 | DOE 不知道响应面有峰值 | 加入二次项 `Y ~ X + X²`，判断 ASCENDING/NEAR_PEAK/DESCENDING |
| 2 | 时序数据当横截面分析 | dY/dX 有偏（热惯性未建模） | lagged regressors + 仅稳态行 |
| 3 | 只分析主 target | 没告诉 DOE 副产物/能耗的代价 | multi_target_summary 总账 |
| 4 | 无响应面位置判断 | DOE 在峰值附近还在设计升温实验 | operating_regime + lever_exhaustion_check |
| 5 | 反馈只降 confidence | 系统永远用第一次估计 | 贝叶斯更新 dY/dX posterior |

---

## 四、强化设计总览

### 4.1 5 个 Phase 一览

```
Phase 1 (2周)  深层因果分析引擎 ─── causal_deep_analysis.py
                输出: marginal_effects + interaction + safe_window + confidence_bounds

Phase 2 (1周)  工艺参数关系图谱 ─── relationship_graph_builder.py
                输出: parameter_relationship_graph.json (DOE 可查询)

Phase 3 (1周)  优化洞察注入诊断 ─── diagnostician Phase 4.5
                输出: diagnosis.json optimization_insights + operating_point_assessment

Phase 4 (2周)  工艺知识库构建 ──── knowledge_base_builder.py
                输出: process_knowledge.db (SQLite WAL) + 贝叶斯更新

Phase 5 (3周)  DOE Agent 集成 ──── DOE Agent + 工艺专家 Agent 团队
                输出: doe_plan.json + dispatch_manifest.json + 闭环反馈

最终交付 (含在 Phase 3 中): process_analysis_report.md
                一份 DOE 专家可直接读懂的深度分析报告
```

### 4.2 技术选型

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 因果量化方法 | OLS 含二次项 + lagged regressors | 透明、可解释、零新依赖、DOE 天然理解 |
| 交互检测 | OLS centered interaction + simple slopes | 已有基础、Bonferroni 校正 |
| 安全窗口 | Bootstrap 分位数回归 | 不对分布做假设、直接回答可验证陈述 |
| 知识库存储 | SQLite WAL + JSONL 审计镜像 | 零新依赖、递归 CTE 够用、可审计 |
| DOE 协调 | 文件驱动（dispatch_manifest.json） | 复用现有 .pipeline_events 范式 |
| Agent 编排 | 1 Generalist + N Specialist 动态装配 | 按工艺本体自动分组、非硬编码 |
| 非线性补充 | n≥2000 时可选 TreeSHAP 辅助验证 | 非主输出、仅交叉验证用 |

### 4.3 核心差异化（vs 纯 ML SHAP 方法）

```
纯 ML (SHAP):     "X对Y有影响，SHAP value=0.3"           → 黑箱，无因果方向
纯统计 (Pearson):  "X与Y相关，r=0.7"                     → 无物理语义、不知净效应
本系统 V3:         "温度对转化率有因果效应(dY/dX=0.42%/°C)   ← 量化(含置信区间)
                   通过Arrhenius方程(物理验证)               ← 物理可解释
                   Simpson验证通过(非混淆)                  ← 统计严谨
                   当前在响应面NEAR_PEAK位置(距峰值3.3°C)    ← 战略级指导
                   注意与硫含量负交互(高硫时效应减半)         ← 深层洞察
                   总代价:副产物+8.3ppm/°C+能耗+2.1kW/°C    ← 多目标总账
                   盈亏平衡点:188.9°C                       ← 可操作边界
                   建议范围184-189°C(超限烧结风险)          ← 安全约束
                   证据等级:OBSERVATIONAL_STRONG(L3)        ← 可信度声明"
```

---

## 五、Phase 1: 深层因果分析引擎

### 5.1 概要

| 项目 | 内容 |
|------|------|
| **目标** | 回答 DOE P0-P4：边际效应、安全窗口、交互拓扑、杠杆排名、因果置信度 |
| **新增脚本** | `.claude/skills/industrial-data-processor/scripts/causal_deep_analysis.py` |
| **依赖** | statsmodels（已有）、scipy（已有）。**零新依赖** |
| **集成位置** | data-processor 协议 Phase 2.4（在 Phase 2.3 统计基线之后） |
| **开关** | `DOE_MODE` 环境变量控制。auto 模式跳过；doe 模式启用 |
| **输入** | cleaned_data.json + ontology.json + validate_report.json + production_regime_filter.json |
| **输出** | 4 个 JSON 文件到 `02_processed/` |

### 5.2 模块 A: marginal_effects.json

**核心修复**：含二次项 + lagged + 稳态过滤 + 多目标 + operating_regime

```json
{
  "$schema": "marginal_effects_schema.json",
  "description": "OLS 含二次项 + lagged regressors, 仅稳态行, 多目标同时回归",
  "method": "OLS Y_j ~ X_i + X_i² + X_i(t-lag*) | steady_state_only",
  "steady_state_filter": {
    "source": "production_regime_filter.json",
    "total_rows": 2160,
    "steady_rows_retained": 1920,
    "excluded_regimes": ["startup", "shutdown", "transition", "maintenance"]
  },

  "effects": {
    "reactor_temp_C": {
      "_regression_quality": {
        "r_squared": 0.78,
        "adjusted_r_squared": 0.77,
        "residual_normality": {"test": "Shapiro-Wilk", "p_value": 0.12, "status": "pass"},
        "multicollinearity_vif": {"max": 3.2, "status": "acceptable (<5)"},
        "durbin_watson": 1.85,
        "n_observations": 1920,
        "lag_applied": "2.5h (from time_lag_analysis)"
      },

      "conversion_pct": {
        "dY_dX_linear": 0.42,
        "dY_dX_quadratic": -0.008,
        "unit": "% per °C",
        "p_value_linear": 0.0001,
        "p_value_quadratic": 0.03,
        "confidence_interval_95": [0.35, 0.49],
        "standardized_effect": 0.38,
        "evidence_quality": "OBSERVATIONAL_STRONG",
        "evidence_rationale": "partial_r=0.52(p<0.001) + Arrhenius物理验证 + Simpson通过 + Granger显著",

        "operating_regime": {
          "status": "ASCENDING_NEAR_PEAK",
          "rationale": "β₁>0(正线性) + β₂<0(负二次) → 存在峰值。峰值估计 X* = -β₁/(2β₂) = 0.42/(2×0.008) = 188.9°C。当前 185.6°C，距峰值 3.3°C。",
          "peak_estimate": 188.9,
          "distance_to_peak": 3.3,
          "doe_implication": "升温仍有收益但递减。到189°C后转化率开始下降。DOE应设计RSM精确定位峰值而非继续factorial升温"
        },

        "interpretation": "温度每升1°C转化率+0.42%(线性部分)。但存在峰值~189°C, 当前距峰值3.3°C, 收益递减中。",
        "doe_implication": "杠杆参数但收益递减。建议小步(1°C)调而非大步(5°C)"
      },

      "byproduct_ppm": {
        "dY_dX_linear": 8.3,
        "dY_dX_quadratic": 0.12,
        "p_value_linear": 0.003,
        "operating_regime": {"status": "ASCENDING", "rationale": "β₁>0+β₂>0 → 单调上升, 无峰值", "doe_implication": "升温的副产物代价线性增长"},
        "interpretation": "温度每升1°C副产物+8.3ppm",
        "doe_implication": "升温有质量代价"
      },

      "selectivity_pct": {
        "dY_dX_linear": -0.3,
        "operating_regime": {"status": "DESCENDING"},
        "interpretation": "温度每升1°C选择性-0.3%"
      },

      "energy_kW": {
        "dY_dX_linear": 2.1,
        "interpretation": "温度每升1°C能耗+2.1kW"
      }
    }
  },

  "multi_target_summary": {
    "reactor_temp_C": {
      "benefits": [{"target": "conversion_pct", "delta_per_unit": "+0.42%"}],
      "costs": [
        {"target": "byproduct_ppm", "delta_per_unit": "+8.3ppm"},
        {"target": "selectivity_pct", "delta_per_unit": "-0.3%"},
        {"target": "energy_kW", "delta_per_unit": "+2.1kW"}
      ],
      "net_assessment": "净收益为正但递减。到189°C后转负",
      "break_even_point": "188.9°C"
    }
  },

  "non_levers": [
    {"parameter": "cooling_water_temp_C", "reason": "partial_r=0.03(p=0.45) 不显著", "classification": "noise_variable"},
    {"parameter": "feed_sulfur_ppm", "reason": "强因果但不可控（原料决定）", "classification": "constraint"}
  ]
}
```

### 5.3 模块 B: interaction_topology.json

```json
{
  "$schema": "interaction_topology_schema.json",
  "description": "参数交互拓扑 + 共线性诊断",
  "method": "OLS centered interaction terms + simple slopes + Bonferroni",
  "interactions": [
    {
      "param_a": "reactor_temp_C",
      "param_b": "h2_partial_pressure_bar",
      "target": "conversion_pct",
      "interaction_coef": 0.034,
      "p_value_corrected": 0.008,
      "interaction_type": "synergistic",
      "simple_slopes": {
        "at_low_B":  {"slope_of_A": 0.28, "regime": "ASCENDING"},
        "at_mid_B":  {"slope_of_A": 0.42, "regime": "ASCENDING_NEAR_PEAK"},
        "at_high_B": {"slope_of_A": 0.56, "regime": "NEAR_PEAK", "warning": "高压时峰值前移至186°C"}
      },
      "doe_implication": "升温+加压协同。单因素实验严重低估潜力。DOE应设计2²factorial含交互项",
      "safety_implication": "组合效应可能触发飞温(>192°C失控反应)",
      "process_explanation": "高温+高压同时提升反应速率和氢气溶解度，化学计量比协同"
    }
  ],
  "parameter_correlations": [
    {
      "pair": ["reactor_temp_C", "cooling_water_temp_C"],
      "pearson_r": 0.68,
      "doe_impact": "共线性高→DOE中不能独立操纵→必须正交扰动→成本上升",
      "recommendation": "DOE设计中用D-optimal而非full factorial"
    }
  ]
}
```

### 5.4 模块 C: safe_operating_windows.json

```json
{
  "$schema": "safe_operating_windows_schema.json",
  "description": "历史合格批次的参数分布。注意：历史范围 ≠ 物理安全极限。",
  "method": "Bootstrap 分位数回归 B=1000, 条件于质量阈值",
  "quality_threshold": {"conversion_pct": ">=85", "byproduct_ppm": "<=150"},

  "windows": {
    "reactor_temp_C": {
      "n_good_batches": 842,
      "quantiles": {
        "p5":  {"value": 182.0, "ci95": [181.2, 182.8]},
        "p25": {"value": 184.5, "ci95": [184.0, 185.0]},
        "p50": {"value": 186.0, "ci95": [185.5, 186.5]},
        "p75": {"value": 188.0, "ci95": [187.5, 188.5]},
        "p95": {"value": 191.0, "ci95": [190.2, 191.8]}
      },
      "optimal_band": [184, 189],
      "current_median": 185.6,
      "headroom_up": 5.4,
      "headroom_down": 3.6,
      "extrapolation_warning": "p5-p95是历史合格批次范围。超出此范围无数据支撑",
      "dynamic_constraints": {
        "ramp_rate_limit": "0.5°C/min (热应力约束)",
        "max_residence_time_at_temp": "190°C以上不超过4h（催化剂烧结风险）"
      },
      "coupling_constraints": "此窗口在h2_pressure 22-27bar范围内成立"
    }
  },

  "layered_safety": {
    "design_limit":      "MAWP 35bar / 250°C (设备设计极限)",
    "regulatory_limit":  "环保排放限值",
    "procedural_limit":  "工艺规程上限 195°C / 30bar",
    "historical_range":  "本系统输出 p5-p95",
    "recommended_band":  "本系统输出 p25-p75"
  }
}
```

### 5.5 模块 D: causal_confidence_bounds.json

```json
{
  "$schema": "causal_confidence_bounds_schema.json",
  "description": "观测数据因果推断的天花板声明",
  "overall_grade": "L3_ConditionalIndependence",

  "grade_definitions": {
    "L2": "统计关联 + 物理约束（系统基本盘）",
    "L3": "条件独立 + refutation（本系统产出）",
    "L4": "准实验 + 干预分析（仅有历史干预记录时可达）",
    "L5": "受控随机实验（DOE金标准，系统永远达不到）"
  },

  "what_we_can_claim": [
    "控制全部观测变量后，温度对转化率有显著净效应(dY/dX=0.42, p<0.001)",
    "Arrhenius方程物理验证通过，因果方向确定",
    "Simpson检测排除了跨单元混淆",
    "Granger检验排除了时间序列反向因果"
  ],

  "what_we_cannot_claim": [
    "未观测的混淆变量(如催化剂装填方式)可能导致效应估计有偏",
    "安全窗口外的外推无数据支撑",
    "操作员选择偏差可能导致数据截断"
  ],

  "known_confounding_risks": [
    {"confounder": "catalyst_loading_method", "status": "unobserved", "impact": "可能使温度效应高估10-15%"}
  ],

  "what_would_upgrade_to_L4": [
    "获取催化剂装填记录",
    "利用酸洗/再生事件做断点回归分析"
  ],

  "minimum_experiments_to_validate": {
    "count": 6,
    "design": "2³factorial with center points",
    "factors": ["reactor_temp_C", "h2_pressure", "feed_rate"],
    "purpose": "从L3观测推断升级到L5实验验证"
  },

  "regression_diagnostics": {
    "max_vif": 3.2,
    "vif_status": "acceptable (<5)",
    "durbin_watson": 1.85,
    "autocorrelation_status": "mild (lagged regressors partially absorbed)"
  }
}
```

### 5.6 data-processor 协议集成

在 `agent-protocol.md` Phase 2.3 之后新增：

```markdown
## Phase 2.4: Deep Causal Analysis (NEW — DOE Knowledge Generation)

⚠️ 受 DOE_MODE 开关控制。auto 模式跳过；doe 模式启用。

- [ ] 2.4.1 Read ontology.json → extract targets, predictors, confounders, known physics
- [ ] 2.4.2 Read production_regime_filter.json → 仅使用 steady_state 行
- [ ] 2.4.3 OLS 含二次项 + lagged: Y ~ X + X² + X(t-lag) → dY/dX + CI + operating_regime
       python causal_deep_analysis.py --mode marginal --run-dir $RUN_DIR
- [ ] 2.4.4 Interaction detection: centered terms + simple slopes + Bonferroni
       python causal_deep_analysis.py --mode interaction --run-dir $RUN_DIR
- [ ] 2.4.5 Safe windows: bootstrap quantile conditional on quality threshold
       python causal_deep_analysis.py --mode safe_window --run-dir $RUN_DIR
- [ ] 2.4.6 Causal confidence bounds: L2-L3 grade + regression diagnostics
       python causal_deep_analysis.py --mode confidence --run-dir $RUN_DIR
- Gate (CP-4.5): 4 files exist + marginal ≥3 significant + confidence has overall_grade + VIF<10
```

---

## 六、Phase 2: 工艺参数关系图谱

### 6.1 概要

| 项目 | 内容 |
|------|------|
| **目标** | 融合 ontology + 4 个因果输出 → DOE 可查询的参数关系图 |
| **新增脚本** | `.claude/skills/industrial-data-processor/scripts/relationship_graph_builder.py` |
| **输出** | `02_processed/parameter_relationship_graph.json` |

### 6.2 图谱结构

**节点类型**（向后兼容 ontology）:

| 类型 | 说明 |
|------|------|
| `quality_target` | 质量目标（转化率/副产物/选择性等） |
| `operating_lever` | 可操作杠杆（温度/压力/流量等可控参数） |
| `constraint` | 约束（原料组成/设备极限等不可控参数） |
| `noise_variable` | 噪音变量（统计不显著的参数） |

**边类型**（5 种）:

| 边类型 | 属性 | 说明 |
|--------|------|------|
| `QUANTIFIED_CAUSAL` | dY/dX + CI + evidence_quality + operating_regime + physics_verified | 量化因果边 |
| `INTERACTS_WITH` | interaction_type + simple_slopes + doe_implication + safety_implication | 交互边 |
| `BOUNDED_BY` | 指向 safe_window | 约束边 |
| `SYNERGISTIC` | 协同强度 | 协同子类 |
| `ANTAGONISTIC` | 拮抗强度 | 拮抗子类 |

### 6.3 杠杆-风险-工况三维矩阵

```json
{
  "leverage_risk_regime_matrix": {
    "dimensions": ["effect_size", "risk_level", "operating_regime"],
    "quadrants": {
      "lever_low_risk_ascending": [
        {"parameter": "h2_partial_pressure_bar", "effect": 1.2, "risk": "low", "regime": "ASCENDING", "action": "优先调, 收益稳定增长", "priority": 1}
      ],
      "lever_low_risk_near_peak": [
        {"parameter": "reactor_temp_C", "effect": 0.42, "risk": "low", "regime": "ASCENDING_NEAR_PEAK", "distance_to_peak": 3.3, "action": "可调但小步", "priority": 2}
      ],
      "lever_high_risk": [
        {"parameter": "pump_speed_pct", "effect": 0.02, "risk": "high(能耗2.8×)", "action": "不动", "priority": 4}
      ],
      "low_effect": [
        {"parameter": "feed_rate_kg_hr", "effect": 0.08, "action": "不优先, 作为约束", "priority": 3}
      ]
    }
  }
}
```

---

## 七、Phase 3: 优化洞察注入诊断

### 7.1 概要

| 项目 | 内容 |
|------|------|
| **目标** | diagnostician 不仅输出"根因是什么"，还输出"接下来怎么做" |
| **集成位置** | diagnostician 协议 Phase 4.5 |
| **输入** | parameter_relationship_graph.json + safe_operating_windows.json + diagnosis 结论 |
| **输出** | diagnosis.json 新增 `optimization_insights` 字段 + **process_analysis_report.md** |

### 7.2 diagnosis.json 新增字段

```json
{
  "optimization_insights": {

    "current_operating_point_assessment": {
      "primary_target": "conversion_pct",
      "current_value": 82.0,
      "target_spec": ">=90",
      "gap": -8.0,
      "response_surface_position": {
        "overall": "ASCENDING_NEAR_PEAK",
        "rationale": "温度杠杆距峰值3.3°C(近耗尽), 压力杠杆安全余量大(ASCENDING)",
        "doe_strategy": "优化重心转向压力+配比, 不建议大范围温度factorial"
      },
      "lever_exhaustion_check": {
        "reactor_temp_C": {"headroom_to_peak": 3.3, "status": "NEAR_EXHAUSTED"},
        "h2_partial_pressure_bar": {"headroom": 2.3, "status": "AVAILABLE"},
        "feed_rate_kg_hr": {"status": "AVAILABLE_BUT_LOW_EFFECT"}
      }
    },

    "leverage_parameters": [
      {
        "parameter": "reactor_temp_C",
        "target": "conversion_pct",
        "effect_direction": "positive",
        "effect_size": 0.42,
        "operating_regime": "ASCENDING_NEAR_PEAK",
        "current_value": 185.6,
        "suggested_range": "184-189°C (小步调)",
        "expected_gain": "+1.3% (升3°C至188.6°C)",
        "confidence": 0.85,
        "evidence_quality": "OBSERVATIONAL_STRONG",
        "physical_basis": "Arrhenius: k ∝ exp(-Ea/RT)",
        "total_cost": "副产物+24.9ppm + 能耗+6.3kW",
        "break_even": "188.9°C",
        "caution": "超过192°C触发烧结风险"
      }
    ],

    "tradeoffs": {
      "routes": [
        {"name": "高转化率路线", "profile": "temp+5°C + pressure+3bar", "gain": "+5% conversion", "cost": "+41.5ppm byproduct + -1.5% selectivity", "net": "negative(质量代价过高)"},
        {"name": "平衡路线(knee)", "profile": "temp+2°C + pressure+1.5bar", "gain": "+2.5% conversion", "cost": "+16.6ppm byproduct", "net": "positive"},
        {"name": "清洁路线", "profile": "pressure+2bar only", "gain": "+1.8% conversion", "cost": "+3ppm byproduct", "net": "positive(recommended)"}
      ],
      "user_weights_configurable": true
    },

    "doe_experiment_recommendations": [
      {
        "rank": 1,
        "purpose": "验证压力杠杆效应(信息增益最高)",
        "design": "2²factorial + center: h2_pressure(24/26/28) × temp(185/186/187)",
        "total_runs": 7,
        "expected_confirmation": "压力dY/dX=1.2±0.3 / 交互项p<0.05",
        "upgrades_confidence": "L3→L5 for h2_pressure edge",
        "risk_level": "low",
        "cost_estimate": "low(7 runs, 无大幅温度变化)"
      }
    ],

    "action_priority": {
      "URGENT": [],
      "SCHEDULE": [{"action": "原料噻吩GC-SCD分析", "deadline": "1周内", "owner": "化验室"}],
      "INFORM": [{"action": "催化剂活性下降趋势, 计划下次再生日期", "owner": "工艺组"}]
    }
  }
}
```

### 7.3 diagnostician 协议新增 Phase 4.5

```markdown
## Phase 4.5: Optimization Insights + Operating Point Assessment (NEW)

- [ ] 4.5.1 读 parameter_relationship_graph.json → 按 dY/dX × evidence × regime 排序杠杆
- [ ] 4.5.2 评估当前操作点在响应面的位置 (ASCENDING/NEAR_PEAK/DESCENDING)
- [ ] 4.5.3 检查杠杆耗尽 (lever_exhaustion_check)
- [ ] 4.5.4 生成 tradeoff 三层 (co-optimization matrix → Pareto frontier → utilities score)
- [ ] 4.5.5 生成 DOE 实验建议 (按信息增益排序)
- [ ] 4.5.6 标注 action_priority (URGENT/SCHEDULE/INFORM)
- [ ] 4.5.7 physical-auditor 审核: 优化建议是否与物理约束一致？
- [ ] 4.5.8 生成 process_analysis_report.md (DOE 可读懂的深度报告)
- Gate (CP-4.6): optimization_insights 非空 + ≥1 leverage + Pareto ≥3 routes + report.md exists
```

---

## 八、Phase 4: 工艺知识库构建

### 8.1 概要

| 项目 | 内容 |
|------|------|
| **目标** | 把单次运行的参数图谱累积成跨场景持久化知识库 |
| **新增脚本** | `.claude/skills/industrial-analysis-auto/scripts/knowledge_base_builder.py` |
| **存储** | SQLite WAL 主存储 + JSONL 审计镜像 |
| **位置** | `workspace/knowledge_base/process_knowledge.db` |

### 8.2 SQLite 表结构

```sql
-- 参数节点（带版本链 + 置信度衰减）
CREATE TABLE kg_nodes (
  id TEXT NOT NULL,
  scene TEXT NOT NULL,
  param_name TEXT,
  role TEXT,  -- quality_target / operating_lever / constraint / noise_variable
  physical_meaning TEXT,
  unit TEXT,
  version INTEGER DEFAULT 1,
  confidence REAL DEFAULT 1.0,  -- exp(-Δt/180天) 衰减
  updated_at TEXT,
  PRIMARY KEY (id, scene, version)
);

-- 因果边（含量化效应 + 贝叶斯 posterior）
CREATE TABLE kg_edges (
  from_node TEXT NOT NULL,
  to_node TEXT NOT NULL,
  scene TEXT NOT NULL,
  edge_type TEXT,  -- QUANTIFIED_CAUSAL / INTERACTS_WITH / BOUNDED_BY
  dY_dX REAL,
  dY_dX_posterior REAL,   -- 贝叶斯更新后的效应估计
  dY_dX_variance REAL,
  partial_r REAL,
  p_value REAL,
  evidence_quality TEXT,
  physics_verified INTEGER,
  operating_regime TEXT,
  confidence REAL,
  n_doe_validations INTEGER DEFAULT 0,
  updated_at TEXT,
  PRIMARY KEY (from_node, to_node, scene, edge_type)
);

-- DOE 决策记录（用于反馈学习）
CREATE TABLE doe_decisions (
  run_id TEXT,
  scene TEXT,
  decision TEXT,
  expected_gain TEXT,
  actual_gain TEXT,
  residual REAL,  -- actual - expected
  created_at TEXT
);

-- 安全窗口
CREATE TABLE safe_windows (
  param TEXT NOT NULL,
  scene TEXT NOT NULL,
  p5 REAL, p25 REAL, p50 REAL, p75 REAL, p95 REAL,
  optimal_band TEXT,
  n_good_batches INTEGER,
  updated_at TEXT,
  PRIMARY KEY (param, scene)
);
```

### 8.3 贝叶斯更新逻辑

```python
def update_effect_bayesian(prior_dYdX, prior_var, observed_dYdX, observed_var):
    """
    DOE 实验结果回流后，用贝叶斯更新修正效应估计。

    prior:    诊断系统从历史数据估计的 dY/dX
    observed: DOE 实验实测的 dY/dX
    posterior: 融合后的更新估计（精度更高）
    """
    posterior_dYdX = (prior_dYdX * observed_var + observed_dYdX * prior_var) / (prior_var + observed_var)
    posterior_var = (prior_var * observed_var) / (prior_var + observed_var)
    return posterior_dYdX, posterior_var
```

### 8.4 DOE 查询接口

```python
class ProcessKnowledgeBase:
    def query_leverage_params(self, scene, target, min_effect=0.1):
        """查询某场景下对指定 target 效应量 ≥ min_effect 的杠杆参数"""
    def query_safe_window(self, param, scene):
        """查询参数的安全操作窗口"""
    def query_interactions(self, param, scene):
        """查询参数的所有交互关系"""
    def query_operating_regime(self, param, scene):
        """查询参数当前在响应面的位置"""
    def get_confidence_bounds(self, scene):
        """查询该场景的因果置信度边界"""
    def compare_scenes(self, scene_a, scene_b):
        """跨场景对比"""
    def update_from_run(self, run_dir):
        """从新的诊断 run 增量更新知识库"""
    def update_from_doe_result(self, doe_decision):
        """从 DOE 实验结果贝叶斯更新 dY/dX"""
```

### 8.5 增量更新策略

每次诊断 run 完成后：
1. 读取 `parameter_relationship_graph.json`
2. UPSERT 到 kg_nodes / kg_edges / safe_windows
3. 相同 (param, scene) 的旧记录 version+1
4. confidence 按 `exp(-Δt_days/180)` 衰减（180 天半衰期）
5. JSONL 追加审计记录

每次 DOE 实验结果回流后：
1. 计算 `residual = actual_gain - expected_gain`
2. 贝叶斯更新 `dY_dX_posterior`
3. `n_doe_validations += 1`
4. evidence_quality 升级：OBSERVATIONAL → EXPERIMENTAL

---

## 九、Phase 5: DOE Agent 集成闭环

### 9.1 DOE Agent 5 阶段闭环

```
① READ
   DOE Agent 启动 → 读 process_knowledge.db
   → 查询 leverage_params + safe_windows + interactions + confidence_bounds + operating_regime

② ANALYZE
   → 按 dY/dX × evidence_quality × operating_regime × safe_headroom 排序
   → 生成 leverage_risk_regime_matrix
   → 识别 Pareto frontier 路线
   → 检查 lever_exhaustion（哪些杠杆已到顶）

③ DESIGN
   → 生成 doe_plan.json:
     · 按信息增益排序实验（不是"能做什么"而是"做什么最值得"）
     · 选设计类型: screen / factorial / RSM
     · 定义因子+水平+重复
     · 风险评估 + 监控计划 + 回退方案
     · 8 个前提条件全部检查

④ DISPATCH
   → 写 dispatch_manifest.json:
     · 按 ontology.parameter_groups 动态分组生成 specialist
     · 强交互参数合并为联合 specialist
     · 每个 specialist: 参数+目标值+变化速率+监控阈值

⑤ COLLECT
   → 新数据流入 → 诊断系统重跑
   → knowledge_base_builder 贝叶斯更新 kg_edges
   → DOE Agent 计算 residual = actual - expected
   → 大残差 → confidence降级 + 触发重分析
```

### 9.2 DOE Agent 必须满足的 8 个前提条件

每次派发优化任务前必须检查并输出：

```
□ 安全预检（设计极限 + 安全裕度）
□ 多目标评估（不只主 target 还有全部副作用）
□ 交互安全检查（组合是否触发危险交互）
□ 外推标记（是否超出历史范围多少 σ）
□ 回退方案（触发条件 + 撤回步骤）
□ 监控计划（2h/8h/24h 看什么 + 异常阈值）
□ 成本核算（能耗 vs 产量经济平衡）
□ MOC 判定（是否变更 + 审批级别）
```

### 9.3 工艺专家 Agent 团队

| 设计点 | 方案 |
|--------|------|
| 编排 | 1 个 Generalist Agent |
| Specialist 生成 | 按 `ontology.parameter_groups` 自动分组（非硬编码） |
| 强交互处理 | INTERACTS_WITH 边的参数合并为联合 specialist |
| 协调机制 | `dispatch_semaphore.json` 文件信号（非 RPC） |
| 扩展示例 | BOPET 39 温度区 → 按 stage 分组生成 5 个 specialist |

---

## 十、最终报告格式

### 10.1 概要

这是本系统强化后最关键的交付物——一份 DOE 研发专家**不需要任何 JSON 知识就能读懂**的深度分析报告。

| 项目 | 内容 |
|------|------|
| **文件名** | `process_analysis_report.md` |
| **位置** | `RUN_DIR/process_analysis_report.md`（与 report.md 并列） |
| **生成者** | diagnostician Phase 4.5.8 |
| **读者** | DOE 研发专家 / 工艺工程师 / 车间主任 |
| **语言** | 中文（JSON enum 保持英文） |

### 10.2 报告结构（10 节）

```markdown
# 工艺参数深度分析报告 — [场景名称]

> 生成时间: YYYY-MM-DD | 数据规模: N行×M列 | 分析模式: DOE_KNOWLEDGE
> 因果置信度等级: L3 (条件独立) | 详见第8节

---

## 1. 执行摘要（给厂长/总监看 — 30秒）

**当前状态**: [工艺在响应面的什么位置]
**核心发现**: [最关键的3个参数关系]
**优化建议**: [一句话战略方向]
**风险提示**: [最需要注意的约束]

---

## 2. 质量目标现状（给工艺工程师看 — 2分钟）

| 质量目标 | 当前值 | 目标值 | 差距 | 趋势 | 置信度 |
|---------|:------:|:------:|:----:|:----:|:------:|
| 转化率 | 82.0% | ≥90% | -8.0% | ↓-0.3%/day | HIGH |
| 副产物 | 180ppm | ≤150 | +30 | ↑+1.2/day | HIGH |

**质量协同性诊断**: [多目标是否协同恶化]
**黄金批次基线**: [历史最佳表现作为参照]

---

## 3. 参数效应总表（给DOE专家看 — 核心章节）

### 3.1 边际效应 (dY/dX)

| 参数 | →目标 | dY/dX | 95%CI | p值 | 证据等级 | 响应面位置 | 物理方程 |
|------|-------|:-----:|:-----:|:---:|:--------:|:---------:|:-------:|
| 温度 | 转化率 | +0.42%/°C | [0.35,0.49] | <0.001 | OBS_STRONG | NEAR_PEAK(距3.3°C) | Arrhenius |
| 温度 | 副产物 | +8.3ppm/°C | [6.1,10.5] | 0.003 | OBS_STRONG | ASCENDING | Ea_side>Ea_main |
| 氢压 | 转化率 | +1.2%/bar | [0.8,1.6] | 0.001 | OBS_STRONG | ASCENDING | Henry |
| 进料率 | 转化率 | -0.15%/kg | [-0.22,-0.08] | 0.002 | OBS_STRONG | — | 空速 |

### 3.2 多目标总账

| 参数 | 收益 | 全部代价 | 净评估 | 盈亏平衡 |
|------|------|---------|:------:|:-------:|
| 温度+1°C | 转化率+0.42% | 副产+8.3ppm+选择性-0.3%+能耗+2.1kW | 递减中 | 188.9°C |
| 氢压+1bar | 转化率+1.2% | 能耗+0.8kW | 正 | >30bar(规程限) |

### 3.3 非杠杆参数（不要浪费实验资源）

| 参数 | 原因 | 分类 |
|------|------|------|
| 冷却水温 | partial_r=0.03 不显著 | noise_variable |
| 进料硫含量 | 强因果但不可控 | constraint |

---

## 4. 参数交互拓扑（给DOE专家看 — 决定实验设计类型）

| 参数A | 参数B | 目标 | 交互类型 | p值(校正) | DOE含义 | 安全含义 |
|-------|-------|------|:--------:|:---------:|---------|---------|
| 温度 | 氢压 | 转化率 | 协同 | 0.008 | 需2²factorial | 高压时峰值前移 |
| 温度 | 硫含量 | 转化率 | 拮抗 | 0.01 | 高硫时升温无效 | — |

**Simple slopes 分解**:
- 低压时温度效应: +0.28%/°C (弱)
- 中压时: +0.42%/°C (正常)
- 高压时: +0.56%/°C (强, 但峰值前移至186°C)

**共线性诊断**: 温度-冷却水温 r=0.68 → DOE用D-optimal

---

## 5. 安全操作窗口（给工艺工程师看 — 决定敢不敢调）

| 参数 | 推荐区间 | 历史范围(p5-p95) | 规程上限 | 设计极限 | 当前值 | 上调余量 |
|------|:--------:|:---------------:|:-------:|:-------:|:------:|:-------:|
| 温度 | 184-189°C | 182-191°C | 195°C | 250°C | 185.6 | 3.4°C到推荐上限 |
| 氢压 | 23-26bar | 22-27bar | 30bar | 35bar | 24.7 | 1.3bar到推荐上限 |

**动态约束**: 升温速率≤0.5°C/min | 190°C以上停留≤4h
**耦合约束**: 温度窗口在氢压22-27bar时成立

> ⚠️ 历史范围 ≠ 物理安全极限。超出历史范围的外推无数据支撑。

---

## 6. 当前操作点评估（战略级指导 — 决定优化方向）

**响应面位置**: ASCENDING_NEAR_PEAK

| 杠杆参数 | 效应量 | 响应面位置 | 距峰值 | 状态 | 建议 |
|---------|:------:|:---------:|:-----:|:----:|------|
| 温度 | 0.42 | NEAR_PEAK | 3.3°C | 接近耗尽 | 小步调, 转RSM |
| 氢压 | 1.2 | ASCENDING | 未知 | 可用 | 优先调 |
| 进料率 | 0.08 | — | — | 低效 | 不优先 |

**DOE战略建议**: 温度已接近收益极限。优化重心转向压力+配比。不建议设计大范围温度factorial实验。

---

## 7. Pareto 前沿（多目标冲突路线）

| 路线 | 参数调整 | 转化率增益 | 副产物代价 | 净评估 |
|------|---------|:---------:|:---------:|:------:|
| 高转化率 | temp+5°C+pressure+3bar | +5% | +41.5ppm | ❌ 质量代价过高 |
| 平衡(knee) | temp+2°C+pressure+1.5bar | +2.5% | +16.6ppm | ✅ 推荐 |
| 清洁 | pressure+2bar only | +1.8% | +3ppm | ✅ 最安全 |

> 权重可配置。质量总监(重转化率)和生产总监(重成本)应看到不同最优方案。

---

## 8. 因果置信度边界（给DOE专家看 — 知道哪些能信）

**总体等级**: L3 (条件独立 + refutation)

**我们可以声称的**:
- ✅ 控制全部观测变量后, 温度对转化率有显著净效应
- ✅ Arrhenius物理验证通过
- ✅ Simpson检测排除混淆
- ✅ Granger排除反向因果

**我们不能声称的**:
- ❌ 未观测混淆(催化剂装填方式)可能使效应高估10-15%
- ❌ 安全窗口外的外推无数据支撑

**升级到L4需要**: 催化剂装填记录 / 断点回归分析
**升级到L5(金标准)的最小实验**: 6次(2³factorial+中心点)

---

## 9. DOE 实验建议（按信息增益排序）

| 优先级 | 实验 | 信息增益 | 升级置信度 | 成本 |
|:------:|------|:--------:|:---------:|:----:|
| 1 | 压力3水平(temp固定186°C) | HIGH | L3→L5(压力边) | 低(3runs) |
| 2 | temp×pressure 2²factorial | MEDIUM | L3→L5(交互边) | 中(7runs) |
| 3 | 进料率扰动 | LOW | — | 低但不值得 |

---

## 10. 行动方案与交接班卡

### 行动优先级

| 级别 | 行动 | 负责人 | 截止 |
|:----:|------|-------|:----:|
| URGENT | — | — | — |
| SCHEDULE | 原料噻吩GC-SCD分析 | 化验室 | 1周 |
| INFORM | 催化剂活性下降,计划再生 | 工艺组 | 下次停修 |

### 交接班诊断卡（给下一班操作工）

```
┌─────────────────────────────────────────┐
│  交接班诊断卡 [日期/班次]                   │
├─────────────────────────────────────────┤
│  异常状态: 转化率下降中(-0.3%/day)         │
│  诊断结论: 催化剂硫中毒(置信度80/HIGH)     │
│  当前状态: 可继续运行, 监控副产物趋势       │
│  行动项: 已送检原料噻吩                    │
│  注意事项: 勿仅靠升温补偿(效率递减)         │
│  紧急联系: 工艺组 XXX                     │
└─────────────────────────────────────────┘
```

---

## 附录: 分析方法与数据质量

- 分析模式: OLS含二次项+lagged regressors, 仅稳态行(1920/2160)
- 回归诊断: R²=0.78, VIF_max=3.2, DW=1.85, Shapiro p=0.12
- 数据清洗: 0行丢弃, 0类型泄漏, 0均值漂移
- Simpson检测: 16对, 关键混淆已排除
- 时滞分析: 温度→转化率最优滞后2.5h
- 物理验证: Arrhenius/Fourier/Darcy 全部通过
```

---

## 十一、Schema 完整定义

### 11.1 新增 Schema 文件清单

| Schema | 位置 | 用途 |
|--------|------|------|
| `marginal_effects_schema.json` | `.claude/shared/schemas/` | 边际效应输出验证 |
| `interaction_topology_schema.json` | 同上 | 交互拓扑验证 |
| `safe_operating_windows_schema.json` | 同上 | 安全窗口验证 |
| `causal_confidence_bounds_schema.json` | 同上 | 因果置信度验证 |
| `parameter_relationship_graph_schema.json` | 同上 | 关系图谱验证 |
| `doe_knowledge_schema.json` | 同上 | 知识库记录验证 |

### 11.2 关键 Schema 定义

#### marginal_effects_schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Marginal Effects Analysis",
  "type": "object",
  "required": ["description", "method", "steady_state_filter", "effects", "multi_target_summary", "non_levers"],
  "properties": {
    "description": {"type": "string"},
    "method": {"type": "string"},
    "steady_state_filter": {
      "type": "object",
      "required": ["source", "steady_rows_retained"],
      "properties": {
        "source": {"type": "string"},
        "total_rows": {"type": "integer"},
        "steady_rows_retained": {"type": "integer"},
        "excluded_regimes": {"type": "array", "items": {"type": "string"}}
      }
    },
    "effects": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "_regression_quality": {
            "type": "object",
            "properties": {
              "r_squared": {"type": "number"},
              "multicollinearity_vif": {"type": "object"},
              "n_observations": {"type": "integer"},
              "lag_applied": {"type": "string"}
            }
          }
        },
        "additionalProperties": {
          "type": "object",
          "required": ["dY_dX_linear", "operating_regime"],
          "properties": {
            "dY_dX_linear": {"type": "number"},
            "dY_dX_quadratic": {"type": "number"},
            "p_value_linear": {"type": "number"},
            "confidence_interval_95": {"type": "array", "items": {"type": "number"}},
            "evidence_quality": {"type": "string", "enum": ["EXPERIMENTAL", "OBSERVATIONAL_STRONG", "OBSERVATIONAL_WEAK", "PHYSICS_ONLY"]},
            "operating_regime": {
              "type": "object",
              "required": ["status"],
              "properties": {
                "status": {"type": "string", "enum": ["ASCENDING", "ASCENDING_NEAR_PEAK", "NEAR_PEAK", "DESCENDING", "FLAT"]},
                "peak_estimate": {"type": ["number", "null"]},
                "distance_to_peak": {"type": ["number", "null"]},
                "doe_implication": {"type": "string"}
              }
            },
            "interpretation": {"type": "string"},
            "doe_implication": {"type": "string"}
          }
        }
      }
    },
    "multi_target_summary": {"type": "object"},
    "non_levers": {"type": "array"}
  }
}
```

---

## 十二、实施时间线

```
Week 1-2:  Phase 1 — causal_deep_analysis.py
           · 4 模块(marginal/interaction/window/confidence)
           · 含二次项+lagged+稳态过滤+多目标+operating_regime
           · 零新依赖(statsmodels+scipy)
           · 在 CSTR + HX + BOPET 上验证

Week 3:    Phase 2 — relationship_graph_builder.py
           · 融合4个因果输出 → parameter_relationship_graph.json
           · 杠杆-风险-工况三维矩阵

Week 4:    Phase 3 — diagnostician Phase 4.5 + process_analysis_report.md
           · optimization_insights + operating_point_assessment
           · lever_exhaustion_check
           · process_analysis_report.md 生成器
           · physical-auditor 新增"优化建议审核"

Week 5-6:  Phase 4 — knowledge_base_builder.py
           · SQLite WAL + JSONL审计镜像
           · 贝叶斯更新(dY_dX_posterior)
           · DOE查询接口(Python class)
           · 增量更新 + confidence衰减

Week 7-9:  Phase 5 — DOE Agent集成
           · DOE Agent prompt + 5阶段闭环
           · 工艺专家Agent动态装配
           · 实验优先级(信息增益排序)
           · 端到端闭环测试: 数据→分析→知识库→DOE→派发→反馈
```

---

## 十三、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|:----:|:----:|------|
| 偏相关在高维数据不稳定 | 中 | dY/dX 有偏 | 限制控制变量数 ≤8；LASSO 预筛选 |
| 二次项在低样本不显著 | 中 | 无法判断峰值 | n<100 时不输出 operating_regime，标注 "insufficient_data" |
| 安全窗口在小样本不可靠 | 中 | 误导 DOE | n<30 标注 `low_confidence`；不输出 optimal_band |
| DOE Agent 误读知识库 | 中 | 错误实验设计 | 所有建议附 evidence_quality + physics_backing；DOE Agent 有"确认门" |
| 外推到历史范围外 | 高 | 物理损伤 | 所有输出带 `extrapolation_warning`；DOE Agent 拒绝超出 p5-p95 的建议 |
| 观测数据因果天花板 | 确定 | 效应估计有偏 | 输出 causal_confidence_bounds 明确声明 L3 天花板 |
| 贝叶斯先验选择不当 | 低 | posterior 收敛慢 | 用无信息先验 (flat prior)；n_doe_validations ≥3 后 posterior 稳定 |

---

## 附录: 工艺工程师的 4 条绝对红线

```
1. 禁止直接控制执行机构
2. 禁止绕过 SIS 安全联锁
3. 禁止未告知修改 DCS 设定值
4. 禁止推荐超规程范围参数（除非有 MOC 审批）
```

---

*规划版本: FINAL | 整合 V1+V2+V3+专家意见+互联网调研 | 可直接进入开发*
