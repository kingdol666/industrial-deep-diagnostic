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


SHA256_CHUNK_BYTES = 1024 * 1024   # stream large inputs, never read_bytes() whole


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(SHA256_CHUNK_BYTES), b""):
            h.update(chunk)
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


def append_text(path, text):
    """Append UTF-8 text (JSON Lines event logs); never truncates."""
    out = _contained(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(text)


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


_DATETIME_UNIT_HOURS = {  # one native unit -> hours (x count)
    "s": 3600.0, "ms": 3.6e6, "us": 3.6e9, "ns": 3.6e12,
}

# numeric epoch detection: (magnitude lower bound, divisor to hours), largest
# first. Unit bands are ~1e3 apart (1e11 s would be year 5138, 1e11 ms is
# 1970-01-02, ...), so magnitude uniquely identifies the epoch unit.
_EPOCH_UNIT_LADDER = (
    (1e17, 3.6e12),  # epoch ns
    (1e14, 3.6e9),   # epoch us
    (1e11, 3.6e6),   # epoch ms
    (EPOCH_THRESHOLD, 3600.0),  # epoch s
)


def _hours_from_datetime(series):
    """(t - t0) in hours for a datetime64 Series of ANY unit.

    pandas >= 3 parses ISO strings to datetime64[us] (and keeps other native
    units), so naive ``astype('int64') / 1e9`` hour math is off by 1e3 (us)
    or worse. Normalize to datetime64[ns] first; fall back to native-unit
    scaling only for dates outside the representable ns range.
    """
    if getattr(series.dtype, "tz", None) is not None:
        series = series.dt.tz_convert("UTC").dt.tz_localize(None)
    try:
        vals = series.astype("datetime64[ns]").astype("int64").to_numpy()
        return (vals - vals[0]) / 3.6e12
    except (pd.errors.OutOfBoundsDatetime, OverflowError, ValueError):
        unit, count = np.datetime_data(series.dtype)
        scale = _DATETIME_UNIT_HOURS.get(str(unit), 3.6e12) * max(1, int(count))
        vals = series.astype("int64").to_numpy(dtype=float)
        return (vals - vals[0]) / scale


def _hours_from_numeric(num):
    """Hour axis from numeric time values: epoch ns/us/ms/s detected by
    magnitude (see _EPOCH_UNIT_LADDER); below EPOCH_THRESHOLD values are
    treated as already-hours (documented convention)."""
    finite = num[np.isfinite(num)]
    scale = float(np.nanmean(np.abs(finite))) if finite.size else 0.0
    for threshold, divisor in _EPOCH_UNIT_LADDER:
        if scale > threshold:
            return (num - num[0]) / divisor
    return num - num[0]


def hours_axis(sub_df, time_col):
    """Numeric hour axis for slope computations; None when unusable.

    datetime column  -> (t - t0) in hours (unit-normalized via
                        _hours_from_datetime: pandas 3 parses ISO strings to
                        datetime64[us]; ns-normalization keeps the axis
                        identical across input representations)
    numeric          -> epoch ns/us/ms/s by magnitude (_hours_from_numeric);
                        below EPOCH_THRESHOLD treated as already-hours
    """
    if time_col is None or str(time_col) not in sub_df.columns:
        return None
    s = sub_df[str(time_col)]
    if pd.api.types.is_datetime64_any_dtype(s):
        return _hours_from_datetime(s)
    num_probe = pd.to_numeric(s, errors="coerce")
    if num_probe.notna().mean() > 0.9:
        return _hours_from_numeric(num_probe.to_numpy(dtype=float))
    parsed = pd.to_datetime(s, errors="coerce")
    if parsed.notna().mean() > 0.9:
        return _hours_from_datetime(parsed)
    return _hours_from_numeric(num_probe.to_numpy(dtype=float))
