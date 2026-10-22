"""Data loading, time slicing and column-role inference for lstcore."""
from __future__ import annotations

import csv
import hashlib
import json
import os

import numpy as np
import pandas as pd

DATA_SUFFIXES = (".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json")
# Metadata/artifact residents of 00_input that must never be picked as the data
# table (exact-name or suffix match — .json stays a legitimate data format).
AUX_EXACT_NAMES = {
    "report_context.json",
    "run_config.json",
    "input_manifest.json",
    "preprocessing_report.json",
    "ontology.json",
    "ontology_brief.json",
    "ontology_coverage.json",
}
AUX_NAME_SUFFIXES = ("action_log.json", "_manifest.json")
# Heuristic names for inspection (quality) columns when context does not pin them.
INSPECTION_HINTS = ("yield", "quality", "qual", "defect", "scrapp", "reject",
                    "pass_rate", "ok_rate", "ng_rate", "spec", "grade", "pct_good")

INSPECTOR_COLUMNS = ["time", "timestamp", "ts", "datetime", "date", "_dt"]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def find_data_file(run_dir: str) -> str | None:
    """Locate the primary data file under <run_dir>/00_input (or run_dir itself)."""
    for base in (os.path.join(run_dir, "00_input"), run_dir):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            low = name.lower()
            if not low.endswith(DATA_SUFFIXES):
                continue
            if low in AUX_EXACT_NAMES or low.endswith(AUX_NAME_SUFFIXES):
                continue
            return os.path.join(base, name)
    return None


def load_table(path: str) -> pd.DataFrame:
    """Load a tabular file into a DataFrame. Raises ValueError on unsupported/empty."""
    low = path.lower()
    if low.endswith(".csv"):
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            # 中文 Windows 导出常见 GBK/GB18030：utf-8 解码失败时回退重试
            try:
                df = pd.read_csv(path, encoding="gb18030")
            except UnicodeDecodeError as exc:
                raise ValueError(f"csv decoding failed (need utf-8 or gb18030): {exc}") from exc
    elif low.endswith(".tsv"):
        df = pd.read_csv(path, sep="\t")
    elif low.endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(path)
        except ImportError as exc:  # openpyxl missing
            raise ValueError(f"excel support unavailable ({exc}); use CSV") from exc
    elif low.endswith(".parquet"):
        df = pd.read_parquet(path)
    elif low.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list):
                    payload = value
                    break
        if not isinstance(payload, list):
            raise ValueError("json table must be an array of row objects")
        df = pd.DataFrame(payload)
    else:
        raise ValueError(f"unsupported data suffix: {path}")
    if df.empty:
        raise ValueError("data table is empty")
    return df


def pick_time_col(df: pd.DataFrame, preferred: str | None) -> str:
    if preferred:
        if preferred in df.columns:
            return preferred
        raise ValueError(f"time column '{preferred}' not in data")
    for name in df.columns:
        if str(name).strip().lower() in INSPECTOR_COLUMNS:
            return name
    # last resort: first column whose values parse as datetimes
    for name in df.columns:
        parsed = pd.to_datetime(df[name], errors="coerce")
        if parsed.notna().mean() > 0.9:
            return name
    raise ValueError("no usable time column found; pass --time-col")


def parse_time(df: pd.DataFrame, time_col: str) -> tuple[pd.DataFrame, str]:
    """Return (df, mode) with a normalized `_dt` column; drops unparseable rows.

    Contract (SKILL.md): numeric time columns are epoch SECONDS. A numeric-dtype
    column must go down the numeric path directly — `pd.to_datetime` would
    silently parse the integers as nanoseconds since epoch (mode "datetime",
    intervals ~1e-6 s), inflating every drift rate ~1e9×. Timezone-aware
    datetime inputs are normalized to naive UTC so downstream numpy dtype
    checks (np.issubdtype on datetime64[ns]) stay valid.
    """
    raw = df[time_col]
    out = df.copy()
    if pd.api.types.is_numeric_dtype(raw):
        parsed = pd.to_numeric(raw, errors="coerce")
        if parsed.notna().mean() < 0.5:
            raise ValueError(f"time column '{time_col}' is numeric but not usable")
        out["_dt"] = parsed
        mode = "numeric"
    else:
        parsed = pd.to_datetime(raw, errors="coerce")
        mode = "datetime"
        if parsed.notna().mean() < 0.5:
            numeric = pd.to_numeric(raw, errors="coerce")
            if numeric.notna().mean() < 0.5:
                raise ValueError(f"time column '{time_col}' is neither datetime nor numeric")
            parsed = numeric
            out["_dt"] = parsed
            mode = "numeric"
        else:
            if isinstance(parsed.dtype, pd.DatetimeTZDtype):
                parsed = parsed.dt.tz_convert("UTC").dt.tz_localize(None)
            out["_dt"] = parsed
    out = out[out["_dt"].notna()].reset_index(drop=True)
    out = out.sort_values("_dt", kind="stable").reset_index(drop=True)
    if out.empty:
        raise ValueError("no rows with parseable time values")
    return out, mode


def slice_period(df: pd.DataFrame, start, end) -> tuple[pd.DataFrame, dict]:
    """Slice rows to [start, end] (either may be None). Returns (df, requested)."""
    requested = {"start": start, "end": end}
    if start is not None:
        s = pd.to_datetime(start, errors="coerce")
        if s is not pd.NaT and not pd.isna(s):
            df = df[df["_dt"] >= s]
    if end is not None:
        e = pd.to_datetime(end, errors="coerce")
        if e is not pd.NaT and not pd.isna(e):
            df = df[df["_dt"] <= e]
    return df.reset_index(drop=True), requested


def infer_roles(df: pd.DataFrame, time_col: str, context: dict) -> dict:
    """Split columns into parameter_cols / inspection_cols / ignored."""
    drop = {time_col, "_dt"}
    group_col = context.get("group_col")
    if group_col:
        drop.add(group_col)
    pinned_params = context.get("parameter_cols") or None
    pinned_insp = context.get("inspection_cols") or None
    numeric = [c for c in df.columns
               if c not in drop and pd.api.types.is_numeric_dtype(df[c])]
    non_numeric = [c for c in df.columns if c not in drop and c not in numeric]
    if pinned_params:
        parameter_cols = [c for c in pinned_params if c in df.columns]
    else:
        parameter_cols = list(numeric)
    if pinned_insp:
        inspection_cols = [c for c in pinned_insp if c in df.columns]
    else:
        inspection_cols = [c for c in numeric
                           if any(h in str(c).lower() for h in INSPECTION_HINTS)]
    inspection_cols = [c for c in inspection_cols if c in parameter_cols]
    return {
        "time_col": time_col,
        "group_col": group_col,
        "parameter_cols": parameter_cols,
        "inspection_cols": inspection_cols,
        "ignored_cols": non_numeric,
    }
