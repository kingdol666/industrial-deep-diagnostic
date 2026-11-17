"""test_p1.py — WS1 PROF acceptance cases (fixtures generated in-place, fixed seed).

P1 magnitude/changepoint assertions on a synthetic 300x21 profile
(baseline 12.0 + slight crown + seed noise 0.01; forward-only "+0.096 on the
outer-right 10% band" injection from t* = 40%);
P2 wide-layout vs long-layout equivalence (<1e-9);
P3 partial profile (>40% positions masked) => shape features NaN + contract
   insufficient_data=true, amplitude features retained;
P4 detect discrimination (wide + long claimed, plain 3-column DCS table not);
P5 end-to-end build.py wiring + quality gate on the wide fixture.
"""
from __future__ import annotations

import importlib.util
import json
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


def _load_prof():
    p = SCRIPTS / "heterocore" / "shapes" / "prof.py"
    spec = importlib.util.spec_from_file_location("hetshape_prof", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PROF = _load_prof()

# ---- fixture constants (deterministic; nothing large is committed) ----------
SEED = 20261015
N_POS, N_SNAP, CP_IDX = 21, 300, 120          # t* = 40% of 300
T0 = datetime(2026, 10, 15, 8, 0, 0)
STEP_S = 60.0
INJECT = 0.096                                 # +0.8% of 12.0 on the right 10% band
SHAPE_FEATS = ["SLOPE-LSQ-PER100", "CURV-LSQ", "ZONE-1-3-MEAN",
               "EDGE-L-DEV", "EDGE-R-DEV", "SHIFT-EST"]
AMP_FEATS = ["MEAN", "STD", "MIN", "MAX", "P05", "P50", "P95", "RANGE", "IQR", "MAD", "N"]


class _Ctx:
    """Minimal stand-in for build.py's Ctx (fields per I9 ExtractCtx)."""

    def __init__(self, root, config=None):
        self.run_dir = Path(root)
        self.raw_path = Path(root)
        self.config = config or {}
        self.enable_vlm = self.enable_llm = self.enable_pca = False
        self.strict_no_rolling = True
        self.seed = SEED
        self.taken_slugs = {}


def _baseline_row():
    i = np.arange(N_POS, dtype=float)
    # slight crown (+0.01 amplitude, centred) plus a small negative tilt so the
    # LSQ slope has a definite sign to flip when the right edge is lifted.
    return 12.0 - 0.002 * i + 0.01 * (1.0 - ((i - 10.0) / 10.0) ** 2)


def _matrix(rng, inject_from=None):
    base = _baseline_row()
    rows = np.empty((N_SNAP, N_POS), dtype=float)
    for t in range(N_SNAP):
        row = base + rng.normal(0.0, 0.01, N_POS)
        if inject_from is not None and t >= inject_from:
            row[N_POS - 2] += INJECT
            row[N_POS - 1] += INJECT
        rows[t] = row
    return rows


def _ts_strings(n=N_SNAP):
    return [(T0 + timedelta(seconds=STEP_S * i)).strftime("%Y-%m-%d %H:%M:%S")
            for i in range(n)]


def _write_wide(path, matrix, mask_rng=None, mask_frac=0.0):
    data = matrix.astype(float).copy()
    if mask_frac > 0:
        # mask >40% of POSITIONS within every snapshot row (per-row random draw)
        k = int(round(mask_frac * N_POS))
        for t in range(len(data)):
            idx = mask_rng.choice(N_POS, size=k, replace=False)
            data[t, idx] = np.nan
    cols = {"时间": _ts_strings(len(data))}
    for j in range(N_POS):
        cols[f"pos_{j + 1:02d}"] = data[:, j]
    pd.DataFrame(cols).to_csv(path, index=False, encoding="utf-8")


def _write_long(path, matrix):
    ts = _ts_strings(len(matrix))
    recs = []
    for t in range(len(matrix)):
        for j in range(N_POS):
            recs.append((ts[t], j + 1, float(matrix[t, j])))
    pd.DataFrame(recs, columns=["时间", "位置", "值"]).to_csv(path, index=False, encoding="utf-8")


def _detect_one(mod, ctx, paths):
    dets = mod.detect(list(paths), ctx)
    return {Path(d["spec"]["path"]).name: d for d in dets}


def case_p1_magnitude():
    mod = PROF
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        matrix = _matrix(np.random.default_rng(SEED), inject_from=CP_IDX)
        wide = root / "thk_profile_a.csv"
        _write_wide(wide, matrix)

        ctx = _Ctx(root)
        dets = mod.detect([wide], ctx)
        out.append(("wide fixture detected as profile",
                    len(dets) == 1 and dets[0]["shape"] == "profile",
                    json.dumps([d["meta"] for d in dets], default=str)))
        if not dets:
            return out
        res = mod.extract(dets[0]["spec"], ctx)
        rows = res["rows"]
        slug = dets[0]["spec"]["slug"]

        def C(f):
            return naming.feature_column("profile", slug, f)

        expect_prefix = ["ts", "_src_ts", "n_inputs"] + [f"pos_{j + 1:02d}" for j in range(N_POS)]
        out.append(("rows column order ts/_src_ts/n_inputs/pos_*/features",
                    list(rows.columns)[:3] == ["ts", "_src_ts", "n_inputs"]
                    and list(rows.columns)[3:3 + N_POS] == expect_prefix[3:]
                    and list(rows.columns)[3 + N_POS:] == [C(f) for f in mod.FEATURE_ORDER],
                    str(list(rows.columns)[:5]) + " ... " + str(list(rows.columns[-2:]))))
        out.append(("_src_ts equals ts on every row",
                    bool((rows["_src_ts"] == rows["ts"]).all()), ""))
        out.append(("n_inputs == 21 on every full snapshot",
                    bool((rows["n_inputs"] == N_POS).all()),
                    str(sorted(rows["n_inputs"].unique().tolist()))))

        edge_r = rows[C("EDGE-R-DEV")].to_numpy(dtype=float)
        pre = float(edge_r[10:CP_IDX - 5].mean())
        post = float(edge_r[CP_IDX + 5:].mean())
        out.append((f"EDGE-R-DEV pre-window mean <= 0.02 (got {pre:+.4f})", pre <= 0.02, f"pre={pre:.4f}"))
        out.append((f"EDGE-R-DEV post-window mean in [0.06,0.10] (got {post:+.4f})",
                    0.06 <= post <= 0.10, f"post={post:.4f}"))

        slope = rows[C("SLOPE-LSQ-PER100")].to_numpy(dtype=float)
        s_pre = float(slope[10:CP_IDX - 5].mean())
        s_post = float(slope[CP_IDX + 5:].mean())
        out.append((f"SLOPE-LSQ-PER100 sign flips across changepoint (pre {s_pre:+.5f} -> post {s_post:+.5f})",
                    s_pre < 0.0 < s_post, f"pre={s_pre:.5f} post={s_post:.5f}"))

        above = np.where(edge_r > 0.04)[0]
        cp = int(above[0]) if len(above) else -1
        out.append((f"changepoint localized within ±1 snapshot (first cross at {cp}, t*={CP_IDX})",
                    abs(cp - CP_IDX) <= 1, f"first_cross={cp} expected={CP_IDX}"))

        arg = rows[C("ARGDEV-NBR")].to_numpy(dtype=float)
        post_arg = arg[CP_IDX + 5:]
        frac_right = float(np.isin(post_arg, [18.0, 19.0, 20.0]).mean())
        out.append((f"post-change ARGDEV-NBR points into the right-edge zone ({frac_right * 100:.1f}% in {{18,19,20}})",
                    frac_right >= 0.9, f"frac={frac_right:.3f}"))
        out.append((f"post-change ARGDEV-NBR mean in right region ({np.nanmean(post_arg):.2f})",
                    float(np.nanmean(post_arg)) >= 17.5, f"mean={np.nanmean(post_arg):.2f}"))

        shift = rows[C("SHIFT-EST")].to_numpy(dtype=float)
        out.append(("SHIFT-EST finite on every snapshot",
                    bool(np.isfinite(shift).all()), f"nan={int(np.isnan(shift).sum())}"))
        out.append((f"SHIFT-EST bounded, no phantom lateral shift (mean {np.nanmean(shift):+.3f})",
                    abs(float(np.nanmean(shift))) <= 2.0, f"mean={np.nanmean(shift):.3f}"))

        mean_f = rows[C("MEAN")].to_numpy(dtype=float)
        delta = float(mean_f[CP_IDX + 5:].mean() - mean_f[10:CP_IDX - 5].mean())
        out.append((f"MEAN level shift ≈ +0.096*2/21 (got {delta:+.4f})",
                    0.007 <= delta <= 0.011, f"delta={delta:.4f}"))

        ctr = {c["column"]: c for c in res["contract"]}
        out.append(("18 feature contracts emitted", len(res["contract"]) == 18, str(len(res["contract"]))))
        out.append(("all contract column names pass the H8 regex",
                    all(naming.validate_column_name(c) for c in ctr),
                    str([c for c in ctr if not naming.validate_column_name(c)])))
        out.append(("contracts carry formula/physics_basis/L1/tag_cn/tag_en/_src_ts=ts",
                    all(c["formula"] and c["physics_basis"] and c["evidence_level"] == 1
                        and c["tag_cn"] and c["tag_en"] and c["_src_ts"] == "ts"
                        for c in ctr.values()), ""))
        out.append(("role=target_candidate on every feature contract",
                    all(c["role"] == "target_candidate" for c in ctr.values()), ""))
        out.append(("no feature marked insufficient on the full fixture",
                    not any(c["insufficient_data"] for c in ctr.values()),
                    str([c for c in ctr if ctr[c]["insufficient_data"]])))
        src = res["source"]
        out.append(("source meta complete (n_snapshots/cadence/ts_format/disposition/features)",
                    src["n_snapshots"] == N_SNAP and src["shape"] == "profile"
                    and src["disposition"] == "featured" and len(src["features"]) == 18
                    and abs(src["cadence_s"] - 60.0) < 1e-9 and src["ts_source"] == "dcs"
                    and src["duplicate_key_policy"] == "aggregate" and src["tz"] is None,
                    json.dumps({k: src[k] for k in ("n_snapshots", "cadence_s", "span_s", "ts_format")},
                               default=str)))

        # declared in_control_window (first 60 snapshots) must equal the
        # first-20% fallback because the window covers exactly those snapshots
        ctx2 = _Ctx(root, config={"in_control_window": {"start": "2026-10-15 08:00:00",
                                                        "end": "2026-10-15 08:59:00"}})
        res2 = mod.extract(dets[0]["spec"], ctx2)
        s1 = rows[C("SHIFT-EST")].to_numpy(dtype=float)
        s2 = res2["rows"][C("SHIFT-EST")].to_numpy(dtype=float)
        out.append(("declared in_control_window baseline == first-20% fallback here",
                    bool(np.array_equal(s1, s2)),
                    f"diffs={int((s1 != s2).sum())}"))
    return out


def case_p2_wide_long_equivalence():
    mod = PROF
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        matrix = _matrix(np.random.default_rng(SEED + 1), inject_from=CP_IDX)
        wide, lng = root / "thk_wide.csv", root / "thk_long.csv"
        _write_wide(wide, matrix)
        _write_long(lng, matrix)

        ctx = _Ctx(root)
        dets = mod.detect([wide, lng], ctx)
        by_name = _detect_one(mod, ctx, [wide, lng])
        out.append(("both layouts detected as profile",
                    {d["meta"]["layout"] for d in dets} == {"wide", "long"},
                    str([(Path(d["spec"]["path"]).name, d["meta"].get("layout")) for d in dets])))
        if {"thk_wide.csv", "thk_long.csv"} - set(by_name):
            return out
        rw = mod.extract(by_name["thk_wide.csv"]["spec"], ctx)["rows"]
        rl = mod.extract(by_name["thk_long.csv"]["spec"], ctx)["rows"]

        fw = [c for c in rw.columns if c.startswith("HX-")]
        fl = [c for c in rl.columns if c.startswith("HX-")]
        out.append((f"both layouts yield 18 derived columns ({len(fw)}/{len(fl)})",
                    len(fw) == 18 and len(fl) == 18, f"{len(fw)}/{len(fl)}"))

        ok, worst = True, 0.0
        for cw, cl in zip(fw, fl):
            a = rw[cw].to_numpy(dtype=float)
            b = rl[cl].to_numpy(dtype=float)
            if a.shape != b.shape:
                ok = False
                break
            d = float(np.nanmax(np.abs(a - b))) if len(a) else 0.0
            worst = max(worst, d)
        out.append((f"P2: every derived feature column wide ≡ long within 1e-9 (max|Δ|={worst:.2e})",
                    ok and worst < 1e-9, f"max|delta|={worst:.3e}"))

        pos_cols = [f"pos_{j + 1:02d}" for j in range(N_POS)]
        pw = rw[pos_cols].to_numpy(dtype=float)
        pl = rl[pos_cols].to_numpy(dtype=float)
        out.append(("retained position matrices identical",
                    bool(np.allclose(pw, pl, equal_nan=True, atol=1e-12)),
                    f"max|delta|={float(np.nanmax(np.abs(pw - pl))):.3e}"))
        out.append(("ts columns identical",
                    bool((rw["ts"].to_numpy() == rl["ts"].to_numpy()).all())
                    and bool((rw["_src_ts"].to_numpy() == rl["_src_ts"].to_numpy()).all()), ""))
    return out


def case_p3_partial_profile():
    mod = PROF
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        matrix = _matrix(np.random.default_rng(SEED + 2))
        p = root / "thk_partial.csv"
        _write_wide(p, matrix, mask_rng=np.random.default_rng(SEED + 3), mask_frac=0.45)

        ctx = _Ctx(root)
        dets = mod.detect([p], ctx)
        out.append(("masked fixture still detected as profile", len(dets) == 1,
                    json.dumps([d["meta"] for d in dets], default=str)))
        if not dets:
            return out
        res = mod.extract(dets[0]["spec"], ctx)
        rows = res["rows"]
        slug = dets[0]["spec"]["slug"]

        def C(f):
            return naming.feature_column("profile", slug, f)

        n_in = rows["n_inputs"].to_numpy(dtype=float)
        out.append((f"every masked snapshot keeps <60% finite (min {n_in.min():.0f}, max {n_in.max():.0f})",
                    bool((n_in < 0.6 * N_POS).all()), f"range=[{n_in.min():.0f},{n_in.max():.0f}]"))

        for f in SHAPE_FEATS:
            col = rows[C(f)].to_numpy(dtype=float)
            out.append((f"shape feature {f} all-NaN on partial snapshots",
                        bool(np.isnan(col).all()), f"finite_count={int(np.isfinite(col).sum())}"))
        for f in AMP_FEATS:
            col = rows[C(f)].to_numpy(dtype=float)
            out.append((f"amplitude feature {f} retained (finite) on partial snapshots",
                        bool(np.isfinite(col).all()), f"nan_count={int(np.isnan(col).sum())}"))
        out.append(("N equals per-row finite count",
                    bool((rows[C("N")].to_numpy(dtype=float) == n_in).all()), ""))

        ctr = {c["column"]: c for c in res["contract"]}
        for f in SHAPE_FEATS:
            out.append((f"contract {f} insufficient_data=true for the whole source",
                        ctr[C(f)]["insufficient_data"] is True,
                        str(ctr[C(f)]["insufficient_data"])))
        out.append(("contract MEAN not insufficient",
                    ctr[C("MEAN")]["insufficient_data"] is False, ""))
        out.append(("contract MEAN coverage 1.0 / sparse false",
                    abs(ctr[C("MEAN")]["coverage"] - 1.0) < 1e-12 and ctr[C("MEAN")]["sparse"] is False,
                    f"coverage={ctr[C('MEAN')]['coverage']}"))
        out.append(("contract EDGE-R-DEV coverage 0.0 / sparse true",
                    ctr[C("EDGE-R-DEV")]["coverage"] == 0.0 and ctr[C("EDGE-R-DEV")]["sparse"] is True,
                    f"coverage={ctr[C('EDGE-R-DEV')]['coverage']}"))
    return out


def case_p4_detect_discrimination():
    mod = PROF
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rng = np.random.default_rng(SEED + 4)
        matrix = _matrix(rng)[:12]
        ts = _ts_strings(12)
        pd.DataFrame({"时间": ts, **{f"pos_{j + 1:02d}": matrix[:, j] for j in range(N_POS)}}).to_csv(
            root / "scan_wide.csv", index=False)
        recs = [(ts[t], j + 1, float(matrix[t, j])) for t in range(12) for j in range(N_POS)]
        pd.DataFrame(recs, columns=["时间", "位置", "值"]).to_csv(root / "scan_long.csv", index=False)
        pd.DataFrame({"时间": ts, "温度": rng.normal(25.0, 1.0, 12),
                      "压力": rng.normal(3.0, 0.2, 12),
                      "流量": rng.normal(120.0, 4.0, 12)}).to_csv(root / "dcs_plain.csv", index=False)

        ctx = _Ctx(root)
        dets = mod.detect(sorted(root.glob("*.csv")), ctx)
        claimed = sorted(Path(d["spec"]["path"]).name for d in dets)
        out.append((f"only wide+long claimed as profile (claimed={claimed})",
                    claimed == ["scan_long.csv", "scan_wide.csv"], str(claimed)))
        out.append(("plain 3-column DCS table NOT claimed as profile",
                    "dcs_plain.csv" not in claimed, str(claimed)))
        out.append(("every detection carries shape=profile",
                    all(d["shape"] == "profile" for d in dets), ""))
        out.append(("detection meta reports layout + heuristic basis",
                    all(d["meta"].get("layout") in ("wide", "long")
                        and d["meta"].get("heuristic") for d in dets),
                    json.dumps([d["meta"] for d in dets], ensure_ascii=False)))
        spec = next(d["spec"] for d in dets if Path(d["spec"]["path"]).name == "scan_wide.csv")
        out.append(("spec carries source_id/path/slug/path_sha6/shape/format",
                    spec["shape"] == "profile" and spec["format"] == "csv"
                    and spec["slug"] == "SCANWIDE" and spec["source_id"] == spec["slug"]
                    and isinstance(spec["path_sha6"], str) and len(spec["path_sha6"]) == 6
                    and spec["path"].endswith("scan_wide.csv"),
                    json.dumps(spec)))
        out.append(("slug registry updated in ctx.taken_slugs",
                    set(ctx.taken_slugs) == {"SCANLONG", "SCANWIDE"}, str(ctx.taken_slugs)))
    return out


def case_p5_build_end_to_end():
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        run_dir, raw = root / "run", root / "raw"
        (run_dir / "00_input").mkdir(parents=True)
        raw.mkdir()
        matrix = _matrix(np.random.default_rng(SEED + 5), inject_from=CP_IDX)
        _write_wide(raw / "thk_e2e.csv", matrix)

        py = str(SHARED_PY if SHARED_PY.exists() else sys.executable)
        r = subprocess.run([py, str(SCRIPTS / "build.py"), "--raw-path", str(raw),
                            "--run-dir", str(run_dir)],
                           capture_output=True, text=True, shell=False, timeout=300)
        out.append(("build.py exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        try:
            payload = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return [("build stdout parseable", False, (r.stdout + r.stderr)[-400:])]
        out.append(("status ok with a featured profile source", payload.get("status") == "ok",
                    r.stdout[-200:]))

        het = run_dir / "07_hetero"
        feats = sorted((het / "features").glob("PROF-*.csv"))
        out.append(("features/PROF-<slug>.csv written", len(feats) == 1,
                    str([f.name for f in feats])))

        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        cols = contract["columns"]
        i5 = ("column", "shape", "source_id", "source_path", "source_sha256", "unit", "role",
              "physical_meaning", "formula", "physics_basis", "evidence_level",
              "evidence_level_basis", "method", "method_version", "n_inputs", "coverage",
              "effective_n", "sparse", "stats_eligible", "cadence_s", "ts_source", "tz",
              "clock_offset_s", "tag_cn", "tag_en", "model_derived", "_src_ts", "insufficient_data")
        out.append(("contract has exactly the 18 PROF feature columns",
                    len(cols) == 18 and all(c["shape"] == "PROF" for c in cols), str(len(cols))))
        out.append(("every contract row carries the full I5 field set",
                    all(all(k in c for k in i5) for c in cols), str(sorted(set(i5) - set(cols[0])))))
        out.append(("contract unit falls back to null for an untagged source",
                    all(c["unit"] is None for c in cols), str({c["unit"] for c in cols})))

        fcsv = pd.read_csv(feats[0])
        out.append(("features CSV header: ts,_src_ts,n_inputs,pos_01.. then HX columns",
                    list(fcsv.columns)[:3] == ["ts", "_src_ts", "n_inputs"]
                    and list(fcsv.columns)[3] == "pos_01"
                    and all(c.startswith("HX-PROF-") for c in fcsv.columns[3 + N_POS:]),
                    str(list(fcsv.columns)[:5])))

        man = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        s0 = man["sources"][0]
        out.append(("manifest source block: profile/featured/18 features/dcs/aggregate",
                    s0["shape"] == "profile" and s0["disposition"] == "featured"
                    and s0["n_snapshots"] == N_SNAP and len(s0["features"]) == 18
                    and s0["ts_source"] == "dcs" and s0["duplicate_key_policy"] == "aggregate"
                    and abs(s0["cadence_s"] - 60.0) < 1e-9
                    and s0["ts_format"] == "%Y-%m-%d %H:%M:%S",
                    json.dumps({k: s0.get(k) for k in ("shape", "disposition", "n_snapshots",
                                                       "cadence_s", "ts_format")})))

        g = subprocess.run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(run_dir)],
                           capture_output=True, text=True, shell=False, timeout=180)
        out.append(("quality gate exit 0 on the profile-only run", g.returncode == 0,
                    (g.stdout + g.stderr)[-400:]))
    return out


def case_p1_fallback_coherence():
    """Wide fallback (no pos_* names) must require spatial coherence across time.

    A genuine profile whose position columns use opaque names is still claimed;
    a narrow multi-signal table (LIMS-style haze/gel/strength/... columns) that
    passes the magnitude gate but whose adjacent columns are unrelated must NOT
    be claimed as a profile.
    """
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rng = np.random.default_rng(SEED + 77)
        n = 200
        ts = _ts_strings(n)
        x = np.linspace(0.0, 1.0, 10)
        common = 0.15 * np.sin(np.arange(n) / 25.0)
        matrix = (12.0 + 0.05 * np.cos(2 * np.pi * x)[None, :]
                  + common[:, None] + rng.normal(0.0, 0.003, (n, 10)))
        probe = root / "thk_opaque_positions.csv"
        data = {"时间": ts}
        for j in range(10):
            data[f"probe_{chr(97 + j)}"] = matrix[:, j]
        pd.DataFrame(data).to_csv(probe, index=False, encoding="utf-8")

        dets = PROF.detect([probe], _Ctx(root))
        out.append(("opaque-name profile claimed via coherence fallback",
                    len(dets) == 1 and dets[0]["meta"].get("layout") == "wide"
                    and "adjacent-coherent" in dets[0]["meta"].get("heuristic", ""),
                    json.dumps([d["meta"] for d in dets], default=str)))

        # 8 unrelated lab-style series; magnitudes stay <=1e4 apart (old gate passed)
        lab = pd.DataFrame({"时间": ts})
        means = [1.5, 3.0, 1.8, 3.1, 215.0, 225.0, 12.0, 32.0]
        for name, mu in zip(["haze", "gel", "shr_td", "shr_md", "str_td", "str_md",
                             "thk", "water"], means):
            lab[name] = mu + rng.normal(0.0, max(0.01, abs(mu) * 0.001), n)
        lab_path = root / "lab_quality.csv"
        lab.to_csv(lab_path, index=False, encoding="utf-8")

        dets2 = PROF.detect([lab_path], _Ctx(root))
        out.append(("narrow multi-signal table not claimed as profile",
                    len(dets2) == 0, json.dumps([d["meta"] for d in dets2], default=str)))
        layout, reason = PROF._identify(lab)
        out.append(("rejection reason names spatial coherence",
                    layout is None and "spatially coherent" in reason, str(reason)))
    return out


CASES = [
    ("p1-magnitude", case_p1_magnitude),
    ("p2-wide-long-equivalence", case_p2_wide_long_equivalence),
    ("p3-partial-profile", case_p3_partial_profile),
    ("p4-detect-discrimination", case_p4_detect_discrimination),
    ("p5-build-end-to-end", case_p5_build_end_to_end),
    ("p1b-fallback-coherence", case_p1_fallback_coherence),
]
