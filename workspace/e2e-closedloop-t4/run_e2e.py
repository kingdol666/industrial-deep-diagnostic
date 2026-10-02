# -*- coding: utf-8 -*-
"""T4 closed-loop E2E: fault injection -> sentinel alert -> experience retrieval
-> optimizer campaign -> converged -> recipe into experience store.

Chain (all real script runs, zero LLM):
  doe-analyzer (designed 2^3 factorial, physical units)
    -> sentinel build_baseline (--doe-run-dir, A7 verbatim handoff)
    -> sentinel watch on fault-injected window (exit 1 expected)
    -> fault_signature derived from the alert
    -> tuning-memory: attribute -> build -> recommend (playbook_hit) -> ack -> gate
    -> optimizer-loop: init -> design/ingest rounds (simulated plant) -> converge -> gate
    -> tuning-memory feedback (effective) -> corroboration+1 -> gate
Plant truth: yield(temp, press) = 100 - 0.25*(temp-84)^2 - 60*(press-0.60)^2
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / ".claude" / "shared"
E2E = ROOT / "workspace" / "e2e-closedloop-t4" / "e2e"
SENT = ROOT / ".claude" / "skills" / "industrial-sentinel"
TUNE = ROOT / ".claude" / "skills" / "industrial-tuning-memory"
OPT = ROOT / ".claude" / "skills" / "industrial-optimizer-loop"
DOE = ROOT / ".claude" / "skills" / "industrial-doe-analyzer"
PY = sys.executable

SEED = 20261001
PRODUCT, MACHINE, REGIME = "PA", "L1", "S1"
ALERT_ID_HOLDER = {}


def plant(temp, press):
    return 100.0 - 0.25 * (temp - 84.0) ** 2 - 60.0 * (press - 0.60) ** 2


def iso_row(i):
    # 1 row = 1 minute sampling step, from 2026-01-05T00:00Z
    base = pd.Timestamp("2026-01-05T00:00:00Z")
    return (base + pd.Timedelta(minutes=int(i))).strftime("%Y-%m-%dT%H:%M:%SZ")


def dithered(level, sigma, n, rng):
    """Alternating bounded jitter (F1-style dithered sensor emulation): steady
    segments are deterministic-quiet under Nelson sign rules."""
    j = 0.02 * sigma
    sign = np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    return level + sign * j + rng.normal(0, 0.01 * sigma, n)


def record(checks, name, ok, detail=""):
    checks.append((name, bool(ok), str(detail)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          timeout=kw.pop("timeout", 600), shell=False, **kw)


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- stage 0: data
def stage0():
    print("[S0] data generation (seed %d, plant: yield=100-0.25*(T-84)^2-60*(P-0.6)^2)" % SEED)
    import shutil
    if E2E.exists():
        shutil.rmtree(E2E)
    rng = np.random.default_rng(SEED)
    (E2E / "doe_run" / "00_input").mkdir(parents=True, exist_ok=True)
    (E2E / "sentinel").mkdir(parents=True, exist_ok=True)
    (E2E / "tune_run" / "00_input").mkdir(parents=True, exist_ok=True)
    (E2E / "opt_run" / "00_input").mkdir(parents=True, exist_ok=True)

    # --- designed experiment 2^3 x 2 reps in physical units
    rows = []
    for _rep in range(2):
        for t, p, r in [(82, 0.55, 110), (82, 0.55, 130), (82, 0.65, 110), (82, 0.65, 130),
                        (88, 0.55, 110), (88, 0.55, 130), (88, 0.65, 110), (88, 0.65, 130)]:
            y = plant(t, p) + rng.normal(0, 0.3)
            rows.append({"temp": t, "press": p, "rate": r, "yield_pct": round(float(y), 4)})
    pd.DataFrame(rows).to_csv(E2E / "doe_run" / "00_input" / "data.csv", index=False)
    write_json(E2E / "doe_run" / "00_input" / "analysis_context.json", {
        "data_path": "00_input/data.csv", "mode_override": None,
        "responses": [{"col": "yield_pct", "goal": "maximize", "lsl": None,
                       "usl": None, "target": None, "weight": None}],
        "factors": [{"col": "temp", "type": "numeric"}, {"col": "press", "type": "numeric"},
                    {"col": "rate", "type": "numeric"}],
        "blocks": [], "covariates": [], "index_cols": [], "time_col": None,
        "group_col": None, "run_order_col": None, "max_lag": 20, "alpha": 0.05,
        "effect_size_threshold": 0.01, "constraints": [],
        "inference": {"assigned_by": "user", "notes": ["T4 e2e physical-unit factorial"]}})

    # --- sentinel history (steady, 8000 rows)
    n_hist = 8000
    hist = pd.DataFrame({
        "t": [iso_row(i) for i in range(n_hist)],
        "temp": np.round(dithered(85.0, 0.8, n_hist, rng), 4),
        "press": np.round(dithered(0.60, 0.02, n_hist, rng), 5),
        "rate": np.round(dithered(120.0, 1.5, n_hist, rng), 3),
    })
    hist.to_csv(E2E / "sentinel" / "history.csv", index=False)

    # --- fault window (10000 rows): temp drifts +0.0006/row from row 3000
    n_win = 10000
    drift = np.where(np.arange(n_win) >= 3000, (np.arange(n_win) - 3000) * 0.0006, 0.0)
    win = pd.DataFrame({
        "t": [iso_row(i) for i in range(n_win)],
        "temp": np.round(dithered(85.0, 0.8, n_win, rng) + drift, 4),
        "press": np.round(dithered(0.60, 0.02, n_win, rng), 5),
        "rate": np.round(dithered(120.0, 1.5, n_win, rng), 3),
    })
    win.to_csv(E2E / "sentinel" / "window_fault.csv", index=False)

    # --- tuning-memory series: yield level steps at rows 2000 / 4000
    n_tune = 6000
    y = np.full(n_tune, plant(85.0, 0.60))
    y[2000:] += plant(88.0, 0.60) - plant(85.0, 0.60)   # wrong-way move (harmful)
    y[4000:] += plant(84.0, 0.60) - plant(88.0, 0.60)   # corrective move (effective)
    y = y + rng.normal(0, 0.5, n_tune)
    pd.DataFrame({"t": [iso_row(i) for i in range(n_tune)],
                  "yield_pct": np.round(y, 4)}).to_csv(
        E2E / "tune_run" / "00_input" / "data.csv", index=False)
    print("  generated: doe 16 rows, history 8000, fault window 10000, tune 6000")


# ------------------------------------------------------- stage 1: doe-analyzer
def stage1(checks):
    print("[S1] doe-analyzer real run (designed mode, physical units)")
    doe_run = E2E / "doe_run"
    r = run([PY, DOE / "scripts" / "analyze.py", "all", "--run-dir", doe_run])
    record(checks, "S1.doe_analyze_exit0", r.returncode == 0, r.stderr[-300:])
    recs = read_json(doe_run / "conclusions" / "recommendations.json")
    record(checks, "S1.recommendations_v1", recs.get("contract_version") == "1.0",
           recs.get("contract_version"))
    record(checks, "S1.operating_windows_present",
           len(recs.get("operating_windows", [])) > 0,
           f"{len(recs.get('operating_windows', []))} windows")
    g = run(["node", DOE / "scripts" / "quality_gate.mjs", doe_run,
             "--skill-path", DOE, "--shared-path", SHARED])
    record(checks, "S1.doe_gate_exit0", g.returncode == 0, (g.stdout + g.stderr)[-300:])
    return recs


# ----------------------------------------------- stage 2: sentinel baseline+watch
def stage2(checks):
    print("[S2] sentinel build_baseline (with doe-run-dir) + watch on fault window")
    b = run([PY, SENT / "scripts" / "build_baseline.py",
             "--history-csv", E2E / "sentinel" / "history.csv",
             "--doe-run-dir", E2E / "doe_run",
             "--time-col", "t",
             "--out", E2E / "sentinel" / "watch_baseline.json"])
    record(checks, "S2.baseline_exit0", b.returncode == 0, b.stderr[-300:])
    base = read_json(E2E / "sentinel" / "watch_baseline.json")
    gf = base.get("generated_from", {})
    record(checks, "S2.doe_verbatim_handoff",
           gf.get("doe_recommendations_path") is not None
           and gf.get("recommendations_contract_version") == "1.0",
           str(gf.get("recommendations_contract_version")))
    all_group = next(iter(base.get("groups", {}).values()), {})
    record(checks, "S2.operating_windows_verbatim",
           len(all_group.get("operating_windows", [])) > 0,
           f"{len(all_group.get('operating_windows', []))} windows copied")

    out_dir = E2E / "sentinel" / "out"
    w = run([PY, SENT / "scripts" / "sentinel.py", "watch",
             "--data", E2E / "sentinel" / "window_fault.csv",
             "--baseline", E2E / "sentinel" / "watch_baseline.json",
             "--time-col", "t",
             "--out-dir", out_dir])
    record(checks, "S3.watch_exit1_findings", w.returncode == 1, f"exit={w.returncode}")
    alert = read_json(out_dir / "alert.json")
    ALERT_ID_HOLDER["id"] = alert.get("alert_id")
    temp_alerts = []
    for a in alert.get("alerts", []):
        params = a.get("parameters") or ([a.get("parameter")] if a.get("parameter") else [])
        if any("temp" in str(p) for p in params) or "temp" in json.dumps(a):
            temp_alerts.append(a)
    record(checks, "S3.temp_alerts_present", len(temp_alerts) > 0,
           f"alerts={len(alert.get('alerts', []))}, temp-related={len(temp_alerts)}")
    kinds = sorted({f"{a.get('check_type')}/{a.get('rule_name')}" for a in temp_alerts})
    print(f"    temp alert kinds: {kinds}")
    onset_idx = [a.get("observed", {}).get("index") for a in temp_alerts
                 if isinstance(a.get("observed", {}).get("index"), int)
                 and a.get("check_type") != "window"]
    record(checks, "S3.post_onset_detection",
           len(onset_idx) > 0 and all(i >= 3000 for i in onset_idx),
           f"detection indexes all >= drift onset 3000: {onset_idx[:5]}")
    regime_new = (alert.get("regime_summary") or {}).get("__ALL__", {}).get(
        "new_change_points", []) if isinstance(alert.get("regime_summary"), dict) else []
    proj = alert.get("projection_summary")
    window_alerts = [a for a in temp_alerts if a.get("check_type") == "window"]
    record(checks, "S3.window_or_regime_evidence",
           bool(proj) or len(window_alerts) > 0 or len(regime_new) > 0,
           f"proj_summary={'set' if proj else 'null'} window_alerts={len(window_alerts)} "
           f"new_cps={len(regime_new)}")
    g = run(["node", SENT / "scripts" / "quality_gate.mjs",
             out_dir / "alert.json",
             "--baseline", E2E / "sentinel" / "watch_baseline.json",
             "--skill-path", SENT, "--shared-path", SHARED])
    record(checks, "S3.sentinel_gate_exit0", g.returncode == 0, (g.stdout + g.stderr)[-300:])
    return alert


# ------------------------------------------------- stage 3: fault signature
def stage3(checks, alert):
    print("[S3] fault_signature derived from sentinel alert (agent-authored input)")
    # pull temp direction + severity out of the alert
    direction, severity = "high", None
    for a in alert.get("alerts", []):
        blob = json.dumps(a)
        if "temp" in blob:
            for key in ("robust_z", "z", "z_score", "severity"):
                v = a.get(key)
                if isinstance(v, (int, float)):
                    severity = round(float(v), 3)
                    break
            break
    sig = {
        "signature_version": "1.0",
        "source_ref": alert.get("alert_id"),
        "anomalous_params": [{"parameter": "temp", "direction": direction,
                              "severity": severity}],
        "regime": {"product": PRODUCT, "machine": MACHINE, "regime_label": REGIME},
        "degraded_metric": "yield_pct",
    }
    write_json(E2E / "tune_run" / "00_input" / "fault_signature.json", sig)
    v = run(["node", SHARED / "scripts" / "validate.mjs",
             TUNE / "schemas" / "fault_signature.schema.json",
             E2E / "tune_run" / "00_input" / "fault_signature.json"])
    record(checks, "S4.signature_schema_valid", "\"valid\": true" in v.stdout, v.stdout[-200:])
    return sig


# ------------------------------------------------- stage 4: tuning-memory chain
def stage4(checks):
    print("[S4] tuning-memory: attribute -> build -> recommend -> ack -> gate")
    run_dir = E2E / "tune_run"
    logs = [
        {   # A1: alert-triggered wrong-way move (harmful) — matches B5 hit pattern
            "schema_version": "1.0",
            "ts": iso_row(2000),
            "actor": {"actor_id": "ENG-ZHANG-0091", "actor_type": "engineer",
                      "display_alias": None},
            "actions": [{"parameter": "temp", "from": 85.0, "to": 88.0, "unit": "degC"}],
            "bundled_action": {"is_bundle": False, "bundle_reason": "single", "note": None},
            "context": {"product": PRODUCT, "machine": MACHINE,
                        "regime_label": REGIME, "steady_segment_ref": None,
                        "group_key": None},
            "trigger": {"trigger_type": "alert", "ref_id": ALERT_ID_HOLDER.get("id")},
            "attribution_confounds": [],
            "recommendation_ref": None,
            "ingest_meta": {"source": "csv_import", "ingested_at": None},
        },
        {   # A2: corrective move (effective), manual
            "schema_version": "1.0",
            "ts": iso_row(4000),
            "actor": {"actor_id": "ENG-ZHANG-0091", "actor_type": "engineer",
                      "display_alias": None},
            "actions": [{"parameter": "temp", "from": 88.0, "to": 84.0, "unit": "degC"}],
            "bundled_action": {"is_bundle": False, "bundle_reason": "single", "note": None},
            "context": {"product": PRODUCT, "machine": MACHINE,
                        "regime_label": REGIME, "steady_segment_ref": None,
                        "group_key": None},
            "trigger": {"trigger_type": "manual", "ref_id": None},
            "attribution_confounds": [],
            "recommendation_ref": None,
            "ingest_meta": {"source": "csv_import", "ingested_at": None},
        },
    ]
    write_json(run_dir / "00_input" / "action_log.json", logs)
    write_json(run_dir / "00_input" / "actor_alias_map.json", {"ENG-ZHANG-0091": "eng_03"})

    t = run([PY, TUNE / "scripts" / "tune_stats.py", "attribute",
             "--run-dir", run_dir, "--time-col", "t", "--metric", "yield_pct"])
    record(checks, "S5.tune_exit0", t.returncode == 0, t.stderr[-300:])
    deltas = {}
    for f in sorted((run_dir / "06_experience" / "attribution").glob("*.json")):
        rep = read_json(f)
        eff = (rep.get("effect") or {})
        deltas[rep.get("action_log_id") or f.stem] = (
            rep.get("attribution_status"), eff.get("delta"))
    print(f"    attribution deltas: {deltas}")
    est = [d for d in deltas.values() if d[0] == "estimable"]
    record(checks, "S5.both_estimable", len(est) == 2, str(deltas))
    neg = [d for d in deltas.values() if d[0] == "estimable" and (d[1] or 0) < 0]
    pos = [d for d in deltas.values() if d[0] == "estimable" and (d[1] or 0) > 0]
    record(checks, "S5.a1_harmful_a2_effective", len(neg) >= 1 and len(pos) >= 1,
           f"neg={len(neg)} pos={len(pos)}")

    b = run(["node", TUNE / "scripts" / "experience_build.mjs", "build",
             "--run-dir", run_dir,
             "--alias-map", "00_input/actor_alias_map.json"])
    record(checks, "S6.build_exit0", b.returncode == 0, b.stderr[-300:])
    store_path = run_dir / "06_experience" / "tuning_experience.jsonl"
    store = [json.loads(l) for l in store_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    types = {}
    for e in store:
        types[e["experience_type"]] = types.get(e["experience_type"], 0) + 1
    record(checks, "S6.recipe_entry_created",
           types.get("fault_control_recipe", 0) >= 1, str(types))
    record(checks, "S6.privacy_alias", all(
        e.get("provenance", {}).get("actor_alias") == "eng_03" for e in store
        if e.get("provenance")), "alias=eng_03")

    m = run(["node", TUNE / "scripts" / "match_playbook.mjs", "recommend",
             "--run-dir", run_dir,
             "--signature", "00_input/fault_signature.json"])
    record(checks, "S7.recommend_exit0", m.returncode == 0, m.stderr[-300:])
    rec = read_json(run_dir / "conclusions" / "recommendation.json")
    record(checks, "S7.playbook_hit", rec.get("recommendation_status") == "playbook_hit",
           rec.get("recommendation_status"))
    pbs = rec.get("playbooks", [])
    record(checks, "S7.score_ge_threshold",
           len(pbs) >= 1 and (pbs[0].get("match_score") or 0) >= 0.55,
           str(pbs[0].get("match_score") if pbs else None))
    record(checks, "S7.autonomy_null_carrier",
           all(pb.get("autonomy_level", "missing") is None for pb in pbs),
           "AWS-side dispatch policy carrier stays null")
    record(checks, "S7.match_scope",
           rec.get("match_scope") in ("regime", "product", "machine", "generic"),
           rec.get("match_scope"))

    # execution receipt (AWS-side ack simulation)
    ack = {"recommendation_id": rec.get("recommendation_id"),
           "status": "executed", "executed_action_log_id": "LOG-E2E-0001"}
    write_json(run_dir / "00_input" / "ack-20261001-0001.json", ack)
    a = run(["node", TUNE / "scripts" / "match_playbook.mjs", "ack",
             "--run-dir", run_dir,
             "--ack-file", "00_input/ack-20261001-0001.json"])
    record(checks, "S7.ack_exit0", a.returncode == 0, a.stderr[-300:])

    g = run(["node", TUNE / "scripts" / "quality_gate.mjs", run_dir,
             "--skill-path", TUNE, "--shared-path", SHARED,
             "--alias-map", "00_input/actor_alias_map.json"])
    record(checks, "S7.tuning_gate_exit0", g.returncode == 0, (g.stdout + g.stderr)[-400:])
    return rec


# ------------------------------------------------ stage 5: optimizer campaign
def stage5(checks):
    print("[S5] optimizer-loop campaign (simulated plant trials, 3 replicates)")
    run_dir = E2E / "opt_run"
    objective = {
        "contract_version": "1.0",
        "campaign_id": "OPT-20261001-001",
        "target_metric": "yield_pct",
        "goal": "target",
        "target_range": [98.0, 100.2],
        "factors": [
            {"name": "temp", "type": "numeric", "min": 82.0, "max": 88.0, "unit": "degC"},
            {"name": "press", "type": "numeric", "min": 0.55, "max": 0.65, "unit": "MPa"},
        ],
        "budget": {"max_rounds": 10, "max_trials": 30},
        "noise": {"replicates_for_sigma": 3},
        "seed": 7,
    }
    write_json(run_dir / "00_input" / "objective.json", objective)
    r = run([PY, OPT / "scripts" / "optimizer.py", "init", "--run-dir", run_dir])
    record(checks, "S8.init_exit0", r.returncode == 0, r.stderr[-300:])

    rng = np.random.default_rng(99)
    order = ["temp", "press"]
    n_rounds, phase = 0, "designing"
    for i in range(1, 15):
        rid = f"R{i:03d}"
        d = run([PY, OPT / "scripts" / "optimizer.py", "design", "--run-dir", run_dir])
        if d.returncode != 0:
            record(checks, "S8.design_exit0", False, d.stderr[-300:])
            return None
        design = read_json(run_dir / "02_rounds" / rid / "trial_design.json")
        trials_out = []
        for tr in design["trials"]:
            sp = tr["setpoints"]
            reps = tr.get("replicates") or 1
            vals = [round(float(plant(sp[order[0]], sp[order[1]]) + rng.normal(0, 0.3)), 4)
                    for _ in range(reps)]
            trials_out.append({"trial_id": tr["trial_id"], "status": "completed",
                               "measurements": {"yield_pct": vals}})
        write_json(run_dir / "02_rounds" / rid / "trial_result.json", {
            "result_version": "1.0", "campaign_id": objective["campaign_id"],
            "round_id": rid, "trials": trials_out})
        ing = run([PY, OPT / "scripts" / "optimizer.py", "ingest", "--run-dir", run_dir])
        if ing.returncode != 0:
            record(checks, "S8.ingest_exit0", False, ing.stderr[-300:])
            return None
        n_rounds = i
        phase = read_json(run_dir / "01_state" / "optimizer_state.json")["phase"]
        if phase in ("converged", "paused", "exhausted", "aborted"):
            break
    record(checks, "S8.terminal_phase_reached",
           phase in ("converged", "exhausted"), f"phase={phase} rounds={n_rounds}")

    c = run([PY, OPT / "scripts" / "optimizer.py", "converge", "--run-dir", run_dir])
    record(checks, "S8.converge_exit0", c.returncode == 0, c.stderr[-300:])
    recipe = read_json(run_dir / "conclusions" / "recipe.json")
    record(checks, "S9.recipe_exists", recipe is not None, "conclusions/recipe.json")
    # goal=target semantics: convergence = achieved yield inside target_range
    # (NOT the global plant max — target objectives settle at the first
    # in-range setpoint the confirm gate verifies)
    fs = (recipe or {}).get("final_setpoints") or {}
    ach = (recipe or {}).get("achieved") or {}
    ach_mean = (ach.get("yield_pct") or {}).get("mean") if isinstance(ach, dict) else None
    record(checks, "S9.setpoints_in_domain",
           82.0 <= (fs.get("temp") or 0) <= 88.0 and 0.55 <= (fs.get("press") or 0) <= 0.65,
           f"final_setpoints={fs}")
    record(checks, "S9.achieved_in_target_range",
           ach_mean is not None and 98.0 <= ach_mean <= 100.2,
           f"achieved={ach_mean} target=[98.0,100.2]")
    record(checks, "S9.verification_converged",
           (recipe or {}).get("verification_status") in ("converged", "confirmed", "verified"),
           str((recipe or {}).get("verification_status")))
    six = ["conclusions/optimization_conclusion.json", "conclusions/recipe.json",
           "report.md", "06_experience/experience_candidates.jsonl",
           "06_experience/kb_summary.md", "01_state/optimizer_state.json"]
    missing = [f for f in six if not (run_dir / f).exists()]
    record(checks, "S9.six_artifacts", not missing, f"missing={missing}")
    g = run(["node", OPT / "scripts" / "optimizer_gate.mjs", run_dir,
             "--skill-path", OPT, "--shared-path", SHARED])
    record(checks, "S9.optimizer_gate_exit0", g.returncode == 0, (g.stdout + g.stderr)[-400:])
    return recipe


# --------------------------------------- stage 6: feedback -> recipe into store
def stage6(checks, recommendation):
    print("[S6] feedback: recommendation executed effectively -> corroboration+1")
    run_dir = E2E / "tune_run"
    pbs = (recommendation or {}).get("playbooks", [])
    chunk_id = pbs[0].get("experience_id") if pbs else None
    record(checks, "S10.chunk_id_available", bool(chunk_id), str(chunk_id))
    if not chunk_id:
        return
    f = run(["node", TUNE / "scripts" / "experience_build.mjs", "feedback",
             "--run-dir", run_dir, "--chunk-id", chunk_id,
             "--result", "effective", "--note", "T4 e2e: optimizer recipe confirmed effective"])
    record(checks, "S10.feedback_exit0", f.returncode == 0, f.stderr[-300:])
    store = [json.loads(l) for l in
             (run_dir / "06_experience" / "tuning_experience.jsonl")
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    ent = next((e for e in store if e["chunk_id"] == chunk_id), None)
    grade_after = (ent or {}).get("evidence_grade")
    corr_count = (ent or {}).get("corroboration_count", 0)
    record(checks, "S10.corroboration_promotes_grade",
           ent is not None and (grade_after == "E2" or corr_count >= 1),
           f"grade_after_feedback={grade_after} corroboration_count={corr_count}")
    # protocol: after feedback the stale recommendation.json must be refreshed
    # by RE-RUNNING recommend (fix = re-run script step), then the gate passes T7
    m2 = run(["node", TUNE / "scripts" / "match_playbook.mjs", "recommend",
              "--run-dir", run_dir,
              "--signature", "00_input/fault_signature.json"])
    record(checks, "S10.recommend_refresh_exit0", m2.returncode == 0, m2.stderr[-300:])
    rec2 = read_json(run_dir / "conclusions" / "recommendation.json")
    pb2 = (rec2.get("playbooks") or [{}])[0]
    record(checks, "S10.refreshed_rec_shows_promotion",
           pb2.get("evidence_grade") == grade_after,
           f"rec_grade={pb2.get('evidence_grade')} store_grade={grade_after}")
    kb = (run_dir / "06_experience" / "kb_summary.md").read_text(encoding="utf-8")
    record(checks, "S10.kb_summary_has_regime", f"regime_key: `{PRODUCT}|{MACHINE}|{REGIME}`" in kb,
           "kb_summary.md")
    g = run(["node", TUNE / "scripts" / "quality_gate.mjs", run_dir,
             "--skill-path", TUNE, "--shared-path", SHARED,
             "--alias-map", "00_input/actor_alias_map.json"])
    record(checks, "S10.final_gate_exit0", g.returncode == 0, (g.stdout + g.stderr)[-400:])


def main():
    t0 = time.time()
    checks = []
    stage0()
    stage1(checks)
    alert = stage2(checks)
    stage3(checks, alert)
    rec = stage4(checks)
    stage5(checks)
    stage6(checks, rec)
    dt = time.time() - t0
    npass = sum(1 for _, ok, _ in checks if ok)
    print("\n" + "=" * 62)
    for name, ok, detail in checks:
        if not ok:
            print(f"  FAIL  {name}  {detail}")
    print(f"[T4-E2E] {npass}/{len(checks)} checks passed in {dt:.1f}s — "
          f"{'ALL GREEN' if npass == len(checks) else 'FAILURES PRESENT'}")
    sys.exit(0 if npass == len(checks) else 1)


if __name__ == "__main__":
    main()
