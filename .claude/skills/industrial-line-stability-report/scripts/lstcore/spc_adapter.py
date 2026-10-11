"""SPC adapter — reuse industrial-sentinel's sentinelcore as the single source
of SPC truth (house rule: no reinvented wheels). Falls back to a minimal local
implementation (recorded as a degradation) when the sibling skill is absent.

sentinelcore.spc.evaluate(z) returns episodes:
  [{rule_name: "NELSON_R1..R6", index, run_length, statistic}]
with materiality floors hardened during the 2026-10-04 field test.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_SENTINEL_SCRIPTS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "industrial-sentinel", "scripts"))

_SOURCE = None


def _load_sentinelcore():
    global _SOURCE
    if _SOURCE is None:
        try:
            if _SENTINEL_SCRIPTS not in sys.path:
                sys.path.insert(0, _SENTINEL_SCRIPTS)
            from sentinelcore import spc as _spc  # noqa: PLC0415
            _SOURCE = _spc
        except Exception:
            _SOURCE = False
    return _SOURCE


def source_name() -> str:
    return "sentinelcore" if _load_sentinelcore() else "local_fallback"


def sigma_within_mr(x: np.ndarray) -> float | None:
    mod = _load_sentinelcore()
    if mod:
        v = mod.sigma_within_mr(np.asarray(x, dtype=float))
        return float(v) if v is not None and np.isfinite(v) else None
    clean = np.asarray(x, dtype=float)
    clean = clean[~np.isnan(clean)]
    if len(clean) < 2:
        return None
    mr = np.abs(np.diff(clean))
    val = float(np.mean(mr) / 1.128)
    return val if np.isfinite(val) else None


def evaluate_episodes(x, center: float, sigma: float) -> list[dict]:
    """All five Nelson rules as episodes [{rule_name, index, run_length,
    statistic}] (0-based into x). sentinelcore when available."""
    mod = _load_sentinelcore()
    arr = np.asarray(x, dtype=float)
    if mod:
        if not sigma or not np.isfinite(sigma) or len(arr) < 3:
            return []
        z = (arr - center) / sigma
        return [e for e in mod.evaluate(z)]
    # local fallback (subset semantics: R1/R2/R5/R6 point episodes)
    episodes: list[dict] = []
    if not sigma or not np.isfinite(sigma) or len(arr) < 3:
        return episodes
    z = (arr - center) / sigma
    n = len(z)
    for i in range(n):
        if np.isfinite(z[i]) and abs(z[i]) > 3.0:
            episodes.append({"rule_name": "NELSON_R1", "index": i,
                             "run_length": 1, "statistic": float(z[i])})
    run_side, run_len = 0, 0
    for i in range(n):
        side = 1 if z[i] > 0 else (-1 if z[i] < 0 else 0)
        if side != 0 and side == run_side:
            run_len += 1
        else:
            run_side, run_len = side, (1 if side != 0 else 0)
        if run_len >= 9:
            episodes.append({"rule_name": "NELSON_R2", "index": i,
                             "run_length": run_len,
                             "statistic": float(z[i])})
    for i in range(2, n):
        w = z[i - 2:i + 1]
        if np.sum(w > 2.0) >= 2:
            idx = int(i - 2 + int(np.argmax(w > 2.0)))
            episodes.append({"rule_name": "NELSON_R5", "index": idx,
                             "run_length": 3, "statistic": float(z[idx])})
        elif np.sum(w < -2.0) >= 2:
            idx = int(i - 2 + int(np.argmax(w < -2.0)))
            episodes.append({"rule_name": "NELSON_R5", "index": idx,
                             "run_length": 3, "statistic": float(z[idx])})
    for i in range(4, n):
        w = z[i - 4:i + 1]
        if np.sum(w > 1.0) >= 4:
            idx = int(i - 4 + int(np.argmax(w > 1.0)))
            episodes.append({"rule_name": "NELSON_R6", "index": idx,
                             "run_length": 5, "statistic": float(z[idx])})
        elif np.sum(w < -1.0) >= 4:
            idx = int(i - 4 + int(np.argmax(w < -1.0)))
            episodes.append({"rule_name": "NELSON_R6", "index": idx,
                             "run_length": 5, "statistic": float(z[idx])})
    return episodes


def robust_z_value(x, baseline_median: float, baseline_mad: float) -> float | None:
    """Robust z vs a sentinel baseline — reuses sentinelcore.robust when present."""
    mod = _load_sentinelcore()
    arr = np.asarray(x, dtype=float)
    arr = arr[~np.isnan(arr)]
    if not len(arr) or not baseline_mad:
        return None
    if mod:
        try:
            from sentinelcore import robust as _robust  # noqa: PLC0415
            v = _robust.robust_z(arr, float(baseline_median), float(baseline_mad))
            v = float(np.nanmedian(v)) if hasattr(v, "__len__") else float(v)
            return v if np.isfinite(v) else None
        except Exception:
            pass
    val = float((np.median(arr) - baseline_median) / (1.4826 * baseline_mad))
    return val if np.isfinite(val) else None


def rule_label(rule_name: str) -> str:
    return str(rule_name).replace("NELSON_", "R")
