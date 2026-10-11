"""Regime (working-condition) segmentation — reuse industrial-sentinel's
sentinelcore.regime_map (C3 pipeline: variance-ratio + drift-ramp fusion,
binary-segmentation change points with significance filter). Graceful method
reporting when the fast detector (data-processor) is unavailable."""
from __future__ import annotations

import os
import sys

import numpy as np

_SENTINEL_SCRIPTS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "industrial-sentinel", "scripts"))


def _load_regime_map():
    try:
        if _SENTINEL_SCRIPTS not in sys.path:
            sys.path.insert(0, _SENTINEL_SCRIPTS)
        from sentinelcore import regime_map  # noqa: PLC0415
        return regime_map
    except Exception:
        return None


def detect_regimes(df, param_cols: list[str], min_rows: int = 60) -> dict:
    """Segment the period into working-condition regimes.

    Returns {available, method, change_points, regimes: [{start,end,label}],
    abnormal_ratio}. Row indices are 0-based into the analyzed (possibly
    sampled) frame.
    """
    empty = {"available": False, "method": None, "change_points": [],
             "regimes": [], "abnormal_ratio": None}
    n = len(df)
    if n < min_rows or len(param_cols) < 2:
        return {**empty, "method": "skipped_too_few_rows_or_params"}
    mod = _load_regime_map()
    if mod is None:
        return {**empty, "method": "sentinelcore_unavailable"}
    arrays = {c: pd_to_num(df[c]) for c in param_cols}
    z_mean = None
    stacked = [a for a in arrays.values() if a is not None]
    if stacked:
        mat = np.vstack(stacked)
        with np.errstate(invalid="ignore"):
            med = np.nanmedian(mat, axis=0)
            mad = np.nanmedian(np.abs(mat - med), axis=0)
        scale = np.where(mad > 0, 1.4826 * mad, 1.0)
        z_mean = np.nanmean((mat - med) / scale, axis=0)
    try:
        res = mod.detect({c: a for c, a in arrays.items() if a is not None},
                         z_mean=z_mean)
    except Exception:
        return {**empty, "method": "detect_failed"}
    cps = [int(c) for c in res.get("change_points", [])]
    labels = res.get("labels") or []
    bounds = [0, *cps, n - 1]
    regimes = []
    for i in range(len(bounds) - 1):
        start, end = int(bounds[i]), int(bounds[i + 1])
        seg_labels = labels[start:end + 1] if labels else []
        dominant = max(set(seg_labels), key=seg_labels.count) if seg_labels else "steady"
        regimes.append({"start": start, "end": end, "label": str(dominant),
                        "n_rows": end - start + 1})
    return {"available": True,
            "method": str(res.get("method")),
            "change_points": cps,
            "regimes": regimes,
            "abnormal_ratio": res.get("abnormal_ratio")}


def pd_to_num(col) -> np.ndarray | None:
    import pandas as pd
    try:
        return pd.to_numeric(col, errors="coerce").to_numpy(dtype=float)
    except Exception:
        return None
