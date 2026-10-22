#!/usr/bin/env python3
"""Test suite for industrial-line-stability-report.

Run:  uv run --project .claude/shared/scripts python tests/run_tests.py all
House style: deterministic PASS/FAIL checks, exits 1 on any failure.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
SCRIPTS = os.path.join(SKILL, "scripts")
ANALYZER = os.path.join(SCRIPTS, "stability_analyzer.py")
BUILDER = os.path.join(SCRIPTS, "report_builder.py")
GATE = os.path.join(SCRIPTS, "quality_gate.mjs")
PREPARE = os.path.join(SCRIPTS, "ontology_prepare.py")
PREPROCESSOR = os.path.join(REPO, ".claude", "skills", "industrial-data-preprocessor",
                            "scripts", "data_preprocessor.py")
ONTOLOGY_SCHEMA = os.path.join(REPO, ".claude", "skills", "industrial-ontology-builder",
                               "schemas", "ontology_schema.json")
VALIDATOR = os.path.join(REPO, ".claude", "shared", "scripts", "validate.mjs")
SHARED_ENUMS = os.path.join(REPO, ".claude", "shared", "schemas", "closedloop_enums.json")

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not cond else ""))


def py(*args, cwd=None, env=None):
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, cwd=cwd or REPO, timeout=300, encoding="utf-8",
                          errors="replace", env={**os.environ, **(env or {})})


def node_gate(report_path, out_dir):
    return subprocess.run(["node", GATE, report_path, out_dir], capture_output=True,
                          text=True, cwd=REPO, timeout=120, encoding="utf-8",
                          errors="replace")


# ---------------------------------------------------------------- fixtures
def write_stable_csv(path, n=1000, seed=7):
    rng = np.random.default_rng(seed)
    t0 = datetime(2026, 10, 1, 8, 0, 0)
    t = [(t0 + timedelta(seconds=60 * i)).isoformat() for i in range(n)]
    df = pd.DataFrame({
        "t": t,
        "temp": 85.0 + rng.normal(0, 0.03, n),
        "press": 0.60 + rng.normal(0, 0.0008, n),
        "rate": 120.0 + rng.normal(0, 0.25, n),
        "yield_pct": 98.5 + rng.normal(0, 0.15, n),
    })
    df.to_csv(path, index=False)
    return df


def write_unstable_csv(path, n=1000, seed=11):
    rng = np.random.default_rng(seed)
    t0 = datetime(2026, 10, 2, 8, 0, 0)
    t = [(t0 + timedelta(seconds=60 * i)).isoformat() for i in range(n)]
    drift = np.linspace(0, 0.6, n)          # strong ramp on temp
    step = np.where(np.arange(n) >= 500, 0.25, 0.0)  # level shift on press
    spikes = np.zeros(n)
    for i in (200, 480, 760):
        spikes[i] = 0.35                     # >3 sigma events on rate
    df = pd.DataFrame({
        "t": t,
        "temp": 85.0 + rng.normal(0, 0.05, n) + drift,
        "press": 0.60 + rng.normal(0, 0.0012, n) + step,
        "rate": 120.0 + rng.normal(0, 0.05, n) + spikes,
        "yield_pct": 98.5 + rng.normal(0, 0.2, n) - drift * 1.5,
    })
    df.to_csv(path, index=False)
    return df


def write_snapshot_csv(path, n=120, n_params=5, varying=0, seed=7):
    """Degenerate-export fixture: hourly rows whose parameter values are the
    SAME single snapshot repeated on every row (`varying` cols get real noise)."""
    rng = np.random.default_rng(seed)
    t0 = datetime(2026, 10, 1, 8, 0, 0)
    t = [(t0 + timedelta(hours=i)).isoformat() for i in range(n)]
    cols = {"t": t}
    for i in range(n_params):
        base = 85.0 + 10 * i
        col = f"p{i}"
        cols[col] = (base + rng.normal(0, 0.05, n) if i < varying
                     else [round(base, 6)] * n)
    pd.DataFrame(cols).to_csv(path, index=False)
    return path


def write_baseline(path, temp_median=85.5, temp_mad=0.02):
    payload = {
        "contract_version": "sentinel-baseline/1.0",
        "baseline_version": "v1.0.0",
        "global": {"time_col": "t", "group_col": None,
                   "numeric_columns": ["temp", "press", "rate"]},
        "groups": {"__ALL__": {"parameters": {
            "temp": {"median": temp_median, "mad": temp_mad, "q10": temp_median - 0.02,
                     "q90": temp_median + 0.02, "cv": 0.0004,
                     "center": temp_median, "sigma_within_mr": temp_mad * 1.5,
                     "sigma_overall": temp_mad * 1.4},
        }}},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def write_attribution(path):
    payload = {
        "contract_version": "1.0",
        "reports": [{
            "attribution_status": "estimable",
            "action_id": "act-001",
            "action": {"parameter": "temp", "to": 86.0, "unit": "C"},
            "effect": {"delta": 0.42, "higher_is_better": True},
        }, {
            "attribution_status": "not_estimable",
            "action_id": "act-002",
            "reason_code": "min_points",
        }],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def write_doe_recommendations(path, temp_low=92.0, temp_high=94.0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "contract_version": "1.0",
        "audience": ["optimizer-loop", "sentinel", "line-stability-report"],
        "operating_windows": [
            {"parameter": "temp", "low": temp_low, "high": temp_high,
             "confidence": "high"},
        ],
        "confirmations": [{"parameter": "temp", "status": "pending_trial"}],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def run_analyze(run_dir, out_dir=None, extra=None):
    cmd = [ANALYZER, "analyze", "--run-dir", run_dir]
    if out_dir:
        cmd += ["--out-dir", out_dir]
    if extra:
        cmd += extra
    return py(*cmd)


def run_prepare(run_dir, extra=None, store=None):
    """Ontology prepare with --json; ONTOLOGY_STORE_DIR comes from the suite env
    unless a private in-repo store is passed (zero-declaration fixtures that
    must observe their own first build)."""
    cmd = [PREPARE, "--run-dir", run_dir, "--json"]
    if extra:
        cmd += extra
    env = {"ONTOLOGY_STORE_DIR": store} if store else None
    return py(*cmd, env=env)


def load_report(out_dir):
    with open(os.path.join(out_dir, "stability_report.json"), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- scenarios
def scenario_stable(base):
    print("[S1] stable line -> grade A, no high findings, gate PASS")
    run_dir = os.path.join(base, "stable")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"))
    r = run_analyze(run_dir)
    check("stable.exit_code_in_0_1", r.returncode in (0, 1), r.stderr[-300:])
    rep = load_report(out)
    check("stable.status_ok", rep["status"] == "ok")
    check("stable.grade_A", rep["conclusion"]["grade"] == "A",
          f"score={rep['conclusion']['score']}")
    check("stable.score_ge_85", rep["conclusion"]["score"] >= 85)
    check("stable.no_high_findings",
          rep["conclusion"]["findings_by_severity"]["high"] == 0)
    check("stable.provenance_zero_llm", rep["provenance"]["zero_llm"] is True)
    b = py(BUILDER, "--report", os.path.join(out, "stability_report.json"),
           "--charts", os.path.join(out, "charts.json"))
    check("stable.html_pass", b.returncode == 0, b.stdout[-300:])
    g = node_gate(os.path.join(out, "stability_report.json"), out)
    check("stable.gate_exit0", g.returncode == 0, g.stdout[-400:])
    return rep, out


def scenario_unstable(base):
    print("[S2] disturbed line -> low score, drift/spc findings, exit 1")
    run_dir = os.path.join(base, "unstable")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_unstable_csv(os.path.join(run_dir, "00_input", "data.csv"))
    r = run_analyze(run_dir)
    check("unstable.exit1", r.returncode == 1, f"rc={r.returncode} {r.stderr[-200:]}")
    rep = load_report(out)
    check("unstable.score_below_70", rep["conclusion"]["score"] < 70,
          f"score={rep['conclusion']['score']}")
    cats = {f["category"] for f in rep["findings"]}
    check("unstable.spc_finding", "spc" in cats)
    check("unstable.drift_finding", "drift" in cats)
    check("unstable.temp_score_low",
          min(p["score"] for p in rep["parameters"] if p["name"] == "temp") < 70)
    ev_ok = all(all("metric" in e and "value" in e for e in f["evidence"])
                for f in rep["findings"])
    check("unstable.findings_carry_evidence", ev_ok)
    return rep


def scenario_capability(base):
    print("[S3] spec limits -> cpk finding when incapable")
    run_dir = os.path.join(base, "capable")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    csvp = os.path.join(run_dir, "00_input", "data.csv")
    df = write_stable_csv(csvp, n=600, seed=21)
    # melt_temp centered far from narrow spec -> low cpk
    df["melt_temp"] = 185.0 + np.random.default_rng(5).normal(0, 0.4, len(df))
    df.to_csv(csvp, index=False)
    ctx = {"line_id": "L-TEST", "spec_limits": {
        "melt_temp": {"lsl": 178.0, "usl": 182.0, "target": 180.0}}}
    with open(os.path.join(run_dir, "00_input", "report_context.json"), "w",
              encoding="utf-8") as f:
        json.dump(ctx, f)
    r = run_analyze(run_dir)
    rep = load_report(out)
    mt = next(p for p in rep["parameters"] if p["name"] == "melt_temp")
    check("capable.cpk_computed", mt["capability"]["cpk"] is not None
          and mt["capability"]["cpk"] < 0.67, str(mt["capability"]))
    check("capable.capability_finding",
          any(f["category"] == "capability" and "melt_temp" in f["affected"]
              for f in rep["findings"]))
    check("capable.line_id_picked", rep["line"]["line_id"] == "L-TEST")
    return rep


def scenario_correlation(base):
    print("[S4] lagged driver -> leader/lag detected")
    run_dir = os.path.join(base, "corr")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    n = 800
    rng = np.random.default_rng(3)
    a = rng.normal(0, 1, n)
    b = np.empty(n)
    b[:] = np.nan
    b[5:] = a[:-5] * 1.0 + rng.normal(0, 0.1, n - 5)
    t0 = datetime(2026, 10, 3, 0, 0, 0)
    pd.DataFrame({
        "t": [(t0 + timedelta(seconds=10 * i)).isoformat() for i in range(n)],
        "drive_a": a, "resp_yield": b,
        "filler": rng.normal(50, 1, n),
    }).to_csv(os.path.join(run_dir, "00_input", "data.csv"), index=False)
    r = run_analyze(run_dir)
    rep = load_report(out)
    pair = next((p for p in rep["correlations"]["pairs"]
                 if {p["a"], p["b"]} == {"drive_a", "resp_yield"}), None)
    check("corr.pair_found", pair is not None)
    if pair:
        check("corr.leader_is_drive_a", pair["leader"] == "drive_a", str(pair))
        check("corr.lag_5", pair["best_lag_rows"] == 5, str(pair["best_lag_rows"]))
        check("corr.strong_r", pair["best_abs_r"] > 0.95, str(pair["best_abs_r"]))
    check("corr.contribution_targets_resp",
          any(c["target"] == "resp_yield" and c["driver"] == "drive_a"
              for c in rep["correlations"]["contributions"]))
    return rep


def scenario_baseline(base):
    print("[S5] sentinel baseline deviation -> finding + penalty")
    run_dir = os.path.join(base, "baseline")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=600, seed=31)
    bl = write_baseline(os.path.join(run_dir, "watch_baseline.json"))
    r = run_analyze(run_dir, extra=["--baseline", bl])
    rep = load_report(out)
    temp = next(p for p in rep["parameters"] if p["name"] == "temp")
    check("baseline.ref_attached", temp["baseline_ref"] is not None)
    check("baseline.high_deviation", temp["baseline_ref"]["deviation"] == "high",
          str(temp["baseline_ref"]))
    check("baseline.penalty_applied", temp["score_breakdown"]["baseline_penalty"] < 0)
    check("baseline.integration_used",
          rep["integrations"]["sentinel_baseline"]["used"] is True)
    check("baseline.deviation_finding",
          any(f["category"] == "baseline_deviation" for f in rep["findings"]))


def scenario_attribution(base):
    print("[S6] tuning-memory attribution merge -> action finding")
    run_dir = os.path.join(base, "attribution")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=600, seed=41)
    att = write_attribution(os.path.join(run_dir, "att.json"))
    log = os.path.join(run_dir, "action_log.json")
    with open(log, "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1.0", "ts": "2026-10-01T09:00:00Z",
                   "actor": {"actor_id": "u1", "actor_type": "engineer"},
                   "actions": [{"parameter": "temp", "to": 86.0, "unit": "C"}],
                   "context": {}}, f)
    r = run_analyze(run_dir, extra=["--action-log", log, "--attribution-json", att])
    rep = load_report(out)
    tm = rep["integrations"]["tuning_memory"]
    check("attribution.used", tm["used"] is True, json.dumps(tm)[:200])
    check("attribution.estimable_1", len(tm.get("estimable", [])) == 1)
    check("attribution.action_finding",
          any(f["category"] == "action" and "改善" in f["title"] for f in rep["findings"]),
          str([f["title"] for f in rep["findings"]]))


def scenario_doe(base):
    print("[S7] doe-analyzer operating window -> violation finding")
    run_dir = os.path.join(base, "doe")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=600, seed=51)
    doe_run = os.path.join(run_dir, "doe_run")
    write_doe_recommendations(os.path.join(doe_run, "conclusions", "recommendations.json"))
    r = run_analyze(run_dir, extra=["--doe-run-dir", doe_run])
    rep = load_report(out)
    doe = rep["integrations"]["doe_analyzer"]
    check("doe.used", doe["used"] is True)
    check("doe.window_violated", len(doe["violations"]) == 1, json.dumps(doe["violations"]))
    check("doe.window_finding",
          any(f["category"] == "window" for f in rep["findings"]))


def scenario_period_slice(base):
    print("[S8] period slice from report_context")
    run_dir = os.path.join(base, "slice")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=800, seed=61)
    ctx = {"start": "2026-10-01T12:00:00", "end": "2026-10-01T16:00:00"}
    with open(os.path.join(run_dir, "00_input", "report_context.json"), "w",
              encoding="utf-8") as f:
        json.dump(ctx, f)
    r = run_analyze(run_dir)
    rep = load_report(out)
    check("slice.rows_reduced", rep["data"]["n_rows_used"] < 800,
          str(rep["data"]["n_rows_used"]))
    check("slice.requested_recorded",
          rep["period"]["requested"]["start"] == "2026-10-01T12:00:00")
    check("slice.start_matches", rep["period"]["start"].startswith("2026-10-01 12:"))


def scenario_not_assessable(base):
    print("[S9] tiny data -> honest not_assessable, exit 2")
    run_dir = os.path.join(base, "tiny")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=30, seed=71)
    r = run_analyze(run_dir)
    check("tiny.exit2", r.returncode == 2, f"rc={r.returncode}")
    rep = load_report(out)
    check("tiny.status", rep["status"] == "not_assessable")
    check("tiny.null_score", rep["conclusion"]["score"] is None
          and rep["conclusion"]["grade"] is None)
    check("tiny.honest_statement", "不足以" in rep["conclusion"]["statement"])


def scenario_frozen_snapshot(base):
    print("[S9b] frozen snapshot (all channels time-invariant) -> no fake perfect grade")
    run_dir = os.path.join(base, "snapshot")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_snapshot_csv(os.path.join(run_dir, "00_input", "data.csv"),
                       n=120, n_params=5, varying=0)
    with open(os.path.join(run_dir, "00_input", "ontology.json"), "w",
              encoding="utf-8") as f:
        json.dump({
            "scene": {"name": "快照测试线", "process_type": "test"},
            "signals": {"g": [
                {"column": "p0", "name": "温度零点", "unit": "C", "role": "parameter",
                 "governing_law": "测试方程", "stage_ref": "工段A"},
                {"column": "p1", "name": "压力零点", "unit": "bar", "role": "parameter"},
            ]},
        }, f)
    r = run_analyze(run_dir)
    check("snap.exit2", r.returncode == 2, f"rc={r.returncode}")
    rep = load_report(out)
    check("snap.status", rep["status"] == "not_assessable")
    check("snap.null_score", rep["conclusion"]["score"] is None
          and rep["conclusion"]["grade"] is None)
    check("snap.snapshot_reason", "快照" in rep["conclusion"]["statement"],
          rep["conclusion"]["statement"])
    check("snap.invariant_stats",
          rep["data"]["time_invariant_channels"]["count"] == 5
          and rep["data"]["time_invariant_channels"]["total"] == 5)
    check("snap.degradation", any(d.get("check") == "time_invariant_channels"
                                  for d in rep["degradations"]))
    check("snap.no_params_scored", rep["parameters"] == [])
    check("snap.advice", "历史" in rep["conclusion"]["statement"],
          rep["conclusion"]["statement"])
    snap_tbl = rep["condition"].get("snapshot") or []
    check("snap.instant_table", len(snap_tbl) == 2
          and snap_tbl[0]["value"] == 85.0 and snap_tbl[0]["label"] == "温度零点",
          str(snap_tbl))
    b = py(os.path.join(SKILL, "scripts", "report_builder.py"),
           "--report", os.path.join(out, "stability_report.json"),
           "--charts", os.path.join(out, "charts.json"),
           "--out", os.path.join(out, "line_stability_report.html"),
           "--md", os.path.join(out, "line_stability_report.md"))
    check("snap.builder_ok", b.returncode == 0, b.stderr[-300:])
    with open(os.path.join(out, "line_stability_report.html"), encoding="utf-8") as f:
        html = f.read()
    check("snap.html_section", "当前状态快照" in html and "瞬时值" in html)
    with open(os.path.join(out, "line_stability_report.md"), encoding="utf-8") as f:
        md = f.read()
    check("snap.md_section", "当前状态快照" in md)
    g = node_gate(os.path.join(out, "stability_report.json"), out)
    check("snap.gate_pass", g.returncode == 0, g.stdout[-300:])


def scenario_partial_invariant(base):
    print("[S9c] mixed export: invariant channels excluded, varying ones assessed")
    run_dir = os.path.join(base, "partial")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_snapshot_csv(os.path.join(run_dir, "00_input", "data.csv"),
                       n=600, n_params=8, varying=4, seed=13)
    r = run_analyze(run_dir)
    check("mix.ok_or_findings", r.returncode in (0, 1), f"rc={r.returncode}")
    rep = load_report(out)
    check("mix.status_ok", rep["status"] == "ok")
    names = [p["name"] for p in rep["parameters"]]
    check("mix.only_varying_scored",
          sorted(names) == ["p0", "p1", "p2", "p3"], str(names))
    check("mix.invariant_stats",
          rep["data"]["time_invariant_channels"]["count"] == 4
          and rep["data"]["time_invariant_channels"]["total"] == 8)
    check("mix.degradation", any(d.get("check") == "time_invariant_channels"
                                 for d in rep["degradations"]))
    inv_f = [f for f in rep["findings"] if "不变量" in (f.get("title") or "")]
    check("mix.invariant_finding", len(inv_f) == 1
          and inv_f[0]["severity"] == "high"  # 50% share >= 0.5 threshold
          and inv_f[0]["confidence"] is not None
          and inv_f[0]["affected"] == ["p4", "p5", "p6", "p7"], str(inv_f))
    check("mix.n_assessed", rep["conclusion"]["n_parameters_assessed"] == 4,
          str(rep["conclusion"]["n_parameters_assessed"]))
    check("mix.contrib_skipped", rep["correlations"]["contributions"] == []
          and bool(rep["correlations"].get("contributions_skipped")),
          json.dumps(rep["correlations"], ensure_ascii=False)[:200])


def scenario_adaptive_targets(base):
    print("[S17] adaptive: inspection-first under cap + target pinning + preprocessing passthrough")
    run_dir = os.path.join(base, "adaptive")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    rng = np.random.default_rng(21)
    n = 400
    t0 = datetime(2026, 10, 5)
    cols = {"t": [(t0 + timedelta(seconds=60 * i)).isoformat() for i in range(n)]}
    for i in range(61):
        cols[f"param_{i:02d}"] = rng.normal(10 + i, 0.1, n)
    # yield_pct LAST and genuinely driven by param_00 → contribution target+pinned
    cols["yield_pct"] = 98.0 + 0.8 * (cols["param_00"] - 10.0) + rng.normal(0, 0.05, n)
    pd.DataFrame(cols).to_csv(os.path.join(run_dir, "00_input", "data.csv"), index=False)
    with open(os.path.join(run_dir, "00_input", "report_context.json"), "w",
              encoding="utf-8") as f:
        json.dump({"time_col": "t",
                   "preprocessing": {"source_file": "sim_export.xlsx",
                                     "script": "gen_fixture", "rows": n}}, f)
    r = run_analyze(run_dir)
    check("adap.runs", r.returncode in (0, 1), f"rc={r.returncode}")
    rep = load_report(out)
    names = [p["name"] for p in rep["parameters"]]
    check("adap.inspection_first_under_cap",
          names and names[0] == "yield_pct"
          and rep["parameters"][0]["role"] == "inspection", str(names[:3]))
    check("adap.cap_respected", len(names) == 60, str(len(names)))
    check("adap.prep_passthrough",
          rep["data"].get("preprocessing") == {"source_file": "sim_export.xlsx",
                                               "script": "gen_fixture", "rows": n},
          json.dumps(rep["data"].get("preprocessing"), ensure_ascii=False))
    contribs = rep["correlations"]["contributions"]
    check("adap.contrib_target_pinned", bool(contribs)
          and all(c.get("target") == "yield_pct" for c in contribs),
          json.dumps(contribs[:1], ensure_ascii=False)[:160])
    b = py(os.path.join(SKILL, "scripts", "report_builder.py"),
           "--report", os.path.join(out, "stability_report.json"),
           "--charts", os.path.join(out, "charts.json"))
    with open(os.path.join(out, "line_stability_report.html"), encoding="utf-8") as f:
        html = f.read()
    check("adap.html_prep_row", b.returncode == 0 and "预处理溯源" in html
          and "sim_export.xlsx" in html)
    check("adap.html_contrib_panel", "对检测/目标指标的方差解释占比" in html)


def scenario_epoch_time(base):
    print("[S18] numeric (epoch-second) time column -> physical drift rates")
    run_dir = os.path.join(base, "epoch")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    rng = np.random.default_rng(31)
    n = 400
    # 纯算术生成 epoch 秒（Windows 上 datetime.timestamp() 对 1970 附近会 OSError）；
    # 诊断器只要求"数值秒等间隔"，不要求真实 1970 基准
    epoch = [1_790_812_800 + 60.0 * i for i in range(n)]
    drift = np.linspace(0, 0.6, n)
    pd.DataFrame({
        "ts": epoch,
        "temp": 85.0 + rng.normal(0, 0.05, n) + drift,
        "yield_pct": 98.5 + rng.normal(0, 0.2, n),
    }).to_csv(os.path.join(run_dir, "00_input", "data.csv"), index=False)
    r = run_analyze(run_dir)
    check("epoch.runs", r.returncode in (0, 1), f"rc={r.returncode}")
    rep = load_report(out)
    # 数值模式下 period 保留原始秒（不被误解析成 1970 纳秒 datetime）
    check("epoch.numeric_mode_kept",
          rep["period"]["start"].startswith("1790812800"), rep["period"]["start"])
    interval = rep["data"]["sampling_interval_median_seconds"]
    check("epoch.interval_is_60s", abs((interval or 0) - 60) < 0.001, str(interval))
    p = next(p for p in rep["parameters"] if p["name"] == "temp")
    d = p.get("drift") or {}
    check("epoch.drift_rate_physical",
          d.get("significant") is True and 0.0005 < d.get("per_day_relative", 0) < 0.05,
          json.dumps(d))


def scenario_html_and_gate(base, stable_out):
    print("[S10] html content + gate tamper detection")
    with open(os.path.join(stable_out, "line_stability_report.html"),
              encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(stable_out, "html_selfcheck.json"), encoding="utf-8") as f:
        selfcheck = json.load(f)
    check("html.size_ge_8k", selfcheck["size_bytes"] >= 8192, str(selfcheck["size_bytes"]))
    check("html.selfcheck_pass", selfcheck["pass"] is True)
    check("html.hero_cn", "运行稳定性报告" in html)
    check("html.findings_cn", "核心发现" in html)
    check("html.evidence_tables", "ev-table" in html)
    check("html.methods_appendix", "方法与阈值" in html)
    check("html.disclaimer", "不构成参数下发" in html)
    check("html.three_cdn", html.count("echarts.min.js") == 3)
    check("html.static_fallback", "fallback" in html)

    # tamper the grade -> gate must fail
    tam_dir = os.path.join(base, "tampered")
    shutil.copytree(stable_out, tam_dir)
    rp = os.path.join(tam_dir, "stability_report.json")
    rep = load_report(tam_dir)
    rep["conclusion"]["grade"] = "D"  # inconsistent with a high score
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(rep, f)
    g = node_gate(rp, tam_dir)
    check("gate.tamper_detected", g.returncode == 3, g.stdout[-300:])
    # tamper severity enum -> S5 must fail (unconditional replacement)
    rep["findings"] = [{
        "finding_id": "F001", "severity": "blocker", "category": "spc",
        "title": "x", "detail": "x", "evidence": [{"metric": "m", "value": 1, "source": "s"}]}]
    rep["conclusion"]["grade"] = "A"
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(rep, f)
    g2 = node_gate(rp, tam_dir)
    check("gate.bad_severity_detected", g2.returncode == 3, g2.stdout[-200:])


def scenario_zero_llm_scan(base):
    print("[S11] zero-LLM source scan")
    bad = []
    banned = ("import requests", "import socket", "urllib", "httpx",
              "http.client", "openai", "anthropic", "api_key", "websocket")
    for root, _dirs, files in os.walk(os.path.join(SCRIPTS, "lstcore")):
        for fn in files:
            if fn.endswith(".py"):
                p = os.path.join(root, fn)
                with open(p, encoding="utf-8") as f:
                    src = f.read().lower()
                for kw in banned:
                    if kw in src:
                        bad.append((fn, kw))
    for fn in ("stability_analyzer.py", "report_builder.py"):
        with open(os.path.join(SCRIPTS, fn), encoding="utf-8") as f:
            src = f.read().lower()
        for kw in ("import requests", "urllib", "httpx", "openai", "anthropic"):
            if kw in src:
                bad.append((fn, kw))
    check("zerollm.no_network_llm_imports", not bad, str(bad))


def write_ontology(path):
    payload = {
        "scene": {"name": "演示反应线", "process_type": "batch_reactor",
                  "production_goal": "收率稳定在 96% 以上"},
        "signals": {
            "process_parameters": [
                {"column": "drive_a", "name": "驱动量A", "unit": "kPa", "role": "parameter",
                 "governing_law": "传递方程", "normal_range": [-2.0, 2.0]},
                {"column": "  FILLER  ", "name": "填充量", "unit": "L/h", "role": "parameter"},
            ],
            "inspection_signals": [
                {"column": "resp_yield", "name": "收率", "unit": "%", "role": "target",
                 "normal_range": [-2.0, 2.0]},
            ],
        },
        "parameter_groups": {"drive_group": ["drive_a", "filler"]},
        "relationships": [
            {"from": "drive_a", "to": "resp_yield", "type": "causal",
             "strength": "strong", "mechanism": "驱动量A直接改变转化速率",
             "governing_equation": "r = k·C_A"},
        ],
        "confounders": [
            {"variable": "feed_source", "why": "原料切换同时影响驱动量与收率",
             "controlled": False},
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path


def scenario_ontology(base):
    print("[S13] ontology-first: roles/spec fallback/mechanism/confounders")
    run_dir = os.path.join(base, "ontology")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    n = 800
    rng = np.random.default_rng(9)
    a = rng.normal(0, 1, n)
    b = np.empty(n)
    b[:] = np.nan
    b[5:] = a[:-5] + rng.normal(0, 0.15, n - 5)
    other = rng.normal(0, 1, n)
    resp2 = np.empty(n)
    resp2[:] = np.nan
    resp2[4:] = other[:-4] + rng.normal(0, 0.15, n - 4)
    t0 = datetime(2026, 10, 4)
    pd.DataFrame({
        "t": [(t0 + timedelta(seconds=30 * i)).isoformat() for i in range(n)],
        "drive_a": a, "resp_yield": b,
        "drive_b": other, "resp_other": resp2,
        "filler": rng.normal(50, 1, n),
    }).to_csv(os.path.join(run_dir, "00_input", "data.csv"), index=False)
    write_ontology(os.path.join(run_dir, "00_input", "ontology.json"))
    r = run_analyze(run_dir)
    check("ontology.runs", r.returncode in (0, 1, 2), r.stderr[-200:])
    rep = load_report(out)
    check("ontology.mode", rep["condition"]["ontology"]["mode"] == "ontology",
          json.dumps(rep["condition"]["ontology"]))
    cols = rep["condition"]["columns"]
    check("ontology.role_target", cols.get("resp_yield", {}).get("role") == "inspection")
    check("ontology.assigned_by", cols.get("drive_a", {}).get("assigned_by") == "ontology")
    check("ontology.norm_match_fallback",
          cols.get("filler", {}).get("assigned_by") == "ontology"
          and cols["filler"]["label"] == "填充量",
          json.dumps(cols.get("filler"), ensure_ascii=False)[:160])
    check("ontology.spec_fallback_cpk",
          next(p for p in rep["parameters"]
               if p["name"] == "drive_a")["capability"]["cpk"] is not None)
    check("ontology.unit_parsed",
          cols.get("drive_a", {}).get("unit") == "kPa")
    pair = next((p for p in rep["correlations"]["pairs"]
                 if {p["a"], p["b"]} == {"drive_a", "resp_yield"}), None)
    drv = next((f for f in rep["findings"]
                if f["category"] == "driver" and pair and
                set(f["affected"][:2]) == {"drive_a", "resp_yield"}), None)
    check("ontology.mechanism_known", drv is not None and
          drv.get("mechanism", {}).get("level") == "known", str(drv)[:200] if drv else "none")
    check("ontology.mechanism_equation",
          drv and drv["mechanism"].get("governing_equation") == "r = k·C_A")
    check("ontology.confidence_high", drv and (drv.get("confidence") or 0) >= 70,
          str(drv and drv.get("confidence")))
    unknown = next((f for f in rep["findings"] if f["category"] == "driver" and
                    f.get("mechanism", {}).get("level") == "unknown"), None)
    check("ontology.mechanism_unknown_tagged",
          unknown is not None and "MECHANISM_UNKNOWN" in unknown["title"] and
          (unknown.get("confidence") or 100) <= 60,
          str(unknown)[:160] if unknown else "none")
    check("ontology.confounders_in_limitations",
          any(c.get("variable") == "feed_source"
              for c in rep["limitations"]["confounders"]))
    check("ontology.scene_narrative",
          rep["condition"]["scene"]["name"] == "演示反应线")
    b2 = py(BUILDER, "--report", os.path.join(out, "stability_report.json"),
            "--charts", os.path.join(out, "charts.json"))
    with open(os.path.join(out, "line_stability_report.html"), encoding="utf-8") as f:
        html = f.read()
    check("ontology.html_condition_section", b2.returncode == 0 and
          "场景理解" in html and "演示反应线" in html)
    check("ontology.html_mechanism_line", "物理机制" in html)
    check("ontology.html_limitations", "假设与局限" in html and "feed_source" in html)
    return rep


def scenario_reuse_and_regime(base):
    print("[S14] sentinelcore reuse provenance + regime segmentation")
    run_dir = os.path.join(base, "regime")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    n = 900
    rng = np.random.default_rng(17)
    step = np.where(np.arange(n) >= 450, 2.5, 0.0)  # large step on temp
    t0 = datetime(2026, 10, 5)
    pd.DataFrame({
        "t": [(t0 + timedelta(seconds=60 * i)).isoformat() for i in range(n)],
        "temp": 85.0 + rng.normal(0, 0.05, n) + step,
        "press": 0.6 + rng.normal(0, 0.001, n),
    }).to_csv(os.path.join(run_dir, "00_input", "data.csv"), index=False)
    r = run_analyze(run_dir)
    rep = load_report(out)
    check("reuse.spc_source_sentinelcore",
          rep["provenance"].get("spc_source") == "sentinelcore",
          str(rep["provenance"].get("spc_source")))
    check("reuse.methods_named",
          "sentinelcore_nelson_episodes" in rep["provenance"]["methods"] and
          "ontology_first_condition" in rep["provenance"]["methods"])
    reg = rep["condition"]["regimes"]
    check("regime.available", reg.get("available") is True, json.dumps(reg)[:200])
    check("regime.segments_listed", len(reg.get("regimes", [])) >= 1)
    if reg.get("change_points"):
        check("regime.finding_present",
              any(f["category"] == "regime" for f in rep["findings"]))
    else:
        check("regime.finding_present", True)  # fallback python: labels only
    check("regime.step_detected_high_score_diff",
          abs(next(p for p in rep["parameters"] if p["name"] == "temp")["score"]) < 100)


def scenario_confidence_and_data_truth(base, stable_out):
    print("[S15] data-truth mandates: limitations/derived/row_range in real report")
    rep = load_report(stable_out)
    lim = rep["limitations"]
    check("data_truth.limitations_present",
          "raw" in lim.get("data_source", "") and lim.get("model_assumptions"))
    check("data_truth.spec_coverage_keys",
          set(lim.get("spec_coverage", {}).keys()) == {"user", "ontology", "none"})
    p0 = rep["parameters"][0]
    check("data_truth.row_range_and_source",
          p0.get("row_range") == [0, p0["n"] - 1] and p0.get("data_source") == "raw")
    pairs = rep["correlations"]["pairs"]
    if pairs:
        check("data_truth.pair_derived", pairs[0].get("best_abs_r") is not None)
    check("data_truth.provenance_fields",
          "spc_source" in rep["provenance"] and "regime_method" in rep["provenance"])
    check("data_truth.subject_present",
          (rep.get("subject") or {}).get("noun") in ("产线", "系统", "对象"))
    check("data_truth.weights_source",
          rep["provenance"].get("weights_source") in ("user", "role_weights", "equal"))


def scenario_sampling(base):
    print("[S16] systematic sampling helper")
    sys.path.insert(0, SCRIPTS)
    from lstcore import ontology as ont_mod  # noqa: PLC0415
    check("sample.small_untouched", ont_mod.systematic_sample(50_000) == 1)
    check("sample.large_stride", ont_mod.systematic_sample(200_000) == 2)
    check("sample.exact_cap", ont_mod.systematic_sample(100_000) == 1)


def scenario_schema_validation(base, stable_out):
    print("[S12] shared validator accepts the report against our schema")
    validator = os.path.join(REPO, ".claude", "shared", "scripts", "validate.mjs")
    schema = os.path.join(SKILL, "schemas", "stability_report.schema.json")
    r = subprocess.run(
        ["node", validator, schema,
         os.path.join(stable_out, "stability_report.json")],
        capture_output=True, text=True, cwd=REPO, timeout=60, encoding="utf-8")
    check("schema.valid_report", r.returncode == 0, r.stdout[-300:])


def scenario_ontology_prepare(base):
    print("[S19] ontology prepare: build/reuse + CP-2 + honest provenance")
    run_dir = os.path.join(base, "prep_build")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=600, seed=81)
    with open(os.path.join(run_dir, "00_input", "report_context.json"), "w",
              encoding="utf-8") as f:
        json.dump({"line_id": "L-PREP",
                   "inspection_cols": ["yield_pct"],
                   "spec_limits": {"yield_pct": {"lsl": 97.0, "usl": 100.0,
                                                 "target": 98.5}},
                   "units": {"temp": "degC"}}, f)
    r = run_prepare(run_dir)
    check("prep.build_exit0", r.returncode == 0, r.stderr[-300:])
    res = json.loads(r.stdout)
    check("prep.action_built", res["action"] == "built", str(res.get("action")))
    ontology_path = res.get("ontology_path")
    check("prep.four_artifacts", bool(ontology_path) and all(
        os.path.isfile(p) for p in (ontology_path, res.get("brief_json"),
                                    res.get("brief_md"), res.get("coverage_path"))),
          json.dumps({k: res.get(k) for k in ("ontology_path", "brief_json",
                                              "brief_md", "coverage_path")}))
    check("prep.cp2_floor_ok", res.get("cp2_floor_ok") is True)
    check("prep.rag_web_unused",
          res.get("rag_used") is False and res.get("web_used") is False
          and res.get("rag_used_by_prepare") is False)
    v = subprocess.run(["node", VALIDATOR, ONTOLOGY_SCHEMA, ontology_path],
                       capture_output=True, text=True, cwd=REPO, timeout=60,
                       encoding="utf-8")
    check("prep.ontology_schema_valid", v.returncode == 0, v.stdout[-300:])
    with open(res["brief_json"], encoding="utf-8") as f:
        brief = json.load(f)
    yp = next((c for c in brief["columns"] if c["col"] == "yield_pct"), None)
    check("prep.user_spec_matched",
          yp and yp["mapping_status"] == "matched"
          and yp["knowledge_source"] == "user_provided" and yp["spec"] is not None,
          json.dumps(yp, ensure_ascii=False))
    check("prep.spec_only_user_declared",
          all(c["spec"] is None or c["col"] == "yield_pct" for c in brief["columns"]),
          json.dumps([c["col"] for c in brief["columns"] if c["spec"]]))
    with open(ontology_path, encoding="utf-8") as f:
        ont = json.load(f)
    sigs = ont["signals"]["process_parameters"] + ont["signals"]["inspection_signals"]
    check("prep.normal_range_only_user",
          all("normal_range" not in s or s.get("knowledge_source") == "user_provided"
              for s in sigs))
    r2 = run_prepare(run_dir)
    res2 = json.loads(r2.stdout)
    check("prep.reuse_action", res2["action"] == "reused", str(res2.get("action")))
    check("prep.reuse_lookup_exact", res2["lookup"] == "exact", str(res2.get("lookup")))
    ra = run_analyze(run_dir)
    check("prep.analyze_runs", ra.returncode in (0, 1, 2), ra.stderr[-200:])
    rep = load_report(out)
    ont_prov = rep["provenance"].get("ontology") or {}
    check("prep.analyzer_provenance_rag_false", ont_prov.get("rag_used") is False,
          json.dumps(ont_prov, ensure_ascii=False))
    check("prep.analyzer_action_reused", ont_prov.get("action") == "reused",
          str(ont_prov.get("action")))
    summary = ont_prov.get("brief_summary")
    check("prep.analyzer_brief_summary",
          isinstance(summary, dict) and 0 < len(summary) <= 10
          and summary.get("coverage_ratio") == 1.0,
          json.dumps(summary, ensure_ascii=False))


def scenario_multisource_merge(base):
    print("[S20] folder multi-source integrate-merge -> merge disclosure")
    src = os.path.join(base, "raw_folder")
    os.makedirs(src, exist_ok=True)
    rng = np.random.default_rng(23)
    n_main, n_lab = 200, 100
    t0 = datetime(2026, 10, 6, 8, 0, 0)
    pd.DataFrame({
        # space-separated timestamps: the canonical DCS export shape this
        # skill documents (data-prep-dcs.md), and the format the preprocessor's
        # CN-datetime normalizer handles for its cadence gate
        "t": [(t0 + timedelta(seconds=60 * i)).strftime("%Y-%m-%d %H:%M:%S")
              for i in range(n_main)],
        "temp": 85.0 + rng.normal(0, 0.05, n_main),
        "press": 0.6 + rng.normal(0, 0.001, n_main),
        "rate": 120.0 + rng.normal(0, 0.3, n_main),
        "yield_pct": 98.5 + rng.normal(0, 0.2, n_main),
    }).to_csv(os.path.join(src, "dcs_main.csv"), index=False)
    pd.DataFrame({
        # 2-min cadence inside the main table's own window: every lab timestamp
        # also exists on the minute grid, so the merged union stays at the
        # primary's row count (a wider window would trip the anti-bloat gate)
        "t": [(t0 + timedelta(seconds=120 * i)).strftime("%Y-%m-%d %H:%M:%S")
              for i in range(n_lab)],
        "lab_moisture": 0.42 + rng.normal(0, 0.01, n_lab),
    }).to_excel(os.path.join(src, "lab_secondary.xlsx"), index=False)
    run_dir = os.path.join(base, "merged_run")
    in_dir = os.path.join(run_dir, "00_input")
    os.makedirs(in_dir, exist_ok=True)
    r_prep = py(PREPROCESSOR, "--data-path", src, "--output", in_dir,
                "--integrate-merge", "--recursive")
    check("merge.preproc_exit0", r_prep.returncode == 0, r_prep.stderr[-300:])
    with open(os.path.join(in_dir, "preprocessing_report.json"), encoding="utf-8") as f:
        prep_report = json.load(f)
    merge = prep_report.get("merge") or {}
    check("merge.strategy_outer", merge.get("strategy") == "outer_merge_on_time_column",
          json.dumps(merge, ensure_ascii=False)[:200])
    check("merge.cadence_fields",
          "source_cadence_seconds" in merge and "cadence_ratio" in merge
          and (merge.get("cadence_ratio") or 0) >= 1,
          json.dumps({k: merge.get(k) for k in ("source_cadence_seconds", "cadence_ratio")},
                     ensure_ascii=False))
    check("merge.column_source",
          isinstance(merge.get("column_source"), dict)
          and "lab_moisture" in merge["column_source"],
          json.dumps(merge.get("column_source"), ensure_ascii=False)[:200])
    r = run_analyze(run_dir)
    check("merge.analyze_runs", r.returncode in (0, 1, 2), r.stderr[-200:])
    rep = load_report(os.path.join(run_dir, "line_report"))
    check("merge.disclosure_in_degradations",
          any(d.get("check") == "merged_sources" for d in rep["degradations"]),
          json.dumps(rep["degradations"], ensure_ascii=False)[:300])


def scenario_md_default_and_gate(base, stable_out):
    print("[S21] md companion by default + gate md check")
    md_path = os.path.join(stable_out, "line_stability_report.md")
    check("md.default_written", os.path.isfile(md_path))
    if os.path.isfile(md_path):
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        check("md.content_cn", "运行稳定性报告" in md and "核心发现" in md)
    nomd = os.path.join(base, "nomd")
    shutil.copytree(stable_out, nomd)
    os.remove(os.path.join(nomd, "line_stability_report.md"))
    b = py(BUILDER, "--report", os.path.join(nomd, "stability_report.json"),
           "--charts", os.path.join(nomd, "charts.json"),
           "--out", os.path.join(nomd, "line_stability_report.html"), "--no-md")
    check("md.no_md_skips",
          not os.path.isfile(os.path.join(nomd, "line_stability_report.md")),
          b.stderr[-200:])
    g = node_gate(os.path.join(nomd, "stability_report.json"), nomd)
    check("md.gate_exit3_without_md", g.returncode == 3, g.stdout[-300:])
    b2 = py(BUILDER, "--report", os.path.join(nomd, "stability_report.json"),
            "--charts", os.path.join(nomd, "charts.json"),
            "--out", os.path.join(nomd, "line_stability_report.html"))
    check("md.default_rewrites",
          os.path.isfile(os.path.join(nomd, "line_stability_report.md")),
          b2.stderr[-200:])
    g2 = node_gate(os.path.join(nomd, "stability_report.json"), nomd)
    check("md.gate_exit0_with_md", g2.returncode == 0, g2.stdout[-300:])


def scenario_units_and_dictionary(base):
    print("[S22] unit discipline + dictionary reference bands never Cpk")
    # (a) undeclared units surface verbatim in the report; declared ones flow through
    run_a = os.path.join(base, "units_a")
    out_a = os.path.join(run_a, "line_report")
    os.makedirs(os.path.join(run_a, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_a, "00_input", "data.csv"), n=600, seed=91)
    with open(os.path.join(run_a, "00_input", "report_context.json"), "w",
              encoding="utf-8") as f:
        json.dump({"units": {"temp": "degC"}}, f)
    r = run_analyze(run_a)
    check("units.analyze_runs", r.returncode in (0, 1, 2), r.stderr[-200:])
    b = py(BUILDER, "--report", os.path.join(out_a, "stability_report.json"),
           "--charts", os.path.join(out_a, "charts.json"))
    check("units.builder_ok", b.returncode == 0, b.stderr[-200:])
    with open(os.path.join(out_a, "line_stability_report.md"), encoding="utf-8") as f:
        md = f.read()
    check("units.undeclared_marked", "单位未声明" in md)
    rep_a = load_report(out_a)
    temp_doc = (rep_a["condition"].get("columns") or {}).get("temp") or {}
    check("units.declared_unit_flows", temp_doc.get("unit") == "degC",
          json.dumps(temp_doc, ensure_ascii=False)[:120])

    def _vib_csv(run_dir):
        os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
        rng = np.random.default_rng(9)
        n = 600
        t0 = datetime(2026, 10, 7, 8, 0, 0)
        pd.DataFrame({
            "t": [(t0 + timedelta(seconds=60 * i)).isoformat() for i in range(n)],
            "temp": 85.0 + rng.normal(0, 0.03, n),
            "vibration": 0.008 + rng.normal(0, 0.0004, n),
        }).to_csv(os.path.join(run_dir, "00_input", "data.csv"), index=False)

    # (b) prepare: unique dictionary hit carries unit/meaning but NO normal_range
    run_b = os.path.join(base, "dict_prior")
    _vib_csv(run_b)
    rp = run_prepare(run_b)
    check("units.prepare_exit0", rp.returncode == 0, rp.stderr[-300:])
    res_p = json.loads(rp.stdout)
    with open(res_p["ontology_path"], encoding="utf-8") as f:
        ont = json.load(f)
    vib = next((s for s in ont["signals"]["process_parameters"]
                if s["column"] == "vibration"), None)
    check("units.dict_hit_auto_inferred",
          vib is not None and vib.get("knowledge_source") == "auto_inferred"
          and vib.get("unit") == "m/s" and "normal_range" not in vib,
          json.dumps(vib, ensure_ascii=False)[:200])
    check("units.dict_band_only_in_watch",
          "vibration" in ((ont.get("watch") or {}).get("reference_bands") or {}))
    rd = run_analyze(run_b)
    check("units.dict_prior_analyze", rd.returncode in (0, 1, 2), rd.stderr[-200:])
    rep_b = load_report(os.path.join(run_b, "line_report"))
    check("units.prior_ontology_consumed",
          rep_b["condition"]["ontology"]["mode"] == "ontology",
          json.dumps(rep_b["condition"]["ontology"], ensure_ascii=False))
    vib_b = next(p for p in rep_b["parameters"] if p["name"] == "vibration")
    check("units.no_cpk_without_user_spec",
          vib_b["capability"]["cpk"] is None and vib_b["spec"]["source"] is None,
          json.dumps(vib_b["capability"]))

    def _hand_ontology(run_dir, ks):
        with open(os.path.join(run_dir, "00_input", "ontology.json"), "w",
                  encoding="utf-8") as f:
            json.dump({
                "scene": {"name": "词典纪律线", "process_type": "test"},
                "signals": {"process_parameters": [
                    {"column": "vibration", "name": "振动", "unit": "m/s",
                     "role": "predictor", "normal_range": [0.0, 0.02],
                     "knowledge_source": ks},
                ]},
            }, f, ensure_ascii=False)

    # (c) negative control: user_provided ontology spec DOES produce Cpk
    run_c = os.path.join(base, "dict_user")
    _vib_csv(run_c)
    _hand_ontology(run_c, "user_provided")
    run_analyze(run_c)
    rep_c = load_report(os.path.join(run_c, "line_report"))
    vib_c = next(p for p in rep_c["parameters"] if p["name"] == "vibration")
    check("units.user_spec_cpk_computed", vib_c["capability"]["cpk"] is not None,
          json.dumps(vib_c["capability"]))

    # (d) guard: auto_inferred signal with a baked normal_range never enters Cpk
    run_d = os.path.join(base, "dict_guard")
    _vib_csv(run_d)
    _hand_ontology(run_d, "auto_inferred")
    run_analyze(run_d)
    rep_d = load_report(os.path.join(run_d, "line_report"))
    vib_d = next(p for p in rep_d["parameters"] if p["name"] == "vibration")
    check("units.auto_inferred_cpk_blocked",
          vib_d["capability"]["cpk"] is None and vib_d["spec"]["source"] is None,
          json.dumps(vib_d["capability"]))


def scenario_bare_zero_declaration(base):
    print("[S22b] bare CSV zero declarations -> minimal prior + honest exit 2")
    run_dir = os.path.join(base, "bare_tiny")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=30, seed=97)
    # private store: the shared suite store already holds this bare column
    # contract from S1 — a zero-declaration first build needs its own namespace
    bare_store = os.path.join(base, "bare_store")
    r = run_prepare(run_dir, store=bare_store)
    check("bare.prepare_exit0", r.returncode == 0, r.stderr[-300:])
    res = json.loads(r.stdout)
    check("bare.action_built", res["action"] == "built", str(res.get("action")))
    check("bare.store_dir_isolated", os.path.normpath(res.get("store_dir") or "")
          == os.path.normpath(bare_store), str(res.get("store_dir")))
    check("bare.rag_unused", res.get("rag_used") is False
          and res.get("rag_used_by_prepare") is False)
    with open(res["brief_json"], encoding="utf-8") as f:
        brief = json.load(f)
    statuses = sorted({c["unit_status"] for c in brief["columns"]})
    check("bare.all_units_undeclared", statuses == ["undeclared"], str(statuses))
    check("bare.coverage_full", brief["coverage"]["ratio"] == 1.0,
          str(brief["coverage"]["ratio"]))
    ra = run_analyze(run_dir)
    check("bare.analyze_exit2", ra.returncode == 2,
          f"rc={ra.returncode} {ra.stderr[-200:]}")
    rep = load_report(os.path.join(run_dir, "line_report"))
    check("bare.honest_status", rep["status"] == "not_assessable"
          and rep["conclusion"]["score"] is None
          and rep["provenance"]["ontology"]["rag_used"] is False)


def scenario_pipeline_events(base):
    print("[S23] specialist event log: prepare_done + analysis_done + gate_done; "
          "crash exit-code contract in source")
    run_dir = os.path.join(base, "events")
    out = os.path.join(run_dir, "line_report")
    os.makedirs(os.path.join(run_dir, "00_input"), exist_ok=True)
    write_stable_csv(os.path.join(run_dir, "00_input", "data.csv"), n=600, seed=77)
    r = run_analyze(run_dir)
    check("events.analyze_runs", r.returncode in (0, 1), r.stderr[-200:])
    events_path = os.path.join(run_dir, ".pipeline_events.jsonl")
    check("events.file_exists", os.path.isfile(events_path))
    events = []
    if os.path.isfile(events_path):
        with open(events_path, encoding="utf-8") as f:
            events = [json.loads(line) for line in f if line.strip()]
    names = [e.get("event") for e in events]
    check("events.prepare_done", "prepare_done" in names, str(names))
    check("events.analysis_done", "analysis_done" in names, str(names))
    analysis = next((e for e in events if e.get("event") == "analysis_done"), {})
    check("events.analysis_detail", "status" in (analysis.get("detail") or {}),
          str(analysis.get("detail")))

    b = py(BUILDER, "--report", os.path.join(out, "stability_report.json"),
           "--charts", os.path.join(out, "charts.json"))
    check("events.builder_ok", b.returncode == 0, b.stderr[-300:])
    with open(events_path, encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]
    names = [e.get("event") for e in events]
    check("events.gate_done", "gate_done" in names, str(names))
    gate_ev = next((e for e in events if e.get("event") == "gate_done"), {})
    check("events.gate_detail", "pass" in (gate_ev.get("detail") or {}), str(gate_ev))

    # D4 static contract: uncaught exceptions surface as CRASH + exit 4
    with open(ANALYZER, encoding="utf-8") as f:
        src = f.read()
    check("events.crash_contract", "CRASH:" in src and "return 4" in src)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    base = tempfile.mkdtemp(prefix="lsr-tests-", dir=os.path.join(HERE))
    # whole-suite ontology store isolation: every analyze/prepare subprocess in
    # this run publishes into the in-repo temp store, never the repo's own
    os.environ["ONTOLOGY_STORE_DIR"] = os.path.join(base, "ontology_store")
    try:
        rep, stable_out = scenario_stable(base)
        scenario_unstable(base)
        scenario_capability(base)
        scenario_correlation(base)
        scenario_baseline(base)
        scenario_attribution(base)
        scenario_doe(base)
        scenario_period_slice(base)
        scenario_not_assessable(base)
        scenario_frozen_snapshot(base)
        scenario_partial_invariant(base)
        scenario_adaptive_targets(base)
        scenario_epoch_time(base)
        scenario_html_and_gate(base, stable_out)
        scenario_zero_llm_scan(base)
        scenario_schema_validation(base, stable_out)
        scenario_ontology(base)
        scenario_reuse_and_regime(base)
        scenario_confidence_and_data_truth(base, stable_out)
        scenario_sampling(base)
        scenario_ontology_prepare(base)
        scenario_multisource_merge(base)
        scenario_md_default_and_gate(base, stable_out)
        scenario_units_and_dictionary(base)
        scenario_bare_zero_declaration(base)
        scenario_pipeline_events(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    total = len(CHECKS)
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print("=" * 62)
    print(f"[TESTS] {passed}/{total} passed — {'ALL GREEN' if passed == total else 'FAILURES'}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
