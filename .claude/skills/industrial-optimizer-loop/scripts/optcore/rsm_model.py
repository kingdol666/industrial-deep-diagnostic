"""rsm_model.py — quadratic RSM / poly_refine for the optimizer loop.

Reuse contract (same precedent as doe-analyzer correlation.py reusing
core_stats): sys.path-inject the doe-analyzer scripts directory, then
    from doestats import rsm, effects_anova
    from doestats._stats_util import ols_fit
rsm.combined_desirability / rsm.refine_optimum are THE D implementations;
this module only builds coded quadratic design matrices, curvature evidence
(OLS t-tests, same se = sqrt(sigma^2 * diag([X'X]^-1)) caliber as
effects_anova), stationary-point/Hessian classification (rsm.stationary_point
semantics), and box-constrained optimum refinement.
"""

import itertools

import numpy as np

from . import DOE_SCRIPTS

if str(DOE_SCRIPTS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(DOE_SCRIPTS))

from doestats import effects_anova as _anova  # noqa: E402,F401  (caliber reuse)
from doestats import rsm as _rsm              # noqa: E402
from doestats._stats_util import ols_fit      # noqa: E402

combined_desirability = _rsm.combined_desirability
refine_optimum = _rsm.refine_optimum

CURVATURE_T_THRESHOLD = 2.0  # ~95% two-sided on large df; pinned in method_notes


def split_grid(specs):
    """objective.metric_specs output -> (clean_specs, grid_lo_hi) for
    rsm.combined_desirability."""
    clean, grid = {}, {}
    for metric, spec in specs.items():
        clean[metric] = {k: v for k, v in spec.items() if not k.startswith("_")}
        grid[metric] = (spec.get("_grid_lo"), spec.get("_grid_hi"))
    return clean, grid


def quad_term_names(k):
    names = [f"x{i}" for i in range(k)]
    quads = [f"x{i}^2" for i in range(k)]
    twofi = [f"x{i}:x{j}" for i, j in itertools.combinations(range(k), 2)]
    return names, quads, twofi


def quad_design_matrix(Xc, with_intercept=True, with_2fi=True):
    """Coded quadratic expansion: 1 + x + x^2 [+ x:x] (column order)."""
    Xc = np.atleast_2d(np.asarray(Xc, dtype=float))
    n, k = Xc.shape
    cols = [np.ones(n)] if with_intercept else []
    for i in range(k):
        cols.append(Xc[:, i])
    for i in range(k):
        cols.append(Xc[:, i] ** 2)
    if with_2fi:
        for i, j in itertools.combinations(range(k), 2):
            cols.append(Xc[:, i] * Xc[:, j])
    return np.column_stack(cols)


def quad_term_names(k, with_2fi=True):
    names = [f"x{i}" for i in range(k)]
    quads = [f"x{i}^2" for i in range(k)]
    twofi = [f"x{i}:x{j}" for i, j in itertools.combinations(range(k), 2)]
    return names, quads, (twofi if with_2fi else [])


def fit_quadratic(Xc, y, with_2fi=True):
    """OLS quadratic (doestats ols_fit caliber — ols_fit prepends its own
    intercept). with_2fi=False fits the 1+x+x^2 model (used as the curvature
    probe when n cannot support the full quadratic). Returns model dict with
    predict(coded), curvature evidence, stationary point + Hessian class."""
    Xc = np.atleast_2d(np.asarray(Xc, dtype=float))
    y = np.asarray(y, dtype=float)
    n, k = Xc.shape
    Xm = quad_design_matrix(Xc, with_intercept=False, with_2fi=with_2fi)
    beta, rank, rss, xtx_inv, Xa = ols_fit(Xm, y)
    p = Xa.shape[1]
    lin_names, quad_names, twofi_names = quad_term_names(k, with_2fi=with_2fi)
    names = ["intercept"] + lin_names + quad_names + twofi_names
    t_stats = {}
    sigma2 = rss / max(n - p, 1)
    if xtx_inv is not None:
        se = np.sqrt(np.maximum(sigma2 * np.diag(xtx_inv), 0.0))
        for j in range(1, min(p, len(names))):
            t_stats[names[j]] = float(beta[j] / se[j]) if se[j] > 0 else 0.0
    quad_ts = [t for nm, t in t_stats.items()
               if nm.endswith("^2") or ":" in nm]
    curvature = bool(n > p and quad_ts
                     and max(abs(t) for t in quad_ts) >= CURVATURE_T_THRESHOLD)
    ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1.0
    r2 = 1.0 - rss / ss_tot

    lin = np.array([float(beta[1 + i]) for i in range(k)]) if p >= 1 + k \
        else np.zeros(k)
    coef_q = {}
    idx = 1 + k
    for i in range(k):
        coef_q[f"x{i}^2"] = float(beta[idx]) if idx < p else 0.0
        idx += 1
    for i, j in itertools.combinations(range(k), 2):
        coef_q[f"x{i}:x{j}"] = float(beta[idx]) if idx < p else 0.0
        idx += 1
    H = np.zeros((k, k))
    for i in range(k):
        H[i, i] = 2.0 * coef_q.get(f"x{i}^2", 0.0)
    for i, j in itertools.combinations(range(k), 2):
        H[i, j] = H[j, i] = coef_q.get(f"x{i}:x{j}", 0.0)
    stationary = None
    try:
        if np.linalg.matrix_rank(H) == k and p >= 1 + 2 * k:
            x_s = -np.linalg.solve(H, lin)
            eig = np.linalg.eigvalsh(H)
            tol = 1e-9 * max(1.0, float(np.abs(eig).max()))
            kind = "max" if np.all(eig <= tol) else (
                "min" if np.all(eig >= -tol) else "saddle")
            stationary = {"coded": np.clip(x_s, -1.0, 1.0).tolist(),
                          "classification": kind,
                          "eigenvalues": [float(e) for e in eig],
                          "inside_box": bool(np.all(np.abs(x_s) <= 1.0 + 1e-9))}
    except np.linalg.LinAlgError:
        stationary = None

    def predict(Xq):
        return quad_design_matrix(Xq) @ beta

    return {"beta": beta, "names": names, "r2": float(r2), "rss": rss,
            "rank": int(rank), "n_params": int(p), "t_stats": t_stats,
            "curvature": curvature, "stationary": stationary,
            "predict": predict, "k": k}


def d_vectorized(draws, metrics, specs, grid):
    """Vectorized mirror of doe-analyzer rsm.d_individual + combined
    (geometric weighted mean). Test C5 asserts pointwise equality with
    rsm.combined_desirability within 1e-12, so the two stay the same caliber.

    draws: (m, len(metrics)) raw-unit draws. Returns (m,) D values.
    """
    draws = np.atleast_2d(np.asarray(draws, dtype=float))
    num = np.zeros(draws.shape[0])
    den = 0.0
    for j, metric in enumerate(metrics):
        spec = specs.get(metric, {})
        lsl, usl, target = spec.get("lsl"), spec.get("usl"), spec.get("target")
        goal = spec.get("goal")
        y = draws[:, j]
        glo, ghi = grid.get(metric, (None, None))
        if target is not None and lsl is not None and usl is not None:
            span = np.where(y <= target, float(target) - float(lsl),
                            float(usl) - float(target))
            d = np.where(span <= 0, 0.0,
                         np.maximum(0.0, 1.0 - np.abs(y - target) / span))
        elif goal == "minimize" or (goal is None and usl is not None
                                    and lsl is None):
            lo = ghi if ghi is not None else y
            hi = usl if usl is not None else glo
            span = lo - hi
            d = np.where(span <= 0, 0.0,
                         np.clip((lo - y) / span, 0.0, 1.0))
        else:  # maximize (default)
            lo = lsl if lsl is not None else (glo if glo is not None else y)
            hi = (usl or target) if (usl is not None or target is not None) \
                else ghi
            span = hi - lo
            d = np.where(span <= 0, 0.0,
                         np.clip((y - lo) / span, 0.0, 1.0))
        w = float(spec.get("weight") or 1.0)
        num += w * np.log(np.maximum(d, 1e-12))
        den += w
    if den <= 0:
        return np.zeros(draws.shape[0])
    return np.exp(num / den)


def factor_info_adapter(domain_numeric):
    """doe-analyzer factor_info-shaped dicts for rsm.refine_optimum."""
    infos = []
    for name, spec in domain_numeric.items():
        lo, hi = spec["lo"], spec["hi"]
        infos.append({"col": name, "mean": (lo + hi) / 2.0,
                      "half_range": (hi - lo) / 2.0, "type": "numeric",
                      "zero_variance": False, "is_block": False,
                      "is_covariate": False, "unit": None, "levels": []})
    return infos


def refine_optimum_D(predict_fns, specs, domain_numeric, active=None,
                     fixed_raw=None):
    """Box-constrained desirability optimum via doe-analyzer
    rsm.refine_optimum (L-BFGS-B inside the coded box). Returns {coded, raw, D}."""
    infos = factor_info_adapter(domain_numeric)
    names = [i["col"] for i in infos] if active is None else list(active)
    clean, grid = split_grid(specs)
    best = refine_optimum(predict_fns, clean, infos, names, fixed_raw or {}, grid)
    return best


def propose_rsm_augment(incumbent_coded, k, batch, step=0.6):
    """RSM augmentation batch: center (incumbent) + 2k axial + corner fillers.
    Total = 2k+4 when batch allows (pinned batch for rsm_augment)."""
    pts = [dict(incumbent_coded)]
    for i in range(k):
        for s in (+step, -step):
            p = dict(incumbent_coded)
            p[f"x{i}"] = float(np.clip(incumbent_coded[f"x{i}"] + s, -1.0, 1.0))
            pts.append(p)
    corner_steps = list(itertools.product((-step, step), repeat=min(k, 3)))
    ci = 0
    while len(pts) < batch and ci < len(corner_steps) * max(1, k // 3):
        combo = corner_steps[ci % len(corner_steps)]
        p = dict(incumbent_coded)
        for d, s in enumerate(combo):
            p[f"x{d}"] = float(np.clip(incumbent_coded[f"x{d}"] + s, -1.0, 1.0))
        pts.append(p)
        ci += 1
    while len(pts) < batch:
        pts.append(dict(incumbent_coded))
    return pts[:max(batch, 1)]


def propose_poly_refine(quad_model, specs, domain_numeric, batch, seed=42,
                        grid_n=6):
    """poly_refine proposal: coded grid coarse search -> L-BFGS-B fine search
    (refine_optimum_D) on the fitted quadratic -> filler LHS points."""
    k = quad_model["k"]
    names = [f"x{i}" for i in range(k)]
    axes = [np.linspace(-1.0, 1.0, grid_n)] * k
    grid_pts = np.array(list(itertools.product(*axes))) if k <= 4 else None
    if grid_pts is None:
        from .gp import lhs_uniform
        grid_pts = 2.0 * lhs_uniform(200, k, seed) - 1.0

    def D_of(coded_matrix):
        # single-metric desirability of the modeled primary response
        preds = quad_model["predict"](coded_matrix)
        metrics = list(specs)
        draws = np.column_stack([preds] * len(metrics))
        return d_vectorized(draws, metrics, specs,
                            {m: (specs[m].get("_grid_lo"), specs[m].get("_grid_hi"))
                             for m in metrics})

    d_vals = D_of(grid_pts)
    top = grid_pts[np.argsort(-d_vals)[:8]]
    center = top[0].tolist()
    infos = [{"col": f"x{i}", "mean": 0.0, "half_range": 1.0, "type": "numeric",
              "zero_variance": False, "is_block": False, "is_covariate": False}
             for i in range(k)]
    # refine on the modeled primary response under the primary metric's spec
    primary = next(iter(specs))
    primary_spec = {primary: {kk: vv for kk, vv in specs[primary].items()
                              if not kk.startswith("_")}}
    primary_grid = {primary: (specs[primary].get("_grid_lo"),
                              specs[primary].get("_grid_hi"))}

    def _predict_raw(raw):
        coded = np.array([[ (raw[f"x{i}"] - infos[i]["mean"]) / infos[i]["half_range"]
                            for i in range(k)]])
        return float(quad_model["predict"](coded)[0])

    best = refine_optimum({primary: _predict_raw}, primary_spec, infos,
                          [f"x{i}" for i in range(k)], {}, primary_grid)
    pts = [dict(zip(names, best["coded"])), dict(zip(names, center))]
    from .gp import lhs_uniform
    fill = 2.0 * lhs_uniform(max(batch - 2, 0), k, seed + 1) - 1.0
    for row in fill:
        pts.append(dict(zip(names, row.tolist())))
    return pts[:max(batch, 1)]
