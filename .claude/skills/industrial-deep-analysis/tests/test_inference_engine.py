#!/usr/bin/env python3
"""Unit tests for the inference engine (E3.5).

Verifies that the deterministic inference layer genuinely recovers:

1. p-value scientific floor (no 0.0 underflow corruption)
2. indirect/mediation channel detection (X → M → Y)
3. temporal precedence direction + lag recovery
4. change-point co-movement alignment
5. group/regime interaction (moderation) detection
6. leave-one-out leverage stability + influence flagging
7. full pairwise scan correctness (r and BH q)

Run:  python .claude/skills/industrial-deep-analysis/tests/test_inference_engine.py
No third-party test runner required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from inference_engine import (  # noqa: E402
    pairwise_scan,
    temporal_causality,
    change_point_co_movement,
    conditional_independence,
    leverage_stability,
    moderator_check,
    mediation_scan,
    causality_ceiling,
    build_association_graph,
    _cusum_change_points,
    P_VALUE_FLOOR,
)

_FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        _FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL {name}: {detail}")
    else:
        print(f"  ok   {name}")


def test_p_value_floor() -> None:
    """Extreme t never reports exact 0.0; floor flag is set."""
    from stat_utils import safe_p_value

    p, hit = safe_p_value(66.0)
    check("p-floor-clamp", p == P_VALUE_FLOOR and hit, f"p={p} hit={hit}")
    p, hit = safe_p_value(2.5)
    check("p-floor-normal", 0.005 < p < 0.05 and not hit, f"p={p} hit={hit}")
    p, hit = safe_p_value(float("nan"))
    check("p-floor-nan", p == 1.0 and not hit, f"p={p} hit={hit}")


def test_temporal_causality_direction() -> None:
    """A leads B by 3 steps: engine must recover direction and lag."""
    rng = np.random.default_rng(42)
    n = 800
    t = np.arange(n, dtype=float)
    a = 0.05 * t + np.sin(t / 40.0) + rng.normal(0, 0.3, n)
    b = np.empty(n)
    noise = rng.normal(0, 0.3, n)
    for i in range(n):
        if i >= 3:
            b[i] = 0.8 * a[i - 3] + noise[i]
        else:
            b[i] = noise[i]
    res = temporal_causality(a, b, t, max_lag=15)
    check("temporal-valid", res["valid"], str(res))
    check("temporal-direction", res["direction"] == "x_leads_y",
          f"direction={res['direction']}")
    check("temporal-lag", res["optimal_lag_steps"] == 3,
          f"lag={res['optimal_lag_steps']}")
    check("temporal-significant", res["p_value"] <= 0.05, f"p={res['p_value']}")


def test_temporal_concurrent() -> None:
    """Truly synchronous series must NOT claim precedence."""
    rng = np.random.default_rng(7)
    n = 500
    t = np.arange(n, dtype=float)
    common = np.sin(t / 30.0) + rng.normal(0, 0.2, n)
    a = common + rng.normal(0, 0.3, n)
    b = common + rng.normal(0, 0.3, n)
    res = temporal_causality(a, b, t, max_lag=15)
    check("temporal-concurrent", res["direction"] == "concurrent",
          f"direction={res['direction']} lag={res['optimal_lag_steps']}")


def test_mediation_detection() -> None:
    """X→M→Y chain: global strong, full partial collapses, mediator found."""
    rng = np.random.default_rng(1)
    n = 600
    x = rng.normal(0, 1, n)
    m = 0.9 * x + rng.normal(0, 0.4, n)
    y = 0.8 * m + rng.normal(0, 0.4, n)
    # noise channel — must not appear as mediator
    z = rng.normal(0, 1, n)
    df = pd.DataFrame({"X": x, "M": m, "Y": y, "Z": z, "W": rng.normal(0, 1, n)})

    r_xy = float(np.corrcoef(x, y)[0, 1])
    ci = conditional_independence(df, "X", "Y", ["M", "Z", "W"])
    check("mediation-CI-valid", ci["valid"] and abs(ci["partial_r"]) < 0.15,
          f"partial_full={ci}")
    med = mediation_scan(df, "X", "Y", ["M", "Z", "W"], r_xy,
                         ci["partial_r"], ci["valid"])
    check("mediation-channel", med["valid"] and med["candidates"] and
          med["candidates"][0]["mediator"] == "M",
          f"candidates={[c['mediator'] for c in med['candidates']]}")


def test_direct_association() -> None:
    """X→Y direct: partial survives conditioning on noise variables."""
    rng = np.random.default_rng(3)
    n = 800
    x = rng.normal(0, 1, n)
    y = 0.7 * x + rng.normal(0, 0.6, n)
    z = rng.normal(0, 1, n)
    df = pd.DataFrame({"X": x, "Y": y, "Z": z, "Q": rng.normal(0, 1, n)})
    ci = conditional_independence(df, "X", "Y", ["Z", "Q"])
    check("direct-CI", ci["valid"] and ci["partial_r"] > 0.4, str(ci))


def test_change_point_co_movement() -> None:
    """Two series with a joint level shift must align."""
    rng = np.random.default_rng(11)
    n = 400
    base = np.zeros(n)
    base[150:] = 3.0
    a = base + rng.normal(0, 0.4, n)
    b = base + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"A": a, "B": b})
    res = change_point_co_movement(df, "A", "B")
    check("cp-aligned", res["valid"] and res["flagged"],
          f"cpa={res['cp_a']} cpb={res['cp_b']} score={res['score']}")

    # Independent shifts must NOT flag
    c = np.zeros(n)
    c[300:] = 3.0
    df2 = pd.DataFrame({"A": a, "C": c})
    res2 = change_point_co_movement(df2, "A", "C")
    check("cp-independent", not res2["flagged"],
          f"score={res2['score']} cpa={res2['cp_a']} cpc={res2['cp_b']}")


def test_moderator_interaction() -> None:
    """Sign divergence across groups must flag interaction."""
    rng = np.random.default_rng(5)
    g1 = pd.DataFrame({"X": rng.normal(0, 1, 200), "Y": 0.8 * rng.normal(0, 1, 200), "G": "g1"})
    g1["Y"] = 0.8 * g1["X"] + rng.normal(0, 0.3, 200)
    g2 = pd.DataFrame({"X": rng.normal(0, 1, 200), "G": "g2"})
    g2["Y"] = -0.8 * g2["X"] + rng.normal(0, 0.3, 200)
    df = pd.concat([g1, g2], ignore_index=True)
    rs = []
    for name, sub in df.groupby("G"):
        rs.append(float(np.corrcoef(sub["X"], sub["Y"])[0, 1]))
    inter = moderator_check(df, "X", "Y", "G", rs, "G")
    check("interaction-sign", inter["flagged"] and inter["sign_divergence"],
          f"r={rs} {inter}")


def test_leverage_outlier() -> None:
    """A single extreme point must be detected by LOO range."""
    rng = np.random.default_rng(9)
    n = 120
    x = rng.normal(0, 1, n)
    y = 0.6 * x + rng.normal(0, 0.4, n)
    res_clean = leverage_stability(x, y)
    check("loo-clean", res_clean["valid"] and not res_clean["flagged"],
          str(res_clean))
    # Inject one huge outlier
    x2 = x.copy()
    y2 = y.copy()
    x2[-1] = 30.0
    y2[-1] = -30.0
    res_dirty = leverage_stability(x2, y2)
    check("loo-outlier", res_dirty["valid"] and res_dirty["flagged"],
          str(res_dirty))


def test_pairwise_scan() -> None:
    """Scan recovers known correlations and BH-corrects p-values."""
    rng = np.random.default_rng(15)
    n = 300
    a = rng.normal(0, 1, n)
    b = 0.85 * a + rng.normal(0, 0.4, n)
    c = rng.normal(0, 1, n)
    df = pd.DataFrame({"A": a, "B": b, "C": c})
    scan = pairwise_scan(df, ["A", "B", "C"])
    check("scan-count", len(scan) == 3, str(len(scan)))
    top = scan[0]
    check("scan-top-pair", {top["predictor"], top["target"]} == {"A", "B"},
          f"{top['predictor']}-{top['target']}")
    check("scan-r", abs(top["r"] - 0.85) < 0.1, f"r={top['r']}")
    check("scan-q", top["q_value"] <= 0.05, f"q={top['q_value']}")
    ac = next(s for s in scan if {s["predictor"], s["target"]} == {"A", "C"})
    check("scan-noise-q", ac["q_value"] > 0.05, f"q={ac['q_value']}")


def test_causality_ceiling_levels() -> None:
    """Ceiling never exceeds what evidence supports."""
    # Ontology-consistent + temporal + CI → highest level
    temporal = {"valid": True, "direction": "x_leads_y", "optimal_lag_steps": 2,
                "p_value": 0.001, "ccf_peak_r": 0.5, "lag_aligned_r": 0.5, "n_used": 100}
    partial_full = {"valid": True, "partial_r": 0.5, "method": "full_order_ridge",
                    "n_controls": 3, "n_used": 100}
    onto = {"from": "X", "to": "Y", "data_direction_validated": "true",
            "predicted_direction_sign": 1}
    c = causality_ceiling(temporal, partial_full, onto, 0.6, 100)
    check("ceiling-top", c["ceiling"] == "ontology_consistent" and not c["ontology_contradiction"],
          str(c))
    # Contradiction: data negative vs ontology positive
    c2 = causality_ceiling(temporal, partial_full, onto, -0.6, 100)
    check("ceiling-contradiction", c2["ontology_contradiction"], str(c2))
    # Weak: no temporal, no CI → contemporaneous
    c3 = causality_ceiling({"valid": False}, {"valid": False, "partial_r": 0.0},
                           None, 0.4, 50)
    check("ceiling-contemp", c3["ceiling"] == "contemporaneous_correlation", str(c3))


def test_association_graph_semantics() -> None:
    """Graph edges carry sign/inhibits/contradicts semantics."""
    rng = np.random.default_rng(33)
    n = 500
    x = rng.normal(0, 1, n)
    y_pos = 0.8 * x + rng.normal(0, 0.4, n)
    y_neg = -0.8 * x + rng.normal(0, 0.4, n)
    df = pd.DataFrame({"X": x, "YP": y_pos, "YN": y_neg})
    ontology = {
        "signals": {"process_parameters": [
            {"column": "X", "label": "X", "role": "predictor"},
            {"column": "YP", "label": "YP", "role": "target"},
            {"column": "YN", "label": "YN", "role": "target"},
        ]},
        "relationships": [
            {"from": "X", "to": "YP", "data_direction_validated": "true",
             "predicted_direction_sign": 1},
            {"from": "X", "to": "YN", "data_direction_validated": "true",
             "predicted_direction_sign": 1},
        ],
        "metadata": {"units": {}},
    }
    selection = {"quality_targets": ["YP", "YN"], "predictor_cols": ["X"],
                 "analysis_tiers": {}, "metadata_cols": []}
    pairwise = pairwise_scan(df, ["X", "YP", "YN"])
    graph = build_association_graph(df, ["X", "YP", "YN"], ontology, selection, [], pairwise)
    edges = {(e["source"], e["target"]): e for e in graph["edges"]}
    # Full scan: X→YP, X→YN and the YP↔YN collateral edge all enter the network
    check("graph-edge-count", len(graph["edges"]) == 3, str(len(graph["edges"])))
    check("graph-supports", edges[("X", "YP")]["relationship"] == "supports" and edges[("X", "YP")]["sign"] == 1,
          str(edges[("X", "YP")].get("relationship")))
    check("graph-inhibits", edges[("YP", "YN")]["relationship"] == "inhibits" and edges[("YP", "YN")]["sign"] == -1,
          str(edges[("YP", "YN")].get("relationship")))
    check("graph-contradiction", edges[("X", "YN")]["ontology_contradiction"] is True
          and edges[("X", "YN")]["relationship"] == "contradicts",
          str(edges[("X", "YN")].get("relationship")))


def main() -> None:
    print("inference engine tests:")
    for fn in [
        test_p_value_floor,
        test_temporal_causality_direction,
        test_temporal_concurrent,
        test_mediation_detection,
        test_direct_association,
        test_change_point_co_movement,
        test_moderator_interaction,
        test_leverage_outlier,
        test_pairwise_scan,
        test_causality_ceiling_levels,
        test_association_graph_semantics,
    ]:
        fn()
    if _FAILURES:
        print(f"\n{len(_FAILURES)} FAILURES")
        sys.exit(1)
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
