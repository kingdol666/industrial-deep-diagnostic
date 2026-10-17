# Analysis plan（由 ontology_brief 生成）

- 场景 scene_key: `bopet-lineA-12um-tdo`（profile=doe, data_stage=collected）
- 本体版本: v1

## 因子

- `tdo_z4_temp`（°C）预期方向 +：TDO 第4区加热温度：提高取向与结晶，厚度上升、雾度上升
- `mdo_speed`（m/min）预期方向 -：MDO 车速：提高纵向拉伸，厚度下降
- `tdo_ratio`（-）预期方向 -：TDO 横向拉伸比：提高横向取向，厚度略降

## 响应与规格

- `thickness_um`（um）goal=target lsl=48.0 usl=52.0 target=50.0
- `haze_pct`（%）goal=minimize lsl=None usl=2.2 target=None
- `tensile_mpa`（MPa）goal=maximize lsl=170.0 usl=None target=None
- `gauge_mean`（um）goal=target lsl=48.0 usl=52.0 target=50.0
- `HX-PROF-PROFILES-EDGE-L-DEV`（um）goal=minimize lsl=None usl=None target=None

## 机理关系

- tdo_z4_temp → thickness_um：TDO 第4区加热温度：提高取向与结晶，厚度上升、雾度上升 对 thickness_um 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）
- tdo_z4_temp → haze_pct：TDO 第4区加热温度：提高取向与结晶，厚度上升、雾度上升 对 haze_pct 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）
- tdo_z4_temp → tensile_mpa：TDO 第4区加热温度：提高取向与结晶，厚度上升、雾度上升 对 tensile_mpa 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）
- tdo_z4_temp → gauge_mean：TDO 第4区加热温度：提高取向与结晶，厚度上升、雾度上升 对 gauge_mean 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）
- tdo_z4_temp → HX-PROF-PROFILES-EDGE-L-DEV：TDO 第4区加热温度：提高取向与结晶，厚度上升、雾度上升 对 HX-PROF-PROFILES-EDGE-L-DEV 的先验影响（方向声明 +；机理来自用户/上下文声明，尚未实测）
- mdo_speed → thickness_um：MDO 车速：提高纵向拉伸，厚度下降 对 thickness_um 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- mdo_speed → haze_pct：MDO 车速：提高纵向拉伸，厚度下降 对 haze_pct 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- mdo_speed → tensile_mpa：MDO 车速：提高纵向拉伸，厚度下降 对 tensile_mpa 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- mdo_speed → gauge_mean：MDO 车速：提高纵向拉伸，厚度下降 对 gauge_mean 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- mdo_speed → HX-PROF-PROFILES-EDGE-L-DEV：MDO 车速：提高纵向拉伸，厚度下降 对 HX-PROF-PROFILES-EDGE-L-DEV 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- tdo_ratio → thickness_um：TDO 横向拉伸比：提高横向取向，厚度略降 对 thickness_um 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）
- tdo_ratio → haze_pct：TDO 横向拉伸比：提高横向取向，厚度略降 对 haze_pct 的先验影响（方向声明 -；机理来自用户/上下文声明，尚未实测）

## 混杂与局限

- 混杂: {'variable': 'ambient_temp', 'why': 'declared as covariate in analysis_context (may co-move with factors and responses)', 'controlled': False}
- 局限: 先验本体：关系方向来自上下文声明与物理先验，未经实测数据验证

## 分析模式

- designed（CCD 设计矩阵可识别）→ 效应表 + 响应面 + 联合推荐点
- 逐因子窗口仅作诊断，执行依据取 joint_setpoints
- 异构剖面特征 HX-PROF-* 由 E-1H 提供，作为附加响应/证据，不改变因果层级
