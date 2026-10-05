#!/usr/bin/env python
"""gen_T3_tuning.py — Examiner generator for T3 (tuning memory).

Creates cases/T3_tuning_memory/:
  data.csv          200 rows: t, temp_c, pressure_mpa, speed_rpm, feed_rate_kgh,
                    yield_pct. Injected dynamics (truth):
                      row 100 (t=01:40Z): temp 85.0 -> 77.0 AND yield +1.6 (+2 sigma)
                      row 150 (t=02:30Z): pressure 2.40 -> 2.60, yield unchanged
                      row 197 (t=03:17Z): speed 1250 -> 1255, recording ends 3 rows later
  action_log.json   3 action logs (schema action_log v1.0, trigger=manual)
  fault_signature.json  regime-matched signature (temp_c high + speed_rpm high)
  playbook_seed/tuning_experience.jsonl  2 seeded historical entries in the exact
                    tuning_experience envelope the skill scripts read/write.
Seeded: numpy default_rng(20261003).
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261003
OUT = Path(__file__).resolve().parent.parent / "T3_tuning_memory"
BASE = pd.Timestamp("2026-10-04 00:00:00Z")
N = 200


def canon(obj):
    """Mirror of experience_build.mjs canonical JSON (sorted keys, compact)."""
    if obj is None or not isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, list):
        return "[" + ",".join(canon(x) for x in obj) + "]"
    keys = sorted(k for k in obj.keys() if obj[k] is not None)
    return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canon(obj[k])
                          for k in keys) + "}"


def sha16(obj):
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()[:16]


def ar1(rng, n, sigma, phi=0.2):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + np.sqrt(1 - phi * phi) * e[i]
    return x


def main():
    rng = np.random.default_rng(SEED)
    (OUT / "playbook_seed").mkdir(parents=True, exist_ok=True)

    ts = pd.date_range(BASE, periods=N, freq="min")
    temp = 85.0 + ar1(rng, N, 0.3)
    temp[100:] = 77.0 + ar1(rng, N - 100, 0.3)          # A1 real move
    press = 2.40 + ar1(rng, N, 0.008)
    press[150:] = 2.60 + ar1(rng, N - 150, 0.008)       # A2 below-noise move
    speed = 1250.0 + ar1(rng, N, 1.2)
    speed[197:] = 1255.0 + ar1(rng, N - 197, 1.2)       # A3 no data after
    feed = 320.0 + ar1(rng, N, 2.0)
    y = 93.5 + ar1(rng, N, 0.78)
    y[100:] = y[100:] + 1.6                             # +2 sigma step aligned to A1
    df = pd.DataFrame({
        "t": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temp_c": np.round(temp, 4),
        "pressure_mpa": np.round(press, 5),
        "speed_rpm": np.round(speed, 3),
        "feed_rate_kgh": np.round(feed, 3),
        "yield_pct": np.round(y, 4),
    })
    df.to_csv(OUT / "data.csv", index=False)

    action_log = [
        {
            "schema_version": "1.0",
            "ts": "2026-10-04T01:40:00Z",
            "actor": {"actor_id": "eng_zhou", "actor_type": "engineer", "display_alias": None},
            "actions": [{"parameter": "temp_c", "from": 85.0, "to": 77.0, "unit": "degC"}],
            "bundled_action": {"is_bundle": False, "bundle_reason": "single", "note": None},
            "context": {"product": "PVC-M", "machine": "calender-03",
                        "regime_label": "night_shift", "group_key": None},
            "trigger": {"trigger_type": "manual", "ref_id": None},
            "outcome": {"metric": "yield_pct", "observed_trajectory": "settled_to_target",
                        "observed_by": "engineer_reported"},
        },
        {
            "schema_version": "1.0",
            "ts": "2026-10-04T02:30:00Z",
            "actor": {"actor_id": "eng_zhou", "actor_type": "engineer", "display_alias": None},
            "actions": [{"parameter": "pressure_mpa", "from": 2.40, "to": 2.60, "unit": "bar"}],
            "bundled_action": {"is_bundle": False, "bundle_reason": "single", "note": None},
            "context": {"product": "PVC-M", "machine": "calender-03",
                        "regime_label": "night_shift", "group_key": None},
            "trigger": {"trigger_type": "manual", "ref_id": None},
            "outcome": {"metric": "yield_pct", "observed_trajectory": "no_change",
                        "observed_by": "engineer_reported"},
        },
        {
            "schema_version": "1.0",
            "ts": "2026-10-04T03:17:00Z",
            "actor": {"actor_id": "eng_li", "actor_type": "engineer", "display_alias": None},
            "actions": [{"parameter": "speed_rpm", "from": 1250.0, "to": 1255.0, "unit": "rpm"}],
            "bundled_action": {"is_bundle": False, "bundle_reason": "single", "note": None},
            "context": {"product": "PVC-M", "machine": "calender-03",
                        "regime_label": "night_shift", "group_key": None},
            "trigger": {"trigger_type": "manual", "ref_id": None},
            "outcome": {"metric": "yield_pct", "observed_trajectory": "not_observed",
                        "observed_by": "engineer_reported"},
        },
    ]
    (OUT / "action_log.json").write_text(json.dumps(action_log, ensure_ascii=False, indent=2),
                                         encoding="utf-8")

    fault_sig = {
        "signature_version": "1.0",
        "source_ref": "ALT-20261003-0217-001",
        "anomalous_params": [
            {"parameter": "temp_c", "direction": "high", "severity": 2.8},
            {"parameter": "speed_rpm", "direction": "high", "severity": 2.1},
        ],
        "regime": {"product": "PVC-M", "machine": "calender-03", "regime_label": "night_shift"},
        "degraded_metric": "yield_pct",
    }
    (OUT / "fault_signature.json").write_text(json.dumps(fault_sig, ensure_ascii=False, indent=2),
                                              encoding="utf-8")

    # ---- seeded historical entries (exact tuning_experience envelope) -------
    def recipe_entry(regime_key, anomalous, seq, effect, summary, actor_alias,
                     log_id, invalidations):
        params = [[a["parameter"], a["to"], a["unit"]] for a in seq]
        params += [[p["parameter"], p["direction"]] for p in anomalous]
        sig = {"etype": "fault_control_recipe", "params": params}
        chunk = {"etype": "fault_control_recipe", "regime_key": regime_key, "params": params}
        return {
            "experience_version": "1.0",
            "experience_type": "fault_control_recipe",
            "regime_key": regime_key,
            "payload": {
                "action_summary": summary,
                "effect": effect,
                "attribution_status": "estimable",
                "confound_detected": False,
                "fault_signature": {"anomalous_params": anomalous},
                # frozen schema surface for seq items: parameter/to/to_level/
                # unit/step_order/expected_effect (no "from" — the gate's
                # strict-extra-keys check rejects it; mirror buildRecipeEntry)
                "action_sequence": [{**{"parameter": a["parameter"], "to": a["to"],
                                        "unit": a["unit"]},
                                     "to_level": None, "step_order": i + 1,
                                     "expected_effect": {"delta": effect["delta"],
                                                         "ci95": effect["ci95"]}}
                                    for i, a in enumerate(seq)],
                "applicability_note": None,
                "lesson": "历史处置：熔温/线速双高导致收率下降，按配方降设定后恢复。",
                "confirm_status": None,
                "trajectory": "settled_to_target",
            },
            "applicability": {"factor_observed_ranges": None, "system": None,
                              "scenario_tags": [regime_key]},
            "provenance": {
                "actor_alias": actor_alias,
                "action_log_ids": [log_id],
                "run_ids": [],
                "batch_ids": [],
                "regime_key": regime_key,
                "attribution_version": "tune_stats/1.0",
                "built_from": "industrial-tuning-memory/experience_build/1.0",
                "judge_score": None,
                "era": "2025H2",
            },
            "confidence_label": "observation",
            "evidence_grade": "E1",
            "corroboration_count": 1,
            "refutation_count": 0,
            "cross_regime_consistent": False,
            "invalidation_conditions": invalidations,
            "chunk_id": f"exp_fault_control_recipe_{regime_key[:8]}_{sha16(chunk)}",
            "action_signature": sha16(sig),
            "retro_mined": False,
            "param_directions": {},
        }

    s1 = recipe_entry(
        regime_key="PVC-M|calender-03|night_shift",
        anomalous=[{"parameter": "temp_c", "direction": "high"},
                   {"parameter": "speed_rpm", "direction": "high"}],
        seq=[{"parameter": "temp_c", "from": 85.0, "to": 77.0, "unit": "degC"},
             {"parameter": "speed_rpm", "from": 1250.0, "to": 1238.0, "unit": "rpm"}],
        effect={"metric": "yield_pct", "delta": 1.58, "ci95": [1.02, 2.14],
                "n_eff": 19, "direction_established": True},
        summary="故障处置处方：temp_c: 85.0 → 77.0 (degC); speed_rpm: 1250.0 → 1238.0 (rpm)"
                "（触发源 ALT-20251102-0144-006）",
        actor_alias="eng_li",
        log_id="20251102ALT014406",
        invalidations=["超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推"],
    )
    s2 = recipe_entry(
        regime_key="PVC-R|calender-05|day_shift",
        anomalous=[{"parameter": "viscosity_cp", "direction": "high"}],
        seq=[{"parameter": "viscosity_cp", "from": 2180.0, "to": 2105.0, "unit": "cP"}],
        effect={"metric": "gloss_gu", "delta": -0.9, "ci95": [-1.6, -0.2],
                "n_eff": 22, "direction_established": True},
        summary="故障处置处方：viscosity_cp: 2180.0 → 2105.0 (cP)（触发源 ALT-20250918-0312-002）",
        actor_alias="eng_wang",
        log_id="20250918ALT031202",
        invalidations=["超出该 regime_key 工况范围的应用未经本经验支持，不得直接外推"],
    )
    (OUT / "playbook_seed" / "tuning_experience.jsonl").write_text(
        json.dumps(s1, ensure_ascii=False) + "\n" + json.dumps(s2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print("T3 tuning-memory assets written to", OUT)
    print("  seeded chunk_ids:", s1["chunk_id"], "|", s2["chunk_id"])


if __name__ == "__main__":
    main()
