# 本体简报 · lithium_coating_doe

- 契约版本：1.0（profile=doe）
- 数据阶段：`collected`
- 本体版本：1　本体哈希：`sha256:51364d135eec2af4859ae3acee58266a04a58d0ce8bf2679090d7ca80dcf2604`
- 上下文指纹 context_fp：`sha256:e508b7eeba0ea30bdb196a0ba3c389185189a66f6eac5390918a9aedbeba1e62`
- 工艺类型：designed_experiment　产线/实验：— / —
- 目标：—　分析目的：—
- 设计类型：partial_factorial_3level

## 1. 场景解释

- （本体未给出工序分解；以列语义与因子/响应表为准）

## 2. 因子（可控参数）

| 列 | 名称 | 类型 | 单位 | 范围 | 预期方向 | 映射 | 置信 | 物理含义 |
|---|---|---|---|---|---|---|---|---|
| `coat_speed_mpm` | coat_speed_mpm | — | [120, 150, 180] | / ~ n | — | matched | INFERRED | coat_speed_mpm（由分析上下文声明；未提供独立物理机理描述） |
| `oven1_temp_c` | oven1_temp_c | — | [80, 90, 100] | ℃ ~ ℃ | — | matched | INFERRED | oven1_temp_c（由分析上下文声明；未提供独立物理机理描述） |
| `oven2_temp_c` | oven2_temp_c | — | [70, 80, 90] | ℃ ~ ℃ | — | matched | INFERRED | oven2_temp_c（由分析上下文声明；未提供独立物理机理描述） |
| `gap_um` | gap_um | — | [150, 180, 210] | m ~ µ | — | matched | INFERRED | gap_um（由分析上下文声明；未提供独立物理机理描述） |
| `solid_content_pct` | solid_content_pct | — | [55, 60, 65] | % ~ % | — | matched | INFERRED | solid_content_pct（由分析上下文声明；未提供独立物理机理描述） |
| `substrate_gsm` | substrate_gsm | — | [95, 105, 115] | / ~ ² | — | matched | INFERRED | substrate_gsm（由分析上下文声明；未提供独立物理机理描述） |
| `humidity_rh` | humidity_rh | — | [35, 50, 65] | % ~ R | — | matched | INFERRED | humidity_rh（由分析上下文声明；未提供独立物理机理描述） |
| `tension_n` | tension_n | — | [300, 350, 400] | N ~ N | — | matched | INFERRED | tension_n（由分析上下文声明；未提供独立物理机理描述） |

## 3. 响应（被优化目标）

| 列 | 名称 | 单位 | 目标 | LSL | USL | Target | 映射 | 置信 |
|---|---|---|---|---|---|---|---|---|
| `coat_weight_gsm` | coat_weight_gsm | g/m² | target | 3.8 | 4.2 | 4.0 | matched | INFERRED |
| `coating_thick_um` | coating_thick_um | µm | target | 9.5 | 11.5 | 10.5 | matched | INFERRED |
| `defect_rate_pct` | defect_rate_pct | % | minimize | — | 0.5 | — | matched | INFERRED |

## 4. 关系（预期机理）

- （本体未声明显式关系；一致性检查将跳过，不会编造方向）

## 5. 局限

- 先验本体：关系方向来自上下文声明与物理先验，未经实测数据验证
- 未声明任何 expected_sign —— 未生成因子→响应关系，一致性检查将如实记为 not_estimable

## 6. 列映射覆盖（0 静默）

- matched: 11　inferred: 0　unmatched: 0
- coverage.ratio = 1.0（1.0 = 每个已声明因子/响应都有 matched 或 inferred+reason）

## 7. 来源

- build_mode=prior_knowledge　engine=industrial-ontology-builder
- rag_used=False　web_used=False　physics_prior_used=True
- build_seconds=0.111

> 本简报由确定性脚本生成；Agent 必须阅读本文件后写出 `01_profile/analysis_plan.md` 才能进入统计阶段（门禁 `ONTOLOGY_BRIEF_REQUIRED` / `ANALYSIS_PLAN_REQUIRED`）。
