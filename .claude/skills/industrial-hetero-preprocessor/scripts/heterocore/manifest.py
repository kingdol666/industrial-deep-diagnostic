"""manifest.py — builders + atomic writers for 07_hetero artifacts.

All JSON is written UTF-8, ensure_ascii=False, indent=2, via tmp+rename so a
crash never leaves a half-written manifest behind (the always-marker contract
depends on the manifest being trustworthy).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from . import CONTRACT_VERSION


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return "sha256:" + h.hexdigest()
    except OSError:
        return None


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_csv_atomic(path: Path, df) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(fd)
    try:
        df.to_csv(tmp, index=False, encoding="utf-8-sig")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def base_manifest(run_dir: Path, status: str, anchor_path: Path | None,
                  anchor_time_col: str | None, anchor_rows: int,
                  raw_path: Path | None, raw_source: str | None,
                  h7_files: list[dict]) -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "generated_at": now_iso(),
        "zero_llm": True,
        "run_dir": str(run_dir),
        "raw_path": str(raw_path) if raw_path else None,
        "raw_path_source": raw_source,
        "anchor": {
            "path": str(anchor_path) if anchor_path else None,
            "sha256": sha256_file(anchor_path) if anchor_path else None,
            "time_column": anchor_time_col,
            "n_rows": int(anchor_rows),
        },
        "time_ingest": {"formats": [], "tz_policy": "strip_to_anchor_local", "ambiguous": [], "epoch_and_serial_detected": 0},
        "alignment": {
            "method": "merge_asof_backward",
            "max_age_factor": 3.0,
            "interpolation": "none",
            "forward_fill": "none",
            "rolling_features": False,
            "transport_lag_s": {},
        },
        "in_control_window": None,
        "sources": [],
        "outputs": {
            "joined_table": None,
            "contract": "07_hetero/column_contract.json",
            "explicit_cols": "07_hetero/explicit_cols.json",
            "features_dir": "07_hetero/features",
            "annotations": None,
            "objects_dir": None,
        },
        "h7_guard": {"anchor_sha256": sha256_file(anchor_path) if anchor_path else None, "files": h7_files, "written": []},
        "notes": [],
    }
