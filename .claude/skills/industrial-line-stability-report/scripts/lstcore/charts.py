"""ECharts data bundles for the HTML landing page."""
from __future__ import annotations

import numpy as np

MAX_TREND_POINTS = 1500
MAX_TREND_PARAMS = 12


def _epoch_ms(v) -> float:
    return int(v.value // 10**6) if hasattr(v, "value") else int(v * 1000)


def build_charts(report: dict, df, roles: dict, top_n: int = MAX_TREND_PARAMS) -> dict:
    """Trend series (downsampled, violation points always kept), score bars,
    correlation heatmap and contribution bars."""
    params = report["parameters"][:top_n]
    byolename = {p["name"]: p for p in report["parameters"]}
    trend = []
    for p in params:
        col = p["name"]
        v = df[col].to_numpy(dtype=float)
        n = len(v)
        stride = max(1, int(np.ceil(n / MAX_TREND_POINTS))) if n else 1
        keep = sorted(set(range(0, n, stride))
                      | {idx for d in p["nelson"].values() for idx in d["indices"]})
        ts = df["_dt"]
        t_out = [ts.iloc[i].value // 10**6 if hasattr(ts.iloc[i], "value")
                 else float(ts.iloc[i]) * 1000.0 for i in keep]
        sigma = p["sigma_within_mr"] or p["sigma"] or 0.0
        trend.append({
            "name": col,
            "role": p["role"],
            "n": n,
            "n_plotted": len(keep),
            "t": t_out,
            "v": [None if not np.isfinite(v[i]) else round(float(v[i]), 6) for i in keep],
            "center": p["median"],
            "ucl": round(p["median"] + 3 * sigma, 6) if sigma else None,
            "lcl": round(p["median"] - 3 * sigma, 6) if sigma else None,
            "violation_indices_in_plot": [
                keep.index(idx) for rule, idxs in p["nelson"].items() for idx in idxs
                if idx in keep],
            "spec": p["spec"],
        })
    heatmap_labels = [p["name"] for p in report["parameters"]]
    matrix = [[None] * len(heatmap_labels) for _ in heatmap_labels]
    pair_map = {}
    for pair in report.get("correlations", {}).get("pairs", []):
        pair_map[(pair["a"], pair["b"])] = pair["best_abs_r"]
        pair_map[(pair["b"], pair["a"])] = pair["best_abs_r"]
    for i, a in enumerate(heatmap_labels):
        for j, b in enumerate(heatmap_labels):
            if i == j:
                matrix[i][j] = 1.0
            else:
                matrix[i][j] = pair_map.get((a, b))
    return {
        "contract_version": "line-stability-charts/1.0",
        "trend": trend,
        "score_bars": [{"name": p["name"], "score": p["score"],
                        "role": p["role"]} for p in report["parameters"]],
        "corr_heatmap": {"labels": heatmap_labels, "matrix": matrix},
        "contribution_bar": report.get("correlations", {}).get("contributions", []),
    }
