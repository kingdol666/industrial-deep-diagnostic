# 本体简报 · bopet-tdo-thickness

- 契约版本：1.0（profile=doe）
- 数据阶段：`collected`
- 本体版本：1　本体哈希：`sha256:5329c7af76bb471df6ff92d6746f7830ce30b40cee2064b9ea6a488a6fd253b5`
- 上下文指纹 context_fp：`sha256:573a901fb3f74d6278a849961b919eaccbe554c241a5889586784dad4de9d19b`
- 工艺类型：L5-bopet　产线/实验：L5-bopet / doe-bopet-tdo-2026q4-r3
- 目标：在安全窗口内寻找 TDO/MDO 工况，使厚度落在 50±2 µm 的同时抑制雾度（≤1.8%），并给出下一轮布点建议　分析目的：在安全窗口内寻找 TDO/MDO 工况，使厚度落在 50±2 µm 的同时抑制雾度（≤1.8%），并给出下一轮布点建议
- 设计类型：ccd

## 1. 场景解释

- （本体未给出工序分解；以列语义与因子/响应表为准）

**已知混杂/协变量**：
- `ambient_temp`：declared as covariate in analysis_context (may co-move with factors and responses)（受控=False）
- `ambient_temp`：listed in analysis_context.covariates（受控=False）

## 2. 因子（可控参数）

| 列 | 名称 | 类型 | 单位 | 范围 | 预期方向 | 映射 | 置信 | 物理含义 |
|---|---|---|---|---|---|---|---|---|
| `tdo_z4_temp` | tdo_z4_temp | numeric | °C | 196 ~ 204 | - | matched | KNOWN | TDO 北侧 Z4 加热区温度，主导纵向拉伸时的取向与结晶，直接影响厚度与雾度 |
| `mdo_speed` | mdo_speed | numeric | m/min | 310 ~ 330 | - | matched | KNOWN | MDO 线速，与拉伸张力耦合；提速会减薄并抬高雾度 |
| `tdo_ratio` | tdo_ratio | numeric | - | 2.9 ~ 3.1 | + | matched | KNOWN | TDO 纵横向拉伸比，影响厚度均匀性 |

## 3. 响应（被优化目标）

| 列 | 名称 | 单位 | 目标 | LSL | USL | Target | 映射 | 置信 |
|---|---|---|---|---|---|---|---|---|
| `thickness_um` | thickness_um | um | target | 48.0 | 52.0 | 50.0 | matched | INFERRED |
| `haze_pct` | haze_pct | % | minimize | — | 1.8 | — | matched | INFERRED |

## 4. 关系（预期机理）

- `tdo_z4_temp` → `thickness_um`（causal，证据=physics_prior）：TDO 北侧 Z4 加热区温度，主导纵向拉伸时的取向与结晶，直接影响厚度与雾度 对 thickness_um 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- `tdo_z4_temp` → `haze_pct`（causal，证据=physics_prior）：TDO 北侧 Z4 加热区温度，主导纵向拉伸时的取向与结晶，直接影响厚度与雾度 对 haze_pct 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- `mdo_speed` → `thickness_um`（causal，证据=physics_prior）：MDO 线速，与拉伸张力耦合；提速会减薄并抬高雾度 对 thickness_um 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- `mdo_speed` → `haze_pct`（causal，证据=physics_prior）：MDO 线速，与拉伸张力耦合；提速会减薄并抬高雾度 对 haze_pct 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- `tdo_ratio` → `thickness_um`（causal，证据=physics_prior）：TDO 纵横向拉伸比，影响厚度均匀性 对 thickness_um 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）
- `tdo_ratio` → `haze_pct`（causal，证据=physics_prior）：TDO 纵横向拉伸比，影响厚度均匀性 对 haze_pct 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）

## 5. 局限

- 先验本体：关系方向来自上下文声明与物理先验，未经实测数据验证

## 6. 列映射覆盖（0 静默）

- matched: 5　inferred: 0　unmatched: 0
- coverage.ratio = 1.0（1.0 = 每个已声明因子/响应都有 matched 或 inferred+reason）

## 7. 来源

- build_mode=prior_knowledge　engine=industrial-ontology-builder
- rag_used=False　web_used=False　physics_prior_used=True
- build_seconds=0.069

> 本简报由确定性脚本生成；Agent 必须阅读本文件后写出 `01_profile/analysis_plan.md` 才能进入统计阶段（门禁 `ONTOLOGY_BRIEF_REQUIRED` / `ANALYSIS_PLAN_REQUIRED`）。
