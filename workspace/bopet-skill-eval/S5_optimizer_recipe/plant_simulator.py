# -*- coding: utf-8 -*-
"""虚拟 BOPET 产线 —— optimizer-loop 演示替身（评审用，非生产代码）。

读取 <run-dir>/02_rounds/<round>/trial_design.json，按二次响应面真值 + 确定性
噪声生成 trial_result.json（同目录）。真值与噪声见 ground_truth.md。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

OPT = Path(__file__).resolve().parent
SKILL_SCRIPTS = OPT / ".." / ".." / ".claude" / "skills" / \
    "industrial-optimizer-loop" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))


def truth(cx4: float, v: float, cx6: float) -> float:
    return (99.2 - 0.045 * (cx4 - 241) ** 2 - 0.30 * (v - 53.2) ** 2
            - 0.028 * (cx6 - 192) ** 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=str(OPT))
    ap.add_argument("--round", required=True, help="e.g. R001")
    a = ap.parse_args()
    run = Path(a.run_dir)
    design_p = run / "02_rounds" / a.round / "trial_design.json"
    design = json.loads(design_p.read_text(encoding="utf-8"))

    trials_out = []
    for trial in design.get("trials", []):
        tid = trial["trial_id"]
        vals = trial.get("setpoints") or trial.get("params") or trial.get("values") or {}
        cx4 = float(vals["TDO拉伸区温度CX4"])
        v = float(vals["纵拉拉伸速度"])
        cx6 = float(vals["TDO定型区温度CX6"])
        seed = int(hashlib.sha256(tid.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        n_rep = int(trial.get("replicates") or 3)
        reps = [round(truth(cx4, v, cx6) + float(rng.normal(0, 0.15)), 3)
                for _ in range(n_rep)]
        trials_out.append({
            "trial_id": tid,
            "status": "completed",
            "measurements": {"优品率": reps},
            "measured_at": "2026-10-14T00:00:00Z",
            "operator_note": "虚拟产线替身回投（演示）",
        })

    result = {
        "result_version": "1.0",
        "campaign_id": design.get("campaign_id"),
        "round_id": a.round,
        "trials": trials_out,
        "ingest_meta": {"source": "manual_csv", "ingested_at": None},
    }
    out = design_p.parent / "trial_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"[plant] {design_p} -> {out} ({len(trials_out)} trials)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
