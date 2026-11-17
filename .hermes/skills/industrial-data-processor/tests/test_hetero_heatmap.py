#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_hetero_heatmap.py — WS7 (time x position heatmap branch) acceptance.

Covers the WS7 acceptance items from
.omc/plans/hetero-data-preprocessing-skill-v1-execution.md (§4 WS7) and the
chart-row of plan §9 AC3③:

 1. `adaptive_charts.py RUN_DIR` renders 03_figures/fig_hetero_profile_heatmap.png
    (>0 bytes) from 07_hetero/features/PROF-*.csv — WITHOUT any anchor frame
    chart input (no 02_processed/cleaned_data.csv, no --data)
 2. the appended plot_manifest.json is plot_manifest_schema.json-valid
    (node validate.mjs exits 0; entry carries figure_type/priority/metadata)
    and the fixture column_contract.json passes column_contract_schema.json
 3. generate_vlm_manifest.py includes the heatmap in vlm_input_manifest.json
    with vlm_priority MANDATORY (the filename contains "heatmap", which its
    default heuristic sends to NOT_FOR_VLM — the explicit producer
    designation in the manifest entry must override that)
 4. a RUN_DIR without 07_hetero features behaves exactly as mainline:
    no heatmap PNG, no manifest entry, no metadata block, unchanged exit
    code and stdout (this is the red-line regression assertion)
 5. plot_verification.py PASSES on the heatmap manifest entry

Fixture: generated on the fly into a temp dir with a fixed seed — nothing
committed. Run standalone:

    .claude/shared/scripts/.venv/Scripts/python.exe tests/test_hetero_heatmap.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent          # .../industrial-data-processor/tests
SKILL = HERE.parent                             # .../industrial-data-processor
REPO = HERE.parents[3]                          # repo root (.claude/skills/<skill>/tests -> up 3)
SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "Scripts" / "python.exe"
if not SHARED_PY.exists():
    SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "bin" / "python"
PY = str(SHARED_PY if SHARED_PY.exists() else sys.executable)

SEED = 20261016


def _run(cmd, timeout=300):
    """Run a fixed argument-list command (never a shell string)."""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, timeout=timeout)


def _validate_with_node(schema_rel, data_path):
    """node validate.mjs <schema> <data> -> (returncode, report_dict|None)."""
    r = _run(["node", REPO / ".claude" / "shared" / "scripts" / "validate.mjs",
              REPO / schema_rel, data_path])
    try:
        return r.returncode, json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.returncode, None


# ---------------------------------------------------------------- fixtures --

def write_anchor(run_dir, n_rows=432, cadence_min=10):
    """00_input/preprocessed_data.csv — 10 min x 3 days anchor (E-1 output)."""
    rng = np.random.default_rng(SEED)
    t0 = datetime(2026, 10, 1, 0, 0, 0)
    ts = [t0 + timedelta(minutes=cadence_min * i) for i in range(n_rows)]
    df = pd.DataFrame({
        "ts": [t.strftime("%Y-%m-%d %H:%M:%S") for t in ts],
        "temp_c": np.round(78.0 + 2.0 * np.sin(np.arange(n_rows) / 30.0) + rng.normal(0, 0.1, n_rows), 4),
        "press_kpa": np.round(315.0 + rng.normal(0, 0.8, n_rows), 4),
        "motor_a": np.round(42.0 + rng.normal(0, 0.5, n_rows), 4),
    })
    p = run_dir / "00_input" / "preprocessed_data.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p


def write_prof_features(run_dir, stem="PROF-DEMO", n_snap=300, n_pos=21,
                        cadence_s=120, edge_bump=True):
    """07_hetero/features/<STEM>.csv — ts + bookkeeping + pos_01..pos_N matrix.

    Known injected effect (for human inspection only, the chart branch is not
    asserted on physics): outer 3 positions gain +0.8 after snapshot 120."""
    rng = np.random.default_rng(SEED + 1)
    t0 = datetime(2026, 10, 1, 2, 0, 0)
    idx = np.arange(n_snap)
    snap_time = np.round(rng.normal(0, 0.02, n_snap), 4)  # capture jitter
    cols = {"ts": [(t0 + timedelta(seconds=cadence_s * int(i))).strftime("%Y-%m-%d %H:%M:%S")
                   for i in idx],
            "_src_ts": [(t0 + timedelta(seconds=cadence_s * int(i))).strftime("%Y-%m-%d %H:%M:%S")
                        for i in idx],
            "n_inputs": np.full(n_snap, n_pos, dtype=int)}
    for j in range(n_pos):
        base = 100.0 + 0.05 * j + 0.4 * np.sin(idx / 40.0) + snap_time
        if edge_bump and j >= n_pos - 3:
            base = base + np.where(idx >= 120, 0.8, 0.0)
        cols["pos_%02d" % (j + 1)] = np.round(base + rng.normal(0, 0.3, n_snap), 4)
    p = run_dir / "07_hetero" / "features" / ("%s.csv" % stem)
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(cols).to_csv(p, index=False)
    return p


def write_contract(run_dir, stem="PROF-DEMO", unit="um"):
    """07_hetero/column_contract.json — minimal contract, valid per
    column_contract_schema.json (every required field present)."""
    contract = {
        "contract_version": "hetero-features/1.1",
        "generated_at": "2026-10-16T00:00:00Z",
        "anchor_sha256": None,
        "columns": [{
            "column": "HX-%s-MEAN" % stem,
            "shape": "PROF",
            "source_id": stem,
            "source_path": "raw/%s.csv" % stem.lower(),
            "source_sha256": "0" * 64,
            "unit": unit,
            "role": "target_candidate",
            "physical_meaning": "Cross-profile mean thickness at each snapshot",
            "formula": "mean(pos_01..pos_N)",
            "physics_basis": "aggregate of directly measured thickness profile",
            "evidence_level": 1,
            "evidence_level_basis": "direct measurement aggregation (L1)",
            "method": "arithmetic mean",
            "method_version": "1.0",
            "n_inputs": 21,
            "coverage": 1.0,
            "effective_n": 21,
            "sparse": False,
            "stats_eligible": True,
            "cadence_s": 120.0,
            "ts_source": "dcs",
            "tz": None,
            "clock_offset_s": None,
            "tag_cn": "剖面均值",
            "tag_en": "profile mean",
            "model_derived": False,
            "_src_ts": "anchor",
            "insufficient_data": False,
        }],
    }
    p = run_dir / "07_hetero" / "column_contract.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(contract, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def build_hetero_only_dir(root):
    """Fixture RUN_DIR: anchor + hetero PROF source + contract, NO cleaned data
    (exercises the anchor-frame-independent hetero-only path)."""
    run_dir = Path(root) / "run_hetero"
    run_dir.mkdir(parents=True, exist_ok=True)
    write_anchor(run_dir)
    write_prof_features(run_dir)
    write_contract(run_dir)
    return run_dir


# ------------------------------------------------------------------- cases --

def case_hetero_only_render_and_manifest():
    """AC-1 + AC-2: bare `adaptive_charts.py RUN_DIR` renders the heatmap and
    appends a schema-compliant manifest entry (+ top-level metadata)."""
    out = []
    with tempfile.TemporaryDirectory(prefix="ws7_") as tmp:
        run_dir = build_hetero_only_dir(tmp)
        png = run_dir / "03_figures" / "fig_hetero_profile_heatmap.png"
        manifest_p = run_dir / "03_figures" / "plot_manifest.json"

        r = _run([PY, SKILL / "scripts" / "adaptive_charts.py", run_dir])
        out.append(("AC1 adaptive_charts exits 0 on hetero-only run", r.returncode == 0,
                    "exit=%s stderr=%s" % (r.returncode, r.stderr.strip()[:200])))
        out.append(("AC1 heatmap PNG generated", png.is_file(), str(png)))
        size = png.stat().st_size if png.is_file() else 0
        out.append(("AC1 heatmap PNG size > 0 (and >5KB gate)", size > 5120, "%d bytes" % size))

        plan_p = run_dir / "03_figures" / "adaptive_chart_plan.json"
        plan = json.loads(plan_p.read_text(encoding="utf-8")) if plan_p.is_file() else {}
        out.append(("AC1 plan records hetero branch decision",
                    "hetero_profile_heatmaps" in plan, str(list(plan.keys()))))

        manifest = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.is_file() else {}
        plots = manifest.get("plots", [])
        out.append(("AC2 manifest has exactly 1 plot entry", len(plots) == 1, str(len(plots))))
        e = plots[0] if plots else {}
        out.append(("AC2 entry filename", e.get("filename") == "fig_hetero_profile_heatmap.png",
                    str(e.get("filename"))))
        out.append(("AC2 entry figure_type is schema enum value", e.get("figure_type") == "heatmap",
                    str(e.get("figure_type"))))
        out.append(("AC2 entry priority is int >= 1",
                    isinstance(e.get("priority"), int) and e.get("priority", 0) >= 1,
                    repr(e.get("priority"))))
        out.append(("AC2 entry chart_type marks profile heatmap",
                    e.get("chart_type") == "profile_heatmap", str(e.get("chart_type"))))
        out.append(("AC2 entry source is this script", e.get("source") == "adaptive_charts.py",
                    str(e.get("source"))))
        out.append(("AC2 entry has explicit vlm_priority",
                    e.get("vlm_priority") in ("CRITICAL", "MANDATORY"), str(e.get("vlm_priority"))))
        out.append(("AC2 entry carries VLM producer designation (plot_type vlm_*)",
                    str(e.get("plot_type", "")).startswith("vlm_"), str(e.get("plot_type"))))
        out.append(("AC2 entry has path for plot_verification",
                    e.get("path") == "03_figures/fig_hetero_profile_heatmap.png", str(e.get("path"))))
        md = manifest.get("metadata")
        out.append(("AC2 manifest has top-level metadata",
                    isinstance(md, dict)
                    and isinstance(md.get("total_plots"), int)
                    and bool(md.get("generated_by"))
                    and bool(md.get("generation_timestamp")),
                    json.dumps(md, ensure_ascii=False) if isinstance(md, dict) else str(md)))

        rc, report = _validate_with_node(".claude/shared/schemas/plot_manifest_schema.json", manifest_p)
        out.append(("AC2 plot_manifest passes plot_manifest_schema.json (validate.mjs exit 0)",
                    rc == 0 and bool(report and report.get("valid")),
                    json.dumps((report or {}).get("errors", []))[:300]))
    return out


def case_contract_schema():
    """AC-2 (fixture hygiene): the minimal column contract passes its schema."""
    out = []
    with tempfile.TemporaryDirectory(prefix="ws7c_") as tmp:
        run_dir = Path(tmp) / "run"
        run_dir.mkdir(parents=True)
        p = write_contract(run_dir)
        rc, report = _validate_with_node(
            ".claude/skills/industrial-hetero-preprocessor/schemas/column_contract_schema.json", p)
        out.append(("fixture column_contract passes column_contract_schema.json",
                    rc == 0 and bool(report and report.get("valid")),
                    json.dumps((report or {}).get("errors", []))[:300]))
    return out


def case_vlm_manifest_inclusion():
    """AC-3: generate_vlm_manifest.py puts the heatmap into the VLM input list
    with priority MANDATORY (not NOT_FOR_VLM despite the filename)."""
    out = []
    with tempfile.TemporaryDirectory(prefix="ws7_") as tmp:
        run_dir = build_hetero_only_dir(Path(tmp))
        r1 = _run([PY, SKILL / "scripts" / "adaptive_charts.py", run_dir])
        out.append(("setup: adaptive_charts exit 0", r1.returncode == 0, r1.stderr.strip()[:200]))
        r2 = _run([PY, SKILL / "scripts" / "generate_vlm_manifest.py", run_dir])
        out.append(("AC3 generate_vlm_manifest exits 0", r2.returncode == 0,
                    (r2.stdout + r2.stderr).strip()[:200]))
        out.append(("AC3 generate_vlm_manifest stdout lists the heatmap as MANDATORY",
                    "fig_hetero_profile_heatmap.png" in r2.stdout and "[MANDATORY]" in r2.stdout,
                    r2.stdout.strip()[:300]))
        vlm_p = run_dir / "03_figures" / "vlm_input_manifest.json"
        vlm = json.loads(vlm_p.read_text(encoding="utf-8")) if vlm_p.is_file() else {}
        imgs = vlm.get("vlm_images", [])
        hit = [i for i in imgs if i.get("filename") == "fig_hetero_profile_heatmap.png"]
        out.append(("AC3 VLM input manifest contains the heatmap", len(hit) == 1,
                    "vlm_images=%d" % len(imgs)))
        if hit:
            out.append(("AC3 VLM priority is MANDATORY", hit[0].get("vlm_priority") == "MANDATORY",
                        str(hit[0].get("vlm_priority"))))
            out.append(("AC3 VLM read order is 1 (main reading sequence)",
                        hit[0].get("vlm_read_order") == 1, str(hit[0].get("vlm_read_order"))))
        out.append(("AC3 excluded count does not include the heatmap",
                    vlm.get("total_images_for_vlm", 0) >= 1, str(vlm.get("total_images_for_vlm"))))
    return out


def case_no_hetero_mainline_unchanged():
    """AC-4 (red line): without 07_hetero features the behavior is mainline.

    (a) bare dir (no data file) -> exit 2 with the exact mainline line,
        no heatmap, no manifest;
    (b) dir with cleaned data -> normal charts, manifest WITHOUT metadata and
        WITHOUT any hetero entry (legacy writer untouched);
    (c) dir with 07_hetero/ but empty features/ (always-marker, no sources) ->
        identical to (b)."""
    out = []
    not_applicable = "[adaptive] NOT_APPLICABLE: no data file (checked --data, 02_processed/cleaned_data.csv)"

    with tempfile.TemporaryDirectory(prefix="ws7n_") as tmp:
        # (a) bare dir
        bare = Path(tmp) / "bare"
        (bare / "00_input").mkdir(parents=True)
        shutil.copy(write_anchor(Path(tmp) / "anchor_seed"), bare / "00_input" / "preprocessed_data.csv")
        r = _run([PY, SKILL / "scripts" / "adaptive_charts.py", bare])
        out.append(("AC4a no-hetero bare run exits 2 (unchanged)", r.returncode == 2, str(r.returncode)))
        out.append(("AC4a stdout is exactly the mainline NOT_APPLICABLE line",
                    r.stdout.strip() == not_applicable, repr(r.stdout.strip()[:200])))
        out.append(("AC4a no heatmap PNG", not (bare / "03_figures" / "fig_hetero_profile_heatmap.png").is_file(), ""))
        out.append(("AC4a no plot_manifest.json",
                    not (bare / "03_figures" / "plot_manifest.json").is_file(), ""))

        # (b) mainline with cleaned data
        withdata = Path(tmp) / "withdata"
        (withdata / "02_processed").mkdir(parents=True)
        shutil.copy(Path(tmp) / "anchor_seed" / "00_input" / "preprocessed_data.csv",
                    withdata / "02_processed" / "cleaned_data.csv")
        r = _run([PY, SKILL / "scripts" / "adaptive_charts.py", withdata])
        out.append(("AC4b mainline with-data run exits 0", r.returncode == 0,
                    "exit=%s %s" % (r.returncode, (r.stdout + r.stderr).strip()[:200])))
        out.append(("AC4b stdout carries no hetero lines", "hetero" not in r.stdout.lower(),
                    repr(r.stdout.strip()[:200])))
        mp = withdata / "03_figures" / "plot_manifest.json"
        manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
        names = [p.get("filename", "") for p in manifest.get("plots", [])]
        out.append(("AC4b manifest has no hetero entry",
                    not any("hetero" in n for n in names), str(names)))
        out.append(("AC4b legacy manifest has no metadata block (writer untouched)",
                    "metadata" not in manifest, str(list(manifest.keys()))))

        # (c) 07_hetero exists but features/ empty (always-marker, no sources)
        marker = Path(tmp) / "marker"
        (marker / "02_processed").mkdir(parents=True)
        shutil.copy(Path(tmp) / "anchor_seed" / "00_input" / "preprocessed_data.csv",
                    marker / "02_processed" / "cleaned_data.csv")
        (marker / "07_hetero" / "features").mkdir(parents=True)
        (marker / "07_hetero" / "hetero_manifest.json").write_text(
            json.dumps({"status": "no_hetero_sources"}), encoding="utf-8")
        r = _run([PY, SKILL / "scripts" / "adaptive_charts.py", marker])
        out.append(("AC4c always-marker-only run exits 0 (mainline)", r.returncode == 0,
                    "exit=%s" % r.returncode))
        out.append(("AC4c stdout carries no hetero lines", "hetero" not in r.stdout.lower(),
                    repr(r.stdout.strip()[:200])))
        mp = marker / "03_figures" / "plot_manifest.json"
        manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
        out.append(("AC4c manifest has no metadata block",
                    "metadata" not in manifest, str(list(manifest.keys()))))
        out.append(("AC4c manifest identical to (b) entry set",
                    [p.get("filename") for p in manifest.get("plots", [])] == names, ""))
    return out


def case_plot_verification():
    """AC-5: plot_verification.py PASSES on the heatmap manifest entry."""
    out = []
    with tempfile.TemporaryDirectory(prefix="ws7_") as tmp:
        run_dir = build_hetero_only_dir(Path(tmp))
        r1 = _run([PY, SKILL / "scripts" / "adaptive_charts.py", run_dir])
        out.append(("setup: adaptive_charts exit 0", r1.returncode == 0, r1.stderr.strip()[:200]))
        r = _run([PY, SKILL / "scripts" / "plot_verification.py", run_dir])
        out.append(("AC5 plot_verification exits 0", r.returncode == 0,
                    (r.stdout + r.stderr).strip()[:300]))
        out.append(("AC5 plot_verification reports PASSED",
                    "PLOT_VERIFICATION_PASSED" in r.stdout, r.stdout.strip()[:200]))
    return out


def case_multi_source_naming():
    """Branch design: one heatmap PER PROF source; single source keeps the bare
    filename, multiple sources get source-id-suffixed filenames."""
    out = []
    with tempfile.TemporaryDirectory(prefix="ws7m_") as tmp:
        run_dir = Path(tmp) / "run"
        run_dir.mkdir(parents=True)
        write_anchor(run_dir)
        write_prof_features(run_dir, stem="PROF-DEMO")
        write_prof_features(run_dir, stem="PROF-GAUGE", n_snap=200, n_pos=9)
        write_contract(run_dir, stem="PROF-DEMO")
        r = _run([PY, SKILL / "scripts" / "adaptive_charts.py", run_dir])
        out.append(("multi-source run exits 0", r.returncode == 0,
                    (r.stdout + r.stderr).strip()[:200]))
        f1 = run_dir / "03_figures" / "fig_hetero_profile_heatmap_PROF-DEMO.png"
        f2 = run_dir / "03_figures" / "fig_hetero_profile_heatmap_PROF-GAUGE.png"
        out.append(("multi-source: per-source suffixed PNGs exist",
                    f1.is_file() and f2.is_file() and f1.stat().st_size > 0 and f2.stat().st_size > 0,
                    "%s/%s" % (f1.stat().st_size if f1.is_file() else -1,
                               f2.stat().st_size if f2.is_file() else -1)))
        mp = run_dir / "03_figures" / "plot_manifest.json"
        manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
        entries = [p for p in manifest.get("plots", []) if p.get("chart_type") == "profile_heatmap"]
        srcs = sorted(e.get("source_id", "") for e in entries)
        out.append(("multi-source: one manifest entry per source",
                    srcs == ["PROF-DEMO", "PROF-GAUGE"], str(srcs)))
        out.append(("multi-source: manifest metadata total_plots matches",
                    manifest.get("metadata", {}).get("total_plots") == len(manifest.get("plots", [])),
                    str(manifest.get("metadata", {}).get("total_plots"))))
        rc, report = _validate_with_node(".claude/shared/schemas/plot_manifest_schema.json", mp)
        out.append(("multi-source: manifest still schema-valid",
                    rc == 0 and bool(report and report.get("valid")),
                    json.dumps((report or {}).get("errors", []))[:300]))
    return out


# ------------------------------------------------------------------ runner --

CASES = [
    ("hetero-only render + manifest schema", case_hetero_only_render_and_manifest),
    ("fixture contract schema", case_contract_schema),
    ("VLM manifest inclusion (MANDATORY)", case_vlm_manifest_inclusion),
    ("no-hetero mainline unchanged (red line)", case_no_hetero_mainline_unchanged),
    ("plot_verification PASS", case_plot_verification),
    ("multi-source naming", case_multi_source_naming),
]


def main():
    any_fail = False
    for name, fn in CASES:
        print("== case: %s" % name)
        try:
            results = fn()
        except Exception as exc:  # noqa: BLE001 — a crashed case is a failed case
            print("   CRASH: %r" % exc)
            any_fail = True
            continue
        for assertion, ok, detail in results:
            print("   [%s] %s%s" % ("PASS" if ok else "FAIL", assertion,
                                    (" — %s" % detail) if detail else ""))
            if not ok:
                any_fail = True
    print("\nWS7 heatmap test: %s" % ("FAIL" if any_fail else "ALL PASS"))
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
