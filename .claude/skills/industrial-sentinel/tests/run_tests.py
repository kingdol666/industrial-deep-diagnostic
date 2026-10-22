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
  F7  hours_axis unit regression across time representations (pandas 3)
  F8  baseline without operating_windows -> explicit C2-skipped notice
  F9  sentinel ontology prepare build/reuse (isolated ONTOLOGY_STORE_DIR) +
      explicit --ontology adoption + units into alert.ontology (plan P2.6)
  F10 ontology-declared windows -> baseline (capped warn, interpretation) +
      indicators negative (plan P2.2/P2.6)
  F11 folder multi-source via preprocessor single-primary -> watch +
      per-file disposition audit, <= 120s (plan P2.2/P2.6)
  F12 gate ontology block: declared top-level key passes / undeclared fails
  tamper  gate negative battery: bad enum / storm / extra keys -> gate exit 1 (A6)
  perf    measured inside F2/F11 (duration <= 120s)                    (A2)
AC definitions live in tests/AC.md.

All fixture/step writes use pandas/pathlib (no raw open() in this skill).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPTS = SKILL / "scripts"
REPO = SKILL.parents[2]
SHARED = REPO / ".claude" / "shared"
# Tests rewrite fixture directories (rmtree + regenerate). Run against a
# private copy so the committed tests/fixtures tree is never modified. The
# copy must stay INSIDE the repo: sentinelcore._io enforces repo-root
# containment on every data/output path.
_SOURCE_FIXTURES = (HERE / "fixtures").resolve()
FIXTURES = Path(tempfile.mkdtemp(prefix=".tmp-fixtures-", dir=HERE)).resolve()
if _SOURCE_FIXTURES.is_dir():
    shutil.copytree(_SOURCE_FIXTURES, FIXTURES, dirs_exist_ok=True)

SENTINEL = SCRIPTS / "sentinel.py"
SENTINEL_FAST = SCRIPTS / "sentinel_fast.py"
BUILD_BASELINE = SCRIPTS / "build_baseline.py"
PREPARE = SCRIPTS / "sentinel_ontology_prepare.py"
PREPROCESSOR = (REPO / ".claude" / "skills" / "industrial-data-preprocessor"
                / "scripts" / "data_preprocessor.py")
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


def py(args, timeout=300, env=None):
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, timeout=timeout, shell=False, env=env)


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


# ---------------------------------------------------------------- F7

F7_TIME_REPRS = ("iso_us", "iso_ns", "epoch_s", "epoch_ms", "epoch_us",
                 "epoch_ns", "datetime")


def f7_watch_frame(seed, n, time_repr):
    """Watch window with +0.0008/row drift on temp; identical parameter values
    across calls, only the time-column representation differs (1-min cadence
    from 2026-03-01T00:00:00Z)."""
    rng = np.random.default_rng(seed)
    i = np.arange(n)
    temp = 49.6 + 0.0008 * i + rng.normal(0, 0.1, n)
    press = 10.0 + rng.normal(0, 0.04, n)
    t0 = 1772323200  # 2026-03-01T00:00:00Z
    base_s = t0 + 60 * i
    base_dt = pd.Series(pd.to_datetime(base_s, unit="s"))
    if time_repr == "iso_us":
        ts = (base_dt.astype("datetime64[us]").dt.strftime("%Y-%m-%dT%H:%M:%S")
              + ".123456")
    elif time_repr == "iso_ns":
        ts = (base_dt.astype("datetime64[ns]").dt.strftime("%Y-%m-%dT%H:%M:%S")
              + ".123456789")
    elif time_repr == "epoch_s":
        ts = pd.Series(base_s)
    elif time_repr == "epoch_ms":
        ts = pd.Series(base_s * 10**3)
    elif time_repr == "epoch_us":
        ts = pd.Series(base_s * 10**6)
    elif time_repr == "epoch_ns":
        ts = pd.Series(base_s * 10**9)
    elif time_repr == "datetime":
        ts = base_dt
    else:
        raise ValueError(f"unknown time representation: {time_repr}")
    return pd.DataFrame({"timestamp": ts, "temp": temp, "press": press})


def f7_doe_artifacts(doe):
    """Canned doe-analyzer recommendations carrying one operating window."""
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
             "extrapolation": False, "confirmation_needed": False,
             "notes": "F7 canned window"},
        ],
        "current_baseline": {"point": {"temp": 49.6}, "distance_to_window": {},
                             "move_instruction": None},
        "response_specs": {},
        "confirmations": [],
        "watchlist": [],
        "constraints": [],
        "applicability_domain": None,
        "invalidation_conditions": [],
        "usage_rules": [],
        "provenance": {"input_sha256": "canned", "script_version": "1.0",
                       "seed": 42, "authored_by": "script"},
    }
    (doe / "conclusions" / "recommendations.json").write_text(
        json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
    (doe / "02_analysis" / "stability_report.json").write_text(
        json.dumps({"generated_at": "2026-10-01T00:00:00+00:00",
                    "n_rows": 300, "time_col": None, "capability": [],
                    "steady_segments": [], "change_points": [],
                    "drift_flags": [], "regime_summary": None},
                   ensure_ascii=False, indent=2), encoding="utf-8")


def case_f7():
    print("[F7] hours_axis unit regression: identical hours_to_edge for the "
          "same window as ISO-us strings / epoch s / epoch ns (pandas 3)")
    # unit-level: all representations produce the same hour axis
    sys.path.insert(0, str(SCRIPTS))
    from sentinelcore._io import hours_axis  # noqa: E402

    ref = None
    for repr_name in F7_TIME_REPRS:
        df = f7_watch_frame(7, 24, repr_name)
        h = hours_axis(df, "timestamp")
        if ref is None:
            ref = h
        rel = float(np.max(np.abs((h - ref) / np.maximum(np.abs(ref), 1e-12))))
        record(f"F7_hours_axis_{repr_name}_rel_le_1e-6", rel <= 1e-6,
               f"max_rel={rel:.3e}")

    # end-to-end: identical C2 projection numbers across representations
    d = case_dir("F7_hours_axis_units")
    f2_history(d / "history.csv")
    f7_doe_artifacts(d / "doe_run")
    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--doe-run-dir", str(d / "doe_run"),
            "--out", str(d / "watch_baseline.json")])
    record("F7_baseline_build", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F7_abort", "baseline build failed")

    projs = {}
    exit_codes = {}
    for repr_name in F7_TIME_REPRS:
        f7_watch_frame(7, 600, repr_name).to_csv(d / f"watch_{repr_name}.csv",
                                                 index=False)
        r = py([str(SENTINEL), "watch", "--data", str(d / f"watch_{repr_name}.csv"),
                "--baseline", str(d / "watch_baseline.json"),
                "--out-dir", str(d / "sentinel" / repr_name)])
        exit_codes[repr_name] = r.returncode
        require((d / "sentinel" / repr_name / "alert.json").exists(),
                "F7_abort", f"no alert.json for {repr_name}")
        alert = read(d / "sentinel" / repr_name / "alert.json")
        psum = alert.get("projection_summary") or []
        require(psum, "F7_abort", f"empty projection_summary for {repr_name}")
        projs[repr_name] = psum[0]
        if repr_name == "iso_us":
            record("F7_windows_present_no_c2_skip",
                   alert["checks_summary"].get("checks_skipped") == [],
                   str(alert["checks_summary"].get("checks_skipped")))

    record("F7_exit_codes_identical",
           len(set(exit_codes.values())) == 1, str(exit_codes))
    ref_proj = projs["iso_us"]
    for repr_name, p in projs.items():
        for key in ("hours_to_edge", "slope_per_hour", "current"):
            a, b = ref_proj.get(key), p.get(key)
            ok = (a is None and b is None) or (
                a is not None and b is not None
                and abs(a - b) <= 1e-6 * max(abs(a), abs(b), 1e-12))
            record(f"F7_{key}_{repr_name}_identical", ok, f"{a} vs {b}")
    g = run_gate(d / "sentinel" / "iso_us" / "alert.json",
                 d / "watch_baseline.json")
    record("F7_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F8

F8_C2_NOTICE = ("C2 drift projection disabled: no operating_windows "
                "in baseline (build with --doe-run-dir to enable)")


def case_f8():
    print("[F8] baseline without operating_windows -> explicit C2-skipped "
          "notice in alert.json / watch_report.md / stdout")
    d = case_dir("F8_c2_no_windows")
    jitter_df(101, 400).to_csv(d / "history.csv", index=False)
    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--out", str(d / "watch_baseline.json")])
    record("F8_baseline_build", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F8_abort", "baseline build failed")
    bl = read(d / "watch_baseline.json")
    require(not any(s.get("operating_windows") for s in bl["groups"].values()),
            "F8_abort", "baseline unexpectedly has operating_windows")

    jitter_df(202, 240).to_csv(d / "watch.csv", index=False)
    r = py([str(SENTINEL), "watch", "--data", str(d / "watch.csv"),
            "--baseline", str(d / "watch_baseline.json"),
            "--out-dir", str(d / "sentinel")])
    record("F8_watch_exit0", r.returncode == 0, f"rc={r.returncode} {r.stdout[-200:]}")
    alert = read(d / "sentinel" / "alert.json")
    skipped = alert["checks_summary"].get("checks_skipped")
    record("F8_checks_skipped_entry",
           skipped == [{"check": "window_projection", "reason": F8_C2_NOTICE}],
           str(skipped))
    report = (d / "sentinel" / "watch_report.md").read_text(encoding="utf-8")
    record("F8_report_chinese_notice", "C2 漂移投影未启用" in report, "")
    record("F8_report_contract_notice", F8_C2_NOTICE in report, "")
    record("F8_stdout_notice", F8_C2_NOTICE in r.stdout,
           r.stdout[-300:])
    g = run_gate(d / "sentinel" / "alert.json", d / "watch_baseline.json")
    record("F8_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F9

F9_CONTEXT = {
    "scene": "F9 sentinel ontology fixture",
    "parameter_cols": ["temp", "press"],
    "units": {"temp": "degC", "press": "kPa"},
    "spec_limits": {"temp": {"lsl": 49.5, "usl": 50.5}},
    "ontology": {"mode": "auto", "scene_key": "f9scene"},
}


def _f9_run(d):
    run = d / "run"
    (run / "00_input").mkdir(parents=True, exist_ok=True)
    jitter_df(101, 300).to_csv(run / "00_input" / "history.csv", index=False)
    (run / "00_input" / "report_context.json").write_text(
        json.dumps(F9_CONTEXT, ensure_ascii=False, indent=2), encoding="utf-8")
    env = dict(os.environ)
    env["ONTOLOGY_STORE_DIR"] = str(d / "ontology_store")
    return run, env


def case_f9():
    print("[F9] ontology prepare build/reuse (isolated store) + explicit "
          "--ontology adoption + units into alert.ontology (plan P2.6)")
    d = case_dir("F9_prepare_build_reuse")
    run, env = _f9_run(d)

    def prepare_run(*extra):
        return py([str(PREPARE), "--run-dir", str(run), "--scene", "f9scene",
                   "--json", *extra], env=env)

    r = prepare_run()
    record("F9_prepare_exit0", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])
    require(r.returncode == 0, "F9_abort", "prepare failed")
    res = json.loads(r.stdout)
    record("F9_action_built", res["action"] == "built", res["action"])
    record("F9_store_published", res["store"].get("published") is True
           and res["store"].get("entry_version") is not None,
           json.dumps(res["store"]))
    record("F9_cp2_floor_ok", res["cp2_floor_ok"] is True, str(res.get("ontology_bytes")))
    record("F9_rag_used_false", res["rag_used"] is False
           and res["rag_used_by_prepare"] is False, str(res["rag_used"]))
    for key in ("ontology_path", "brief_json", "brief_md", "coverage_path"):
        record(f"F9_artifact_{key}", Path(res[key]).is_file(), str(res[key]))

    ont = read(res["ontology_path"])
    record("F9_units_declared",
           ont["metadata"]["units"] == {"temp": "degC", "press": "kPa"},
           str(ont["metadata"]["units"]))
    temp_sig = next(s for s in ont["signals"]["process_parameters"]
                    if s["column"] == "temp")
    record("F9_spec_normal_range", temp_sig.get("normal_range") == [49.5, 50.5],
           str(temp_sig.get("normal_range")))
    record("F9_relationships_empty", ont["relationships"] == [],
           str(ont["relationships"]))
    cov = read(res["coverage_path"])
    record("F9_coverage_ratio_1", cov["coverage"]["ratio"] == 1.0,
           json.dumps(cov["coverage"]))
    record("F9_coverage_profile_sentinel", cov["profile"] == "sentinel", cov["profile"])
    brief_md = Path(res["brief_md"]).read_text(encoding="utf-8")
    record("F9_brief_md_chinese_sections",
           "场景理解" in brief_md and "列角色与单位" in brief_md
           and "规格与参考区间" in brief_md and "列映射与覆盖" in brief_md, "")

    # same declarations again -> exact store hit -> verbatim reuse
    r2 = prepare_run()
    record("F9_reuse_exit0", r2.returncode == 0, r2.stdout[-300:] + r2.stderr[-300:])
    res2 = json.loads(r2.stdout)
    record("F9_action_reused", res2["action"] == "reused", res2["action"])
    record("F9_reuse_recorded", res2["store"].get("published") is True
           and bool(res2["store"].get("reuse")), json.dumps(res2["store"]))

    # watch consumes the run's ontology via 01_ontology auto-discovery
    # (before the adoption block below, which overwrites the run ontology)
    jitter_df(202, 240).to_csv(run / "00_input" / "aaa_watch.csv", index=False)
    r5 = py([str(SENTINEL), "watch", "--run-dir", str(run)])
    record("F9_watch_exit", r5.returncode in (0, 1), f"rc={r5.returncode} {r5.stdout[-200:]}")
    alert = read(run / "sentinel" / "alert.json")
    block = alert.get("ontology") or {}
    record("F9_alert_ontology_units",
           block.get("units") == {"temp": "degC", "press": "kPa"}, str(block.get("units")))
    record("F9_alert_ontology_rag_false", block.get("rag_used") is False, str(block))
    record("F9_alert_declared_window_count", block.get("declared_window_count") == 1,
           str(block.get("declared_window_count")))
    g = run_gate(run / "sentinel" / "alert.json")
    record("F9_gate_pass", g.returncode == 0, g.stdout[-300:])

    # explicit --ontology adoption: verbatim asset, build_mode=full, store publish
    adopted = d / "adopted_ontology.json"
    adopted.write_text(json.dumps({
        "scene": {"name": "adopted_scene", "process_type": "watch"},
        "signals": {"inspection_signals": [], "process_parameters": [
            {"name": "temp", "column": "temp", "role": "predictor", "unit": "degC",
             "normal_range": [10, 90],
             "observed_data_behavior": "NOT_APPLICABLE", "behavior_match": "UNVERIFIED"}],
            "control_variables": [], "events": [], "metadata_columns": []},
        "relationships": [],
        "metadata": {"units": {"temp": "degC"}, "note": "z" * 1200},
        "provenance": {"engine": "industrial-ontology-builder", "profile": "sentinel",
                       "build_mode": "full", "rag_used": False, "web_used": False},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    r3 = prepare_run("--mode", "full", "--ontology", str(adopted))
    record("F9_adopt_exit0", r3.returncode == 0, r3.stdout[-300:] + r3.stderr[-300:])
    res3 = json.loads(r3.stdout)
    record("F9_adopt_action_built", res3["action"] == "built", res3["action"])
    record("F9_adopt_build_mode_full", res3["build_mode"] == "full", str(res3["build_mode"]))
    record("F9_adopt_source_note",
           "adopted explicit ontology asset" in (res3["source_note"] or ""),
           str(res3["source_note"]))
    record("F9_adopt_verbatim_scene",
           read(res3["ontology_path"])["scene"]["name"] == "adopted_scene", "")
    record("F9_adopt_store_published", res3["store"].get("published") is True,
           json.dumps(res3["store"]))

    # missing explicit asset -> honest refusal (SystemExit, clear code)
    r4 = prepare_run("--ontology", str(d / "missing_ontology.json"))
    record("F9_adopt_missing_refused",
           r4.returncode != 0 and "EXPLICIT_ONTOLOGY_INVALID" in (r4.stderr + r4.stdout),
           f"rc={r4.returncode} {(r4.stderr + r4.stdout)[-160:]}")


def case_f9b():
    print("[F9b] bare CSV zero-declaration -> minimal prior (plan C1, mirrors S22b)")
    d = case_dir("F9b_bare_zero_declaration")
    run = d / "run"
    (run / "00_input").mkdir(parents=True, exist_ok=True)
    jitter_df(101, 300).to_csv(run / "00_input" / "history.csv", index=False)
    env = dict(os.environ)
    env["ONTOLOGY_STORE_DIR"] = str(d / "ontology_store")

    r = py([str(PREPARE), "--run-dir", str(run), "--scene", "f9b_bare", "--json"], env=env)
    record("F9b_prepare_exit0", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])
    require(r.returncode == 0, "F9b_abort", "prepare failed on bare CSV")
    res = json.loads(r.stdout)
    record("F9b_action_built", res["action"] == "built", res["action"])
    record("F9b_cp2_floor_ok", res["cp2_floor_ok"] is True, str(res.get("ontology_bytes")))
    record("F9b_rag_used_false", res["rag_used"] is False
           and res["rag_used_by_prepare"] is False, str(res["rag_used"]))
    for key in ("ontology_path", "brief_json", "brief_md", "coverage_path"):
        record(f"F9b_artifact_{key}", Path(res[key]).is_file(), str(res[key]))
    record("F9b_store_published", res["store"].get("published") is True,
           json.dumps(res["store"]))

    ont = read(res["ontology_path"])
    signals = []
    for group in ("inspection_signals", "process_parameters", "control_variables"):
        signals.extend(ont["signals"].get(group) or [])
    record("F9b_no_user_spec",
           all(not s.get("normal_range") for s in signals)
           and all(s.get("knowledge_source") != "user_provided" for s in signals),
           json.dumps([{"c": s.get("column"), "ks": s.get("knowledge_source")} for s in signals]))
    record("F9b_relationships_empty", ont["relationships"] == [],
           str(ont["relationships"]))

    cov = read(res["coverage_path"])
    mapping = cov.get("column_mapping") or {}
    statuses = [item.get("status") for bucket in ("matched", "inferred", "unmatched")
                for item in (mapping.get(bucket) or [])]
    record("F9b_zero_matched", "matched" not in statuses and len(statuses) > 0,
           json.dumps(mapping)[:240])
    brief_md = Path(res["brief_md"]).read_text(encoding="utf-8")
    record("F9b_undeclared_marked", "单位未声明" in brief_md, brief_md[-240:])


# ---------------------------------------------------------------- F10

def case_f10():
    print("[F10] ontology windows -> baseline (ontology_declared, capped warn) "
          "+ out-of-window positive + indicators negative (plan P2.2/P2.6)")
    d = case_dir("F10_ontology_windows")
    run = d / "run"
    (run / "00_input").mkdir(parents=True)
    jitter_df(101, 400).to_csv(run / "00_input" / "history.csv", index=False)
    context = dict(F9_CONTEXT)
    context["ontology"] = {"mode": "full", "scene_key": "f10scene"}
    (run / "00_input" / "report_context.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    env = dict(os.environ)
    env["ONTOLOGY_STORE_DIR"] = str(d / "ontology_store")
    r = py([str(PREPARE), "--run-dir", str(run), "--scene", "f10scene", "--json"], env=env)
    record("F10_prepare_built", r.returncode == 0
           and json.loads(r.stdout or "{}").get("action") == "built",
           r.stdout[-200:] + r.stderr[-200:])
    require(r.returncode == 0, "F10_abort", "prepare failed")
    ont_path = run / "01_ontology" / "ontology.json"

    r = py([str(BUILD_BASELINE), "--history-csv", str(run / "00_input" / "history.csv"),
            "--ontology", str(ont_path), "--out", str(d / "watch_baseline.json")])
    record("F10_baseline_build", r.returncode == 0, r.stdout + r.stderr)
    require(r.returncode == 0, "F10_abort", "baseline build failed")
    bl = read(d / "watch_baseline.json")
    wins = bl["groups"]["__ALL__"]["operating_windows"]
    record("F10_window_source_declared",
           bool(wins) and all(w.get("window_source") == "ontology_declared" for w in wins),
           json.dumps(wins)[:200])
    record("F10_confirmation_needed_true",
           bool(wins) and all(w.get("confirmation_needed") is True for w in wins),
           json.dumps(wins)[:200])
    record("F10_window_range_from_ontology",
           any(w.get("factor") == "temp" and w.get("range") == [49.5, 50.5] for w in wins),
           json.dumps(wins)[:200])
    record("F10_window_source_path",
           all(w.get("source_path") == str(ont_path) for w in wins),
           str([w.get("source_path") for w in wins]))
    record("F10_indicators_empty",
           all(not s.get("indicators") for s in bl["groups"].values()),
           json.dumps({k: v.get("indicators") for k, v in bl["groups"].items()}))

    # positive: window data outside the declared band -> warn-capped + labelled
    watch = jitter_df(202, 240)
    watch["temp"] = watch["temp"] + 2.0        # ~52, outside [49.5, 50.5]
    t0 = pd.Timestamp("2026-03-01 00:00:00")
    watch.insert(0, "timestamp",
                 [t0 + pd.Timedelta(minutes=int(m)) for m in range(len(watch))])
    watch.to_csv(d / "watch_out.csv", index=False)
    r = py([str(SENTINEL), "watch", "--data", str(d / "watch_out.csv"),
            "--baseline", str(d / "watch_baseline.json"),
            "--ontology", str(ont_path), "--out-dir", str(d / "sentinel")], timeout=300)
    record("F10_watch_exit_findings", r.returncode == 1,
           f"rc={r.returncode} {r.stdout[-200:]}")
    require((d / "sentinel" / "alert.json").exists(), "F10_abort", "no alert.json")
    alert = read(d / "sentinel" / "alert.json")
    proj = [a for a in alert["alerts"] if a["check_type"] == "window_projection"]
    require(proj, "F10_abort", "no window_projection alerts")
    record("F10_projection_warn_only",
           all(a["severity"] == "warn" for a in proj),
           str([(a["rule_name"], a["severity"]) for a in proj]))
    record("F10_interpretation_declared",
           all("ontology_declared" in (a.get("interpretation") or "") for a in proj),
           str([a.get("interpretation") for a in proj]))
    record("F10_suggestion_mentions_declared",
           all("本体声明" in (a.get("suggested_check") or "") for a in proj),
           str([a.get("suggested_check") for a in proj])[:200])
    block = alert.get("ontology") or {}
    record("F10_alert_ontology_block",
           block.get("declared_window_count") == 1
           and block.get("units", {}).get("temp") == "degC", str(block))
    report = (d / "sentinel" / "watch_report.md").read_text(encoding="utf-8")
    record("F10_report_window_source_line", "ontology_declared" in report, "")
    g = run_gate(d / "sentinel" / "alert.json", d / "watch_baseline.json")
    record("F10_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F11

def case_f11():
    print("[F11] folder multi-source -> preprocessor single-primary -> watch "
          "(per-file disposition audit, <=120s) (plan P2.2/P2.6)")
    d = case_dir("F11_folder_multisource")
    raw = d / "raw"
    raw.mkdir(parents=True)
    main_df = jitter_df(101, 240)
    t0 = pd.Timestamp("2026-03-01 00:00:00")
    main_df.insert(0, "timestamp",
                   [t0 + pd.Timedelta(minutes=int(m)) for m in range(len(main_df))])
    main_df.to_csv(raw / "line1_main.csv", index=False)
    pd.DataFrame({
        "date": ["2026-03-01", "2026-03-02", "2026-03-03"],
        "shift": ["早班", "中班", "夜班"],
        "note": ["更换轴承", "调整参数", "例行保养"],
    }).to_csv(raw / "maintenance_log.csv", index=False)

    run = d / "run"
    r = py([str(PREPROCESSOR), "--data-path", str(raw), "--output", str(run / "00_input"),
            "--name", "f11", "--stability-single-primary", "--recursive"], timeout=180)
    record("F11_preprocess_exit0", r.returncode == 0,
           r.stdout[-400:] + r.stderr[-300:])
    require(r.returncode == 0, "F11_abort", "preprocess failed")
    report = read(run / "00_input" / "preprocessing_report.json")
    record("F11_report_status_ok", report.get("status") == "ok", str(report.get("status")))
    disp = {entry.get("relative_path"): entry
            for entry in report.get("source_dispositions", [])}
    record("F11_disposition_per_file",
           {"line1_main.csv", "maintenance_log.csv"} <= set(disp)
           and all(entry.get("disposition") for entry in disp.values()),
           json.dumps(report.get("source_dispositions", []))[:300])
    record("F11_primary_selected",
           disp.get("line1_main.csv", {}).get("disposition") == "selected"
           and (report.get("selected_table") or {}).get("file") == "line1_main.csv",
           json.dumps(disp.get("line1_main.csv", {}))[:200])
    record("F11_event_excluded",
           disp.get("maintenance_log.csv", {}).get("disposition") == "excluded_from_scoring",
           json.dumps(disp.get("maintenance_log.csv", {}))[:200])

    t0w = time.time()
    r = py([str(SENTINEL), "watch", "--run-dir", str(run)], timeout=180)
    wall_s = time.time() - t0w
    record("F11_watch_exit", r.returncode in (0, 1),
           f"rc={r.returncode} {r.stdout[-200:]}")
    require((run / "sentinel" / "alert.json").exists(), "F11_abort", "no alert.json")
    alert = read(run / "sentinel" / "alert.json")
    record("F11_watch_report_written",
           (run / "sentinel" / "watch_report.md").is_file(), "")
    record("F11_status_valid", alert["status"] in ("ok", "warn", "alert"),
           alert["status"])
    dur = alert["provenance"]["duration_ms"]
    record("F11_duration_le_120s", dur <= 120000 and wall_s <= 125,
           f"duration_ms={dur} wall={wall_s:.1f}s")
    g = run_gate(run / "sentinel" / "alert.json")
    record("F11_gate_pass", g.returncode == 0, g.stdout[-300:])


# ---------------------------------------------------------------- F12

def case_f12():
    print("[F12] gate ontology block: declared top-level key passes, undeclared "
          "top-level key fails (gate S3 hard gate)")
    src = FIXTURES / "F1_watch_steady" / "sentinel" / "alert.json"
    if not src.exists():
        record("F12_prereq_F1", False, "F1 alert.json missing; run F1 first")
        return
    base = read(src)
    base["ontology"] = {
        "source_path": "fixtures/F9/run/01_ontology/ontology.json",
        "scene": "f12scene",
        "rag_used": False,
        "units": {"temp": "degC", "press": "kPa"},
        "roles": {"temp": "parameter", "press": "parameter"},
        "declared_window_count": 1,
    }
    d = case_dir("F12_gate_ontology_keys")

    def write_and_gate(name, payload):
        p = d / name
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return run_gate(p)

    r = write_and_gate("alert_ontology_ok.json", base)
    record("F12_ontology_block_passes", r.returncode == 0, r.stdout[-300:])

    bad = json.loads(json.dumps(base))
    bad["ontology_policy"] = "auto"    # undeclared top-level key -> S3 hard fail
    r = write_and_gate("alert_undeclared_top_key.json", bad)
    record("F12_undeclared_top_key_fails", r.returncode == 1, r.stdout[-300:])


# ---------------------------------------------------------------- F13

def case_f13_pipeline_events():
    print("[F13] specialist event log: prepare_done + analysis_done; "
          "crash exit-code contract in source")
    d = case_dir("F13_pipeline_events")
    run = d / "run"
    (run / "00_input").mkdir(parents=True)
    jitter_df(303, 300).to_csv(run / "00_input" / "data.csv", index=False)
    env = dict(os.environ)
    env["ONTOLOGY_STORE_DIR"] = str(d / "store")
    rp = py([str(PREPARE), "--run-dir", str(run), "--json"], env=env)
    record("F13_prepare_exit0", rp.returncode == 0, (rp.stdout + rp.stderr)[-300:])
    require(rp.returncode == 0, "F13_abort", "prepare failed")
    r = py([str(SENTINEL), "watch", "--run-dir", str(run)], env=env)
    record("F13_watch_runs", r.returncode in (0, 1),
           f"rc={r.returncode} {r.stdout[-200:]}")
    require(r.returncode in (0, 1), "F13_abort", "watch did not complete")

    events_path = run / ".pipeline_events.jsonl"
    record("F13_events_file", events_path.is_file(), str(events_path))
    require(events_path.is_file(), "F13_abort", "no .pipeline_events.jsonl")
    events = [json.loads(line) for line in
              events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    names = [e.get("event") for e in events]
    record("F13_prepare_done", "prepare_done" in names, str(names))
    record("F13_analysis_done", "analysis_done" in names, str(names))
    analysis = next((e for e in events if e.get("event") == "analysis_done"), {})
    detail = analysis.get("detail") or {}
    record("F13_analysis_detail", "alerts" in detail and "mode" in detail,
           str(detail))

    # D4 static contract: uncaught exceptions surface as CRASH + exit 4
    src = SENTINEL.read_text(encoding="utf-8")
    record("F13_crash_contract", "CRASH:" in src and "return 4" in src, "")


# ---------------------------------------------------------------- driver

def case_t7_events():
    print("[T7] event aggregation + AR(1) sigma inflation (fieldtest R2)")
    # ---- unit: aggregate_events grouping semantics
    sys.path.insert(0, str(SENTINEL.parent))
    from sentinelcore.events import aggregate_events  # noqa: E402

    def mk(idx, param="p1", sev="warn", stat=-3.5):
        return {"check_type": "spc", "rule_name": "NELSON_R1", "parameter": param,
                "group": "1", "severity": sev, "suppression_key": f"g1|spc|{param}",
                "observed": {"index": idx, "statistic": stat}}

    evs = aggregate_events([mk(10), mk(60), mk(400), mk(460), mk(2000, "p2")],
                           generated_at="2026-10-05T00:00:00Z")
    record("T7_unit_samekey_gap_folds", len(evs) == 3, f"events={len(evs)}")
    record("T7_unit_count", evs[0]["alert_count"] == 2 and evs[1]["alert_count"] == 2
           and evs[2]["alert_count"] == 1,
           str([(e["alert_count"], e["parameter"]) for e in evs]))
    record("T7_unit_span", evs[0]["span_rows"] == 50 and evs[1]["span_rows"] == 60,
           str([(e["first_index"], e["last_index"]) for e in evs[:2]]))
    record("T7_unit_id", all(str(e["event_id"]).startswith("EVT-") for e in evs),
           str([e["event_id"] for e in evs]))
    seq = aggregate_events([mk(5), mk(10)])
    record("T7_unit_deterministic", [e["event_id"] for e in seq] ==
           [e["event_id"] for e in aggregate_events([mk(5), mk(10)])], "stable ids")

    # ---- end-to-end: AR(1) baseline stores rho; watch folds into events
    d = case_dir("T7_events_ar1")
    rng = np.random.default_rng(20261005)
    phi, eps = 0.85, 0.5

    def ar1(n, rng, shift=0.0):
        x = np.empty(n)
        x[0] = 50.0 + shift
        for t in range(1, n):
            x[t] = 50.0 + shift + phi * (x[t - 1] - 50.0 - shift) \
                + rng.normal(0, eps)
        return x

    # baseline = STATIONARY AR(1) only (no excursion — rho must reflect the
    # process, not a trend); watch continues the same process with a shift
    hist = ar1(2200, rng)
    pd.DataFrame({"ts": pd.date_range("2026-01-01", periods=2200, freq="min"),
                  "temp": hist}).to_csv(d / "history.csv", index=False)
    r = py([str(BUILD_BASELINE), "--history-csv", str(d / "history.csv"),
            "--time-col", "ts", "--parameters", "temp",
            "--out", str(d / "watch_baseline.json")])
    record("T7_baseline_build", r.returncode == 0, r.stdout + r.stderr[-200:])
    require(r.returncode == 0, "T7_abort", "baseline build failed")
    base = read(d / "watch_baseline.json")
    gkey = sorted(base["groups"])[0]
    p = base["groups"][gkey]["parameters"]["temp"]
    record("T7_ar1_rho_stored", p.get("ar1_rho") is not None
           and 0.70 < p["ar1_rho"] < 0.95, f"rho={p.get('ar1_rho')}")
    record("T7_ar1_sigma_inflated", p.get("sigma_within_mr_ar1", 0) >
           1.5 * (p.get("sigma_within_mr") or 1e-9),
           f"ar1={p.get('sigma_within_mr_ar1')} mr={p.get('sigma_within_mr')}")

    watch = ar1(200, rng, shift=4.0)
    pd.DataFrame({"ts": pd.date_range("2026-01-03", periods=200, freq="min"),
                  "temp": watch}).to_csv(d / "watch.csv", index=False)
    r = py([str(SENTINEL), "watch", "--data", str(d / "watch.csv"),
            "--baseline", str(d / "watch_baseline.json"), "--time-col", "ts",
            "--out-dir", str(d / "sentinel")])
    record("T7_watch_exit", r.returncode == 1, f"rc={r.returncode} {r.stdout[-200:]}")
    require((d / "sentinel" / "alert.json").exists(), "T7_abort", "no alert.json")
    alert = read(d / "sentinel" / "alert.json")
    record("T7_events_in_payload", isinstance(alert.get("events"), list)
           and "event_count" in alert.get("checks_summary", {}), "events layer")
    record("T7_events_fold", len(alert.get("events", [])) < len(alert["alerts"]),
           f"events={len(alert.get('events', []))} alerts={len(alert['alerts'])}")
    record("T7_ar1_fewer_alerts", len(alert["alerts"]) < 60,
           f"n_alerts={len(alert['alerts'])} (inflated sigma must curb storm)")
    g = run_gate(d / "sentinel" / "alert.json", d / "watch_baseline.json")
    record("T7_gate_pass", g.returncode == 0, g.stdout[-300:])


CASES = {
    "F1": case_f1,
    "F2": case_f2,
    "F3": case_f3,
    "F4": case_f4,
    "F5": case_f5,
    "F6": case_f6,
    "F7": case_f7,
    "F8": case_f8,
    "F9": case_f9,
    "F9b": case_f9b,
    "F10": case_f10,
    "F11": case_f11,
    "F12": case_f12,
    "F13": case_f13_pipeline_events,
    "T7": case_t7_events,
    "tamper": case_tamper,
}


def main(argv):
    which = argv[1] if len(argv) > 1 else "all"
    t0 = time.time()
    try:
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
    finally:
        shutil.rmtree(FIXTURES, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
