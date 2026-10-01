"""RSM: stationary point with Hessian classification + Derringer-Suich desirability.

The quadratic model comes from effects_anova (term name conventions: linear = the
factor column, curvature = "F^2", interaction = "F:G"). Stationary point
x_s = -H^-1 b with H_ii = 2*coef(F^2), H_ij = coef(F:G); eigenvalues classify
min/max/saddle (P2 review: saddle/out-of-box points only warn, optimization is
always box-constrained).
"""

import numpy as np
from scipy import optimize as sps_opt


def stationary_point(model):
    """Returns None for non-quadratic models; else coded/raw stationary point."""
    core = [i for i in model["factor_info"]
            if not i.get("is_block") and not i.get("is_covariate")
            and not i["zero_variance"] and i["type"] == "numeric"]
    names = [i["col"] for i in core]
    k = len(names)
    if k == 0:
        return None
    coefs = {}
    for term, specs in model["kept_specs"]:
        if len(specs) == 1 and specs[0]["name"] in model["colnames"]:
            coefs[term["name"]] = float(model["beta"][model["colnames"].index(specs[0]["name"]) + 1])
    has_quad = any(f"{f}^2" in coefs for f in names)
    has_2fi = any(f"{a}:{c}" in coefs for a, c in __import__("itertools").combinations(names, 2))
    if not (has_quad or has_2fi):
        return None
    b = np.array([coefs.get(f, 0.0) for f in names])
    H = np.zeros((k, k))
    for i, f in enumerate(names):
        H[i, i] = 2.0 * coefs.get(f"{f}^2", 0.0)
    for i in range(k):
        for j in range(i + 1, k):
            H[i, j] = H[j, i] = coefs.get(f"{names[i]}:{names[j]}", 0.0)
    try:
        x_s = -np.linalg.solve(H, b)
    except np.linalg.LinAlgError:
        return None
    eig = np.linalg.eigvalsh(H)
    tol = 1e-9 * max(1.0, float(np.abs(eig).max()))
    if np.all(eig <= tol):
        kind = "max"
    elif np.all(eig >= -tol):
        kind = "min"
    else:
        kind = "saddle"
    in_box = bool(np.all(np.abs(x_s) <= 1.0 + 1e-9))
    return {
        "coded": {f: round(float(v), 6) for f, v in zip(names, x_s)},
        "raw": {f: round(info["mean"] + xs * info["half_range"], 6)
                for f, xs, info in zip(names, x_s, core)},
        "classification": kind,
        "inside_design_region": in_box,
        "eigenvalues": [round(float(e), 6) for e in eig],
        "warning": (None if (kind == "max" and in_box) else
                    "驻点为鞍点或落在设计域外 — 仅作警告，优化请在盒约束内进行 (W3/W5)"),
    }


def d_individual(y, spec, grid_lo, grid_hi):
    """Derringer-Suich individual desirability (s=t=1).

    target-type when a target and both spec limits exist; otherwise
    maximize/minimize against [lsl|grid_lo, usl|target|grid_hi].
    """
    lsl, usl, target = spec.get("lsl"), spec.get("usl"), spec.get("target")
    goal = spec.get("goal")
    if target is not None and lsl is not None and usl is not None:
        if y <= target:
            lo, hi = lsl, target
        else:
            lo, hi = target, usl
        val = abs(y - target)
        span_hi = abs(hi - lo)
        return 0.0 if span_hi <= 0 else max(0.0, 1.0 - val / span_hi)
    if goal == "minimize" or (goal is None and usl is not None and lsl is None):
        lo = grid_hi if grid_hi is not None else y
        hi = usl if usl is not None else grid_lo
        span = lo - hi
        return 0.0 if span <= 0 else max(0.0, min(1.0, (lo - y) / span))
    # maximize (default)
    lo = lsl if lsl is not None else (grid_lo if grid_lo is not None else y)
    hi = usl or target if (usl is not None or target is not None) else grid_hi
    span = (hi if hi is not None else y) - lo
    return 0.0 if span <= 0 else max(0.0, min(1.0, (y - lo) / span))


def combined_desirability(y_by_response, specs, grid_lo_hi):
    """D = (prod d_i^w_i)^(1/sum w). Returns (D, per-response d dict)."""
    num, den, ds = 0.0, 0.0, {}
    for resp, y in y_by_response.items():
        spec = specs.get(resp, {})
        lo, hi = (grid_lo_hi or {}).get(resp, (None, None))
        d = d_individual(float(y), spec, lo, hi)
        w = float(spec.get("weight") or 1.0)
        ds[resp] = round(d, 6)
        num += w * np.log(max(d, 1e-12))
        den += w
    if den <= 0:
        return 0.0, ds
    return float(np.exp(num / den)), ds


def refine_optimum(predict_fns, specs, factor_info, active, fixed_raw, grid_lo_hi):
    """L-BFGS-B refine of the desirability optimum inside the coded box (W2)."""
    infos = {i["col"]: i for i in factor_info}
    names = list(active)

    def neg_D(x_coded):
        raw = dict(fixed_raw)
        for f, v in zip(names, x_coded):
            raw[f] = infos[f]["mean"] + float(v) * infos[f]["half_range"]
        y_by = {}
        for resp, fn in predict_fns.items():
            yv = fn(raw)
            if yv is None or not np.isfinite(yv):
                return 1e6
            y_by[resp] = yv
        D, _ = combined_desirability(y_by, specs, grid_lo_hi)
        return -D

    x0 = np.zeros(len(names))
    res = sps_opt.minimize(neg_D, x0, method="L-BFGS-B",
                           bounds=[(-1.0, 1.0)] * len(names))
    best = {"coded": {f: round(float(v), 6) for f, v in zip(names, res.x)},
            "D": round(float(-res.fun), 6)}
    raw = dict(fixed_raw)
    for f, v in zip(names, res.x):
        raw[f] = infos[f]["mean"] + float(v) * infos[f]["half_range"]
    best["raw"] = {f: round(float(v), 6) for f, v in raw.items()}
    return best
