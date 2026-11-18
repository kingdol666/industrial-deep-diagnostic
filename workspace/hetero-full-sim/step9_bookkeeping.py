#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step-9 bookkeeping: input_manifest.time_column + fast-mode pre-audit skip evidence."""
import json
from pathlib import Path

RUN = sorted(Path("workspace/hetero-full-sim/runs").glob("*_heat_treat_sim"))[-1]

# 1) input_manifest: the canonical time column (true for this dataset)
im_path = RUN / "00_input" / "input_manifest.json"
im = json.loads(im_path.read_text(encoding="utf-8"))
im["time_column"] = "时间"
im_path.write_text(json.dumps(im, ensure_ascii=False, indent=2), encoding="utf-8")

# 2) run_manifest: record the fast-mode pre-report-audit skip in execution_policy.audit
rm_path = RUN / "run_manifest.json"
rm = json.loads(rm_path.read_text(encoding="utf-8"))
audit = rm.setdefault("execution_policy", {}).setdefault("audit", {})
skipped = audit.setdefault("skipped_stages", [])
if not any(s.get("stage") == "pre_report_audit" for s in skipped):
    skipped.append({"stage": "pre_report_audit", "reason": "fast_mode", "event": "artifact_check_complete"})
rm_path.write_text(json.dumps(rm, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps({"run": str(RUN), "time_column": im["time_column"],
                  "skipped_stages": skipped}, ensure_ascii=False))
