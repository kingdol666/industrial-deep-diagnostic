#!/usr/bin/env python3
"""Causal evidence map (skill 5.7) — deterministic redraw with real edges.

Reads 02_processed/validate_report.json (validations), filters to significant
pairs (p<0.05 and |r|>=0.5, excluding constant columns), draws a bipartite
evidence map, writes:
  - 02_processed/causal_evidence_map.json
  - 03_figures/fig6_causal_evidence_map.png   (overwrites dp_toolkit render)
"""
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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

vr = json.load(open(os.path.join(PROC, "validate_report.json"), encoding="utf-8"))
val = vr["validations"]
edges = [v for v in val if v.get("p_value", 1) < 0.05 and abs(v["pearson_r"]) >= 0.5]
hard = [v for v in edges if abs(v["pearson_r"]) >= 0.7]

preds = sorted({e["parameter"] for e in edges})
targets = sorted({e["target"] for e in edges})
short = lambda c: c.replace("HX-PROF-L1BANDTEMPPROFILE30M-", "PROF.").replace("HX-MAP-L1FURNACETHERMALMAP2-", "MAP.").replace("HX-IMG-L1SURFACECCDINDEX-", "IMG.").replace("HX-TXT-L1OPERATORNOTES-", "TXT.").replace("FUR-", "")

# root-cause candidates: predictors connected to >=3 targets with |r|>=0.7
deg = {}
for e in hard:
    deg[e["parameter"]] = deg.get(e["parameter"], 0) + 1
candidates = sorted([k for k, n in deg.items() if n >= 3], key=lambda k: -deg[k])

fig, ax = plt.subplots(figsize=(13.5, 9))
yp = np.linspace(0.05, 0.95, len(preds))
yt = np.linspace(0.05, 0.95, len(targets))
px = {p: 0.06 for p in preds}
tx = {t: 0.72 for t in targets}
for p, y in zip(preds, yp):
    c = "#d62728" if p in candidates else "#1f77b4"
    ax.scatter([px[p]], [y], s=180, color=c, zorder=3)
    ax.text(px[p] - 0.012, y, short(p), ha="right", va="center", fontsize=9)
for t, y in zip(targets, yt):
    ax.scatter([tx[t]], [y], s=190, marker="s", color="#2ca02c", zorder=3)
    ax.text(tx[t] + 0.012, y, short(t), ha="left", va="center", fontsize=9)
for e in edges:
    y1 = yp[preds.index(e["parameter"])]
    y2 = yt[targets.index(e["target"])]
    r = e["pearson_r"]
    w = 0.6 + 2.6 * abs(r)
    col = "#d62728" if abs(r) >= 0.7 else "#ff9f4a" if r > 0 else "#8ca0b3"
    ax.plot([px[e["parameter"]] + 0.01, tx[e["target"]] - 0.01], [y1, y2], lw=w, color=col, alpha=0.45, zorder=1)
    if abs(r) >= 0.85:
        ax.text((px[e["parameter"]] + tx[e["target"]]) / 2, (y1 + y2) / 2, f"{r:.2f}", fontsize=7.5, color="#7a1010", ha="center")
ax.set_xlim(-0.30, 1.05)
ax.set_ylim(0, 1)
ax.axis("off")
ax.set_title("Causal evidence map — significant pairs |r|>=0.5 (red node = candidate hub with >=3 edges at |r|>=0.7)\n"
             "edges: red |r|>=0.7, orange 0.5-0.7; steady-state n=1367 (10-min anchor rows; HX columns backward-merged)", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig6_causal_evidence_map.png"), dpi=160)
plt.close(fig)

out = {
    "generated_by": "06_scripts/causal_map.py (data-processor)",
    "edge_filter": "p<0.05 and |r|>=0.5 (steady-state; excludes constant columns)",
    "n_edges": len(edges), "n_edges_strong_ge_0.7": len(hard),
    "candidate_hubs": [{"column": c, "strong_edges": deg[c]} for c in candidates],
    "edges": [{"parameter": e["parameter"], "target": e["target"], "pearson_r": e["pearson_r"],
               "spearman_rho": e.get("spearman_rho"), "detrended_r": e.get("detrended_r"),
               "best_lag_steps": e.get("best_lag_steps"), "evidence_grade": e.get("evidence_grade"),
               "warnings": e.get("warnings", [])} for e in sorted(edges, key=lambda x: -abs(x["pearson_r"]))],
}
Path(PROC, "causal_evidence_map.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"causal map: {len(edges)} edges ({len(hard)} strong), hubs: {[c for c in candidates]}")
