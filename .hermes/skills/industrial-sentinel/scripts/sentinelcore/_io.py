"""_io.py — data loading, inline path containment, column identification.

File-IO discipline (same as industrial-doe-analyzer): every path passes
through `_contained()` (normpath + traversal-segment rejection + repo-root
prefix whitelist) and all reads/writes use pathlib methods — there is no raw
open() anywhere in this skill.
"""

import datetime
import hashlib
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from sentinelcore._constants import REPO_ROOT

REPO_ROOT_NORM = os.path.normpath(os.path.abspath(str(REPO_ROOT)))

TIME_HINTS = re.compile(r"(time|date|timestamp|时刻|时间|日期)", re.IGNORECASE)
GROUP_HINTS = re.compile(r"(group|line|batch|shift|product|机组|产线|批次|班组|产品|产线号|线体)", re.IGNORECASE)
ID_HINTS = re.compile(r"(^id$|_id$|^no$|_no$|编号|序号|^index$|^row$)", re.IGNORECASE)
EPOCH_THRESHOLD = 1e8  # numeric time values above this are treated as epoch seconds

GROUP_ALL = "__ALL__"


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _contained(candidate, extra_root=None):
    """Return `candidate` normalized as a Path, enforcing containment inline:
    normpath -> reject any traversal segment -> repo-root prefix whitelist."""
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    roots = [REPO_ROOT_NORM]
    if extra_root is not None:
        roots.append(os.path.normpath(os.path.abspath(str(extra_root))))
    for root in roots:
        if cand == root or cand.startswith(root + os.sep):
            return Path(cand)
    raise ValueError(f"path outside allowed roots: {candidate}")


def sha256_file(path):
    h = hashlib.sha256()
    data = Path(path).read_bytes()
    h.update(data)
    return h.hexdigest()


def read_json(path):
    return json_loads(_contained(path).read_text(encoding="utf-8"))


def json_loads(text):
    import json

    return json.loads(text)


def write_json(path, payload):
    import json

    out = _contained(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=float),
                   encoding="utf-8")


def write_text(path, text):
    out = _contained(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def load_table(path):
    """Load a CSV/TSV/Parquet table via pandas (multi-format via extension)."""
    safe = _contained(path)
    suffix = safe.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(safe)
    if suffix in (".tsv", ".tab"):
        return pd.read_csv(safe, sep="\t")
    return pd.read_csv(safe)


def identify_columns(df, time_col=None, group_col=None):
    """Resolve time/group columns: explicit config wins, then hint regexes."""
    cols = [str(c) for c in df.columns]
    if time_col is None:
        time_col = next((c for c in cols if TIME_HINTS.search(c)), None)
    if group_col is None:
        cand = [c for c in cols if GROUP_HINTS.search(c)]
        # group column must be low-cardinality relative to row count
        group_col = next(
            (c for c in cand
             if df[c].nunique(dropna=True) <= max(1, min(50, len(df) // 10))),
            None)
    return time_col, group_col


def numeric_columns(df, exclude=()):
    """Numeric columns (>=70% coercible), excluding time/group/id columns."""
    excl = {str(c) for c in exclude if c is not None}
    out = []
    for c in df.columns:
        cs = str(c)
        if cs in excl or ID_HINTS.search(cs):
            continue
        if time_like(df[c]):
            continue
        coerced = pd.to_numeric(df[c], errors="coerce")
        if coerced.notna().mean() > 0.7 and coerced.nunique(dropna=True) > 1:
            out.append(cs)
    return out


def time_like(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        sample = series.dropna().head(20).astype(str)
        if sample.empty:
            return False
        hits = sum(1 for v in sample if re.search(r"[-/:]\d", v))
        return hits >= len(sample) * 0.8
    return False


def split_groups(df, group_col):
    """Ordered dict group -> sub-DataFrame. No group column -> single pseudo-group."""
    if group_col is not None and str(group_col) in df.columns:
        ordered = list(dict.fromkeys(df[str(group_col)].dropna().astype(str)))
        return {g: df[df[str(group_col)].astype(str) == g] for g in ordered}
    return {GROUP_ALL: df}


def to_arrays(sub_df, cols):
    """dict col -> float ndarray preserving NaN."""
    out = {}
    for c in cols:
        out[c] = pd.to_numeric(sub_df[c], errors="coerce").to_numpy(dtype=float)
    return out


def hours_axis(sub_df, time_col):
    """Numeric hour axis for slope computations; None when unusable.

    datetime column  -> (t - t0) in hours
    numeric epoch s  -> (v - v0) / 3600
    numeric small    -> treated as already-hours (documented convention)
    """
    if time_col is None or str(time_col) not in sub_df.columns:
        return None
    s = sub_df[str(time_col)]
    if pd.api.types.is_datetime64_any_dtype(s):
        vals = s.astype("int64").to_numpy() / 1e9
        return (vals - vals[0]) / 3600.0
    parsed = pd.to_datetime(s, errors="coerce")
    if parsed.notna().mean() > 0.9:
        vals = parsed.astype("int64").to_numpy() / 1e9
        return (vals - vals[0]) / 3600.0
    num = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    if np.nanmean(np.abs(num[np.isfinite(num)])) > EPOCH_THRESHOLD:
        return (num - num[0]) / 3600.0
    return num - num[0]
