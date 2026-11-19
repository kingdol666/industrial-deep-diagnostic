#!/usr/bin/env python
"""gen_experience_scenario.py — scenario generator for the industrial-tuning-memory
pipeline job (closed-loop demo, 05-closedloop/experience).

Design intent (all parameters below are scenario choices, fixed before any
skill script runs; the skill scripts recompute every number from the series):

  Injection-molding line IMM-07, product PP-Cup-330ml, two operating regimes
  (normal / high_output). 42 logged parameter actions spaced 220 sampling rows
  apart (1 row = 1 minute) so each effect window [t+tau, t+settle) stays
  untruncated (settle=200 default < 220 spacing) and free of same/other-lever
  overlap (confound-free attribution geometry).

  Ground-truth response used to SYNTHESIZE the series (the attribution scripts
  never see this file):
      energy_kwh_per_kg = 2.62 + 0.018*(barrel_temp_c - 200)
                              + 0.010*(cooling_time_s - 28)
                              + 0*injection_pressure_bar + 0*back_pressure_bar
                              + N(0, 0.02)   (iid, seed 20261119)
    -> barrel_temp_c DOWN moves carry an attributable energy decrease
       (delta ~ -0.09 per -5 degC, CI excludes 0 -> estimable -> corroboration
       promotes to E2 within a regime, E3 across the two regimes);
    -> back_pressure_bar / injection_pressure_bar moves have NO energy effect
       (delta ~ 0, CI crosses 0 -> stays E1 "observation"; the evidence gate
       must refuse promotion despite repeated corroboration counts).

  The CSV ledger's kpi_before/kpi_after columns are the engineer-visible 30-row
  pre / 195-row post means computed from the SAME series (no hand-entered KPIs).

Outputs (under 05-closedloop/experience/):
  00_input/data.csv              time series (t + 4 setpoint columns + metric)
  00_input/action_log.csv        human-readable adjustment ledger (42 rows)
  00_input/action_log.json       schema v1.0 action logs (1 log per CSV row,
                                 ingest_meta.source=csv_import, explicit
                                 action_log_id = ledger action_id)
  00_input/actor_alias_map.json  privacy alias map (raw engineer ids -> eng_NN)
  00_input/fault_signature.json  NEW observation encoded as retrieval query
  00_input/new_observation.csv   the same new observation in ledger form
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "experience"
INP = RUN / "00_input"

SEED = 20261119
SIGMA = 0.02
BASE = 2.62
K_BT = 0.018      # kWh/kg per degC
K_CT = 0.010      # kWh/kg per s
BT0, IP0, CT0, BP0 = 200.0, 115.0, 28.0, 12.0
ROW_SPACING = 220
FIRST_ROW = 60
N_ROWS = 9600
T0 = "2026-11-08T06:00:00Z"
PRODUCT, MACHINE = "PP-Cup-330ml", "IMM-07"
ACTORS = ["EMP-023", "EMP-041", "EMP-077", "EMP-115"]

# (lever, direction, magnitude, regime) — executed in this order on ONE machine,
# so each lever's setpoint state carries forward.
PLAN = [
    # barrel_temp_c — normal regime: repeated DOWN moves landing on shared
    # targets (195/190/185) so same-signature logs corroborate within regime
    ("barrel_temp_c", "down", 5, "normal"),    # 1  200->195
    ("barrel_temp_c", "down", 5, "normal"),    # 2  195->190
    ("barrel_temp_c", "down", 5, "normal"),    # 3  190->185
    ("barrel_temp_c", "up", 15, "normal"),     # 4  185->200  (recipe reset)
    ("barrel_temp_c", "down", 5, "normal"),    # 5  200->195
    ("barrel_temp_c", "down", 5, "normal"),    # 6  195->190
    ("barrel_temp_c", "down", 5, "normal"),    # 7  190->185
    ("barrel_temp_c", "up", 14, "normal"),     # 8  185->199
    ("barrel_temp_c", "down", 4, "normal"),    # 9  199->195
    ("barrel_temp_c", "down", 5, "normal"),    # 10 195->190
    # barrel_temp_c — high_output regime; setpoint state carries over from the
    # normal block (bt=190 at this point). Two DOWN moves land on to=185 so the
    # signature repeats across BOTH regimes (cross-regime E3 demonstration);
    # the up-move to=190 is a same-signature-but-opposite-direction observation
    # that the E3 gate must honestly refuse (all-E2 precondition fails).
    ("barrel_temp_c", "down", 5, "high_output"),   # 11 190->185
    ("barrel_temp_c", "down", 5, "high_output"),   # 12 185->180
    ("barrel_temp_c", "up", 10, "high_output"),    # 13 180->190
    ("barrel_temp_c", "down", 5, "high_output"),   # 14 190->185
    # cooling_time_s — small real effect (down = less energy)
    ("cooling_time_s", "down", 2, "normal"),   # 15 28->26
    ("cooling_time_s", "down", 2, "normal"),   # 16 26->24
    ("cooling_time_s", "up", 4, "normal"),     # 17 24->28
    ("cooling_time_s", "down", 2, "normal"),   # 18 28->26
    ("cooling_time_s", "down", 2, "normal"),   # 19 26->24
    ("cooling_time_s", "up", 6, "normal"),     # 20 24->30
    ("cooling_time_s", "down", 4, "normal"),   # 21 30->26
    # injection_pressure_bar — no energy effect (counter-example lever 1)
    ("injection_pressure_bar", "up", 3, "normal"),    # 22 115->118
    ("injection_pressure_bar", "down", 6, "normal"),  # 23 118->112
    ("injection_pressure_bar", "up", 3, "normal"),    # 24 112->115
    ("injection_pressure_bar", "up", 3, "normal"),    # 25 115->118
    ("injection_pressure_bar", "down", 3, "normal"),  # 26 118->115
    ("injection_pressure_bar", "down", 5, "normal"),  # 27 115->110
    ("injection_pressure_bar", "up", 5, "normal"),    # 28 110->115
    ("injection_pressure_bar", "up", 3, "normal"),    # 29 115->118
    ("injection_pressure_bar", "down", 3, "normal"),  # 30 118->115
    ("injection_pressure_bar", "down", 3, "normal"),  # 31 115->112
    # back_pressure_bar — no energy effect, mixed directions
    # (counter-example lever 2: direction/result inconsistent -> gate refuses E2)
    ("back_pressure_bar", "up", 1.5, "high_output"),  # 32 12->13.5
    ("back_pressure_bar", "down", 1.5, "high_output"),  # 33 13.5->12
    ("back_pressure_bar", "up", 1.5, "high_output"),  # 34 12->13.5
    ("back_pressure_bar", "down", 3, "high_output"),  # 35 13.5->10.5
    ("back_pressure_bar", "up", 3, "high_output"),    # 36 10.5->13.5
    ("back_pressure_bar", "down", 1.5, "normal"),     # 37 13.5->12
    ("back_pressure_bar", "up", 2, "normal"),         # 38 12->14
    ("back_pressure_bar", "down", 2, "normal"),       # 39 14->12
    ("back_pressure_bar", "up", 1.5, "normal"),       # 40 12->13.5
    ("back_pressure_bar", "down", 1.5, "normal"),     # 41 13.5->12
    ("back_pressure_bar", "down", 1.5, "normal"),     # 42 12->10.5
]

UNITS = {"barrel_temp_c": "degC", "injection_pressure_bar": "bar",
         "cooling_time_s": "s", "back_pressure_bar": "bar"}
TRAJECTORY_REAL = "settled_to_target"
TRAJECTORY_NONE = "no_change"


def energy_model(bt, ct):
    return BASE + K_BT * (bt - BT0) + K_CT * (ct - CT0)


def main():
    INP.mkdir(parents=True, exist_ok=True)
    assert len(PLAN) >= 40, "ledger must carry >=40 actions"

    # ------------------------------------------------ action rows + setpoint steps
    action_rows = [FIRST_ROW + i * ROW_SPACING for i in range(len(PLAN))]
    sp = {"barrel_temp_c": BT0, "injection_pressure_bar": IP0,
          "cooling_time_s": CT0, "back_pressure_bar": BP0}
    logs, ledger = [], []
    for i, (lever, direction, mag, regime) in enumerate(PLAN):
        row = action_rows[i]
        frm = sp[lever]
        step = mag if direction == "up" else -mag
        to = round(frm + step, 3)
        sp[lever] = to
        aid = f"ACT-{i + 1:03d}"
        ts_min = row  # minutes since T0
        ts = pd.Timestamp(T0) + pd.Timedelta(minutes=ts_min)
        ts_iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        logs.append({
            "schema_version": "1.0",
            "action_log_id": aid,
            "ts": ts_iso,
            "actor": {"actor_id": ACTORS[i % len(ACTORS)], "actor_type": "engineer",
                      "display_alias": None},
            "actions": [{"parameter": lever, "from": frm, "to": to,
                         "unit": UNITS[lever]}],
            "bundled_action": {"is_bundle": False, "bundle_reason": "single",
                               "note": None},
            "context": {"product": PRODUCT, "machine": MACHINE,
                        "regime_label": regime},
            "trigger": {"trigger_type": "manual", "ref_id": None},
            "outcome": {"metric": "energy_kwh_per_kg",
                        "observed_trajectory": (TRAJECTORY_REAL if lever in
                                                ("barrel_temp_c", "cooling_time_s")
                                                else TRAJECTORY_NONE),
                        "observed_by": "engineer_reported"},
            "ingest_meta": {"source": "csv_import", "ingested_at": None},
        })
        ledger.append({"action_id": aid, "timestamp": ts_iso, "row": row,
                       "lever": lever, "direction": direction,
                       "magnitude": mag, "from_value": frm, "to_value": to,
                       "unit": UNITS[lever], "regime": regime,
                       "actor_id": ACTORS[i % len(ACTORS)]})

    # ------------------------------------------------ time series
    rng = np.random.default_rng(SEED)
    bt = np.full(N_ROWS, BT0)
    ip = np.full(N_ROWS, IP0)
    ct = np.full(N_ROWS, CT0)
    bp = np.full(N_ROWS, BP0)
    for i, (lever, _d, _m, _r) in enumerate(PLAN):
        row = action_rows[i]
        val = logs[i]["actions"][0]["to"]
        col = {"barrel_temp_c": bt, "injection_pressure_bar": ip,
               "cooling_time_s": ct, "back_pressure_bar": bp}[lever]
        col[row:] = val
    energy = energy_model(bt, ct) + rng.normal(0.0, SIGMA, N_ROWS)
    energy = np.round(energy, 4)

    times = [(pd.Timestamp(T0) + pd.Timedelta(minutes=int(r))).strftime(
        "%Y-%m-%dT%H:%M:%SZ") for r in range(N_ROWS)]
    df = pd.DataFrame({"t": times, "barrel_temp_c": bt,
                       "injection_pressure_bar": ip, "cooling_time_s": ct,
                       "back_pressure_bar": bp, "energy_kwh_per_kg": energy})
    df.to_csv(INP / "data.csv", index=False)

    # ------------------------------------------------ ledger KPI columns
    # engineer-visible before/after KPI = same window semantics as the skill's
    # segment defaults (baseline 30 rows pre-action; effect [t+5, t+200))
    for i, rec in enumerate(ledger):
        row = rec["row"]
        b = energy[max(0, row - 30):row].mean()
        a = energy[row + 5:min(row + 5 + 195, N_ROWS)].mean()
        rec["kpi_before"] = round(float(b), 4)
        rec["kpi_after"] = round(float(a), 4)

    led = pd.DataFrame(ledger)[["action_id", "timestamp", "row", "lever",
                                "direction", "magnitude", "from_value",
                                "to_value", "unit", "regime", "actor_id",
                                "kpi_before", "kpi_after"]]
    led.to_csv(INP / "action_log.csv", index=False)
    (INP / "action_log.json").write_text(
        json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------ privacy alias map
    alias = {a: f"eng_{n + 1:02d}" for n, a in enumerate(ACTORS)}
    (INP / "actor_alias_map.json").write_text(
        json.dumps(alias, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------ NEW observation (retrieval query)
    # Observation recorded 2026-11-19 (today): same machine/regime, energy run
    # high; the corrective direction under consideration for barrel_temp_c is
    # DOWN ("low" = sign(to-from) track of tuning_action_effect entries).
    new_obs = {
        "signature_version": "1.0",
        "source_ref": "manual-observation-20261119-IMM07",
        "anomalous_params": [{"parameter": "barrel_temp_c", "direction": "low",
                              "severity": 1.6}],
        "regime": {"product": PRODUCT, "machine": MACHINE,
                   "regime_label": "normal"},
        "degraded_metric": "energy_kwh_per_kg",
    }
    (INP / "fault_signature.json").write_text(
        json.dumps(new_obs, ensure_ascii=False, indent=2), encoding="utf-8")
    tail_mean = round(float(energy[-60:].mean()), 4)
    pd.DataFrame([{
        "action_id": "OBS-001",
        "timestamp": "2026-11-19T08:30:00Z",
        "lever": "barrel_temp_c",
        "direction": "down",
        "magnitude": "",
        "kpi_before": tail_mean,
        "kpi_after": "",
        "note": "新观察(检索查询,尚未执行动作):能耗偏高,拟下调 barrel_temp_c; "
                "以 fault_signature.json 编码后做本地经验检索",
    }]).to_csv(INP / "new_observation.csv", index=False)

    # ------------------------------------------------ scenario ground truth note
    gt = {
        "purpose": "scenario ground truth used ONLY by the generator to synthesize "
                   "00_input/data.csv; tuning-memory scripts never read this file",
        "seed": SEED, "sigma": SIGMA, "base": BASE,
        "coef_barrel_temp_c_per_degC": K_BT,
        "coef_cooling_time_s_per_s": K_CT,
        "coef_injection_pressure_bar": 0.0,
        "coef_back_pressure_bar": 0.0,
        "row_spacing": ROW_SPACING, "first_action_row": FIRST_ROW,
        "n_rows": N_ROWS,
    }
    (INP / "scenario_ground_truth.json").write_text(
        json.dumps(gt, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"data.csv rows={N_ROWS}; ledger actions={len(ledger)}; "
          f"regimes={sorted(set(r['regime'] for r in ledger))}")
    print(f"barrel_temp final={sp['barrel_temp_c']} cooling={sp['cooling_time_s']} "
          f"inj={sp['injection_pressure_bar']} back={sp['back_pressure_bar']}")


if __name__ == "__main__":
    main()
