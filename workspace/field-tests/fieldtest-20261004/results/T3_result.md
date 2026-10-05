# T3_result.md — industrial-tuning-memory（归因 / 入库 / 检索 / 佐证回填）

**Brief 要求**：按 RUN_DIR 契约搭建 results/T3/run（00_input + 种子经验库）→ attribute（--settle-steps 30，逐字记录 3 条 action 的 status/reason/delta/ci95/direction/grade）→ build 入库 → recommend 检索故障签名 → feedback --result effective 回填 → 复检 recommend + quality_gate。

**执行与退出码**：attribute **0**；build **0**；recommend **0**；feedback **0**；复检 recommend **0**；gate **0**。

**系统产出（关键数字，逐字）**：
- 归因：202610041d4e2b1b（temp_c 85→77）**estimable / E1 / delta=1.9928553333333525 / ci95=[1.430640409110767, 2.555070257555938] / direction_established=true**；20261004a1309c2f（pressure_mpa 2.4→2.6）**estimable / E1 / delta=0.154487999999958 / ci95=[-0.21925685660480254, 0.5282328566047185] / direction_established=false**；20261004451edd06（speed_rpm 1250→1255 @03:17，动作后仅剩 ~3 个采样点）**not_estimable / reason_code=min_points / E0 / effect=null**（stdout 原话 "1 not_estimable (honest nulls)"）。
- 入库：created ×2（chunk_id 后缀 6d7959d486594335 / ede263eec22a6f4f）、**SKIP** 451edd06（"attribution_status=not_estimable (admission rule)"）、store=**4 entries**（2 种子 + 2 新建）。
- 检索：recommendation_status=**playbook_hit**，match_scope=**regime**，命中 exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21（PVC-M|calender-03|night_shift 处方：temp_c 85→77 + speed_rpm 1250→1238），**match_score=1**，grade E1，corroboration/refutation=1/0；degradation_path=["regime: best 1.0000 (...)","-> playbook_hit @regime"]。
- 回填：corroboration 1→**2**、grade **E1→E2**、label **observation→verified**（refutation 0 不变）；tuning_experience.jsonl 与 accumulated/state.json 中对应字段一致更新。
- 复检 recommend 反映 E2/corr=2；gate **8/8 ALL PASS**（T1-T8）。

**判定**：PASS。可估/不可估两路（诚实空值 + 准入拒绝）、regime 级命中、佐证晋升（E1→E2/verified）全链路正确且产物互相一致。无阻塞，无文档/CLI 冲突。

**产物**：results/T3/run/{00_input/, 06_experience/attribution/*.json, 06_experience/tuning_experience.jsonl, 06_experience/accumulated/state.json, conclusions/recommendation.json} + results/T3/{T3_report.md, commands.log}
