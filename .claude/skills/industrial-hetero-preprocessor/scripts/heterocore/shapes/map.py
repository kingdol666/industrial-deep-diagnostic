"""map.py — MAP shape (WS3): regular-grid 2-D field snapshots (frozen interface I9).

Scope (plan v1.1 §3.1 MAP row, M1):
  long-format CSV  ``<time>, <x>, <y>, <value>``  whose distinct (x, y) pairs
  cover the coordinate lattice with ``pairs/(nx*ny) >= 0.6`` (regular grid).
  A 2-D raster is pivoted per timestamp (missing cells stay NaN — no
  interpolation, no filling, plan D9) and folded into a handful of named
  per-snapshot features: MEAN P95 HOTAREA-P90 COLDAREA-P10 CENTROID-X/Y
  GRAD-P95 ASYM-LR POSMAX-X/Y N (formulas frozen in references/method_notes.md
  §1 — that file, not this code, is the authority).

Scatter deferral: a long x/y/value CSV that does NOT qualify as a regular grid
(coverage < 0.6, or an axis outside 4..400) is still *registered*
(meta scatter=true in the spec) but ``extract`` returns
``disposition="insufficient_data"`` with no feature columns, its reason naming
the criterion that failed — irregular point clouds (NPTS/BBOX/HULL/NN-MED) are
M3 scope.

Detection gates (cheap, metadata-first; full table never parsed at detect):
  time column present + >=3 numeric columns (x, y, value distinct)
  + >=30 coordinate-finite rows; grid additionally needs
  unique(x)>=4, unique(y)>=4, 4<=nx,ny<=400 and coverage>=0.6.

Independence note (decision D10): the coverage>=0.6 grid test is the same
*idea* as `industrial-data-processor/scripts/adaptive_charts.py
:detect_2d_field`, but this module deliberately does NOT import it —
everything here is self-contained so the E-1H skill never couples to the
data-processor's code.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]  # .../scripts
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from heterocore import CONTRACT_VERSION  # noqa: E402
from heterocore import manifest as mani  # noqa: E402
from heterocore import naming  # noqa: E402
from heterocore import robust  # noqa: E402
from heterocore import time_ingest as ting  # noqa: E402

SHAPE = "map"
FORMAT_GRID = "long_grid"
FORMAT_SCATTER = "long_scatter"
METHOD = "map.snapshot_features (per-ts pivot to raster; median+3*rawMAD robust thresholds; numpy.diff gradient; no interpolation)"

GRID_COVERAGE_MIN = 0.6     # pairs/(nx*ny) needed to call it a regular grid
GRID_AXIS_MIN = 4           # unique(x) >= 4 and unique(y) >= 4
GRID_AXIS_MAX = 400         # a 2-D field lattice, not two continuous channels
MIN_ROWS = 30               # minimum coordinate-finite rows for any claim
MIN_SNAPSHOTS = 6           # fewer time snapshots -> insufficient_data
MIN_FINITE_CELLS = 30       # legacy absolute floor for large grids
MIN_FINITE_FLOOR = 10       # small grids (e.g. 5x4=20 cells) use a relative floor
MIN_PARSE_RATE = 0.9        # time parse rate below this -> skip the source
DETECT_SAMPLE_ROWS = 200
MAX_DETECT_NUMERIC_COLS = 8
MAX_PAIR_PASSES = 6         # bounded detection work per file
PAIR_SET_CAP = 200_000      # beyond this a grid cannot be confirmed anyway
_WEIGHT_EPS = 1e-12

TABLE_EXTS = {".csv", ".tsv", ".txt", ".dat"}
TIME_NAME_HINTS = {"时间", "时间戳", "timestamp", "datetime", "time", "ts", "date", "日期", "采集时间", "取样时间"}
_X_AXIS_NAMES = {"x", "xm", "xmm", "xpos", "xpos2", "px", "u", "lon", "longitude", "xi", "xidx", "xindex",
                 "colx", "xcol", "坐标x", "x坐标"}
_Y_AXIS_NAMES = {"y", "ym", "ymm", "ypos", "py", "v2", "lat", "latitude", "yi", "yidx", "yindex",
                 "coly", "ycol", "坐标y", "y坐标"}
GEOM_CAVEAT = "；几何解释依赖坐标系声明（geometric interpretation depends on the declared x/y coordinate frame）"

# (feature, arg, unit_kind, role, tag_cn, tag_en, formula, physics_basis, physical_meaning, geometry)
FEATURE_DEFS = [
    ("MEAN", None, "value", "predictor_candidate", "场均值", "field mean",
     "mean(v) over finite cells of the snapshot raster",
     "direct spatial statistic of the measured field (L1)",
     "快照二维场有限格元的算术均值（场整体幅值水平）", False),
    ("P95", None, "value", "predictor_candidate", "场P95", "field P95",
     "numpy.percentile(v, 95) linear interpolation over finite cells",
     "high-tail field level, robust to single-cell spikes",
     "快照二维场有限格元的第95百分位（高段幅值水平）", False),
    ("HOTAREA-P90", None, "ratio", "predictor_candidate", "过热区占比", "hot-area fraction",
     "count(v > median(v)+3*MAD(v)) / count(v); MAD = median(|v-median(v)|), raw (no 1.4826 factor)",
     "robust median+3MAD exceedance share; insensitive to non-Gaussian field tails (method_notes §1)",
     "过热像元占比：值大于快照中位数+3倍MAD的有限格元比例（局部过热面积指标）", True),
    ("COLDAREA-P10", None, "ratio", "predictor_candidate", "过冷区占比", "cold-area fraction",
     "count(v < median(v)-3*MAD(v)) / count(v)",
     "robust median-3MAD shortfall share (mirror of HOTAREA-P90)",
     "过冷像元占比：值小于快照中位数-3倍MAD的有限格元比例（局部过冷面积指标）", True),
    ("CENTROID", "X", "xy", "predictor_candidate", "值加权质心X", "value-weighted centroid X",
     "sum(v*x) / sum(v) over finite cells",
     "first spatial moment of the field (value centroid)",
     "以值为权的场质心横坐标（场分布重心的水平位置）", True),
    ("CENTROID", "Y", "xy", "predictor_candidate", "值加权质心Y", "value-weighted centroid Y",
     "sum(v*y) / sum(v) over finite cells",
     "first spatial moment of the field (value centroid)",
     "以值为权的场质心纵坐标（场分布重心的纵向位置）", True),
    ("GRAD-P95", None, "value_per_cell", "predictor_candidate", "梯度幅值P95", "gradient magnitude P95",
     "P95 over interior cells of hypot(diff(F,axis=1)/dx, diff(F,axis=0)/dy); dx,dy = median grid spacing",
     "first-order numpy-difference gradient; P95 keeps it robust to single-cell noise (method_notes §1)",
     "空间梯度幅值的第95百分位除以格间距（场内变化最剧烈部分的强度）", False),
    ("ASYM-LR", None, "value", "predictor_candidate", "左右均差", "left-minus-right mean difference",
     "mean(left half of columns) - mean(right half of columns); middle column excluded when nx is odd",
     "zeroth-order left/right half-field comparison",
     "左右不对称度：左半列有限格均值减右半列有限格均值（场的水平偏置）", True),
    ("POSMAX", "X", "xy", "predictor_candidate", "最大值格X", "argmax cell X",
     "x coordinate of the maximum finite cell (row-major first on ties)",
     "argmax location of the measured field",
     "场最大有限值所在格的x坐标（峰值定位）", True),
    ("POSMAX", "Y", "xy", "predictor_candidate", "最大值格Y", "argmax cell Y",
     "y coordinate of the maximum finite cell (row-major first on ties)",
     "argmax location of the measured field",
     "场最大有限值所在格的y坐标（峰值定位）", True),
    ("N", None, "count", "metadata", "有限格数", "finite cell count",
     "count(isfinite(F)) in the snapshot raster",
     "completeness of the pivot grid; missing cells stay NaN and are never interpolated",
     "快照有限格元数（场完整性指标，缺失格恒为NaN，不做任何插值）", False),
]
FEATURE_KEYS = [(f, a) for (f, a, *_rest) in FEATURE_DEFS]


# ────────────────────────── shared ctx plumbing ──────────────────────────

def _config_of(frame) -> dict:
    cfg = getattr(frame, "config", None)
    if cfg is None and isinstance(frame, dict):
        cfg = frame.get("config")
    return cfg if isinstance(cfg, dict) else {}


def _taken_slugs(frame) -> dict:
    taken = getattr(frame, "taken_slugs", None)
    if taken is None and isinstance(frame, dict):
        taken = frame.get("taken_slugs")
    return taken if isinstance(taken, dict) else {}


def _norm_name(col: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", str(col).lower())


# ────────────────────────────── detection ────────────────────────────────

def detect(paths, frame=None):
    """I9 detect: cheap per-file probe -> [{"shape": "map", "spec": {...}}, ...].

    Never raises on a bad file (a broken candidate must not fail the run).
    spec.meta carries the column bindings (time/x/y/value + sep) so extract
    never re-guesses them, plus scatter/nx/ny/pair_coverage/n_rows.
    """
    cfg = _config_of(frame)
    taken = _taken_slugs(frame)
    claims = []
    for p in paths or []:
        try:
            claim = _probe_file(Path(str(p)), cfg, taken)
        except Exception:
            claim = None
        if claim:
            claims.append(claim)
    return claims


def _sniff_sep(path: Path) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        line = fh.readline()
    counts = {",": line.count(","), "\t": line.count("\t"), ";": line.count(";")}
    best = max(counts, key=lambda k: counts[k])
    return best if counts[best] > 0 else ","


def _chunks(path: Path, sep: str, usecols: list[str], chunksize: int = 65536):
    reader = pd.read_csv(path, sep=sep, encoding="utf-8-sig", usecols=usecols, chunksize=chunksize)
    for chunk in reader:
        yield chunk


def _probe_file(path: Path, cfg: dict, taken: dict):
    if not path.is_file() or path.suffix.lower() not in TABLE_EXTS:
        return None
    sep = _sniff_sep(path)
    try:
        sample = pd.read_csv(path, sep=sep, encoding="utf-8-sig", nrows=DETECT_SAMPLE_ROWS)
    except Exception:
        return None
    if sample.shape[0] == 0 or sample.shape[1] < 4:
        return None  # need time + x + y + value as distinct columns
    cols = [str(c) for c in sample.columns]

    t_col = cfg.get("map_time_col")
    if not (isinstance(t_col, str) and t_col in cols):
        t_col = next((c for c in cols if _norm_name(c) in TIME_NAME_HINTS), None)
    if t_col is None:
        for c in cols[:6]:
            if pd.api.types.is_numeric_dtype(sample[c]):
                continue
            if ting.parse_series(sample[c].tolist())["ok_rate"] >= MIN_PARSE_RATE:
                t_col = c
                break
    if t_col is None:
        return None

    num = [c for c in cols if c != t_col and pd.api.types.is_numeric_dtype(sample[c])]
    if len(num) < 3:
        return None
    num = num[:MAX_DETECT_NUMERIC_COLS]

    # coordinate-priority pair: explicit config binding, else x/y-style names
    xp, yp = cfg.get("map_x_col"), cfg.get("map_y_col")
    coord_pair = None
    if (isinstance(xp, str) and isinstance(yp, str) and xp in num and yp in num and xp != yp):
        coord_pair = (xp, yp)
    else:
        xs_c = [c for c in num if _norm_name(c) in _X_AXIS_NAMES]
        ys_c = [c for c in num if _norm_name(c) in _Y_AXIS_NAMES]
        if xs_c and ys_c and xs_c[0] != ys_c[0]:
            coord_pair = (xs_c[0], ys_c[0])

    # one bounded pass for per-column cardinality -> grid-likelihood pair order
    card: dict[str, set] = {c: set() for c in num}
    for chunk in _chunks(path, sep, num):
        for c in num:
            vals = pd.to_numeric(chunk[c], errors="coerce").to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            s = card[c]
            if len(s) <= GRID_AXIS_MAX:
                s.update(vals.tolist())

    ordered = sorted(range(len(num)), key=lambda i: (len(card[num[i]]), i))
    eval_pairs: list[tuple[str, str]] = []
    if coord_pair:
        eval_pairs.append(coord_pair)
    for a in range(len(ordered)):
        for b in range(a + 1, len(ordered)):
            pr = (num[ordered[a]], num[ordered[b]])
            if pr not in eval_pairs:
                eval_pairs.append(pr)
    eval_pairs = eval_pairs[:MAX_PAIR_PASSES]

    grid_hit = None
    coord_stats = None
    for xc, yc in eval_pairs:
        st = _pair_stats(path, sep, xc, yc)
        if coord_pair and (xc, yc) == coord_pair:
            coord_stats = st
        if _is_grid(st):
            grid_hit = (xc, yc, st)
            break

    if grid_hit:
        xc, yc, st = grid_hit
        scatter = False
        pair_coverage, nx, ny, n_rows = st["coverage"], st["nx"], st["ny"], st["n_rows"]
    elif coord_stats is not None and coord_stats["n_rows"] >= MIN_ROWS \
            and coord_stats["nx"] >= 2 and coord_stats["ny"] >= 2:
        # registered only: irregular point cloud, features are M3 scope
        xc, yc = coord_pair
        scatter = True
        pair_coverage, nx, ny, n_rows = (coord_stats["coverage"], coord_stats["nx"],
                                         coord_stats["ny"], coord_stats["n_rows"])
    else:
        return None

    axis = {t_col, xc, yc}
    value_col = next((c for c in num if c not in axis), None)
    if value_col is None:
        return None
    extra = [c for c in num if c not in axis and c != value_col][:4]

    slug, sha6 = naming.unique_slug(path.stem, path, taken)
    spec = {
        "source_id": path.name,
        "path": str(path),
        "slug": slug,
        "path_sha6": sha6,
        "kind": "csv",
        "shape": SHAPE,
        "meta": {
            "time_col": t_col, "x_col": xc, "y_col": yc, "value_col": value_col,
            "extra_value_cols": extra, "sep": sep,
            "scatter": scatter, "pair_coverage": pair_coverage,
            "nx": int(nx), "ny": int(ny), "n_rows": int(n_rows),
        },
    }
    return {"shape": SHAPE, "spec": spec}


def _pair_stats(path: Path, sep: str, x_col: str, y_col: str) -> dict:
    ux: set = set()
    uy: set = set()
    pairs: set = set()
    n_rows = 0
    capped = False
    for chunk in _chunks(path, sep, [x_col, y_col]):
        x = pd.to_numeric(chunk[x_col], errors="coerce").to_numpy(dtype=float)
        y = pd.to_numeric(chunk[y_col], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        x, y = x[ok], y[ok]
        n_rows += int(ok.sum())
        if len(ux) <= GRID_AXIS_MAX:
            ux.update(x.tolist())
        if len(uy) <= GRID_AXIS_MAX:
            uy.update(y.tolist())
        if not capped:
            pairs.update(zip(x.tolist(), y.tolist()))
            if len(pairs) > PAIR_SET_CAP:
                capped = True
    nx, ny = len(ux), len(uy)
    cov = (len(pairs) / float(nx * ny)) if (nx and ny and not capped) else 0.0
    return {"n_rows": n_rows, "nx": nx, "ny": ny, "n_pairs": len(pairs), "coverage": cov, "capped": capped}


def _is_grid(st: dict) -> bool:
    return (not st["capped"]
            and GRID_AXIS_MIN <= st["nx"] <= GRID_AXIS_MAX
            and GRID_AXIS_MIN <= st["ny"] <= GRID_AXIS_MAX
            and st["n_rows"] >= MIN_ROWS
            and st["coverage"] >= GRID_COVERAGE_MIN)


# ────────────────────────────── extraction ───────────────────────────────

def snapshot_matrix(sub: pd.DataFrame, y_order, x_order) -> np.ndarray:
    """Pivot one time snapshot to a raster (rows=y, cols=x).

    Missing cells stay NaN. This is the whole story: pivot + reindex only —
    no interpolation, no fill, ever (plan D9 / H6b discipline).
    """
    piv = sub.pivot_table(index="y", columns="x", values="v", aggfunc="mean")
    piv = piv.reindex(index=list(y_order), columns=list(x_order))
    return piv.to_numpy(dtype=float)


def snapshot_features(mat: np.ndarray, xs, ys) -> dict:
    """Deterministic per-snapshot features (method_notes §1). Returns NaN
    features (except N) when fewer than the relative finite floor
    max(MIN_FINITE_FLOOR, 50% of the grid) is reached; GRAD-P95 additionally
    requires the legacy absolute MIN_FINITE_CELLS (gradients on tiny grids
    are noise-dominated)."""
    out = {"N": float("nan")}
    for feat, arg in FEATURE_KEYS:
        out[_key(feat, arg)] = float("nan")
    m = np.isfinite(mat)
    n = int(m.sum())
    out["N"] = float(n)
    floor = max(MIN_FINITE_FLOOR, int(0.5 * mat.size))
    if n < floor:
        return out
    v = mat[m]
    out["MEAN"] = robust.mean(v)
    out["P95"] = robust.pctl(v, 95)
    med = robust.median(v)
    mad = robust.mad(v)
    if np.isfinite(med) and np.isfinite(mad):
        out["HOTAREA-P90"] = float(np.mean(v > med + 3.0 * mad))
        out["COLDAREA-P10"] = float(np.mean(v < med - 3.0 * mad))
    xg, yg = np.meshgrid(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    tot = float(np.sum(v))
    if np.isfinite(tot) and abs(tot) > _WEIGHT_EPS:
        out["CENTROID-X"] = float(np.sum(v * xg[m]) / tot)
        out["CENTROID-Y"] = float(np.sum(v * yg[m]) / tot)
    nx_, ny_ = mat.shape[1], mat.shape[0]
    zz = np.where(m, mat, -np.inf)
    k = int(np.argmax(zz))
    if np.isfinite(zz.flat[k]):
        out["POSMAX-X"] = float(xs[k % nx_])
        out["POSMAX-Y"] = float(ys[k // nx_])
    if nx_ >= 2 and ny_ >= 2 and n >= MIN_FINITE_CELLS:
        # gradient on tiny/under-filled grids is noise-dominated: keep the
        # legacy absolute floor for GRAD-P95 only (other features use the
        # relative floor decided by the caller)
        dx = float(np.median(np.diff(np.asarray(xs, dtype=float))))
        dy = float(np.median(np.diff(np.asarray(ys, dtype=float))))
        if np.isfinite(dx) and dx > 0 and np.isfinite(dy) and dy > 0:
            gx = np.diff(mat, axis=1) / dx
            gy = np.diff(mat, axis=0) / dy
            mag = np.hypot(gx[:-1, :], gy[:, :-1])
            if np.isfinite(mag).any():
                out["GRAD-P95"] = robust.pctl(mag[np.isfinite(mag)], 95)
    half = nx_ // 2
    if half >= 1:
        lm = robust.mean(mat[:, :half][m[:, :half]])
        rm = robust.mean(mat[:, nx_ - half:][m[:, nx_ - half:]])
        out["ASYM-LR"] = float(lm) - float(rm) if np.isfinite(lm) and np.isfinite(rm) else float("nan")
    return out


def _key(feat: str, arg) -> str:
    return f"{feat}-{arg}" if arg else feat


def extract(spec, ctx=None):
    """I9 extract: SourceSpec -> ShapeResult{source, rows, contract, annotations, objects}."""
    path = Path(str(spec.get("path", "")))
    meta = dict(spec.get("meta") or {})
    sid = str(spec.get("source_id") or path.name)
    slug = str(spec.get("slug") or naming.slugify(path.stem))
    cfg = _config_of(ctx)
    sep = str(meta.get("sep") or ",")
    sha = mani.sha256_file(path) or "sha256:unavailable"

    src = {
        "source_id": sid,
        "path": str(path),
        "path_sha6": str(spec.get("path_sha6") or naming.path_sha6(path)),
        "slug": slug,
        "shape": SHAPE,
        "ts_source": "dcs",
        "duplicate_key_policy": "aggregate",
        "sparse": True,
        "stats_eligible": False,
        "features": [],
        "objects_dir": None,
        "disposition": "skipped",
        "reason": "",
    }
    empty = {"source": src, "rows": None, "contract": [], "annotations": [], "objects": []}

    if meta.get("scatter"):
        nx_, ny_ = int(meta.get("nx") or 0), int(meta.get("ny") or 0)
        cov_ = float(meta.get("pair_coverage") or 0.0)
        src["format"] = FORMAT_SCATTER
        src["disposition"] = "insufficient_data"
        src["effective_n"] = 0
        # report the criterion that actually rejected the source: a mostly-empty
        # lattice is an irregular cloud; a sufficiently-covered lattice outside
        # the 4..400 axis bounds is a size problem, not a coverage one
        if cov_ < GRID_COVERAGE_MIN:
            src["reason"] = (
                "scatter field: pairs/(nx*ny)=%.3f below the %.2f grid-coverage minimum over %dx%d "
                "distinct coordinates; irregular 2-D point cloud — registered only, "
                "per-snapshot rasters and features are M3 scope"
                % (cov_, GRID_COVERAGE_MIN, nx_, ny_))
        elif nx_ < GRID_AXIS_MIN or ny_ < GRID_AXIS_MIN:
            src["reason"] = (
                "lattice %dx%d below the %dx%d minimum field size; registered only — "
                "no per-snapshot rasters or features emitted"
                % (nx_, ny_, GRID_AXIS_MIN, GRID_AXIS_MIN))
        else:
            src["reason"] = (
                "lattice %dx%d exceeds the %d-per-axis maximum for field treatment; "
                "registered only — no per-snapshot rasters or features emitted"
                % (nx_, ny_, GRID_AXIS_MAX))
        return empty

    cols = [meta.get(k) for k in ("time_col", "x_col", "y_col", "value_col")]
    if not all(isinstance(c, str) and c for c in cols):
        src["reason"] = "map spec missing time/x/y/value column bindings"
        return empty
    t_col, x_col, y_col, v_col = cols

    try:
        df = pd.read_csv(path, sep=sep, encoding="utf-8-sig", usecols=cols)
    except Exception:
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
        except Exception as exc:
            src["reason"] = f"unreadable source: {exc}"
            return empty
    missing = [c for c in cols if c not in df.columns]
    if missing:
        src["reason"] = f"declared columns absent in file: {missing}"
        return empty

    parsed = ting.parse_series(df[t_col].tolist())
    if parsed["ok_rate"] < MIN_PARSE_RATE or parsed["ambiguous"] > 0:
        src["disposition"] = "skipped"
        src["n_snapshots"] = 0
        src["reason"] = ("time parse rate %.3f (<%.2f) and/or %d ambiguous-date stamps; "
                         "source refused instead of guessing (plan §7)"
                         % (parsed["ok_rate"], MIN_PARSE_RATE, parsed["ambiguous"]))
        return empty

    ts_all = [p.ts for p in parsed["parsed"]]
    x = pd.to_numeric(df[x_col], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(df[y_col], errors="coerce").to_numpy(dtype=float)
    v = pd.to_numeric(df[v_col], errors="coerce").to_numpy(dtype=float)
    ok = np.array([t is not None for t in ts_all]) & np.isfinite(x) & np.isfinite(y) & np.isfinite(v)
    idx = np.where(ok)[0]
    frame = pd.DataFrame({"ts": [ts_all[i] for i in idx],
                          "x": x[idx], "y": y[idx], "v": v[idx]})

    groups = {k: g for k, g in frame.groupby("ts", sort=True)}
    stamps = sorted(groups)
    if len(stamps) < MIN_SNAPSHOTS:
        src["format"] = FORMAT_GRID
        src["n_snapshots"] = int(len(stamps))
        src["disposition"] = "insufficient_data"
        src["effective_n"] = 0
        src["reason"] = ("only %d time snapshots with finite (time,x,y,value) rows (<%d); "
                         "no per-snapshot raster statistics emitted" % (len(stamps), MIN_SNAPSHOTS))
        return empty

    x_order = sorted(float(q) for q in frame["x"].unique())
    y_order = sorted(float(q) for q in frame["y"].unique())
    if len(x_order) < 2 or len(y_order) < 2:
        src["format"] = FORMAT_GRID
        src["n_snapshots"] = int(len(stamps))
        src["disposition"] = "insufficient_data"
        src["effective_n"] = 0
        src["reason"] = "degenerate field: fewer than 2 distinct x or y coordinates"
        return empty

    dup_cells = 0
    snap_feats = []
    for t in stamps:
        sub = groups[t]
        dup_cells += int(len(sub) - len(sub.drop_duplicates(subset=["x", "y"])))
        mat = snapshot_matrix(sub, y_order, x_order)
        snap_feats.append(snapshot_features(mat, x_order, y_order))
    # relative floor: small grids (5x4=20 cells) are legitimate maps; a
    # snapshot counts as computable when it has >= max(10, 50% of its cells)
    grid_floor = max(MIN_FINITE_FLOOR, int(0.5 * len(y_order) * len(x_order)))
    computed = [f["N"] >= grid_floor for f in snap_feats]
    n_feat = int(sum(computed))
    if n_feat == 0:
        src["format"] = FORMAT_GRID
        src["n_snapshots"] = int(len(stamps))
        src["disposition"] = "insufficient_data"
        src["effective_n"] = 0
        src["reason"] = ("no snapshot reached %d finite cells (grid %dx%d); nothing featured, nothing interpolated"
                         % (grid_floor, len(x_order), len(y_order)))
        return empty

    coverage = n_feat / float(len(stamps))
    total_cells = int(sum(snap_feats[i]["N"] for i in range(len(stamps)) if computed[i]))

    # ---- feature rows (I4: ts, _src_ts, n_inputs, <derived>) ----------------
    colnames = {(feat, arg): naming.feature_column(SHAPE, slug, feat, arg) for (feat, arg) in FEATURE_KEYS}
    rows_data = {"ts": [], "_src_ts": [], "n_inputs": []}
    for key in colnames:
        rows_data[colnames[key]] = []
    for i, t in enumerate(stamps):
        iso = _iso(t)
        rows_data["ts"].append(iso)
        rows_data["_src_ts"].append(iso)  # native cadence: source stamp == feature stamp (H3: <=)
        rows_data["n_inputs"].append(int(snap_feats[i]["N"]) if computed[i] else 0)
        for (feat, arg) in FEATURE_KEYS:
            name = colnames[(feat, arg)]
            rows_data[name].append(float(snap_feats[i][_key(feat, arg)]) if computed[i] else float("nan"))
    rows = pd.DataFrame(rows_data)

    # ---- column contract (I5, all fields) -----------------------------------
    bs = ting.bucket_stats(parsed["parsed"])
    tz_orig = sorted(parsed["tz_originals"])
    tz = tz_orig[0] if len(tz_orig) == 1 else ("|".join(tz_orig) if tz_orig else None)
    lag_map = cfg.get("transport_lag_s") if isinstance(cfg.get("transport_lag_s"), dict) else {}
    lag = float(lag_map.get(sid, lag_map.get(slug, 0)) or 0)
    value_unit = _value_unit(cfg, v_col)

    contract = []
    for (feat, arg, unit_kind, role, tag_cn, tag_en, formula, basis, meaning, geometry) in FEATURE_DEFS:
        contract.append({
            "column": colnames[(feat, arg)],
            "shape": "MAP",
            "source_id": sid,
            "source_path": str(path),
            "source_sha256": sha,
            "unit": _unit_for(unit_kind, value_unit, cfg),
            "role": role,
            "physical_meaning": meaning + (GEOM_CAVEAT if geometry else ""),
            "formula": formula,
            "physics_basis": basis,
            "evidence_level": 1,
            "evidence_level_basis": ("L1: deterministic statistic of retained source cell values; "
                                     "formula frozen in references/method_notes.md section 1"),
            "method": METHOD,
            "method_version": CONTRACT_VERSION,
            "n_inputs": total_cells,
            "coverage": float(coverage),
            "effective_n": n_feat,
            "sparse": bool(coverage < 0.3),
            "stats_eligible": False,  # anchor-coverage gated (I8); align layer flips it
            "cadence_s": bs["cadence_s"],
            "ts_source": "dcs",
            "tz": tz,
            "clock_offset_s": lag,
            "tag_cn": tag_cn,
            "tag_en": tag_en,
            "model_derived": False,
            "_src_ts": "ts",
            "insufficient_data": False,
            "first_ts": _iso(stamps[0]),
            "last_ts": _iso(stamps[-1]),
        })

    # ---- manifest source block (I6-legal keys only) --------------------------
    src["format"] = FORMAT_GRID
    src["n_snapshots"] = int(len(stamps))
    src["cadence_s"] = bs["cadence_s"]
    src["span_s"] = bs["span_s"]
    src["ts_format"] = parsed["format"]
    src["tz"] = tz
    src["anchor_coverage"] = None
    src["effective_n"] = n_feat
    src["sparse"] = bool(coverage < 0.3)
    src["disposition"] = "featured"
    src["features"] = [colnames[k] for k in FEATURE_KEYS]
    notes = []
    n_insuff = len(stamps) - n_feat
    if n_insuff:
        notes.append("%d/%d snapshots below %d finite cells -> features NaN (no interpolation)"
                     % (n_insuff, len(stamps), grid_floor))
    if dup_cells:
        notes.append("duplicate (ts,x,y) cells aggregated by mean (count=%d)" % dup_cells)
    src["reason"] = "; ".join(notes)

    return {"source": src, "rows": rows, "contract": contract, "annotations": [], "objects": []}


# ────────────────────────────── helpers ──────────────────────────────────

def _iso(t) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S")


def _value_unit(cfg: dict, v_col: str):
    units = cfg.get("units")
    if isinstance(units, dict) and isinstance(units.get(v_col), str):
        return units[v_col]
    u = cfg.get("map_value_unit")
    return u if isinstance(u, str) else None


def _unit_for(kind: str, value_unit, cfg: dict):
    if kind == "value":
        return value_unit
    if kind == "ratio":
        return "ratio"
    if kind == "count":
        return "count"
    if kind == "xy":
        u = cfg.get("map_xy_unit")
        return u if isinstance(u, str) else None
    if kind == "value_per_cell":
        return f"{value_unit}/cell" if value_unit else None
    return None
