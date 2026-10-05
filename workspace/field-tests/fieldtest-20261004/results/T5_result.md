# T5_result.md — industrial-doe-analyzer designed 模式

**Brief 要求**：把 doe_table.csv + analysis_context.json 拷入 RUN_DIR/00_input → `analyze.py all` → quality_gate 逐项 → 中文报告（design_type/中心点/run 数、每项效应的编码系数/p/BH q、α=0.05 显著性判定、operating_windows 逐字段、最大化的调整方向，数字注明来源文件）。

**执行与退出码**：`analyze.py all --run-dir results/T5/run` → **0**（profile rows=12 design=full_factorial；run windows=2 confirmations=0 plots=4；contract grade=A authored_by=script；report.html 99897 bytes charts=10）；`quality_gate.mjs` → **0**（**21/21 ALL PASS**）。

**系统产出（关键数字，逐字）**：
- 设计识别（01_profile/data_profile.json）：**design_type=full_factorial**、mode=designed（mode_overridden=true，由 context 钉住）、**n_runs=12**（8 角点组合 + **center_points=4**）、balanced=true、axial_points=0；识别注记含 "detected after stripping 4 center rows"。
- 效应估计（02_analysis/effect_table.json，df_resid=4，df_pure_error=3，R²=0.997278，LOF p=0.8265 不显著）：
  - **显著（BH q<0.05）**：Extrusion_Temp coef=**+4.059375**（p=9.20e-6，q=**6.44e-5**，rank 1）；Draw_Ratio coef=**-3.220625**（p=2.31e-5，q=**8.09e-5**，rank 2）；Extrusion_Temp:Draw_Ratio coef=**+1.741625**（p=2.62e-4，q=**6.11e-4**，rank 3）；
  - **不显著**：Extrusion_Temp:Cooling_Rate（q=0.1211）、Cooling_Rate（q=0.6579）、Draw_Ratio:Cooling_Rate（q=0.7256）、Extrusion_Temp^2（q=0.7784）；multiple_testing=BH，7 tests，3 significant。
- 方向与操作窗（conclusions/recommendations.json）：OW-001 Draw_Ratio **[2, 3.75]**，delta=-3.220625/原始单位，confidence=high，fdr_q=8.09e-5，extrapolation=true；OW-002 Extrusion_Temp **[185, 195]**，delta=+0.405938/原始单位，fdr_q=6.44e-5，extrapolation=true。最大化方向（主效应符号 + setpoints 佐证）：**升 Extrusion_Temp、降 Draw_Ratio、Cooling_Rate 不动**；setpoints[0] raw = **Extrusion_Temp=195, Draw_Ratio=2, Cooling_Rate=25**，D=1，confidence=medium；watchlist 含 STATIONARY_POINT_WARNING（驻点鞍点/域外）。
- gate 21 项全部 PASS（FILE_*×8、G1/G3/G4/G5/G6×3/G7a-f）。

**判定**：PASS。一个粗糙点：model_spec 声明 10 项模型（含 Draw_Ratio^2、Cooling_Rate^2、三阶交互），实际只估计 7 项，未估的 3 项在 effect_table.json/model.json 中无 reason_code 或任何说明（pooled_terms=[]）——按 df 推测有意为之但产物未自解释。其余全链路一致，无阻塞。

**产物**：results/T5/run/{00_input/, 01_profile/data_profile.json, 02_analysis/{effect_table.json, model.json}, 03_figures/, conclusions/{doe_conclusion.json, recommendations.json}, report.html, run_manifest.json} + results/T5/{T5_report.md, commands.log}
