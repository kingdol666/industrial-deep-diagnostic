"""objective.py — objective.json loading, O-G1/O-G1a validation, domain resolution.

O-G1 (contract): goal=target  <=>  target_range present (2 numbers, lo<=hi);
                 tolerance is mutually exclusive with target_range (O-G1a).
O-G2 domain   : effective domain = factor [min,max] ∩ constraints(box)
                 ∩ prior.factor_observed_ranges (when prior present).
Everything here is deterministic; zero LLM. Raises ObjectiveError on any
contract violation (the CLI turns it into exit code 1 + EXECUTION CONTRACT).
"""

from . import (_contained, _read_json, OPTIMIZER_GOALS, sha256_file)


class ObjectiveError(ValueError):
    """Raised when 00_input/objective.json violates the O-G1 contract."""


NUMERIC_ERRORS = "numeric factor requires numeric min<max"
LEVEL_ERRORS = "categorical factor requires non-empty levels[]"


def validate_objective(o):
    """Returns list of O-G1 error strings ([] = valid). Mirrors objective.schema.json
    plus the strict conditions validate.mjs only warns about."""
    errs = []
    if o.get("contract_version") != "1.0":
        errs.append("contract_version must be '1.0'")
    import re
    if not re.match(r"^OPT-[0-9]{8}-[0-9]{3,}$", str(o.get("campaign_id", ""))):
        errs.append("campaign_id must match ^OPT-[0-9]{8}-[0-9]{3,}$")
    if o.get("goal") not in OPTIMIZER_GOALS:
        errs.append(f"goal must be one of {OPTIMIZER_GOALS}")
    goal = o.get("goal")
    tr = o.get("target_range")
    tol = o.get("tolerance")
    # O-G1a: goal=target <=> target_range; tolerance mutually exclusive
    if goal == "target":
        if not isinstance(tr, (list, tuple)) or len(tr) != 2:
            errs.append("O-G1a: goal=target requires target_range [lo, hi]")
        else:
            lo, hi = tr
            if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float))):
                errs.append("O-G1a: target_range entries must be numbers")
            elif not (float(lo) <= float(hi)):
                errs.append("O-G1a: target_range lo must be <= hi")
        if tol is not None:
            errs.append("O-G1a: tolerance is mutually exclusive with goal=target")
    else:
        if tr is not None:
            errs.append("O-G1a: target_range is only allowed when goal=target")
        if tol is not None and not isinstance(tol, (int, float)):
            errs.append("tolerance must be a number")

    factors = o.get("factors") or []
    if not factors:
        errs.append("at least one factor is required")
    names = set()
    for f in factors:
        name = f.get("name")
        if not name:
            errs.append("every factor requires a name")
            continue
        if name in names:
            errs.append(f"duplicate factor name: {name}")
        names.add(name)
        if f.get("type") == "numeric":
            mn, mx = f.get("min"), f.get("max")
            if not (isinstance(mn, (int, float)) and isinstance(mx, (int, float))
                    and float(mn) < float(mx)):
                errs.append(f"factor {name}: {NUMERIC_ERRORS}")
        elif f.get("type") == "categorical":
            lv = f.get("levels")
            if not isinstance(lv, list) or not lv or not all(
                    isinstance(x, str) and x for x in lv):
                errs.append(f"factor {name}: {LEVEL_ERRORS}")
            if len(set(lv or [])) != len(lv or []):
                errs.append(f"factor {name}: duplicate levels")
        else:
            errs.append(f"factor {name}: type must be numeric|categorical")

    for c in o.get("constraints") or []:
        ctype = c.get("type")
        if ctype not in ("box", "safety", None):
            errs.append(f"constraint type must be box|safety|null, got {ctype}")
        if ctype == "safety" and not c.get("hard", True):
            errs.append("safety constraints are hard by priority (O-G5); "
                        "hard:false is not allowed")
        fac = c.get("factor")
        if fac is not None and fac not in names:
            errs.append(f"constraint references unknown factor {fac}")
        if fac is None and ctype == "box":
            errs.append("box constraint requires a factor")

    b = o.get("budget") or {}
    if not isinstance(b.get("max_rounds"), int) or b.get("max_rounds", 0) < 1:
        errs.append("budget.max_rounds must be a positive integer")
    if not isinstance(b.get("max_trials"), int) or b.get("max_trials", 0) < 1:
        errs.append("budget.max_trials must be a positive integer")
    tpr = b.get("trials_per_round")
    if tpr is not None and (not isinstance(tpr, list) or len(tpr) != 2
                            or tpr[0] < 1 or tpr[1] < tpr[0]):
        errs.append("budget.trials_per_round must be [min, max] with 1 <= min <= max")

    if o.get("convergence_mode") not in (None, "in_range", "desirability"):
        errs.append("convergence_mode must be in_range|desirability")
    for m in o.get("secondary_metrics") or []:
        if m.get("goal") not in OPTIMIZER_GOALS:
            errs.append(f"secondary metric {m.get('metric')}: invalid goal")
    return errs


def load(run_dir, path=None):
    """Load + validate 00_input/objective.json. Returns (objective, meta)."""
    rd = _contained(run_dir)
    obj_path = _contained(path) if path else rd / "00_input" / "objective.json"
    if not obj_path.exists():
        raise ObjectiveError(f"objective.json not found at {obj_path}")
    o = _read_json(obj_path)
    errs = validate_objective(o)
    if errs:
        raise ObjectiveError(
            "objective.json failed O-G1 validation:\n  - " + "\n  - ".join(errs))
    meta = {"path": str(obj_path), "sha256": sha256_file(obj_path)}
    return o, meta


def factor_names(o):
    return [f["name"] for f in o.get("factors", [])]


def numeric_factors(o):
    return [f for f in o.get("factors", []) if f.get("type") == "numeric"]


def categorical_factors(o):
    return [f for f in o.get("factors", []) if f.get("type") == "categorical"]


def _box_constraints(o):
    out = {}
    for c in o.get("constraints") or []:
        if c.get("type") == "box" and c.get("factor"):
            lo, hi = c.get("min"), c.get("max")
            cur = out.setdefault(c["factor"], [None, None])
            if isinstance(lo, (int, float)):
                cur[0] = float(lo) if cur[0] is None else max(cur[0], float(lo))
            if isinstance(hi, (int, float)):
                cur[1] = float(hi) if cur[1] is None else min(cur[1], float(hi))
    return out


def safety_constraints(o):
    """Machine-checkable safety limits: (factor, min, max, expr) with hard priority.
    Constraints carrying only a free-text `expr` are returned too — the script
    cannot evaluate them and flags agent_review_required instead (recorded,
    never silently dropped)."""
    out = []
    for c in o.get("constraints") or []:
        if c.get("type") == "safety":
            out.append({"factor": c.get("factor"), "min": c.get("min"),
                        "max": c.get("max"), "expr": c.get("expr"),
                        "hard": c.get("hard", True), "source": c.get("source")})
    return out


def resolve_domain(o, prior_ranges=None):
    """O-G2 effective domain per factor.

    numeric: intersection of factor [min,max] ∩ box constraints ∩
    prior.factor_observed_ranges (each when present). Empty intersection with
    the prior band falls back to (factor ∩ constraints) — the prior must narrow,
    never invert, the declared domain.
    categorical: declared levels (prior does not remove levels; it only narrows
    numeric ranges).
    """
    boxes = _box_constraints(o)
    prior_ranges = prior_ranges or {}
    domain = {}
    for f in o.get("factors", []):
        name = f["name"]
        if f.get("type") == "categorical":
            domain[name] = {"levels": list(f.get("levels") or [])}
            continue
        lo, hi = float(f["min"]), float(f["max"])
        bc = boxes.get(name)
        if bc:
            lo = max(lo, bc[0]) if bc[0] is not None else lo
            hi = min(hi, bc[1]) if bc[1] is not None else hi
        pr = prior_ranges.get(name)
        if isinstance(pr, dict):
            plo, phi = pr.get("min"), pr.get("max")
        elif isinstance(pr, (list, tuple)) and len(pr) == 2:
            plo, phi = pr[0], pr[1]
        else:
            plo = phi = None
        if plo is not None and phi is not None and float(plo) < float(phi):
            if float(plo) <= hi and float(phi) >= lo:  # non-empty intersection
                lo, hi = max(lo, float(plo)), min(hi, float(phi))
            # else: prior band disjoint from declared domain -> keep declared∩box
        if lo >= hi:
            raise ObjectiveError(
                f"factor {name}: empty effective domain after O-G2 intersection "
                f"[{lo}, {hi}] — check constraints / prior ranges")
        domain[name] = {"lo": float(lo), "hi": float(hi)}
    return domain


def clip_to_domain(setpoints, domain):
    """Clip numeric setpoints into the domain (O-G2 guardrail); returns
    (clipped, [factor names that moved]). Categorical levels pass through —
    membership is enforced by the caller."""
    clipped, moved = dict(setpoints), []
    for name, spec in domain.items():
        if name not in clipped or "lo" not in spec:
            continue
        try:
            v = float(clipped[name])
        except (TypeError, ValueError):
            continue
        v2 = min(max(v, spec["lo"]), spec["hi"])
        if abs(v2 - v) > 1e-12:
            moved.append(name)
            clipped[name] = v2
    return clipped, moved


def in_domain(setpoints, domain):
    for name, spec in domain.items():
        if name not in setpoints:
            return False
        v = setpoints[name]
        if "levels" in spec:
            if v not in spec["levels"]:
                return False
        else:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                return False
            if not (spec["lo"] - 1e-9 <= fv <= spec["hi"] + 1e-9):
                return False
    return True


def categorical_factors_from_domain(domain):
    return [name for name, spec in domain.items() if "levels" in spec]


def numeric_factors_from_domain(domain):
    return [name for name, spec in domain.items() if "lo" in spec]


def prior_observed_ranges(recs):
    """factor_observed_ranges from a doe-analyzer recommendations.json."""
    if not isinstance(recs, dict):
        return {}
    dom = recs.get("applicability_domain") or {}
    fr = dom.get("factor_observed_ranges")
    return fr if isinstance(fr, dict) else {}


def primary_metric(o):
    return o.get("target_metric")


def metric_specs(o, observed_grid=None):
    """Build the desirability spec dict consumed by doe-analyzer
    rsm.combined_desirability: {metric: {goal, lsl, usl, target, weight}}.

    goal=target      -> triangular desirability (lsl=lo, usl=hi, target=mid)
    goal=minimize    -> usl = tolerance when given (full achievement at <= usl)
    goal=maximize    -> lsl = tolerance when given
    observed_grid    -> {metric: (lo, hi)} fallback span for maximize/minimize
    """
    specs = {}
    grid = observed_grid or {}
    goal = o.get("goal")
    if goal == "target":
        lo, hi = [float(x) for x in o["target_range"]]
        specs[o["target_metric"]] = {"goal": "target", "lsl": lo, "usl": hi,
                                     "target": (lo + hi) / 2.0,
                                     "weight": float(o.get("weight") or 1.0)}
    else:
        base = {"goal": goal, "lsl": None, "usl": None, "target": None,
                "weight": float(o.get("weight") or 1.0)}
        if o.get("tolerance") is not None:
            if goal == "minimize":
                base["usl"] = float(o["tolerance"])
            else:
                base["lsl"] = float(o["tolerance"])
        specs[o["target_metric"]] = base
    glo, ghi = grid.get(o["target_metric"], (None, None))
    spec = specs[o["target_metric"]]
    if spec["lsl"] is None:
        spec["_grid_lo"] = glo
    if spec["usl"] is None:
        spec["_grid_hi"] = ghi
    for m in o.get("secondary_metrics") or []:
        name = m.get("metric")
        if not name:
            continue
        specs[name] = {"goal": m.get("goal"), "lsl": m.get("lsl"),
                       "usl": m.get("usl"), "target": m.get("target"),
                       "weight": float(m.get("weight") or 1.0)}
        glo, ghi = grid.get(name, (None, None))
        if specs[name]["lsl"] is None:
            specs[name]["_grid_lo"] = glo
        if specs[name]["usl"] is None:
            specs[name]["_grid_hi"] = ghi
    return specs
