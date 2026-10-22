# -*- coding: utf-8 -*-
"""Build all remaining CP-4 artifacts from custom_analysis.json + pipeline outputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RUN = Path(__file__).resolve().parents[1]
PROC, FIG = RUN / "02_processed", RUN / "03_figures"
A = json.loads((PROC / "custom_analysis.json").read_text(encoding="utf-8"))
schema = json.loads((RUN / "01_ontology" / "schema.json").read_text(encoding="utf-8"))
FAM = schema["classification"]["process_parameter"]["families"]
PARAMS = [c for f in FAM.values() for c in f["columns"]]
PARAM_FAMILY = {c: k for k, f in FAM.items() for c in f["columns"]}
RESP = ["total_defects", "oligomer", "dust", "other_defects_derived"]
CN = {"total_defects": "缺陷总数", "oligomer": "低聚物", "dust": "粉尘/异物",
      "other_defects_derived": "未分类残差"}
df = pd.read_csv(PROC / "analysis_frame.csv")
df["ts_start"] = pd.to_datetime(df["ts_start"])
df = df.sort_values("ts_start").reset_index(drop=True)
now = pd.Timestamp.now().isoformat()
TS = lambda x: pd.Timestamp(x).isoformat()

# ============ feature_summary ============
cols = {}
role_of = {}
for c in RESP:
    role_of[c] = "target"
for c in PARAMS:
    role_of[c] = "process_parameter"
role_of.update({"batch_id": "metadata", "ts_start": "time", "model": "group", "meters": "confounder"})
for r in ["total_per_km", "oligomer_per_km", "dust_per_km", "other_per_km"]:
    role_of[r] = "derived_target"
for c in df.columns:
    if c in role_of:
        continue
    role_of[c] = "derived" if c.endswith(("_robust_z",)) else "metadata"
for c in df.columns:
    s = df[c]
    if pd.api.types.is_numeric_dtype(s):
        cols[c] = {"dtype": "numeric", "role": role_of.get(c, "metadata"),
                   "mean": round(float(s.mean()), 4), "std": round(float(s.std()), 4),
                   "min": round(float(s.min()), 4), "max": round(float(s.max()), 4),
                   "median": round(float(s.median()), 4),
                   "missing": int(s.isna().sum()), "unique": int(s.nunique())}
    else:
        cols[c] = {"dtype": "categorical", "role": role_of.get(c, "metadata"),
                   "missing": int(s.isna().sum()), "unique": int(s.nunique()),
                   "top_values": s.value_counts().head(5).to_dict() if c != "ts_start" else None}
fs = {
    "columns": cols,
    "dataset_profile": {
        "row_count": int(len(df)), "column_count": int(len(df.columns)),
        "time_range": {"start": float(df.ts_start.iloc[0].timestamp()), "end": float(df.ts_start.iloc[-1].timestamp()),
                       "duration": float(df.ts_start.iloc[-1].timestamp() - df.ts_start.iloc[0].timestamp()),
                       "human_readable": [str(df.ts_start.iloc[0]), str(df.ts_start.iloc[-1])]},
        "product_groups": sorted(df.model.unique().tolist()),
        "group_sizes": df.model.value_counts().to_dict(),
        "time_column": "ts_start",
        "group_column": "model",
        "sort_key": "ts_start",
    },
    "metadata": {"generated_by": "data-processor (dp_toolkit preprocess + custom_analysis)", "data_source": "cleaned",
                 "timestamp": now},
}
(PROC / "feature_summary.json").write_text(json.dumps(fs, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ pre_profile ============
pre = {
    "generated_by": "data-processor Phase 0 (independent of ontology semantics)",
    "format": {"original_file": "00_input/batches.csv", "rows_raw": 149, "cols_raw": 51,
               "delimiter": ",", "encoding": "utf-8", "time_format": "YYYY-MM-DD HH:MM:SS"},
    "quality": {"missing_cells": int(df.isna().sum().sum()), "duplicate_batch_ids": ["H2652611"],
                "duplicate_rows": A["duplicate_batch_sensitivity"]["duplicate_rows"],
                "constant_columns": [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() <= 1],
                "zero_inflated_targets": {r: A["response_profiles"][r]["zero_rows"] for r in RESP[:3]}},
    "time": A["time_structure"],
    "production_state": {"method": "three-algorithm fusion (production_regime_detector)", **A["steady_state_check"]},
    "distribution_shape": {r: {"median": A["response_profiles"][r]["median"], "mean": A["response_profiles"][r]["mean"],
                               "skew": A["response_profiles"][r]["skew"]} for r in RESP},
    "recommended_transforms": {"responses": "log1p + rank statistics", "parameters": "z-score per family for composites"},
}
(PROC / "pre_profile.json").write_text(json.dumps(pre, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ data_view_mode ============
dvm = {"data_view_mode": "process_plus_inspection",
       "justification": "44 个工艺/回路过程列（F_PS 4 + MD_TH 18 + W1C 22）+ 3 个缺陷检测列，二者按批次一一对齐；存在 batch 级时间戳与 exposure 列，可做过程-检测联合分析。",
       "targets": ["total_defects", "oligomer", "dust", "other_defects_derived"],
       "predictors": 44, "confounders": ["model", "meters", "t_index"],
       "grain": "one row = one production batch", "time_column": "ts_start"}
(PROC / "data_view_mode.json").write_text(json.dumps(dvm, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ scenario_classification ============
sc = {
    "scene_type": "batch_process_quality_defect_attribution", "process_category": "BOPET film MD-stretch + coating line",
    "confidence": "high",
    "classification_basis": [
        "本体 process_type: 双向拉伸聚酯薄膜（BOPET）涂布-拉伸产线",
        "row grain = 1 batch，149 批，9 个牌号，批次长度 meters 1065-6473 m",
        "3 个检测响应 + 1 个派生残差响应，44 个过程/回路参数，重尾计数型响应",
        "批次级时间戳不规则（11-1161 min），无批内高频轨迹 → 只能做批级关联与批级滞后",
    ],
    "ontology_available": True,
    "adaptive_visualization_plan": {
        "time_series_required": True, "scatter_plots_required": True, "heatmap_required": True,
        "ccf_lag_analysis": True, "transition_analysis": True, "batch_cycle_overlay": True,
        "quality_reset_check": True,
        "custom_strategies": [
            "三类响应分别建模，不合并（total != oligomer+dust）",
            "牌号分层 + 固定效应双重估计，Simpson 检查",
            "计数与缺陷密度双轨报告（暴露分母 meters）",
            "参数族复合指标替代 44 列独立比较",
        ]},
    "expected_physics": [
        "oligomer: 扩散控制表面析出 C_surf≈C_bulk[1-exp(-Dt/L²)]，D=D0exp(-Ea/RT)；MD 段 75-86°C 下生成速率极低 → MD 温度只影响迁移",
        "dust: 多源（磨屑/环境颗粒/低聚物升华冷凝），batch 级不可分离",
        "total/other: 涂布均匀性与划伤类，理论上与 W1C 通道（涂布/冷却）和张力/线速相关",
        "MD 冷却区跨过 Tg（26-41°C）→ 取向冻结，温度异常影响薄膜平整度与后续涂布",
    ],
    "degradation_candidates": [
        "W1C 涂布/冷却通道族随时间整体漂移（10 个参数 |rho vs time|>0.7）",
        "F_PS005 供料回路锯齿（段内上升 + 3 次阶跃复位）",
        "牌号配方差异（FP41 n=3 中位 4145，极端）",
        "批次长度暴露效应（密度随 meters 下降 rho=-0.32）",
    ],
}
(PROC / "scenario_classification.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ time_alignment ============
ta = {"time_column": "ts_start", "parsed_format": "%Y-%m-%d %H:%M:%S", "rows_total": int(len(df)),
      "rows_unparsable_dropped": 0, "monotonic_after_sort": bool(df.ts_start.is_monotonic_increasing),
      "duplicate_timestamps": int(df.ts_start.duplicated().sum()),
      "median_interval_seconds": A["time_structure"]["median_interval_seconds"],
      "interval_min_seconds": A["time_structure"]["gap_min_min"] * 60,
      "interval_max_seconds": A["time_structure"]["gap_min_max"] * 60,
      "span_hours": A["time_structure"]["span_hours"],
      "axis_provenance": "real parsed timestamps (not index-implied)",
      "note": "批间间隔极不规则（11-1161 min），因此任何'滞后 N 批'都对应浮动的物理时长；滞后结论只能定性。"}
(PROC / "time_alignment.json").write_text(json.dumps(ta, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ analysis_parameter_selection ============
sel = {
    "decision": "analyse all 44 process parameters, but at family level for interpretation; 3 responses + 1 derived residual",
    "selected": [{"group": k, "columns": v["columns"], "n": len(v["columns"]),
                  "reason": "本体定义的过程族，语义置信度 " + v["semantic_confidence"]} for k, v in FAM.items()],
    "responses": {"total_defects": "L1 主响应", "oligomer": "L2 独立机制", "dust": "L2 独立机制",
                  "other_defects_derived": "L2 残差（中位占比 62.8%，主体类）"},
    "confounders": {"model": "牌号固定效应/分层轴（9 水平）", "meters": "暴露分母", "t_index": "共同时间趋势"},
    "pruned": [{"columns": [c for c in df.columns if c.endswith("_dev")],
                "reason": "preprocess 生成的 *_dev 派生列与原始列信息重复（r=1.0），保留会造成多重比较膨胀；统计分析只用原始 44 列"},
               {"columns": ["batch_id", "ts_start"],
                "reason": "标识/时间轴，仅作排序与追溯，不作为预测变量"}],
    "why_not_more": "无熔体温度/挤出机/张力测点 → 挤出段不可直接检验（本体 S1/S6 observed=false）",
}
(PROC / "analysis_parameter_selection.json").write_text(json.dumps(sel, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ analysis_method_plan ============
plan = {"generated_at": now, "method_selection_policy": "methods follow hypotheses",
        "hypotheses": [
            {"id": "H1", "statement": "涂布/冷却通道族（W1C）漂移驱动总缺陷与未分类残差上升",
             "methods": ["family composite partial Spearman (control model+meters)", "time-control partial (add t_index)",
                         "segment re-estimation pre/post change point", "leave-one-out leverage"]},
            {"id": "H2", "statement": "F_PS005 供料回路压差累积（锯齿）+ 复位，是周期性污染源",
             "methods": ["Mann-Kendall/Spearman trend", "Pettitt change point", "segment medians", "lagged CCF <=5 batches"]},
            {"id": "H3", "statement": "牌号配方差异（model）是主要分层混杂，甚至造成 Simpson 反转",
             "methods": ["Kruskal-Wallis per response", "fixed-effect variance decomposition", "within-model Spearman", "stratified scatter"]},
            {"id": "H4", "statement": "缺陷计数主要由批次长度暴露决定，密度才是可比量",
             "methods": ["log-log regression with model FE", "partial r of meters after model", "density vs meters Spearman"]},
            {"id": "H5", "statement": "oligomer 由挤出段热历史决定，MD 温度只影响迁移，故模型内参数关联应很弱",
             "methods": ["pooled vs partial Spearman per family", "FDR control", "comparison with dust"]},
            {"id": "H6", "statement": "dust 多源且与过程参数弱关联，时间上无趋势",
             "methods": ["pooled/partial Spearman", "time trend", "change point"]},
        ],
        "skipped": [{"method": "steady-state filtering as primary input",
                     "reason": "稳态标签按 76 列窗口方差判定，对 149 个批次的慢漂移线会误删漂移主体（101/149 判 steady）；实际用全 149 行做主分析，稳态子集仅作敏感性对照（中位 62 vs 51，方向一致）"},
                    {"method": "intra-batch analysis", "reason": "数据为批级聚合，无批内轨迹"},
                    {"method": "Granger causality", "reason": "149 点 + 不规则间隔 + 强共同趋势，Granger 会被趋势伪造"}]}
(PROC / "analysis_method_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ anomaly_report ============
targets = {}
for r in RESP:
    items = A["outliers"][r]
    intervals = [{"start_index": int(x["row_index"]), "end_index": int(x["row_index"]),
                  "severity": "critical" if abs(x["robust_z_log1p"]) > 6 else "high",
                  "max_deviation_sigma": float(abs(x["robust_z_log1p"])),
                  "batch_id": x["batch_id"], "model": x["model"], "ts_start": x["ts_start"],
                  "value": x["value"], "per_km": x["per_km"]} for x in items]
    targets[r] = {
        "anomaly_intervals": intervals,
        "threshold_analysis": {"critical_threshold": float(np.quantile(df[r], 0.99)),
                               "threshold_crossing_count": int((df[r] > np.quantile(df[r], 0.99)).sum()),
                               "robust_z_threshold": 3.5,
                               "method": "MAD-based robust z on log1p(value)"},
        "change_points": A["time_trends"][r]["change_points"],
    }
ar = {"targets": targets,
      "transition_events": [{"index": c["index"], "batch_id": c["batch_id"], "ts_start": c["ts_start"],
                             "target": r, "p_value": c["p_value"], "pettitt_K": c["pettitt_K"]}
                            for r in RESP for c in A["time_trends"][r]["change_points"]],
      "quality_reset_analysis": {"applicable": True,
                                 "finding": "F_PS005 在索引 70/108/128 出现阶跃回落（疑似过滤器更换/清洗），同期缺陷密度存在分段特征",
                                 "reset_indices": [c["index"] for c in A["C11_F_PS005_trend"]["level_jumps"]],
                                 "strong_resets": [c for c in A["C11_F_PS005_trend"]["level_jumps"] if c["delta"] < -2.0]},
      "metadata": {"generated_by": "data-processor custom_analysis", "method": "MAD robust z + Pettitt",
                   "data_source": "cleaned", "row_count": int(len(df))}}
(PROC / "anomaly_report.json").write_text(json.dumps(ar, ensure_ascii=False, indent=1), encoding="utf-8")

# ============ validate_report (schema-conformant) ============
if not (PROC / "validate_report_pipeline_raw.json").exists():
    raw = json.loads((PROC / "validate_report.json").read_text(encoding="utf-8"))
    (PROC / "validate_report_pipeline_raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
rob = {(x["parameter"], x["target"]): x for x in A["robustness_time_control"]}
validations = []
for a in A["associations"]:
    r_, p_ = a["target"], a["parameter"]
    x, y = df[p_].to_numpy(float), df[r_].to_numpy(float)
    pr = float(stats.pearsonr(x, y)[0])
    rr = rob.get((p_, r_), {})
    strata = a["within_model"]
    rev = sum(1 for v in strata.values() if np.sign(v) != np.sign(a["spearman_rho"]))
    grade = "NONE"
    if a.get("fdr_significant") and a["loo_stable"] and rr.get("survives_time_control"):
        grade = "STRONG"
    elif a.get("fdr_significant") and a["loo_stable"]:
        grade = "MODERATE"
    elif a["p_value"] < 0.05:
        grade = "WEAK"
    warnings = []
    if abs(pr - a["spearman_rho"]) > 0.3:
        warnings.append(f"Pearson({pr:.2f}) 与 Spearman({a['spearman_rho']:.2f}) 分歧 >0.3：重尾/极值主导，采用 Spearman")
    if not a["loo_stable"]:
        warnings.append("留一杠杆不稳定（单点可改变 rho>0.15）")
    if rev and len(strata) >= 3 and rev / len(strata) >= 0.5:
        warnings.append(f"分层内 {rev}/{len(strata)} 个牌号方向与合并相反")
    if rr.get("explained_by_shared_trend"):
        warnings.append("关联可由共同时间趋势解释（控制时间后 |rho|<0.2）")
    validations.append({
        "parameter": p_, "target": r_,
        "pearson_r": round(pr, 4), "spearman_rho": a["spearman_rho"], "p_value": a["p_value"],
        "detrended_r": rr.get("partial_rho_model_meters_time", a["spearman_rho"]),
        "detrended_p_value": rr.get("p_time_ctrl", 1.0),
        "simpson_check": {"safe": not (rev and len(strata) >= 3 and rev / len(strata) >= 0.5),
                          "strata_count": len(strata), "strata_correlations": strata,
                          "direction_reversals": int(rev)},
        "change_point_detected": len(A["time_trends"][r_]["change_points"]) > 0,
        "leave_one_out_stable": bool(a["loo_stable"]),
        "outlier_leverage": float(a["loo_max_abs_delta"] or 0),
        "significance": a["significance"], "evidence_grade": grade,
        "warnings": warnings,
        "family": a["family"], "fdr_q": a.get("fdr_q"),
        "notes": "detrended_r = partial Spearman controlling model FE + log(meters) + time rank",
    })
vr = {"validations": validations,
      "summary": {"total_pairs_analyzed": len(validations),
                  "significant_pairs": sum(1 for v in validations if v["significance"] == "significant"),
                  "simpson_safe_pairs": sum(1 for v in validations if v["simpson_check"]["safe"]),
                  "detrended_robust_pairs": sum(1 for v in validations if abs(v["detrended_r"] or 0) >= 0.2 and (v["detrended_p_value"] or 1) < 0.05),
                  "leave_one_out_passed_pairs": sum(1 for v in validations if v["leave_one_out_stable"]),
                  "top_correlations": [{"parameter": v["parameter"], "target": v["target"],
                                        "spearman_rho": v["spearman_rho"], "evidence_grade": v["evidence_grade"]}
                                       for v in sorted(validations, key=lambda z: -abs(z["spearman_rho"]))[:10]]},
      "metadata": {"generated_by": "data-processor", "pipeline_phase": "Phase 2-3",
                   "data_source": "cleaned", "sample_size": int(len(df)),
                   "anti_spurious_rules_applied": ["v6.4 lag compensation", "v6.5 steady-state cross-check",
                                                   "v6.6 batch integrity", "v6.7 leave-one-out",
                                                   "BH-FDR per target", "time-trend control", "winsorized Spearman",
                                                   "model fixed-effects partial Spearman"],
                   "pipeline_raw_report": "02_processed/validate_report_pipeline_raw.json"}}
(PROC / "validate_report.json").write_text(json.dumps(vr, ensure_ascii=False, indent=1), encoding="utf-8")
print("artifacts OK; validations", len(validations))
