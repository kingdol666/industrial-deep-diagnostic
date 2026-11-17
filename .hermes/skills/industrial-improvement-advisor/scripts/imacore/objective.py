"""imacore.objective — goal contract validation, deterministic goal inference,
conflict detection (method_notes §5).

Explicit objective.json: targets[1..3] {metric,direction,target_value?,…},
constraints[], horizon, dead_time?, levers?, kpis?.

Vague mode (missing/empty targets): script infers KPI candidates that BOTH
(a) have ≥1 significant operable lever relation and (b) show improvable
deviation (spec/window departure, else IQR/|median| dispersion proxy —
disclosed in limitations). Ranking = deviation × max|effect| × log10(n_eff).
Inferred targets stay capped at grade B until the user re-runs with an
explicit objective.
"""

import math

from . import _io

DIRECTION_KEYWORDS = {
    "max": ("yield", "良率", "合格率", "收率", "throughput", "效率", "产出",
            "efficiency", "recovery"),
    "min": ("defect", "不良", "废品", "缺陷", "能耗", "energy", "loss", "损失",
            "scrap", "cost", "成本", "noise", "噪声", "nvh", "排放", "emission"),
}


def name_direction(col):
    """Deterministic keyword prior for the goal direction of a KPI name."""
    lower = str(col).lower()
    for kw in DIRECTION_KEYWORDS["max"]:
        if kw in lower:
            return "max"
    return "min"


def load_objective(run_dir):
    path = run_dir / "00_input" / "objective.json"
    if not path.is_file():
        return None
    try:
        return _io.read_json(path)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"OBJECTIVE_INVALID: {path} — unreadable JSON ({exc})")


def validate_objective(obj, numeric_cols):
    """Strict validation; returns normalized targets/constraints or raises."""
    errors = []
    if not isinstance(obj, dict):
        raise SystemExit("OBJECTIVE_INVALID: top-level must be an object")
    if str(obj.get("contract_version")) != "1.0":
        errors.append("contract_version must be '1.0'")
    targets = obj.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("targets must be a non-empty array (vague mode = omit file)")
        targets = []
    if len(targets) > 3:
        errors.append("targets maxItems = 3")
    normalized = []
    for i, t in enumerate(targets):
        if not isinstance(t, dict):
            errors.append(f"targets[{i}] must be an object")
            continue
        metric = t.get("metric")
        direction = t.get("direction")
        if not metric or str(metric) not in numeric_cols:
            errors.append(f"targets[{i}].metric '{metric}' not a numeric column")
        if direction not in ("min", "max", "target"):
            errors.append(f"targets[{i}].direction must be min|max|target")
        if direction == "target" and not isinstance(t.get("target_value"), (int, float)):
            errors.append(f"targets[{i}].target_value required for direction=target")
        normalized.append({
            "metric": str(metric), "direction": direction,
            "target_value": t.get("target_value"),
            "tolerance": t.get("tolerance"), "weight": t.get("weight"),
        })
    dead_time = obj.get("dead_time", None)
    if isinstance(dead_time, (int, float)):
        if dead_time < 0:
            errors.append("dead_time must be >= 0")
        dead_time = float(dead_time)
    elif dead_time in (None, "unknown"):
        dead_time = None
    else:
        errors.append("dead_time must be a number >= 0, 'unknown', or omitted")
    constraints = []
    for i, c in enumerate(obj.get("constraints") or []):
        if not isinstance(c, dict):
            errors.append(f"constraints[{i}] must be an object")
            continue
        param = c.get("param")
        if param and str(param) not in numeric_cols:
            errors.append(f"constraints[{i}].param '{param}' not a numeric column")
        constraints.append({"param": str(param) if param else None,
                            "min": c.get("min"), "max": c.get("max"),
                            "type": c.get("type") or "box",
                            "hard": bool(c.get("hard", False))})
    levers = [str(x) for x in (obj.get("levers") or [])]
    kpis = [str(x) for x in (obj.get("kpis") or [])]
    for name in levers + kpis:
        if name not in numeric_cols:
            errors.append(f"levers/kpis entry '{name}' not a numeric column")
    if errors:
        raise SystemExit("OBJECTIVE_INVALID: " + " | ".join(errors))
    return {
        "contract_version": "1.0",
        "targets": normalized,
        "constraints": constraints,
        "horizon": obj.get("horizon"),
        "dead_time": dead_time,
        "levers": levers,
        "kpis": kpis,
        "notes": obj.get("notes"),
    }


def deviation_score(series, spec=None, window=None):
    """Improvable deviation: 0 when no departure and no dispersion.

    * spec [lsl,usl] / window [lsl,usl] when available: |median-center|/half
    * else dispersion proxy IQR/|median| (disclosed in limitations)
    """
    clean = series.dropna()
    if len(clean) < 10:
        return 0.0, "insufficient"
    median = float(clean.median())
    for rng in (spec, window):
        if isinstance(rng, (list, tuple)) and len(rng) == 2 \
                and rng[0] is not None and rng[1] is not None:
            lo, hi = float(rng[0]), float(rng[1])
            lo, hi = min(lo, hi), max(lo, hi)
            half = (hi - lo) / 2.0
            if half > 1e-12:
                center = (hi + lo) / 2.0
                return abs(median - center) / half, "spec_or_window"
    q10, q90 = clean.quantile(0.10), clean.quantile(0.90)
    iqr = float(q90 - q10)
    scale = max(abs(median), 1e-9)
    return iqr / scale, "dispersion_proxy"


def infer_targets(df, kpi_cols, lever_effects, windows, specs):
    """Deterministic vague-mode goal inference.

    lever_effects: {(lever, kpi): {"r":…, "p":…, "fdr_q":…, "ok": bool}}
    """
    candidates = []
    n = len(df)
    for kpi in kpi_cols:
        if kpi not in df.columns:
            continue
        effects = [e for (lever, k), e in lever_effects.items()
                   if k == kpi and e.get("ok")]
        if not effects:
            continue
        max_effect = max(abs(e.get("r") or 0.0) for e in effects)
        if max_effect < _io.CONSTANTS["min_effect_r"]:
            continue
        dev, basis = deviation_score(df[kpi], spec=specs.get(kpi),
                                     window=windows.get(kpi))
        if dev <= 0.0 or basis == "insufficient":
            continue
        direction = name_direction(kpi)
        score = dev * max_effect * math.log10(max(n, 10))
        candidates.append({
            "metric": kpi, "direction": direction,
            "deviation": _io.finite(dev), "deviation_basis": basis,
            "max_effect_r": _io.finite(max_effect),
            "score": _io.finite(score),
            "rationale": (f"偏离={dev:.3f}({basis}) × |r|max={max_effect:.3f} × "
                          f"log10(n={n})"),
        })
    candidates.sort(key=lambda c: -(c["score"] or 0))
    if not candidates:
        return {"inferred": True, "targets": [], "candidates": [],
                "rationale": "没有同时满足'有显著可操作杠杆'与'有可改善偏离'的 KPI"}
    top = candidates[0]["score"] or 0.0
    chosen = [c for c in candidates if (c["score"] or 0.0) >= 0.8 * top][:2]
    targets = [{"metric": c["metric"], "direction": c["direction"],
                "target_value": None, "tolerance": None, "weight": 1.0}
               for c in chosen]
    rationale = ("系统推断目标: 从数据中按'偏离度×传导强度×数据充分度'排序确定；"
                 "推断目标未确认前全部建议封顶 B 级。用户显式声明目标重跑即可解锁。")
    return {"inferred": True, "targets": targets, "candidates": candidates,
            "rationale": rationale}


def required_lever_sign(direction, slope, current=None, target_value=None):
    """Sign of the lever move that improves the KPI (method_notes §5)."""
    if direction == "min":
        want = -1.0
    elif direction == "max":
        want = 1.0
    elif direction == "target" and target_value is not None and current is not None:
        if abs(float(target_value) - float(current)) <= 1e-9:
            return 0  # already at target — no direction exists
        want = 1.0 if target_value > current else -1.0
    else:
        return 0
    if abs(slope) < 1e-15:
        return 0
    return int(want * (1 if slope > 0 else -1))


def detect_conflicts(targets, lever_effects):
    """Opposite required directions for the same lever across two targets."""
    conflicts = []
    for i, a in enumerate(targets):
        for b in targets[i + 1:]:
            for (lever, kpi), ev in lever_effects.items():
                if not ev.get("ok") or kpi != a["metric"]:
                    continue
                ev_b = lever_effects.get((lever, b["metric"]))
                if not ev_b or not ev_b.get("ok"):
                    continue
                req_a = required_lever_sign(a["direction"], ev.get("slope") or 0.0)
                req_b = required_lever_sign(b["direction"], ev_b.get("slope") or 0.0)
                if req_a == 0 or req_b == 0 or req_a == req_b:
                    continue
                conflicts.append({
                    "lever": lever,
                    "target_a": a["metric"], "target_b": b["metric"],
                    "direction_a": "increase" if req_a > 0 else "decrease",
                    "direction_b": "increase" if req_b > 0 else "decrease",
                    "resolution": "user_decision_required",
                })
    return conflicts
