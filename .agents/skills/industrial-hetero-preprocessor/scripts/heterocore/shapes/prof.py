#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prof.py — PROF shape module (WS1): profile / vector-over-time scans.

Interface I9 (frozen): build.py dynamically imports this file and calls
    detect(candidates: list[Path], ctx) -> list[{"spec": {...}, "shape": "profile", "meta": {...}}]
    extract(spec: dict, ctx)            -> {"source": {...}, "rows": DataFrame,
                                           "contract": [...], "annotations": [], "objects": []}

Detection heuristics (numeric density + column count, probe of the first 60
rows only — never a full-table parse at detect time):

wide   a time column exists (name contains 时间/时间戳/timestamp/datetime/
       date/time/日期 and >= 80% of probe values parse via heterocore.time_ingest;
       otherwise the first NON-numeric-dense column with parse ok-rate >= 0.9 —
       a numeric-dense column is never guessed to be time) AND >= 8 numeric
       columns (numeric density >= 0.8) that EITHER
         (a) share a position naming pattern pos_N / pN / chN / chanN /
             channelN / pointN / ptN / 位置N / 测点N / 通道N / 点位N
             (pattern share >= 0.6 of the numeric columns), OR
         (b) are ALL non-time columns and are magnitude-similar:
             max/min of per-column |median| <= 1e4 — one physical quantity
             scanned across positions, not unrelated process tags.
long   exactly 3-4 columns: the time column plus EXACTLY TWO numeric columns;
       the one with the higher duplicate ratio (ties: fewer distinct values,
       then leftmost) is the position axis and must hold >= 3 distinct values.

extract pivots the long layout into the snapshot x position matrix, retains it
verbatim as pos_01..pos_N columns (I4: features CSV keeps the original matrix
for the heatmap / H3 audit), and derives 18 deterministic features per
snapshot, formulas verbatim from references/method_notes.md §1 (implemented by
heterocore.robust): MEAN STD MIN MAX P05 P50 P95 RANGE IQR MAD N (amplitude),
SLOPE-LSQ-PER100 CURV-LSQ ZONE-1-3-MEAN EDGE-L-DEV EDGE-R-DEV (shape),
ARGDEV-NBR (localisation), SHIFT-EST (registration vs the in-control baseline
template: per-position median of the snapshots inside the declared
in_control_window, else the first max(3, ceil(20%)) snapshots).

Partial-profile policy (plan §3.1): a snapshot whose finite fraction is below
0.6 keeps its amplitude features but every shape feature (SLOPE/CURV/ZONE/
EDGE-L/EDGE-R/SHIFT) is NaN for that row. A feature that NO snapshot could
compute (e.g. n_positions < 6 makes EDGE impossible forever) gets
insufficient_data=true on its contract row. SHIFT-EST additionally requires
the snapshot's missing-position pattern to match the baseline template's
(position-paired correlation; misaligned NaN patterns => NaN, never guessed).

Time is parsed ONLY via heterocore.time_ingest (never pandas to_datetime
guessing — plan R4); a source with ambiguous day/month order is refused, not
guessed (plan §4). Duplicate snapshot timestamps are aggregated by mean
(duplicate_key_policy="aggregate"). Deterministic: no RNG, no network, no LLM.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_SCRIPTS = Path(__file__).resolve().parents[2]  # .../scripts
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from heterocore import CONTRACT_VERSION  # noqa: E402
from heterocore import manifest as mani  # noqa: E402
from heterocore import naming  # noqa: E402
from heterocore import robust as rb  # noqa: E402
from heterocore import time_ingest as ting  # noqa: E402

SHAPE = "profile"
TABLE_EXTS = {".csv", ".tsv", ".txt", ".dat"}
PROBE_ROWS = 60

NUM_DENSITY = 0.8          # column counts as numeric at/above this parse density
MIN_NUMERIC_WIDE = 8       # wide layout needs at least this many numeric columns
PREFIX_SHARE_MIN = 0.6     # share of numeric columns matching a position pattern
MAG_RATIO_MAX = 1e4        # fallback wide: max/min of per-column |median|
ADJ_COHERENCE_MIN = 0.25   # fallback wide: adjacent-column temporal coherence floor
TIME_OK_RATE = 0.8         # named time column must parse at/above this
TIME_OK_RATE_FALLBACK = 0.9  # unnamed parseable time column (stricter)

PARTIAL_FRACTION = 0.6     # finite fraction below this => shape features NaN (row)
BASELINE_MIN_SNAPSHOTS = 3
BASELINE_FRACTION = 0.2    # fallback baseline = first max(3, ceil(20%)) snapshots

TIME_NAME_TOKENS = ("时间", "时间戳", "timestamp", "datetime", "date", "time", "日期")
POS_NAME_RE = re.compile(r"^(pos|p|ch|chan|channel|point|pt)[_\- ]?\d+$", re.IGNORECASE)
POS_CJK_PREFIX = ("位置", "测点", "通道", "点位")

FEATURE_ORDER = [
    "MEAN", "STD", "MIN", "MAX", "P05", "P50", "P95", "RANGE", "IQR", "MAD", "N",
    "SLOPE-LSQ-PER100", "CURV-LSQ", "ZONE-1-3-MEAN",
    "EDGE-L-DEV", "EDGE-R-DEV", "ARGDEV-NBR", "SHIFT-EST",
]
# shape-class features withheld on partial snapshots (plan §3.1 partial-profile policy)
SHAPE_FEATURES = {"SLOPE-LSQ-PER100", "CURV-LSQ", "ZONE-1-3-MEAN",
                  "EDGE-L-DEV", "EDGE-R-DEV", "SHIFT-EST"}

_L1_BASIS = ("deterministic statistic of a retained source snapshot (formula above); "
             "L1 per method_notes §1 evidence levelling")


def _meta(tag_cn, tag_en, meaning, formula, physics, unit_kind, method):
    return {"tag_cn": tag_cn, "tag_en": tag_en, "meaning": meaning,
            "formula": formula, "physics": physics, "unit_kind": unit_kind,
            "method": method}


FEATURE_META = {
    "MEAN": _meta("剖面均值", "profile mean",
                  "该快照全部有效位置测值的算术平均，代表剖面整体质量水平",
                  "mean(x_finite)",
                  "同一横断面物理量采样的一阶矩；整体增厚/减薄直接反映在均值上",
                  "source", "heterocore.robust.mean"),
    "STD": _meta("剖面标准差", "profile std",
                 "该快照有效位置测值的标准差（ddof=1），刻画剖面内不均匀度",
                 "std(x_finite, ddof=1)",
                 "同一横断面内的离散度；板形波动/厚度不均在标准差上直接显形",
                 "source", "heterocore.robust.std"),
    "MIN": _meta("剖面最小值", "profile min", "该快照有效位置测值的最小值",
                 "min(x_finite)", "剖面最薄点（下限极值）",
                 "source", "heterocore.robust.vmin"),
    "MAX": _meta("剖面最大值", "profile max", "该快照有效位置测值的最大值",
                 "max(x_finite)", "剖面最厚点（上限极值）",
                 "source", "heterocore.robust.vmax"),
    "P05": _meta("剖面5%分位", "profile p05",
                 "该快照有效位置测值的 5% 分位数（线性插值），稳健下包络",
                 "numpy.percentile(x_finite, 5, method='linear')",
                 "分位数比极值抗单点噪声，P05 稳健刻画剖面下包络水平",
                 "source", "numpy.percentile(linear)"),
    "P50": _meta("剖面中位数", "profile p50",
                 "该快照有效位置测值的 50% 分位数（线性插值）",
                 "numpy.percentile(x_finite, 50, method='linear')",
                 "中位数是抗离群的整体水平读数，与均值互为对照",
                 "source", "numpy.percentile(linear)"),
    "P95": _meta("剖面95%分位", "profile p95",
                 "该快照有效位置测值的 95% 分位数（线性插值），稳健上包络",
                 "numpy.percentile(x_finite, 95, method='linear')",
                 "分位数比极值抗单点噪声，P95 稳健刻画剖面上包络水平",
                 "source", "numpy.percentile(linear)"),
    "RANGE": _meta("剖面极差", "profile range",
                   "该快照有效位置测值最大值减最小值（剖面总幅值跨度）",
                   "max(x_finite) - min(x_finite)",
                   "极差是最直接的剖面总波动幅度度量（对单点噪声敏感，与 IQR 互为对照）",
                   "source", "heterocore.robust.vmax - vmin"),
    "IQR": _meta("剖面四分位距", "profile iqr",
                 "该快照 75% 分位减 25% 分位（剖面包络宽度，抗端点噪声）",
                 "numpy.percentile(x_finite, 75) - numpy.percentile(x_finite, 25)",
                 "四分位距是稳健散布度量，不受剖面两端单点异常影响",
                 "source", "heterocore.robust.iqr"),
    "MAD": _meta("剖面中位绝对偏差", "profile mad",
                 "该快照有效值的中位绝对偏差（不带 1.4826 因子，稳健散布）",
                 "median(|x_finite - median(x_finite)|)  # no 1.4826 factor",
                 "MAD 对离群点稳健；口径按 method_notes 冻结为原始 MAD（不乘一致性因子）",
                 "source", "heterocore.robust.mad"),
    "N": _meta("有效点数", "profile finite count",
               "该快照有限（可测）位置点数，剖面完整性指标",
               "count(x_finite)",
               "完整性决定形状类结论的可信边界：点数不足时形状特征按策略弃用",
               "count", "heterocore.robust.n_finite"),
    "SLOPE-LSQ-PER100": _meta("剖面斜率(每100位)", "profile LSQ slope per 100 positions",
                              "对有效位置做一次最小二乘拟合的斜率，按每 100 个位置归一（剖面整体倾斜度）",
                              "polyfit(0..k-1, x_finite, 1)[0] * 100/(k-1), k=count(x_finite)",
                              "剖面整体倾斜对应横向厚度/浓度梯度；最小二乘斜率在均匀采样栅格上收敛于真实梯度",
                              "source", "heterocore.robust.lsq_slope_curv(per_n=100).slope"),
    "CURV-LSQ": _meta("剖面二次项系数", "profile LSQ curvature",
                      "对有效位置做二次多项式最小二乘拟合的二次项系数（剖面凸度/板形弯曲）",
                      "polyfit(0..k-1, x_finite, 2)[0], k>=4",
                      "二次项系数是剖面 Crown（凸度）的线性读数，板形/厚度横向弯曲的直接度量",
                      "source", "heterocore.robust.lsq_slope_curv(per_n=100).curv"),
    "ZONE-1-3-MEAN": _meta("剖面1区均值(三等分)", "profile zone-1-of-3 mean",
                           "剖面三等分后第 1 区（起始段，操作侧）的平均值",
                           "mean(x_finite[linspace(0,k,4)[0]:linspace(0,k,4)[1]])",
                           "分区均值把连续剖面离散为工艺分区水平，便于分区归因（操作侧/中部/传动侧）",
                           "source", "heterocore.robust.zone_means(n_zones=3)[0]"),
    "EDGE-L-DEV": _meta("左边缘偏差", "profile left edge deviation",
                        "左侧 10% 边缘带均值减中心带均值（操作侧边缘增/减厚）",
                        "mean(x_finite[0:w]) - mean(x_finite[w:k-w]), w=max(1,round(k*0.1)), k>=6",
                        "边缘增减厚（edge drop）是剖面最常见缺陷形态；外侧带-中心带对比是其直接度量",
                        "source", "heterocore.robust.edge_band_deviation(band_frac=0.10).edge_l"),
    "EDGE-R-DEV": _meta("右边缘偏差", "profile right edge deviation",
                        "右侧 10% 边缘带均值减中心带均值（传动侧边缘增/减厚）",
                        "mean(x_finite[k-w:k]) - mean(x_finite[w:k-w]), w=max(1,round(k*0.1)), k>=6",
                        "边缘增减厚（edge drop）是剖面最常见缺陷形态；外侧带-中心带对比是其直接度量",
                        "source", "heterocore.robust.edge_band_deviation(band_frac=0.10).edge_r"),
    "ARGDEV-NBR": _meta("最大邻域偏差位置", "profile argmax neighbour deviation",
                        "邻域偏差绝对值最大的位置点号（0 基；局部异常点的剖面内定位）",
                        "argmax_i |x[i] - mean(finite neighbours of i)| (0-based index)",
                        "局部异常点在邻域对比下最突出；取最大邻域偏差的位置作剖面内定位",
                        "index", "heterocore.robust.max_abs_neighbour_deviation().argmax"),
    "SHIFT-EST": _meta("横向偏移估计", "profile lateral shift estimate",
                       "对基线模板（in-control 逐位中位剖面）互相关估计的整位横向偏移（右移为正）",
                       "argmax_s corr(profile[overlap], baseline[overlap-shift]); integer s, overlap>=max(3,k/3)",
                       "横向配准漂移会被误读为形状变化（J. Process Control 2011 告诫）；先看 SHIFT 再解释 EDGE",
                       "index", "heterocore.robust.cross_correlation_shift vs in-control median template"),
}


# ────────────────────────────── small probes ──────────────────────────────

def _read_table(path: Path, nrows: int | None = None):
    """Read a delimiter-sniffed table. utf-8-sig first, gbk fallback. None if unreadable."""
    for enc in ("utf-8-sig", "gbk"):
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=enc, nrows=nrows)
        except Exception:
            continue
    for enc in ("utf-8-sig", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc, nrows=nrows)
        except Exception:
            continue
    return None


def _density(series) -> float:
    v = series[series.notna()]
    if not len(v):
        return 0.0
    return float(pd.to_numeric(v, errors="coerce").notna().mean())


def _dup_ratio(series) -> float:
    v = series[series.notna()]
    n = len(v)
    if not n:
        return 0.0
    return 1.0 - float(v.nunique()) / float(n)


def _nunique(series) -> int:
    return int(series.dropna().nunique())


def _is_pos_name(c) -> bool:
    s = str(c).strip()
    if POS_NAME_RE.match(s):
        return True
    return any(s.startswith(p) and any(ch.isdigit() for ch in s) for p in POS_CJK_PREFIX)


def _magnitude_ratio(df, cols) -> float:
    meds = []
    for c in cols:
        v = rb.finite(pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float))
        meds.append(float(np.median(np.abs(v))) if v.size else 0.0)
    hi = max(meds) if meds else 0.0
    lo = min((m for m in meds if m > 1e-12), default=0.0)
    if hi <= 0:
        return 1.0
    return hi / max(lo, 1e-12)


def _adjacent_coherence(df, cols, sample: int = 300) -> float:
    """Median pairwise temporal correlation of ADJACENT columns.

    A profile is one physical quantity sampled along one spatial axis, so
    neighbouring positions co-move over time (shared process state), even when
    their absolute levels differ. A narrow multi-signal table (e.g. LIMS haze /
    gel / strength) passes the magnitude gate but its adjacent columns are
    unrelated — coherence is the discriminator that keeps it out of PROF.
    """
    sub = df[cols].head(sample).apply(pd.to_numeric, errors="coerce")
    cors = []
    for left, right in zip(cols, cols[1:]):
        pair = sub[[left, right]].dropna()
        if len(pair) < 20:
            continue
        a, b = pair[left], pair[right]
        if a.std() <= 0 or b.std() <= 0:
            continue
        value = float(a.corr(b))
        if np.isfinite(value):
            cors.append(value)
    return float(np.median(cors)) if cors else 0.0


def _find_time_col(df):
    """(time_col, parse_series_result) — name tokens first, then parseability.
    A numeric-dense column is never guessed to be time (epoch cols excluded on
    purpose: a 22-column sensor table with an epoch stamp must not silently
    turn its stamp into a 'position')."""
    cols = list(df.columns)
    named = [c for c in cols if any(tok in str(c).lower() for tok in TIME_NAME_TOKENS)]
    for c in named:
        res = ting.parse_series(df[c].head(200).tolist())
        if res["ok_rate"] >= TIME_OK_RATE:
            return c, res
    for c in cols:
        if c in named:
            continue
        if _density(df[c]) >= 0.5:
            continue
        res = ting.parse_series(df[c].head(200).tolist())
        if res["ok_rate"] >= TIME_OK_RATE_FALLBACK:
            return c, res
    return None, None


def _identify(df):
    """-> (layout, info) | (None, reason). layout in {"wide","long"}."""
    n_row, n_col = df.shape
    if n_row < 3 or n_col < 2:
        return None, "fewer than 3 data rows or 2 columns"
    tcol, _ = _find_time_col(df)
    if tcol is None:
        return None, "no time column (name token or parseable non-numeric column)"
    others = [c for c in df.columns if c != tcol]
    numcols = [c for c in others if _density(df[c]) >= NUM_DENSITY]

    # long: 时间,位置,值[,备注] — 3-4 columns, exactly two numeric non-time columns
    if 3 <= n_col <= 4 and len(numcols) == 2:
        order = {c: i for i, c in enumerate(df.columns)}

        def _long_key(c):
            return (-_dup_ratio(df[c]), _nunique(df[c]), order[c])

        pos, val = sorted(numcols, key=_long_key)
        n_pos = _nunique(df[pos])
        if n_pos >= 3:
            return "long", {"time_col": tcol, "pos_col": pos, "val_col": val,
                            "n_positions": n_pos,
                            "heuristic": ("3-4 columns with exactly 2 numeric; position = higher "
                                          f"duplicate ratio ({str(pos)}), >=3 distinct (={n_pos})")}
        return None, "two numeric columns but fewer than 3 distinct positions"

    # wide: time + >=8 numeric columns, position-pattern or magnitude-similar
    if len(numcols) >= MIN_NUMERIC_WIDE:
        pref = [c for c in numcols if _is_pos_name(c)]
        share = len(pref) / len(numcols)
        if share >= PREFIX_SHARE_MIN:
            return "wide", {"time_col": tcol, "pos_cols": numcols,
                            "heuristic": (f"position-pattern names on {len(pref)}/{len(numcols)} "
                                          f"numeric columns (share {share:.2f} >= {PREFIX_SHARE_MIN})")}
        if len(numcols) == len(others):
            ratio = _magnitude_ratio(df, numcols)
            if ratio <= MAG_RATIO_MAX:
                coherence = _adjacent_coherence(df, numcols)
                if coherence >= ADJ_COHERENCE_MIN:
                    return "wide", {"time_col": tcol, "pos_cols": numcols,
                                    "heuristic": (f"all {len(numcols)} non-time columns numeric, "
                                                  f"magnitude-similar (ratio {ratio:.1f} <= {MAG_RATIO_MAX:g}) "
                                                  f"and adjacent-coherent (median r {coherence:.2f} >= "
                                                  f"{ADJ_COHERENCE_MIN})")}
                return None, (f"{len(numcols)} numeric columns are magnitude-similar (ratio {ratio:.1f}) "
                              f"but not spatially coherent (adjacent median r {coherence:.2f} < "
                              f"{ADJ_COHERENCE_MIN}) — reads as a narrow multi-signal table, not a profile")
            return None, (f"{len(numcols)} numeric columns but heterogeneous magnitudes "
                          f"(ratio {ratio:.1f} > {MAG_RATIO_MAX:g}) — reads as unrelated tags")
        return None, (f"only {len(pref)}/{len(numcols)} numeric columns match a position "
                      f"pattern (share {share:.2f} < {PREFIX_SHARE_MIN})")
    return None, (f"only {len(numcols)} numeric column(s) beside the time column "
                  f"(wide needs >= {MIN_NUMERIC_WIDE}, long needs exactly 2)")


# ────────────────────────────── detect (I9) ──────────────────────────────

def detect(candidates, ctx):
    """Claim table files laid out as profile wide/long scans. Probe-only."""
    out = []
    for p in candidates or []:
        try:
            p = Path(p)
            if p.suffix.lower() not in TABLE_EXTS:
                continue
            df = _read_table(p, nrows=PROBE_ROWS)
            if df is None or df.empty:
                continue
            layout, info = _identify(df)
            if layout is None:
                continue
            taken = getattr(ctx, "taken_slugs", None)
            if taken is None:  # never swap the caller's registry for a copy
                taken = {}
            slug, sha6 = naming.unique_slug(p.stem, p, taken)
            out.append({
                "spec": {"source_id": slug, "path": str(p), "slug": slug,
                         "path_sha6": sha6, "shape": SHAPE, "format": "csv"},
                "shape": SHAPE,
                "meta": {"layout": layout, **info},
            })
        except Exception:
            # one unreadable candidate must not break discovery for every shape
            continue
    return out


# ────────────────────────────── extract (I9) ──────────────────────────────

def _baseline_profile(matrix, ts_list, cfg):
    """(per-position median template, basis) — in_control_window if declared and
    holding >= 3 snapshots, else the first max(3, ceil(20%)) snapshots."""
    n = matrix.shape[0]
    rows_idx, basis = None, "first_20pct"
    win = (cfg or {}).get("in_control_window")
    if isinstance(win, dict):
        s = ting.parse_ts(win.get("start"))
        e = ting.parse_ts(win.get("end"))
        if s is not None and e is not None and s.ts is not None and e.ts is not None:
            idx = [i for i, t in enumerate(ts_list) if s.ts <= t <= e.ts]
            if len(idx) >= BASELINE_MIN_SNAPSHOTS:
                rows_idx, basis = idx, "in_control_window"
    if rows_idx is None:
        k0 = max(BASELINE_MIN_SNAPSHOTS, int(math.ceil(BASELINE_FRACTION * n)))
        rows_idx = list(range(min(k0, n)))
    sub = matrix[rows_idx]
    base = np.full(matrix.shape[1], np.nan)
    for j in range(sub.shape[1]):
        v = rb.finite(sub[:, j])
        if v.size:
            base[j] = float(np.median(v))
    return base, basis


def _infer_unit(df):
    for c in df.columns:
        if str(c).strip().lower() in ("单位", "unit"):
            v = df[c].dropna()
            if len(v):
                return str(v.iloc[0])[:16]
    return None


def _pivot_long(df, info, ok_idx, parsed):
    """Long 时间,位置,值 -> (matrix, ts_list, dropped_note)."""
    tcol, pos_col, val_col = info["time_col"], info["pos_col"], info["val_col"]
    ts = [parsed[i].ts for i in ok_idx]
    sub = df.iloc[ok_idx]
    pos = pd.to_numeric(sub[pos_col], errors="coerce")
    val = pd.to_numeric(sub[val_col], errors="coerce")
    frame = pd.DataFrame({"ts": ts, "pos": pos.to_numpy(), "val": val.to_numpy()})
    bad_pos = int(frame["pos"].isna().sum())
    frame = frame[frame["pos"].notna()]
    g = frame.groupby(["ts", "pos"], sort=True)["val"].mean().unstack()  # duplicates -> mean
    matrix = g.to_numpy(dtype=float)
    ts_sorted = list(g.index)
    note = f"dropped {bad_pos} row(s) with non-numeric position label" if bad_pos else ""
    return matrix, ts_sorted, note


def _unfold_wide(df, info, ok_idx, parsed):
    """Wide 时间,pos_01..pos_N -> (matrix, ts_list, dropped_note). Duplicated
    snapshot timestamps are aggregated by per-position mean (policy 'aggregate')."""
    tcol, pos_cols = info["time_col"], info["pos_cols"]
    ts = [parsed[i].ts for i in ok_idx]
    sub = df.iloc[ok_idx]
    vals = sub[pos_cols].apply(lambda s: pd.to_numeric(s, errors="coerce")).to_numpy(dtype=float)
    frame = pd.DataFrame(vals, index=pd.Index(ts, name="ts"))
    g = frame.groupby(level=0, sort=True).mean()
    matrix = g.to_numpy(dtype=float)
    ts_sorted = list(g.index)
    return matrix, ts_sorted, ""


def _skip(base, path, reason):
    return {"source": {**base, "n_snapshots": 0, "cadence_s": None, "span_s": None,
                       "ts_format": None, "ts_source": "dcs", "tz": None,
                       "duplicate_key_policy": "aggregate", "disposition": "skipped",
                       "reason": reason, "features": [], "objects_dir": None},
            "rows": None, "contract": [], "annotations": [], "objects": []}


def extract(spec, ctx):
    path = Path(spec.get("path", ""))
    slug = spec.get("slug") or naming.slugify(path.stem)
    sid = spec.get("source_id") or slug
    sha6 = spec.get("path_sha6") or naming.path_sha6(path)
    base = {"source_id": sid, "path": str(path), "slug": slug,
            "path_sha6": sha6, "shape": SHAPE, "format": "csv"}

    if not path.exists():
        return _skip(base, path, "source file missing at extract time")
    sha = mani.sha256_file(path)
    if not sha:
        return _skip(base, path, "source file unreadable")
    df = _read_table(path)
    if df is None or df.empty or df.shape[0] < 3:
        return _skip(base, path, "unreadable as a table or fewer than 3 data rows")
    layout, info = _identify(df)
    if layout is None:
        return _skip(base, path, f"layout is not a profile on full read ({info})")

    # full time parse with OUR parser (R4: never pandas to_datetime guessing)
    tres = ting.parse_series(df[info["time_col"]].tolist())
    if tres["ambiguous"] > 0:
        return _skip(base, path, (f"ambiguous_date_order on {tres['ambiguous']} value(s); "
                                  "day/month order refused, not guessed (plan §4)"))
    ok_idx = [i for i, pv in enumerate(tres["parsed"]) if pv.ts is not None]
    dropped_ts = df.shape[0] - len(ok_idx)
    if len(ok_idx) < 3:
        return _skip(base, path, "fewer than 3 parseable timestamps")

    if layout == "long":
        matrix, ts_sorted, note = _pivot_long(df, info, ok_idx, tres["parsed"])
    else:
        matrix, ts_sorted, note = _unfold_wide(df, info, ok_idx, tres["parsed"])
    if matrix.size == 0 or matrix.shape[1] == 0:
        return _skip(base, path, "no numeric position values survived parsing")

    # drop all-NaN snapshots (nothing measurable), then re-check the >=3 gate
    keep = [r for r in range(matrix.shape[0]) if rb.n_finite(matrix[r]) > 0]
    dropped_empty = matrix.shape[0] - len(keep)
    if len(keep) < 3:
        return _skip(base, path, "fewer than 3 measurable snapshots after timestamp aggregation")
    matrix = matrix[keep]
    ts_sorted = [ts_sorted[r] for r in keep]
    n_snap, n_pos = matrix.shape

    gaps = [(b - a).total_seconds() for a, b in zip(ts_sorted, ts_sorted[1:]) if b > a]
    cadence = float(sorted(gaps)[len(gaps) // 2]) if gaps else None
    span = float((ts_sorted[-1] - ts_sorted[0]).total_seconds()) if n_snap > 1 else 0.0

    baseline, basis = _baseline_profile(matrix, ts_sorted, getattr(ctx, "config", None) or {})
    shift_possible = n_snap >= BASELINE_MIN_SNAPSHOTS
    finite_base = np.isfinite(baseline)

    feat_vals = {f: [] for f in FEATURE_ORDER}
    n_in_rows = []
    for r in range(n_snap):
        x = matrix[r]
        k = rb.n_finite(x)
        n_in_rows.append(int(k))
        partial = k < PARTIAL_FRACTION * n_pos
        slope, curv = rb.lsq_slope_curv(x, 100.0)
        edges = rb.edge_band_deviation(x)
        zone1 = rb.zone_means(x, 3)[0]
        dev, argi = rb.max_abs_neighbour_deviation(x)
        argdev = float(argi) if argi >= 0 else float("nan")
        # SHIFT only when the row's missing-position pattern matches the baseline's:
        # the frozen cross-correlation compares position-paired finite values, so
        # misaligned NaN patterns would be paired wrongly (不足即 NaN, never guess).
        aligned = bool((np.isfinite(x) == finite_base).all())
        if shift_possible and k >= 3 and not partial and aligned:
            shift = float(rb.cross_correlation_shift(x, baseline))
        else:
            shift = float("nan")
        if partial:  # plan §3.1: incomplete profile => keep amplitude, drop shape
            slope = curv = zone1 = float("nan")
            edges["edge_l"] = edges["edge_r"] = float("nan")
            shift = float("nan")
        vals = [rb.mean(x), rb.std(x), rb.vmin(x), rb.vmax(x),
                rb.pctl(x, 5), rb.pctl(x, 50), rb.pctl(x, 95),
                rb.vmax(x) - rb.vmin(x), rb.iqr(x), rb.mad(x), float(k),
                slope, curv, zone1,
                edges["edge_l"], edges["edge_r"], argdev, shift]
        for f, v in zip(FEATURE_ORDER, vals):
            feat_vals[f].append(v)

    # rows: ts,_src_ts,n_inputs,pos_01..pos_N,<derived>   (frozen I4)
    ts_str = [t.strftime("%Y-%m-%d %H:%M:%S") for t in ts_sorted]
    data = {"ts": ts_str, "_src_ts": ts_str,
            "n_inputs": np.asarray(n_in_rows, dtype=np.int64)}
    for j in range(n_pos):
        data[f"pos_{j + 1:02d}"] = matrix[:, j].astype(float)
    feature_cols = []
    for f in FEATURE_ORDER:
        col = naming.feature_column("profile", slug, f)
        feature_cols.append(col)
        data[col] = np.asarray(feat_vals[f], dtype=float)
    rows = pd.DataFrame(data)

    # contracts: one per derived feature column (I5, all fields)
    unit_src = _infer_unit(df)
    n_in_contract = max(1, int(round(float(np.median(n_in_rows)))))
    contract = []
    for f in FEATURE_ORDER:
        arr = np.asarray(feat_vals[f], dtype=float)
        n_ok = int(np.isfinite(arr).sum())
        coverage = n_ok / n_snap
        m = FEATURE_META[f]
        unit = None
        if m["unit_kind"] == "source":
            unit = unit_src
        contract.append({
            "column": naming.feature_column("profile", slug, f),
            "shape": "PROF",
            "source_id": sid,
            "source_path": str(path),
            "source_sha256": sha,
            "unit": unit,
            "role": "target_candidate",
            "physical_meaning": m["meaning"],
            "formula": m["formula"],
            "physics_basis": m["physics"],
            "evidence_level": 1,
            "evidence_level_basis": _L1_BASIS,
            "method": m["method"],
            "method_version": CONTRACT_VERSION,
            "n_inputs": n_in_contract,
            "coverage": coverage,
            "effective_n": n_ok,
            "sparse": coverage < 0.3,
            # honest pre-align default: I8 stats_eligible needs ANCHOR coverage,
            # which only the align layer (WS5) knows; it rewrites this field.
            "stats_eligible": False,
            "cadence_s": cadence,
            "ts_source": "dcs",
            "tz": None,
            "clock_offset_s": 0.0,
            "tag_cn": m["tag_cn"],
            "tag_en": m["tag_en"],
            "model_derived": False,
            "_src_ts": "ts",
            "insufficient_data": n_ok == 0,
        })

    notes = []
    if dropped_ts:
        notes.append(f"dropped {dropped_ts} row(s) with unparseable/empty timestamps")
    if note:
        notes.append(note)
    if dropped_empty:
        notes.append(f"dropped {dropped_empty} all-NaN snapshot(s)")
    notes.append(f"shift_baseline={basis}")

    src = {**base,
           "n_snapshots": int(n_snap),
           "cadence_s": cadence,
           "span_s": span,
           "ts_format": tres["format"],
           "ts_source": "dcs",
           "tz": None,
           "duplicate_key_policy": "aggregate",
           "disposition": "featured",
           "reason": "; ".join(notes),
           "features": feature_cols,
           "objects_dir": None,
           "effective_n": int(n_snap),
           "sparse": False}
    return {"source": src, "rows": rows, "contract": contract,
            "annotations": [], "objects": []}
