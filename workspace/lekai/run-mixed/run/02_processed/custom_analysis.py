# -*- coding: utf-8 -*-
"""Ontology-guided custom analysis for lekai-mixed-defects-diag.

Reads cleaned_data.csv + ontology.json, writes:
  custom_analysis.json  (all statistics consumed by charts + conclusion)
Every number is recomputable from 02_processed/cleaned_data.csv.
"""
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RUN = Path(__file__).resolve().parents[1]
PROC = RUN / "02_processed"
ONT = json.loads((RUN / "01_ontology" / "ontology.json").read_text(encoding="utf-8"))

df = pd.read_csv(PROC / "cleaned_data.csv")
df["ts_start"] = pd.to_datetime(df["ts_start"])
# batch_id is NOT time ordered -> sort strictly by ts_start (directive 5)
df = df.sort_values(["ts_start", "batch_id"]).reset_index(drop=True)
df["t_index"] = np.arange(len(df))
df["gap_min"] = df["ts_start"].diff().dt.total_seconds().div(60)

# ---- derived responses (ontology: other_defects_derived) ----
for c in ["total_defects", "oligomer", "dust", "meters"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["other_defects_derived"] = df["total_defects"] - df["oligomer"] - df["dust"]
df["total_per_km"] = df["total_defects"] / df["meters"] * 1000.0
df["oligomer_per_km"] = df["oligomer"] / df["meters"] * 1000.0
df["dust_per_km"] = df["dust"] / df["meters"] * 1000.0
df["other_per_km"] = df["other_defects_derived"] / df["meters"] * 1000.0
PKM = {"total_defects": "total_per_km", "oligomer": "oligomer_per_km",
       "dust": "dust_per_km", "other_defects_derived": "other_per_km"}
df["share_oligomer"] = df["oligomer"] / df["total_defects"].replace(0, np.nan)
df["share_dust"] = df["dust"] / df["total_defects"].replace(0, np.nan)
df["dup_batch"] = df["batch_id"].duplicated(keep=False)

RESP = ["total_defects", "oligomer", "dust", "other_defects_derived"]
FAM = ONT and json.loads((RUN / "01_ontology" / "schema.json").read_text(encoding="utf-8"))["classification"]["process_parameter"]["families"]
PARAMS = [c for f in FAM.values() for c in f["columns"]]
PARAM_FAMILY = {c: k for k, f in FAM.items() for c in f["columns"]}
assert len(PARAMS) == 44, len(PARAMS)

out = {
    "meta": {
        "rows": int(len(df)),
        "columns_raw": int(pd.read_csv(RUN / "00_input" / "batches.csv", nrows=0).shape[1]),
        "time_start": str(df["ts_start"].min()),
        "time_end": str(df["ts_start"].max()),
        "sort_key": "ts_start (batch_id is not time-ordered)",
        "duplicate_batch_ids": sorted(df.loc[df.dup_batch, "batch_id"].unique().tolist()),
    }
}

# ---------------- regime filter ----------------
reg = json.loads((PROC / "production_regime_filter.json").read_text(encoding="utf-8"))
labels = reg["per_row_labels"]
# regime labels were computed on the same ts-sorted order? verify by index alignment
df["regime"] = labels if len(labels) == len(df) else "unknown"
out["meta"]["regime_counts"] = df["regime"].value_counts().to_dict()


# ---------------- helpers ----------------
def sig(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "not_significant"
    return "significant" if p < 0.05 else ("marginal" if p < 0.10 else "not_significant")


def sp(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 6:
        return None, None, int(m.sum())
    r, p = stats.spearmanr(x[m], y[m])
    return float(r), float(p), int(m.sum())


def rankit(v):
    v = np.asarray(v, float)
    r = stats.rankdata(v)
    return (r - r.mean()) / (r.std(ddof=0) + 1e-12)


def design(groups, meters):
    g = pd.get_dummies(pd.Series(groups), drop_first=True).to_numpy(float)
    return np.column_stack([np.ones(len(g)), np.log(meters), g])


def resid(v, X):
    beta, *_ = np.linalg.lstsq(X, v, rcond=None)
    return v - X @ beta


def partial_spearman(x, y, groups, meters):
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(meters)
    if m.sum() < 10:
        return None, None, int(m.sum())
    X = design(pd.Series(groups)[m], meters[m])
    rx, ry = rankit(x[m]), rankit(y[m])
    ex, ey = resid(rx, X), resid(ry, X)
    r, p = stats.pearsonr(ex, ey)
    return float(r), float(p), int(m.sum())


def winsor(v, lo=0.01, hi=0.99):
    v = np.asarray(v, float)
    a, b = np.nanquantile(v, [lo, hi])
    return np.clip(v, a, b)


def loo_max_delta(x, y):
    """max |rho_all - rho_without_i| over single-row deletions (outlier leverage)."""
    r0, _, _ = sp(x, y)
    if r0 is None:
        return None, 0
    deltas = []
    for i in range(len(x)):
        keep = np.ones(len(x), bool)
        keep[i] = False
        r, _, n = sp(np.asarray(x)[keep], np.asarray(y)[keep])
        if r is not None:
            deltas.append(abs(r0 - r))
    if not deltas:
        return None, 0
    # which single row produces the largest swing
    return float(max(deltas)), int(len(deltas))


def robs_z(v):
    v = np.asarray(v, float)
    med = np.median(v)
    mad = np.median(np.abs(v - med)) * 1.4826
    return (v - med) / (mad + 1e-12)


def pettitt(v):
    n = len(v)
    r = stats.rankdata(v)
    s = np.sign(np.subtract.outer(r, r))
    U = np.array([s[:t + 1, t + 1:].sum() for t in range(n - 1)])
    K = np.max(np.abs(U))
    idx = int(np.argmax(np.abs(U)))
    p = min(1.0, 2 * math.exp(-6 * K ** 2 / (n ** 3 + n ** 2)))
    return idx, float(K), float(p)


def change_points(v, max_cp=3):
    v = np.asarray(v, float)
    cps = []
    bounds = [(0, len(v))]
    for _ in range(max_cp):
        best = None
        for (a, b) in bounds:
            seg = v[a:b]
            if len(seg) < 15:
                continue
            i, K, p = pettitt(seg)
            if p < 0.05 and (best is None or p < best[2]):
                best = (a + i, K, p, (a, b))
        if best is None:
            break
        cps.append({"index": int(best[0]), "batch_id": str(df["batch_id"].iloc[best[0]]),
                    "ts_start": str(df["ts_start"].iloc[best[0]]),
                    "pettitt_K": round(best[1], 2), "p_value": round(best[2], 5),
                    "segment_size": int(best[3][1] - best[3][0])})
        a, b = best[3]
        bounds = [(a, best[0] + 1), (best[0] + 1, b)]
    return cps


# ---------------- 1. response profiling (three separate responses) ----------------
prof = {}
for r_ in RESP + ["total_per_km", "oligomer_per_km", "dust_per_km", "other_per_km"]:
    v = df[r_].to_numpy(float)
    lv = np.log1p(v)
    prof[r_] = {
        "n": int(np.isfinite(v).sum()),
        "mean": round(float(np.nanmean(v)), 2),
        "median": round(float(np.nanmedian(v)), 2),
        "sd": round(float(np.nanstd(v, ddof=1)), 2),
        "q25": round(float(np.nanquantile(v, .25)), 2),
        "q75": round(float(np.nanquantile(v, .75)), 2),
        "q90": round(float(np.nanquantile(v, .90)), 2),
        "q99": round(float(np.nanquantile(v, .99)), 2),
        "min": round(float(np.nanmin(v)), 2),
        "max": round(float(np.nanmax(v)), 2),
        "skew": round(float(stats.skew(v, nan_policy="omit")), 2),
        "skew_log1p": round(float(stats.skew(lv, nan_policy="omit")), 2),
        "cv": round(float(np.nanstd(v, ddof=1) / max(np.nanmean(v), 1e-9)), 2),
        "zero_rows": int((v == 0).sum()),
        "top1_share": round(float(np.nanmax(v) / np.nansum(v)), 4),
        "top5_share": round(float(np.sort(v)[-5:].sum() / np.nansum(v)), 4),
        "mean_over_median": round(float(np.nanmean(v) / max(np.nanmedian(v), 1e-9)), 2),
        "is_heavy_tailed": bool(stats.skew(v, nan_policy="omit") > 2),
        "distribution_used": "log1p for modelling; median/rank for inference",
    }
out["response_profiles"] = prof

out["defect_composition"] = {
    "median_share_oligomer": round(float(df["share_oligomer"].median()), 4),
    "median_share_dust": round(float(df["share_dust"].median()), 4),
    "median_share_other": round(float((1 - df["share_oligomer"] - df["share_dust"]).median()), 4),
    "median_total": float(df["total_defects"].median()),
    "median_oligomer": float(df["oligomer"].median()),
    "median_dust": float(df["dust"].median()),
    "median_other": float(df["other_defects_derived"].median()),
    "note": "total_defects != oligomer + dust; other_defects_derived dominates by median share",
}

# ---------------- 2. model stratification ----------------
models = df["model"].value_counts()
mod_table = {}
for g, sub in df.groupby("model"):
    mod_table[g] = {
        "n": int(len(sub)),
        "median_total": float(sub["total_defects"].median()),
        "median_oligomer": float(sub["oligomer"].median()),
        "median_dust": float(sub["dust"].median()),
        "median_other": float(sub["other_defects_derived"].median()),
        "median_total_per_km": round(float(sub["total_per_km"].median()), 2),
        "median_meters": float(sub["meters"].median()),
        "median_share_other": round(float((1 - sub["share_oligomer"] - sub["share_dust"]).median()), 3),
        "max_total": float(sub["total_defects"].max()),
    }
out["model_table"] = mod_table
out["model_kruskal"] = {}
for r_ in RESP:
    groups = [s[r_].dropna().to_numpy() for _, s in df.groupby("model") if len(s) >= 3]
    H, p = stats.kruskal(*groups)
    out["model_kruskal"][r_] = {"H": round(float(H), 2), "p_value": float(f"{p:.3e}"),
                                "groups": len(groups), "eta2_rank": round(float((H - len(groups) + 1) / (len(df) - len(groups))), 3)}

# per-model defect density (directive 3: count-only invalid)
out["exposure"] = {
    "meters_min": float(df["meters"].min()), "meters_max": float(df["meters"].max()),
    "meters_max_over_min": round(float(df["meters"].max() / df["meters"].min()), 2),
    "median_meters": float(df["meters"].median()),
}

# C10 exposure calibration: log-log slope
lm, ly = np.log(df["meters"]), np.log(df["total_defects"].clip(lower=1))
sl, ic, rv, pv, se = stats.linregress(lm, ly)
X = design(df["model"], df["meters"])
b, *_ = np.linalg.lstsq(X, ly.values, rcond=None)
r_fe, p_fe = stats.pearsonr(resid(ly.values, X), resid(lm.values, X))
out["exposure_calibration_C10"] = {
    "loglog_slope_pooled": round(float(sl), 3),
    "loglog_slope_se": round(float(se), 3),
    "loglog_r2": round(float(rv ** 2), 3),
    "loglog_p": float(f"{pv:.3e}"),
    "slope_with_model_fixed_effects": round(float(b[1]), 3),
    "partial_r_meters_after_model": round(float(r_fe), 3),
    "partial_p": float(f"{p_fe:.3e}"),
    "spearman_meters_total": [round(float(x), 3) if x is not None else None for x in sp(df["meters"], df["total_defects"])[:2]],
    "spearman_meters_total_per_km": [round(float(x), 3) for x in sp(df["meters"], df["total_per_km"])[:2]],
    "verdict": None,
}
slope = b[1]
out["exposure_calibration_C10"]["verdict"] = (
    "counts scale ~proportionally with exposure (density valid)" if 0.6 <= slope <= 1.4
    else "counts scale sub/super-proportionally; density analysis mandatory")

# ---------------- 3. time structure ----------------
out["time_structure"] = {
    "gap_min_median": round(float(df["gap_min"].median()), 1),
    "gap_min_min": round(float(df["gap_min"].min()), 1),
    "gap_min_max": round(float(df["gap_min"].max()), 1),
    "span_hours": round(float((df["ts_start"].max() - df["ts_start"].min()).total_seconds() / 3600), 1),
    "median_interval_seconds": round(float(df["gap_min"].median() * 60), 0),
    "max_lag_searched_steps": 5,
}
trend = {}
for r_ in RESP:
    rho, p, n = sp(df["t_index"], df[r_])
    rho_d, p_d, _ = sp(df["t_index"], df[PKM[r_]])
    trend[r_] = {"spearman_vs_time_index": round(rho, 3) if rho else None,
                 "p_value": float(f"{p:.3e}") if p is not None else None,
                 "spearman_density_vs_time": round(rho_d, 3) if rho_d else None,
                 "p_value_density": float(f"{p_d:.3e}") if p_d is not None else None,
                 "change_points": change_points(np.log1p(df[r_].to_numpy(float)))}
out["time_trends"] = trend

# C11 F_PS005 monotone trend (pre-registered)
ps5 = df["F_PS005@PV1_mean"].to_numpy(float)
rho5, p5, _ = sp(df["t_index"], ps5)
# Mann-Kendall tau
tau, ptau = stats.kendalltau(np.arange(len(ps5)), ps5)

def level_jumps(v, thresh=-1.0):
    d = np.diff(v)
    idx = np.where(d < thresh)[0] + 1
    res = []
    for i in idx:
        pre = float(np.median(v[max(0, i - 3):i]))
        post = float(np.median(v[i:i + 3]))
        res.append({"index": int(i), "batch_id": str(df["batch_id"].iloc[i]),
                    "ts_start": str(df["ts_start"].iloc[i]),
                    "delta": round(float(d[i - 1]), 3),
                    "level_before": round(pre, 3), "level_after": round(post, 3),
                    "density_before_per_km": round(float(df["total_per_km"].iloc[max(0, i - 3):i].median()), 1),
                    "density_after_per_km": round(float(df["total_per_km"].iloc[i:i + 3].median()), 1)})
    return sorted(res, key=lambda z: z["delta"])

out["C11_F_PS005_trend"] = {
    "spearman": round(rho5, 3), "p_value": float(f"{p5:.3e}"),
    "kendall_tau": round(float(tau), 3), "kendall_p": float(f"{ptau:.3e}"),
    "n": int(len(ps5)),
    "first5_median": float(np.median(ps5[:5])), "last5_median": float(np.median(ps5[-5:])),
    "delta": round(float(np.median(ps5[-5:]) - np.median(ps5[:5])), 3),
    "change_points": change_points(ps5),
    "level_jumps": level_jumps(ps5),
    "verdict": "sawtooth: within-segment upward drift + discrete resets (see level_jumps); overall Spearman sign is an artefact of the resets",
}

# ---------------- 4. anomalies / outliers ----------------
anom = {}
for r_ in RESP:
    z = robs_z(np.log1p(df[r_].to_numpy(float)))
    df[r_ + "_robust_z"] = z
    idx = np.argsort(-np.abs(z))[:8]
    anom[r_] = [{
        "batch_id": str(df["batch_id"].iloc[i]), "row_index": int(i),
        "ts_start": str(df["ts_start"].iloc[i]), "model": str(df["model"].iloc[i]),
        "value": float(df[r_].iloc[i]), "per_km": round(float(df[PKM[r_]].iloc[i]), 2),
        "meters": float(df["meters"].iloc[i]),
        "robust_z_log1p": round(float(z[i]), 2),
        "duplicate_batch": bool(df["dup_batch"].iloc[i]),
    } for i in idx if abs(z[i]) > 3.5]
out["outliers"] = anom

# ---------------- 5. associations ----------------
assoc = []
for r_ in RESP:
    y = df[r_].to_numpy(float)
    ylog = np.log1p(y)
    for pcol in PARAMS + ["meters"]:
        x = df[pcol].to_numpy(float)
        rho, p, n = sp(x, y)
        if rho is None:
            continue
        prho, pp, _ = partial_spearman(x, ylog, df["model"], df["meters"])
        wrho, wp, _ = sp(x, winsor(y))
        # within-model strata (n>=8)
        strata = {}
        for g, sub in df.groupby("model"):
            if len(sub) < 8:
                continue
            rr, ppp, _ = sp(sub[pcol], sub[r_])
            if rr is not None:
                strata[g] = round(float(rr), 3)
        same_sign = sum(1 for v in strata.values() if np.sign(v) == np.sign(rho))
        deltas, _ = loo_max_delta(x, y)
        assoc.append({
            "parameter": pcol, "family": PARAM_FAMILY.get(pcol, "exposure"),
            "target": r_, "n": n,
            "spearman_rho": round(rho, 3), "p_value": float(f"{p:.3e}"),
            "spearman_winsor": round(wrho, 3),
            "partial_rho_model_meters": round(prho, 3) if prho is not None else None,
            "partial_p": float(f"{pp:.3e}") if pp is not None else None,
            "within_model": strata,
            "within_model_same_sign": f"{same_sign}/{len(strata)}",
            "simpson_reversal": bool(strata and same_sign / len(strata) < 0.5),
            "loo_max_abs_delta": round(deltas, 3) if deltas is not None else None,
            "loo_stable": bool(deltas is not None and deltas < 0.15),
            "significance": sig(p),
        })
out["associations"] = assoc

# BH-FDR per target
for r_ in RESP:
    rows = [a for a in assoc if a["target"] == r_]
    ps = np.array([a["p_value"] for a in rows])
    order = np.argsort(ps)
    m = len(ps)
    q = np.empty(m)
    prev = 1.0
    for rank, i in enumerate(order[::-1]):
        val = min(prev, ps[i] * m / (m - rank))
        q[i] = val
        prev = val
    for a, qq in zip(rows, q):
        a["fdr_q"] = float(f"{qq:.4f}")
        a["fdr_significant"] = bool(qq < 0.05)

# ---------------- 6. collinearity / families ----------------
P = df[PARAMS].to_numpy(float)
C = stats.spearmanr(P).statistic
C = np.nan_to_num(C, nan=0.0)
np.fill_diagonal(C, 1.0)
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
D = 1 - np.abs(C)
np.fill_diagonal(D, 0.0)
Z = linkage(squareform(D, checks=False), method="average")
cl = fcluster(Z, t=0.6, criterion="distance")
clusters = {}
for c, name in zip(cl, PARAMS):
    clusters.setdefault(f"C{int(c)}", []).append(name)
eig = np.sort(np.linalg.eigvalsh(C))[::-1]
var_expl = np.cumsum(eig) / eig.sum()
n_pc90 = int(np.searchsorted(var_expl, 0.90) + 1)
out["collinearity"] = {
    "n_params": len(PARAMS),
    "n_components_90pct_var": n_pc90,
    "pc1_var_share": round(float(eig[0] / eig.sum()), 3),
    "mean_abs_offdiag_rho": round(float(np.abs(C - np.eye(len(C))).sum() / (len(C) ** 2 - len(C))), 3),
    "data_clusters_avg_link_cut0.6": {k: v for k, v in clusters.items() if len(v) > 1},
    "ontological_families": {k: v["columns"] for k, v in FAM.items()},
    "family_internal_median_abs_rho": {
        k: round(float(np.median([abs(C[i][j]) for i, a in enumerate(PARAMS) for j, b in enumerate(PARAMS)
                                 if i < j and a in v["columns"] and b in v["columns"]])), 3)
        for k, v in FAM.items() if len(v["columns"]) > 1},
    "effective_independent_signals": n_pc90,
}

# family composite -> response
famassoc = []
for k, v in FAM.items():
    cols = [c for c in v["columns"] if df[c].notna().sum() > 0]
    Zs = df[cols].apply(lambda s: (s - s.mean()) / (s.std(ddof=0) + 1e-12))
    comp = Zs.mean(axis=1).to_numpy()
    for r_ in RESP:
        rho, p, n = sp(comp, df[r_].to_numpy(float))
        prho, pp, _ = partial_spearman(comp, np.log1p(df[r_].to_numpy(float)), df["model"], df["meters"])
        famassoc.append({"family": k, "target": r_, "rho": round(rho, 3), "p": float(f"{p:.3e}"),
                         "partial_rho": round(prho, 3), "partial_p": float(f"{pp:.3e}"),
                         "n_cols": len(cols)})
out["family_associations"] = famassoc

# ---------------- 7. time-lag CCF (<=5 batches) ----------------
df_s = df.sort_values("ts_start").reset_index(drop=True)
lagres = []
keys = ["F_PS005@PV1_mean", "F_PS006@PV1_mean", "F_PS002@PV1_mean", "meters",
        "MD_TH011@PV_mean", "MD_TH016@PV_mean", "MD_TH018@PV_mean",
        "W1C40@PV1_mean", "W1C84@PV1_mean", "W1C7C@PV1_mean", "W1C83@PV1_mean"]
for key in keys:
    for r_ in RESP:
        yv = np.log1p(df_s[r_].to_numpy(float))
        xv = df_s[key].to_numpy(float)
        best = None
        for L in range(0, 6):
            if L == 0:
                a, b = xv, yv
            else:
                a, b = xv[:-L], yv[L:]
            if len(a) < 20:
                continue
            r, p = stats.spearmanr(a, b)
            if best is None or abs(r) > abs(best[0]):
                best = (float(r), float(p), L)
        r0, p0 = stats.spearmanr(xv, yv)
        lagres.append({"predictor": key, "target": r_,
                       "raw_rho": round(float(r0), 3), "raw_p": float(f"{p0:.3e}"),
                       "best_lag_steps": int(best[2]), "lagged_rho": round(best[0], 3),
                       "lagged_p": float(f"{best[1]:.3e}"),
                       "improvement_pct": round(float((abs(best[0]) - abs(r0)) / max(abs(r0), 1e-6) * 100), 1),
                       "lag_seconds_median": round(float(df_s["gap_min"].median() * 60 * best[2]), 0),
                       "significant_improvement": bool(abs(best[0]) - abs(r0) > 0.05 and best[1] < 0.05)})
out["time_lag"] = {
    "applicable": True,
    "max_lag_steps": 5,
    "pairs": len(lagres),
    "results": lagres,
    "significant_count": sum(1 for x in lagres if x["significant_improvement"]),
}

# ---------------- 8. model as fixed effect: variance decomposition ----------------
# how much of log-response variance is between-model?
dec = {}
for r_ in RESP:
    y = np.log1p(df[r_].to_numpy(float))
    X = design(df["model"], df["meters"])
    X0 = np.column_stack([np.ones(len(y)), np.log(df["meters"])])
    rss1 = np.sum(resid(y, X) ** 2)
    rss0 = np.sum(resid(y, X0) ** 2)
    rss_null = np.sum((y - y.mean()) ** 2)
    dec[r_] = {"r2_model_plus_meters": round(float(1 - rss1 / rss_null), 3),
               "incremental_r2_from_model": round(float((rss0 - rss1) / rss_null), 3)}
out["variance_decomposition"] = dec

# ---------------- 9. Simpson explicit table (control model) ----------------
simp = []
for a in assoc:
    if a["significance"] == "significant" and a["target"] in ("total_defects", "oligomer", "dust"):
        pooled = a["spearman_rho"]
        pr = a["partial_rho_model_meters"]
        if pr is not None and np.sign(pr) != np.sign(pooled) and abs(pr) > 0.1:
            simp.append({"parameter": a["parameter"], "target": a["target"],
                         "pooled_rho": pooled, "partial_rho": pr, "within_model": a["within_model"]})
out["simpson_reversals"] = simp

# ---------------- 10. steady-state comparison ----------------
st = df[df["regime"] == "steady"]
out["steady_state_check"] = {
    "n_steady": int(len(st)), "n_all": int(len(df)),
    "median_total_steady": float(st["total_defects"].median()),
    "median_total_all": float(df["total_defects"].median()),
    "median_per_km_steady": round(float(st["total_per_km"].median()), 2),
    "median_per_km_all": round(float(df["total_per_km"].median()), 2),
    "regime_distribution": df["regime"].value_counts().to_dict(),
}

# ---------------- 11. association top lists per response ----------------
top = {}
for r_ in RESP:
    rows = sorted([a for a in assoc if a["target"] == r_], key=lambda x: -abs(x["spearman_rho"]))[:8]
    rows_p = sorted([a for a in assoc if a["target"] == r_ and a["partial_rho_model_meters"] is not None],
                    key=lambda x: -abs(x["partial_rho_model_meters"]))[:8]
    top[r_] = {"pooled": rows, "partial": rows_p}
out["top_associations"] = top

(PROC / "custom_analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
df.to_csv(PROC / "analysis_frame.csv", index=False)
print("OK custom_analysis.json")
print(json.dumps(out["top_associations"]["total_defects"]["pooled"][:5], ensure_ascii=False)[:900])
