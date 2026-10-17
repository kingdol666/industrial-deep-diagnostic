"""windows_seed.py — prior doe-analyzer recommendations.json -> R001 seeds.

Window prior (contract bus row: "窗口先验: doe-analyzer -> C prior.recommendations:
operating_windows / setpoints / current_baseline"). Seed classes for the R001
window_seed design (plan §5.1 / contract §10):

  joint_setpoint    — recs.joint_setpoints[] entry (contract §5.3, the ONLY
                      actionable carrier in recommendations v1.1). Consumed only
                      when `actionable==true`, `confidence` >= medium,
                      `evidence_level` within `EVIDENCE_LEVEL_THRESHOLD`, and
                      `feasible` with zero hard-constraint violations.
  W2_optimum        — legacy setpoints[] entry factor=="MULTI" (refined optimum + D)
  window_center     — composite midpoints of the top-priority operating window per
                      numeric factor. v1.1 windows are consumed only when
                      `window_role=="marginal_diagnostic"` (frozen) AND
                      `actionable==true`.
  current_baseline  — current_baseline.point verbatim (clipped into domain)

Backward compatibility (P3-4 red line): a window/setpoint WITHOUT the v1.1 keys
(`window_role`, `actionable`, `confidence>=medium`, `evidence_level`) is
legacy-accepted — the pre-v1.1 prior format must keep producing the same three
seed classes, so the optimizer-loop's existing tests stay green.

Traceability: every entry that is *seen but not consumed* is recorded in
`rejected_prior[]` as `{source, window_id|setpoint_id, reason}` (+ `detail` for
the exact blockers). `seed_plan()` returns `{seeds, rejected_prior}`;
`seed_points()` keeps its legacy list return value AND carries the same list on
`.rejected_prior` so a caller can read it without changing the call.

Each seed is clipped into the O-G2 domain; every clip is reported so the CLI
can append a guardrail_log entry. Categorical factors take the baseline level
when present, else the first declared level.
"""

from . import (_read_json, objective as obj_mod)

# Contract §10: joint_setpoints must be actionable, at least medium confidence and
# meet the evidence-level threshold. IDD's evidence ladder is L1 (direct
# measurement, strongest) .. L7 (unsupported assumption); E0-E3 is the tuning
# memory ladder. The optimizer-loop consumes evidence up to L4 (statistical /
# chart-backed) — L5+ (domain knowledge, web, assumptions) is recorded as a
# rejected prior instead of being used as a seed.
EVIDENCE_LEVEL_THRESHOLD = 4

SEED_KINDS = ("joint_setpoint", "W2_optimum", "window_center", "current_baseline")

_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


class SeedList(list):
    """Legacy list return value that also carries the rejection trace.

    `list` subclass so every existing consumer (`if not seeds`, `zip(seeds, …)`,
    indexing, JSON serialisation) keeps working unchanged.
    """

    def __init__(self, seeds=(), rejected_prior=()):
        super().__init__(seeds)
        self.rejected_prior = list(rejected_prior)


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


def _evidence_ok(entry, rejected, source, ident):
    """Contract §10 evidence-level gate. Missing level = legacy-accepted."""
    level = entry.get("evidence_level")
    if level is None:
        return True
    if isinstance(level, (int, float)):
        num = int(level)
    elif isinstance(level, str) and level.strip().upper().startswith("L"):
        try:
            num = int(level.strip().upper()[1:])
        except ValueError:
            num = None
    else:
        num = None
    if num is None:
        rejected.append({"source": source, ident[0]: ident[1],
                         "reason": f"unparsable evidence_level={level!r}"})
        return False
    if num > EVIDENCE_LEVEL_THRESHOLD:
        rejected.append({"source": source, ident[0]: ident[1],
                         "reason": f"evidence_level={level} above the L"
                                   f"{EVIDENCE_LEVEL_THRESHOLD} threshold"})
        return False
    return True


def _window_usable(w, rejected):
    """Contract §10 window gate. Missing v1.1 keys = legacy-accepted."""
    wid = w.get("id")
    role = w.get("window_role")
    if role is not None and role != "marginal_diagnostic":
        rejected.append({"source": "operating_windows", "window_id": wid,
                         "reason": f"window_role={role!r} is not marginal_diagnostic"})
        return False
    if "actionable" in w and w.get("actionable") is not True:
        blockers = w.get("actionable_blockers") or []
        rec = {"source": "operating_windows", "window_id": wid,
               "reason": "actionable=false"}
        if blockers:
            rec["detail"] = {"blockers": list(blockers)}
        rejected.append(rec)
        return False
    if w.get("confirmation_needed") is True:
        rejected.append({"source": "operating_windows", "window_id": wid,
                         "reason": "confirmation_needed_pending"})
        return False
    return True


def _joint_setpoint_usable(sp, rejected):
    """Contract §10 joint_setpoints gate (v1.1 only; nothing legacy here)."""
    sid = sp.get("id")
    if sp.get("actionable") is not True:
        blockers = sp.get("blockers") or sp.get("actionable_blockers") or []
        rec = {"source": "joint_setpoints", "setpoint_id": sid,
               "reason": "actionable!=true"}
        if blockers:
            rec["detail"] = {"blockers": list(blockers)}
        rejected.append(rec)
        return False
    conf = sp.get("confidence")
    if conf is not None and _CONFIDENCE_RANK.get(str(conf), -1) < _CONFIDENCE_RANK["medium"]:
        rejected.append({"source": "joint_setpoints", "setpoint_id": sid,
                         "reason": f"confidence={conf} below medium"})
        return False
    if sp.get("feasible") is False:
        rejected.append({"source": "joint_setpoints", "setpoint_id": sid,
                         "reason": "feasible=false"})
        return False
    if (sp.get("hard_constraint_violations") or 0) > 0:
        rejected.append({"source": "joint_setpoints", "setpoint_id": sid,
                         "reason": f"hard_constraint_violations="
                                   f"{sp.get('hard_constraint_violations')}"})
        return False
    return _evidence_ok(sp, rejected, "joint_setpoints", ("setpoint_id", sid))


def prior_valid(recs):
    """A prior counts as valid when at least one machine-usable anchor exists:
    a consumed joint_setpoint, a MULTI setpoint, any usable operating window, or
    a non-empty baseline point."""
    if not isinstance(recs, dict):
        return False
    rejected = []
    if any(_joint_setpoint_usable(sp, []) for sp in _joint_setpoints(recs)):
        return True
    if _w2_optimum(recs) is not None:
        return True
    if any(w.get("range") and _window_usable(w, rejected)
           for w in recs.get("operating_windows") or []):
        return True
    bp = (recs.get("current_baseline") or {}).get("point") or {}
    if any(v is not None for v in bp.values()):
        return True
    return False


def _joint_setpoints(recs):
    out = []
    for sp in recs.get("joint_setpoints") or []:
        if isinstance(sp, dict) and isinstance(sp.get("factors"), dict) \
                and any(v is not None for v in sp["factors"].values()):
            out.append(sp)
    return out


def _w2_optimum(recs, rejected=None):
    """Legacy refined optimum from setpoints[] factor=="MULTI"."""
    multi = [sp for sp in recs.get("setpoints") or []
             if isinstance(sp, dict) and sp.get("factor") == "MULTI"]
    for i, sp in enumerate(multi):
        raw = ((sp.get("expected_response") or {}).get("raw")) or {}
        if not any(v is not None for v in raw.values()):
            continue
        conf = sp.get("confidence")
        if conf is not None and _CONFIDENCE_RANK.get(str(conf), -1) \
                < _CONFIDENCE_RANK["medium"]:
            if rejected is not None:
                rejected.append({"source": "setpoints", "setpoint_id": f"setpoints[MULTI#{i}]",
                                 "reason": f"confidence={conf} below medium"})
            continue
        return {"raw": raw, "D": (sp.get("expected_response") or {}).get("D")}
    return None


def _window_centers(recs, rejected=None):
    """Top-priority *usable* window per factor -> raw midpoint."""
    best = {}
    for w in recs.get("operating_windows") or []:
        if not isinstance(w, dict):
            continue
        f = w.get("factor")
        rng = w.get("range")
        if not f or not isinstance(rng, (list, tuple)) or len(rng) != 2:
            continue
        try:
            lo, hi = float(rng[0]), float(rng[1])
        except (TypeError, ValueError):
            rejected and rejected.append({"source": "operating_windows",
                                          "window_id": w.get("id"),
                                          "reason": "non-numeric range"})
            continue
        if not (hi >= lo):
            rejected and rejected.append({"source": "operating_windows",
                                          "window_id": w.get("id"),
                                          "reason": "reversed range"})
            continue
        if not _window_usable(w, rejected if rejected is not None else []):
            continue
        pr = w.get("priority")
        pr = pr if isinstance(pr, (int, float)) else 10**9
        cur = best.get(f)
        if cur is None or pr < cur[0]:
            best[f] = (pr, (lo + hi) / 2.0)
    return {f: mid for f, (_p, mid) in best.items()}


def seed_plan(recs, domain, baseline_level=None):
    """Build the R001 seeds + the rejection trace.

    Returns `{"seeds": [{kind, setpoints, moved, prior_D, source}], "rejected_prior":
    [{source, window_id|setpoint_id, reason}]}`. Deduplicated on rounded
    setpoints (the joint setpoint and the legacy optimum often coincide).
    """
    rejected = []
    if not prior_valid(recs):
        return {"seeds": [], "rejected_prior": rejected}
    baseline_pt = dict((recs.get("current_baseline") or {}).get("point") or {})
    centers = _window_centers(recs, rejected)
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

    for sp in _joint_setpoints(recs):
        if _joint_setpoint_usable(sp, rejected):
            seeds.append({"kind": "joint_setpoint", "setpoints": _complete(sp["factors"]),
                          "prior_D": sp.get("desirability"),
                          "source": f"joint_setpoints[{sp.get('id')}]"})
    w2 = _w2_optimum(recs, rejected)
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
    return {"seeds": out, "rejected_prior": rejected}


def seed_points(recs, domain, baseline_level=None):
    """Returns a list of dicts: {kind, setpoints, moved, source} (+ .rejected_prior).

    Kinds (plan §5.1 / contract §10): joint_setpoint / W2_optimum / window_center /
    current_baseline. Deduplicated on rounded setpoints. The returned value is a
    plain-behaving list subclass carrying `rejected_prior` for traceability.
    """
    plan = seed_plan(recs, domain, baseline_level)
    return SeedList(plan["seeds"], plan["rejected_prior"])
