#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 0/1 finalize for the heat_treat_sim full-pipeline run.

Copies the pre-produced 00_input/07_hetero into the canonical run dir, then
writes run_config (data_path -> joined table + hetero block), input_manifest
and user_context with real numbers read from the artifacts.
"""
import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "workspace" / "hetero-full-sim"
SRC = BASE / "run"
RUN = sorted((BASE / "runs").glob("*_heat_treat_sim"))[-1]

# ---- 1. carry the E-1 / E-1H artifacts into the canonical run dir -----------
dst_input = RUN / "00_input"
dst_input.mkdir(parents=True, exist_ok=True)
for f in (SRC / "00_input").iterdir():
    if f.is_dir():
        shutil.copytree(f, dst_input / f.name, dirs_exist_ok=True)
    else:
        shutil.copy2(f, dst_input / f.name)
if (RUN / "07_hetero").exists():
    shutil.rmtree(RUN / "07_hetero")
shutil.copytree(SRC / "07_hetero", RUN / "07_hetero")

# ---- 2. read the anchored truth from the artifacts --------------------------
mani = json.loads((RUN / "07_hetero" / "hetero_manifest.json").read_text(encoding="utf-8"))
joined = RUN / "07_hetero" / "preprocessed_data_hetero.csv"
joined_lines = joined.read_text(encoding="utf-8-sig").count("\n")
n_rows = joined_lines - 1
n_cols = len(joined.read_text(encoding="utf-8-sig").split("\n", 1)[0].split(","))
anchor = RUN / "00_input" / "preprocessed_data.csv"
anchor_sha = "sha256:" + hashlib.sha256(anchor.read_bytes()).hexdigest()
features = (RUN / "07_hetero" / "preprocessed_data_hetero.csv").read_text(encoding="utf-8-sig").split("\n", 1)[0].split(",")
n_hx = len([c for c in features if c.startswith("HX-")])

# ---- 3. run_config: DATA_PATH switch + hetero provenance block --------------
rc_path = RUN / "00_input" / "run_config.json"
rc = json.loads(rc_path.read_text(encoding="utf-8"))
rc["data_path"] = "07_hetero/preprocessed_data_hetero.csv"
rc["raw_data_path"] = "workspace/hetero-full-sim/raw"
rc["run_mode"] = "fast"
rc["hetero"] = {
    "enabled": "auto",
    "anchor_path": "00_input/preprocessed_data.csv",
    "manifest": "07_hetero/hetero_manifest.json",
    "anchor_sha256": anchor_sha,
}
rc_path.write_text(json.dumps(rc, ensure_ascii=False, indent=2), encoding="utf-8")

# ---- 4. input_manifest + user_context (Step 1 outputs) -----------------------
im = {
    "run_id": RUN.name,
    "raw_data_path": "workspace/hetero-full-sim/raw",
    "files": [{
        "path": "07_hetero/preprocessed_data_hetero.csv",
        "role": "primary",
        "rows": n_rows,
        "cols": n_cols,
        "hx_cols": n_hx,
        "note": "E-1 anchor + E-1H HX tail columns (status ok)",
    }],
    "hetero": {
        "status": mani["status"],
        "sources": len(mani.get("sources", [])),
        "joined_table": "07_hetero/preprocessed_data_hetero.csv",
        "anchor_sha256": anchor_sha,
    },
    "context_files": ["raw/README.md"],
}
(RUN / "00_input" / "input_manifest.json").write_text(
    json.dumps(im, ensure_ascii=False, indent=2), encoding="utf-8")

uc = {
    "language": "zh",
    "scene_name": "heat_treat_sim",
    "data_description": "连续热处理线 10 天数据：DCS（10min 锚定）+ 带材横向温度剖面（30min）+ 炉膛温度场（2h）+ 表面检查图像（1h）+ 操作备注 + 实验室硬度（2h）",
    "analysis_goal": "定位产线质量异常根因并给出证据链（自动模式，模拟场景）",
}
(RUN / "00_input" / "user_context.json").write_text(
    json.dumps(uc, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps({"run_dir": str(RUN), "rows": n_rows, "cols": n_cols, "hx": n_hx,
                  "sources": len(mani.get("sources", []))}, ensure_ascii=False))
