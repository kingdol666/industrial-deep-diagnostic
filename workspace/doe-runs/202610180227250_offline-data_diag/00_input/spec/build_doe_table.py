#!/usr/bin/env python
"""Build the DOE analysis table from the AW DAQ snapshot (deterministic ETL).

Inputs (absolute, read-only):
  <SNAPSHOT>/manifest.json      node id -> name/unit/semantics
  <SNAPSHOT>/dn-*.csv           ts_iso, ts_ms, value, state

Outputs (inside the run dir):
  00_input/doe_table.csv              one row per settled shot per condition
  00_input/doe_table_build_report.json provenance + per-condition raw/settled stats

Rules (see 00_input/condition_windows.json):
  * one row = one shot (part_weight_g sample); secondary signals averaged over
    [shot_ts, shot_ts + 5.2 s)
  * settling guard: discard shots in the first `settling_guard_s` seconds of a
    condition window WHEN the factor levels changed vs the preceding condition
    (C1 inherits the pre-experiment baseline, so it has no step to settle from)
  * balance: keep the LAST K shots per condition, K = min available
"""
import csv
import json
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN_DIR = Path(sys.argv[1]).resolve()
SNAPSHOT = Path(sys.argv[2]).resolve()

BLOCK_S = 5.2
GUARD_S = 180


def ms(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def iso(millis):
    return datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc).isoformat()


def load_csv(path):
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append((int(r["ts_ms"]), float(r["value"]), r["state"]))
    rows.sort()
    return rows


def main():
    win_spec = json.loads((RUN_DIR / "00_input" / "spec" / "condition_windows.json").read_text(encoding="utf-8"))
    manifest = json.loads((SNAPSHOT / "manifest.json").read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in manifest["nodes"]}
    mapping = win_spec["node_mapping"]

    series = {}
    for nid, spec in mapping.items():
        path = SNAPSHOT / f"{nid}.csv"
        series[spec["column"]] = load_csv(path)
        assert nodes[nid]["name"], nid

    shot = series["part_weight_g"]
    conditions = win_spec["conditions"]
    pre_start = shot[0][0]
    first_cond_start = ms(conditions[0]["start"])

    # rows per condition, with the guard applied only where a step actually occurred
    prev_levels = None
    per_cond = []
    for cond in conditions:
        s, e = ms(cond["start"]), ms(cond["end"])
        levels = (cond["hold_pressure_sp_bar"], cond["barrel_zone1_temp_sp_c"])
        stepped = prev_levels is not None and levels != prev_levels
        guard_from = s + (GUARD_S * 1000 if stepped else 0)
        shots = [(t, v) for t, v, _ in shot if guard_from <= t < e]
        rows = []
        for t, v in shots:
            block = {}
            for col, data in series.items():
                vals = [x[1] for x in data if t <= x[0] < t + BLOCK_S * 1000]
                block[col] = st.mean(vals) if vals else None
            block["part_weight_g"] = v
            block["ts_ms"] = t
            rows.append(block)
        per_cond.append({"cond": cond, "levels": levels, "stepped": stepped,
                         "guard_from_ms": guard_from, "rows": rows})
        prev_levels = levels

    K = min(len(c["rows"]) for c in per_cond)

    table_rows, cond_stats = [], []
    for c in per_cond:
        cond = c["cond"]
        rows = c["rows"][-K:]
        for i, r in enumerate(rows, start=1):
            table_rows.append({
                "run_id": f"{cond['id']}-{i:02d}",
                "condition": cond["id"],
                "ts_block_start": iso(r["ts_ms"]),
                "hold_pressure_sp_bar": cond["hold_pressure_sp_bar"],
                "barrel_zone1_temp_sp_c": cond["barrel_zone1_temp_sp_c"],
                "part_weight_g": round(r["part_weight_g"], 4),
                "cycle_time_s": round(r["cycle_time_s"], 4) if r["cycle_time_s"] is not None else "",
                "melt_temp_c": round(r["melt_temp_c"], 4),
                "injection_pressure_bar": round(r["injection_pressure_bar"], 4),
            })
        raw = c["rows"]
        used = rows
        cond_stats.append({
            "condition": cond["id"],
            "levels": {"hold_pressure_sp_bar": c["levels"][0],
                       "barrel_zone1_temp_sp_c": c["levels"][1]},
            "window": {"start": cond["start"], "end": cond["end"]},
            "factor_step_vs_previous": c["stepped"],
            "guard_discarded_s": GUARD_S if c["stepped"] else 0,
            "n_shots_raw_in_window": len([1 for t, _v, _s in shot
                                          if ms(cond["start"]) <= t < ms(cond["end"])]),
            "n_shots_after_guard": len(raw),
            "n_shots_used": len(used),
            "used_window": {"from": iso(used[0]["ts_ms"]), "to": iso(used[-1]["ts_ms"])},
            "settled_means": {k: round(st.mean([r[k] for r in used]), 4)
                              for k in ("part_weight_g", "cycle_time_s", "melt_temp_c",
                                        "injection_pressure_bar")},
            "settled_sd": {k: round(st.pstdev([r[k] for r in used]), 4)
                           for k in ("part_weight_g", "cycle_time_s", "melt_temp_c",
                                     "injection_pressure_bar")},
            "raw_window_means": {k: round(st.mean([r[k] for r in raw]), 4)
                                 for k in ("part_weight_g", "melt_temp_c",
                                           "injection_pressure_bar")},
        })

    # pre-experiment baseline (before C1) for the "C1 inherits steady state" claim
    pre = [(t, v) for t, v, _ in shot if pre_start <= t < first_cond_start]
    pre_melt = [x[1] for x in series["melt_temp_c"] if pre_start <= x[0] < first_cond_start]
    pre_inj = [x[1] for x in series["injection_pressure_bar"] if pre_start <= x[0] < first_cond_start]
    baseline = {
        "n_shots": len(pre),
        "part_weight_g_mean": round(st.mean([v for _, v in pre]), 4),
        "part_weight_g_sd": round(st.pstdev([v for _, v in pre]), 4),
        "melt_temp_c_mean": round(st.mean(pre_melt), 4),
        "injection_pressure_bar_mean": round(st.mean(pre_inj), 4),
    }

    out_csv = RUN_DIR / "00_input" / "doe_table.csv"
    cols = ["run_id", "condition", "ts_block_start", "hold_pressure_sp_bar",
            "barrel_zone1_temp_sp_c", "part_weight_g", "cycle_time_s",
            "melt_temp_c", "injection_pressure_bar"]
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(table_rows)

    report = {
        "schema": "doe.table-build/1",
        "snapshot": str(SNAPSHOT),
        "manifest_export_id": manifest.get("export_id"),
        "line": manifest["lines"][0]["lineName"],
        "product": manifest["lines"][0].get("productName"),
        "recipe": {"name": manifest["lines"][0].get("recipeName"),
                   "version": manifest["lines"][0].get("recipeVersion")},
        "node_columns": {nid: {"name": nodes[nid]["name"], "unit": nodes[nid]["unit"],
                               "column": spec["column"], "role": spec["role"]}
                         for nid, spec in mapping.items()},
        "block_seconds": BLOCK_S,
        "settling_guard_s": GUARD_S,
        "balance_k_per_condition": K,
        "n_rows": len(table_rows),
        "design": "2^2 full factorial (A x B) + 1 center condition, run sequentially",
        "pre_experiment_baseline": baseline,
        "conditions": cond_stats,
        "zero_variance_responses": ["cycle_time_s (single value 15.3 s in every sample of the snapshot)"],
        "notes": [
            "A shot = one part_weight_g sample; 2 s process signals are averaged inside each shot block.",
            "Settling guard only applies to conditions whose factor levels changed vs the previous condition.",
            "Each condition was run once; shots inside a condition are repeated measures (pseudo-replication), "
            "run-order is not randomized.",
        ],
    }
    (RUN_DIR / "00_input" / "doe_table_build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[etl] rows={len(table_rows)} K={K} conditions={len(cond_stats)} -> {out_csv}")
    for c in cond_stats:
        print(f"  {c['condition']} levels={c['levels']} used={c['n_shots_used']} "
              f"means={c['settled_means']}")


if __name__ == "__main__":
    main()
