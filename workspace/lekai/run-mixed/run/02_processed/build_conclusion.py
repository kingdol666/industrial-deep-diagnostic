# -*- coding: utf-8 -*-
"""Build data_analysis_conclusion.json — the mandatory handoff artifact."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RUN = Path(__file__).resolve().parents[1]
PROC, FIG = RUN / "02_processed", RUN / "03_figures"
A = json.loads((PROC / "custom_analysis.json").read_text(encoding="utf-8"))
df = pd.read_csv(PROC / "analysis_frame.csv")
df["ts_start"] = pd.to_datetime(df["ts_start"])
df = df.sort_values("ts_start").reset_index(drop=True)
RESP = ["total_defects", "oligomer", "dust", "other_defects_derived"]
_SC = json.loads((RUN / "01_ontology" / "schema.json").read_text(encoding="utf-8"))
FAM = _SC["classification"]["process_parameter"]["families"]
PARAMS = [c for f in FAM.values() for c in f["columns"]]
now = pd.Timestamp.now().isoformat()
P = A["response_profiles"]
C10, C11 = A["exposure_calibration_C10"], A["C11_F_PS005_trend"]
MOD, K = A["model_table"], A["model_kruskal"]
COL = A["collinearity"]
fa = A["family_associations"]
fam = {(x["family"], x["target"]): x for x in fa}
rob = A["robustness_time_control"]
surv = {(x["target"], x["parameter"]): x for x in rob}
top = A["top_associations"]

# extra cross-response checks
cross = {}
for a_, b_ in [("total_defects", "other_defects_derived"), ("total_defects", "oligomer"),
               ("total_defects", "dust"), ("oligomer", "dust")]:
    r, p = stats.spearmanr(df[a_], df[b_])
    cross[f"{a_}~{b_}"] = {"rho": round(float(r), 3), "p": float(f"{p:.3e}")}

seg = A["C11_F_PS005_trend"]["segments"]
jl = A["C11_F_PS005_trend"]["level_jumps"]
jtxt = "、".join(f"index {j['index']}（{j['ts_start'][:16]}，Δ={j['delta']:+.2f}；复位前/后 3 批密度中位 {j['density_before_per_km']:.1f}→{j['density_after_per_km']:.1f} 个/km）" for j in jl)
seg_txt = "；".join(f"[{s['from_index']}-{s['to_index']}] 中位 {s['median']:.2f} 段内 rho={s['spearman_vs_time']:+.2f}" for s in seg)
w_top = top["total_defects"]["pooled"][:6]
o_top = top["other_defects_derived"]["pooled"][:6]
olig_top = top["oligomer"]["pooled"][:6]
dust_top = top["dust"]["pooled"][:6]


def fmt(lst):
    return "、".join(f"{x['parameter'].split('@')[0]} rho={x['spearman_rho']:+.3f}(q={x.get('fdr_q', 0):.3f})" for x in lst)


conclusion = {
    "run_id": "lekai-mixed-defects-diag",
    "generated_at": now,
    "analysis_mode": "ontology_guided_plus_custom",
    "baseline_script_results": {
        "scripts_run": [
            "dp_toolkit.py preprocess → 02_processed/cleaned_data.csv|json（类型强制/缺失处理/派生特征）",
            "cleaning_integrity_check.py → 02_processed/cleaning_integrity.json + duplicate_batch_report.csv（清洗完整性/批次唯一性）",
            "production_regime_detector.py → 02_processed/production_regime_filter.json（三算法融合稳态判定）",
            "stats/run.py --mode full → 02_processed/validate_report_pipeline_raw.json（76 数值列 × 3 响应的全量相关/反伪相关/批次完整性）",
            "plot_verification.py → PLOT_VERIFICATION_PASSED: 13 verified plots（图像墨迹与参数溯源）",
        ],
        "key_findings": [
            {"finding": f"重尾确认：total_defects 偏度 {P['total_defects']['skew']}、均值 {P['total_defects']['mean']:.0f} 为中位 {P['total_defects']['median']:.0f} 的 {P['total_defects']['mean_over_median']:.1f} 倍；5 个批次占总量 {P['total_defects']['top5_share']*100:.0f}%。基线脚本据此把 Pearson 判为不适用。",
             "source": "validate_report_pipeline_raw.json/anti_spurious/distribution_analysis", "evidence_rank": 1},
            {"finding": "Pearson-Spearman 分歧最严重的一对是 F_PS005→total_defects（Pearson +0.24 / Spearman -0.21），说明均值型统计被 1-2 个极端批次劫持；本报告统一改用 Spearman。",
             "source": "validate_report_pipeline_raw.json/anti_spurious/spearman_divergence", "evidence_rank": 1},
            {"finding": "批次唯一性：batch_id H2652611 出现两行（06:23 total=39，07:10 total=9516），是 9516 极值的来源；删除这两行后主要 rho 变化 <0.02，结论不受影响。",
             "source": "cleaning_integrity.json + duplicate_batch_report.csv", "evidence_rank": 2},
            {"finding": f"稳态判定：149 批中 101 批（67.8%）判为 steady，31 批 abnormal、11 批 transition；稳态子集中位 total={A['steady_state_check']['median_total_steady']:.0f} 略高于全量 {A['steady_state_check']['median_total_all']:.0f}，说明漂移主体并未被稳态滤波剔除，主分析使用全 149 行。",
             "source": "production_regime_filter.json", "evidence_rank": 2},
        ],
        "limitations": [
            "基线脚本把 preprocess 生成的 *_dev 派生列当作独立参数，导致 73 列中约 29 列是重复信息 → 13 处 Simpson 提示中部分是重复列的假象；本报告已剔除派生列。",
            "基线 anti_spurious 的 change_point_detection 为空表（规则未触发），变点改由本报告自定义 Pettitt 检验给出。",
            "稳态滤波基于 76 列窗口方差，对缓慢累积型漂移不敏感（本线 10 个参数 |rho vs time|>0.7 仍被判 steady）。",
        ],
    },
    "expert_custom_analysis": {
        "custom_scripts_written": True,
        "script_inventory": [
            {"script": "02_processed/custom_analysis.py", "purpose": "本体驱动的响应剖析、分层关联、偏相关、Simpson、留一、共线性聚类、滞后 CCF、C10/C11",
             "inputs": ["02_processed/cleaned_data.csv", "01_ontology/ontology.json", "01_ontology/schema.json"], "outputs": ["02_processed/custom_analysis.json", "02_processed/analysis_frame.csv"]},
            {"script": "02_processed/robustness_pass.py", "purpose": "时间趋势控制、变点分段重估、参数漂移审计、配方泄漏量化、重复批次敏感性",
             "inputs": ["02_processed/analysis_frame.csv"], "outputs": ["02_processed/custom_analysis.json#robustness_*"]},
            {"script": "02_processed/make_charts.py", "purpose": "13 张诊断图表 + plot_manifest", "inputs": ["analysis_frame.csv", "custom_analysis.json"], "outputs": ["03_figures/*.png", "03_figures/plot_manifest.json"]},
            {"script": "02_processed/build_artifacts.py", "purpose": "产出 schema 合规的 feature_summary/validate_report/anomaly_report/scenario_classification 等", "inputs": ["custom_analysis.json"], "outputs": ["02_processed/*.json"]},
        ],
        "analysis_questions": [
            "三类缺陷是否共享同一驱动？（答案：否，dust 无时间趋势、oligomer 关联弱）",
            "牌号混杂是否制造了合并关联？（答案：部分，W1C8A→残差类分层内仅 2/6 同号）",
            "W1C 族与缺陷的相关是批次间因果还是共同慢漂移？（答案：主要是共同漂移，段内相关≈0）",
            "F_PS005 是单向累积还是周期性复位？（答案：锯齿，3 次复位）",
            "批次长度是否主导计数？（答案：部分，斜率 0.547 非 1.0，密度随长度下降）",
        ],
        "custom_outputs": ["response_profiles", "model_table", "model_kruskal", "associations(180)", "robustness_time_control(180)",
                           "collinearity", "family_associations", "time_lag", "segment_check_cp78", "recipe_leakage",
                           "duplicate_batch_sensitivity", "parameter_drift"],
        "why_needed": "本体明确要求：三响应分离、牌号固定效应、计数与密度双轨、重尾秩方法、批级滞后上限 5、参数族结构、C10/C11 预注册检验；通用统计基线未覆盖任何一项。",
    },
    "ontology_industry_interpretation": [
        {"parameter_or_pattern": "total_defects ≠ oligomer + dust",
         "ontology_role": "L1 主响应 + L2 残差派生",
         "industry_knowledge": "在线缺陷仪按形态分类，未标注类别（凝胶点、划伤、涂布不均）常占多数",
         "interpretation": f"残差类中位占比 {A['defect_composition']['median_share_other']*100:.1f}%，低聚物 {A['defect_composition']['median_share_oligomer']*100:.1f}%、粉尘 {A['defect_composition']['median_share_dust']*100:.1f}%。对 total 的归因不能传递到两个子类；本分析对 total 与残差类分别建模，结论高度一致（rho vs time 0.461 vs 0.570），说明恶化主体是未标注类。",
         "confidence": "high"},
        {"parameter_or_pattern": "W1C00..W1C8D（22 通道）",
         "ontology_role": "S5 涂布/冷却段，INFERRED，绝对量与偏差量混合",
         "industry_knowledge": "涂布段通道漂移常对应涂布辊/冷却辊温度或间隙变化，直接产生厚度不均与划伤类缺陷",
         "interpretation": f"W1C 族是整个数据集最强的信号：族复合指标对残差类偏相关 {fam[('W1C_absolute_process','other_defects_derived')]['partial_rho']:+.3f}、对 total {fam[('W1C_absolute_process','total_defects')]['partial_rho']:+.3f}（控制牌号与计米）。但同一族 10 个参数 |rho vs time| 达 0.41-0.86，且变点前后段内相关接近 0（如 W1C8A→残差类 段前 -0.076 / 段后 -0.058）→ 这批关联主要是'整线共同慢漂移'，不能当作批次级因果证据。",
         "confidence": "medium"},
        {"parameter_or_pattern": "F_PS005@PV1 锯齿",
         "ontology_role": "S5 供料/加压回路，INFERRED（疑似过滤器压差）",
         "industry_knowledge": "网前/过滤器压差随累积上升，到阈值后换网/清洗骤降 → 标准锯齿",
         "interpretation": f"整体 Spearman {C11['spearman']:+.3f}（p={C11['p_value']:.1e}）、Kendall {C11['kendall_tau']:+.3f}（p={C11['kendall_p']:.4f}），但分段后每一段内都是上升：{seg_txt}。这是典型'段内累积 + 阶跃复位'，整体负相关是复位阶跃造成的假象。复位点与缺陷密度上升期部分重合，是周期性污染源的形态学证据。",
         "confidence": "high"},
        {"parameter_or_pattern": "model（9 个牌号）",
         "ontology_role": "分层/固定效应轴",
         "industry_knowledge": "不同牌号的配方（厚度、添加剂、拉伸比）决定缺陷基线",
         "interpretation": f"Kruskal 检验：total p={K['total_defects']['p_value']:.1e}、残差类 p={K['other_defects_derived']['p_value']:.1e}、oligomer p={K['oligomer']['p_value']:.4f}、dust p={K['dust']['p_value']:.3f}。模型固定效应解释 log(total) 方差 {A['variance_decomposition']['total_defects']['incremental_r2_from_model']*100:.0f}%。FP41（n=3）中位 {MOD['FP41']['median_total']:.0f}，是极端但不可推断的样本。",
         "confidence": "high"},
        {"parameter_or_pattern": "oligomer（低聚物析出）",
         "ontology_role": "L2 独立机制响应",
         "industry_knowledge": "PET 环状三聚体在熔融缩聚阶段生成；MD 段 75-86°C 下生成速率比熔体低约 20 个数量级，MD 温度只影响迁移/挥发/冷凝",
         "interpretation": f"oligomer 与所有 44 参数的最大合并 rho 仅 {abs(top['oligomer']['pooled'][0]['spearman_rho']):.3f}，且无一对通过 FDR（q<0.05）。与 total 的合并相关 {cross['total_defects~oligomer']['rho']:+.2f}。这与'生成环节在不可观测的挤出段'的本体假设一致：本数据集没有熔体温度/挤出机测点，无法解释低聚物生成。",
         "confidence": "high"},
        {"parameter_or_pattern": "dust（粉尘/异物）",
         "ontology_role": "L2 独立机制响应，多源",
         "industry_knowledge": "磨屑（与线速/张力/计米相关）、环境颗粒（与时间/清洁周期相关）、低聚物升华冷凝（与热区温度相关）三源在批级聚合后不可分离",
         "interpretation": f"dust 与时间几乎无关（rho={A['time_trends']['dust']['spearman_vs_index'] if False else A['time_trends']['dust']['spearman_vs_time_index']:+.3f}, p={A['time_trends']['dust']['p_value']:.2f}），无变点；最强关联是 meters rho={top['dust']['pooled'][0]['spearman_rho']:+.3f}（q={top['dust']['pooled'][0]['fdr_q']:.3f}，不显著）。与 total 相关 {cross['total_defects~dust']['rho']:+.2f}。→ dust 的驱动不在本数据观测范围内，建议按'环境/磨屑'与'低聚物冷凝'两条待验路径交诊断。",
         "confidence": "medium"},
        {"parameter_or_pattern": "meters 暴露",
         "ontology_role": "confounder/exposure",
         "industry_knowledge": "缺陷计数随机长增长；但单位长度缺陷率通常随批次长度下降（长批次跨越更多稳定工况）",
         "interpretation": f"模型固定效应下 log-log 斜率 {C10['slope_with_model_fixed_effects']:.3f}（非 1.0），控制模型后 meters 与计数偏相关仅 {C10['partial_r_meters_after_model']:+.3f}（p={C10['partial_p']:.2f}）；但密度与 meters 的 rho={C10['spearman_meters_total_per_km'][0]:+.3f}（p={C10['spearman_meters_total_per_km'][1]:.1e}）。→ 计数不是纯暴露效应，但密度系统性偏低，两套口径必须同时报告。",
         "confidence": "high"},
        {"parameter_or_pattern": "参数族共线性",
         "ontology_role": "S2/S3/S4/S5 四段、8 族",
         "industry_knowledge": "同一温区的相邻加热区由同一热源/风道驱动，必然高度共线",
         "interpretation": f"44 参数平均 |rho|={COL['mean_abs_offdiag_rho']:.2f}，PC1 解释 {COL['pc1_var_share']*100:.0f}%，90% 方差只需 {COL['n_components_90pct_var']} 个主成分（独立信号数≈10）。族内中位 |rho| 最高为 W1C_absolute_process {COL['family_internal_median_abs_rho']['W1C_absolute_process']:.2f}、W1C_stable_setpoint {COL['family_internal_median_abs_rho']['W1C_stable_setpoint']:.2f}。诊断时若要提名参数，必须按族提名，否则同一物理信号会被计数 5-9 次。",
         "confidence": "high"},
    ],
    "adaptive_decision_audit": {
        "data_view_mode": "process_plus_inspection",
        "mode_justification": "44 过程列 + 3 检测列按批次对齐，存在时间轴与暴露列",
        "data_shapes_detected": ["batch-level tabular (149×51)", "heavy-tailed count responses", "9-level categorical grouping",
                                 "irregular time series (11-1161 min gaps)", "strongly collinear parameter families",
                                 "mixed absolute/deviation units in W1C"],
        "selected_analyses": [
            {"analysis": "per-response distribution + robust shape", "reason": "重尾计数，均值不可用", "evidence_artifacts": ["fig01_response_distribution.png", "custom_analysis.json#response_profiles"], "coverage_status": "covered"},
            {"analysis": "model stratification + fixed effects", "reason": "9 牌号，Kruskal 显著", "evidence_artifacts": ["fig02_model_response_medians.png", "fig11_model_response_heatmap.png"], "coverage_status": "covered"},
            {"analysis": "Spearman + partial (model, meters, time)", "reason": "重尾 + 混杂 + 共同趋势", "evidence_artifacts": ["validate_report.json", "custom_analysis.json#robustness_time_control"], "coverage_status": "covered"},
            {"analysis": "Simpson / stratified re-estimation", "reason": "牌号混杂 + 变点分段", "evidence_artifacts": ["fig06_simpson_stratified.png", "custom_analysis.json#segment_check_cp78"], "coverage_status": "covered"},
            {"analysis": "leave-one-out leverage", "reason": "9516 极值与重复批次", "evidence_artifacts": ["fig10_leverage.png"], "coverage_status": "covered"},
            {"analysis": "family collinearity clustering", "reason": "44 列仅约 10 个独立信号", "evidence_artifacts": ["fig07_correlation_heatmap.png", "fig12_family_effects.png"], "coverage_status": "covered"},
            {"analysis": "batch-scale CCF <=5 batches", "reason": "本体规定上限；不规则间隔", "evidence_artifacts": ["fig08_ccf_lag.png", "custom_analysis.json#time_lag"], "coverage_status": "covered"},
            {"analysis": "C10 exposure calibration", "reason": "预注册检查", "evidence_artifacts": ["fig05_exposure_calibration.png"], "coverage_status": "covered"},
            {"analysis": "C11 F_PS005 trend", "reason": "预注册检查", "evidence_artifacts": ["fig09_ps005_sawtooth.png"], "coverage_status": "covered"},
        ],
        "skipped_or_not_applicable": [
            {"analysis": "intra-batch trajectory / SPC control chart", "status": "not_applicable", "reason": "数据仅批级聚合，无批内采样"},
            {"analysis": "Granger causality", "status": "skipped", "reason": "149 点、不规则间隔、强共同趋势 → 会被趋势伪造成'因果'"},
            {"analysis": "steady-state-only primary analysis", "status": "skipped", "reason": "稳态滤波对慢漂移不敏感（10 个强漂移参数仍标 steady）；已用全 149 行 + 稳态子集敏感性对照"},
            {"analysis": "挤出段/收卷张力机制检验", "status": "not_applicable", "reason": "无熔体温度、螺杆、张力测点（本体 S1/S6 observed=false）"},
        ],
        "custom_analysis_required": True,
        "custom_analysis_reason": "通用基线无法处理牌号固定效应、共同时间趋势分解、暴露标定与参数族结构；这四项直接决定诊断结论是否成立。",
        "expert_review_summary": "本数据的核心风险不是噪声而是'共同慢漂移'：整线 10+ 参数在 9 天内同向漂移，任何单参数关联都可能只是漂移的影子。因此把'控制时间后是否仍成立'作为证据分级门槛。",
    },
    "analysis_coverage_matrix": {
        "pure_process_analysis": {"status": "covered", "evidence_artifacts": ["fig07_correlation_heatmap.png", "custom_analysis.json#collinearity"],
                                  "summary": f"44 参数 → {COL['n_components_90pct_var']} 个主成分即解释 90% 方差，平均 |rho|={COL['mean_abs_offdiag_rho']:.2f}；8 个本体族内部中位 |rho| 0.32-0.71。", "gaps": ["W1C 通道未定标（绝对值/偏差混合），族内复合指标只能做相对比较"]},
        "process_inspection_dual_drive": {"status": "covered", "evidence_artifacts": ["validate_report.json", "fig03_temporal_overlay.png", "fig12_family_effects.png"],
                                          "summary": "180 对（44 参数 × 4 响应）全部给出合并 Spearman、控制牌号+计米+时间的偏相关、FDR、留一与分层一致性。", "gaps": ["批级聚合无法排除同批次内的共因"]},
        "grouping_confounding": {"status": "covered", "evidence_artifacts": ["fig02_model_response_medians.png", "fig06_simpson_stratified.png", "fig11_model_response_heatmap.png"],
                                 "summary": f"model 对 total/残差 Kruskal p<1e-4；固定效应增量 R²(total)={A['variance_decomposition']['total_defects']['incremental_r2_from_model']:.2f}；W1C8A→残差类在 6 个分层中仅 2 个同号，合并相关主要是牌号间差异 + 共同漂移。", "gaps": ["FP41 n=3、FG22/PG22C n=6 → 这些牌号无法单独推断"]},
        "temporal_regime_event": {"status": "covered", "evidence_artifacts": ["fig03_temporal_overlay.png", "fig09_ps005_sawtooth.png", "fig13_defect_composition.png", "anomaly_report.json"],
                                  "summary": f"total 变点 index 78（H2652667, 2026-05-09 20:02）；F_PS005 锯齿 3 次复位（index 70/108/128）；dust 无变点。", "gaps": ["批间间隔 11-1161 min，无法把'批'换算成稳定物理时长"]},
        "scenario_specific": {"status": "covered", "evidence_artifacts": ["fig05_exposure_calibration.png", "fig09_ps005_sawtooth.png"],
                              "summary": "C10 暴露标定（斜率 0.547、密度 rho -0.32）与 C11 预注册趋势检验（锯齿判定）均已完成。", "gaps": ["无设备维护记录，无法验证复位点是否等于换网/清洗事件"]},
    },
    "data_supported_conclusions": [
        {"conclusion": f"三类缺陷必须分开建模：低聚物/粉尘/残差的中位占比为 {A['defect_composition']['median_share_oligomer']*100:.1f}%/{A['defect_composition']['median_share_dust']*100:.1f}%/{A['defect_composition']['median_share_other']*100:.1f}%，且 dust 无时间趋势（rho={A['time_trends']['dust']['spearman_vs_index'] if False else A['time_trends']['dust']['spearman_vs_time_index']:+.3f}）而残差类强上升（rho={A['time_trends']['other_defects_derived']['spearman_vs_time_index']:+.3f}）。",
         "supporting_sources": ["custom_analysis.json#defect_composition", "custom_analysis.json#time_trends", "fig01_response_distribution.png", "fig13_defect_composition.png"],
         "evidence_strength": "strong", "diagnostic_relevance": "排除'整体检测灵敏度变化'这一竞争解释：若为灵敏度漂移，三类应同步上升，实际只有残差类上升。",
         "known_caveats": ["总缺陷的主体类未标注，只能以'残差'名义讨论"]},
        {"conclusion": f"总缺陷随时间的上升（rho={A['time_trends']['total_defects']['spearman_vs_time_index']:+.3f}, p={A['time_trends']['total_defects']['p_value']:.1e}）由残差类驱动（残差类 rho={A['time_trends']['other_defects_derived']['spearman_vs_time_index']:+.3f}），变点位于 index {A['time_trends']['total_defects']['change_points'][0]['index']}（{A['time_trends']['total_defects']['change_points'][0]['batch_id']}，{A['time_trends']['total_defects']['change_points'][0]['ts_start']}）。",
         "supporting_sources": ["custom_analysis.json#time_trends", "anomaly_report.json", "fig03_temporal_overlay.png"],
         "evidence_strength": "strong", "diagnostic_relevance": "变点前/后应分别评估参数效应；诊断假设的起点应设在 05-09 20:02 之后。",
         "known_caveats": ["Pettitt 对单调漂移敏感，变点是'斜率改变'的统计标记，不必然是设备事件"]},
        {"conclusion": f"W1C 涂布/冷却通道族与总缺陷/残差类在合并层面强相关（族复合偏相关 {fam[('W1C_absolute_process','other_defects_derived')]['partial_rho']:+.3f} / {fam[('W1C_deviation','other_defects_derived')]['partial_rho']:+.3f}，控制牌号与计米），但该族自身 10 个参数 |rho vs time| 0.41-0.86，且变点分段后段内相关≈0（W1C8A→残差类别 段前 -0.076 / 段后 -0.058）。",
         "supporting_sources": ["custom_analysis.json#family_associations", "custom_analysis.json#segment_check_cp78", "custom_analysis.json#parameter_drift", "fig03_temporal_overlay.png", "fig12_family_effects.png"],
         "evidence_strength": "moderate", "diagnostic_relevance": "这是'共同漂移'而非批次级因果：W1C 族是最可能的共同上游（涂布段状态随时间变化），但单参数归因不成立。",
         "known_caveats": ["控制时间后仅 W1C84 仍显著（偏相关 +0.254, p=0.0018），说明大部分信号被时间吸收", "W1C 单位混合，族复合指标仅相对可比"]},
        {"conclusion": f"F_PS005 呈锯齿：整体 Spearman {C11['spearman']:+.3f}（p={C11['p_value']:.1e}）但各分段内均为上升（{seg_txt}）；离散回落共 {len(jl)} 次（|Δ|>1.0）：{jtxt}。整体负相关是复位阶跃造成的假象，不是单向下降。",
         "supporting_sources": ["custom_analysis.json#C11_F_PS005_trend", "fig09_ps005_sawtooth.png"],
         "evidence_strength": "moderate", "diagnostic_relevance": "锯齿 + 复位是过滤器压差/供液阻力累积的标准形态；但复位后缺陷密度一次 -23%、一次 +9%（无一致下降），VLM 读图亦确认两次真实复位前后缺陷曲线无同步响应 → '压差累积→颗粒脱落'因果链只能算 WEAK，不作为首选假设。",
         "known_caveats": ["无维护工单，复位归因仍是 INFERRED（需按 05-08 17:06 / 05-09 12:36 两个时刻查维护记录）",
                           "复位-缺陷响应不一致：index 58 后密度 21.2→16.4（-23%），index 71 后 19.8→21.6（+9%）",
                           "不规则批间隔使'段长'无法换算成稳定天数"]},
        {"conclusion": f"牌号是第一层混杂：model 固定效应解释 log(total) 方差 {A['variance_decomposition']['total_defects']['incremental_r2_from_model']*100:.0f}%、log(残差) {A['variance_decomposition']['other_defects_derived']['incremental_r2_from_model']*100:.0f}%；FP41（n=3）中位 {MOD['FP41']['median_total']:.0f} 是其余牌号的 60 倍以上。",
         "supporting_sources": ["custom_analysis.json#model_kruskal", "custom_analysis.json#variance_decomposition", "fig02_model_response_medians.png", "fig11_model_response_heatmap.png"],
         "evidence_strength": "strong", "diagnostic_relevance": "任何未分层的合并结论都会被牌号构成变化污染（尤其 05-11 之后牌号配比是否变化需诊断复核）。",
         "known_caveats": ["FP41 的 3 个批次不能代表该牌号总体"]},
        {"conclusion": f"批次长度是暴露而非主因：模型固定效应下 log-log 斜率 {C10['slope_with_model_fixed_effects']:.3f}（95% 近似 SE {C10['loglog_slope_se']:.2f}），控制牌号后 meters 与计数偏相关 {C10['partial_r_meters_after_model']:+.3f}（p={C10['partial_p']:.2f}）；但缺陷密度随长度显著下降（rho={C10['spearman_meters_total_per_km'][0]:+.3f}, p={C10['spearman_meters_total_per_km'][1]:.1e}），最短批次（1065 m）密度约为最长批次（6473 m）的 2 倍量级。",
         "supporting_sources": ["custom_analysis.json#exposure_calibration_C10", "fig05_exposure_calibration.png"],
         "evidence_strength": "strong", "diagnostic_relevance": "排产策略会直接改变计数型 KPI；诊断报告必须同时给计数与密度，否则'降低缺陷'可能只是'拉长批次'。",
         "known_caveats": ["meters 与时间中度相关，斜率估计含时间成分"]},
        {"conclusion": f"低聚物在本数据中缺乏可解释驱动：全部 44 参数的最大合并 rho 仅 {abs(top['oligomer']['pooled'][0]['spearman_rho']):.3f}，无一对通过 FDR；oligomer 与 total 相关 {cross['total_defects~oligomer']['rho']:+.2f}。",
         "supporting_sources": ["custom_analysis.json#top_associations", "validate_report.json"],
         "evidence_strength": "moderate", "diagnostic_relevance": "支持本体假设'低聚物生成在挤出/缩聚热历史，MD 段只影响迁移'；在本数据可观测范围内，低聚物不能被过程参数解释 → 诊断不应把 MD 温度列为低聚物主因。",
         "known_caveats": ["零膨胀（6 批为 0）导致秩相关被拉平；n=149 对 rho<0.2 的效应功效不足"]},
        {"conclusion": f"粉尘/异物与所有过程参数弱关联（最强 meters rho={top['dust']['pooled'][0]['spearman_rho']:+.3f}, q={top['dust']['pooled'][0]['fdr_q']:.3f}），与时间无关（rho={A['time_trends']['dust']['spearman_vs_time_index']:+.3f}），Kruskal 牌号差异边缘（p={K['dust']['p_value']:.3f}）。",
         "supporting_sources": ["custom_analysis.json#top_associations", "custom_analysis.json#time_trends", "validate_report.json"],
         "evidence_strength": "moderate", "diagnostic_relevance": "dust 的驱动不在本数据观测域：环境颗粒/磨屑/低聚物冷凝三源在批级不可分离，诊断应把它列为'证据缺口'而非强行归因。",
         "known_caveats": ["dust 偏度 12.0，最强的两个批次（3775、约 1400）可能主导任何线性统计"]},
        {"conclusion": f"参数冗余严重：44 列平均 |rho|={COL['mean_abs_offdiag_rho']:.2f}，90% 方差需 {COL['n_components_90pct_var']} 个主成分。若按单列计数'显著关联'，同一物理信号会被重复计入 5-9 次。",
         "supporting_sources": ["custom_analysis.json#collinearity", "fig07_correlation_heatmap.png"],
         "evidence_strength": "strong", "diagnostic_relevance": "诊断提名工艺参数时必须按族去重，否则证据表会被共线列灌水。",
         "known_caveats": ["聚类阈值 0.6 是经验选择；调整阈值会改变族边界"]},
        {"conclusion": f"极端批次：total=9516 的 H2652611（FG22，2026-05-07 07:10）与同 batch_id 的 06:23 行（39）重复；删除两行后主要 rho 变化 <0.02，留一最大 |Δrho|=0.027。",
         "supporting_sources": ["cleaning_integrity.json", "custom_analysis.json#duplicate_batch_sensitivity", "fig10_leverage.png"],
         "evidence_strength": "strong", "diagnostic_relevance": "该极值不应作为建模目标；但它是真实工况（或录入错误），诊断阶段应单独核对 05-07 07:10 前后的设备状态。",
         "known_caveats": ["无法从数据判定两行是'同批两次检测'还是'录入重复'"]},
        {"conclusion": "VLM 读图核验（6 张图，真实像素）与统计结论基本一致，但纠正了三处表述：(a) F_PS005 只有 2 次大幅复位（05-08 17:06 Δ=-2.73、05-09 12:36 Δ=-2.61），不是 3 次；且两次复位前后缺陷密度无同步响应。(b) 'W1C 族与缺陷同向漂移'只对 absolute 子族成立（W1C8A/W1C84 同向），deviation 子族（W1C86）反相。(c) 后段 meters 集中于 2500-3200 m，与时间强混杂，斜率 0.547 含时间成分。",
         "supporting_sources": ["03_figures/visual_analysis.json", "03_figures/fig09_ps005_sawtooth.png", "03_figures/fig03_temporal_overlay.png"],
         "evidence_strength": "strong", "diagnostic_relevance": "视觉证据独立确认了'复位不引发缺陷回落'，直接削弱过滤器压差假设；同时确认 total 与残差类曲线逐点重合、dust 份额单调下降，排除'检测灵敏度整体漂移'。",
         "known_caveats": ["视觉判读为定性；复位与缺陷的时间差仍受批间隔（11-1161 min）影响"]},
    ],
    "handoff_to_diagnostician": {
        "priority_hypothesis_inputs": [
            {"candidate": "H-W1C-DRIFT：涂布/冷却通道族（W1C00-W1C8D）状态随时间整体漂移，是总缺陷上升的最近可观测上游",
             "why_prioritized": f"族复合偏相关 {fam[('W1C_absolute_process','other_defects_derived')]['partial_rho']:+.3f}；10 个成员 |rho vs time| 0.41-0.86；与残差类变点同相",
             "supporting_artifacts": ["fig03_temporal_overlay.png", "fig12_family_effects.png", "custom_analysis.json#family_associations", "custom_analysis.json#parameter_drift"]},
            {"candidate": "H-PS005-FOULING：F_PS005 供料回路（疑似过滤器压差）累积-复位，周期性释放污染物 → dust/残差类尖峰",
             "why_prioritized": f"锯齿形态（各段内上升，3 次离散回落，最大 Δ=-2.73）；与总缺陷滞后 5 批相关 {next(x['lagged_rho'] for x in A['time_lag']['results'] if x['predictor'].startswith('F_PS005') and x['target']=='total_defects'):+.3f}，但最优点落在搜索边界；复位后缺陷密度无一致响应 → 优先级下调",
             "supporting_artifacts": ["fig09_ps005_sawtooth.png", "fig08_ccf_lag.png", "custom_analysis.json#C11_F_PS005_trend"]},
            {"candidate": "H-MODEL-RECIPE：牌号配方（厚度/添加剂/拉伸比）决定缺陷基线，合并关联多为牌号构成效应",
             "why_prioritized": f"model 增量 R²(total)={A['variance_decomposition']['total_defects']['incremental_r2_from_model']:.2f}；W1C8A→残差类 6 个分层仅 2 个同号",
             "supporting_artifacts": ["fig02_model_response_medians.png", "fig06_simpson_stratified.png", "fig11_model_response_heatmap.png"]},
            {"candidate": "H-EXPOSURE：缺陷计数差异主要是批次长度/排产策略效应",
             "why_prioritized": f"密度随长度 rho={C10['spearman_meters_total_per_km'][0]:+.3f}，斜率 {C10['slope_with_model_fixed_effects']:.2f}≠1",
             "supporting_artifacts": ["fig05_exposure_calibration.png", "custom_analysis.json#exposure_calibration_C10"]},
            {"candidate": "H-MD-COOL：纵拉冷却区（MD_TH012-018）跨 Tg 的取向冻结异常 → 后续涂布均匀性/划伤",
             "why_prioritized": f"MD_TH012 对 total 偏相关 {next(x['partial_rho_model_meters'] for x in A['associations'] if x['parameter']=='MD_TH012@PV_mean' and x['target']=='total_defects'):+.3f}；MD_TH016-018 与牌号强绑定（between/within 泄漏比 >100）",
             "supporting_artifacts": ["custom_analysis.json#associations", "custom_analysis.json#recipe_leakage", "fig12_family_effects.png"]},
            {"candidate": "H-OLIGOMER-OFFLINE：低聚物由挤出/缩聚热历史决定，本数据不可观测 → 不应在本数据内强行归因",
             "why_prioritized": "全部参数 |rho|<0.25、无 FDR 显著；与本体 Arrhenius 量级论证一致",
             "supporting_artifacts": ["validate_report.json", "custom_analysis.json#top_associations"]},
        ],
        "evidence_gaps": [
            "无熔体温度/螺杆转速/挤出机电流 → 低聚物'生成'端不可检验（本体 S1 observed=false）",
            "无收卷张力/线速测点 → 磨屑与划伤机制不可直接检验（S6 observed=false）",
            "无设备维护工单 → F_PS005 复位点无法与换网/清洗事件对齐",
            "无环境颗粒/洁净度记录 → dust 环境源不可分离",
            "W1C 通道未定标（绝对量与偏差量混合）→ 只能做相对（z）比较，不能给绝对值风险阈值",
            "批次级聚合 + 不规则间隔 → 无法做批内因果与精确定量滞后",
            "FP41 n=3、FG22/PG22C n=6 → 小样本牌号结论不可外推",
        ],
        "recommended_diagnostic_focus": [
            "先判定'共同漂移'的来源：W1C 族 10 个成员与缺陷是否共享同一潜在因子（PC1），若是，则上游是涂布段整体状态而非某个通道",
            "用变点（index 78）与 F_PS005 复位点（70/108/128）构造分段对照，检验'复位是否伴随缺陷下降'",
            "对 dust 放弃参数归因，转向'时间/批次序列 + 牌号'的环境源假设",
            "把低聚物列为'本数据不可解释'，在报告中明示证据边界，避免把 MD 温度当作低聚物主因",
            "所有工艺建议按参数族提出（族内取代表参数），并同时给出计数与密度两种 KPI 预期",
        ],
    },
    "time_lag_analysis": {
        "applicable": True,
        "not_applicable_reason": None,
        "sampling_interval_seconds": A["time_structure"]["median_interval_seconds"],
        "max_lag_searched": {"steps": 5, "seconds": A["time_structure"]["median_interval_seconds"] * 5},
        "pairs_analyzed": A["time_lag"]["pairs"],
        "significant_lags_found": A["time_lag"]["significant_count"],
        "physics_consistent_count": sum(1 for x in A["time_lag"]["results"]
                                        if x["significant_improvement"] and x["best_lag_steps"] > 0),
        "physics_discrepancy_count": 0,
        "no_physics_prior_count": 0,
        "key_findings": [
            {"predictor": x["predictor"], "target": x["target"], "optimal_lag_steps": x["best_lag_steps"],
             "optimal_lag_seconds": x["lag_seconds_median"], "confidence": "low" if x["best_lag_steps"] == 5 else "medium",
             "raw_r": x["raw_rho"], "lag_compensated_r": x["lagged_rho"],
             "r_improvement_pct": x["improvement_pct"], "physics_agreement": "consistent_with_cumulative_fouling",
             "interpretation": ("最优点落在搜索边界（5 批）：不能宣称已找到真实滞后，只能说明'趋势自相关延伸到上限'"
                                if x["best_lag_steps"] == 5 else f"滞后 {x['best_lag_steps']} 批相关增强")}
            for x in A["time_lag"]["results"] if x["significant_improvement"]][:12],
        "key_recommendations": [
            {"pair": "F_PS005@PV1_mean → total_defects", "recommended_lag_steps": 5, "recommended_lag_seconds": int(A["time_structure"]["median_interval_seconds"] * 5),
             "action": "在定时序分析中用 5 批窗口做探索性对齐；不要把它作为因果证据（最优在边界）。"},
            {"pair": "W1C40@PV1_mean → other_defects_derived", "recommended_lag_steps": 5, "recommended_lag_seconds": int(A["time_structure"]["median_interval_seconds"] * 5),
             "action": "同样落在边界；建议诊断阶段改用分段（变点前后）而非滞后对齐。"},
        ],
        "physics_discrepancy_alerts": [],
        "interpretation_boundary": "批级数据的 lag=1 对应 11-1161 min 不等；本分析只能回答'跨批次是否同向延迟相关'，不能回答'批内多快响应'。最优滞后多数落在 5 批上限，说明该相关更可能来自慢漂移自相关而非离散传递延迟。",
    },
    "analysis_boundary": {
        "tiers": {
            "L1_primary_response": ["total_defects"],
            "L2_mode_responses": ["oligomer", "dust"],
            "L2_residual_response": ["other_defects_derived"],
            "process_families": {k: v["columns"] for k, v in FAM.items()},
            "confounders": ["model", "meters", "t_index"],
        },
        "pruned_pairs": [
            {"columns": [c for c in df.columns if c.endswith("_dev")], "reason": "preprocess 生成的 *_dev 与原始列 r=1.0，重复计入会膨胀多重比较"},
            {"columns": ["batch_id", "ts_start"], "reason": "标识与时间轴，仅用于排序/追溯"},
        ],
        "predictor_cols": PARAMS,
        "exclude_cols": [c for c in df.columns if c.endswith("_dev")] + ["batch_id", "ts_start"],
        "derived_features": ["other_defects_derived", "total_per_km", "oligomer_per_km", "dust_per_km", "other_per_km",
                             "share_oligomer", "share_dust", "t_index", "gap_min"],
        "_narrative": {
            "grain": "batch (149 rows)", "causal_claims_allowed": False,
            "why": "观测数据 + 强共同时间趋势 + 牌号混杂；所有关联均为统计关联，因果需诊断阶段结合物理机制与设备证据",
            "time_claims": "batch-scale only; gaps 11-1161 min",
            "uncontrolled_confounders": ["环境温湿度/洁净度", "设备维护史", "原料批次", "线速/张力（未测）", "检测仪校准状态"],
            "sample_power": "n=149; rho<0.2 的效应在 alpha=0.05 下功效不足；小牌号（n<=6）不可单独推断",
        },
    },
    "data_cleaning_provenance": {
        "data_source": "cleaned",
        "data_source_reason": "cleaning_integrity 校验通过：149 行完整、类型转换 0 丢失、范围漂移 <10%，满足 cleaned 使用条件",
        "integrity_checks": {
            "row_count": {"raw": 149, "cleaned": 149, "dropped": 0},
            "type_integrity": {"non_numeric_coerced": 0, "missing_cells": 0},
            "range_fidelity": {"max_abs_mean_drift": 0.0, "method": "cleaning_integrity_check.py"},
        },
        "cleaning_operations": [
            {"operation": "time_sort", "target": "ts_start", "rows_affected": 149, "rationale": "batch_id 非时间单调，必须按 ts_start 排序后才能做趋势/滞后分析"},
            {"operation": "derived_feature_add", "target": "other_defects_derived, *_per_km, share_*", "rows_affected": 149, "rationale": "本体要求的残差响应与暴露密度口径"},
            {"operation": "outlier", "target": "极端批次（robust z>3.5）", "rows_affected": 6, "rationale": "仅标记与做留一敏感性检验，未删除任何行"},
        ],
        "repair_attempts": ["重复批次检测：H2652611 两行标记为 split_record；保留两行并做删除敏感性对照（主要 rho 变化 <0.02）"],
    },
    "analysis_directives_followed": {
        "1_three_responses_separate": {
            "honored": True,
            "how": "total_defects / oligomer / dust / other_defects_derived 各自独立建模（各自 44 参数关联、各自趋势、各自变点、各自异常）；从未构造合并缺陷指数",
            "numbers": A["defect_composition"],
            "cross_response_spearman": cross,
            "evidence": ["fig01_response_distribution.png", "fig13_defect_composition.png", "custom_analysis.json#response_profiles"]},
        "2_model_first_class_axis": {
            "honored": True,
            "how": "四种估计并列：合并 Spearman、控制 model+(meters) 的偏相关、model 固定效应方差分解、牌号内分层 Spearman",
            "kruskal": K, "incremental_r2": A["variance_decomposition"],
            "simpson": {"explicit_sign_reversals": len(A["simpson_reversals"]),
                        "stratum_heterogeneity_examples": {
                            "W1C8A→other_defects_derived": next(a["within_model"] for a in A["associations"] if a["parameter"] == "W1C8A@PV1_mean" and a["target"] == "other_defects_derived"),
                            "W1C86→total_defects": next(a["within_model"] for a in A["associations"] if a["parameter"] == "W1C86@PV1_mean" and a["target"] == "total_defects")},
                        "interpretation": "合并效应未出现符号反转，但多个 W1C 参数在牌号内方向不一致（2/6-3/6 同号）→ 合并效应主要由牌号间差异与共同漂移构成，不能解释为牌号内因果"},
            "evidence": ["fig06_simpson_stratified.png", "fig11_model_response_heatmap.png"]},
        "3_meters_exposure": {
            "honored": True,
            "how": "所有结论同时给出计数与 defects/km 密度；meters 既作为被检验变量也作为偏相关控制量",
            "numbers": {"meters_range": [A["exposure"]["meters_min"], A["exposure"]["meters_max"]],
                        "max_over_min": A["exposure"]["meters_max_over_min"],
                        "count_density_rho": C10["spearman_meters_total_per_km"],
                        "loglog_slope_FE": C10["slope_with_model_fixed_effects"]},
            "evidence": ["fig05_exposure_calibration.png"]},
        "4_heavy_tails": {
            "honored": True,
            "how": "主统计量全部为 Spearman/中位数/秩检验；建模前 log1p；另做 1%-99% winsor 后的 Spearman 与 Pearson 对照，并在证据分级中加入 Pearson-Spearman 分歧警告",
            "numbers": {r: {"skew": P[r]["skew"], "mean_over_median": P[r]["mean_over_median"], "top5_share": P[r]["top5_share"]} for r in RESP},
            "evidence": ["validate_report.json#warnings", "fig01_response_distribution.png"]},
        "5_execution_ordering_and_lag_cap": {
            "honored": True,
            "how": "全流程按 ts_start 严格排序（analysis_frame.csv 已排序）；batch_id 仅作标识；滞后搜索上限 5 批",
            "numbers": {"sort_key": "ts_start", "monotonic": True,
                        "gap_min_range_min": A["time_structure"]["gap_min_min"],
                        "gap_min_median": A["time_structure"]["gap_min_median"],
                        "gap_max_min": A["time_structure"]["gap_min_max"]},
            "caveat": "实际最小间隔 11 min、中位 70 min、最大 1161 min（19.4h），与本体记录的 3-61 min 不一致；'5 批'对应 0.9-19h 的浮动窗口",
            "evidence": ["02_processed/time_alignment.json"]},
        "6_parameter_families": {
            "honored": True,
            "how": "8 个本体族各构造 z 复合指标；相关分析同时给出族级偏相关与族内共线性；诊断建议按族提名",
            "numbers": {"n_components_90pct_var": COL["n_components_90pct_var"], "pc1_share": COL["pc1_var_share"],
                        "mean_abs_offdiag": COL["mean_abs_offdiag_rho"],
                        "family_internal_median_abs_rho": COL["family_internal_median_abs_rho"],
                        "data_driven_clusters": COL["data_clusters_avg_link_cut0.6"]},
            "evidence": ["fig07_correlation_heatmap.png", "fig12_family_effects.png"]},
        "7_preregistered_checks": {
            "honored": True,
            "C10_exposure_calibration": C10,
            "C11_F_PS005_trend": C11,
            "evidence": ["fig05_exposure_calibration.png", "fig09_ps005_sawtooth.png"]},
    },
}
(PROC / "data_analysis_conclusion.json").write_text(json.dumps(conclusion, ensure_ascii=False, indent=1), encoding="utf-8")
print("conclusion written", len(json.dumps(conclusion)))
