"""imacore.levers — column role classification, variance gates, reverse
causality exclusion (method_notes §2 门A / 五陷阱).

Role sources (deterministic priority):
  KPIs   : explicit objective targets/kpis > ontology inspection_signals
           (role=target) > context.inspection_cols
  levers : explicit objective levers > ontology control_variables >
           context.parameter_cols > ontology process_parameters (fallback)
  Never a lever: time/group/metadata columns, the target KPI itself,
  non-numeric columns, reverse-causal parameters (excluded_levers).
"""

import numpy as np
import pandas as pd

from . import _io


def classify(df, time_col, group_col, ontology, objective, context):
    """Return {"levers","kpis","metadata"} plus disclosure lists."""
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    numeric_set = set(numeric)
    context = context or {}
    objective = objective or {}

    kpis = []
    for src in (
        [t.get("metric") for t in (objective.get("targets") or [])],
        list(objective.get("kpis") or []),
        [s.get("column") for s in _bucket(ontology, "inspection_signals")],
        list(context.get("inspection_cols") or []),
    ):
        for name in src:
            if name and str(name) in numeric_set and str(name) not in kpis:
                kpis.append(str(name))

    levers = []
    for src in (
        list(objective.get("levers") or []),
        [s.get("column") for s in _bucket(ontology, "control_variables")],
        [s.get("column") for s in _bucket(ontology, "process_parameters")],
        list(context.get("parameter_cols") or []),
    ):
        for name in src:
            if name and str(name) in numeric_set and str(name) not in levers:
                levers.append(str(name))
    if not levers:
        for name in [s.get("column") for s in _bucket(ontology, "process_parameters")]:
            if name and str(name) in numeric_set and str(name) not in levers:
                levers.append(str(name))
    if not levers:
        # deterministic last resort: every numeric non-KPI column (disclosed)
        levers = [c for c in numeric if c not in kpis]

    levers = [c for c in levers if c != (time_col or "") and c != (group_col or "")
              and c not in kpis]
    # Ontology role=confounder means "ambient/uncontrollable known disturber":
    # never a lever, never an inferred KPI (an explicit user-declared target wins).
    explicit_kpis = {str(t.get("metric")) for t in (objective.get("targets") or [])
                     if isinstance(t, dict) and t.get("metric")}
    explicit_kpis |= {str(x) for x in (objective.get("kpis") or [])}
    confounders = set()
    for bucket in ("process_parameters", "control_variables", "inspection_signals"):
        for sig in _bucket(ontology, bucket):
            if sig.get("role") == "confounder" and sig.get("column"):
                confounders.add(str(sig["column"]))
    levers = [c for c in levers if c not in confounders]
    kpis = [c for c in kpis if c not in confounders or c in explicit_kpis]
    metadata = [c for c in (time_col, group_col) if c]
    metadata += [s.get("column") for s in _bucket(ontology, "metadata_columns")
                 if s.get("column")]
    return {"levers": levers, "kpis": kpis,
            "metadata": sorted(set(metadata))}


def _bucket(ontology, bucket):
    if not isinstance(ontology, dict):
        return []
    signals = ontology.get("signals")
    if not isinstance(signals, dict):
        return []
    items = signals.get(bucket) or []
    return [s for s in items if isinstance(s, dict)]


def variance_stats(df, col):
    s = df[col].dropna()
    if len(s) == 0:
        return {"n": 0, "cv": None, "nunique": 0, "mean": None, "sd": None,
                "min": None, "max": None, "q10": None, "q50": None, "q90": None}
    mean = float(s.mean())
    sd = float(s.std(ddof=1)) if len(s) > 1 else 0.0
    cv = abs(sd / mean) if abs(mean) > 1e-12 else (0.0 if sd < 1e-12 else float("inf"))
    return {
        "n": int(len(s)),
        "cv": _io.finite(cv),
        "nunique": int(s.nunique()),
        "mean": _io.finite(mean),
        "sd": _io.finite(sd),
        "min": _io.finite(s.min()),
        "max": _io.finite(s.max()),
        "q10": _io.finite(s.quantile(0.10)),
        "q50": _io.finite(s.quantile(0.50)),
        "q90": _io.finite(s.quantile(0.90)),
    }


def has_variance(stats):
    cv = stats.get("cv")
    return (stats.get("nunique") or 0) > 2 and cv is not None and cv > 1e-12


def reverse_causality(df, lever, kpi, max_lag):
    """Lead-lag asymmetry test (五陷阱): KPI leading the lever at negative lags
    with a stronger |r| than any positive (lever-leads) lag ⇒ reverse causal.

    Convention: core_stats.full_lag_ccf pairs lever[i] with kpi[i+lag]; a
    positive lag means the lever leads the KPI (the actionable direction).
    """
    cs = _io.core_stats
    if cs is None:
        return {"reverse": False, "available": False}
    lag = max(1, int(max_lag or 3))
    try:
        ccf = cs.full_lag_ccf(df[lever].tolist(), df[kpi].tolist(), lag)
    except Exception:
        return {"reverse": False, "available": False}
    pos = [e for e in ccf if e["lag"] >= 0 and e.get("r") is not None]
    neg = [e for e in ccf if e["lag"] < 0 and e.get("r") is not None]
    if not pos or not neg:
        return {"reverse": False, "available": True}
    best_pos = max(pos, key=lambda e: abs(e["r"]))
    best_neg = max(neg, key=lambda e: abs(e["r"]))
    reverse = (abs(best_neg["r"]) > abs(best_pos["r"])
               and abs(best_neg["r"]) >= _io.CONSTANTS["min_effect_r"])
    return {"reverse": bool(reverse), "available": True,
            "best_pos_lag": best_pos["lag"], "best_pos_r": _io.finite(best_pos["r"]),
            "best_neg_lag": best_neg["lag"], "best_neg_r": _io.finite(best_neg["r"])}


def segment_check(df, lever, kpi, segments=3, min_segment_n=20):
    """Direction robustness across time thirds (区间选择偏差防护)."""
    cs = _io.core_stats
    n = len(df)
    if cs is None or n < segments * min_segment_n:
        return {"stable": True, "available": False, "signs": []}
    signs = []
    bounds = np.linspace(0, n, segments + 1).astype(int)
    for i in range(segments):
        seg = df.iloc[bounds[i]:bounds[i + 1]]
        try:
            r = cs.pearson(seg[lever].tolist(), seg[kpi].tolist())["r"]
        except Exception:
            return {"stable": False, "available": False, "signs": []}
        if r is None:
            return {"stable": False, "available": False, "signs": []}
        signs.append(1 if r > 0 else (-1 if r < 0 else 0))
    nonzero = [s for s in signs if s != 0]
    stable = len(set(nonzero)) <= 1 and bool(nonzero)
    return {"stable": bool(stable), "available": True, "signs": signs}
