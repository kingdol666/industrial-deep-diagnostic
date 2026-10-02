"""acquisition.py — candidate generation + greedy batch selection (deterministic).

Support / extrapolation flag (O-G3, pinned neighborhood_coded = 0.8):
a candidate is `extrapolation=true` when its coded distance to the nearest
observed point exceeds 0.8 OR it touches the domain boundary.
Duplication guard (delta_confirm_coded = 0.05): a selected candidate closer
than 0.05 (coded) to an existing point or an already-picked batch member is
skipped; duplication_ratio counts batch members that violate it anyway.
"""

import numpy as np

from . import (DELTA_CONFIRM, DUPLICATE_EPS_CODED, MC_SAMPLES, MC_SEED,
               NEIGHBORHOOD, objective as obj_mod)
from .gp import ei_closed_form, lhs_uniform, mc_ei_desirability
from .rsm_model import d_vectorized, split_grid


def numeric_names(domain_numeric):
    """Numeric factor names in canonical order; coded coords are x0..x{k-1}."""
    return list(domain_numeric)


def code_point(raw, domain_numeric):
    """raw setpoints (real factor names) -> coded dict with x0..x{k-1} keys."""
    out = {}
    for i, f in enumerate(numeric_names(domain_numeric)):
        spec = domain_numeric[f]
        out[f"x{i}"] = 2.0 * (float(raw[f]) - spec["lo"]) / (spec["hi"] - spec["lo"]) - 1.0
    return out


def decode_point(coded, domain_numeric):
    """coded x0..x{k-1} -> raw setpoints with real factor names."""
    out = {}
    for i, f in enumerate(numeric_names(domain_numeric)):
        spec = domain_numeric[f]
        out[f] = spec["lo"] + (float(coded[f"x{i}"]) + 1.0) / 2.0 * (spec["hi"] - spec["lo"])
    return out


def coded_to_matrix(coded_points):
    """List of coded dicts -> (n, k) matrix in x0..x{k-1} order."""
    if not coded_points:
        return np.zeros((0, 0))
    k = max(len(c) for c in coded_points)
    return np.atleast_2d(np.asarray(
        [[float(c[f"x{i}"]) for i in range(k)] for c in coded_points], dtype=float))


def nearest_distance(coded_point, coded_matrix):
    if coded_matrix.size == 0 or coded_matrix.shape[0] == 0:
        return float("inf")
    d = np.sqrt(np.sum((coded_matrix - np.asarray(
        [coded_point[f"x{i}"] for i in range(coded_matrix.shape[1])])) ** 2,
        axis=1))
    return float(np.min(d))


def is_boundary(coded_point):
    return any(abs(float(v)) >= 1.0 - 1e-9 for v in coded_point.values())


def make_candidates(domain_numeric, n_cand=256, seed=42, extra_coded=None):
    """LHS candidate set in the coded box + pinned extra anchors (seeds,
    incumbent). Deterministic. Keys are x0..x{k-1}."""
    k = len(domain_numeric)
    u = lhs_uniform(n_cand, k, seed)
    cands = [dict(zip((f"x{i}" for i in range(k)), (2.0 * row - 1.0).tolist()))
             for row in u]
    for e in extra_coded or []:
        cands.append({f"x{i}": float(np.clip(e[f"x{i}"], -1.0, 1.0))
                      for i in range(k)})
    return cands


def gp_fits_for_metrics(coded_matrix, per_metric, replicate_vars=None):
    """Fit one GPFit per metric. per_metric: {metric: y_raw_vector}.
    Returns ({metric: GPFit}, failures dict)."""
    from .gp import GPFit, GPDegenerateError
    fits, failures = {}, {}
    for metric, y in per_metric.items():
        try:
            rv = (replicate_vars or {}).get(metric)
            fits[metric] = GPFit(coded_matrix, np.asarray(y, dtype=float),
                                 replicate_var=rv).fit()
        except GPDegenerateError as exc:
            failures[metric] = str(exc)
        except Exception as exc:  # numeric degeneracy -> honest failure
            failures[metric] = f"{type(exc).__name__}: {exc}"
    return fits, failures


def _d_eval_fn(specs, metrics):
    clean, grid = split_grid(specs)

    def d_eval(draws):
        return d_vectorized(draws, metrics, clean, grid)
    return d_eval


def observed_D(raw_means_by_point, specs):
    """D per observed point via doe-analyzer combined_desirability (scalar path).
    raw_means_by_point: iterable of {metric: mean}."""
    from .rsm_model import combined_desirability, split_grid
    clean, grid = split_grid(specs)
    out = []
    for means in raw_means_by_point:
        d, _ = combined_desirability(dict(means), clean, grid)
        out.append(float(d))
    return out


def _best_observed_D(fits, specs):
    """D of the best observed point — evaluated through the desirability
    itself (for goal=target the best point is the band CENTER, so max(y) is
    wrong). Uses the shared fitted X; per-metric row subsets must align (v1:
    metrics are measured together), else falls back to max-mean per metric."""
    from .rsm_model import d_vectorized, split_grid
    ref = next(iter(fits.values()))
    lens = {f.y_raw.shape[0] for f in fits.values()}
    clean, grid = split_grid(specs)
    if len(lens) == 1:
        draws = np.column_stack([fits[m].y_raw for m in fits])
        ds = d_vectorized(draws, list(fits), clean, grid)
        return float(np.max(ds))
    best_point = {m: float(np.max(fits[m].y_raw)) for m in fits}
    from .rsm_model import combined_desirability
    d, _ = combined_desirability(best_point, clean, grid)
    return float(d)


def _ranking_scores(fits, specs, X_cand, y_best_d):
    """Candidate ranking scores. Single metric with goal in {minimize,
    maximize} -> exact closed-form EI on the response scale (identical
    ordering to D-scale EI because D is a monotone linear rescale there).
    Otherwise -> desirability-MC-EI (seed=42, 1024 LHS). X_cand: (n, k)."""
    if _single_linear(fits, specs):
        fit = fits[next(iter(fits))]
        mu, sd = fit.predict(X_cand)
        goal = specs[next(iter(fits))]["goal"]
        signed = mu if goal == "maximize" else -mu
        return ei_closed_form(signed, sd, float(np.max(fit.y))), "closed_form"
    d_eval = _d_eval_fn(specs, list(fits))
    ei, _ = mc_ei_desirability(fits, X_cand, d_eval, y_best_d,
                               seed=MC_SEED, n_samples=MC_SAMPLES)
    return ei, "mc_desirability"


def _single_linear(fits, specs):
    """True when the campaign is a single metric with goal in {minimize,
    maximize} and no target anchor — its desirability is a monotone linear
    rescale of y, so exact closed-form EI on the response scale is the
    ranking/EI criterion (the eps threshold anchors to the observed y span)."""
    return (len(fits) == 1
            and specs[next(iter(fits))].get("goal") in ("minimize", "maximize")
            and specs[next(iter(fits))].get("target") is None)


def evaluate_ei(fits, specs, cands_coded, d_span=None):
    """EI over candidates (the eps-gated quantity) + its reference span.

    Single metric minimize/maximize -> closed-form EI on the response scale;
    the reference span is the observed y span (D is grid-relative there and
    degenerate as an improvement scale). Otherwise -> desirability-MC-EI on
    the D scale; the reference span is the observed D span.
    Returns (ei array, path, ref_span).
    """
    if _single_linear(fits, specs):
        fit = fits[next(iter(fits))]
        X = coded_to_matrix(cands_coded)
        mu, sd = fit.predict(X)
        goal = specs[next(iter(fits))]["goal"]
        signed = mu if goal == "maximize" else -mu
        ei = ei_closed_form(signed, sd, float(np.max(fit.y)))
        span = float(np.max(fit.y_raw) - np.min(fit.y_raw)) or 1.0
        return ei, "closed_form", span
    d_eval = _d_eval_fn(specs, list(fits))
    y_best_d = _best_observed_D(fits, specs)
    X = coded_to_matrix(cands_coded)
    ei, _ = mc_ei_desirability(fits, X, d_eval, y_best_d,
                               seed=MC_SEED, n_samples=MC_SAMPLES)
    return ei, "mc_desirability", d_span


def greedy_batch(fits, specs, cands_coded, existing_coded, batch, d_span,
                 domain_numeric, seed=42):
    """Greedy q-EI: rank by closed-form EI (single linear metric) or MC-EI(D);
    pick argmax, mask within DELTA_CONFIRM coded of the pick, repeat.
    Returns list of {coded, ei (MC-EI on D), ranking path, predicted (per
    metric), predicted_D, distance_to_nearest_data, extrapolation, duplicate}."""
    d_eval = _d_eval_fn(specs, list(fits))
    from .rsm_model import combined_desirability, split_grid
    clean, grid = split_grid(specs)
    y_best_d = _best_observed_D(fits, specs)
    X_all = coded_to_matrix(cands_coded)
    scores, rank_path = _ranking_scores(fits, specs, X_all, y_best_d)
    ei_all, _ = mc_ei_desirability(fits, X_all, d_eval, y_best_d,
                                   seed=MC_SEED, n_samples=MC_SAMPLES)
    masked = np.array(scores, dtype=float)
    # mask out the duplication radius of already-observed points (deterministic)
    if existing_coded:
        ex = coded_to_matrix(existing_coded)
        if ex.size:
            d0 = np.sqrt(((X_all[:, None, :] - ex[None, :, :]) ** 2)
                         .sum(-1)).min(axis=1)
            masked[d0 < DELTA_CONFIRM] = -np.inf
    picked = []
    k = X_all.shape[1]
    existing = list(existing_coded) if existing_coded is not None else []
    for _ in range(batch):
        if masked.size == 0 or not np.isfinite(masked).any() \
                or float(np.max(masked)) <= -np.inf:
            break
        idx = int(np.argmax(masked))
        coded = {f"x{i}": float(X_all[idx, i]) for i in range(k)}
        d_near = nearest_distance(coded, coded_to_matrix(existing)) if existing \
            else float("inf")
        dup = d_near < DELTA_CONFIRM - DUPLICATE_EPS_CODED
        pred_raw, pred_sd = {}, {}
        for m, fit in fits.items():
            mu, sd = fit.predict_raw(np.array([[coded[f"x{i}"] for i in
                                                range(fit.k)]]))
            pred_raw[m] = float(mu[0])
            pred_sd[m] = float(sd[0])
        pD, _ = combined_desirability(pred_raw, clean, grid)
        picked.append({
            "coded": coded,
            "ei": float(ei_all[idx]),
            "ranking_score": float(scores[idx]),
            "ranking_path": rank_path,
            "predicted": pred_raw,
            "predicted_sd": pred_sd,
            "predicted_D": float(pD),
            "distance_to_nearest_data": None if d_near == float("inf") else d_near,
            "extrapolation": (d_near > NEIGHBORHOOD) or is_boundary(coded),
            "duplicate": dup,
        })
        existing = existing + [coded]
        dm = np.sqrt(np.sum((X_all - X_all[idx][None, :]) ** 2, axis=1))
        masked[dm < DELTA_CONFIRM] = -np.inf
        masked[idx] = -np.inf
    return picked


def domain_coverage(existing_coded, domain_numeric, n_grid=5):
    """Fraction of a coarse domain grid with a data point within
    NEIGHBORHOOD (0.8 coded) — belief.domain_coverage."""
    k = len(domain_numeric)
    if k > 4 or not existing_coded:
        return None
    import itertools
    axes = [np.linspace(-1.0, 1.0, n_grid)] * k
    cells = np.array(list(itertools.product(*axes)))
    data = coded_to_matrix(existing_coded)
    d = np.sqrt(((cells[:, None, :] - data[None, :, :]) ** 2).sum(-1)).min(axis=1)
    return float(np.mean(d <= NEIGHBORHOOD))
