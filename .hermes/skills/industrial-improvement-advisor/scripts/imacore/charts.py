"""imacore.charts — deterministic chart data bundle for report_builder.

No rendering here; report_builder draws inline SVG from these series.
Downsampled to ≤500 points per series (deterministic stride).
"""

from . import _io

MAX_POINTS = 500


def _downsample(series, max_points=MAX_POINTS):
    n = len(series)
    if n <= max_points:
        return [[i, _io.finite(v)] for i, v in enumerate(series)]
    stride = int((n + max_points - 1) // max_points)
    return [[i, _io.finite(series[i])] for i in range(0, n, stride)]


def build_charts(df, targets, dose_bins, window_notes, lever_names):
    kpis = []
    for t in targets:
        metric = t.get("metric")
        if metric in df.columns:
            clean = df[metric].dropna()
            kpis.append({
                "metric": metric,
                "direction": t.get("direction"),
                "points": _downsample(clean.tolist()),
                "n": int(len(clean)),
            })
    doses = []
    for item in dose_bins:
        doses.append({
            "lever": item.get("lever"), "metric": item.get("metric"),
            "bins": item.get("bins") or [],
            "slope": item.get("slope"),
            "slope_ci95": item.get("slope_ci95"),
        })
    return {
        "contract_version": "improvement-advisory-charts/1.0",
        "kpi_series": kpis,
        "dose_response": doses,
        "windows": window_notes or [],
        "levers": lever_names,
        "note": ("downsampled stride disclosure: see points density; "
                 "charts are script-authored, agent must not alter numbers"),
    }
