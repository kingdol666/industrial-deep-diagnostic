#!/usr/bin/env python3
"""Expert scenario analysis — heat_treat_sim (data-processor Phase 3, M11+M13).

Deterministic. Reads:
  - 02_processed/cleaned_data.csv            (full 1440-row cleaned table)
  - 07_hetero/features/PROF-L1BANDTEMPPROFILE30M.csv (time x position profiles)
  - 02_processed/anomaly_report.json         (dp_toolkit intervals)
Writes:
  - 02_processed/expert_findings.json        (all numbers cited in the conclusion)
  - 03_figures/fig_hetero_profile_heatmap.png  (time x position, events)  [MANDATORY]
  - 03_figures/fig_event_response.png        (before/after event windows)
  - appends entries to 03_figures/plot_manifest.json (plots[] + metadata)
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RUN = os.path.realpath(sys.argv[1] if len(sys.argv) > 1 else ".")
PROC = os.path.join(RUN, "02_processed")
FIG = os.path.join(RUN, "03_figures")


def _inside_run(p):
    """Containment guard (Mimosa L2): the argv run dir is operator input, so
    every derived path is proven to stay inside RUN (also catches symlink
    escapes) instead of trusting the caller."""
    try:
        return os.path.commonpath([RUN, os.path.realpath(p)]) == RUN
    except ValueError:
        return False


if not (_inside_run(PROC) and _inside_run(FIG)):
    raise SystemExit("refusing: derived path escapes the run directory")

os.makedirs(FIG, exist_ok=True)

EV_MAINT = pd.Timestamp("2026-02-06 06:40:00")
EV_HEATUP = pd.Timestamp("2026-02-08 10:00:00")
EV_RESTORED = pd.Timestamp("2026-02-08 21:00:00")
EV_CLOSED = pd.Timestamp("2026-02-10 09:00:00")

df = pd.read_csv(os.path.join(PROC, "cleaned_data.csv"))
df.columns = [c.replace("\ufeff", "") for c in df.columns]
tcol = "时间"
df[tcol] = pd.to_datetime(df[tcol])
df = df.sort_values(tcol).reset_index(drop=True)

KEY = {
    "z1": "FUR-Z1-TEMP", "z2": "FUR-Z2-TEMP", "z3": "FUR-Z3-TEMP",
    "speed": "FUR-SPEED", "pres": "FUR-PRES", "out": "FUR-OUT-TEMP", "yield": "FUR-YIELD",
    "pmean": "HX-PROF-L1BANDTEMPPROFILE30M-MEAN", "pstd": "HX-PROF-L1BANDTEMPPROFILE30M-STD",
    "pmin": "HX-PROF-L1BANDTEMPPROFILE30M-MIN", "pmax": "HX-PROF-L1BANDTEMPPROFILE30M-MAX",
    "p05": "HX-PROF-L1BANDTEMPPROFILE30M-P05", "p50": "HX-PROF-L1BANDTEMPPROFILE30M-P50",
    "p95": "HX-PROF-L1BANDTEMPPROFILE30M-P95", "prange": "HX-PROF-L1BANDTEMPPROFILE30M-RANGE",
    "piqr": "HX-PROF-L1BANDTEMPPROFILE30M-IQR", "pmad": "HX-PROF-L1BANDTEMPPROFILE30M-MAD",
    "pslope": "HX-PROF-L1BANDTEMPPROFILE30M-SLOPE-LSQ-PER100",
    "pcurv": "HX-PROF-L1BANDTEMPPROFILE30M-CURV-LSQ",
    "pzone1": "HX-PROF-L1BANDTEMPPROFILE30M-ZONE-1-3-MEAN",
    "pedgel": "HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV",
    "pedger": "HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV",
    "pshift": "HX-PROF-L1BANDTEMPPROFILE30M-SHIFT-EST",
    "mmean": "HX-MAP-L1FURNACETHERMALMAP2-MEAN", "mp95": "HX-MAP-L1FURNACETHERMALMAP2-P95",
    "mhot": "HX-MAP-L1FURNACETHERMALMAP2-HOTAREA-P90", "mcold": "HX-MAP-L1FURNACETHERMALMAP2-COLDAREA-P10",
    "mcx": "HX-MAP-L1FURNACETHERMALMAP2-CENTROID-X", "mcy": "HX-MAP-L1FURNACETHERMALMAP2-CENTROID-Y",
    "masym": "HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR",
    "immean": "HX-IMG-L1SURFACECCDINDEX-MEAN", "imstd": "HX-IMG-L1SURFACECCDINDEX-STD",
    "iment": "HX-IMG-L1SURFACECCDINDEX-ENTROPY", "imsat": "HX-IMG-L1SURFACECCDINDEX-SATFRAC",
    "imdark": "HX-IMG-L1SURFACECCDINDEX-DARKFRAC", "imfocus": "HX-IMG-L1SURFACECCDINDEX-FOCUS",
}

out = {"generated_at": pd.Timestamp.now().isoformat(), "input": "02_processed/cleaned_data.csv (1440 rows full cleaned)"}

# ---------- 1. regime segmentation by annotation anchors ----------
segs = {
    "A_pre_aging": (None, EV_MAINT),
    "B_maintenance_window": (EV_MAINT, EV_HEATUP),
    "C_heatup_recovery": (EV_HEATUP, EV_RESTORED),
    "D_restored": (EV_RESTORED, None),
}
seg_stats = {}
for name, (a, b) in segs.items():
    m = pd.Series(True, index=df.index)
    if a is not None:
        m &= df[tcol] >= a
    if b is not None:
        m &= df[tcol] < b
    sub = df[m]
    st = {"n_rows": int(len(sub)), "start": str(sub[tcol].min()), "end": str(sub[tcol].max()), "columns": {}}
    for k, c in KEY.items():
        if c not in sub.columns:
            continue
        s = sub[c].dropna()
        if len(s) == 0:
            continue
        st["columns"][k] = {"mean": round(float(s.mean()), 4), "std": round(float(s.std(ddof=1)), 4),
                            "min": round(float(s.min()), 4), "max": round(float(s.max()), 4)}
    seg_stats[name] = st
out["regime_segments"] = seg_stats

# level-shift deltas (key metrics, segment mean differences)
deltas = {}
for k in ["z3", "out", "yield", "pmean", "pstd", "pedgel", "pedger", "pslope", "mmean", "masym", "mcx", "immean", "imstd", "iment"]:
    try:
        a = seg_stats["A_pre_aging"]["columns"][k]["mean"]
        b = seg_stats["B_maintenance_window"]["columns"][k]["mean"]
        d = seg_stats["D_restored"]["columns"][k]["mean"]
    except KeyError:
        continue
    deltas[k] = {"A_pre": a, "B_maint": b, "D_restored": d,
                 "B_minus_A": round(b - a, 4), "D_minus_A": round(d - a, 4)}
out["level_shift_deltas"] = deltas

# ---------- 2. within-segment correlations for key pairs ----------
pairs = [
    ("z3", "out"), ("z3", "yield"), ("z3", "pmean"), ("z3", "pstd"),
    ("z3", "pedgel"), ("z3", "pedger"), ("z3", "pslope"),
    ("masym", "pedgel"), ("masym", "pedger"), ("mcx", "yield"), ("mcx", "pmean"),
    ("immean", "yield"), ("immean", "pmean"), ("imstd", "yield"),
    ("mmean", "yield"), ("mmean", "z3"),
]
def pear(a, b):
    d = pd.concat([a, b], axis=1).dropna()
    if len(d) < 8:
        return None
    return round(float(d.iloc[:, 0].corr(d.iloc[:, 1])), 4)

seg_corr = {}
for name in segs:
    a, b = segs[name]
    m = pd.Series(True, index=df.index)
    if a is not None:
        m &= df[tcol] >= a
    if b is not None:
        m &= df[tcol] < b
    sub = df[m]
    rec = {"n_rows": int(len(sub))}
    for k1, k2 in pairs:
        c1, c2 = KEY[k1], KEY[k2]
        if c1 in sub.columns and c2 in sub.columns:
            r = pear(sub[c1], sub[c2])
            if r is not None:
                rec[f"{k1}~{k2}"] = r
    seg_corr[name] = rec
out["within_segment_pearson"] = seg_corr

# ---------- 3. snapshot-level (deduplicated) correlation for HX columns ----------
def dedup_pairs(col):
    d = df[[tcol, col]].dropna()
    changed = d[col].ne(d[col].shift())
    return d[changed]

snap = {}
hx_cols = ["pmean", "pstd", "pedger", "pedgel", "pshift", "mmean", "masym", "mcx", "immean", "imstd", "iment"]
for k in hx_cols:
    c = KEY[k]
    if c not in df.columns:
        continue
    d = dedup_pairs(c)
    rec = {"n_snapshots": int(len(d))}
    for kk in ["z3", "yield", "out"]:
        if KEY[kk] in df.columns:
            m = df[[tcol, c, KEY[kk]]].dropna()
            mm = m[m[c].ne(m[c].shift())]
            if len(mm) >= 8:
                rec[f"vs_{kk}_pearson"] = round(float(mm[c].corr(mm[KEY[kk]])), 4)
                rec[f"vs_{kk}_spearman"] = round(float(mm[c].corr(mm[KEY[kk]], method="spearman")), 4)
    snap[k] = rec
out["snapshot_level_correlation"] = snap

# ---------- 4. confounder probes: SHIFT-EST / DARKFRAC / SATFRAC / N uniqueness ----------
probes = {}
for k in ["pshift", "imdark", "imsat", "speed", "pres"]:
    c = KEY.get(k)
    if c in df.columns:
        s = df[c].dropna()
        probes[k] = {"column": c, "n": int(len(s)), "unique": int(s.nunique()),
                     "min": float(s.min()), "max": float(s.max()),
                     "nonzero_share": round(float((s.abs() > 1e-12).mean()), 4)} if len(s) else {}
out["confounder_probes"] = probes

# ---------- 5. event-response windows (+/-12h) ----------
ev_windows = {}
for evname, ev in [("maint_20260206_0640", EV_MAINT), ("heatup_20260208_1000", EV_HEATUP)]:
    before = df[(df[tcol] >= ev - pd.Timedelta(hours=12)) & (df[tcol] < ev)]
    after = df[(df[tcol] >= ev) & (df[tcol] < ev + pd.Timedelta(hours=12))]
    rec = {"event": str(ev), "n_before": int(len(before)), "n_after": int(len(after))}
    for k in ["z3", "out", "yield", "pmean", "pstd", "pedger", "immean"]:
        c = KEY[k]
        if c in df.columns and len(before) and len(after):
            rec[f"{k}_before"] = round(float(before[c].mean()), 4)
            rec[f"{k}_after"] = round(float(after[c].mean()), 4)
            rec[f"{k}_delta"] = round(float(after[c].mean() - before[c].mean()), 4)
    ev_windows[evname] = rec
out["event_response_windows_12h"] = ev_windows

# ---------- 6. anomaly report intervals (carry-over summary) ----------
with open(os.path.join(PROC, "anomaly_report.json"), encoding="utf-8") as f:
    ar = json.load(f)
an = {"anomaly_targets": {}, "process_parameter_fluctuation": {}, "transition_events_n": 0}
for tgt, rec in (ar.get("targets") or {}).items():
    ivs = (rec or {}).get("anomaly_intervals") or (rec or {}).get("intervals") or []
    an["anomaly_targets"][tgt] = {
        "n_intervals": len(ivs),
        "intervals": [{"start": str(i.get("start_time") or i.get("start")), "end": str(i.get("end_time") or i.get("end")),
                       "mean": i.get("mean"), "direction": i.get("direction") or i.get("type")} for i in ivs[:12]],
    }
pf = ar.get("process_parameter_fluctuation") or {}
for tgt, rec in (pf.items() if isinstance(pf, dict) else []):
    lst = rec if isinstance(rec, list) else (rec or {}).get("intervals") or []
    if lst:
        an["process_parameter_fluctuation"][tgt] = len(lst)
an["transition_events_n"] = len(ar.get("transition_events") or [])
an["summary_text"] = (ar.get("summary") or {}).get("text") if isinstance(ar.get("summary"), dict) else str(ar.get("summary"))[:400]
out["anomaly_report_digest"] = an

# ---------- 7. change-point dip window time mapping (steady-only idx 722..933) ----------
steady = pd.read_csv(os.path.join(PROC, "cleaned_data_steady_only.csv"))
steady.columns = [c.replace("\ufeff", "") for c in steady.columns]
steady[tcol] = pd.to_datetime(steady[tcol])
if len(steady) > 933:
    out["out_temp_dip_window_steady_idx722_933"] = {
        "start": str(steady[tcol].iloc[722]), "end": str(steady[tcol].iloc[933]),
        "duration_hours": round(212 * 10 / 60, 2),
        "out_temp_mean_dip": round(float(steady[KEY["out"]].iloc[722:934].mean()), 4),
        "z3_mean_dip": round(float(steady[KEY["z3"]].iloc[722:934].mean()), 4),
        "yield_mean_dip": round(float(steady[KEY["yield"]].iloc[722:934].mean()), 4),
    }
if len(steady) > 968:
    out["yield_cp_window_steady_idx663_977"] = {
        "start": str(steady[tcol].iloc[663]), "end": str(steady[tcol].iloc[min(977, len(steady) - 1)]),
        "yield_mean": round(float(steady[KEY["yield"]].iloc[663:978].mean()), 4),
        "yield_mean_before": round(float(steady[KEY["yield"]].iloc[:663].mean()), 4),
        "z3_mean": round(float(steady[KEY["z3"]].iloc[663:978].mean()), 4),
        "z3_mean_before": round(float(steady[KEY["z3"]].iloc[:663].mean()), 4),
    }

Path(PROC, "expert_findings.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("expert_findings.json written")

# ---------- 8. figures ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ev_lines = [("maintenance\n02-06 06:40", EV_MAINT), ("heatup\n02-08 10:00", EV_HEATUP),
            ("restored\n02-08 21:00", EV_RESTORED), ("closed\n02-10 09:00", EV_CLOSED)]
evts = [e for _, e in ev_lines]

# 8a. time x position heatmap from PROF features
prof = pd.read_csv(os.path.join(RUN, "07_hetero", "features", "PROF-L1BANDTEMPPROFILE30M.csv"))
prof.columns = [c.replace("\ufeff", "") for c in prof.columns]
pos_cols = [c for c in prof.columns if c.startswith("pos_")]
pt = pd.to_datetime(prof["ts"])
Z = prof[pos_cols].to_numpy(dtype=float).T  # positions x snapshots

fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
ax = axes[0]
im = ax.imshow(Z, aspect="auto", origin="lower", cmap="inferno",
               extent=[mdates.date2num(pt.iloc[0]), mdates.date2num(pt.iloc[-1]), 1, len(pos_cols)])
cb = fig.colorbar(im, ax=ax, pad=0.01)
cb.set_label("Band temperature at position (°C)")
for lab, e in ev_lines:
    ax.axvline(mdates.date2num(e), color="#00e5ff", ls="--", lw=1.4)
    ax.text(mdates.date2num(e), len(pos_cols) + 0.15, lab, color="#005f6e", fontsize=9, ha="center", va="bottom")
ax.set_title("L1 band temperature profile 30min — time × position (12 positions, 480 snapshots) with operator events")
ax.set_ylabel("Position index (1=drive side → 12)")

ax2 = axes[1]
m = df[[tcol, KEY["z3"], KEY["pmean"], KEY["pedger"], KEY["pedgel"], KEY["yield"]]].copy()
for c, lab, style in [(KEY["z3"], "FUR-Z3-TEMP (°C)", "-"), (KEY["pmean"], "PROF-MEAN (°C)", "-"),
                      (KEY["pedgel"], "PROF EDGE-L-DEV (°C)", "-"), (KEY["pedger"], "PROF EDGE-R-DEV (°C)", "-"),
                      (KEY["yield"], "FUR-YIELD (%)", "-")]:
    s = m[c] - m[c].mean()
    ax2.plot(m[tcol], s / s.std(), style, lw=1.1, label=f"{lab} (z)")
ax2.axhline(0, color="gray", lw=0.6)
for lab, e in ev_lines:
    ax2.axvline(e, color="#d62728", ls="--", lw=1.2)
ax2.set_ylabel("z-score (0-mean, 1-std)")
ax2.set_xlabel("Time (10-min anchor grid)")
ax2.legend(loc="upper right", ncol=3, fontsize=8)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_hetero_profile_heatmap.png"), dpi=160)
plt.close(fig)

# 8b. event response windows
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
metrics = [("z3", KEY["z3"]), ("out", KEY["out"]), ("yield", KEY["yield"]), ("pmean", KEY["pmean"]), ("pedger", KEY["pedger"])]
for axi, (evname, ev) in enumerate([("maintenance 02-06 06:40", EV_MAINT), ("heatup 02-08 10:00", EV_HEATUP)]):
    ax = axes[axi]
    xs, labs = [], []
    for k, c in metrics:
        b = df[(df[tcol] >= ev - pd.Timedelta(hours=12)) & (df[tcol] < ev)][c].mean()
        a = df[(df[tcol] >= ev) & (df[tcol] < ev + pd.Timedelta(hours=12))][c].mean()
        xs.append((a - b) / (abs(b) + 1e-9) * 100)
        labs.append(f"{k}\n(b {b:.3g}→a {a:.3g})")
    colors = ["#d62728" if v < 0 else "#2ca02c" for v in xs]
    ax.bar(range(len(xs)), xs, color=colors)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels(labs, fontsize=7)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title(f"±12h relative change around {evname}", fontsize=10)
    ax.set_ylabel("relative change after vs before (%)")
fig.suptitle("Event-response windows (cleaner: maintenance & heatup) — after/before ±12h means", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_event_response.png"), dpi=160)
plt.close(fig)

# append to plot_manifest
mfile = os.path.join(FIG, "plot_manifest.json")
if os.path.exists(mfile):
    with open(mfile, encoding="utf-8") as f:
        pm = json.load(f)
else:
    pm = {"plots": [], "metadata": {}}
pm.setdefault("plots", [])
have = {p.get("filename") for p in pm["plots"]}
add = [
    {"filename": "fig_hetero_profile_heatmap.png", "path": os.path.join(FIG, "fig_hetero_profile_heatmap.png"),
     "figure_type": "profile_heatmap_over_time", "priority": "CRITICAL",
     "description_zh": "带材横向温度剖面 时间×位置 热图（12 位点 × 480 快照）+ 事件线与关键参数 z 叠加",
     "diagnostic_question": "剖面水平/边部偏差何时开始恶化？是否与 02-06 检修与 02-08 升温事件对齐？",
     "columns": [KEY["pmean"], KEY["pedgel"], KEY["pedger"], KEY["z3"], KEY["yield"]],
     "source": "07_hetero/features/PROF-L1BANDTEMPPROFILE30M.csv + 02_processed/cleaned_data.csv"},
    {"filename": "fig_event_response.png", "path": os.path.join(FIG, "fig_event_response.png"),
     "figure_type": "event_response_bar", "priority": "HIGH",
     "description_zh": "维护/升温事件前后 ±12h 相对变化（Z3/出口温度/收得率/剖面均值/右边缘偏差）",
     "diagnostic_question": "事件是否伴随指标的台阶式变化（非稳态窗证据）？",
     "columns": [KEY["z3"], KEY["out"], KEY["yield"], KEY["pmean"], KEY["pedger"]],
     "source": "02_processed/cleaned_data.csv"},
]
for a in add:
    if a["filename"] not in have:
        pm["plots"].append(a)
pm.setdefault("metadata", {})["expert_analysis_script"] = "06_scripts/expert_analysis.py"
Path(mfile).write_text(json.dumps(pm, ensure_ascii=False, indent=1), encoding="utf-8")
print("figures written + plot_manifest updated")

# digest print
print("\nregime segments:")
for k, v in seg_stats.items():
    print(f"  {k}: n={v['n_rows']} [{v['start']} .. {v['end']}]")
print("deltas (B-A / D-A):")
for k, v in deltas.items():
    print(f"  {k}: A={v['A_pre']} B={v['B_maint']} D={v['D_restored']} dB-A={v['B_minus_A']} dD-A={v['D_minus_A']}")
print("within-segment key corr z3~yield / z3~out / z3~pmean:")
for k, v in seg_corr.items():
    print(f"  {k}: {v.get('z3~yield')} | {v.get('z3~out')} | {v.get('z3~pmean')} (n={v['n_rows']})")
print("snapshot-level:")
for k, v in snap.items():
    print(f"  {k}: {json.dumps(v)}")
print("probes:", json.dumps(probes))
print("dip window:", json.dumps(out.get("out_temp_dip_window_steady_idx722_933")))
print("yield cp window:", json.dumps(out.get("yield_cp_window_steady_idx663_977")))
