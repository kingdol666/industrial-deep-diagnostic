#!/usr/bin/env python
"""plant_sim.py — deterministic 2-factor black-box plant for field test T4.

The plant accepts one trial design and returns measured impurity replicates in
the EXACT trial_result.json contract that industrial-optimizer-loop's `ingest`
expects (schemas/trial_result.schema.json).

Interface
---------
  python plant_sim.py --design <trial_design.json | design.csv> --out trial_result.json
  (design.csv input additionally accepts --campaign-id / --round-id)

Input
  trial_design.json : the optimizer `design` artifact (campaign_id, round_id,
                      trials[].trial_id, trials[].setpoints{Temperature,
                      Concentration}, trials[].replicates)
  design.csv        : one row per trial, columns Temperature,Concentration

Output  trial_result.json (trial_result/1.0):
  {result_version, campaign_id, round_id, trials: [{trial_id, status:
   "completed", measurements: {impurity_pct: [replicate values]}}]}

Determinism: the true response is a fixed quadratic bowl; measurement noise is
Gaussian sigma=0.03 with a per-(campaign, round, trial, replicate) RNG seed
derived from sha256 — identical inputs always give identical outputs.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

T_STAR = 78.5          # degC
C_STAR = 0.42          # mass fraction
IMPURITY_MIN = 0.35
NOISE_SIGMA = 0.03
SEED = 42
STATUS_COMPLETED = "completed"


def true_response(temperature, concentration):
    return (IMPURITY_MIN
            + 0.0018 * (temperature - T_STAR) ** 2
            + 1.6 * (concentration - C_STAR) ** 2)


def measure(campaign_id, round_id, trial_id, rep_index, t, c):
    key = f"{SEED}|{campaign_id}|{round_id}|{trial_id}|{rep_index}|{t:.6f}|{c:.6f}"
    digest = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(digest)
    return round(float(true_response(t, c) + rng.normal(0.0, NOISE_SIGMA)), 6)


def load_design(path, campaign_id, round_id):
    p = Path(path)
    if p.suffix.lower() == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        campaign_id = d.get("campaign_id") or campaign_id
        round_id = d.get("round_id") or round_id
        trials = []
        for tr in d.get("trials") or []:
            sp = tr.get("setpoints") or {}
            trials.append({
                "trial_id": tr.get("trial_id"),
                "T": float(sp["Temperature"]),
                "C": float(sp["Concentration"]),
                "reps": int(tr.get("replicates") or 1),
            })
        return campaign_id, round_id, trials
    # CSV fallback: columns Temperature,Concentration
    trials = []
    with p.open(newline="", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=1):
            trials.append({
                "trial_id": row.get("trial_id") or f"{round_id or 'R000'}-T{i:02d}",
                "T": float(row["Temperature"]),
                "C": float(row["Concentration"]),
                "reps": int(row["replicates"]) if (row.get("replicates") or "").isdigit() else 1,
            })
    return campaign_id, round_id, trials


def main(argv=None):
    ap = argparse.ArgumentParser(description="T4 black-box plant (impurity bowl)")
    ap.add_argument("--design", required=True,
                    help="trial_design.json (preferred) or design.csv")
    ap.add_argument("--out", required=True, help="trial_result.json output path")
    ap.add_argument("--campaign-id", default="OPT-UNKNOWN-000")
    ap.add_argument("--round-id", default="R000")
    args = ap.parse_args(argv)

    campaign_id, round_id, trials = load_design(args.design, args.campaign_id,
                                                args.round_id)
    if not trials:
        print("[plant] no trials in design — nothing to run", file=sys.stderr)
        return 2

    out_trials = []
    for tr in trials:
        reps = [measure(campaign_id, round_id, tr["trial_id"], r, tr["T"], tr["C"])
                for r in range(tr["reps"])]
        out_trials.append({
            "trial_id": tr["trial_id"],
            "status": STATUS_COMPLETED,
            "measurements": {"impurity_pct": reps},
            "measured_at": None,
            "operator_note": "plant_sim deterministic black-box run",
        })
    payload = {
        "result_version": "1.0",
        "campaign_id": campaign_id,
        "round_id": round_id,
        "trials": out_trials,
        "late_results": None,
        "environment": None,
        "ingest_meta": {"source": "inbox_file",
                        "ingested_at": None},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[plant] ran {len(out_trials)} trial(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
