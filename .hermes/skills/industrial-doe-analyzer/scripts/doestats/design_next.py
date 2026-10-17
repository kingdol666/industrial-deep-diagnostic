"""Next-round design proposal (Phase 3 / P3-3, contract §8.2 / DS-11 / T-NEXT-01).

`propose(profile, effect_table, model, recs, ctx, *, seed=None) -> dict`

Rules (first match = primary; every applicable rule is emitted in `actions[]`):

1. `resolution <= 4` **and** an alias chain exists        -> `fold_over`
2. linear model lacking curvature evidence chain + a
   design without axial star points                      -> `augment_star`
3. curvature evidence present but the design has no
   axial star points                                     -> `augment_axial`
4. non-randomized run order (data_profile randomization
   check / NON_RANDOMIZED caveat / explicit flag)        -> `confirm_replicate`
5. observational mode, or every window extrapolated,
   or an unbounded / low-confidence design hull           -> `space_filling`
(no rule matches -> a single `none` action: the current design is adequate)

Every action carries executable `settings`, `n_runs`, `block_policy`,
`replicate_policy`, `expected_information` and `constraints_ok`. Every proposed
setpoint is checked against ALL hard constraints of `ctx.constraints` (a
constraint without a `hard` key is treated as hard — never propose outside a
declared limit): a violation sets `constraints_ok=false` AND moves the action to
`skipped_actions[]` instead of `actions[]` (skipped, never silently dropped).

Out-of-scope by design: this module only *designs* runs. It never dispatches a
parameter, never claims causality and never edits the measurement system.
"""

import argparse
import datetime
import json
from pathlib import Path

import numpy as np

if __package__ in (None, ""):                 # `python <this file>` (CLI invocation)
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "doestats"                  # enables the relative imports below

from . import design_build as db

CONTRACT_VERSION = "1.0"

ACTIONS = ("fold_over", "augment_star", "augment_axial", "space_filling",
           "confirm_replicate", "none")

# Designs whose coded structure has no axial star points (curvature cannot be
# estimated from them alone).
NO_AXIAL_DESIGNS = {"full_factorial", "fractional_factorial", "orthogonal_array"}

DEFAULT_CONFIRM_RUNS = 3          # optimizer-loop requires m >= 3 confirm replicates
DEFAULT_STAR_CENTER = 3
DEFAULT_SPACE_FILL_RUNS = 8


# ------------------------------------------------------------------ helpers

def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _design(profile):
    return (profile or {}).get("design") or {}


def _alias_chains(profile, effect_table):
    """Alias chains from the design block or from the effect table's dropped terms."""
    chains = dict(_design(profile).get("alias_chains") or {})
    spec = (effect_table or {}).get("model_spec") or {}
    for term, info in (spec.get("term_status") or {}).items():
        if not isinstance(info, dict):
            continue
        chain = info.get("alias_chain") or []
        if chain:
            chains.setdefault(term, [str(c) for c in chain])
    return chains


def _curvature(effect_table, model, alpha=0.05):
    """(has_curvature_evidence, has_quadratic_terms, evidence) from table + model."""
    evidence, quad_terms, sig = [], [], []
    spec = (effect_table or {}).get("model_spec") or {}
    quad_terms = [str(t) for t in spec.get("quadratic") or []]
    for fam in (effect_table or {}).get("families") or []:
        for t in fam.get("tests") or []:
            name = str(t.get("term") or "")
            if name not in quad_terms and "^2" not in name:
                continue
            p = t.get("q_value_bh") if t.get("q_value_bh") is not None else t.get("p_value")
            if t.get("estimable") and p is not None and float(p) < alpha:
                sig.append({"response": fam.get("response"), "term": name,
                            "p": float(p), "source": "effect_table"})
    models = model if isinstance(model, list) else ([model] if isinstance(model, dict) else [])
    for m in models:
        coefs = (m or {}).get("coded_coefficients") or {}
        if any("^2" in str(k) for k in coefs):
            if not quad_terms:
                quad_terms = [str(k) for k in coefs if "^2" in str(k)]
        lof = (m or {}).get("lack_of_fit") or {}
        ct = lof.get("curvature_test") or {}
        p = ct.get("p_value") if isinstance(ct, dict) else None
        if p is not None and float(p) < alpha:
            sig.append({"response": m.get("response"), "term": "curvature_test",
                        "p": float(p), "source": "model.lack_of_fit.curvature_test"})
    evidence.extend(sig)
    return bool(sig), bool(quad_terms), evidence


def _randomization_state(profile, ctx):
    """(randomized|None, evidence) — None means "no randomization information".

    Sources, in order: explicit randomization block, design/quality block,
    NON_RANDOMIZED caveat, explicit context flag. Missing information is never
    read as "non-randomized" (that would force a confirm round on no evidence).
    """
    for src, block in (("profile.randomization", (profile or {}).get("randomization")),
                       ("profile.design.randomization", _design(profile).get("randomization")),
                       ("profile.quality.randomization",
                        ((profile or {}).get("quality") or {}).get("randomization")),
                       ("ctx.randomization", (ctx or {}).get("randomization"))):
        if isinstance(block, bool):
            return (not block), f"{src}={block}"
        if isinstance(block, dict) and "randomized" in block:
            return (not bool(block["randomized"])), f"{src}.randomized={block['randomized']}"
    for cav in (profile or {}).get("caveats") or []:
        if str(cav.get("code") or "").upper() in ("NON_RANDOMIZED", "NOT_RANDOMIZED"):
            ev = cav.get("evidence")
            rho = ev.get("spearman_rho") if isinstance(ev, dict) else None
            return True, (f"profile.caveats[{cav.get('code')}]"
                          + (f" (spearman_rho={rho})" if rho is not None else ""))
    for key in ("non_randomized", "run_order_sorted"):
        if (ctx or {}).get(key) is True:
            return True, f"ctx.{key}=true"
    run_order = (ctx or {}).get("run_order_col")
    if (ctx or {}).get("randomization") is None and run_order is None:
        return None, "no run_order column and no randomization declaration"
    return None, "randomization not declared"


def _bounds(ctx, recs, profile):
    """{factor: (low, high)} from design_region -> ctx factors -> observed ranges."""
    out, source = {}, {}
    region = (ctx or {}).get("design_region") or {}
    for f, rng in (region.get("factorial_bounds") or {}).items():
        try:
            out[str(f)] = (float(rng[0]), float(rng[1]))
            source[str(f)] = "ctx.design_region.factorial_bounds"
        except (TypeError, ValueError, IndexError):
            continue
    for f in (ctx or {}).get("factors") or []:
        col = f.get("col") or f.get("name")
        if not col or col in out or f.get("type") == "categorical":
            continue
        lo = f.get("low", f.get("min"))
        hi = f.get("high", f.get("max"))
        if lo is None or hi is None:
            continue
        try:
            out[str(col)] = (float(lo), float(hi))
            source[str(col)] = "ctx.factors[].low/high"
        except (TypeError, ValueError):
            continue
    for f, rng in ((recs or {}).get("applicability_domain") or {}).get(
            "factor_observed_ranges", {}).items():
        if f in out:
            continue
        try:
            out[str(f)] = (float(rng.get("min")), float(rng.get("max")))
            source[str(f)] = "recs.applicability_domain.factor_observed_ranges"
        except (TypeError, ValueError, AttributeError):
            continue
    return out, source


def _hard_constraints(ctx):
    """{factor: (lo, hi, item)} — `hard` missing counts as hard (conservative)."""
    out = {}
    for c in (ctx or {}).get("constraints") or []:
        if not isinstance(c, dict) or not c.get("factor"):
            continue
        if c.get("hard") is False:
            continue
        f = str(c["factor"])
        lo = c.get("min")
        hi = c.get("max")
        try:
            lo = None if lo is None else float(lo)
            hi = None if hi is None else float(hi)
        except (TypeError, ValueError):
            continue
        out[f] = (lo, hi, c)
    return out


def _effective_bounds(bounds, hard):
    """Region ∩ hard constraints -> ({f: (lo, hi)}, infeasible_factors, notes).

    Everything proposed by this module is constructed on the clipped region, so
    a hard limit can never be crossed by construction; a factor whose
    intersection is empty makes the design unbuildable and the action is skipped
    (never silently narrowed to a degenerate point).
    """
    eff, infeasible, notes = {}, [], []
    for f, (lo, hi) in sorted(bounds.items()):
        lim = hard.get(f)
        if lim is None:
            eff[f] = (lo, hi)
            continue
        lmin, lmax, _ = lim
        nlo = lo if lmin is None else max(lo, lmin)
        nhi = hi if lmax is None else min(hi, lmax)
        if nlo > nhi:
            infeasible.append(f)
            continue
        if nlo != lo or nhi != hi:
            notes.append(f"{f}: 设计域 {lo}..{hi} 按硬约束裁剪为 {nlo}..{nhi}")
        eff[f] = (nlo, nhi)
    return eff, infeasible, notes


def _violations(points, hard):
    """[(factor, value, kind, limit)] for every hard-constraint violation."""
    bad = []
    for p in points:
        for f, v in p.items():
            if f not in hard:
                continue
            lo, hi, _ = hard[f]
            if v is None:
                continue
            try:
                vv = float(v)
            except (TypeError, ValueError):
                continue
            if lo is not None and vv < lo - 1e-9:
                bad.append({"factor": f, "value": vv, "violation": "below_min", "min": lo})
            if hi is not None and vv > hi + 1e-9:
                bad.append({"factor": f, "value": vv, "violation": "above_max", "max": hi})
    return bad


def _pack_constrained(action, points, hard, soft_notes):
    """Attach the constraint verdict; return (action, None) or (None, skipped_record)."""
    bad = _violations(points, hard)
    action["constraints_ok"] = not bad
    action["constraint_violations"] = bad
    if bad:
        rec = dict(action)
        rec["skipped_reason"] = "hard_constraint_violation"
        rec["source_evidence"] = list(action.get("source_evidence") or [])
        return None, rec
    if soft_notes:
        action["soft_constraint_notes"] = soft_notes
    return action, None


def _incumbent(recs, bounds):
    """The best concrete point available for a confirm round (first that exists)."""
    for sp in (recs or {}).get("joint_setpoints") or []:
        if sp.get("actionable") and isinstance(sp.get("factors"), dict):
            return dict(sp["factors"]), "recs.joint_setpoints[actionable].factors"
    for sp in (recs or {}).get("setpoints") or []:
        if sp.get("factor") == "MULTI":
            raw = ((sp.get("expected_response") or {}).get("raw")) or {}
            if raw:
                return dict(raw), "recs.setpoints[MULTI].expected_response.raw"
    base = ((recs or {}).get("current_baseline") or {}).get("point") or {}
    if any(v is not None for v in base.values()):
        return dict(base), "recs.current_baseline.point"
    if bounds:
        return {f: (lo + hi) / 2.0 for f, (lo, hi) in sorted(bounds.items())}, \
            "design-region centre (no incumbent available)"
    return {}, "no incumbent and no design region"


def _safe_power(t_a, df, ncp):
    """Noncentral-t power with a normal-approximation guard (never NaN in JSON)."""
    from scipy import stats as sps
    try:
        v = float(sps.nct.sf(t_a, df, ncp) + sps.nct.cdf(-t_a, df, ncp))
    except (ValueError, OverflowError, RuntimeError):
        v = float("nan")
    if not np.isfinite(v):
        v = float(sps.norm.sf(t_a - ncp))
    return round(v, 6)


def _power_at_2mde(effect_table, model, n_target, sigma_default=1.0):
    """Approximate power at 2xMDE for an orthogonal design with n_target runs."""
    from scipy import stats as sps
    mde, df0, sigma = None, None, sigma_default
    for fam in (effect_table or {}).get("families") or []:
        if fam.get("mde") is not None:
            mde = float(fam["mde"])
            df0 = fam.get("df_resid")
            s = fam.get("sigma_pure_error")
            if s is None and fam.get("mse"):
                s = float(fam["mse"]) ** 0.5
            if s:
                sigma = float(s)
            break
    if mde is None or not n_target or n_target < 4:
        return None, "no effect_table mde (power not estimable)"
    df = max(int(n_target) - 2, 1)
    t_a = float(sps.t.ppf(0.975, df))
    ncp = mde * np.sqrt(n_target) / max(sigma, 1e-12)
    p = _safe_power(t_a, df, ncp)
    return p, (f"orthogonal-design approximation: ncp = mde*sqrt(n)/sigma with "
               f"mde={round(mde, 4)} (from effect_table, df_resid={df0}), "
               f"sigma={round(sigma, 4)}, n={int(n_target)}")


# ------------------------------------------------------------------ rules

def _act_fold_over(profile, effect_table, ctx, bounds, chains, ev, eff_bounds, clip_notes):
    design = _design(profile)
    n_base = design.get("n_distinct_combos") or design.get("n_runs")
    n_runs = int(n_base) if n_base else None
    settings = [{"factor": f, "low": lo, "high": hi}
                for f, (lo, hi) in sorted(eff_bounds.items())]
    points = []
    for f, (lo, hi) in sorted(eff_bounds.items()):
        points.extend([{f: lo}, {f: hi}])
    broken = []
    for key, aliases in sorted(chains.items()):
        if aliases:
            broken.append(f"{key} → {sorted(aliases)}")
    info = {
        "alias_break": broken,
        "alias_break_note": ("镜像折叠点：折叠后(resolution 提升)原 alias 链的两端可分离"
                             f"（链数 {len(broken)}）"),
        "region_clipping": clip_notes,
        "note": ("镜像组合沿用父代的因子水平（不引入新水平）；设定范围已按硬约束裁剪，"
                 "父代表仍需通过硬约束校验"),
    }
    act = {
        "id": "ND-01",
        "action": "fold_over",
        "settings": settings,
        "n_runs": n_runs,
        "block_policy": "new_block_per_fold_half" if n_runs else "same_block_as_parent",
        "replicate_policy": "none (fold-over adds mirrored combinations, not replicates)",
        "expected_information": info,
        "source_evidence": ev + [
            f"profile.design.resolution={design.get('resolution')} (<=4)",
            f"alias_chains: {sorted(chains)[:5]}",
        ],
        "design_points": "mirror (sign-flipped) combinations of the parent run set; "
                         "concrete values follow the parent run table",
    }
    return act, points


def _act_augment_star(profile, effect_table, model, ctx, bounds, ev, eff_bounds,
                      clip_notes, axial_only=False):
    k = len(eff_bounds)
    if k == 0:
        return None, None, [], "no numeric factor bounds — star points not constructible"
    n_center = int((ctx or {}).get("n_center") or DEFAULT_STAR_CENTER)
    alpha_req = float((ctx or {}).get("axial_alpha") or ((ctx or {}).get("design_region") or {})
                      .get("axial_alpha") or (2 ** k) ** 0.25)
    centre, recentred = {}, False
    for f, (lo, hi) in sorted(eff_bounds.items()):
        c = (bounds[f][0] + bounds[f][1]) / 2.0
        if c < lo - 1e-12 or c > hi + 1e-12:
            recentred = True
            c = (lo + hi) / 2.0
        centre[f] = c
    alpha_used = alpha_req
    for f, (lo, hi) in sorted(eff_bounds.items()):
        half = (bounds[f][1] - bounds[f][0]) / 2.0
        if half <= 0:
            continue
        room = min((hi - centre[f]) / half, (centre[f] - lo) / half)
        alpha_used = min(alpha_used, max(room, 0.0))
    if alpha_used <= 0:
        return None, None, [], "hard constraints leave no axial headroom at the centre"
    star = {f: [centre[f] - alpha_used * (bounds[f][1] - bounds[f][0]) / 2.0,
                centre[f] + alpha_used * (bounds[f][1] - bounds[f][0]) / 2.0]
            for f in sorted(eff_bounds)}
    points = []
    for f in sorted(star):
        for v in star[f]:
            pt = dict(centre)
            pt[f] = v
            points.append(pt)
    points.extend([dict(centre)] * n_center)
    settings = [{"factor": f, "value": centre[f]} for f in sorted(eff_bounds)]
    settings += [{"factor": f, "low": star[f][0], "high": star[f][1]} for f in sorted(star)]
    n_new = 2 * k + n_center
    n_old = (_design(profile).get("n_runs") or 0)
    power, power_note = _power_at_2mde(effect_table, model, int(n_old) + n_new)
    curv_list = [f"{e.get('response')}/{e.get('term')}" for e in _curvature(effect_table,
                                                                           model)[2]]
    act = {
        "id": "ND-02",
        "action": "augment_axial" if axial_only else "augment_star",
        "settings": settings,
        "star_values": star,
        "n_runs": n_new,
        "block_policy": "new_block_for_augmentation",
        "replicate_policy": (f"{n_center} centre replicates (pure-error df gain)"),
        "expected_information": {
            "power_at_2mde": power,
            "power_at_2mde_note": power_note,
            "d_efficiency": None,
            "d_efficiency_note": ("augmented-design D-efficiency needs the parent coded "
                                 "run table (not an artifact input) — rerun design_build "
                                 "on the merged table to obtain it"),
            "coverage_gain": {"value": round(min(1.0, n_new / max(n_old, 1)), 4)
                              if n_old else None,
                              "note": "augmentation runs / parent runs (design-support gain)"},
            "star_geometry": (f"2k={2 * k} axial points at ±alpha plus {n_center} centre "
                              f"points (k={k})"),
            "alpha_requested": round(alpha_req, 6),
            "alpha_used": round(alpha_used, 6),
            "alpha_limited_by": ("hard constraints" if alpha_used < alpha_req - 1e-12
                                 else "none"),
            "recentred_to_feasible_region": recentred,
            "region_clipping": clip_notes,
        },
        "source_evidence": ev + [
            f"curvature evidence: {curv_list or 'none'}",
            f"alpha_requested={round(alpha_req, 6)} alpha_used={round(alpha_used, 6)}, "
            f"n_center={n_center}",
        ],
    }
    return act, points, [], None


def _act_confirm(recs, profile, bounds, ev, n_runs=DEFAULT_CONFIRM_RUNS):
    point, source = _incumbent(recs, bounds)
    if not point:
        return None, [], "no incumbent setpoint to confirm"
    settings = [{"factor": f, "value": v} for f, v in sorted(point.items())]
    act = {
        "id": "ND-03",
        "action": "confirm_replicate",
        "settings": settings,
        "n_runs": int(n_runs),
        "block_policy": "same_block_as_parent (order randomized within the round)",
        "replicate_policy": (f"{int(n_runs)} independent replicates at the incumbent point "
                             f"(replicate_kind=replicate; pure-error df={int(n_runs) - 1})"),
        "expected_information": {
            "coverage_gain": None,
            "power_at_2mde": None,
            "alias_break": None,
            "note": ("独立重复 → 纯误差 df = m-1，用于验证未随机化的效应是否可复现"
                     f"（m={int(n_runs)}；optimizer-loop 要求 m>=3）"),
        },
        "source_evidence": ev + [f"incumbent source: {source}"],
        "design_points": [dict(point) for _ in range(int(n_runs))],
    }
    return act, [dict(point)] * int(n_runs), None


def _act_space_filling(ctx, recs, bounds, profile, ev, seed, eff_bounds, clip_notes):
    k = len(eff_bounds)
    if k < 2:
        return None, [], (f"space-filling needs >= 2 numeric factors (have {k}); "
                          "not constructible")
    n = int((ctx or {}).get("space_filling_runs") or max(DEFAULT_SPACE_FILL_RUNS, 2 * k))
    factors = [{"name": f, "type": "numeric", "low": lo, "high": hi}
               for f, (lo, hi) in sorted(eff_bounds.items())]
    built = db.build_design({"design_type": "latin_hypercube", "factors": factors,
                             "runs": n}, seed=seed)
    points = [{f: rec[f] for f in sorted(eff_bounds)} for rec in built["run_table"]]
    md = built["properties"].get("min_distance")
    act = {
        "id": "ND-04",
        "action": "space_filling",
        "settings": [{"factor": f, "low": lo, "high": hi}
                     for f, (lo, hi) in sorted(eff_bounds.items())],
        "n_runs": int(built["properties"]["n_runs"]),
        "block_policy": "single_block (randomized run order)" if built["randomization"]["randomized"]
                        else "single_block (natural order; pass seed to randomize)",
        "replicate_policy": "none (space-filling exploration; centre repeats optional)",
        "expected_information": {
            "coverage_gain": {
                "value": md,
                "note": ("normalized minimum pairwise distance of the emitted LHS points "
                         "(0..1; larger = better region coverage)"),
            },
            "d_efficiency": built["properties"]["d_efficiency"]["value"],
            "d_efficiency_note": "D-efficiency of the space-filling design for its linear model",
            "power_at_2mde": None,
            "alias_break": None,
            "region_clipping": clip_notes,
        },
        "source_evidence": ev + [
            f"design_type={_design(profile).get('design_type')}",
            f"lhs n={int(built['properties']['n_runs'])}, min_distance={md}",
        ],
        "design_points": points,
    }
    return act, points, None


# ------------------------------------------------------------------ entry

def propose(profile, effect_table, model, recs, ctx, *, seed=None):
    """Propose the next design (contract §8.2). Deterministic; `seed` drives the LHS."""
    profile = profile or {}
    ctx = ctx or {}
    recs = recs or {}
    design = _design(profile)
    alpha = float(ctx.get("alpha") or 0.05)
    bounds, bound_sources = _bounds(ctx, recs, profile)
    hard = _hard_constraints(ctx)
    soft_notes = [f"{f}: {c.get('min')}..{c.get('max')} (soft)"
                  for f, c in ((c.get("factor"), c) for c in (ctx.get("constraints") or []))
                  if isinstance(c, dict) and c.get("hard") is False and c.get("factor")]

    chains = _alias_chains(profile, effect_table)
    has_curvature, has_quad, curvature_evidence = _curvature(effect_table, model, alpha)
    non_randomized, rand_evidence = _randomization_state(profile, ctx)
    dtype = design.get("design_type")
    mode = design.get("mode")
    no_axial = dtype in NO_AXIAL_DESIGNS
    hull = ((recs.get("design_region") or {}).get("hull")
            or (ctx.get("design_region") or {}).get("hull"))
    windows = recs.get("operating_windows") or []
    all_extrapolated = bool(windows) and all(w.get("extrapolation") is True for w in windows)
    low_hull = bool(hull in ("unbounded",) or
                    (recs.get("design_region") or {}).get("design_hull_confidence") == "low")

    candidates, skipped, fired = [], [], []
    eff_bounds, infeasible, clip_notes = _effective_bounds(bounds, hard)
    if infeasible:
        # nothing can be constructed on an empty (region ∩ hard constraint) for these
        for f in infeasible:
            skipped.append({"action": "all_rules", "skipped_reason":
                            f"hard constraints leave an empty design region for factor {f}",
                            "constraints_ok": False, "factor": f})
    if design.get("resolution") is not None and int(design["resolution"]) <= 4 and chains:
        if infeasible:
            skipped.append({"action": "fold_over", "constraints_ok": False,
                            "skipped_reason": "empty region ∩ hard constraints",
                            "source_evidence": [f"infeasible factor(s): {infeasible}"]})
        else:
            act, points = _act_fold_over(profile, effect_table, ctx, bounds, chains,
                                        [f"profile.design.resolution={design.get('resolution')}"],
                                        eff_bounds, clip_notes)
            candidates.append((act, points, "alias_chain+resolution<=4"))
    if no_axial and not has_curvature:
        act, points, _unused, why = _act_augment_star(
            profile, effect_table, model, ctx, bounds,
            ["no quadratic term is significant (curvature evidence absent)",
             f"design_type={dtype} has no axial star points"], eff_bounds, clip_notes)
        if act is None:
            skipped.append({"action": "augment_star", "skipped_reason": why,
                            "constraints_ok": None})
        else:
            candidates.append((act, points, "linear_model_no_curvature"))
    elif no_axial and has_curvature:
        act, points, _unused, why = _act_augment_star(
            profile, effect_table, model, ctx, bounds,
            [f"curvature evidence present: {len(curvature_evidence)} significant quadratic "
             f"test(s)",
             f"design_type={dtype} has no axial star points (axial_only=True)"],
            eff_bounds, clip_notes, axial_only=True)
        if act is None:
            skipped.append({"action": "augment_axial", "skipped_reason": why,
                            "constraints_ok": None})
        else:
            candidates.append((act, points, "curvature_without_axial_points"))
    if non_randomized:
        act, points, why = _act_confirm(recs, profile, bounds,
                                       [f"non-randomized: {rand_evidence}"])
        if act is None:
            skipped.append({"action": "confirm_replicate", "skipped_reason": why,
                            "constraints_ok": None})
        else:
            candidates.append((act, points, "non_randomized_run_order"))
    if mode == "observational" or dtype == "observational" or all_extrapolated or low_hull:
        why = []
        if mode == "observational" or dtype == "observational":
            why.append("analysis mode is observational (no designed structure)")
        if all_extrapolated:
            why.append("every operating window is flagged extrapolation=true")
        if low_hull:
            why.append(f"design hull={hull or 'unbounded'} (low confidence)")
        act, points, why_none = _act_space_filling(ctx, recs, bounds, profile, why, seed,
                                                  eff_bounds, clip_notes)
        if act is None:
            skipped.append({"action": "space_filling", "skipped_reason": why_none,
                            "constraints_ok": None})
        else:
            candidates.append((act, points, "extrapolation_or_observational"))

    for act, points, _reason in candidates:
        packed, skip = _pack_constrained(act, points, hard, soft_notes)
        if packed is None:
            skipped.append(skip)
        else:
            fired.append(packed)

    if not fired:
        act = {
            "id": "ND-00",
            "action": "none",
            "settings": [],
            "n_runs": 0,
            "block_policy": "n/a",
            "replicate_policy": "n/a",
            "expected_information": {"note": "no confirmation / augmentation rule fired"},
            "constraints_ok": True,
            "constraint_violations": [],
            "source_evidence": [
                f"resolution={design.get('resolution')}",
                f"alias_chains={len(chains)}",
                f"curvature_evidence={has_curvature}",
                f"non_randomized={non_randomized}",
                "mode=" + str(mode or dtype),
            ],
        }
        fired = [act]

    for i, act in enumerate(fired, start=1):
        act["id"] = f"ND-{i:02d}"
    primary = fired[0]
    primary["primary"] = True
    rationale = _rationale(primary, fired, chains, has_curvature, curvature_evidence,
                           non_randomized, rand_evidence, mode, dtype, all_extrapolated,
                           low_hull, design, len(skipped))
    out = {
        "contract_version": CONTRACT_VERSION,
        # No wall-clock on purpose: recommendations.next_design_ref carries this
        # file's sha256, so a timestamp would make two identical runs differ (RG-03).
        "recommended_action": primary["action"],
        "rationale": rationale,
        "primary_action_id": primary["id"],
        "actions": fired,
        "skipped_actions": skipped,
        "design_type": dtype,
        "design_mode": mode,
        "resolution": design.get("resolution"),
        "randomization": {"non_randomized": non_randomized, "evidence": rand_evidence},
        "curvature_evidence": curvature_evidence,
        "has_quadratic_terms": has_quad,
        "design_region_bounds": {f: {"low": lo, "high": hi, "source": bound_sources.get(f)}
                                 for f, (lo, hi) in sorted(bounds.items())},
        "hard_constraints": {f: {"min": lo, "max": hi, "source": c.get("source")}
                             for f, (lo, hi, c) in sorted(hard.items())},
        "seed": seed,
        "provenance": {"authored_by": "script", "script_version": CONTRACT_VERSION,
                       "window_emission": "forbidden (design-only artifact)"},
    }
    return out


def _rationale(primary, fired, chains, has_curvature, curvature_evidence, non_randomized,
               rand_evidence, mode, dtype, all_extrapolated, low_hull, design, n_skipped):
    bits = []
    if primary["action"] == "fold_over":
        bits.append(f"分辨率 {design.get('resolution')} ≤ 4 且存在别名链（{len(chains)} 条）："
                    f"先做镜像折叠以解除二阶混淆")
    elif primary["action"] in ("augment_star", "augment_axial"):
        if has_curvature:
            bits.append(f"已有 {len(curvature_evidence)} 个显著二次项但设计无轴向星点，"
                        f"需补 axial 点以定位驻点")
        else:
            bits.append("线性模型且无曲率证据、设计无星点：补星点以估计曲率（避免把弯曲"
                        "误判为线性）")
    elif primary["action"] == "confirm_replicate":
        bits.append(f"运行顺序未随机化（{rand_evidence}）：效应与时序混杂，先做独立重复确认")
    elif primary["action"] == "space_filling":
        why = []
        if mode in ("observational", None) and dtype == "observational":
            why.append("观测模式")
        if all_extrapolated:
            why.append("全部窗口外推")
        if low_hull:
            why.append("设计域为凸包外/置信低")
        bits.append("、".join(why) + "：用空间填充设计覆盖区域，而不是继续在无支撑区推优")
    else:
        bits.append("没有触发任何确认/补点规则：现有设计对当前结论足够")
    others = [a["action"] for a in fired[1:]]
    if others:
        bits.append("同时可执行：" + "、".join(others))
    if n_skipped:
        bits.append(f"{n_skipped} 个候选因硬约束违例或几何不可构造被跳过（见 skipped_actions）")
    return "；".join(bits)


# ------------------------------------------------------------------ CLI

def _read_json(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Next-round design proposal (P3-3)")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=None,
                    help="default: <run-dir>/conclusions/next_design.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    ctx = _read_json(run_dir / "00_input" / "analysis_context.json") or {}
    profile = _read_json(run_dir / "01_profile" / "data_profile.json") or {}
    effect_table = _read_json(run_dir / "02_analysis" / "effect_table.json")
    model = _read_json(run_dir / "02_analysis" / "model.json")
    recs = _read_json(run_dir / "conclusions" / "recommendations.json") or {}
    payload = propose(profile, effect_table, model, recs, ctx, seed=args.seed)
    out = Path(args.out) if args.out else run_dir / "conclusions" / "next_design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[design_next] action={payload['recommended_action']} "
          f"primary={payload['primary_action_id']} "
          f"actions={[a['action'] for a in payload['actions']]} -> {out}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
