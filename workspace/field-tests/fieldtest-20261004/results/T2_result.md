# T2_result.md — industrial-sentinel（建档 / watch / fast-screen）

**Brief 要求**：history.csv 建档（注册 DOE 先验操作窗）→ fast-screen 正常窗/漂移窗 → watch 批筛变点窗/漂移窗 → 无基线快筛拒跑场景 → 对两个 watch alert 跑 quality_gate → 中文报告（退出码逐字、告警清单、projection_summary、exit 2 契约引用）。

**执行与退出码（逐字）**：build_baseline **0**；fast normal **0**（alerts=0）；fast drift **1**（alerts=7）；watch changepoint **1**（alerts=3）；watch drift **1**（alerts=9）；orphan 无基线 **2**（"no baseline (...) — refusing to run (exit 2)"，不产出 alert）；gate ×2 均 **0**（6/6 PASS）。

**系统产出（关键数字）**：DOE 先验 speed_rpm [1225,1275] 操作窗逐字段注册进 baseline.groups.__ALL__.operating_windows。正常窗 0 告警。漂移窗 fast 7 条全在 speed_rpm（ROBUST_Z_OUTLIER ×2 high、NELSON_R1 ×2 high、R5/R6 high、R2 warn）；watch 9 条，额外 WINDOW_DRIFT_PROJECTION high（slope_per_hour=3.605815555555561，**hours_to_edge=3.4438713818479867**，direction=up）+ VARIANCE_RATIO_HIGH ratio=11.937。变点窗 3 条定位在 temp_c：ROBUST_Z_OUTLIER high（n=113）、REGIME_CHANGE_NEW warn（**cp_position=121**）、VARIANCE_RATIO_HIGH warn（ratio=34.7975）；speed_rpm 投影 level=info（hours_to_edge 5228h）。exit 2 语义与恢复路径在 sentinel_fast.py docstring（L15-21）与 SKILL.md（"exit 2 拒跑——先建基线"）均有原文。

**判定**：PASS。四种场景行为全部符合契约语义（0/1/2 退出码、告警分级、投影到 DOE 窗、无基线拒跑），gate 6/6 ×2。无阻塞，无文档/CLI 冲突。

**产物**：results/T2/{baseline/watch_baseline.json, screen_normal/, screen_drift/, watch_changepoint/, watch_drift/, orphan_out/stdout_stderr.txt, T2_report.md, commands.log}
