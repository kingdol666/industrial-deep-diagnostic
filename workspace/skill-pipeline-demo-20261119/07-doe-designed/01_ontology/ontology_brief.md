# 本体简报 · injection_energy_doe

- 契约版本：1.0（profile=doe）
- 数据阶段：`collected`
- 本体版本：1　本体哈希：`sha256:0f70f3d1a2e3dd6382aedda2baeca95bc28d3ca7f4c6aff746be5f554d6ad5f0`
- 上下文指纹 context_fp：`sha256:d492c75d095621f84d72f87a2f255ce945e6ec22db80a045416d2edb42deb497`
- 工艺类型：designed_experiment　产线/实验：— / —
- 目标：—　分析目的：—
- 设计类型：full_factorial_randomized

## 1. 场景解释

- （本体未给出工序分解；以列语义与因子/响应表为准）

## 2. 因子（可控参数）

| 列 | 名称 | 类型 | 单位 | 范围 | 预期方向 | 映射 | 置信 | 物理含义 |
|---|---|---|---|---|---|---|---|---|
| `barrel_temp_c` | barrel_temp_c | — | ℃ | 186 ~ 194 | — | matched | INFERRED | barrel_temp_c（由分析上下文声明；未提供独立物理机理描述） |
| `cooling_time_s` | cooling_time_s | — | s | 24 ~ 32 | — | matched | INFERRED | cooling_time_s（由分析上下文声明；未提供独立物理机理描述） |

## 3. 响应（被优化目标）

| 列 | 名称 | 单位 | 目标 | LSL | USL | Target | 映射 | 置信 |
|---|---|---|---|---|---|---|---|---|
| `energy_kwh_per_kg` | energy_kwh_per_kg | kWh/kg | minimize | — | 0.75 | — | matched | INFERRED |

## 4. 关系（预期机理）

- （本体未声明显式关系；一致性检查将跳过，不会编造方向）

## 5. 局限

- 先验本体：关系方向来自上下文声明与物理先验，未经实测数据验证
- 未声明任何 expected_sign —— 未生成因子→响应关系，一致性检查将如实记为 not_estimable

## 6. 列映射覆盖（0 静默）

- matched: 3　inferred: 0　unmatched: 0
- coverage.ratio = 1.0（1.0 = 每个已声明因子/响应都有 matched 或 inferred+reason）

## 7. 来源

- build_mode=prior_knowledge　engine=industrial-ontology-builder
- rag_used=False　web_used=False　physics_prior_used=True
- build_seconds=0.087

> 本简报由确定性脚本生成；Agent 必须阅读本文件后写出 `01_profile/analysis_plan.md` 才能进入统计阶段（门禁 `ONTOLOGY_BRIEF_REQUIRED` / `ANALYSIS_PLAN_REQUIRED`）。
