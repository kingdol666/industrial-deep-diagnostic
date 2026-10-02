#!/usr/bin/env python
"""s6b_run_target.py — S6 adaptation: same campaign, goal=target with
target_range [0.0, 0.15] (semantically "deviation pressed to ~0"), bypassing
the d_individual minimize+usl desirability bug documented in EVAL_REPORT.md.

Truth unchanged: dev_pos07(x) = 0.25 * (die_bolt_T3_pct - 2.0)^2 + N(0, 0.03).
"""
import json
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "Scripts" / "python.exe"
OPT = REPO / ".claude" / "skills" / "industrial-optimizer-loop" / "scripts" / "optimizer.py"
RUN_DIR = HERE / "S6b" / "run"
METRIC = "dev_pos07"
SIGMA = 0.03
X_STAR = 2.0


def truth(x):
    return 0.25 * (x - X_STAR) ** 2


def cli(*args):
    r = subprocess.run([str(PY), str(OPT), *args], capture_output=True,
                       text=True, timeout=600, shell=False)
    print(f"[opt {' '.join(args)}] rc={r.returncode}")
    if r.stdout.strip():
        print(r.stdout.strip()[-400:])
    if r.returncode != 0 and r.stderr.strip():
        print(r.stderr.strip()[-400:])
        raise SystemExit(f"optimizer {args} failed")
    return r


def read(rel):
    return json.loads((RUN_DIR / rel).read_text(encoding="utf-8"))


def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "00_input").mkdir(exist_ok=True)
    objective = {
        "contract_version": "1.0", "campaign_id": "OPT-20261001-007",
        "target_metric": METRIC, "goal": "target",
        "target_range": [0.0, 0.15],
        "factors": [{"name": "die_bolt_T3_pct", "type": "numeric",
                     "min": 0.0, "max": 10.0, "unit": "%"}],
        "budget": {"max_rounds": 14, "max_trials": 80},
        "noise": {"replicates_for_sigma": 3}, "seed": 42,
    }
    (RUN_DIR / "00_input" / "objective.json").write_text(
        json.dumps(objective, indent=2), encoding="utf-8")

    rng = np.random.default_rng(20261001)
    cli("init", "--run-dir", str(RUN_DIR))
    for i in range(1, objective["budget"]["max_rounds"] + 1):
        rid = f"R{i:03d}"
        cli("design", "--run-dir", str(RUN_DIR))
        design = read(f"02_rounds/{rid}/trial_design.json")
        trials_out = []
        for t in design["trials"]:
            sp = t["setpoints"]["die_bolt_T3_pct"]
            reps = t.get("replicates") or 1
            meas = {METRIC: [round(float(truth(sp) + rng.normal(0, SIGMA)), 4)
                             for _ in range(reps)]}
            trials_out.append({"trial_id": t["trial_id"], "status": "completed",
                               "measurements": meas})
        result = {"result_version": "1.0",
                  "campaign_id": objective["campaign_id"],
                  "round_id": rid, "trials": trials_out}
        (RUN_DIR / "02_rounds" / rid / "trial_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        cli("ingest", "--run-dir", str(RUN_DIR))
        st = read("01_state/optimizer_state.json")
        print(f"  -> phase={st['phase']} round={rid} incumbent="
              f"{json.dumps((st.get('incumbent') or {}).get('setpoints'))}")
        if st["phase"] in ("converged", "paused", "exhausted", "aborted"):
            break
    st = read("01_state/optimizer_state.json")
    print("terminal phase:", st["phase"])
    if st["phase"] == "converged":
        cli("converge", "--run-dir", str(RUN_DIR))
    (HERE / "S6b" / "terminal_phase.txt").write_text(
        st["phase"] + "\n" + json.dumps(st.get("incumbent"), ensure_ascii=False),
        encoding="utf-8")


if __name__ == "__main__":
    main()
