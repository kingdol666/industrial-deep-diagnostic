# Analysis plan（由 ontology_brief 生成）

- 场景 scene_key: `bopet-tdo-thickness`（profile=doe, data_stage=collected）
- 本体版本: v1 sha256=sha256:5329c7af7…

## 因子

- `tdo_z4_temp`（°C）预期方向 -：TDO 北侧 Z4 加热区温度，主导纵向拉伸时的取向与结晶，直接影响厚度与雾度
- `mdo_speed`（m/min）预期方向 -：MDO 线速，与拉伸张力耦合；提速会减薄并抬高雾度
- `tdo_ratio`（-）预期方向 +：TDO 纵横向拉伸比，影响厚度均匀性

## 响应与规格

- `thickness_um`（um）goal=target lsl=48.0 usl=52.0 target=50.0
- `haze_pct`（%）goal=minimize lsl=None usl=1.8 target=None

## 机理关系

- tdo_z4_temp → thickness_um：TDO 北侧 Z4 加热区温度，主导纵向拉伸时的取向与结晶，直接影响厚度与雾度 对 thickness_um 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- tdo_z4_temp → haze_pct：TDO 北侧 Z4 加热区温度，主导纵向拉伸时的取向与结晶，直接影响厚度与雾度 对 haze_pct 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- mdo_speed → thickness_um：MDO 线速，与拉伸张力耦合；提速会减薄并抬高雾度 对 thickness_um 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- mdo_speed → haze_pct：MDO 线速，与拉伸张力耦合；提速会减薄并抬高雾度 对 haze_pct 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- tdo_ratio → thickness_um：TDO 纵横向拉伸比，影响厚度均匀性 对 thickness_um 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）
- tdo_ratio → haze_pct：TDO 纵横向拉伸比，影响厚度均匀性 对 haze_pct 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）

## 混杂与局限

- 混杂: {'variable': 'ambient_temp', 'why': 'declared as covariate in analysis_context (may co-move with factors and responses)', 'controlled': False}
- 混杂: {'variable': 'ambient_temp', 'why': 'listed in analysis_context.covariates', 'controlled': False}
- 局限: 先验本体：关系方向来自上下文声明与物理先验，未经实测数据验证

## 映射覆盖（0 静默）

- 因子 3/3，响应 2/2，未匹配 0

## 分析模式

- designed（设计矩阵可识别）→ 效应表 + 响应面 + 联合推荐点；
  逐因子窗口仅作诊断，执行依据取 joint_setpoints（单位有效 + 无硬约束违例）。
