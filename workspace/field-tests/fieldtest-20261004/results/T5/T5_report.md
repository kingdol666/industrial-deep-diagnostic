# T5 结果报告 — industrial-doe-analyzer designed 模式（3 因子薄膜挤出试验）

## 逐条命令与退出码

| # | 命令 | 退出码 | 关键输出 |
|---|---|---|---|
| 1 | `mkdir -p results/T5/run/00_input` + cp doe_table.csv / analysis_context.json | 0 | RUN_DIR 就绪 |
| 2 | `analyze.py all --run-dir results/T5/run` | **0** | `[profile] rows=12 cols=5 mode=designed design=full_factorial responses=['Tear_Strength'] factors=3`；`[run] mode=designed windows=2 confirmations=0 plots=4`；`[contract] v1.0 grade=A authored_by=script`；report.html 99897 bytes charts=10 |
| 3 | `quality_gate.mjs results/T5/run --skill-path ... --shared-path ...` | **0** | `21/21 checks passed — ALL PASS`（逐项见下） |

## 设计识别（01_profile/data_profile.json → design）

- `design_type` = **full_factorial**，`mode` = **designed**（mode_overridden=true，由 analysis_context.json 的 mode_override 钉住；detection note 明确"evidence grade 不被 override"）
- `n_runs` = **12**，`n_distinct_combos` = 8，`balanced` = true（balance_ratio 1）
- `center_points` = **4**，`axial_points` = 0，`replicates` = 1
- 识别注记（原文）："LHS occupancy only 0.00 (<0.85)" / "all 8 level combos present and balanced" / "detected after stripping 4 center rows"

## 效应估计（02_analysis/effect_table.json，family Tear_Strength，n=12，df_resid=4，df_pure_error=3）

模型质量：R²=0.997278，adj R²=0.992514，Q²(LOO)=0.991998，MSE=0.163934，MDE=1.112597（编码主效应 α=0.05/power=0.8）；lack_of_fit 可估且不显著（F=0.057092，p=0.8265）。

| term | 编码系数 | p 值 | BH q 值 | q<0.05 | pareto rank |
|---|---|---|---|---|---|
| Extrusion_Temp | **+4.059375** | 9.2019e-06 | **6.4414e-05** | **显著** | 1 |
| Draw_Ratio | **-3.220625** | 2.3113e-05 | **8.0894e-05** | **显著** | 2 |
| Extrusion_Temp:Draw_Ratio | **+1.741625** | 2.6193e-04 | **6.1116e-04** | **显著** | 3 |
| Extrusion_Temp:Cooling_Rate | -0.353125 | 0.069182 | 0.121068 | 不显著 | 4 |
| Cooling_Rate | +0.114125 | 0.469955 | 0.657937 | 不显著 | 5 |
| Draw_Ratio:Cooling_Rate | +0.076375 | 0.621932 | 0.725588 | 不显著 | 6 |
| Extrusion_Temp^2 | +0.074625 | 0.778428 | 0.778428 | 不显著 | 7 |

`multiple_testing`：BH 法，1 family，7 tests，`total_significant_q05` = **3**。

**α=0.05（BH q<0.05）下的结论**：显著项 = Extrusion_Temp 主效应、Draw_Ratio 主效应、Extrusion_Temp×Draw_Ratio 交互（3 项）；不显著 = Cooling_Rate 主效应及其两个交互、Extrusion_Temp 平方项。

（观察：model_spec 还声明了 Draw_Ratio^2、Cooling_Rate^2 与三阶交互 Extrusion_Temp:Draw_Ratio:Cooling_Rate，但 effect_table.json 的 tests 只有 7 项，三者未给出任何 reason_code/说明 — 见"粗糙点"。）

## 方向与操作窗（conclusions/recommendations.json）

- **OW-001**（priority 1）：factor=Draw_Ratio，range=**[2, 3.75]**，shape=connected，expected_effect.delta=**-3.220625**（"因子 Draw_Ratio 每增加 1 个原始单位，响应 Tear_Strength 变化约 -3.220625"），confidence=high，fdr_q=8.0894e-05，extrapolation=true，confirmation_needed=false，evidence_refs=["effect_table.json#Tear_Strength.Draw_Ratio.main"]
- **OW-002**（priority 2）：factor=Extrusion_Temp，range=**[185, 195]**，expected_effect.delta=**+0.405938**（编码主效应 4.059375 / 半极差 10.0），confidence=high，fdr_q=6.4414e-05，extrapolation=true
- **最大化 Tear_Strength 的调整方向**：主效应编码系数 Extrusion_Temp +4.06（升）、Draw_Ratio -3.22（降）、Cooling_Rate +0.11（不显著，不动）→ recommendations.json 的 `setpoints[0]` 给出推荐点：coded {Extrusion_Temp: 1, Draw_Ratio: -1}，raw **Extrusion_Temp=195, Draw_Ratio=2, Cooling_Rate=25**，D=1，confidence=medium
- current_baseline（Draw_Ratio=3, Extrusion_Temp=185）两窗距离均为 0；move_instruction："优先处理 OW-001：将 Draw_Ratio 调整至 [2.0, 3.75]（当前已在窗内）"
- interactions 记录 ET×DR 交互显著（q=6.11e-4，partial η²=0.973688）
- watchlist：**STATIONARY_POINT_WARNING** — "驻点为鞍点或落在设计域外 — 仅作警告，优化请在盒约束内进行"

## gate 逐项（21/21 ALL PASS，exit 0）

FILE_context / FILE_profile / FILE_effect / FILE_model / FILE_manifest / FILE_conclusion / FILE_recs / FILE_report / G1_effect_rows_complete / G3_windows_in_domain / G4_observational_confirmation_required / G5_figures_ink_and_presence / G6_schema_validation / G6_strict_extra_keys_recommendations / G6_strict_extra_keys_conclusion / G7a_report_present_sized / G7f_report_size_cap / G7b_report_meta_sha256 / G7c_report_sections_for_mode / G7d_report_chart_readings / G7e_report_no_leaked_tokens — 全部 PASS。

## 粗糙点

1. model_spec 声明 10 项（3 主效应 + 3 平方 + 3 双因子交互 + 1 三阶交互），实际只估计 7 项；未估计的 Draw_Ratio^2 / Cooling_Rate^2 / 三阶交互在 effect_table.json 与 model.json 中均无 reason_code 或说明（pooled_terms=[]，family 内也无 dropped/excluded 字段）。按 df 推测是有意为之（12 行 8 参数后仅余 4 df），但产物未自解释。
2. 其余链路（profile→effect→recommendations→gate→report）数字互相一致，无其他问题。

## 结论

designed 模式全链路一次通过：12 行（8 角点 + 4 中心点）被识别为平衡 full_factorial；主效应 ET(+4.06)/DR(-3.22) 与 ET×DR 交互(+1.74) 显著（BH q 分别 6.4e-5 / 8.1e-5 / 6.1e-4），Cooling_Rate 各项均不显著；操作窗 Draw_Ratio [2, 3.75]、Extrusion_Temp [185, 195]；推荐配方 ET=195 / DR=2 / CR=25（D=1）。gate 21/21。无阻塞。
