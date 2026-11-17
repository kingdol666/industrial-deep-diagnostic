"""test_p3.py — WS3 MAP (regular-grid 2-D field) acceptance cases.

Fixtures are generated on the fly with a fixed seed (run_tests.py contract;
nothing is committed). Cases:

  p3-grid-hotspot    40 snapshots of a 20x20 grid (baseline 50 + bounded noise 1);
                     from t*=50% a Gaussian hotspot (sigma=8 cells, +15%) is
                     injected at a fixed position. Asserts the post-change-point
                     HOTAREA-P90 rise, the CENTROID-X/Y shift toward the hotspot
                     (<=5 cells) and POSMAX-X/Y within +/-2 cells of it.
  p3-grid-negative   same generator WITHOUT the hotspot -> HOTAREA ~0 (<0.005).
  p3-scatter         random (non-grid) x/y -> registered only:
                     disposition=insufficient_data, no feature columns.
  p3-missing-cells   20% of cells punched out -> features still computed,
                     N tracks the finite cells, and NO interpolation happens
                     (a punched cell is NaN in the raster; a retained cell keeps
                     its exact original value).
  p3-build-e2e       build.py + quality_gate.mjs on a mixed raw folder
                     (grid + scatter) -> status ok, MAP features file, contract,
                     manifest source meta, gate exit 0.

Noise-model note (why uniform): method_notes §1 fixes MAD as the RAW median
absolute deviation (no 1.4826 factor), so the HOTAREA threshold is
median + 3*0.6745*sigma for Gaussian noise, which pure Gaussian noise exceeds
~2.2% of the time — the required "<0.005" negative bound would be impossible
by construction. Bounded uniform noise "1" (amplitude 1, U(-1,1)) has raw MAD
0.5, so median+3*MAD = 1.5 >= max|deviation| = 1.0 and the negative case is
exactly 0 by construction, deterministically.

Hotspot placement note: sigma=8 cells on a 20x20 grid is broader than the
field, so the hotspot is anchored at (x=2, y=3) — most of the field stays near
baseline, the value distribution keeps its baseline anchor, and the per-
snapshot median+3*MAD threshold fires on the hot zone (verified numerically:
post-change HOTAREA >= 0.03 on every post snapshot).
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent          # tests/cases
SKILL = HERE.parent.parent                      # skill root
SCRIPTS = SKILL / "scripts"
REPO = SCRIPTS.parent.parent.parent.parent
SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "Scripts" / "python.exe"
if not SHARED_PY.exists():
    SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "bin" / "python"
sys.path.insert(0, str(SCRIPTS))

from heterocore import naming  # noqa: E402

SEED = 20261015
N = 20
T = 40
TSTAR = 20                      # t* = 50%
CX, CY, SIGMA, AMP = 2, 3, 8.0, 7.5   # sigma=8 cells, +15% of baseline 50
BASE_TS = datetime(2026, 10, 15, 8, 0, 0)
CADENCE_S = 60
I5_FIELDS = [
    "column", "shape", "source_id", "source_path", "source_sha256", "unit", "role",
    "physical_meaning", "formula", "physics_basis", "evidence_level", "evidence_level_basis",
    "method", "method_version", "n_inputs", "coverage", "effective_n", "sparse",
    "stats_eligible", "cadence_s", "ts_source", "tz", "clock_offset_s", "tag_cn", "tag_en",
    "model_derived", "_src_ts", "insufficient_data",
]

_MAP_MOD = None


def _map():
    global _MAP_MOD
    if _MAP_MOD is None:
        spec = importlib.util.spec_from_file_location(
            "hetshape_map_under_test", SCRIPTS / "heterocore" / "shapes" / "map.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MAP_MOD = mod
    return _MAP_MOD


class _Ctx:
    """Minimal stand-in for build.py's Ctx (interface I9 frame)."""

    def __init__(self, root: Path):
        self.run_dir = root
        self.raw_path = root
        self.config = {}
        self.seed = SEED
        self.taken_slugs = {}


def _ts(i: int) -> str:
    return (BASE_TS + timedelta(seconds=CADENCE_S * i)).strftime("%Y-%m-%d %H:%M:%S")


def _write_grid_csv(path: Path, hotspot: bool = False, punch: int = 0, seed: int = SEED) -> None:
    """40 x (20x20) long-format grid; optional Gaussian hotspot from t*=50%."""
    rng = np.random.default_rng(seed)
    xs = np.arange(N, dtype=float)
    X, Y = np.meshgrid(xs, xs)
    hot = AMP * np.exp(-((X - CX) ** 2 + (Y - CY) ** 2) / (2.0 * SIGMA ** 2))
    recs = []
    for t in range(T):
        z = 50.0 + rng.uniform(-1.0, 1.0, size=(N, N))
        if hotspot and t >= TSTAR:
            z = z + hot
        drop = {int(i) for i in rng.choice(N * N, size=punch, replace=False)} if punch else set()
        if punch and t == 5:
            drop.add(10 * N + 10)        # force (x=10, y=10) out of snapshot 5
            drop.discard(11 * N + 10)    # keep neighbour (x=10, y=11) exactly
        stamp = _ts(t)
        for iy in range(N):
            for ix in range(N):
                if iy * N + ix in drop:
                    continue
                recs.append((stamp, ix, iy, float(z[iy, ix])))
    pd.DataFrame(recs, columns=["ts", "x", "y", "thick"]).to_csv(path, index=False, encoding="utf-8-sig")


def _write_scatter_csv(path: Path, n_rows: int = 500, seed: int = SEED + 1) -> None:
    rng = np.random.default_rng(seed)
    ts = [_ts(i // 10) for i in range(n_rows)]
    pd.DataFrame({
        "ts": ts,
        "x": rng.uniform(0.0, 19.0, n_rows),
        "y": rng.uniform(0.0, 19.0, n_rows),
        "thick": rng.uniform(45.0, 55.0, n_rows),
    }).to_csv(path, index=False, encoding="utf-8-sig")


def _detect_one(root: Path, csv: Path):
    mod = _map()
    claims = mod.detect([csv], _Ctx(root))
    return mod, claims


def _feature_frame(rows: pd.DataFrame, slug: str) -> pd.DataFrame:
    names = [naming.feature_column("map", slug, f, a) for (f, a) in
             [(feat, arg) for (feat, arg, *_r) in _map().FEATURE_DEFS]]
    return rows[names]


def case_grid_hotspot():
    mod = _map()
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        csv = root / "p3_grid.csv"
        _write_grid_csv(csv, hotspot=True)
        claims = mod.detect([csv], _Ctx(root))
        out.append(("detect claims exactly one source", len(claims) == 1, f"{len(claims)} claims"))
        if len(claims) != 1:
            return out
        spec = claims[0]["spec"]
        meta = spec["meta"]
        out.append(("detected as regular grid (scatter=False)", meta["scatter"] is False, json.dumps(meta)))
        out.append(("grid axes 20x20", meta["nx"] == N and meta["ny"] == N,
                    f"nx={meta['nx']} ny={meta['ny']}"))
        out.append(("grid coverage >= 0.6", meta["pair_coverage"] >= 0.6, f"cov={meta['pair_coverage']:.3f}"))
        res = mod.extract(spec, _Ctx(root))
        src = res["source"]
        rows = res["rows"]
        out.append(("disposition featured", src["disposition"] == "featured", src["reason"]))
        out.append(("source meta shape/format/ts_source",
                    src["shape"] == "map" and src["format"] == "long_grid" and src["ts_source"] == "dcs",
                    f"{src['shape']}/{src['format']}/{src['ts_source']}"))
        out.append(("40 snapshot rows", rows is not None and len(rows) == T,
                    f"{0 if rows is None else len(rows)} rows"))
        if rows is None or len(rows) != T:
            return out
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        ts_vals = rows["ts"].tolist()
        out.append(("ts strictly ascending ISO, non-midnight (H6b), _src_ts == ts",
                    all(ts_vals[i] < ts_vals[i + 1] for i in range(T - 1))
                    and all(iso_re.match(v) for v in ts_vals)
                    and any(not v.endswith("00:00:00") for v in ts_vals)
                    and (rows["ts"] == rows["_src_ts"]).all(),
                    ""))
        out.append(("n_inputs == 400 finite cells per snapshot", (rows["n_inputs"] == N * N).all(),
                    f"min={int(rows['n_inputs'].min())}"))
        slug = spec["slug"]
        feat = _feature_frame(rows, slug)
        out.append(("11 feature columns", feat.shape[1] == 11, f"{feat.shape[1]} cols"))
        pre = feat.iloc[:TSTAR]
        post = feat.iloc[TSTAR:]
        hot_name = naming.feature_column("map", slug, "HOTAREA-P90")
        pre_hot = float(pre[hot_name].max())
        post_hot = post[hot_name].to_numpy(dtype=float)
        out.append(("pre-change HOTAREA < 0.005", pre_hot < 0.005, f"pre_max={pre_hot:.6f}"))
        out.append(("post-change HOTAREA mean >= 0.02", float(np.mean(post_hot)) >= 0.02,
                    f"post_mean={float(np.mean(post_hot)):.4f}"))
        out.append(("post-change HOTAREA > 5x pre (pre=0, all post > 0)", bool((post_hot > 0).all()),
                    f"post_min={float(post_hot.min()):.4f}"))
        cx_name = naming.feature_column("map", slug, "CENTROID", "X")
        cy_name = naming.feature_column("map", slug, "CENTROID", "Y")
        pre_c = np.array([float(pre[cx_name].mean()), float(pre[cy_name].mean())])
        post_c = np.array([float(post[cx_name].mean()), float(post[cy_name].mean())])
        disp = post_c - pre_c
        dist = float(np.hypot(*disp))
        toward = float(np.dot(disp, np.array([CX, CY], dtype=float) - pre_c))
        out.append(("centroid shift toward hotspot <= 5 cells", 0.0 < dist <= 5.0,
                    f"|shift|={dist:.3f} shift={np.round(disp, 3).tolist()}"))
        out.append(("centroid displacement points at the hotspot", toward > 0.0, f"dot={toward:.3f}"))
        px = post[naming.feature_column("map", slug, "POSMAX", "X")].to_numpy(dtype=float)
        py = post[naming.feature_column("map", slug, "POSMAX", "Y")].to_numpy(dtype=float)
        cheb = int(np.max(np.maximum(np.abs(px - CX), np.abs(py - CY))))
        out.append(("POSMAX within +/-2 cells of the hotspot on every post snapshot", cheb <= 2,
                    f"max_chebyshev={cheb}"))
        # contract: 11 columns, I5 complete, evidence L1, geometry caveat present
        contract = res["contract"]
        out.append(("contract has 11 MAP columns", len(contract) == 11, f"{len(contract)}"))
        bad_fields = [c["column"] for c in contract
                      for f in I5_FIELDS if f not in c]
        out.append(("all I5 fields present in every contract row", not bad_fields,
                    f"missing in {sorted(set(bad_fields))[:3]}"))
        out.append(("column names pass the H8 naming regex",
                    all(naming.validate_column_name(c["column"]) for c in contract), ""))
        out.append(("contract shape enum is MAP",
                    all(c["shape"] == "MAP" for c in contract), ""))
        out.append(("evidence_level == 1 (direct measurement)",
                    all(c["evidence_level"] == 1 for c in contract), ""))
        geom_cols = [c for c in contract if naming.is_geometry_feature(c["column"])]
        out.append(("geometry columns carry the coordinate-frame caveat",
                    len(geom_cols) >= 7 and all("坐标系声明" in c["physical_meaning"] for c in geom_cols),
                    f"{len(geom_cols)} geometry columns"))
        units = {c["column"].rsplit("-", 1)[-1]: c["unit"] for c in contract}
        out.append(("units: ratio for HOTAREA, count for N, null for value-unit columns",
                    units["P90"] == "ratio" and units["P10"] == "ratio"
                    and any(c["unit"] == "count" for c in contract if c["column"].endswith("-N"))
                    and next(c["unit"] for c in contract if c["column"].endswith("-MEAN")) is None,
                    json.dumps({k: units[k] for k in ("P90", "P10") })))
    return out


def case_grid_negative():
    mod = _map()
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        csv = root / "p3_grid_neg.csv"
        _write_grid_csv(csv, hotspot=False)
        claims = mod.detect([csv], _Ctx(root))
        out.append(("detect claims the clean grid", len(claims) == 1, f"{len(claims)} claims"))
        if len(claims) != 1:
            return out
        res = mod.extract(claims[0]["spec"], _Ctx(root))
        rows = res["rows"]
        if rows is None:
            out.append(("extract produced rows", False, res["source"]["reason"]))
            return out
        slug = claims[0]["spec"]["slug"]
        feat = _feature_frame(rows, slug)
        hot = feat[naming.feature_column("map", slug, "HOTAREA-P90")].to_numpy(dtype=float)
        cold = feat[naming.feature_column("map", slug, "COLDAREA-P10")].to_numpy(dtype=float)
        out.append(("no hotspot: HOTAREA < 0.005 everywhere", float(hot.max()) < 0.005,
                    f"max={float(hot.max()):.6f}"))
        out.append(("no hotspot: COLDAREA < 0.005 everywhere", float(cold.max()) < 0.005,
                    f"max={float(cold.max()):.6f}"))
        out.append(("negative run still featured (40 rows)", len(rows) == T, f"{len(rows)} rows"))
    return out


def case_scatter():
    mod = _map()
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        csv = root / "p3_scatter.csv"
        _write_scatter_csv(csv)
        claims = mod.detect([csv], _Ctx(root))
        out.append(("scatter source is registered (one claim)", len(claims) == 1, f"{len(claims)} claims"))
        if len(claims) != 1:
            return out
        meta = claims[0]["spec"]["meta"]
        out.append(("detect marks scatter=true", meta["scatter"] is True, json.dumps(meta)))
        out.append(("scatter coverage < 0.6", meta["pair_coverage"] < 0.6,
                    f"cov={meta['pair_coverage']:.4f}"))
        res = mod.extract(claims[0]["spec"], _Ctx(root))
        src = res["source"]
        out.append(("disposition insufficient_data", src["disposition"] == "insufficient_data",
                    src["disposition"]))
        out.append(("registered under shape=map", src["shape"] == "map", src["shape"]))
        out.append(("no feature rows", res["rows"] is None,
                    "rows is None" if res["rows"] is None else "rows emitted"))
        out.append(("no feature columns in contract", list(res["contract"]) == [],
                    f"{len(res['contract'])} contract rows"))
        out.append(("reason names the scatter/M3 deferral", "scatter" in src["reason"], src["reason"][:120]))
    return out


def case_missing_cells():
    mod = _map()
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        csv = root / "p3_grid_punched.csv"
        _write_grid_csv(csv, hotspot=True, punch=N * N // 5)  # 20% of 400 = 80 cells per snapshot
        claims = mod.detect([csv], _Ctx(root))
        out.append(("80% coverage still claims a regular grid",
                    len(claims) == 1 and claims[0]["spec"]["meta"]["scatter"] is False
                    and claims[0]["spec"]["meta"]["pair_coverage"] >= 0.6,
                    f"cov={claims[0]['spec']['meta']['pair_coverage']:.3f}" if claims else "no claim"))
        if len(claims) != 1:
            return out
        res = mod.extract(claims[0]["spec"], _Ctx(root))
        rows = res["rows"]
        out.append(("disposition featured with missing cells",
                    res["source"]["disposition"] == "featured", res["source"]["reason"]))
        if rows is None:
            out.append(("extract produced rows", False, res["source"]["reason"]))
            return out
        slug = claims[0]["spec"]["slug"]
        feat = _feature_frame(rows, slug)
        finite = np.isfinite(feat.to_numpy(dtype=float))
        out.append(("all 11 features finite on all 40 punched snapshots",
                    bool(finite.all()), f"{int((~finite).sum())} non-finite entries"))
        # N must track the actual retained cells read back from the CSV
        raw = pd.read_csv(csv)
        expected_n = raw.groupby("ts").size().reindex([_ts(i) for i in range(T)]).to_numpy()
        got_n = rows["n_inputs"].to_numpy()
        out.append(("N / n_inputs equal the retained cell count per snapshot",
                    bool((got_n == expected_n).all()),
                    f"expected~320, t5={int(expected_n[5])}, got t5={int(got_n[5])}, min={int(got_n.min())}"))
        # ---- no interpolation, probed on the raster itself -------------------
        df5 = raw[raw["ts"] == _ts(5)]
        x_order = sorted(float(q) for q in raw["x"].unique())
        y_order = sorted(float(q) for q in raw["y"].unique())
        sub = df5[["x", "y", "thick"]].rename(columns={"thick": "v"}).astype(float)
        mat = mod.snapshot_matrix(sub, y_order, x_order)
        ix, iy = 10, 10
        out.append(("punched cell (x=10,y=10) stays NaN in the raster",
                    not math.isfinite(mat[iy, ix]),
                    f"value={mat[iy, ix]}"))
        neighbour_csv = float(df5[(df5["x"] == 10) & (df5["y"] == 11)]["thick"].iloc[0])
        out.append(("retained neighbour (x=10,y=11) equals its original CSV value (no local fill)",
                    mat[11, 10] == neighbour_csv,
                    f"raster={mat[11, 10]!r} csv={neighbour_csv!r}"))
        mean_csv = float(df5["thick"].mean())
        mean_col = naming.feature_column("map", slug, "MEAN")
        out.append(("snapshot MEAN equals the independent recomputation (1e-9)",
                    abs(float(rows.iloc[5][mean_col]) - mean_csv) <= 1e-9,
                    f"rows={float(rows.iloc[5][mean_col]):.9f} csv={mean_csv:.9f}"))
        out.append(("cell count N reflects finite cells (not the full 400)",
                    280 <= got_n.min() and got_n.max() <= 360, f"min={int(got_n.min())} max={int(got_n.max())}"))
    return out


def _run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, timeout=300)


def case_build_e2e():
    out = []
    build_py = SCRIPTS / "build.py"
    gate = SCRIPTS / "quality_gate.mjs"
    py = str(SHARED_PY if SHARED_PY.exists() else sys.executable)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw = root / "raw"
        raw.mkdir()
        _write_grid_csv(raw / "p3_field_grid.csv", hotspot=True)
        _write_scatter_csv(raw / "p3_scatter_points.csv")
        run_dir = root / "run"
        r = _run([py, build_py, "--raw-path", raw, "--run-dir", run_dir])
        out.append(("build.py exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        try:
            payload = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            out.append(("build stdout parseable", False, (r.stdout + r.stderr)[-300:]))
            return out
        out.append(("status ok (grid featured)", payload.get("status") == "ok", r.stdout[-200:]))
        out.append(("two sources registered", payload.get("sources") == 2, str(payload.get("sources"))))
        out.append(("11 contract columns", payload.get("columns") == 11, str(payload.get("columns"))))
        het = run_dir / "07_hetero"
        feat_files = sorted(p.name for p in (het / "features").glob("*.csv")) if (het / "features").exists() else []
        out.append(("MAP feature file written", feat_files == ["MAP-P3FIELDGRID.csv"], str(feat_files)))
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        by_disp = {s.get("disposition"): s for s in m.get("sources", [])}
        featured = by_disp.get("featured", {})
        out.append(("manifest featured source: shape/format/ts_source/n_snapshots/cadence",
                    featured.get("shape") == "map" and featured.get("format") == "long_grid"
                    and featured.get("ts_source") == "dcs" and featured.get("n_snapshots") == T
                    and abs((featured.get("cadence_s") or 0) - CADENCE_S) < 1e-9,
                    json.dumps({k: featured.get(k) for k in
                                ("shape", "format", "ts_source", "n_snapshots", "cadence_s")})))
        out.append(("manifest featured source carries 11 feature names",
                    len(featured.get("features", [])) == 11, str(len(featured.get("features", [])))))
        insufficient = by_disp.get("insufficient_data", {})
        out.append(("scatter source registered as insufficient_data with no features",
                    insufficient.get("disposition") == "insufficient_data"
                    and insufficient.get("features") == [],
                    json.dumps({k: insufficient.get(k) for k in ("disposition", "features")})))
        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        cols = contract.get("columns", [])
        out.append(("contract file has 11 columns with all I5 fields",
                    len(cols) == 11 and all(all(f in c for f in I5_FIELDS) for c in cols),
                    f"{len(cols)} columns"))
        out.append(("contract column names pass H8",
                    all(naming.validate_column_name(c["column"]) for c in cols), ""))
        explicit = json.loads((het / "explicit_cols.json").read_text(encoding="utf-8"))
        names = {c["column"] for c in cols}
        out.append(("all MAP columns land in explicit_cols.excludes (stats_eligible=false pending align)",
                    names.issubset(set(explicit.get("excludes", []))),
                    f"excludes={len(explicit.get('excludes', []))}"))
        g = _run(["node", gate, "--run-dir", run_dir])
        verdict = "ok" in (g.stdout or "")
        out.append(("quality gate exit 0 / verdict ok", g.returncode == 0 and verdict,
                    f"rc={g.returncode} {(g.stdout + g.stderr)[-300:]}"))
    return out


def case_small_lattice():
    """3x3 lattice: regular, but below GRID_AXIS_MIN — registered only, and the
    reason must name the size criterion, never a bogus coverage number."""
    mod = _map()
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        csv = root / "p3_small_lattice.csv"
        recs = []
        for t in range(10):
            for x in range(3):
                for y in range(3):
                    recs.append({"ts": _ts(t), "x": x, "y": y, "thick": 50.0 + x - y})
        pd.DataFrame(recs).to_csv(csv, index=False, encoding="utf-8-sig")
        claims = mod.detect([csv], _Ctx(root))
        out.append(("small lattice is registered (one map claim)", len(claims) == 1, f"{len(claims)} claims"))
        if len(claims) != 1:
            return out
        meta = claims[0]["spec"]["meta"]
        out.append(("3x3 lattice is not treated as a regular grid",
                    meta["scatter"] is True and meta["nx"] == 3 and meta["ny"] == 3,
                    json.dumps({k: meta[k] for k in ("scatter", "nx", "ny", "pair_coverage")})))
        res = mod.extract(claims[0]["spec"], _Ctx(root))
        src = res["source"]
        out.append(("disposition insufficient_data", src["disposition"] == "insufficient_data",
                    src["disposition"]))
        out.append(("reason names the minimum field size, not grid coverage",
                    "minimum field size" in src["reason"] and "coverage" not in src["reason"],
                    src["reason"]))
        out.append(("no feature rows", res["rows"] is None,
                    "rows is None" if res["rows"] is None else "rows emitted"))
    return out


CASES = [
    ("p3-grid-hotspot", case_grid_hotspot),
    ("p3-grid-negative", case_grid_negative),
    ("p3-scatter", case_scatter),
    ("p3-small-lattice", case_small_lattice),
    ("p3-missing-cells", case_missing_cells),
    ("p3-build-e2e", case_build_e2e),
]
