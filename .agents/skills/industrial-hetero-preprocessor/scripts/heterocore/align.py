"""align.py — anchor joining (frozen interface I10). Owned by WS5.

anchor_join() attaches feature snapshots to the anchor time axis:
  pandas.merge_asof(direction="backward") per source, staleness cap
  (max_age = max_age_factor * cadence_s; a camera ts_source doubles the
  factor; beyond the cap cells stay NaN — never ZOH, never interpolated),
  duplicate_key_policy="aggregate" collapses multi-snapshot stamps
  (numeric feature columns -> mean, n_inputs -> sum, ts deduplicated),
  transport_lag_s holds a snapshot stamped T back until anchor time
  T + lag — i.e. the source timeline is queried at (t - lag), plan §4
  "特征只用 t−lag 的输入": still causal, and a source-side step appears
  exactly lag seconds LATER on the anchor (frozen P6 assertion).
EVT columns (name contains "-EVT-") are never asof-carried: value = 1 at
anchor t iff some event ts satisfies  event_ts <= t < event_ts + window
(forward-only window, default 3600 s, per-column evt_window_s from
policy["contract_rows"]).
Row count/order of the joined table MUST equal the anchor (gate H2);
feature columns are appended at the tail only, sources ordered by
source_id (D6 fingerprint stability).

Sparse bookkeeping (frozen I8): stats_eligible requires joined-coverage
>= 0.5 and no insufficient_data flag; a column that is not
stats_eligible is always flagged sparse (R2: sparse HX columns must never
silently enter core_stats). The three explicit sparse triggers
(coverage<0.3, effective_n<30, cadence ratio >50x) stay as in the plan.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import time_ingest as ting

__all__ = ["AlignNotAvailable", "anchor_join", "aggregate_duplicate_stamps"]

DEFAULT_EVT_WINDOW_S = 3600.0
RESERVED_COLS = ("ts", "_src_ts", "n_inputs")
SPARSE_MAX_COVERAGE = 0.3
SPARSE_MIN_EFFECTIVE_N = 30
SPARSE_MAX_CADENCE_RATIO = 50.0
STATS_MIN_COVERAGE = 0.5


class AlignNotAvailable(Exception):
    """Backward-compat marker: build.py catches it. anchor_join no longer
    raises it — the implementation below is always available."""


# ---------------------------------------------------------------- helpers


def _parse_times(values, where: str) -> list:
    """Parse a whole time column with the skill's own parser (R4 discipline:
    never a home-grown regex, never silent time-of-day loss)."""
    out = []
    for i, v in enumerate(values):
        tv = ting.parse_ts(v)
        if tv.ts is None:
            raise ValueError(f"{where}: unparseable timestamp at row {i}: {v!r}")
        out.append(tv.ts)
    return out


def _median_gap_s(times: list) -> float | None:
    """Median positive gap in seconds; None when undefined (<2 stamps or
    all-identical)."""
    if len(times) < 2:
        return None
    a = np.array([(t - times[0]).total_seconds() for t in times], dtype=float)
    gaps = np.diff(a)
    gaps = gaps[gaps > 0]
    if not gaps.size:
        return None
    return float(np.median(gaps))


def _contract_index(contract_rows) -> tuple[dict, dict]:
    """(by_column, by_source) views over the optional policy["contract_rows"]."""
    by_col: dict = {}
    by_src: dict = {}
    for cr in contract_rows or []:
        if not isinstance(cr, dict):
            continue
        col = cr.get("column")
        if col and col not in by_col:
            by_col[col] = cr
        sid = cr.get("source_id")
        if sid and sid not in by_src:
            by_src[sid] = cr
    return by_col, by_src


def aggregate_duplicate_stamps(frame: pd.DataFrame, ts_parsed: list) -> tuple[pd.DataFrame, list]:
    """duplicate_key_policy="aggregate": collapse rows sharing one snapshot
    stamp. Numeric feature columns -> mean, n_inputs -> sum (missing cells
    count as 1 input per row), _src_ts -> last (latest write wins), other
    non-numeric columns -> first. Returns (deduped_frame, stamps) with the
    frame sorted by stamp, one row per distinct ts."""
    if len(frame) == 0:
        return frame.copy(), []
    df = frame.copy()
    if "n_inputs" in df.columns:
        df["n_inputs"] = pd.to_numeric(df["n_inputs"], errors="coerce").fillna(1.0)
    else:
        df["n_inputs"] = 1.0
    df["__stamp"] = pd.to_datetime(pd.Index(ts_parsed))
    sort_cols = ["__stamp"] + (["_src_ts"] if "_src_ts" in df.columns else [])
    df = df.sort_values(sort_cols, kind="stable")
    agg = {}
    for c in df.columns:
        if c == "__stamp":
            continue
        if c == "n_inputs":
            agg[c] = "sum"
        elif c == "_src_ts":
            agg[c] = "last"
        else:
            agg[c] = "mean" if pd.api.types.is_numeric_dtype(df[c]) else "first"
    out = df.groupby("__stamp", sort=True).agg(agg)
    stamps = list(out.index)
    out = out.reset_index(drop=True)
    return out, stamps


def _join_regular(anchor_keys: pd.DatetimeIndex, stamps: list, frame_d: pd.DataFrame,
                  reg_cols: list, lag_s: float, max_age_s: float) -> np.ndarray:
    """Backward merge_asof of the deduped source onto the anchor axis with a
    staleness cap. Returns an (n_anchor, len(reg_cols)) float array; cells
    with no usable snapshot (nothing at or before t-lag, or older than
    max_age measured from the moment the snapshot became usable) are NaN."""
    n = len(anchor_keys)
    if n == 0 or not reg_cols:
        return np.empty((n, len(reg_cols)), dtype=float)
    if len(stamps) == 0:
        return np.full((n, len(reg_cols)), np.nan)
    key = pd.to_datetime(pd.Index(stamps)) + pd.Timedelta(seconds=lag_s)
    left = pd.DataFrame({"_anchor_key": anchor_keys})
    right = pd.DataFrame({"_src_key": key})
    for c in reg_cols:  # feature cells are numeric by contract (I4); anything
        right[c] = pd.to_numeric(frame_d[c], errors="coerce").astype("float64")  # else → NaN, never invented
    merged = pd.merge_asof(left, right, left_on="_anchor_key", right_on="_src_key",
                           direction="backward")
    vals = merged[reg_cols].to_numpy(dtype=float, copy=True)
    age_s = (left["_anchor_key"].to_numpy() - merged["_src_key"].to_numpy()) / np.timedelta64(1, "s")
    stale = age_s > float(max_age_s)  # NaT ages (no match) -> False; those cells are NaN already
    if stale.any():
        vals[stale, :] = np.nan
    return vals


def _evt_column(events, anchor_keys: pd.DatetimeIndex, window_s: float) -> np.ndarray:
    """Forward-only event window: 1 iff event_ts <= t < event_ts + window.
    Vectorized with searchsorted (the most recent event at or before t marks
    the active window); never carried, never NaN."""
    n = len(anchor_keys)
    out = np.zeros(n, dtype="int64")
    if not events:
        return out
    ev = pd.to_datetime(pd.Index(sorted(events))).to_numpy().astype("datetime64[ns]")
    t = anchor_keys.to_numpy().astype("datetime64[ns]")
    idx = np.searchsorted(ev, t, side="right") - 1
    has = idx >= 0
    win = np.timedelta64(int(round(window_s * 1e9)), "ns")
    active = np.zeros(n, dtype=bool)
    active[has] = t[has] < (ev[idx[has]] + win)
    out[active] = 1
    return out


# ------------------------------------------------------------------- main


def anchor_join(anchor_df, features: dict, policy: dict):
    """Frozen interface I10.

    anchor_df : DataFrame containing `policy["anchor_time_col"]` (ISO strings,
                time-sorted, no duplicate stamps — both are validated with
                row-numbered ValueErrors).
    features  : {source_id: DataFrame[ts, _src_ts, n_inputs, <feature cols>]}
                with ts at the source's native cadence (ISO strings).
    policy    : {max_age_factor, duplicate_key_policy, transport_lag_s,
                 anchor_time_col[, ts_source{source_id: "dcs"|"camera"|...},
                 contract_rows[list of column-contract rows supplying
                 ts_source / cadence_s / insufficient_data / evt_window_s]]}

    Returns (joined_df, contract_updates) where joined_df is a copy of the
    anchor with feature columns appended at the tail (sources ordered by
    source_id, columns in frame order) and one update per feature column:
    {column, coverage, effective_n, sparse, stats_eligible}.
    """
    if not isinstance(anchor_df, pd.DataFrame):
        raise ValueError("anchor_df must be a pandas DataFrame")
    if not isinstance(features, dict):
        raise ValueError("features must be a dict {source_id: DataFrame}")
    policy = policy or {}

    time_col = policy.get("anchor_time_col")
    if not time_col:
        raise ValueError("policy['anchor_time_col'] is required")
    if time_col not in anchor_df.columns:
        raise ValueError(f"anchor_time_col {time_col!r} not in anchor columns")

    max_age_factor = policy.get("max_age_factor", 3.0)
    try:
        max_age_factor = float(max_age_factor)
    except (TypeError, ValueError):
        raise ValueError(f"max_age_factor must be a number, got {max_age_factor!r}")
    if not math.isfinite(max_age_factor) or max_age_factor <= 0:
        raise ValueError(f"max_age_factor must be finite and > 0, got {max_age_factor}")

    dup_policy = policy.get("duplicate_key_policy", "aggregate") or "aggregate"
    if dup_policy != "aggregate":
        # plan §4 offers subsecond_offset_ms as an opt-in; until specified we
        # refuse instead of guessing (歧义拒绝).
        raise ValueError(f"unsupported duplicate_key_policy {dup_policy!r} (only 'aggregate')")

    lag_map = policy.get("transport_lag_s") or {}
    ts_source_map = policy.get("ts_source") or {}
    by_col, by_src = _contract_index(policy.get("contract_rows"))

    # ---- anchor validation (排序/重复键门禁, row-numbered) ------------------
    a_ts = _parse_times(list(anchor_df[time_col]), "anchor")
    anchor_keys = pd.to_datetime(pd.Index(a_ts)) if a_ts else pd.to_datetime(pd.Index([]))
    n = len(a_ts)
    for i in range(1, n):
        if a_ts[i] < a_ts[i - 1]:
            raise ValueError(
                f"anchor must be time-sorted: row {i} ({a_ts[i]}) is earlier than row {i - 1} ({a_ts[i - 1]})")
        if a_ts[i] == a_ts[i - 1]:
            raise ValueError(
                f"anchor has duplicate timestamp at rows {i - 1} and {i}: {a_ts[i]}")
    anchor_cadence = _median_gap_s(a_ts)

    joined = anchor_df.copy(deep=True)
    anchor_cols = set(joined.columns)
    emitted: set = set()
    updates: list[dict] = []

    for sid in sorted(features):
        frame = features[sid]
        if not isinstance(frame, pd.DataFrame):
            raise ValueError(f"features[{sid!r}] must be a pandas DataFrame")
        if "ts" not in frame.columns:
            raise ValueError(f"source {sid!r}: features frame is missing the ts column")
        if sid in lag_map:
            try:
                lag_s = float(lag_map[sid] or 0.0)
            except (TypeError, ValueError):
                raise ValueError(f"transport_lag_s[{sid!r}] must be a number, got {lag_map[sid]!r}")
            if not math.isfinite(lag_s) or lag_s < 0:
                raise ValueError(f"transport_lag_s[{sid!r}] must be finite and >= 0, got {lag_s}")
        else:
            lag_s = 0.0

        raw_ts = _parse_times(list(frame["ts"]), f"source {sid!r}")
        # joined table carries ONLY HX-* derived columns (plan §3.3): retained
        # raw matrices (pos_*) stay in features/*.csv for the heatmap — appending
        # them here would inject non-HX columns past the H2 tail guard.
        feat_cols = [c for c in frame.columns
                     if c not in RESERVED_COLS and c.startswith("HX-")]
        for c in feat_cols:
            if c in anchor_cols or c in emitted:
                raise ValueError(f"feature column {c!r} (source {sid!r}) collides with an existing column")

        frame_d, stamps = aggregate_duplicate_stamps(frame, raw_ts)

        cadence = _median_gap_s(sorted(stamps))
        if cadence is None:
            cr = by_src.get(sid) or {}
            try:
                cadence = float(cr.get("cadence_s")) if cr.get("cadence_s") is not None else None
            except (TypeError, ValueError):
                cadence = None
        ts_source = ts_source_map.get(sid) or (by_src.get(sid) or {}).get("ts_source") or "dcs"
        factor = max_age_factor * (2.0 if str(ts_source).lower() == "camera" else 1.0)
        max_age_s = factor * (cadence if cadence is not None else 0.0)
        ratio = None
        if cadence and anchor_cadence:
            ratio = cadence / anchor_cadence

        reg_cols = [c for c in feat_cols if "-EVT-" not in c]
        reg_vals = _join_regular(anchor_keys, stamps, frame_d, reg_cols, lag_s, max_age_s)
        reg_pos = {c: i for i, c in enumerate(reg_cols)}

        for c in feat_cols:
            if "-EVT-" in c:
                truthy = pd.to_numeric(frame[c], errors="coerce").fillna(0.0).to_numpy() != 0.0
                events = [raw_ts[i] for i in np.where(truthy)[0]]
                cr = by_col.get(c) or {}
                try:
                    window_s = float(cr.get("evt_window_s")) if cr.get("evt_window_s") is not None \
                        else DEFAULT_EVT_WINDOW_S
                except (TypeError, ValueError):
                    window_s = DEFAULT_EVT_WINDOW_S
                col_vals = _evt_column(events, anchor_keys, window_s)
                effective_n = int(n)
            else:
                col_vals = reg_vals[:, reg_pos[c]]
                effective_n = int(np.count_nonzero(~np.isnan(col_vals)))
            joined[c] = col_vals
            emitted.add(c)

            coverage = (effective_n / n) if n else 0.0
            insufficient = bool((by_col.get(c) or {}).get("insufficient_data", False))
            stats_eligible = bool(n > 0 and coverage >= STATS_MIN_COVERAGE and not insufficient)
            sparse = bool(coverage < SPARSE_MAX_COVERAGE
                          or effective_n < SPARSE_MIN_EFFECTIVE_N
                          or (ratio is not None and ratio > SPARSE_MAX_CADENCE_RATIO)
                          or not stats_eligible)  # frozen I8: not eligible ⇒ sparse
            updates.append({
                "column": c,
                "coverage": float(coverage),
                "effective_n": int(effective_n),
                "sparse": bool(sparse),
                "stats_eligible": bool(stats_eligible),
            })

    return joined, updates
