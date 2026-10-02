#!/usr/bin/env python
"""Test runner for industrial-tuning-memory (plan AC group B, B1-B14).

Usage (from repo root, inside the uv venv):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-tuning-memory/tests/run_tests.py [case|all]

All fixtures are synthetic time series with fixed seeds (numpy default_rng).
AC definitions live in tests/AC.md — each case below names the AC it proves.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
SHARED = REPO / ".claude" / "shared"
DOE_SCRIPTS = REPO / ".claude" / "skills" / "industrial-doe-analyzer" / "scripts"
sys.path.insert(0, str(DOE_SCRIPTS))
from doestats._stats_util import effective_n, lag1_autocorr, welch_delta_ci  # noqa: E402

FIXTURES = (HERE / "fixtures").resolve()
BASE_TS = datetime(2026, 1, 15)
RESULTS = []


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def make_run(name):
    safe = Path(str(name)).name
    run_dir = (FIXTURES / safe / "run").resolve()
    if FIXTURES not in run_dir.parents:
        raise ValueError(f"fixture path escaped fixtures root: {name}")
    (run_dir / "00_input").mkdir(parents=True, exist_ok=True)
    return run_dir


def iso(i):
    return (BASE_TS + timedelta(seconds=int(i))).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_tsdata(run_dir, n, cols, seed, steps, phi=0.0, sigma=0.3, base=50.0):
    """Synthetic time-ordered frame. cols: {name: (base_level, sd)}; steps:
    {col: [(row, delta), ...]} — level shifts applied from `row` onward."""
    rng = np.random.default_rng(seed)
    data = {"t": [iso(i) for i in range(n)]}
    innov = {c: rng.normal(0, s, n) for c, (_, s) in cols.items()}
    for c, (level, _) in cols.items():
        x = np.empty(n)
        x[0] = innov[c][0]
        for i in range(1, n):
            x[i] = phi * x[i - 1] + innov[c][i]
        if phi > 0:  # normalize AR(1) stationary sd to the requested sigma
            x = x * (sigma / max(x.std(ddof=1), 1e-12))
        x = x + level
        for row, delta in steps.get(c, []):
            x[int(row):] += delta
        data[c] = np.round(x, 6)
    df = pd.DataFrame(data)
    df.to_csv(run_dir / "00_input" / "data.csv", index=False)
    return df


def base_log(ts, actions, actor_id="ENG-ZHANG-0091", actor_type="engineer",
             product="P1", machine="M1", regime="R1", trigger=None, confounds=None,
             bundle=None, outcome=None, source=None):
    log = {
        "schema_version": "1.0",
        "ts": ts,
        "actor": {"actor_id": actor_id, "actor_type": actor_type, "display_alias": None},
        "actions": actions,
        "bundled_action": bundle or {"is_bundle": False, "bundle_reason": "single", "note": None},
        "context": {"product": product, "machine": machine, "regime_label": regime,
                    "steady_segment_ref": None, "group_key": None},
        "attribution_confounds": confounds or [],
        "recommendation_ref": None,
        "ingest_meta": {"source": source, "ingested_at": None},
    }
    if trigger:
        log["trigger"] = trigger
    if outcome:
        log["outcome"] = outcome
    return log


def write_logs(run_dir, logs, name="00_input/action_log.json"):
    p = run_dir / name
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = logs if isinstance(logs, list) else [logs]
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run_tune(run_dir, metric, extra=()):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "tune_stats.py"), "attribute",
         "--run-dir", str(run_dir), "--metric", metric, *extra],
        capture_output=True, text=True, timeout=600, shell=False)


def run_py(script, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, timeout=600, shell=False)


def run_node(script, *args):
    return subprocess.run(
        ["node", str(SCRIPTS / script), *args],
        capture_output=True, text=True, timeout=300, shell=False)


def run_build(run_dir, *extra):
    return run_node("experience_build.mjs", "build", "--run-dir", str(run_dir), *extra)


def run_gate(run_dir, *extra):
    return subprocess.run(
        ["node", str(SCRIPTS / "quality_gate.mjs"), str(run_dir),
         "--skill-path", str(SKILL), "--shared-path", str(SHARED), *extra],
        capture_output=True, text=True, timeout=300, shell=False)


def read(run_dir, rel):
    return json.loads((Path(run_dir) / rel).read_text(encoding="utf-8"))


def read_store(run_dir):
    p = Path(run_dir) / "06_experience" / "tuning_experience.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def hand_neff_welch(hi, lo, rho_hi=None, rho_lo=None):
    """Independent re-implementation from doestats primitives (the 'manual'
    reference for B2/B6): AR(1)-adjusted Welch delta + CI. rho_* default to the
    series' own lag-1; layers pass the parent-segment rho (documented contract)."""
    hi = np.asarray(hi, dtype=float)
    lo = np.asarray(lo, dtype=float)
    hi = hi[~np.isnan(hi)]
    lo = lo[~np.isnan(lo)]
    if rho_hi is None:
        rho_hi = lag1_autocorr(hi)
    if rho_lo is None:
        rho_lo = lag1_autocorr(lo)
    n_hi = max(int(effective_n(hi.size, rho_hi)), 2) if rho_hi is not None else hi.size
    n_lo = max(int(effective_n(lo.size, rho_lo)), 2) if rho_lo is not None else lo.size
    v_hi = hi.var(ddof=1) / n_hi
    v_lo = lo.var(ddof=1) / n_lo
    se = float(np.sqrt(v_hi + v_lo))
    df = (v_hi + v_lo) ** 2 / max((v_hi ** 2) / (n_hi - 1) + (v_lo ** 2) / (n_lo - 1), 1e-300)
    from scipy import stats as sps
    t_crit = float(sps.t.ppf(0.975, df))
    delta = float(hi.mean() - lo.mean())
    return delta, (delta - t_crit * se, delta + t_crit * se), int(n_hi), int(n_lo)


def clean_artifacts():
    """Keep fixture inputs; drop generated run artifacts (like doe-analyzer)."""
    import shutil
    if not FIXTURES.exists():
        return
    for run in FIXTURES.glob("*/run"):
        shutil.rmtree(run / "06_experience", ignore_errors=True)
        shutil.rmtree(run / "conclusions", ignore_errors=True)


# ------------------------------------------------------------------ cases

def case_b1():
    print("== B1: invalid action_log rejected batch-wise; replay of same id is idempotent ==")
    run = make_run("B1")
    write_tsdata(run, 600, {"temp": (50.0, 0.3), "y": (50.0, 0.3)}, 42,
                 {"temp": [(300, 2.5)], "y": [(300, 2.5)]})
    ok_log = base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}])
    bad_log = {"schema_version": "1.0", "ts": iso(300),
               "actor": {"actor_id": "X", "actor_type": "wizard", "display_alias": None},
               "actions": [{"parameter": "temp", "from": 50.0, "unit": "degC"}],  # missing `to`
               "context": {"product": "P1", "machine": "M1", "regime_label": "R1"}}
    write_logs(run, [ok_log, bad_log])
    proc = run_build(run)
    record("B1.invalid_batch_rejected_exit3", proc.returncode == 3,
           f"rc={proc.returncode} out={proc.stdout[-200:]} err={proc.stderr[-300:]}")
    record("B1.nothing_persisted", not (run / "06_experience" / "tuning_experience.jsonl").exists(),
           "store written despite rejection")
    gate = run_gate(run)
    record("B1.gate_schema_rejects_invalid", gate.returncode == 1 and "T2" in gate.stdout,
           f"rc={gate.returncode} out={gate.stdout[-300:]}")

    # valid replay: same content, same derived id -> second build is a no-op
    run2 = make_run("B1b")
    write_tsdata(run2, 600, {"temp": (50.0, 0.3), "y": (50.0, 0.3)}, 42,
                 {"temp": [(300, 2.5)], "y": [(300, 2.5)]})
    write_logs(run2, ok_log)
    record("B1.tune_exit0", run_tune(run2, "y").returncode == 0, "")
    first = run_build(run2)
    record("B1.build_exit0", first.returncode == 0, first.stderr[-300:])
    store1 = read_store(run2)
    second = run_build(run2)
    store2 = read_store(run2)
    record("B1.replay_exit0", second.returncode == 0, second.stderr[-300:])
    record("B1.replay_idempotent_noop", "idempotent_noop" in second.stdout,
           second.stdout[-300:])
    record("B1.replay_no_new_entry", len(store1) == len(store2) == 1,
           f"{len(store1)} vs {len(store2)}")
    record("B1.replay_counters_unchanged",
           store1[0]["corroboration_count"] == store2[0]["corroboration_count"] == 1, "")
    record("B1.gate_exit0", run_gate(run2).returncode == 0, "")


def case_b2():
    print("== B2: tune_stats welch path identical to manual welch_delta_ci (1e-9); n_eff enters ==")
    # (a) identity fixture: smooth ramp -> lag1 rho >= 0.99 -> effective_n returns n,
    #     so the n_eff-adjusted welch must be byte-identical to doestats.welch_delta_ci
    run = make_run("B2")
    n = 600
    rng = np.random.default_rng(42)
    y = 0.01 * np.arange(n) + rng.normal(0, 0.0005, n)
    df = pd.DataFrame({"t": [iso(i) for i in range(n)], "y": np.round(y, 9)})
    df.to_csv(run / "00_input" / "data.csv", index=False)
    write_logs(run, base_log(iso(300), [{"parameter": "temp", "from": 0.0, "to": 1.0, "unit": "x"}]))
    proc = run_tune(run, "y")
    record("B2.tune_exit0", proc.returncode == 0, proc.stderr[-300:])
    rep = next((run / "06_experience" / "attribution").glob("*.json"))
    r = json.loads(rep.read_text(encoding="utf-8"))
    seg_b = r["segments"]["baseline"]
    seg_e = r["segments"]["effect"]
    record("B2.precond_rho_above_0.99",
           (seg_b["lag1_autocorr"] or 0) >= 0.99 and (seg_e["lag1_autocorr"] or 0) >= 0.99,
           f"rho_b={seg_b['lag1_autocorr']} rho_e={seg_e['lag1_autocorr']}")
    record("B2.precond_neff_equals_n",
           seg_e["n_eff"] == seg_e["n"] and seg_b["n_eff"] == seg_b["n"],
           f"n_eff={seg_e['n_eff']} n={seg_e['n']}")
    lo = pd.to_numeric(df["y"]).to_numpy()
    base_vals = lo[seg_b["row_range"][0]:seg_b["row_range"][1]]
    eff_vals = lo[seg_e["row_range"][0]:seg_e["row_range"][1]]
    delta, ci_lo, ci_hi, n_hi, n_lo = welch_delta_ci(eff_vals, base_vals)
    record("B2.delta_matches_welch_1e-9", abs(r["effect"]["delta"] - delta) <= 1e-9,
           f"report={r['effect']['delta']} manual={delta}")
    record("B2.ci_matches_welch_1e-9",
           abs(r["effect"]["ci95"][0] - ci_lo) <= 1e-9 and abs(r["effect"]["ci95"][1] - ci_hi) <= 1e-9,
           f"report={r['effect']['ci95']} manual={[ci_lo, ci_hi]}")

    # (b) n_eff really enters: AR(1) phi=0.5 -> n_eff < n and CI strictly wider
    run_b = make_run("B2b")
    write_tsdata(run_b, 600, {"y": (50.0, 0.3)}, 7, {"y": [(300, 2.0)]}, phi=0.5, sigma=0.3)
    write_logs(run_b, base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 52.0, "unit": "degC"}]))
    record("B2b.tune_exit0", run_tune(run_b, "y").returncode == 0, "")
    rep_b = next((run_b / "06_experience" / "attribution").glob("*.json"))
    rb = json.loads(rep_b.read_text(encoding="utf-8"))
    y2 = pd.to_numeric(pd.read_csv(run_b / "00_input" / "data.csv")["y"]).to_numpy()
    bv = y2[rb["segments"]["baseline"]["row_range"][0]:rb["segments"]["baseline"]["row_range"][1]]
    ev = y2[rb["segments"]["effect"]["row_range"][0]:rb["segments"]["effect"]["row_range"][1]]
    _, nlo, nhi, _, _ = welch_delta_ci(ev, bv)
    record("B2b.neff_below_n", rb["effect"]["n_eff_hi"] < len(ev),
           f"n_eff={rb['effect']['n_eff_hi']} n={len(ev)}")
    record("B2b.ci_wider_than_naive",
           rb["effect"]["ci95"][0] < nlo and rb["effect"]["ci95"][1] > nhi,
           f"report={rb['effect']['ci95']} naive={[nlo, nhi]}")
    record("B2b.delta_identical", abs(rb["effect"]["delta"] - float(np.mean(ev) - np.mean(bv))) <= 1e-12, "")
    record("B2b.gate_exit0", run_gate(run_b).returncode == 0, "")

    # (c) trend confound: shared rising ramp -> detrending shrinks |delta| >= 0.3 -> CAUTION
    run_c = make_run("B2c")
    rng_c = np.random.default_rng(99)
    n_c = 600
    y_c = 50.0 + 0.05 * np.arange(n_c) + 0.5 * (np.arange(n_c) >= 300) \
        + rng_c.normal(0, 0.2, n_c)
    pd.DataFrame({"t": [iso(i) for i in range(n_c)], "y": np.round(y_c, 6)}).to_csv(
        run_c / "00_input" / "data.csv", index=False)
    write_logs(run_c, base_log(iso(300), [{"parameter": "feed", "from": 1.0, "to": 1.1, "unit": "t/h"}]))
    record("B2c.tune_exit0", run_tune(run_c, "y").returncode == 0, "")
    rc = json.loads(next((run_c / "06_experience" / "attribution").glob("*.json"))
                    .read_text(encoding="utf-8"))
    record("B2c.trend_caution", rc["anti_spurious"]["trend_check"] == "CAUTION",
           str(rc["anti_spurious"]))
    record("B2c.status_still_estimable", rc["attribution_status"] == "estimable"
           and rc["evidence_grade"] == "E1", rc["attribution_status"])


def case_b3():
    print("== B3: not_estimable carries reason_code and effect=null (honest null) ==")
    run = make_run("B3")
    write_tsdata(run, 15, {"y": (50.0, 0.3)}, 11, {"y": [(8, 1.0)]})
    write_logs(run, base_log(iso(8), [{"parameter": "temp", "from": 50.0, "to": 51.0, "unit": "degC"}]))
    proc = run_tune(run, "y")
    record("B3.tune_exit0", proc.returncode == 0, proc.stderr[-300:])
    rep = next((run / "06_experience" / "attribution").glob("*.json"))
    r = json.loads(rep.read_text(encoding="utf-8"))
    record("B3.status_not_estimable", r["attribution_status"] == "not_estimable", r["attribution_status"])
    record("B3.reason_min_points", r["reason_code"] == "min_points", str(r["reason_code"]))
    record("B3.effect_is_null", r["effect"] is None, str(r["effect"]))
    record("B3.baseline_n_below_10", r["segments"]["baseline"]["n"] < 10,
           str(r["segments"]["baseline"]["n"]))
    # build must refuse admission (honest), store stays empty, gate still green
    b = run_build(run)
    record("B3.build_admission_skip", b.returncode == 0 and "not_estimable (admission rule)" in b.stdout,
           b.stdout[-300:])
    record("B3.store_empty", len(read_store(run)) == 0, "")
    record("B3.gate_exit0", run_gate(run).returncode == 0, "")

    # (b) outlier-driven delta: single extreme baseline point flips the LOO delta
    run_b = make_run("B3b")
    n_b = 40
    y_b = np.full(n_b, 50.0)
    y_b[5] = 30.0  # the single leveraged point below
    pd.DataFrame({"t": [iso(i) for i in range(n_b)], "y": y_b}).to_csv(
        run_b / "00_input" / "data.csv", index=False)
    write_logs(run_b, base_log(iso(20), [{"parameter": "temp", "from": 50.0, "to": 51.0, "unit": "degC"}]))
    record("B3b.tune_exit0", run_tune(run_b, "y").returncode == 0, "")
    r_b = json.loads(next((run_b / "06_experience" / "attribution").glob("*.json"))
                     .read_text(encoding="utf-8"))
    record("B3b.outlier_check_fail", r_b["anti_spurious"]["outlier_check"] == "FAIL",
           str(r_b["anti_spurious"]))
    record("B3b.reason_outlier_driven", r_b["attribution_status"] == "not_estimable"
           and r_b["reason_code"] == "outlier_driven" and r_b["effect"] is None,
           f"{r_b['attribution_status']}/{r_b['reason_code']}")
    record("B3b.gate_exit0", run_gate(run_b).returncode == 0, "")


def case_b4():
    print("== B4: store slots by regime_key; same regime resubmission corroborates +1; recipe entry ==")
    run = make_run("B4")
    write_tsdata(run, 900, {"temp": (50.0, 0.3), "y": (50.0, 0.3)}, 5,
                 {"temp": [(100, 2.5), (300, 2.5), (500, 2.5)],
                  "y": [(100, 2.5), (300, 2.5), (500, 2.5)]})
    act = [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}]
    logs = [
        base_log(iso(100), act, trigger={"trigger_type": "alert", "ref_id": "alert-001"}),
        base_log(iso(300), act),
        base_log(iso(500), act, product="P2"),
    ]
    write_logs(run, logs)
    write_json(run / "00_input" / "fault_signature.json", {
        "signature_version": "1.0", "source_ref": "alert-001",
        "anomalous_params": [{"parameter": "temp", "direction": "high", "severity": 2.0}],
        "regime": {"product": "P1", "machine": "M1", "regime_label": "R1"},
        "degraded_metric": "y"})
    write_json(run / "00_input" / "actor_alias_map.json", {"ENG-ZHANG-0091": "eng_03"})
    record("B4.tune_exit0", run_tune(run, "y").returncode == 0, "")
    b = run_build(run, "--alias-map", "00_input/actor_alias_map.json")
    record("B4.build_exit0", b.returncode == 0, b.stderr[-400:])
    store = read_store(run)
    tuning = [e for e in store if e["experience_type"] == "tuning_action_effect"]
    recipes = [e for e in store if e["experience_type"] == "fault_control_recipe"]
    record("B4.three_entries", len(store) == 3, f"{[e['chunk_id'] for e in store]}")
    reg_keys = sorted({e["regime_key"] for e in tuning})
    record("B4.regime_slots", reg_keys == ["P1|M1|R1", "P2|M1|R1"], str(reg_keys))
    chunk_p1 = next(e for e in tuning if e["regime_key"] == "P1|M1|R1")
    chunk_p2 = next(e for e in tuning if e["regime_key"] == "P2|M1|R1")
    record("B4.corroboration_plus_1", chunk_p1["corroboration_count"] == 2,
           str(chunk_p1["corroboration_count"]))
    record("B4.e2_promotion", chunk_p1["evidence_grade"] == "E2"
           and chunk_p1["confidence_label"] == "verified",
           f"{chunk_p1['evidence_grade']}/{chunk_p1['confidence_label']}")
    record("B4.cross_regime_ids_differ", chunk_p1["chunk_id"] != chunk_p2["chunk_id"], "")
    record("B4.chunk_id_pattern",
           chunk_p1["chunk_id"].startswith("exp_tuning_action_effect_P1|M1|R1"), chunk_p1["chunk_id"])
    record("B4.cross_regime_not_yet_consistent", chunk_p1["cross_regime_consistent"] is False, "")
    record("B4.recipe_present", len(recipes) == 1, str(len(recipes)))
    if recipes:
        seq = recipes[0]["payload"]["action_sequence"]
        record("B4.recipe_step_order", seq and seq[0]["step_order"] == 1, str(seq))
        record("B4.recipe_expected_effect",
               recipes[0]["payload"]["action_sequence"][0]["expected_effect"]["delta"] is not None, "")
        record("B4.recipe_has_fault_signature",
               (recipes[0]["payload"]["fault_signature"] or {}).get("anomalous_params") is not None, "")
    # corroboration on chunk2 -> both E2, same direction -> E3 cross-regime
    f = run_node("experience_build.mjs", "feedback", "--run-dir", str(run),
                 "--chunk-id", chunk_p2["chunk_id"], "--result", "effective")
    record("B4.feedback_effective_exit0", f.returncode == 0, f.stderr[-300:])
    store = read_store(run)
    p1 = next(e for e in store if e["chunk_id"] == chunk_p1["chunk_id"])
    p2 = next(e for e in store if e["chunk_id"] == chunk_p2["chunk_id"])
    record("B4.e3_cross_regime", p1["evidence_grade"] == "E3" and p2["evidence_grade"] == "E3",
           f"{p1['evidence_grade']}/{p2['evidence_grade']}")
    record("B4.cross_regime_consistent_flag", p1["cross_regime_consistent"] is True, "")
    record("B4.privacy_alias_in_store", p1["provenance"]["actor_alias"] == "eng_03",
           str(p1["provenance"]["actor_alias"]))
    record("B4.kb_summary_exists", (run / "06_experience" / "kb_summary.md").exists(), "")
    kb = (run / "06_experience" / "kb_summary.md").read_text(encoding="utf-8")
    record("B4.kb_regime_heading", "regime_key: `P1|M1|R1`" in kb and "regime_key: `P2|M1|R1`" in kb, "")
    record("B4.state_ledger_exists", (run / "06_experience" / "accumulated" / "state.json").exists(), "")
    record("B4.gate_exit0", run_gate(run).returncode == 0, "")


def case_b5():
    print("== B5: recommend returns a playbook (E1, advisory), threshold/scope correct ==")
    run = make_run("B5")
    write_tsdata(run, 600, {"temp": (50.0, 0.3), "y": (50.0, 0.3)}, 9,
                 {"temp": [(300, 2.5)], "y": [(300, 2.5)]})
    write_logs(run, base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}]))
    write_json(run / "00_input" / "fault_signature.json", {
        "signature_version": "1.0", "source_ref": "alert-777",
        "anomalous_params": [{"parameter": "temp", "direction": "high", "severity": 3.1}],
        "regime": {"product": "P1", "machine": "M1", "regime_label": "R1"},
        "degraded_metric": "y"})
    write_json(run / "00_input" / "actor_alias_map.json", {"ENG-ZHANG-0091": "eng_03"})
    record("B5.tune_exit0", run_tune(run, "y").returncode == 0, "")
    b = run_build(run, "--alias-map", "00_input/actor_alias_map.json")
    record("B5.build_exit0", b.returncode == 0, b.stderr[-300:])
    m = run_node("match_playbook.mjs", "recommend", "--run-dir", str(run))
    record("B5.recommend_exit0", m.returncode == 0, m.stderr[-300:])
    rec = read(run, "conclusions/recommendation.json")
    record("B5.status_playbook_hit", rec["recommendation_status"] == "playbook_hit",
           rec["recommendation_status"])
    record("B5.scope_regime", rec["match_scope"] == "regime", str(rec["match_scope"]))
    record("B5.playbook_present", len(rec["playbooks"]) >= 1, "")
    pb = rec["playbooks"][0]
    record("B5.score_ge_threshold", (pb["match_score"] or 0) >= 0.55, str(pb["match_score"]))
    record("B5.evidence_advisory", pb["evidence_grade"] in ("E1", "E2", "E3"), pb["evidence_grade"])
    record("B5.provenance_alias", pb["provenance_alias"] == "eng_03", str(pb["provenance_alias"]))
    record("B5.id_pattern", rec["recommendation_id"].startswith("REC-2")
           and len(rec["recommendation_id"].split("-")) == 4, rec["recommendation_id"])
    record("B5.autonomy_null_carrier", rec["playbooks"][0].get("autonomy_level", "missing") is None,
           "v1.4: frozen contract keeps the key, IDD always writes null")
    record("B5.gate_exit0", run_gate(run, "--alias-map", "00_input/actor_alias_map.json").returncode == 0, "")


def case_b6():
    print("== B6: stratified attribution matches hand formula (1e-9); layers <20 skipped+counted ==")
    run = make_run("B6")
    n = 600
    rng = np.random.default_rng(21)
    t = [iso(i) for i in range(n)]
    shift = ["A" if i % 2 == 0 else "B" for i in range(n)]
    for i in range(280, 292):
        shift[i] = "C"  # tiny layer inside the baseline window -> must be skipped
    noise = rng.normal(0, 0.4, n)
    y = 50.0 + noise + np.where(np.arange(n) >= 300, 0.0, 0.0)
    y = np.where((np.arange(n) >= 300) & (np.asarray(shift) == "A"), y + 1.0, y)
    y = np.where((np.arange(n) >= 300) & (np.asarray(shift) == "B"), y + 3.0, y)
    df = pd.DataFrame({"t": t, "shift": shift, "y": np.round(y, 6)})
    df.to_csv(run / "00_input" / "data.csv", index=False)
    write_logs(run, base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 51.0, "unit": "degC"}]))
    proc = run_tune(run, "y", ["--group-key", "shift"])
    record("B6.tune_exit0", proc.returncode == 0, proc.stderr[-400:])
    rep = next((run / "06_experience" / "attribution").glob("*.json"))
    r = json.loads(rep.read_text(encoding="utf-8"))
    layers = {l["group"]: l for l in (r["effect"]["stratified"] or [])}
    record("B6.layers_present", set(layers) == {"A", "B", "C"}, str(sorted(layers)))
    record("B6.tiny_layer_skipped_counted",
           layers["C"]["skipped"] is True and layers["C"]["delta"] is None
           and layers["C"]["n"] == 12, str(layers.get("C")))
    record("B6.a_layer_estimable", layers["A"]["skipped"] is False
           and layers["A"]["delta"] is not None, str(layers.get("A")))
    yv = pd.to_numeric(df["y"]).to_numpy()
    sv = np.asarray(df["shift"])
    br = r["segments"]["baseline"]["row_range"]
    er = r["segments"]["effect"]["row_range"]
    rho_b = r["segments"]["baseline"]["lag1_autocorr"]
    rho_e = r["segments"]["effect"]["lag1_autocorr"]
    # hand-check each estimable layer + the weighted aggregation formula
    # (layers inherit the parent-segment lag-1 rho — documented in attribution_method §4)
    ok_layers = True
    acc = []  # (n_layer, delta, ci) per estimable layer, from the HAND reference
    for g in ("A", "B"):
        m_b = sv[br[0]:br[1]] == g
        m_e = sv[er[0]:er[1]] == g
        d, ci, _, _ = hand_neff_welch(yv[er[0]:er[1]][m_e], yv[br[0]:br[1]][m_b],
                                      rho_hi=rho_e, rho_lo=rho_b)
        lay = layers[g]
        if abs(lay["delta"] - d) > 1e-9 or abs(lay["ci95"][0] - ci[0]) > 1e-9 \
                or abs(lay["ci95"][1] - ci[1]) > 1e-9:
            ok_layers = False
        n_layer = int(m_b.sum() + m_e.sum())
        if lay["n"] != n_layer:
            ok_layers = False
        acc.append((n_layer, d, ci))
    record("B6.layer_values_match_hand_1e-9", ok_layers, "layer deltas/CIs differ from hand welch")
    # exact weighted formula (windows.py L474-500) recomputed from the hand reference
    n_tot = sum(n for n, _, _ in acc)
    w_delta = sum(n / n_tot * d for n, d, _ in acc)
    w_se = float(np.sqrt(sum((n / n_tot) ** 2 * ((ci[1] - ci[0]) / (2 * 1.96)) ** 2
                             for n, _, ci in acc))) or 1e-12
    hand_weighted_ci = [w_delta - 1.96 * w_se, w_delta + 1.96 * w_se]
    rec_delta = sum(layers[g]["n"] / sum(layers[h]["n"] for h in ("A", "B")) * layers[g]["delta"]
                    for g in ("A", "B"))
    rec_se = float(np.sqrt(sum(
        (layers[g]["n"] / sum(layers[h]["n"] for h in ("A", "B"))) ** 2
        * ((layers[g]["ci95"][1] - layers[g]["ci95"][0]) / (2 * 1.96)) ** 2 for g in ("A", "B"))))
    record("B6.weighted_delta_matches_hand_1e-9", abs(rec_delta - w_delta) <= 1e-9,
           f"rec={rec_delta} hand={w_delta}")
    record("B6.weighted_ci_matches_hand_1e-9",
           abs(rec_delta - 1.96 * rec_se - hand_weighted_ci[0]) <= 1e-9
           and abs(rec_delta + 1.96 * rec_se - hand_weighted_ci[1]) <= 1e-9, "")
    record("B6.overall_estimable", r["attribution_status"] == "estimable", r["attribution_status"])
    record("B6.gate_exit0", run_gate(run).returncode == 0, "")


def case_b7():
    print("== B7: confound downgrade propagates to store and recommendation ==")
    run = make_run("B7")
    write_tsdata(run, 600, {"y": (50.0, 0.3)}, 13, {"y": [(300, 2.5)]})
    log = base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}],
                   confounds=[{"type": "maintenance", "note": "维护介入", "ts": iso(310)}])
    write_logs(run, log)
    write_json(run / "00_input" / "fault_signature.json", {
        "signature_version": "1.0", "source_ref": "alert-9",
        "anomalous_params": [{"parameter": "temp", "direction": "high", "severity": 2.2}],
        "regime": {"product": "P1", "machine": "M1", "regime_label": "R1"},
        "degraded_metric": "y"})
    record("B7.tune_exit0", run_tune(run, "y").returncode == 0, "")
    rep = next((run / "06_experience" / "attribution").glob("*.json"))
    r = json.loads(rep.read_text(encoding="utf-8"))
    record("B7.confound_detected", r["confound_detected"] is True, "")
    record("B7.grade_E0", r["evidence_grade"] == "E0", r["evidence_grade"])
    record("B7.status_still_estimable", r["attribution_status"] == "estimable", r["attribution_status"])
    record("B7.build_exit0", run_build(run).returncode == 0, "")
    entry = read_store(run)[0]
    record("B7.store_e0", entry["evidence_grade"] == "E0", str(entry["evidence_grade"]))
    record("B7.store_note_mentions_confound",
           "混杂" in (entry["payload"]["applicability_note"] or ""), "")
    m = run_node("match_playbook.mjs", "recommend", "--run-dir", str(run))
    record("B7.recommend_exit0", m.returncode == 0, m.stderr[-300:])
    rec = read(run, "conclusions/recommendation.json")
    record("B7.rec_playbook_E0", rec["playbooks"] and rec["playbooks"][0]["evidence_grade"] == "E0",
           str(rec["playbooks"][:1]))
    record("B7.gate_exit0", run_gate(run).returncode == 0, "")


def case_b8():
    print("== B8: bundle is the attribution unit; overlapping same-param action -> compromised ==")
    run = make_run("B8")
    write_tsdata(run, 600, {"temp": (50.0, 0.3), "press": (1.0, 0.05), "y": (50.0, 0.3)}, 17,
                 {"temp": [(100, 2.0), (350, 2.0), (380, 2.0)],
                  "y": [(100, 2.0), (350, 2.0), (380, 2.0)]})
    logs = [
        base_log(iso(100),
                 [{"parameter": "temp", "from": 50.0, "to": 52.0, "unit": "degC"},
                  {"parameter": "press", "from": 1.0, "to": 1.2, "unit": "kPa"}],
                 bundle={"is_bundle": True, "bundle_reason": "coupled_move", "note": "联动调整"}),
        base_log(iso(350), [{"parameter": "temp", "from": 52.0, "to": 54.0, "unit": "degC"}]),
        base_log(iso(380), [{"parameter": "temp", "from": 54.0, "to": 56.0, "unit": "degC"}]),
    ]
    write_logs(run, logs)
    record("B8.tune_exit0", run_tune(run, "y").returncode == 0, "")
    reports = {}
    for f in (run / "06_experience" / "attribution").glob("*.json"):
        reports[json.loads(f.read_text(encoding="utf-8"))["action_log_id"]] = json.loads(
            f.read_text(encoding="utf-8"))
    by_ts = {iso(100): None, iso(350): None, iso(380): None}
    loaded = read(run, "00_input/action_log.json")
    ids = {}
    import hashlib
    def canon(obj):
        # same normalization as segment_selector.canonical_json (integral floats -> ints)
        def norm(o):
            if isinstance(o, bool) or o is None:
                return o
            if isinstance(o, float) and o.is_integer() and abs(o) < 1e15:
                return int(o)
            if isinstance(o, dict):
                return {k: norm(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [norm(v) for v in o]
            return o
        return json.dumps(norm(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    def sha16(obj):
        return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()[:16]
    for i, lg in enumerate(loaded):
        ts8 = "".join(ch for ch in lg["ts"] if ch.isdigit())[:8]
        ids[lg["ts"]] = ts8 + sha16(lg)[:8]
    bundle_rep = reports[ids[iso(100)]]
    overlap_rep = reports[ids[iso(350)]]
    later_rep = reports[ids[iso(380)]]
    record("B8.bundle_scope_true", bundle_rep["bundle_scope"] is True, "")
    record("B8.bundle_single_report_estimable", bundle_rep["attribution_status"] == "estimable",
           bundle_rep["attribution_status"])
    record("B8.overlap_compromised", overlap_rep["attribution_compromised"] is True, "")
    record("B8.overlap_reason", overlap_rep["reason_code"] == "overlapping_action",
           str(overlap_rep["reason_code"]))
    record("B8.overlap_truncated", overlap_rep["attribution_status"] == "truncated",
           overlap_rep["attribution_status"])
    record("B8.overlap_truncated_by_set",
           (overlap_rep["segments"]["effect"]["truncated_by"] or "").startswith("action_log"),
           str(overlap_rep["segments"]["effect"]["truncated_by"]))
    record("B8.overlap_E0", overlap_rep["evidence_grade"] == "E0", overlap_rep["evidence_grade"])
    record("B8.later_action_estimable", later_rep["attribution_status"] == "estimable",
           later_rep["attribution_status"])
    b = run_build(run)
    record("B8.build_exit0", b.returncode == 0, b.stderr[-300:])
    store = read_store(run)
    bundle_entry = next(e for e in store if e["payload"]["action_summary"].count("→") == 2)
    record("B8.bundle_entry_two_actions", len(bundle_entry["payload"]["action_sequence"]) == 2, "")
    overlap_entry = next(e for e in store
                         if ids[iso(350)] in e["provenance"]["action_log_ids"])
    record("B8.store_overlap_E0", overlap_entry["evidence_grade"] == "E0", "")
    record("B8.all_three_admitted", len(store) == 3, str(len(store)))
    record("B8.gate_exit0", run_gate(run).returncode == 0, "")


def case_b9():
    print("== B9: feedback counters drive grade promotion/demotion (count-only, no LLM) ==")
    run = make_run("B9")
    write_tsdata(run, 600, {"y": (50.0, 0.3)}, 23, {"y": [(300, 2.5)]})
    write_logs(run, base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}]))
    record("B9.tune_exit0", run_tune(run, "y").returncode == 0, "")
    record("B9.build_exit0", run_build(run).returncode == 0, "")
    e0 = read_store(run)[0]
    record("B9.starts_E1_observation", e0["evidence_grade"] == "E1"
           and e0["confidence_label"] == "observation", "")
    fb = lambda res: run_node("experience_build.mjs", "feedback", "--run-dir", str(run),
                              "--chunk-id", e0["chunk_id"], "--result", res)
    r1 = fb("effective")
    e1 = read_store(run)[0]
    record("B9.effective1_corroboration2", e1["corroboration_count"] == 2, "")
    r2 = fb("effective")
    e2 = read_store(run)[0]
    record("B9.effective2_verified_E2", e2["corroboration_count"] == 3
           and e2["evidence_grade"] == "E2" and e2["confidence_label"] == "verified",
           f"{e2['evidence_grade']}/{e2['confidence_label']}")
    r3 = fb("harmful")
    e3 = read_store(run)[0]
    record("B9.refutation_caps_E1", e3["refutation_count"] == 1
           and e3["evidence_grade"] == "E1", f"{e3['evidence_grade']}")
    r4 = fb("harmful")
    e4 = read_store(run)[0]
    record("B9.refutation2_demotes_observation", e4["refutation_count"] == 2
           and e4["confidence_label"] == "observation",
           f"{e4['confidence_label']}")
    state = read(run, "06_experience/accumulated/state.json")
    results_seq = [h["result"] for h in state.get("history", [])][-4:]
    record("B9.ledger_history", len(state.get("history", [])) == 5
           and results_seq == ["effective", "effective", "harmful", "harmful"],
           f"history={len(state.get('history', []))} tail={results_seq}")
    record("B9.all_feedback_exit0", all(x.returncode == 0 for x in (r1, r2, r3, r4)), "")
    record("B9.gate_exit0", run_gate(run).returncode == 0, "")


def case_b10():
    print("== B10: step_detector recall >=90% on injected steps; retro entries locked advisory/E0 ==")
    run = make_run("B10")
    # white noise directly (MR-bar/d2 sigma recovery is exact for white noise)
    rng = np.random.default_rng(31)
    n = 800
    temp = 50.0 + rng.normal(0, 1.0, n)
    press = 100.0 + rng.normal(0, 0.8, n)
    temp[200:] += 4.0
    temp[500:] -= 4.0
    press[350:] += 5.0
    pd.DataFrame({"t": [iso(i) for i in range(n)],
                  "temp": np.round(temp, 6), "press": np.round(press, 6)}).to_csv(
        run / "00_input" / "data.csv", index=False)
    d = run_py("step_detector.py", "detect", "--run-dir", str(run),
               "--cols", "temp,press", "--window", "40", "--k", "3.0")
    record("B10.detect_exit0", d.returncode == 0, d.stderr[-300:])
    retro = read(run, "06_experience/retro_action_log.json")
    record("B10.exactly_three_steps", len(retro) == 3, f"found {len(retro)}")
    true_rows = {("temp", 200), ("temp", 500), ("press", 350)}
    matched = set()
    for lg in retro:
        a = lg["actions"][0]
        row = lg["context"]["steady_segment_ref"]["row_range"][0]
        for (col, tr) in true_rows:
            if a["parameter"] == col and abs(row - tr) <= 40:
                matched.add((col, tr))
    recall = len(matched) / len(true_rows)
    record("B10.recall_ge_90pct", recall >= 0.9, f"recall={recall} matched={matched}")
    record("B10.all_retro_actor", all(lg["actor"]["actor_type"] == "unknown_retro_inferred"
                                      for lg in retro), "")
    record("B10.all_retro_source", all(lg["ingest_meta"]["source"] == "retro_mined"
                                       for lg in retro), "")
    record("B10.all_advisory_note", all("仅参考" in (lg["bundled_action"]["note"] or "")
                                        for lg in retro), "")
    b = run_build(run, "--action-log", "06_experience/retro_action_log.json")
    record("B10.build_retro_exit0", b.returncode == 0, b.stderr[-300:])
    store = read_store(run)
    record("B10.store_retro_E0_locked",
           len(store) == 3 and all(e["evidence_grade"] == "E0" and e["retro_mined"] is True
                                   for e in store), str([(e["retro_mined"], e["evidence_grade"]) for e in store]))
    # retro must never enter E2 promotion even with effective feedback
    fb = run_node("experience_build.mjs", "feedback", "--run-dir", str(run),
                  "--chunk-id", store[0]["chunk_id"], "--result", "effective")
    e = next(x for x in read_store(run) if x["chunk_id"] == store[0]["chunk_id"])
    record("B10.retro_stays_E0_after_feedback", e["evidence_grade"] == "E0", e["evidence_grade"])
    record("B10.gate_exit0", run_gate(run).returncode == 0, "")


def case_b11():
    print("== B11: privacy — raw actor ids never reach store/kb/recommendation (grep-level) ==")
    run = make_run("B11")
    write_tsdata(run, 600, {"y": (50.0, 0.3)}, 41, {"y": [(300, 2.5)]})
    write_logs(run, base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}],
                             actor_id="ENG-ZHANG-0091"))
    write_json(run / "00_input" / "actor_alias_map.json", {"ENG-ZHANG-0091": "eng_03"})
    record("B11.tune_exit0", run_tune(run, "y").returncode == 0, "")
    record("B11.build_exit0", run_build(run, "--alias-map", "00_input/actor_alias_map.json").returncode == 0, "")
    write_json(run / "00_input" / "fault_signature.json", {
        "signature_version": "1.0", "source_ref": None,
        "anomalous_params": [{"parameter": "temp", "direction": "high", "severity": None}],
        "regime": {"product": "P1", "machine": "M1", "regime_label": "R1"},
        "degraded_metric": "y"})
    record("B11.recommend_exit0", run_node("match_playbook.mjs", "recommend", "--run-dir", str(run)).returncode == 0, "")
    leaks = []
    for base in ("06_experience", "conclusions"):
        for p in (run / base).rglob("*"):
            if p.is_file() and p.suffix in (".json", ".jsonl", ".md"):
                if "ENG-ZHANG-0091" in p.read_text(encoding="utf-8"):
                    leaks.append(str(p))
    record("B11.no_raw_id_leak", not leaks, str(leaks))
    entry = read_store(run)[0]
    record("B11.alias_in_store", entry["provenance"]["actor_alias"] == "eng_03",
           str(entry["provenance"]["actor_alias"]))
    g = run_gate(run, "--alias-map", "00_input/actor_alias_map.json")
    record("B11.gate_T8_pass", g.returncode == 0 and "T8" in g.stdout, g.stdout[-300:])


def case_b12():
    print("== B12: tamper battery — gate must FAIL each forged path ==")
    base = FIXTURES
    base.mkdir(parents=True, exist_ok=True)

    def attr_report(**over):
        r = {"report_version": "1.0", "action_log_id": "x", "bundle_scope": None,
             "attribution_status": "estimable", "reason_code": None, "metric": "y",
             "segments": {"baseline": {"row_range": [0, 10], "n": 10, "n_eff": 10, "lag1_autocorr": 0.0},
                          "effect": {"row_range": [20, 30], "n": 10, "n_eff": 10,
                                     "lag1_autocorr": 0.0, "truncated_by": None},
                          "dead_time_used": 0.0},
             "effect": {"delta": 1.0, "ci95": [0.5, 1.5], "n_eff_hi": 10, "n_eff_lo": 10,
                        "direction_established": True, "stratified": None},
             "confound_detected": False, "attribution_compromised": False,
             "anti_spurious": {"trend_check": "PASS", "outlier_check": "PASS"},
             "evidence_grade": "E1",
             "provenance": {"script_version": "tune_stats/1.0", "authored_by": "script"}}
        r.update(over)
        return r

    def tamper_dir(name, files):
        d = (base / name).resolve()
        if FIXTURES not in d.parents:
            raise ValueError("escape")
        for rel, obj in files.items():
            write_json(d / rel, obj)
        return d

    # (a) not_estimable WITH a fabricated effect
    d_a = tamper_dir("tamper_b12_a", {"06_experience/attribution/x.json": attr_report(
        attribution_status="not_estimable", reason_code="min_points",
        effect={"delta": 1.0, "ci95": [0.5, 1.5], "n_eff_hi": 10, "n_eff_lo": 10,
                "direction_established": True, "stratified": None})})
    g_a = run_gate(d_a)
    record("B12.a_not_estimable_with_effect_FAIL", g_a.returncode == 1 and "T4" in g_a.stdout,
           f"rc={g_a.returncode} {g_a.stdout[-200:]}")
    # (b) not_estimable WITHOUT reason_code
    d_b = tamper_dir("tamper_b12_b", {"06_experience/attribution/x.json": attr_report(
        attribution_status="not_estimable", reason_code=None, effect=None)})
    g_b = run_gate(d_b)
    record("B12.b_missing_reason_FAIL", g_b.returncode == 1 and "T4" in g_b.stdout,
           f"rc={g_b.returncode}")
    # (c) extra key on attribution report (strict keys)
    r_c = attr_report()
    r_c["hello_extra"] = 1
    d_c = tamper_dir("tamper_b12_c", {"06_experience/attribution/x.json": r_c})
    g_c = run_gate(d_c)
    record("B12.c_extra_key_FAIL", g_c.returncode == 1 and "T3" in g_c.stdout, f"rc={g_c.returncode}")
    # (d) enum literal not in closedloop_enums
    d_d = tamper_dir("tamper_b12_d", {"06_experience/attribution/x.json": attr_report(
        attribution_status="maybe")})
    g_d = run_gate(d_d)
    record("B12.d_bad_enum_FAIL", g_d.returncode == 1 and "T5" in g_d.stdout, f"rc={g_d.returncode}")
    # (e) store entry E2 with corroboration 1
    entry = {"experience_version": "1.0", "experience_type": "tuning_action_effect",
             "regime_key": "P1|M1|R1",
             "payload": {"action_summary": "x", "effect": {"metric": "y", "delta": 1.0,
                                                           "ci95": [0.5, 1.5], "n_eff": 10,
                                                           "direction_established": True},
                         "attribution_status": "estimable", "confound_detected": False,
                         "trajectory": None, "fault_signature": None, "action_sequence": None,
                         "applicability_note": None, "final_setpoints": None, "achieved": None,
                         "rounds_used": None, "trials_used": None, "confirm_status": None,
                         "lesson": None},
             "applicability": {"factor_observed_ranges": None, "system": None, "scenario_tags": []},
             "provenance": {"actor_alias": "eng_03", "action_log_ids": ["x"], "run_ids": [],
                            "batch_ids": [], "regime_key": "P1|M1|R1", "attribution_version": None,
                            "built_from": "t", "judge_score": None, "era": None},
             "confidence_label": "verified", "evidence_grade": "E2", "corroboration_count": 1,
             "refutation_count": 0, "cross_regime_consistent": False,
             "invalidation_conditions": [], "chunk_id": "exp_x", "action_signature": "sig",
             "retro_mined": False}
    d_e = tamper_dir("tamper_b12_e", {"06_experience/tuning_experience.jsonl": None})
    (d_e / "06_experience" / "tuning_experience.jsonl").write_text(
        json.dumps(entry) + "\n", encoding="utf-8")
    g_e = run_gate(d_e)
    record("B12.e_E2_corroboration1_FAIL", g_e.returncode == 1 and "T6" in g_e.stdout,
           f"rc={g_e.returncode}")
    # (f) retro entry graded E2
    import copy
    entry_f = copy.deepcopy(entry)
    entry_f["retro_mined"] = True
    entry_f["chunk_id"] = "exp_retro"
    d_f = tamper_dir("tamper_b12_f", {})
    (d_f / "06_experience").mkdir(parents=True, exist_ok=True)
    (d_f / "06_experience" / "tuning_experience.jsonl").write_text(
        json.dumps(entry_f) + "\n", encoding="utf-8")
    g_f = run_gate(d_f)
    record("B12.f_retro_E2_FAIL", g_f.returncode == 1 and "T6" in g_f.stdout, f"rc={g_f.returncode}")
    # (g) not_estimable admitted into the store
    entry_g = copy.deepcopy(entry)
    entry_g["payload"]["attribution_status"] = "not_estimable"
    entry_g["chunk_id"] = "exp_ne"
    d_g = tamper_dir("tamper_b12_g", {})
    (d_g / "06_experience").mkdir(parents=True, exist_ok=True)
    (d_g / "06_experience" / "tuning_experience.jsonl").write_text(
        json.dumps(entry_g) + "\n", encoding="utf-8")
    g_g = run_gate(d_g)
    record("B12.g_not_estimable_admitted_FAIL", g_g.returncode == 1 and "T6" in g_g.stdout,
           f"rc={g_g.returncode}")
    # (h) recommendation carrying autonomy_level (IDD must never set dispatch policy)
    rec = json.loads((SKILL / "templates" / "recommendation_template.json").read_text(encoding="utf-8"))
    rec.pop("_template_note", None)
    rec["autonomy_level"] = "auto_within_guardrails"
    d_h = tamper_dir("tamper_b12_h", {"conclusions/recommendation.json": rec})
    g_h = run_gate(d_h)
    record("B12.h_autonomy_level_FAIL", g_h.returncode == 1 and "T7" in g_h.stdout,
           f"rc={g_h.returncode}")


def case_b13():
    print("== B13: recommendation->execution write-back anchoring (ack chain, unconfirmed demotion) ==")
    # path 1: aws_executor action WITHOUT recommendation_ref -> unconfirmed, no promotion
    run = make_run("B13a")
    write_tsdata(run, 900, {"y": (50.0, 0.3)}, 51, {"y": [(300, 2.5)]})
    write_logs(run, base_log(iso(300), [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}],
                             actor_id="aws-agent-01", actor_type="aws_executor"))
    record("B13a.tune_exit0", run_tune(run, "y").returncode == 0, "")
    record("B13a.build_exit0", run_build(run).returncode == 0, "")
    e = read_store(run)[0]
    record("B13a.unconfirmed_marked", e["payload"]["confirm_status"] == "unconfirmed",
           str(e["payload"]["confirm_status"]))
    for _ in range(2):
        run_node("experience_build.mjs", "feedback", "--run-dir", str(run),
                 "--chunk-id", e["chunk_id"], "--result", "effective")
    e = read_store(run)[0]
    record("B13a.unconfirmed_never_promotes",
           e["corroboration_count"] == 3 and e["evidence_grade"] == "E1",
           f"corr={e['corroboration_count']} grade={e['evidence_grade']}")
    record("B13a.gate_exit0", run_gate(run).returncode == 0, "")

    # path 2: with recommendation_ref + executed ack -> confirmed, promotion allowed
    run2 = make_run("B13b")
    write_tsdata(run2, 900, {"y": (50.0, 0.3)}, 53,
                 {"y": [(100, 2.5), (300, 2.5)]})
    write_logs(run2, base_log(iso(100), [{"parameter": "temp", "from": 50.0, "to": 55.0, "unit": "degC"}]))
    write_json(run2 / "00_input" / "fault_signature.json", {
        "signature_version": "1.0", "source_ref": "alert-b13",
        "anomalous_params": [{"parameter": "temp", "direction": "high", "severity": 3.0}],
        "regime": {"product": "P1", "machine": "M1", "regime_label": "R1"},
        "degraded_metric": "y"})
    record("B13b.tune_exit0", run_tune(run2, "y").returncode == 0, "")
    record("B13b.build_exit0", run_build(run2).returncode == 0, "")
    record("B13b.recommend_exit0",
           run_node("match_playbook.mjs", "recommend", "--run-dir", str(run2)).returncode == 0, "")
    rec = read(run2, "conclusions/recommendation.json")
    ack = {"recommendation_id": rec["recommendation_id"], "status": "executed",
           "executed_action_log_id": "20260115aaaaaaaa", "note": "已下发执行"}
    (run2 / "00_input").mkdir(exist_ok=True)
    write_json(run2 / "00_input" / "ack-20261001-000001-001.json", ack)
    a = run_node("match_playbook.mjs", "ack", "--run-dir", str(run2),
                 "--ack-file", "00_input/ack-20261001-000001-001.json")
    record("B13b.ack_recorded", a.returncode == 0
           and read(run2, "conclusions/recommendation.json")["ack"]["status"] == "executed",
           a.stderr[-300:])
    # aws_executor writes back the executed action WITH the recommendation_ref
    log2 = base_log(iso(300), [{"parameter": "temp", "from": 55.0, "to": 60.0, "unit": "degC"}],
                    actor_id="aws-agent-01", actor_type="aws_executor")
    log2["recommendation_ref"] = rec["recommendation_id"]
    logs = read(run2, "00_input/action_log.json")
    logs.append(log2)
    write_logs(run2, logs)
    record("B13b.retune_exit0", run_tune(run2, "y").returncode == 0, "")
    record("B13b.rebuild_exit0", run_build(run2).returncode == 0, "")
    e2 = next(x for x in read_store(run2) if x["payload"].get("confirm_status") == "confirmed")
    record("B13b.confirmed_marked", e2["payload"]["confirm_status"] == "confirmed", "")
    fb = run_node("experience_build.mjs", "feedback", "--run-dir", str(run2),
                  "--chunk-id", e2["chunk_id"], "--result", "effective")
    e2 = next(x for x in read_store(run2) if x["chunk_id"] == e2["chunk_id"])
    record("B13b.confirmed_promotes", e2["evidence_grade"] == "E2",
           f"grade={e2['evidence_grade']} corr={e2['corroboration_count']}")
    record("B13b.gate_exit0", run_gate(run2).returncode == 0, "")


def case_b14():
    print("== B14: retro fallback — cold start from steps alone, advisory-only E0 recommendation ==")
    run = make_run("B14")
    rng = np.random.default_rng(61)
    n = 900
    temp = 50.0 + rng.normal(0, 1.0, n)
    temp[300:] += 4.0
    pd.DataFrame({"t": [iso(i) for i in range(n)], "temp": np.round(temp, 6)}).to_csv(
        run / "00_input" / "data.csv", index=False)
    record("B14.no_action_logs_initially", not (run / "00_input" / "action_log.json").exists(), "")
    d = run_py("step_detector.py", "detect", "--run-dir", str(run), "--cols", "temp")
    record("B14.detect_exit0", d.returncode == 0, d.stderr[-300:])
    retro = read(run, "06_experience/retro_action_log.json")
    record("B14.retro_steps_found", len(retro) == 1, f"{len(retro)}")
    b = run_build(run, "--action-log", "06_experience/retro_action_log.json")
    record("B14.build_retro_exit0", b.returncode == 0, b.stderr[-300:])
    store = read_store(run)
    record("B14.retro_entry_E0", len(store) == 1 and store[0]["evidence_grade"] == "E0"
           and store[0]["retro_mined"] is True, "")
    kb = (run / "06_experience" / "kb_summary.md").read_text(encoding="utf-8")
    record("B14.kb_advisory_note", "仅参考" in kb, "")
    write_json(run / "00_input" / "fault_signature.json", {
        "signature_version": "1.0", "source_ref": None,
        "anomalous_params": [{"parameter": "temp", "direction": "high", "severity": 2.5}],
        "regime": None, "degraded_metric": None})
    m = run_node("match_playbook.mjs", "recommend", "--run-dir", str(run))
    record("B14.recommend_exit0", m.returncode == 0, m.stderr[-300:])
    rec = read(run, "conclusions/recommendation.json")
    record("B14.status_in_enum", rec["recommendation_status"] in
           ("playbook_hit", "direction_only", "fallback_generic", "no_playbook_hit"),
           rec["recommendation_status"])
    if rec["playbooks"]:
        record("B14.retro_playbook_E0_advisory",
               all(p["evidence_grade"] == "E0" for p in rec["playbooks"]),
               str([p["evidence_grade"] for p in rec["playbooks"]]))
    record("B14.gate_exit0", run_gate(run).returncode == 0, "")


CASES = {"B1": case_b1, "B2": case_b2, "B3": case_b3, "B4": case_b4, "B5": case_b5,
         "B6": case_b6, "B7": case_b7, "B8": case_b8, "B9": case_b9, "B10": case_b10,
         "B11": case_b11, "B12": case_b12, "B13": case_b13, "B14": case_b14}


def main():
    selector = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = list(CASES) if selector == "all" else ([selector] if selector in CASES else list(CASES))
    for name in todo:
        CASES[name]()
    if "--keep" not in sys.argv:
        clean_artifacts()
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n[TESTS] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
          + (f" — FAILED: {[r[0] for r in failed]}" if failed else " — ALL GREEN"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
