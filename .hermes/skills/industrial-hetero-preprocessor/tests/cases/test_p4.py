"""test_p4.py — WS4 IMG-min acceptance cases (plan §3.1 IMG row / M1 minimal path).

Covers:
  1. synthetic 60-frame 128x128 index-CSV stream (fixed seed; concentric rings,
     last 30 frames ring width +2px) -> 60 rows, N=60, all 6 whole-frame
     features present, ring thickening shifts MEAN and ENTROPY by more than
     2x the first-30 self-fluctuation;
  2. no calibration sidecar -> NO Q-* column anywhere (plan D9);
  3. 3 deliberately corrupted index times -> ts_conflict=3, rows=57,
     reason counter correct;
  4. directory-stream mode (filename-embedded timestamps, no CSV);
  5. Pillow missing -> loud RuntimeError at detect (never silent skip), and
     build.py exits 1 with the install hint (end-to-end via PYTHONPATH shim);
  6. pyproject.toml declares pillow and `uv run` can import PIL.

Fixture images are generated on the fly into a temp dir (fixed seed) — nothing
large is committed (run_tests.py harness contract).
"""
from __future__ import annotations

import importlib.util
import json
import os
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
REPO = SCRIPTS.parent.parent.parent.parent      # repo root
SHARED = REPO / ".claude" / "shared" / "scripts"
SHARED_PY = SHARED / ".venv" / "Scripts" / "python.exe"
if not SHARED_PY.exists():
    SHARED_PY = SHARED / ".venv" / "bin" / "python"
sys.path.insert(0, str(SCRIPTS))

SEED = 20261016                  # fixed seed (discipline: reproducible fixtures)
N_IMAGES = 60
INTERVAL_S = 60
T0 = datetime(2026, 10, 15, 8, 0, 0)
CORRUPT_ROWS = (5, 17, 29)       # index times moved +2h (>> 1 interval)


def _run(cmd: list[str], cwd: str | None = None, env: dict | None = None,
         timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a fixed argument-list command (never a shell string)."""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, cwd=cwd, env=env, timeout=timeout)


def _build_py() -> str:
    return str(SHARED_PY if SHARED_PY.exists() else sys.executable)


def _load_img_module():
    """Load shapes/img.py exactly the way build.py does (importlib by path)."""
    spec = importlib.util.spec_from_file_location(
        "hetshape_img_p4test", SCRIPTS / "heterocore" / "shapes" / "img.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_image_fixture(root: Path, n: int = N_IMAGES) -> tuple[Path, list[datetime], list[str]]:
    """60 128x128 PNGs: background gradient + 3 concentric rings; from frame 30
    the ring width is +2px (ring thickening = detectable effect). Filenames
    embed the acquisition timestamp so both detect modes work."""
    from PIL import Image

    rng = np.random.default_rng(SEED)
    img_dir = root / "cam"
    img_dir.mkdir(parents=True)
    yy, xx = np.mgrid[0:128, 0:128]
    base = 40.0 + (xx / 127.0) * 100.0                 # gradient 40..140
    dist = np.hypot(yy - 63.5, xx - 63.5)
    times: list[datetime] = []
    names: list[str] = []
    for i in range(n):
        t = T0 + timedelta(seconds=INTERVAL_S * i)
        width = 3 + (2 if i >= n // 2 else 0)
        arr = base.copy()
        for r0 in (20, 32, 44):
            arr[(dist >= r0) & (dist < r0 + width)] = 230.0
        arr = np.clip(arr + rng.normal(0, 3, arr.shape), 0, 255).astype("uint8")
        name = f"frame_{t:%Y%m%d_%H%M%S}.png"
        Image.fromarray(arr, "L").save(img_dir / name)
        times.append(t)
        names.append(f"cam/{name}")
    return img_dir, times, names


def _write_index_csv(root: Path, times: list[datetime], names: list[str],
                     corrupt: tuple[int, ...] = ()) -> Path:
    df = pd.DataFrame({"时间": [t.strftime("%Y-%m-%d %H:%M:%S") for t in times],
                       "文件名": names})
    for i in corrupt:
        df.loc[i, "时间"] = (times[i] + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    p = root / "image_index.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p


def _build(root: Path, raw: Path | None = None,
           run_name: str = "run") -> tuple[subprocess.CompletedProcess, Path, dict]:
    run_dir = root / run_name
    r = _run([_build_py(), str(SCRIPTS / "build.py"),
              "--raw-path", str(raw if raw is not None else root),
              "--run-dir", str(run_dir)])
    payload: dict = {}
    try:
        payload = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        pass
    return r, run_dir, payload


def _slug_of(contract: dict) -> str:
    cols = [c["column"] for c in contract["columns"]]
    return cols[0].split("-")[2]


def _effect_assertion(out: list, f: pd.DataFrame, slug: str) -> None:
    """Ring thickening must move MEAN and ENTROPY by more than 2x the first-30
    self-fluctuation (calibrated: MEAN ratio ~530x, ENTROPY ratio ~12x)."""
    for feat in ("MEAN", "ENTROPY"):
        vals = f[f"HX-IMG-{slug}-{feat}"].to_numpy()
        a, b = vals[:30], vals[30:]
        shift = abs(float(b.mean()) - float(a.mean()))
        fluct = float(a.std(ddof=1))
        out.append((f"ring thickening shifts {feat} > 2x first-30 fluctuation",
                    shift > 2.0 * fluct and fluct > 0,
                    f"shift={shift:.6g} 2xfluct={2 * fluct:.6g}"))


# ───────────────────────────── cases ─────────────────────────────

def case_p4_index_stream():
    """Scenario 1: index CSV stream -> 60 rows, N=60, 6 features, effect."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_image_fixture(root)
        _write_index_csv(root, times, names)
        r, run_dir, payload = _build(root)
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        out.append(("status ok with 1 source",
                    payload.get("status") == "ok" and payload.get("sources") == 1, r.stdout[-300:]))
        het = run_dir / "07_hetero"
        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        feat_files = list((het / "features").glob("*.csv"))
        out.append(("one IMG feature table written",
                    len(feat_files) == 1 and feat_files[0].name.startswith("IMG-"),
                    str([f.name for f in feat_files])))
        f = pd.read_csv(feat_files[0], encoding="utf-8-sig")
        out.append(("60 rows all parsed", len(f) == 60, f"rows={len(f)}"))
        slug = _slug_of(contract)
        feat_cols = [c["column"] for c in contract["columns"]]
        for feat in ("MEAN", "STD", "ENTROPY", "SATFRAC", "DARKFRAC", "FOCUS"):
            col = f"HX-IMG-{slug}-{feat}"
            out.append((f"feature column present: {feat}",
                        col in feat_cols and col in f.columns, str(feat_cols)))
        n_col = f"HX-IMG-{slug}-N"
        out.append(("N column == 60 on every row",
                    n_col in f.columns and bool((f[n_col] == 60).all()),
                    f"N unique={sorted(set(f[n_col])) if n_col in f else 'missing'}"))
        roles = {c["column"]: c["role"] for c in contract["columns"]}
        levels = {c["column"]: c["evidence_level"] for c in contract["columns"]}
        preds = [c for c in feat_cols if roles.get(c) == "predictor_candidate"]
        out.append(("6 features role=predictor_candidate evidence_level=1",
                    len(preds) == 6 and all(levels[c] == 1 for c in preds),
                    json.dumps({c: [roles.get(c), levels.get(c)] for c in feat_cols})))
        meanings = " ".join(c["physical_meaning"] for c in contract["columns"])
        out.append(("physical_meaning declares uncalibrated detector frame",
                    "未标定" in meanings and "探测器坐标系" in meanings, meanings[:120]))
        n_meaning = next(c["physical_meaning"] for c in contract["columns"] if c["column"] == n_col)
        out.append(("N is a metadata count column", roles.get(n_col) == "metadata", n_meaning))
        _effect_assertion(out, f, slug)
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        src = m["sources"][0]
        out.append(("source meta: shape/ts_source/policy",
                    src["shape"] == "image_stream" and src["ts_source"] == "index"
                    and src["duplicate_key_policy"] == "aggregate" and src["n_snapshots"] == 60,
                    json.dumps({k: src[k] for k in ("shape", "ts_source", "duplicate_key_policy", "n_snapshots")}))
                   if src else ("source present", False, "no source"))
        g = _run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(run_dir),
                  "--raw-path", str(root)])
        out.append(("quality gate exit 0 (H1-H8 incl. strict extra keys)",
                    g.returncode == 0, (g.stdout + g.stderr)[-400:]))
    return out


def case_p4_no_q_columns():
    """Scenario 2: without a calibration sidecar NO Q-* column may exist (D9)."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_image_fixture(root)
        _write_index_csv(root, times, names)
        r, run_dir, payload = _build(root)
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        het = run_dir / "07_hetero"
        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        cols = [c["column"] for c in contract["columns"]]
        q_re = re.compile(r"(^|-)Q-[A-Za-z0-9]")
        out.append(("contract has no Q-* column", not any(q_re.search(c) for c in cols), str(cols)))
        deep_re = re.compile(r"RADIAL|AZIM|DIFF-RMSE|DEFECT|SHIFT-[XY]")
        out.append(("no M2 deep-path columns (RADIAL/AZIM/DIFF/DEFECT/SHIFT)",
                    not any(deep_re.search(c) for c in cols), str(cols)))
        feat_files = list((het / "features").glob("*.csv"))
        header = pd.read_csv(feat_files[0], encoding="utf-8-sig", nrows=1)
        out.append(("feature table header has no Q-* column",
                    not any(q_re.search(str(c)) for c in header.columns), str(list(header.columns))))
        explicit = json.loads((het / "explicit_cols.json").read_text(encoding="utf-8"))
        out.append(("explicit_cols has no Q-* entry",
                    not any(q_re.search(str(c)) for c in explicit["targets"] + explicit["predictors"] + explicit["excludes"]),
                    json.dumps(explicit)))
    return out


def case_p4_ts_conflict():
    """Scenario 3: 3 corrupted index times -> ts_conflict=3, rows=57."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_image_fixture(root)
        _write_index_csv(root, times, names, corrupt=CORRUPT_ROWS)
        r, run_dir, payload = _build(root)
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        het = run_dir / "07_hetero"
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        src = m["sources"][0]
        out.append(("manifest reason counts ts_conflict=3",
                    "ts_conflict=3" in src.get("reason", ""), src.get("reason", "")))
        out.append(("n_snapshots=57 after conflict drop", src.get("n_snapshots") == 57,
                    f"n_snapshots={src.get('n_snapshots')}"))
        feat_files = list((het / "features").glob("*.csv"))
        f = pd.read_csv(feat_files[0], encoding="utf-8-sig")
        slug = _slug_of(json.loads((het / "column_contract.json").read_text(encoding="utf-8")))
        out.append(("57 rows kept", len(f) == 57, f"rows={len(f)}"))
        out.append(("N column == 57 (decoded & anchored frames)",
                    bool((f[f"HX-IMG-{slug}-N"] == 57).all()),
                    str(sorted(set(f[f"HX-IMG-{slug}-N"]))))
                   if f"HX-IMG-{slug}-N" in f else out.append(("N column present", False, "missing")))
        kept_times = set(f["ts"])
        corrupted = [(T0 + timedelta(seconds=INTERVAL_S * i)).strftime("%Y-%m-%d %H:%M:%S")
                     for i in CORRUPT_ROWS]
        out.append(("conflicted snapshots absent from rows",
                    not any(c in kept_times for c in corrupted), str(sorted(kept_times))[:160]))
        g = _run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(run_dir),
                  "--raw-path", str(root)])
        out.append(("quality gate exit 0 after conflict skip", g.returncode == 0,
                    (g.stdout + g.stderr)[-300:]))
    return out


def case_p4_dir_stream():
    """Detect mode 2: directory stream with filename-embedded timestamps."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        img_dir, times, _ = _make_image_fixture(root, n=24)
        r, run_dir, payload = _build(root, raw=img_dir)
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        out.append(("status ok", payload.get("status") == "ok", r.stdout[-200:]))
        het = run_dir / "07_hetero"
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        src = m["sources"][0]
        out.append(("dir mode detected with ts_source=camera",
                    src["ts_source"] == "camera" and src["ts_format"] == "filename_embedded",
                    json.dumps({k: src[k] for k in ("ts_source", "ts_format", "path")})))
        out.append(("24 rows anchored at 60s cadence",
                    src["n_snapshots"] == 24 and abs((src["cadence_s"] or 0) - 60.0) < 1e-6,
                    f"n={src['n_snapshots']} cadence={src['cadence_s']}"))
        feat_files = list((het / "features").glob("*.csv"))
        f = pd.read_csv(feat_files[0], encoding="utf-8-sig")
        out.append(("feature table has 24 rows", len(f) == 24, f"rows={len(f)}"))
        g = _run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(run_dir),
                  "--raw-path", str(img_dir)])
        out.append(("quality gate exit 0", g.returncode == 0, (g.stdout + g.stderr)[-300:]))
    return out


def case_p4_pillow_missing():
    """Scenario 4: blocked PIL import -> loud RuntimeError at detect, and
    build.py exits 1 with the install hint (never a silent skip)."""
    out = []
    mod = _load_img_module()

    class _FakeCtx:
        run_dir = None
        config = {}
        taken_slugs = {}

    for k in [k for k in sys.modules if k == "PIL" or k.startswith("PIL.")]:
        sys.modules.pop(k, None)
    sys.modules["PIL"] = None          # `import PIL` now raises ImportError
    sys.modules["PIL.Image"] = None
    try:
        try:
            mod.detect([], _FakeCtx())
            out.append(("detect raises on missing pillow", False, "no exception raised"))
        except RuntimeError as exc:
            out.append(("detect raises RuntimeError containing 'pillow missing'",
                        "pillow missing" in str(exc), str(exc)[:200]))
        except Exception as exc:  # noqa: BLE001
            out.append(("detect raises RuntimeError containing 'pillow missing'",
                        False, f"wrong exception {type(exc).__name__}: {exc}"))
    finally:
        sys.modules.pop("PIL", None)
        sys.modules.pop("PIL.Image", None)

    # end-to-end: a fake PIL.py on PYTHONPATH makes the subprocess fail to import PIL
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw = root / "raw"
        raw.mkdir()                      # resolvable raw path; detect must still fail LOUDLY
        shim = root / "shim"
        shim.mkdir()
        (shim / "PIL.py").write_text('raise ImportError("PIL blocked for p4 test")\n', encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(shim) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        r = _run([_build_py(), str(SCRIPTS / "build.py"), "--raw-path", str(raw),
                  "--run-dir", str(root / "run")], env=env)
        blob = r.stdout + r.stderr
        out.append(("build exits 1 on missing pillow", r.returncode == 1, f"rc={r.returncode} {blob[-200:]}"))
        out.append(("build error names the pillow install hint",
                    "pillow missing" in blob and "uv sync --project" in blob, blob[-300:]))
    return out


def case_p4_pyproject_pillow():
    """Scenario 5: pillow declared in pyproject.toml and importable via uv run."""
    out = []
    text = (SHARED / "pyproject.toml").read_text(encoding="utf-8")
    out.append(("pyproject.toml declares pillow", "pillow" in text.lower(), ""))
    r = _run(["uv", "run", "--project", str(SHARED), "python", "-c",
              "import PIL; print('PIL', PIL.__version__)"], cwd=str(REPO))
    out.append(("uv run --project .claude/shared/scripts python imports PIL",
                r.returncode == 0 and "PIL" in r.stdout,
                (r.stdout + r.stderr)[-300:]))
    return out


CASES = [
    ("p4-index-stream-min", case_p4_index_stream),
    ("p4-no-q-columns", case_p4_no_q_columns),
    ("p4-ts-conflict", case_p4_ts_conflict),
    ("p4-dir-stream", case_p4_dir_stream),
    ("p4-pillow-missing", case_p4_pillow_missing),
    ("p4-pyproject-pillow", case_p4_pyproject_pillow),
]
