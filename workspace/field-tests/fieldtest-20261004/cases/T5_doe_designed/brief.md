# T5 任务简报 — DOE 设计实验分析（industrial-doe-analyzer designed 模式）

## 场景

薄膜挤出工艺做了一组设计实验：3 个因子（挤出温度 Extrusion_Temp、牵伸比
Draw_Ratio、冷却速率 Cooling_Rate）+ 响应（撕裂强度 Tear_Strength，目标：
越大越好）。实验工程师只交给你一张按随机 run order 排列的试验表和一份
分析上下文（analysis_context.json，pin 了 designed 模式与响应/因子角色）。
请完成完整的 designed 模式分析并回答工艺问题。

## 输入（只读）

- `cases/T5_doe_designed/doe_table.csv`（列：run_order, Extrusion_Temp,
  Draw_Ratio, Cooling_Rate, Tear_Strength）
- `cases/T5_doe_designed/analysis_context.json`

## 环境（已验证的入口）

- 工作目录：`workspace/field-tests/fieldtest-20261004/`
- venv Python：
  `D:\codes\industrial-deep-diagnostic\.claude\shared\scripts\.venv\Scripts\python.exe`
  （下称 `$PY`）
- 分析脚本：
  `D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-doe-analyzer\scripts\analyze.py`
  （`analyze.py {profile|run|report|all} --run-dir <RUN_DIR>`；RUN_DIR 需含
  `00_input/` 数据与上下文）
- 门禁：
  `D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-doe-analyzer\scripts\quality_gate.mjs`
  （`node quality_gate.mjs <RUN_DIR> --skill-path <skill目录> --shared-path
  D:\codes\industrial-deep-diagnostic\.claude\shared`）

## 要求（RUN_DIR = `results/T5/run`，全部命令与退出码记入
`results/T5/commands.log`）

1. 搭建 RUN_DIR：把 `doe_table.csv` 与 `analysis_context.json` 拷入
   `results/T5/run/00_input/`。
2. 运行 `analyze.py all --run-dir results/T5/run`。
3. 运行 `quality_gate.mjs`，逐项记录 PASS/FAIL 与退出码。
4. 写中文报告 `results/T5/T5_report.md`，必须包含：
   - **设计识别**：脚本判定出的 design_type、center points 数、run 数；
   - **效应估计**：`02_analysis/effect_table.json` 中每个项（主效应、平方项、
     交互）的编码系数、p 值、BH q 值；指出在 α=0.05（BH FDR q<0.05）下哪些
     项显著、哪些不显著；
   - **方向与操作窗**：`conclusions/recommendations.json` 的
     `operating_windows`（逐字段转述 range 与 expected_effect），以及为最大化
     Tear_Strength 的调整方向（升/降哪个因子）；
   - 每个数字注明来源文件（effect_table.json / recommendations.json / …），
     不得手算或手改。
