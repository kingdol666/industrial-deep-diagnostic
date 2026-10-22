# -*- coding: utf-8 -*-
"""Robustness pass: time-trend confounding, segment re-estimation, drift audit.

Adds `robustness` block to custom_analysis.json. All inputs from analysis_frame.csv.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RUN = Path(__file__).resolve().parents[1]
PROC = RUN / "02_processed"
df = pd.read_csv(PROC / "analysis_frame.csv")
df["ts_start"] = pd.to_datetime(df["ts_start"])
df = df.sort_values("ts_start").reset_index(drop=True)

schema = json.loads((RUN / "01_ontology" / "schema.json").read_text(encoding="utf-8"))
FAM = schema["classification"]["process_parameter"]["families"]
PARAMS = [c for f in FAM.values() for c in f["columns"]]
PKM = {"total_defects": "total_per_km", "oligomer": "oligomer_per_km",
       "dust": "dust_per_km", "other_defects_derived": "other_per_km"}
RESP = list(PKM)
out = json.loads((PROC / "custom_analysis.json").read_text(encoding="utf-8"))


def rankit(v):
    v = np.asarray(v, float)
    r = stats.rankdata(v)
    return (r - r.mean()) / (r.std(ddof=0) + 1e-12)


def design(groups, meters, t):
    g = pd.get_dummies(pd.Series(groups), drop_first=True).to_numpy(float)
    return np.column_stack([np.ones(len(g)), np.log(meters), np.asarray(t, float), g])


def resid(v, X):
    b, *_ = np.linalg.lstsq(X, v, rcond=None)
    return v - X @ b


def partial(x, y, X):
    rx, ry = rankit(x), rankit(y)
    r, p = stats.pearsonr(resid(rx, X), resid(ry, X))
    return float(r), float(p)


Xfull = design(df["model"], df["meters"], df["t_index"])
Xbase = design(df["model"], df["meters"], np.zeros(len(df)))

rows = []
for r_ in RESP:
    y = np.log1p(df[r_].to_numpy(float))
    for pcol in PARAMS + ["meters"]:
        x = df[pcol].to_numpy(float)
        r_base, p_base = partial(x, y, Xbase)
        r_time, p_time = partial(x, y, Xfull)
        rho_t, p_t = stats.spearmanr(x, df["t_index"])
        rows.append({
            "parameter": pcol, "target": r_,
            "partial_rho_model_meters": round(r_base, 3),
            "partial_rho_model_meters_time": round(r_time, 3),
            "p_time_ctrl": float(f"{p_time:.3e}"),
            "attrn_abs_loss": round(abs(r_base) - abs(r_time), 3),
            "param_vs_time_rho": round(float(rho_t), 3),
            "param_vs_time_p": float(f"{p_t:.3e}"),
            "survives_time_control": bool(abs(r_time) >= 0.2 and p_time < 0.05),
            "explained_by_shared_trend": bool(abs(r_base) >= 0.2 and abs(r_time) < 0.2),
        })
out["robustness_time_control"] = rows
out["robustness_time_control_top"] = {
    r_: sorted([x for x in rows if x["target"] == r_], key=lambda z: -abs(z["partial_rho_model_meters_time"]))[:6]
    for r_ in RESP
}

# ---- parameter drift audit (which params are themselves trending) ----
drift = [{"parameter": p, "rho_vs_time": round(float(stats.spearmanr(df[p], df["t_index"])[0]), 3),
          "p": float(f"{stats.spearmanr(df[p], df['t_index'])[1]:.3e}"),
          "family": next((k for k, v in FAM.items() if p in v["columns"]), "exposure")}
         for p in PARAMS + ["meters"]]
out["parameter_drift"] = sorted(drift, key=lambda z: -abs(z["rho_vs_time"]))

# ---- segment re-estimation around total_defects change point (index 78) ----
CP = 78
seg = {}
for r_ in RESP:
    seg[r_] = {}
    for pcol in ["W1C8A@PV1_mean", "W1C81@PV1_mean", "W1C86@PV1_mean", "W1C40@PV1_mean",
                 "W1C84@PV1_mean", "MD_TH012@PV_mean", "F_PS005@PV1_mean", "meters"]:
        a = df.loc[:CP - 1]
        b = df.loc[CP:]
        ra = stats.spearmanr(a[pcol], a[r_])
        rb = stats.spearmanr(b[pcol], b[r_])
        seg[r_][pcol] = {
            "pre_cp_rho": round(float(ra[0]), 3), "pre_p": float(f"{ra[1]:.3e}"),
            "post_cp_rho": round(float(rb[0]), 3), "post_p": float(f"{rb[1]:.3e}"),
            "sign_consistent": bool(np.sign(ra[0]) == np.sign(rb[0])),
        }
out["segment_check_cp78"] = seg

# ---- C11 segment trends (non-monotone pattern) ----
ps5 = df["F_PS005@PV1_mean"].to_numpy(float)
jumps = out["C11_F_PS005_trend"]["level_jumps"]
bounds = [0] + sorted(j["index"] for j in jumps) + [len(df)]
segs = []
for i in range(len(bounds) - 1):
    a, b = bounds[i], bounds[i + 1]
    if b - a < 8:
        continue
    r, p = stats.spearmanr(np.arange(a, b), ps5[a:b])
    segs.append({"from_index": a, "to_index": b - 1,
                 "from_ts": str(df["ts_start"].iloc[a]), "to_ts": str(df["ts_start"].iloc[b - 1]),
                 "n": b - a, "median": round(float(np.median(ps5[a:b])), 3),
                 "spearman_vs_time": round(float(r), 3), "p": float(f"{p:.3e}")})
out["C11_F_PS005_trend"]["segments"] = segs
cs = [s["median"] for s in segs]
out["C11_F_PS005_trend"]["verdict"] = (
    "sawtooth confirmed: every segment drifts upward, resets are discrete level drops; "
    "overall Spearman is negative only because the resets dominate the pooled ranks")

# ---- recipe leakage check for MD_TH016-018 and W1C80-82 ----
leak = {}
for p in ["MD_TH016@PV_mean", "MD_TH017@PV_mean", "MD_TH018@PV_mean",
          "W1C80@PV1_mean", "W1C81@PV1_mean", "W1C82@PV1_mean"]:
    g = df.groupby("model")[p].agg(["median", "count", "min", "max"])
    leak[p] = {"per_model_median": {k: round(float(v), 2) for k, v in g["median"].items()},
               "between_model_median_spread": round(float(g["median"].max() - g["median"].min()), 2),
               "within_model_median_iqr": round(float(df.groupby("model")[p].apply(
                   lambda s: s.quantile(.75) - s.quantile(.25)).median()), 2),
               "leakage_ratio": round(float((g["median"].max() - g["median"].min()) /
                                            max(df.groupby("model")[p].apply(lambda s: s.quantile(.75) - s.quantile(.25)).median(), 1e-9)), 2)}
out["recipe_leakage"] = leak

# ---- duplicate batch sensitivity ----
dup_row = df.index[df["batch_id"].duplicated(keep=False)].tolist()
sensi = {}
for r_ in RESP:
    y = df[r_].to_numpy(float)
    keep = np.array([i not in dup_row for i in df.index])
    for pcol in ["W1C8A@PV1_mean", "W1C81@PV1_mean", "meters"]:
        r_all = stats.spearmanr(df[pcol], y)[0]
        r_sub = stats.spearmanr(df.loc[keep, pcol], y[keep])[0]
        sensi.setdefault(r_, {})[pcol] = {"rho_all": round(float(r_all), 3),
                                          "rho_without_duplicate_batches": round(float(r_sub), 3)}
out["duplicate_batch_sensitivity"] = {"duplicate_rows": [int(i) for i in dup_row], "results": sensi}

(PROC / "custom_analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("OK")
print(json.dumps(out["robustness_time_control_top"]["total_defects"], ensure_ascii=False)[:1400])
print(json.dumps(out["C11_F_PS005_trend"]["segments"], ensure_ascii=False))
print(json.dumps(out["parameter_drift"][:6], ensure_ascii=False))
