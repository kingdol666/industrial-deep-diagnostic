"""imacore.rank — priority score + deterministic truncation (method_notes §8).

priority = grade_weight × gain_ratio × evidence_strength × feasibility
  grade_weight     A=1.0 / B=0.6 / C=0.25
  gain_ratio       |point| / max|point| (no point → 0.3 baseline)
  evidence_strength |r| ∈ [0,1] (dose-response pair r; 0.3 when unavailable)
  feasibility      distance-to-bound / |delta| capped at 1.0 (1.0 when no bound)
"""

GRADE_WEIGHT = {"A": 1.0, "B": 0.6, "C": 0.25}


def priority_score(grade, point, max_abs_point, evidence_r, feasibility):
    weight = GRADE_WEIGHT.get(grade, 0.25)
    if point is not None and max_abs_point:
        gain_ratio = abs(point) / max_abs_point
    else:
        gain_ratio = 0.3
    strength = min(abs(evidence_r), 1.0) if evidence_r is not None else 0.3
    feasi = 1.0 if feasibility is None else min(max(float(feasibility), 0.0), 1.0)
    return round(weight * gain_ratio * strength * feasi, 6)


def sort_and_cap(actions, max_actions):
    ranked = sorted(actions, key=lambda a: (-(a.get("priority_score") or 0.0),
                                            str(a.get("action_id"))))
    return ranked[:max_actions]


def feasibility_ratio(magnitude_to, bound_lo, bound_hi, delta):
    """Fraction of the allowed box the proposed move consumes (1.0 = no bound)."""
    if delta is None or abs(delta) < 1e-15:
        return 1.0
    if bound_lo is None and bound_hi is None:
        return 1.0
    room = None
    if bound_hi is not None and (magnitude_to is not None):
        room = max(bound_hi - magnitude_to, 0.0)
    if bound_lo is not None and (magnitude_to is not None):
        room_lo = max(magnitude_to - bound_lo, 0.0)
        room = room_lo if room is None else min(room, room_lo)
    if room is None:
        return 1.0
    return min(room / abs(delta), 1.0)
