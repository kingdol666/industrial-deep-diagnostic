"""windows_seed.py — prior doe-analyzer recommendations.json -> R001 seeds.

Window prior (contract bus row: "窗口先验: doe-analyzer -> C prior.recommendations:
operating_windows / setpoints / current_baseline"). Three deterministic seed
classes for the R001 window_seed design (plan §5.1):

  W2_optimum     — setpoints[] entry factor=="MULTI" (refined optimum + its D)
  window_center  — composite midpoints of the top-priority operating window
                   per numeric factor (missing factors -> domain center)
  current_baseline — current_baseline.point verbatim (clipped into domain)

Each seed is clipped into the O-G2 domain; every clip is reported so the CLI
can append a guardrail_log entry. Categorical factors take the baseline level
when present, else the first declared level.
"""

from . import (_read_json, objective as obj_mod)


def load_prior_recommendations(o, run_dir):
    """Locate the prior recommendations.json.

    Priority: objective.prior.doe_analyzer_run_dir/conclusions/recommendations.json
    -> RUN_DIR/00_input/recommendations.json -> None (absent prior is legal;
    the R1 design then falls back to lhs_fill).
    """
    prior = o.get("prior") or {}
    ref = prior.get("doe_analyzer_run_dir")
    candidates = []
    if ref:
        candidates.append(_ref_path(ref, run_dir)
                          / "conclusions" / "recommendations.json")
        candidates.append(_ref_path(ref, run_dir) / "recommendations.json")
    rd = obj_mod._contained(run_dir)
    candidates.append(rd / "00_input" / "recommendations.json")
    for p in candidates:
        try:
            if p.exists():
                return obj_mod._read_json(p)
        except (ValueError, OSError):
            continue
    return None


def _ref_path(ref, run_dir):
    import os
    from . import _contained
    try:
        return _contained(ref)
    except ValueError:
        # allow run-dir-relative references (containment still enforced)
        return _contained(obj_mod._contained(run_dir) / str(ref))


def prior_valid(recs):
    """A prior counts as valid when at least one machine-usable anchor exists:
    a MULTI setpoint, any operating window, or a non-empty baseline point."""
    if not isinstance(recs, dict):
        return False
    if _w2_optimum(recs) is not None:
        return True
    if any(w.get("range") for w in recs.get("operating_windows") or []):
        return True
    bp = (recs.get("current_baseline") or {}).get("point") or {}
    if any(v is not None for v in bp.values()):
        return True
    return False


def _w2_optimum(recs):
    for sp in recs.get("setpoints") or []:
        if sp.get("factor") == "MULTI":
            raw = ((sp.get("expected_response") or {}).get("raw")) or {}
            if any(v is not None for v in raw.values()):
                return {"raw": raw, "D": (sp.get("expected_response") or {}).get("D")}
    return None


def _window_centers(recs):
    """Top-priority window per factor -> raw midpoint."""
    best = {}
    for w in recs.get("operating_windows") or []:
        f = w.get("factor")
        rng = w.get("range")
        if not f or not isinstance(rng, (list, tuple)) or len(rng) != 2:
            continue
        try:
            lo, hi = float(rng[0]), float(rng[1])
        except (TypeError, ValueError):
            continue
        if not (hi >= lo):
            continue
        pr = w.get("priority")
        pr = pr if isinstance(pr, (int, float)) else 10**9
        cur = best.get(f)
        if cur is None or pr < cur[0]:
            best[f] = (pr, (lo + hi) / 2.0)
    return {f: mid for f, (_p, mid) in best.items()}


def seed_points(recs, domain, baseline_level=None):
    """Returns list of dicts: {kind, setpoints, moved (clipped factors), source}.

    Kinds (plan §5.1): W2_optimum / window_center / current_baseline.
    Deduplicated on rounded setpoints (W2 optimum often equals a window center).
    """
    if not prior_valid(recs):
        return []
    baseline_pt = dict((recs.get("current_baseline") or {}).get("point") or {})
    centers = _window_centers(recs)
    seeds = []

    def _fill_categorical(sp):
        for f in obj_mod.categorical_factors_from_domain(domain):
            if sp.get(f) not in domain[f]["levels"]:
                sp[f] = baseline_level if baseline_level in domain[f]["levels"] \
                    else domain[f]["levels"][0]
        return sp

    def _complete(sp):
        sp = dict(sp)
        for f, spec in domain.items():
            if "lo" in spec and sp.get(f) is None:
                sp[f] = (spec["lo"] + spec["hi"]) / 2.0
        return _fill_categorical(sp)

    w2 = _w2_optimum(recs)
    if w2:
        seeds.append({"kind": "W2_optimum", "setpoints": _complete(w2["raw"]),
                      "prior_D": w2.get("D"), "source": "setpoints[MULTI]"})
    if centers:
        seeds.append({"kind": "window_center", "setpoints": _complete(centers),
                      "prior_D": None, "source": "operating_windows midpoints"})
    if any(v is not None for v in baseline_pt.values()):
        seeds.append({"kind": "current_baseline", "setpoints": _complete(baseline_pt),
                      "prior_D": None, "source": "current_baseline.point"})

    out, seen = [], set()
    for s in seeds:
        clipped, moved = obj_mod.clip_to_domain(s["setpoints"], domain)
        key = tuple(round(float(clipped[f]), 6) if f in clipped else clipped[f]
                    for f in sorted(domain))
        if key in seen:
            continue
        seen.add(key)
        out.append({"kind": s["kind"], "setpoints": clipped, "moved": moved,
                    "prior_D": s.get("prior_D"), "source": s["source"]})
    return out
