"""Composite stability score, grade, and finding generation.

Score model (frozen, v1 — every penalty maps to evidence in the report):
  start at 100 per parameter, subtract:
  - Nelson:  -min(40, 0.8 * episode_rate_percent)          (0.8 per judge-episode-percent;
             episodes come from sentinelcore.spc.evaluate — field-hardened semantics)
  - CV:      <=1%: 0 | <=3%: -6 | <=5%: -12 | <=10%: -22 | else -32
  - Cpk:     >=1.67: 0 | >=1.33: -4 | >=1.0: -14 | >=0.67: -26 | else -34
             (only when a spec limit exists; one-sided when a single limit)
  - drift:   (only when Mann-Kendall p<0.01 AND relative drift >= 0.1%/day):
             <0.3%: -6 | <1%: -15 | else -25
  - baseline deviation (when a sentinel baseline is used), |robust_z|:
             <=3.5: 0 | <=4.5: -8 | <=6.7: -15 | else -25
Composite = weighted mean of parameter scores (equal weights unless context.weights).
Grade: A >=85 stable | B >=70 sub_stable | C >=50 fluctuating | D <50 unstable.
"""
from __future__ import annotations

import numpy as np

GRADES = [
    ("A", 85, "stable", "稳定"),
    ("B", 70, "sub_stable", "亚稳定"),
    ("C", 50, "fluctuating", "波动"),
    ("D", float("-inf"), "unstable", "不稳定"),
]
MIN_ROWS = 50


def cv_penalty(cv: float | None) -> int:
    if cv is None:
        return 0
    if cv <= 0.01:
        return 0
    if cv <= 0.03:
        return -6
    if cv <= 0.05:
        return -12
    if cv <= 0.10:
        return -22
    return -32


def capability_penalty(cpk) -> int:
    if cpk is None:
        return 0
    if cpk >= 1.67:
        return 0
    if cpk >= 1.33:
        return -4
    if cpk >= 1.0:
        return -14
    if cpk >= 0.67:
        return -26
    return -34


def drift_penalty(per_day_relative: float | None, significant: bool) -> int:
    if not significant or per_day_relative is None:
        return 0
    if per_day_relative < 0.001:
        return 0
    if per_day_relative < 0.003:
        return -6
    if per_day_relative < 0.01:
        return -15
    return -25


def baseline_penalty(robust_z: float | None) -> int:
    if robust_z is None:
        return 0
    az = abs(robust_z)
    if az <= 3.5:
        return 0
    if az <= 4.5:
        return -8
    if az <= 6.7:
        return -15
    return -25


def nelson_penalty(n_violation_points: int, n: int) -> int:
    if not n:
        return 0
    rate_percent = 100.0 * n_violation_points / n
    return int(round(-min(40.0, 0.8 * rate_percent)))


def grade_for(score: float) -> tuple[str, str, str]:
    for grade, floor, key, label in GRADES:
        if score >= floor:
            return grade, key, label
    return "D", "unstable", "不稳定"


def parameter_score(entry: dict) -> dict:
    breakdown = {
        "base": 100,
        "nelson_penalty": nelson_penalty(entry["n_violation_points"], entry["n"]),
        "cv_penalty": cv_penalty(entry["cv"]),
        "capability_penalty": capability_penalty(
            entry["capability"]["cpk"] if entry.get("capability") else None),
        "drift_penalty": drift_penalty(
            (entry.get("drift") or {}).get("per_day_relative"),
            bool((entry.get("drift") or {}).get("significant"))),
        "baseline_penalty": baseline_penalty(
            (entry.get("baseline_ref") or {}).get("robust_z")),
    }
    total = sum(breakdown.values())
    breakdown["total"] = int(round(total))
    return {"score": int(round(total)), "score_breakdown": breakdown}


def composite(parameters: list[dict], weights: dict | None = None) -> float | None:
    scored = [p for p in parameters if p.get("score") is not None]
    if not scored:
        return None
    num = den = 0.0
    for p in scored:
        w = float((weights or {}).get(p["name"], 1.0))
        num += w * p["score"]
        den += w
    return round(num / den, 1) if den else None
