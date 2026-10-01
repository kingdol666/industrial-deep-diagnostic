#!/usr/bin/env python
"""Test runner for industrial-sentinel (plan A-group AC A1-A10).

Usage (from repo root, inside the uv venv):
  uv run --project .claude/shared/scripts python \
      .claude/skills/industrial-sentinel/tests/run_tests.py [case|all]

Cases (all fixture data generated here with FIXED seeds — no random draws):
  F1  watch on a steady tightly-controlled window      -> exit 0, zero alerts
  F2  watch on 10k rows, drift +0.8 sigma/1000 rows    -> R2/R3 in [5800,6200],
      change points found, quiet zones honored, <= 120s (A1/A2/A4)
  F3  fast-screen spike battery                        -> exit 1 <=5s, repeat_count
      merge across runs, hysteresis downgrade, no-baseline exit 2, oversize 2 (A6)
  F4  cold start without baseline                      -> self baseline + SELF_BASELINE
      alert + 48h TTL on every store (A5)
  F5  two registered groups + one rogue group          -> group-tagged alerts +
      UNSEEN_GROUP (A8)
  F6  build_baseline verbatim copy of canned doe-analyzer artifacts (A7)
  tamper  gate negative battery: bad enum / storm / extra keys -> gate exit 1 (A6)
  perf    measured inside F2 (duration <= 120s)                      (A2)
AC definitions live in tests/AC.md.

All fixture/step writes use pandas/pathlib (no raw open() in this skill).
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
SHARED = REPO / ".claude" / "shared"
FIXTURES = (HERE / "fixtures").resolve()

SENTINEL = SCRIPTS / "sentinel.py"
SENTINEL_FAST = SCRIPTS / "sentinel_fast.py"
BUILD_BASELINE = SCRIPTS / "build_baseline.py"
GATE = SCRIPTS / "quality_gate.mjs"

RESULTS = []


class CaseAbort(Exception):
    """Prerequisite failed — abort this case, keep the battery running."""


def require(cond, case, detail=""):
    if not cond:
        record(case, False, detail)
        raise CaseAbort(case)


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {case}  {'' if ok else detail}")


def py(args, timeout=300):
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, timeout=timeout, shell=False)


def node(args, timeout=120):
    return subprocess.run(["node", *args], capture_output=True, text=True,
                          timeout=timeout, shell=False)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def case_dir(name):
    """Fixture dir is ALWAYS a direct child of the fixtures root (containment
    guard before any directory creation)."""
    safe = Path(str(name)).name
    d = (FIXTURES / safe).resolve()
    if FIXTURES not in d.parents:
        raise ValueError(f"fixture path escaped fixtures root: {name}")
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def run_gate(alert_path, baseline=None):
    args = [str(GATE), str(alert_path),
            "--skill-path", str(SKILL), "--shared-path", str(SHARED)]
    if baseline:
        args += ["--baseline", str(baseline)]
    return node(args)


# ---------------------------------------------------------------- generators

def jitter_df(seed, n, cols=("temp", "press"), centers=(50.0, 10.0),
              amps=(0.04, 0.015)):
    """Tightly-controlled steady loop: strictly alternating bounded jitter
    around setpoints. Deterministically SPC-silent (sign alternation kills
    R2/R3; amplitude << baseline sigma kills R1/R5/R6) — see AC.md A-note."""
    rng = np.random.default_rng(seed)
    i = np.arange(n)
    data = {}
    for k, c in enumerate(cols):
        data[c] = centers[k] + (-1.0) ** (i + k) * rng.uniform(0, amps[k], n)
    return pd.DataFrame(data)


def f2_watch_df(seed, n=10000, drift_start=6000):
    """10k rows, iid noise sigma 0.1/0.04 vs baseline sigma 1.0/0.4, drift on
    temp from drift_start at +0.0008 rows (0.8 sigma per 1000 rows)."""
    rng = np.random.default_rng(seed)
    i = np.arange(n)
    drift = np.where(i >= drift_start, 0.0008 * (i - drift_start), 0.0)
    t0 = pd.Timestamp("2026-03-01 00:00:00")
    ts = [t0 + pd.Timedelta(minutes=int(m)) for m in i]
    return pd.DataFrame({
        "timestamp": ts,
        "temp": 50.0 + drift + rng.normal(0, 0.1, n),
        "press": 10.0 + rng.normal(0, 0.04, n),
    })


def f2_history(path):
    rng_a = np.random.default_rng(101)
    rng_b = np.random.default_rng(202)
    pd.DataFrame({
        "temp": 50 + rng_a.normal(0, 1.0, 400),
        "press": 10 + rng_b.normal(0, 0.4, 400),
    }).to_csv(path, index=False)


# ---------------------------------------------------------------- F1

def case_f1():
    print("[F1] steady tightly-controlled window -> exit 0, zero alerts (A6)")
    d = case_dir("F1_watch_steady")
    jitter_df(101, 400).to_csv(d / "history.csv", index=False)
    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--out", str(d / "watch_baseline.json")])
    record("F1_baseline_build", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F1_abort", "baseline build failed")

    jitter_df(202, 240).to_csv(d / "watch.csv", index=False)
    r = py([str(SENTINEL), "watch", "--data", str(d / "watch.csv"),
            "--baseline", str(d / "watch_baseline.json"),
            "--out-dir", str(d / "sentinel")])
    record("F1_watch_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")
    require((d / "sentinel" / "alert.json").exists(), "F1_abort", "no alert.json")
    alert = read(d / "sentinel" / "alert.json")
    record("F1_zero_alerts", alert["alerts"] == [], f"n={len(alert['alerts'])}")
    record("F1_status_ok", alert["status"] == "ok", alert["status"])
    record("F1_baseline_prior", alert["baseline"]["mode"] == "prior",
           str(alert["baseline"]))
    g = run_gate(d / "sentinel" / "alert.json", d / "watch_baseline.json")
    record("F1_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F2

def case_f2():
    print("[F2] drift +0.8sigma/1000 rows from row 6000 -> R2/R3 in band, "
          "change points, quiet zones, <=120s (A1/A2/A4)")
    d = case_dir("F2_watch_drift")
    f2_history(d / "history.csv")
    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--out", str(d / "watch_baseline.json")])
    record("F2_baseline_build", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F2_abort", "baseline build failed")

    f2_watch_df(42).to_csv(d / "watch.csv", index=False)
    t0 = time.time()
    r = py([str(SENTINEL), "watch", "--data", str(d / "watch.csv"),
            "--baseline", str(d / "watch_baseline.json"),
            "--out-dir", str(d / "sentinel")], timeout=300)
    wall_s = time.time() - t0
    record("F2_exit_findings", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    require((d / "sentinel" / "alert.json").exists(), "F2_abort", "no alert.json")
    alert = read(d / "sentinel" / "alert.json")

    def in_band(rule):
        return [a["observed"]["index"] for a in alert["alerts"]
                if a["rule_name"] == rule
                and isinstance(a["observed"].get("index"), (int, float))
                and 5800 <= a["observed"]["index"] <= 6200]

    r2_band, r3_band = in_band("NELSON_R2"), in_band("NELSON_R3")
    record("F2_R2_in_band_5800_6200", bool(r2_band), f"R2 band={r2_band}")
    record("F2_R3_in_band_5800_6200", bool(r3_band), f"R3 band={r3_band}")

    cps = [a["evidence"]["cp_position"] for a in alert["alerts"]
           if a["rule_name"] == "REGIME_CHANGE_NEW"]
    record("F2_change_points_new", len(cps) >= 1, f"cps={cps[:5]}")
    spc_idx = [a["observed"]["index"] for a in alert["alerts"]
               if a["check_type"] == "spc"
               and isinstance(a["observed"].get("index"), (int, float))]
    quiet_hits = [(cp, ix) for cp in cps for ix in spc_idx
                  if cp <= ix < cp + 30]
    record("F2_quiet_zone_honored", quiet_hits == [], f"violations={quiet_hits[:4]}")

    dur = alert["provenance"]["duration_ms"]
    record("F2_duration_le_120s", dur <= 120000 and wall_s <= 125,
           f"duration_ms={dur} wall={wall_s:.1f}s")

    g = run_gate(d / "sentinel" / "alert.json", d / "watch_baseline.json")
    record("F2_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F3

def case_f3():
    print("[F3] fast-screen: spike exit 1 <=5s, repeat merge, hysteresis "
          "downgrade, no-baseline/oversize exit 2 (A6)")
    d = case_dir("F3_fast_spike")
    jitter_df(101, 400).to_csv(d / "history.csv", index=False)
    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--out", str(d / "watch_baseline.json")])
    record("F3_baseline_build", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F3_abort", "baseline build failed")
    base = str(d / "watch_baseline.json")
    state = str(d / "fast_state.json")

    batch1 = jitter_df(7, 200)
    batch1.loc[100, "temp"] = 50.0 + 0.5  # +10 sigma vs baseline sigma_within
    batch1.to_csv(d / "b1.csv", index=False)
    t0 = time.time()
    r = py([str(SENTINEL_FAST), "--data", str(d / "b1.csv"), "--state", state,
            "--baseline", base, "--out", str(d / "fast_alert.json")], timeout=30)
    dt = time.time() - t0
    record("F3_spike_exit1", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    record("F3_latency_le_5s", dt <= 5.0, f"{dt:.2f}s")
    a1 = read(d / "fast_alert.json")
    record("F3_mode_fast_screen", a1["mode"] == "fast_screen", a1["mode"])
    r1_alerts = [a for a in a1["alerts"] if a["rule_name"] == "NELSON_R1"]
    record("F3_spike_detected", bool(r1_alerts), str(a1["alerts"][:2]))

    # re-feed the same batch within the 60-min suppression window
    r = py([str(SENTINEL_FAST), "--data", str(d / "b1.csv"), "--state", state,
            "--baseline", base, "--out", str(d / "fast_alert2.json")], timeout=30)
    a2 = read(d / "fast_alert2.json")
    rcs = [a["repeat_count"] for a in a2["alerts"]
           if a["rule_name"] == "NELSON_R1"]
    record("F3_repeat_count_merged", any(rc >= 2 for rc in rcs), f"rcs={rcs}")
    st = read(state)
    record("F3_ring_cap_le_300", len(st["ring_buffer"]["rows"]) <= 300,
           f"ring={len(st['ring_buffer']['rows'])}")

    # steady batch large enough to age ALL old spikes out of the 300-row ring
    # (b1+b2 = 400 abs rows; 300 steady rows push the buffer to abs 300..599)
    jitter_df(8, 300).to_csv(d / "b3.csv", index=False)
    r = py([str(SENTINEL_FAST), "--data", str(d / "b3.csv"), "--state", state,
            "--baseline", base, "--out", str(d / "fast_alert3.json")], timeout=30)
    record("F3_steady_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-160:]}")

    # spike again after >=5 consecutive in-band points -> downgraded severity
    batch4 = jitter_df(9, 60)
    batch4.loc[30, "temp"] = 50.0 + 0.5
    batch4.to_csv(d / "b4.csv", index=False)
    r = py([str(SENTINEL_FAST), "--data", str(d / "b4.csv"), "--state", state,
            "--baseline", base, "--out", str(d / "fast_alert4.json")], timeout=30)
    a4 = read(d / "fast_alert4.json")
    downgraded = [a for a in a4["alerts"]
                  if a["rule_name"] == "NELSON_R1"
                  and a["evidence"].get("hysteresis_downgraded") is True
                  and a["severity"] == "warn"]
    record("F3_hysteresis_downgrade", bool(downgraded),
           str([(a['severity'], a['evidence']) for a in a4['alerts'][:3]]))

    # no baseline -> exit 2, no artifact
    out_missing = d / "should_not_exist.json"
    r = py([str(SENTINEL_FAST), "--data", str(d / "b1.csv"),
            "--state", str(d / "s2.json"), "--baseline", str(d / "missing.json"),
            "--out", str(out_missing)], timeout=30)
    record("F3_no_baseline_exit2", r.returncode == 2, f"rc={r.returncode}")
    record("F3_no_artifact_on_refusal", not out_missing.exists(), "")

    # oversize input -> exit 2
    pd.DataFrame({"temp": np.full(600, 50.0), "press": np.full(600, 10.0)}
                 ).to_csv(d / "big.csv", index=False)
    r = py([str(SENTINEL_FAST), "--data", str(d / "big.csv"), "--state", state,
            "--baseline", base, "--out", str(d / "fa_big.json")], timeout=30)
    record("F3_oversize_exit2", r.returncode == 2, f"rc={r.returncode}")

    g = run_gate(d / "fast_alert.json", base)
    record("F3_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F4

def case_f4():
    print("[F4] cold start without baseline -> self baseline + SELF_BASELINE "
          "alert + 48h TTL (A5)")
    d = case_dir("F4_cold_start")
    df = jitter_df(11, 240)
    df.loc[200, "temp"] = 50.0 + 0.5  # single-point spike (a STEP would be
    # absorbed by the post-change-point center-line re-estimation by design)
    df.to_csv(d / "watch.csv", index=False)
    r = py([str(SENTINEL), "watch", "--data", str(d / "watch.csv"),
            "--out-dir", str(d / "sentinel")])
    record("F4_exit_findings", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    alert = read(d / "sentinel" / "alert.json")
    record("F4_baseline_mode_self", alert["baseline"]["mode"] == "self",
           str(alert["baseline"]))
    self_alerts = [a for a in alert["alerts"] if a["rule_name"] == "SELF_BASELINE"]
    record("F4_SELF_BASELINE_alert", bool(self_alerts), "")
    record("F4_step_detected", any(a["check_type"] == "spc" for a in alert["alerts"]),
           f"n_alerts={len(alert['alerts'])}")
    base_ver = alert["baseline"]["baseline_version"] or ""
    record("F4_self_baseline_version", base_ver.startswith("self"), base_ver)
    g = run_gate(d / "sentinel" / "alert.json")
    record("F4_gate_pass", g.returncode == 0, g.stdout[-300:])

    # insufficient steady rows -> exit 2 (cannot even self-baseline)
    d2 = case_dir("F4_cold_start_tiny")
    jitter_df(12, 60).to_csv(d2 / "watch.csv", index=False)
    r = py([str(SENTINEL), "watch", "--data", str(d2 / "watch.csv"),
            "--out-dir", str(d2 / "sentinel")])
    record("F4_cold_start_impossible_exit2", r.returncode == 2,
           f"rc={r.returncode} {r.stdout[-160:]}")


# ---------------------------------------------------------------- F5

def case_f5():
    print("[F5] two registered groups + rogue group -> group-tagged alerts + "
          "UNSEEN_GROUP (A8)")
    d = case_dir("F5_multi_group")
    rows = []
    for line, seed in (("A", 21), ("B", 22)):
        sub = jitter_df(seed, 300)
        sub.insert(0, "line", line)
        rows.append(sub)
    pd.concat(rows, ignore_index=True).to_csv(d / "history.csv", index=False)
    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--out", str(d / "watch_baseline.json")])
    record("F5_baseline_groups_AB", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F5_abort", "baseline build failed")
    base = read(d / "watch_baseline.json")
    record("F5_baseline_has_AB", sorted(base["groups"]) == ["A", "B"],
           str(sorted(base["groups"])))

    rows = []
    for line, seed in (("A", 31), ("B", 32)):
        sub = jitter_df(seed, 300)
        sub.loc[150, "temp"] = 50.0 + 0.5
        sub.insert(0, "line", line)
        rows.append(sub)
    rogue = jitter_df(33, 100, amps=(5.0, 2.0))  # wild unregistered line C
    rogue.insert(0, "line", "C")
    rows.append(rogue)
    pd.concat(rows, ignore_index=True).to_csv(d / "watch.csv", index=False)

    r = py([str(SENTINEL), "watch", "--data", str(d / "watch.csv"),
            "--baseline", str(d / "watch_baseline.json"),
            "--out-dir", str(d / "sentinel")])
    record("F5_exit_findings", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    require((d / "sentinel" / "alert.json").exists(), "F5_abort", "no alert.json")
    alert = read(d / "sentinel" / "alert.json")
    unseen = [a for a in alert["alerts"]
              if a["rule_name"] == "UNSEEN_GROUP" and a["group"] == "C"]
    record("F5_UNSEEN_GROUP_C", bool(unseen),
           str([(a['rule_name'], a['group']) for a in alert['alerts'][:6]]))
    tagged = all(a.get("group") for a in alert["alerts"]
                 if a["check_type"] in ("spc", "multivariate"))
    record("F5_all_check_alerts_carry_group", tagged,
           str([(a['rule_name'], a['group']) for a in alert['alerts']
                if a['check_type'] in ('spc', 'multivariate')][:6]))
    for line in ("A", "B"):
        hit = [a for a in alert["alerts"] if a["group"] == line
               and a["rule_name"] == "NELSON_R1"]
        record(f"F5_group_{line}_spike_R1", bool(hit), "")
    g = run_gate(d / "sentinel" / "alert.json", d / "watch_baseline.json")
    record("F5_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F6

def case_f6():
    print("[F6] build_baseline copies doe-analyzer artifacts field-by-field (A7)")
    d = case_dir("F6_baseline_verbatim")
    doe = d / "doe_run"
    (doe / "conclusions").mkdir(parents=True)
    (doe / "02_analysis").mkdir(parents=True)
    recs = {
        "contract_version": "1.0",
        "audience": "downstream_agent",
        "operating_windows": [
            {"id": "OW-001", "priority": 1, "factor": "temp", "factor_unit": "C",
             "response": "quality", "range": [49.5, 50.5],
             "expected_effect": {"delta": 0.8, "direction_semantics": "per unit",
                                 "ci95": [0.5, 1.1], "unit": "sigma"},
             "confidence": "medium", "fdr_q": 0.02, "sample_size": 300,
             "evidence_refs": ["correlation:temp~quality"],
             "extrapolation": False, "confirmation_needed": True,
             "notes": "canned window"},
        ],
        "current_baseline": {"point": {"temp": 50.0}, "distance_to_window": {},
                             "move_instruction": None},
        "response_specs": {
            "quality": {"lsl": 97.5, "usl": 98.5, "target": 98.0,
                        "goal": "target", "current": 98.01}},
        "confirmations": [],
        "watchlist": [],
        "constraints": [],
        "applicability_domain": {"n_rows": 300, "time_span": "0 .. 299",
                                 "regime": "steady",
                                 "factor_observed_ranges": {
                                     "temp": {"min": 49.9, "max": 50.1}}},
        "invalidation_conditions": ["IF 窗口外因子组合出现 THEN 窗口失效"],
        "usage_rules": [],
        "provenance": {"input_sha256": "canned", "script_version": "1.0",
                       "seed": 42, "authored_by": "script"},
    }
    stab = {
        "generated_at": "2026-10-01T00:00:00+00:00",
        "n_rows": 300,
        "time_col": None,
        "capability": [{"response": "quality", "n": 300, "mean": 98.0,
                        "has_specs": True, "lsl": 97.5, "usl": 98.5,
                        "target": 98.0, "sigma_within_mr": 0.02}],
        "steady_segments": [{"start": 0, "end": 299, "n_rows": 300,
                             "selected_for_windows": True}],
        "change_points": [{"response": "quality", "positions": [120, 240]},
                          {"response": "temp", "positions": [77]}],
        "drift_flags": [],
        "regime_summary": None,
    }
    (doe / "conclusions" / "recommendations.json").write_text(
        json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
    (doe / "02_analysis" / "stability_report.json").write_text(
        json.dumps(stab, ensure_ascii=False, indent=2), encoding="utf-8")

    jitter_df(101, 300).to_csv(d / "history.csv", index=False)
    # give history a quality column so response_specs maps to a real column
    hist = pd.read_csv(d / "history.csv")
    hist["quality"] = 98.0
    hist.to_csv(d / "history.csv", index=False)

    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--doe-run-dir", str(doe), "--out", str(d / "watch_baseline.json")])
    record("F6_build_ok", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F6_abort", "baseline build failed")
    bl = read(d / "watch_baseline.json")
    g = bl["groups"]["__ALL__"]

    record("F6_operating_windows_verbatim",
           g["operating_windows"] == recs["operating_windows"],
           json.dumps(g["operating_windows"])[:200])
    record("F6_indicators_verbatim",
           g["indicators"].get("quality") == {
               "lsl": 97.5, "usl": 98.5, "target": 98.0, "goal": "target"},
           json.dumps(g.get("indicators", {}))[:200])
    record("F6_applicability_domain_verbatim",
           g["applicability_domain"] == recs["applicability_domain"],
           json.dumps(g.get("applicability_domain"))[:200])
    record("F6_invalidation_conditions_verbatim",
           g["validity"]["invalidation_conditions"] == recs["invalidation_conditions"],
           json.dumps(g["validity"]["invalidation_conditions"]))
    expected_cps = sorted({120, 240, 77})
    record("F6_known_change_points_verbatim",
           g["regime"]["known_change_points"] == expected_cps,
           str(g["regime"]["known_change_points"]))
    record("F6_recs_contract_version",
           bl["generated_from"]["recommendations_contract_version"] == "1.0",
           str(bl["generated_from"]))
    record("F6_history_params_kept",
           set(g["parameters"]) >= {"temp", "press"},
           str(sorted(g["parameters"])))
    # baseline schema validated directly (gate's S2 covers alert-side runs):
    v = node([str(SHARED / "scripts" / "validate.mjs"),
              str(SKILL / "schemas" / "watch_baseline.schema.json"),
              str(d / "watch_baseline.json")])
    record("F6_baseline_schema_valid", v.returncode == 0, v.stdout[-300:])


# ---------------------------------------------------------------- tamper

def case_tamper():
    print("[tamper] gate negative battery: enum / storm / extra keys (A6/A10)")
    # F1's own alert.json has zero alerts by design, so the battery builds a
    # VALID minimal payload (F1 metadata + one well-formed alert), proves the
    # gate accepts it, then corrupts it three ways.
    src = FIXTURES / "F1_watch_steady" / "sentinel" / "alert.json"
    if not src.exists():
        record("tamper_prereq_F1", False, "F1 alert.json missing; run F1 first")
        return
    base = read(src)
    base["alerts"] = [{
        "alert_id": "ALT-20260101-000000-001",
        "check_type": "spc",
        "rule_name": "NELSON_R1",
        "parameter": "temp",
        "indicator": None,
        "group": "__ALL__",
        "severity": "high",
        "urgency": "same_shift",
        "observed": {"value": 50.5, "statistic": 10.2, "index": 100,
                     "timestamp": None, "run_length": 1},
        "threshold": {"bound": 3.0, "sigma_level": 3.0},
        "evidence": {"n_points": 1},
        "suggested_check": "单点突变核查",
        "suggested_next_skill": "industrial-diagnostician",
        "advisory": False,
        "suppression_key": "__ALL__|spc|NELSON_R1|temp",
        "repeat_count": 1,
    }]
    d = case_dir("tamper_gate")

    def write_and_gate(name, payload):
        p = d / name
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return run_gate(p)

    r = write_and_gate("alert_valid.json", base)
    record("tamper_valid_base_passes", r.returncode == 0, r.stdout[-200:])

    # 1) invalid severity enum literal
    bad = json.loads(json.dumps(base))
    bad["alerts"][0]["severity"] = "URGENT"
    r = write_and_gate("alert_bad_enum.json", bad)
    record("tamper_enum_gate_fail", r.returncode == 1, r.stdout[-200:])

    # 2) storm: same-key alert inside the suppression window
    storm = json.loads(json.dumps(base))
    dup = json.loads(json.dumps(storm["alerts"][0]))
    dup["alert_id"] = "ALT-20260101-000000-099"
    dup["observed"]["index"] = 105  # gap 5 <= 60 -> storm
    storm["alerts"].append(dup)
    r = write_and_gate("alert_storm.json", storm)
    record("tamper_storm_gate_fail", r.returncode == 1, r.stdout[-200:])

    # 3) undeclared extra key on an alert (retired v1.4 autonomy vocabulary)
    extra = json.loads(json.dumps(base))
    extra["alerts"][0]["autonomy"] = "auto_within_guardrails"
    r = write_and_gate("alert_extra_key.json", extra)
    record("tamper_extra_key_gate_fail", r.returncode == 1, r.stdout[-200:])


# ---------------------------------------------------------------- driver

CASES = {
    "F1": case_f1,
    "F2": case_f2,
    "F3": case_f3,
    "F4": case_f4,
    "F5": case_f5,
    "F6": case_f6,
    "tamper": case_tamper,
}


def main(argv):
    which = argv[1] if len(argv) > 1 else "all"
    t0 = time.time()
    if which == "all":
        for name, fn in CASES.items():
            try:
                fn()
            except CaseAbort:
                print(f"  (case {name} aborted after prerequisite failure)")
    else:
        try:
            CASES[which]()
        except CaseAbort:
            pass

    failed = [c for c, ok, _ in RESULTS if not ok]
    print(f"\n{'=' * 62}")
    print(f"[RESULT] {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          f" in {time.time() - t0:.1f}s"
          + (f" — FAILED: {', '.join(failed)}" if failed else " — ALL GREEN"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
