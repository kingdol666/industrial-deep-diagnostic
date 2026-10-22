# 数据分析计划 — lekai-mixed-defects-diag（步骤 3 数据处理器）

## 0. 数据视图
- 149 批 × 51 列（1 batch_id + 1 ts_start + 1 model + 1 meters + 3 响应 + 44 过程参数）
- data_view_mode = process_plus_inspection
- 排序键：ts_start（batch_id 非时间单调）；批间隔 11–1161 min，中位 70 min

## 1. 本体驱动的分析边界
- 响应四分：total_defects（L1）、oligomer（L2）、dust（L2）、other_defects_derived（L2 残差，中位占比 62.8%）
- 混杂轴：model（9 水平）、meters（暴露）、t_index（共同漂移）
- 剔除：preprocess 生成的 *_dev 重复列（与原始列 r=1.0）

## 2. 方法与假设的对应
| 假设 | 方法 |
|---|---|
| H1 W1C 族漂移驱动残差类 | 族复合偏相关（控 model+meters）、加控时间的偏相关、变点分段重估、留一 |
| H2 F_PS005 累积-复位 | Kendall/Spearman 趋势、Pettitt 变点、分段中位、≤5 批滞后 CCF |
| H3 牌号混杂 | Kruskal、固定效应方差分解、牌号内 Spearman、分层散点 |
| H4 暴露效应 | 带牌号固定效应的 log-log 回归、meters 偏相关、密度 vs 长度 |
| H5 低聚物不可解释 | 44 参数合并/偏相关 + FDR |
| H6 dust 多源 | 趋势 + 关联全表 |

## 3. 明确不做的分析
- 批内轨迹/SPC（无批内数据）
- Granger 因果（趋势会被伪造成因果）
- 以稳态子集为主分析（慢漂移不触发稳态判据；仅作敏感性）

## 4. 交付
13 张图（6 张进 VLM）、validate_report、anomaly_report、physics_check、data_analysis_conclusion（含 analysis_directives_followed 1–7）。
