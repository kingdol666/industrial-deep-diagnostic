"""test_p4deep.py — WS10 IMG deep-path acceptance cases (plan §3.1 IMG row / M2).

Covers (plan v1.1 §8 M2 + §9 AC2/P4-deep):
  1. WITH detector.json sidecar the deep path TAKES OVER the M1 minimal path
     (manifest source reason recognizable as deep:img_deep/calibrated, feature
     table carries Q-RADIAL-*) and the M1 whole-frame columns are GONE
     (mutual exclusion, direction A);
     a ring radius +2px moves the Q-RADIAL-P<k> peak bin by EXACTLY one bin
     (bin width 2 = the +2px step); SHIFT-X/Y == 0 for all non-translated
     frames; 10 frames translated by (+3,+2)px recover SHIFT-X/Y within +/-1;
     the quality gate (H1-H8 incl. strict extra keys) stays green on the new
     Q-* columns;
  2. WITHOUT the sidecar the same fixture runs the M1 minimal path only
     (no Q-* / RADIAL / DEFECT / SHIFT columns, M1 columns present — mutual
     exclusion, direction B; "无标定即无深路径", plan D9). Also checked at
     module level: img_deep.detect returns [] without a sidecar and claims
     with meta={"upgrade": True} with one (explicit config key or beside the
     source);
  3. DEFECT: 5 bright spots (+8 sigma, radius 3px) on 10 frames =>
     DEFECT-COUNT >= 3 and DEFECT-AREA-FRAC > 0; spot-free frames ≈ 0
     (<= 2 components); DIFF-RMSE of defect frames above the clean mean;
  4. 500-frame pressure: build.py wall clock < 60 s (extract is O(n) —
     reference precomputed once), 500 feature rows, thumbnails capped <= 200;
  5. thumbnails: 60 frames => exactly min(60, 200) = 60 PNGs, each 64x64.

Fixture images are generated on the fly into a temp dir (fixed seed) — nothing
large is committed (run_tests.py harness contract). All subprocess calls use
fixed argument lists with shell=False.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
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
INTERVAL_S = 60
T0 = datetime(2026, 10, 15, 8, 0, 0)
BG = 100.0                       # constant background (roll == exact translation)
TEXTURE_STD = 40.0               # static per-run texture: the SHIFT correlation anchor must
                                 # dominate ring-arc ghosts (texture^2 ~1600/px vs ring
                                 # full-match ~120^2*66/N ~ 61/px, ghost <= ~15/px)
RING_JUMP = 120.0                # ring adds +120 gray levels over BG (peak 220 < 255)
NOISE_STD = 3.0
SPOT_SIGMA = 8.0                 # spot amplitude = +8 * NOISE_STD
SPOT_RADIUS_PX = 3
N_SPOTS = 5

M1_FEATURES = ("MEAN", "STD", "ENTROPY", "SATFRAC", "DARKFRAC", "FOCUS")
Q_RE = re.compile(r"(^|-)Q-[A-Za-z0-9]")
DEEP_RE = re.compile(r"RADIAL|AZIM|DIFF-RMSE|DEFECT|SHIFT-[XY]")

_DETECTOR = {
    "pixel_size_um": 100.0,
    "beam_center_px": [63.5, 63.5],
    "detector_distance_mm": 1000.0,
    "wavelength_angstrom": 1.0,
}


def _run(cmd: list, cwd: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a fixed argument-list command (never a shell string)."""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, cwd=cwd, timeout=timeout)


def _build_py() -> str:
    return str(SHARED_PY if SHARED_PY.exists() else sys.executable)


def _make_deep_fixture(root: Path, n_frames: int, ring_shift_from: int | None = None,
                       roll_frames: tuple = (), roll: tuple = (3, 2),
                       defect_frames: tuple = (), size: int = 128,
                       ring_r0: float = 10.0) -> tuple[Path, list, list]:
    """PNG stream with a static texture (SHIFT anchor), one thin concentric ring
    (width 1 px) that optionally jumps +2px at frame `ring_shift_from`, optional
    (+dx,+dy)-translated frames (np.roll on the content — exact because the
    background is constant) and optional bright-spot defect frames. Filenames
    embed the acquisition timestamp. Returns (img_dir, times, names)."""
    from PIL import Image

    rng = np.random.default_rng(SEED)
    img_dir = root / "cam"
    img_dir.mkdir(parents=True)
    yy, xx = np.mgrid[0:size, 0:size]
    c = (size - 1) / 2.0
    dist = np.hypot(yy - c, xx - c)
    texture = rng.normal(0.0, TEXTURE_STD, (size, size))
    ang = np.deg2rad(360.0 / N_SPOTS)
    spots = [(c + 25.0 * np.cos(ang * k), c + 25.0 * np.sin(ang * k)) for k in range(N_SPOTS)]
    times: list = []
    names: list = []
    for i in range(n_frames):
        t = T0 + timedelta(seconds=INTERVAL_S * i)
        r0 = ring_r0 + (2.0 if (ring_shift_from is not None and i >= ring_shift_from) else 0.0)
        content = BG + texture
        content[(dist >= r0) & (dist < r0 + 1.0)] += RING_JUMP
        if i in roll_frames:
            content = np.roll(content, shift=(roll[1], roll[0]), axis=(0, 1))  # (+dx, +dy)
        if i in defect_frames:
            for sx, sy in spots:
                content[((yy - sy) ** 2 + (xx - sx) ** 2) <= SPOT_RADIUS_PX ** 2] += SPOT_SIGMA * NOISE_STD
        arr = np.clip(content + rng.normal(0, NOISE_STD, content.shape), 0, 255).astype("uint8")
        name = f"frame_{t:%Y%m%d_%H%M%S}.png"
        Image.fromarray(arr, "L").save(img_dir / name)
        times.append(t)
        names.append(f"cam/{name}")
    return img_dir, times, names


def _write_index_csv(root: Path, times: list, names: list) -> Path:
    df = pd.DataFrame({"时间": [t.strftime("%Y-%m-%d %H:%M:%S") for t in times],
                       "文件名": names})
    p = root / "image_index.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p


def _write_detector(root: Path, detector: dict | None = None) -> Path:
    p = root / "detector.json"
    p.write_text(json.dumps(detector or _DETECTOR, indent=2), encoding="utf-8")
    return p


def _build(root: Path, raw: Path | None = None, run_name: str = "run") -> tuple:
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


def _load_deep_module():
    """Load shapes/img_deep.py exactly the way build.py does (importlib by path)."""
    spec = importlib.util.spec_from_file_location(
        "hetshape_img_deep_p4deeptest", SCRIPTS / "heterocore" / "shapes" / "img_deep.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeCtx:
    """Just the attrs the shape modules read (mirror of build.py's Ctx)."""

    def __init__(self, root: Path, config: dict | None = None):
        self.run_dir = root / "run"
        self.raw_path = root
        self.config = config or {}
        self.taken_slugs = {}


def _feature_table(run_dir: Path) -> tuple[pd.DataFrame, list]:
    het = run_dir / "07_hetero"
    files = sorted((het / "features").glob("*.csv"))
    if not files:
        return pd.DataFrame(), []
    return pd.read_csv(files[0], encoding="utf-8-sig"), files


def _argmax_bin(frame: pd.DataFrame, slug: str, row_range: tuple) -> int:
    """argmax over k of the Q-RADIAL-P<k> mean profile across [a, b) rows."""
    cols = [f"HX-IMG-{slug}-Q-RADIAL-P{k}" for k in range(1, 9)]
    a, b = row_range
    prof = frame.loc[a:b - 1, cols].mean(axis=0).to_numpy()
    return int(np.argmax(prof)) + 1


# ───────────────────────────── cases ─────────────────────────────

def case_p4deep_calibrated_takeover():
    """Scenario 1: sidecar present -> deep takeover, ring +2px moves the peak
    bin by exactly one, SHIFT recovers (3,2)+-1 and is 0 elsewhere."""
    out = []
    n_frames, n_roll = 70, 10
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_deep_fixture(root, n_frames,
                                             ring_shift_from=30,
                                             roll_frames=tuple(range(60, 60 + n_roll)))
        _write_index_csv(root, times, names)
        _write_detector(root)
        r, run_dir, payload = _build(root)
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        out.append(("status ok with 1 source",
                    payload.get("status") == "ok" and payload.get("sources") == 1, r.stdout[-300:]))
        het = run_dir / "07_hetero"
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        src = m["sources"][0]
        out.append(("manifest source reason is recognizable as the deep path",
                    "deep:img_deep" in src.get("reason", "") and "calibrated=true" in src.get("reason", ""),
                    src.get("reason", "")))
        out.append(("manifest source format marked calibrated",
                    str(src.get("format", "")).endswith("+calibrated"), str(src.get("format"))))
        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        cols = [c["column"] for c in contract["columns"]]
        slug = cols[0].split("-")[2]
        f, files = _feature_table(run_dir)
        out.append(("one IMG feature table with 70 rows", len(files) == 1 and len(f) == n_frames,
                    f"files={[p.name for p in files]} rows={len(f)}"))
        for k in range(1, 9):
            col = f"HX-IMG-{slug}-Q-RADIAL-P{k}"
            out.append((f"deep column present: Q-RADIAL-P{k}",
                        col in cols and col in f.columns, str(cols)))
        for feat in ("Q-AZIM-P1", "Q-AZIM-P8", "DIFF-RMSE", "DEFECT-COUNT",
                     "DEFECT-AREA-FRAC", "SHIFT-X", "SHIFT-Y"):
            col = f"HX-IMG-{slug}-{feat}"
            out.append((f"deep column present: {feat}", col in cols and col in f.columns, str(cols)))
        out.append(("mutual exclusion (direction A): no M1 whole-frame columns remain",
                    not any(f"HX-IMG-{slug}-{feat}" in cols for feat in M1_FEATURES), str(cols)))
        unit = {c["column"]: c["unit"] for c in contract["columns"]}
        qcols = [c for c in cols if Q_RE.search(c)]
        out.append(("all Q-* columns carry unit 1/Å",
                    len(qcols) == 16 and all(unit[c] == "1/Å" for c in qcols),
                    json.dumps({c: unit[c] for c in qcols[:3]})))
        out.append(("SHIFT columns carry unit px",
                    all(unit[f"HX-IMG-{slug}-SHIFT-{a}"] == "px" for a in ("X", "Y")),
                    json.dumps({a: unit[f"HX-IMG-{slug}-SHIFT-{a}"] for a in ("X", "Y")})))
        pb = {c["column"]: c["physics_basis"] for c in contract["columns"]}
        out.append(("Q-column physics_basis carries the sidecar sha256",
                    all("sha256=sha256:" in pb[c] for c in qcols),
                    pb[qcols[0]][:160] if qcols else "no q cols"))
        pre, post = _argmax_bin(f, slug, (0, 30)), _argmax_bin(f, slug, (30, 60))
        out.append(("pre ring peak bin is P6 (ring r in [10,11) px, bin width 2)", pre == 6, f"argmax=P{pre}"))
        out.append(("post ring peak bin is P7 (ring r in [12,13) px)", post == 7, f"argmax=P{post}"))
        out.append(("ring radius +2px moves the peak bin by EXACTLY one bin", post - pre == 1,
                    f"pre=P{pre} post=P{post}"))
        sx, sy = f[f"HX-IMG-{slug}-SHIFT-X"].to_numpy(), f[f"HX-IMG-{slug}-SHIFT-Y"].to_numpy()
        out.append(("SHIFT-X/Y exactly 0 on all 60 non-translated frames",
                    bool((sx[:60] == 0).all() and (sy[:60] == 0).all()),
                    f"X={sorted(set(sx[:60].tolist()))} Y={sorted(set(sy[:60].tolist()))}"))
        out.append(("translated frames recover SHIFT-X=3 within +/-1",
                    bool((np.abs(sx[60:] - 3) <= 1).all()), f"X={sx[60:].tolist()}"))
        out.append(("translated frames recover SHIFT-Y=2 within +/-1",
                    bool((np.abs(sy[60:] - 2) <= 1).all()), f"Y={sy[60:].tolist()}"))
        thumbs = sorted((het / "objects" / slug / "thumbs").glob("*.png"))
        out.append(("thumbnails written for min(70,200) frames", len(thumbs) == min(n_frames, 200),
                    f"{len(thumbs)} thumbs"))
        g = _run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(run_dir),
                  "--raw-path", str(root)])
        out.append(("quality gate exit 0 (H1-H8 with Q-* columns)", g.returncode == 0,
                    (g.stdout + g.stderr)[-400:]))
    return out


def case_p4deep_no_sidecar_m1_exclusive():
    """Scenario 2: no sidecar -> M1 minimal path only (mutual exclusion,
    direction B); module-level detect refuses without and claims with a
    sidecar (upgrade flag, explicit config key or beside the source)."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_deep_fixture(root, 60)
        _write_index_csv(root, times, names)
        deep = _load_deep_module()

        det_path = _write_detector(root)
        d1 = deep.detect(sorted(p for p in root.rglob("*") if p.is_file()), _FakeCtx(root))
        out.append(("module detect claims WITH sidecar", len(d1) >= 1,
                    f"{len(d1)} detections"))
        out.append(("claim carries meta upgrade=true",
                    bool(d1) and all(d.get("meta", {}).get("upgrade") is True for d in d1),
                    json.dumps([d.get("meta") for d in d1])))
        out.append(("claim carries the validated calibration",
                    bool(d1) and d1[0]["spec"]["calibration"]["pixel_size_um"] == 100.0
                    and d1[0]["spec"]["calibration"]["beam_center_px"] == [63.5, 63.5],
                    json.dumps(d1[0]["spec"].get("calibration")) if d1 else "none"))
        det_path.unlink()
        d2 = deep.detect(sorted(p for p in root.rglob("*") if p.is_file()), _FakeCtx(root))
        out.append(("module detect returns [] WITHOUT sidecar (D9)", d2 == [], repr(d2)))
        _write_detector(root)
        d3 = deep.detect(sorted(p for p in root.rglob("*") if p.is_file()),
                         _FakeCtx(root, config={"detector_json": str(det_path)}))
        det_path.unlink()
        out.append(("explicit config detector_json key is honored",
                    len(d3) >= 1 and d3[0]["spec"]["calibration"]["sidecar_path"] == str(det_path),
                    json.dumps([d["spec"]["calibration"]["sidecar_path"] for d in d3])))

        r, run_dir, payload = _build(root)   # detector.json removed above
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        het = run_dir / "07_hetero"
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        src = m["sources"][0]
        out.append(("manifest source took the M1 path, not the deep path",
                    "deep:img_deep" not in src.get("reason", ""), src.get("reason", "")))
        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        cols = [c["column"] for c in contract["columns"]]
        slug = cols[0].split("-")[2]
        f, files = _feature_table(run_dir)
        out.append(("no Q-* column anywhere in the contract",
                    not any(Q_RE.search(c) for c in cols), str(cols)))
        out.append(("no deep-path column anywhere in the contract",
                    not any(DEEP_RE.search(c) for c in cols), str(cols)))
        out.append(("feature table header has no Q-*/deep column",
                    not any(Q_RE.search(str(c)) or DEEP_RE.search(str(c)) for c in f.columns),
                    str(list(f.columns))))
        out.append(("mutual exclusion (direction B): M1 whole-frame columns present",
                    all(f"HX-IMG-{slug}-{feat}" in cols for feat in M1_FEATURES), str(cols)))
    return out


def case_p4deep_defect():
    """Scenario 3: 5 bright spots (+8 sigma, r=3px) on 10 frames -> COUNT>=3,
    AREA-FRAC>0; spot-free frames ~0. Scenario 5: 60 frames -> exactly 60
    64x64 PNG thumbnails."""
    out = []
    n_frames = 60
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_deep_fixture(root, n_frames, defect_frames=tuple(range(40, 50)))
        _write_index_csv(root, times, names)
        _write_detector(root)
        r, run_dir, payload = _build(root)
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        het = run_dir / "07_hetero"
        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        cols = [c["column"] for c in contract["columns"]]
        slug = cols[0].split("-")[2]
        f, files = _feature_table(run_dir)
        out.append(("deep path ran (DEFECT columns exist)",
                    f"HX-IMG-{slug}-DEFECT-COUNT" in f.columns, str(cols)))
        if f"HX-IMG-{slug}-DEFECT-COUNT" not in f.columns:
            return out
        cnt = f[f"HX-IMG-{slug}-DEFECT-COUNT"].to_numpy()
        frac = f[f"HX-IMG-{slug}-DEFECT-AREA-FRAC"].to_numpy()
        rmse = f[f"HX-IMG-{slug}-DIFF-RMSE"].to_numpy()
        defect_rows = list(range(40, 50))
        clean_rows = [i for i in range(n_frames) if i not in defect_rows]
        out.append(("defect frames: DEFECT-COUNT >= 3",
                    bool((cnt[defect_rows] >= 3).all()), f"counts={cnt[defect_rows].tolist()}"))
        out.append(("defect frames: DEFECT-AREA-FRAC > 0",
                    bool((frac[defect_rows] > 0).all()), f"frac={np.round(frac[defect_rows], 5).tolist()}"))
        out.append(("spot-free frames: DEFECT-COUNT ~ 0 (<= 2)",
                    bool((cnt[clean_rows] <= 2).all()), f"max={int(cnt[clean_rows].max())}"))
        out.append(("spot-free frames: DEFECT-AREA-FRAC <= 0.005",
                    bool((frac[clean_rows] <= 0.005).all()), f"max={float(np.nanmax(frac[clean_rows])):.5f}"))
        out.append(("defect frames have higher DIFF-RMSE than the clean mean",
                    float(rmse[defect_rows].mean()) > float(rmse[clean_rows].mean()),
                    f"defect={rmse[defect_rows].mean():.3f} clean={rmse[clean_rows].mean():.3f}"))
        thumbs = sorted((het / "objects" / slug / "thumbs").glob("*.png"))
        out.append(("scenario 5: exactly min(60,200) thumbnails", len(thumbs) == min(n_frames, 200),
                    f"{len(thumbs)} thumbs"))
        from PIL import Image
        sizes = set()
        for p in thumbs:
            with Image.open(p) as im:
                sizes.add(im.size)
        out.append(("every thumbnail is a 64x64 PNG", sizes == {(64, 64)},
                    f"unique sizes={sorted(sizes)} sample={thumbs[0].name if thumbs else 'none'}"))
        g = _run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(run_dir),
                  "--raw-path", str(root)])
        out.append(("quality gate exit 0", g.returncode == 0, (g.stdout + g.stderr)[-300:]))
    return out


def case_p4deep_stress_500():
    """Scenario 4: 500-frame pressure — build.py wall clock < 60 s, 500 rows,
    thumbnail cap respected (extract is O(n): reference precomputed once)."""
    out = []
    n_frames = 500
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_deep_fixture(root, n_frames, size=96)
        _write_index_csv(root, times, names)
        _write_detector(root, {**_DETECTOR, "beam_center_px": [47.5, 47.5]})
        t0 = time.perf_counter()
        r, run_dir, payload = _build(root)
        wall = time.perf_counter() - t0
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        out.append(("500-frame build completes in < 60 s", wall < 60.0, f"wall={wall:.1f}s"))
        het = run_dir / "07_hetero"
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        src = m["sources"][0]
        out.append(("manifest reports 500 snapshots", src.get("n_snapshots") == n_frames,
                    f"n_snapshots={src.get('n_snapshots')}"))
        f, files = _feature_table(run_dir)
        slug = [c["column"] for c in
                json.loads((het / "column_contract.json").read_text(encoding="utf-8"))["columns"]][0].split("-")[2]
        out.append(("feature table has 500 rows", len(f) == n_frames, f"rows={len(f)}"))
        out.append(("N column == 500 on every row",
                    bool((f[f"HX-IMG-{slug}-N"] == n_frames).all()),
                    str(sorted(set(f[f"HX-IMG-{slug}-N"].tolist())))))
        thumbs = list((het / "objects" / slug / "thumbs").glob("*.png"))
        out.append(("thumbnails capped at <= 200 (stride sampling)",
                    0 < len(thumbs) <= 200, f"{len(thumbs)} thumbs"))
        cards = list((het / "objects" / slug).glob("*.json"))
        out.append(("one object card per frame", len(cards) >= n_frames, f"{len(cards)} cards"))
    return out


def case_p4deep_thumbs_dedicated():
    """Scenario 5 (dedicated): 60 frames -> 60 PNG thumbnails at 64x64, cards
    reference them, and the calibration provenance is on every card."""
    out = []
    n_frames = 60
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _, times, names = _make_deep_fixture(root, n_frames)
        _write_index_csv(root, times, names)
        _write_detector(root)
        r, run_dir, payload = _build(root)
        out.append(("build exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        het = run_dir / "07_hetero"
        contract = json.loads((het / "column_contract.json").read_text(encoding="utf-8"))
        slug = contract["columns"][0]["column"].split("-")[2]
        obj_dir = het / "objects" / slug
        thumbs = sorted((obj_dir / "thumbs").glob("*.png"))
        out.append(("thumb count == min(60, 200)", len(thumbs) == min(n_frames, 200),
                    f"{len(thumbs)} thumbs"))
        from PIL import Image
        bad = []
        for p in thumbs:
            with Image.open(p) as im:
                if im.size != (64, 64) or im.format != "PNG":
                    bad.append((p.name, im.size, im.format))
        out.append(("all thumbs are 64x64 PNGs", not bad, str(bad[:3])))
        cards = sorted(obj_dir.glob("*.json"))
        with_thumb = sum(1 for p in cards
                         if json.loads(p.read_text(encoding="utf-8")).get("thumb"))
        out.append(("cards reference their thumbnail",
                    with_thumb == min(n_frames, 200), f"{with_thumb}/{len(cards)} cards"))
        cal_cards = [json.loads(p.read_text(encoding="utf-8")) for p in cards[:2]]
        out.append(("cards carry calibration + reference provenance",
                    all(c["params"]["sidecar_sha256"] and c["params"]["ref_source"]
                        and c["params"]["bin_w_px"] == 2 for c in cal_cards),
                    json.dumps(cal_cards[0]["params"])[:200] if cal_cards else "none"))
    return out


CASES = [
    ("p4deep-1-calibrated-takeover", case_p4deep_calibrated_takeover),
    ("p4deep-2-no-sidecar-m1-exclusive", case_p4deep_no_sidecar_m1_exclusive),
    ("p4deep-3-defect", case_p4deep_defect),
    ("p4deep-4-stress-500", case_p4deep_stress_500),
    ("p4deep-5-thumbs", case_p4deep_thumbs_dedicated),
]
