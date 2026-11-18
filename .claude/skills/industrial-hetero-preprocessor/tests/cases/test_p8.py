"""test_p8.py — WS8 anti-forgery acceptance cases (P8 tamper matrix + P7 images-only).

P8: build one legitimate run (anchor + a single PROF source via build.py),
then re-apply the build once per tamper vector and require quality_gate.mjs
to exit 3 while naming the gate that fired (plan v1.1 §7, execution doc §4 WS8):

  T1  features _src_ts moved after ts              -> H3 (look-ahead)
  T2  raw source value edited after the build      -> H3 (source_sha256
      recompute; gate must be invoked with --raw-path)
  T3  coverage lie: coverage=0.2 kept stats_eligible=true -> H4
  T4  illegal contract column name (non-ASCII / _2) -> H8
Control: the untouched run passes with exit 0.

P7 (images-only, plan AC2): 60 synthetic frames + one index CSV, build.py
--images-only -> status ok, 07_hetero/preprocessed_images_only.csv with 60
rows, gate exit 0 (no anchor: H2/H6 paths must still walk clean).

Fixtures are generated on the fly with a fixed seed; subprocess calls use
argument lists with shell=False; nothing touches the network.
"""
from __future__ import annotations

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

SEED = 20261016
N_POS, N_SNAP = 21, 120
T0 = datetime(2026, 10, 15, 8, 0, 0)
STEP_S = 60.0


def _py() -> str:
    return str(SHARED_PY if SHARED_PY.exists() else sys.executable)


def _run(cmd: list, **kw) -> subprocess.CompletedProcess:
    """Fixed argument-list subprocess (never a shell string; zero network)."""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, timeout=300, **kw)


def _ts_strings(n=N_SNAP, t0=T0, step_s=STEP_S):
    return [(t0 + timedelta(seconds=step_s * i)).strftime("%Y-%m-%d %H:%M:%S")
            for i in range(n)]


def _write_profile(path: Path, rng_seed: int):
    """Compact wide profile (baseline + light crown + seed noise)."""
    rng = np.random.default_rng(rng_seed)
    i = np.arange(N_POS, dtype=float)
    base = 12.0 - 0.002 * i + 0.01 * (1.0 - ((i - 10.0) / 10.0) ** 2)
    data = np.vstack([base + rng.normal(0.0, 0.01, N_POS) for _ in range(N_SNAP)])
    cols = {"时间": _ts_strings()}
    for j in range(N_POS):
        cols[f"pos_{j + 1:02d}"] = data[:, j]
    pd.DataFrame(cols).to_csv(path, index=False, encoding="utf-8")


def _legit_run(root: Path):
    """Anchor + one PROF source -> build.py -> status ok. Returns (run_dir, raw)."""
    run_dir, raw = root / "run", root / "raw"
    (run_dir / "00_input").mkdir(parents=True)
    raw.mkdir()
    pd.DataFrame({"时间": _ts_strings(), "温度": np.round(
        np.random.default_rng(SEED).normal(25.0, 0.2, N_SNAP), 4)}).to_csv(
        run_dir / "00_input" / "preprocessed_data.csv", index=False, encoding="utf-8-sig")
    _write_profile(raw / "thk_p8.csv", SEED + 1)
    r = _run([_py(), SCRIPTS / "build.py", "--raw-path", raw, "--run-dir", run_dir])
    return run_dir, raw, r


def _gate(run_dir: Path, raw=None) -> subprocess.CompletedProcess:
    cmd = ["node", SCRIPTS / "quality_gate.mjs", "--run-dir", run_dir]
    if raw is not None:
        cmd += ["--raw-path", raw]
    return _run(cmd)


def _gate_json(r: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def _features_csv(run_dir: Path) -> Path:
    feats = sorted((run_dir / "07_hetero" / "features").glob("PROF-*.csv"))
    assert len(feats) == 1, f"expected one PROF features csv, got {feats}"
    return feats[0]


def _assert_built(out: list, r: subprocess.CompletedProcess) -> bool:
    ok_rc = r.returncode == 0
    out.append(("build.py exits 0 on the legitimate run", ok_rc,
                (r.stdout + r.stderr)[-300:]))
    try:
        payload = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        out.append(("build stdout parseable", False, (r.stdout + r.stderr)[-300:]))
        return False
    out.append(("build status ok", payload.get("status") == "ok", r.stdout[-200:]))
    return ok_rc and payload.get("status") == "ok"


def case_p8_control():
    """Control: the untouched legitimate run must pass the gate with exit 0."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        run_dir, raw, r = _legit_run(Path(td))
        if not _assert_built(out, r):
            return out
        g = _gate(run_dir)
        out.append(("gate exit 0 on the untampered run", g.returncode == 0,
                    (g.stdout + g.stderr)[-400:]))
        gj = _gate_json(g)
        out.append(("gate verdict ok", gj.get("verdict") == "ok", g.stdout[:200]))
        out.append(("gate counted 18 contract columns",
                    gj.get("columns") == 18, str(gj.get("columns"))))
    return out


def _tamper_case(name, tamper, expect_gate_id, use_raw_path):
    """Shared body: build a fresh legitimate run, apply one tamper, gate must
    exit 3 and name the gate that fired."""
    def case():
        out = []
        with tempfile.TemporaryDirectory() as td:
            run_dir, raw, r = _legit_run(Path(td))
            if not _assert_built(out, r):
                return out
            try:
                tamper(run_dir, raw)
            except Exception as exc:
                out.append((f"tamper {name} applied", False, repr(exc)))
                return out
            g = _gate(run_dir, raw if use_raw_path else None)
            out.append((f"gate exit 3 after {name}", g.returncode == 3,
                        f"rc={g.returncode} {(g.stdout + g.stderr)[-300:]}"))
            gj = _gate_json(g)
            fails = json.dumps(gj.get("checks", {}).get("fails", []), ensure_ascii=False)
            out.append((f"gate output names {expect_gate_id} after {name}",
                        expect_gate_id in fails or expect_gate_id in g.stdout,
                        fails[:400]))
            out.append((f"gate verdict gate_fail after {name}",
                        gj.get("verdict") == "gate_fail", g.stdout[:200]))
        return out
    case.__name__ = f"case_{name}"
    return case


def _tamper_future_src_ts(run_dir: Path, raw: Path):
    """T1: move one features row's _src_ts one step AFTER its ts (look-ahead)."""
    p = _features_csv(run_dir)
    lines = p.read_text(encoding="utf-8-sig").splitlines()
    header = lines[0].split(",")
    i_ts, i_src = header.index("ts"), header.index("_src_ts")
    cells = lines[1].split(",")
    ts = datetime.strptime(cells[i_ts], "%Y-%m-%d %H:%M:%S")
    cells[i_src] = (ts + timedelta(seconds=STEP_S)).strftime("%Y-%m-%d %H:%M:%S")
    lines[1] = ",".join(cells)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _tamper_source_edit(run_dir: Path, raw: Path):
    """T2: edit one value in the raw source AFTER the build (provenance break).
    The gate only recomputes source_sha256 when --raw-path is supplied."""
    p = raw / "thk_p8.csv"
    lines = p.read_text(encoding="utf-8").splitlines()
    cells = lines[1].split(",")
    cells[-1] = f"{float(cells[-1]) + 5.0:.6f}"
    lines[1] = ",".join(cells)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _tamper_coverage_lie(run_dir: Path, raw: Path):
    """T3: claim coverage 0.2 while keeping stats_eligible=true (H4 is the
    contract self-consistency check: eligible requires coverage >= 0.5)."""
    p = run_dir / "07_hetero" / "column_contract.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["columns"][0]["coverage"] = 0.2
    doc["columns"][0]["sparse"] = True          # keep the lie surgical: only the
    # stats_eligible-vs-coverage rule must fire, not the sparse-vs-coverage one
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tamper_bad_name(run_dir: Path, raw: Path):
    """T4: smuggle illegal column names into the contract (non-ASCII label and
    the E-1 dedup suffix _2 — both violate the frozen I3 naming contract)."""
    p = run_dir / "07_hetero" / "column_contract.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    smuggle_a = dict(doc["columns"][0])
    smuggle_a["column"] = "HX-PROF-THKP8-下线-MEAN"
    smuggle_b = dict(doc["columns"][0])
    smuggle_b["column"] = "HX-PROF-THKP8-MEAN_2"
    doc["columns"] = doc["columns"] + [smuggle_a, smuggle_b]
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


case_p8_t1_future_src_ts = _tamper_case(
    "p8-t1-future-src-ts", _tamper_future_src_ts, "H3", use_raw_path=False)
case_p8_t2_source_edit = _tamper_case(
    "p8-t2-source-edit", _tamper_source_edit, "H3", use_raw_path=True)
case_p8_t3_coverage_lie = _tamper_case(
    "p8-t3-coverage-lie", _tamper_coverage_lie, "H4", use_raw_path=False)
case_p8_t4_bad_name = _tamper_case(
    "p8-t4-bad-name", _tamper_bad_name, "H8", use_raw_path=False)


def case_p7_images_only():
    """P7: images-only end-to-end — no anchor, no process tags; the derived
    image-feature series is the analysis table and the gate walks clean."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        run_dir, raw = root / "run", root / "raw"
        frames = raw / "frames"
        frames.mkdir(parents=True)

        from PIL import Image

        n = 60
        rng = np.random.default_rng(SEED + 7)
        t0 = datetime(2026, 10, 15, 9, 0, 0)
        index_rows = []
        for k in range(n):
            g = np.zeros((24, 32), dtype=np.uint8)
            g += (np.arange(32, dtype=np.uint8) * 3)[None, :]        # gradient
            g += (rng.normal(0, 6, (24, 32))).astype(np.int16).clip(-20, 20).astype(np.uint8)
            Image.fromarray(g, mode="L").save(frames / f"frame_{k:04d}.png")
            ts = (t0 + timedelta(seconds=300 * k)).strftime("%Y-%m-%d %H:%M:%S")
            index_rows.append({"时间": ts, "image_path": f"frames/frame_{k:04d}.png"})
        pd.DataFrame(index_rows).to_csv(raw / "img_index.csv", index=False, encoding="utf-8")

        r = _run([_py(), SCRIPTS / "build.py", "--images-only",
                  "--raw-path", raw, "--run-dir", run_dir])
        out.append(("images-only build exits 0", r.returncode == 0,
                    (r.stdout + r.stderr)[-300:]))
        try:
            payload = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return out + [("images-only stdout parseable", False, (r.stdout + r.stderr)[-300:])]
        out.append(("images-only status ok", payload.get("status") == "ok", r.stdout[-200:]))

        joined = run_dir / "07_hetero" / "preprocessed_images_only.csv"
        out.append(("preprocessed_images_only.csv written", joined.exists(), str(joined)))
        if joined.exists():
            df = pd.read_csv(joined)
            out.append(("images-only table has 60 rows", len(df) == 60, f"rows={len(df)}"))
            hx = [c for c in df.columns if c.startswith("HX-IMG-")]
            out.append(("images-only table carries the 7 IMG columns",
                        len(hx) == 7, str(hx)))
        feats = sorted((run_dir / "07_hetero" / "features").glob("IMG-*.csv"))
        out.append(("features/IMG-<slug>.csv written", len(feats) == 1,
                    str([f.name for f in feats])))

        man = json.loads((run_dir / "07_hetero" / "hetero_manifest.json").read_text(encoding="utf-8"))
        out.append(("images-only manifest anchor is null",
                    man["anchor"]["path"] is None and man["h7_guard"]["anchor_sha256"] is None,
                    json.dumps(man["anchor"])))
        out.append(("images-only manifest notes no process tags",
                    any("images-only" in s for s in man.get("notes", [])),
                    str(man.get("notes"))))

        g = _gate(run_dir, raw)
        out.append(("gate exit 0 on the images-only run (with --raw-path)",
                    g.returncode == 0, (g.stdout + g.stderr)[-400:]))
        gj = _gate_json(g)
        out.append(("images-only gate verdict ok", gj.get("verdict") == "ok", g.stdout[:200]))
    return out


def case_contract_registry():
    """F-check: the four hetero entries exist in cross_skill_contracts.json and
    each carries id/primary_path/producer/consumer."""
    out = []
    path = REPO / ".claude" / "shared" / "schemas" / "cross_skill_contracts.json"
    out.append(("cross_skill_contracts.json exists", path.exists(), str(path)))
    if not path.exists():
        return out
    doc = json.loads(path.read_text(encoding="utf-8"))
    ids = {c.get("id") for c in doc.get("contracts", [])}
    expected = ["hetero_contract_to_ontology", "hetero_features_to_dataprocessor",
                "hetero_annotations_to_tuning_memory", "hetero_contract_to_optimizer"]
    for cid in expected:
        out.append((f"contract {cid} present", cid in ids,
                    str(sorted(i for i in ids if i and i.startswith("hetero")))))
    for c in doc.get("contracts", []):
        if c.get("id") not in expected:
            continue
        for field in ("primary_path", "producer", "consumer"):
            out.append((f"contract {c['id']} has non-empty {field}",
                        bool(str(c.get(field, "")).strip()), str(c.get(field))))
    return out


CASES = [
    ("p8-control", case_p8_control),
    ("p8-t1-future-src-ts", case_p8_t1_future_src_ts),
    ("p8-t2-source-edit", case_p8_t2_source_edit),
    ("p8-t3-coverage-lie", case_p8_t3_coverage_lie),
    ("p8-t4-bad-name", case_p8_t4_bad_name),
    ("p7-images-only", case_p7_images_only),
    ("p8-contract-registry", case_contract_registry),
]
