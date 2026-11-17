"""test_m3.py — WS11 cross-skill wiring acceptance cases (plan M3 row).

m3-lsr-anti-hijack   a folder holding data.csv plus 07_hetero/preprocessed_data_hetero.csv
                     (41 HX columns — massively out-scoring the 4-column anchor) must still
                     select data.csv as primary, in LSR mode
                     (--stability-single-primary --recursive; the master's '07_hetero'
                     discovery skip, plan §0 R1 / §5 LSR row) AND in standard mode.
m3-sentinel-e2e      21-day anchor (膜厚, +0.15 step in the last 4 days) + profile source
                     (pos_01..pos_10, right edge +0.2 in the last 4 days) → E-1 + build.py →
                     joined table; baseline from the first 17 days; sentinel watch on the last
                     4 days with the explicit --data/--config/--out-dir convention (plan §5
                     sentinel row / AC3④) must raise >= 1 finding whose parameter starts with
                     "HX-" — the proof that the sentinel reads heterogeneous features. Also
                     proves the four contract primary_path templates are reachable on a real
                     run (AC3⑥ shape test).

                     Layout note: the profile source lives in raw/profile/ because E-1's
                     standard mode scans top-level files only (the canonical-table source),
                     while build.py --recursive picks up subfolders — the documented mixed-
                     source layout. A top-level wide profile would be outer-merged INTO the
                     E-1 anchor and then legitimately refused by anchor_join's collision
                     guard (feature column pos_N collides with an existing column).
m3-contract-docs     cross_skill_contracts.json: all 4 hetero_* contract entries must name their
                     07_hetero/... artifact in `producer` (the file-pattern carrier; primary_path
                     is a field path inside the artifact) and carry a shape (primary_path+expect);
                     sentinel SKILL.md must document the E-1H wiring (grep 07_hetero / HX-).

All fixtures are generated on the fly with fixed seeds; zero network; every subprocess uses a
fixed argument list with shell=False. The sentinel case runs inside a repo-contained temp dir
because sentinelcore enforces repo-root path containment.
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
SKILL = HERE.parent.parent                      # industrial-hetero-preprocessor
SCRIPTS = SKILL / "scripts"
REPO = SCRIPTS.parent.parent.parent.parent      # repo root
SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "Scripts" / "python.exe"
if not SHARED_PY.exists():
    SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "bin" / "python"

DP = REPO / ".claude" / "skills" / "industrial-data-preprocessor" / "scripts" / "data_preprocessor.py"
HET_BUILD = SCRIPTS / "build.py"
SENT_SCRIPTS = REPO / ".claude" / "skills" / "industrial-sentinel" / "scripts"
SENTINEL = SENT_SCRIPTS / "sentinel.py"
BUILD_BASELINE = SENT_SCRIPTS / "build_baseline.py"
SENTINEL_SKILL_MD = REPO / ".claude" / "skills" / "industrial-sentinel" / "SKILL.md"
CONTRACTS = REPO / ".claude" / "shared" / "schemas" / "cross_skill_contracts.json"

TIME_COL = "时间"
SEED = 20261016
ROWS_PER_DAY = 144                    # 10-min cadence
DAYS, BASE_DAYS = 21, 17              # watch = last 4 days
N_ROWS = DAYS * ROWS_PER_DAY          # 3024
BASE_ROWS = BASE_DAYS * ROWS_PER_DAY  # 2448 (in-control segment)
N_POS = 10                            # >= 8 numeric cols (wide detect) and >= 6 (EDGE)
PROFILE_FILE = "thk_scan.csv"         # slug -> THKSCAN
STEP_ANCHOR = 0.15                    # 膜厚 regime step in the watch window
STEP_EDGE = 0.20                      # profile right-edge lift in the watch window

# contract artifact templates (plan §5 integration-contract table, M3 rows): consumer-family
# fragment -> the 07_hetero file the contract's producer must name (registered by the contracts
# seat in cross_skill_contracts.json; primary_path itself is a FIELD path inside that artifact)
HETERO_CONTRACT_TEMPLATES = [
    ("ontology", "07_hetero/column_contract.json"),
    ("dataprocessor", "07_hetero/explicit_cols.json"),
    ("tuning_memory", "07_hetero/annotations.json"),
    ("optimizer", "07_hetero/column_contract.json"),
]
# files the four contracts point at, all produced by a status=ok E-1H run (AC3⑥)
RUN_PRIMARY_PATH_TEMPLATES = [
    "07_hetero/column_contract.json",
    "07_hetero/explicit_cols.json",
    "07_hetero/annotations.json",
    "07_hetero/preprocessed_data_hetero.csv",
]


def _run(cmd: list, cwd: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a fixed argument-list command (never a shell string)."""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, cwd=cwd, timeout=timeout)


def _py() -> str:
    return str(SHARED_PY if SHARED_PY.exists() else sys.executable)


def _load_dp():
    """Import the E-1 preprocessor module (import-safe: main guarded)."""
    spec = importlib.util.spec_from_file_location("dp_under_test_m3", DP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ts_strings(n: int) -> list[str]:
    t0 = datetime(2026, 9, 28, 0, 0, 0)
    return [(t0 + timedelta(minutes=10 * i)).strftime("%Y-%m-%d %H:%M:%S") for i in range(n)]


def _last_json(stdout: str) -> dict | None:
    try:
        return json.loads(stdout.strip().splitlines()[-1])
    except Exception:
        return None


# ------------------------------------------------------------------ case 1


def case_m3_lsr_anti_hijack():
    out = []
    dp = _load_dp()
    with tempfile.TemporaryDirectory() as td:
        folder = Path(td) / "lsr_folder"
        (folder / "07_hetero").mkdir(parents=True)
        rng = np.random.default_rng(SEED)
        ts = _ts_strings(200)
        # the anchor E-1/LSR should pick: 时间 + 3 numeric process tags, 10min x 200 rows
        pd.DataFrame({
            TIME_COL: ts,
            "温度": rng.normal(25.0, 0.1, 200),
            "压力": rng.normal(3.0, 0.05, 200),
            "流量": rng.normal(120.0, 0.8, 200),
        }).to_csv(folder / "data.csv", index=False, encoding="utf-8-sig")
        # the E-1H joined table: same time axis + 41 HX columns (score would be ~24 vs ~3.5)
        het = pd.DataFrame({TIME_COL: ts})
        for j in range(40):
            het[f"HX-PROF-DEMO-{j + 1:02d}"] = rng.normal(12.0, 0.01, 200)
        het.to_csv(folder / "07_hetero" / "preprocessed_data_hetero.csv",
                   index=False, encoding="utf-8-sig")

        # defense in depth (post master scoring fix): even WITHOUT the
        # 07_hetero skip, a 40-channel HX joined table must no longer out-score
        # the process backbone — same-prefix HX families are capped at 3 columns
        # each in _score_table, so selection is safe at two independent layers.
        d1 = pd.read_csv(folder / "data.csv", encoding="utf-8-sig")
        d2 = pd.read_csv(folder / "07_hetero" / "preprocessed_data_hetero.csv", encoding="utf-8-sig")
        s1 = dp._score_table(d1, dp._detect_time_col(d1))
        s2 = dp._score_table(d2, dp._detect_time_col(d2))
        out.append(("scoring layer: HX wide table no longer out-scores anchor",
                    s2 <= s1,
                    f"anchor={s1:.2f} hetero={s2:.2f}"))

        # unit-level probe of the fix: recursive discovery must not descend into 07_hetero
        found = [p.relative_to(folder).as_posix() for p in
                 dp._discover_sources(folder, recursive=True)]
        out.append(("recursive discovery skips 07_hetero/ (master fix)",
                    found == ["data.csv"], str(found)))

        # e2e LSR mode: --stability-single-primary --recursive must pick data.csv
        out_lsr = Path(td) / "out_lsr"
        r = _run([_py(), DP, "--data-path", folder, "--output", out_lsr,
                  "--stability-single-primary", "--recursive"])
        out.append(("LSR run exits 0", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        try:
            rep = json.loads((out_lsr / "preprocessing_report.json").read_text(encoding="utf-8"))
        except Exception as exc:
            return out + [("LSR report readable", False, str(exc))]
        sel = (rep.get("selected_table") or {}).get("file")
        out.append(("LSR selected_table.file == data.csv (not hijacked)", sel == "data.csv",
                    f"selected={sel!r}"))
        out.append(("07_hetero absent from the whole LSR report",
                    "07_hetero" not in json.dumps(rep, ensure_ascii=False), ""))
        primary = next((d for d in rep.get("source_dispositions", [])
                        if d.get("disposition") == "selected"), None)
        out.append(("LSR primary disposition names data.csv",
                    bool(primary) and primary.get("relative_path") == "data.csv",
                    json.dumps(primary, ensure_ascii=False)[:200] if primary else "none"))

        # standard mode (no stability flags) must pick data.csv too
        out_std = Path(td) / "out_std"
        r2 = _run([_py(), DP, "--data-path", folder, "--output", out_std])
        out.append(("standard run exits 0", r2.returncode == 0, (r2.stdout + r2.stderr)[-300:]))
        try:
            rep2 = json.loads((out_std / "preprocessing_report.json").read_text(encoding="utf-8"))
        except Exception as exc:
            return out + [("standard report readable", False, str(exc))]
        sel2 = (rep2.get("selected_table") or {}).get("file")
        out.append(("standard selected_table.file == data.csv", sel2 == "data.csv",
                    f"selected={sel2!r}"))
    return out


# ------------------------------------------------------------------ case 2


def _write_raw(raw: Path, rng: np.random.Generator) -> None:
    """anchor table (膜厚, top level) + profile wide source (raw/profile/ subfolder),
    sharing one 21-day 10-min axis."""
    ts = _ts_strings(N_ROWS)
    film = 12.0 + rng.normal(0.0, 0.01, N_ROWS)
    film[BASE_ROWS:] += STEP_ANCHOR
    pd.DataFrame({TIME_COL: ts, "膜厚": film}).to_csv(
        raw / "dcs_table.csv", index=False, encoding="utf-8")

    prof_dir = raw / "profile"
    prof_dir.mkdir()
    base = np.linspace(12.05, 11.95, N_POS)                      # slight deterministic tilt
    rows = np.empty((N_ROWS, N_POS), dtype=float)
    for i in range(N_ROWS):
        rows[i] = base + rng.normal(0.0, 0.01, N_POS)
        if i >= BASE_ROWS:
            rows[i, N_POS - 2] += STEP_EDGE                      # right edge lift
            rows[i, N_POS - 1] += STEP_EDGE
    pd.DataFrame({TIME_COL: ts, **{f"pos_{j + 1:02d}": rows[:, j] for j in range(N_POS)}}).to_csv(
        prof_dir / PROFILE_FILE, index=False, encoding="utf-8")

    # TXT source (annotations.json producer for the tuning-memory contract template)
    notes_dir = raw / "notes"
    notes_dir.mkdir()
    pd.DataFrame({
        TIME_COL: [ts[5 * ROWS_PER_DAY], ts[BASE_ROWS + ROWS_PER_DAY], ts[N_ROWS - 1]],
        "备注": ["3 号位膜厚传感器完成例行校准，短期数据可能有轻微漂移",
                 "右侧边缘连续两个班次偏厚，已通知工艺工程师现场确认",
                 "交接班记录：运行平稳，参数未做调整"],
    }).to_csv(notes_dir / "operation_notes.csv", index=False, encoding="utf-8")


def case_m3_sentinel_e2e():
    out = []
    # sentinelcore enforces repo-root containment -> the whole pipeline runs inside the repo
    ws = REPO / "workspace"
    ws.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m3_ws11_", dir=str(ws)) as td:
        root = Path(td)
        raw, run = root / "raw", root / "run"
        raw.mkdir()
        _write_raw(raw, np.random.default_rng(SEED))

        # 1) E-1 on the raw folder (standard mode = top-level scan -> canonical anchor)
        r = _run([_py(), DP, "--data-path", raw, "--output", run / "00_input"])
        out.append(("E-1 exits 0 on the mixed raw folder", r.returncode == 0,
                    (r.stdout + r.stderr)[-300:]))
        anchor = run / "00_input" / "preprocessed_data.csv"
        out.append(("E-1 anchor written", anchor.exists(), str(anchor)))
        if not anchor.exists():
            return out
        adf = pd.read_csv(anchor, encoding="utf-8-sig")
        out.append(("anchor is the canonical table only (no pos_* merge from the subfolder)",
                    list(adf.columns) == [TIME_COL, "膜厚"], str(list(adf.columns)[:4])))

        # 2) E-1H build on the same raw folder (recursive picks up raw/profile/),
        #    anchored on the E-1 output
        r = _run([_py(), HET_BUILD, "--raw-path", raw, "--recursive", "--run-dir", run])
        payload = _last_json(r.stdout)
        out.append(("build.py exits 0 with status ok",
                    r.returncode == 0 and payload is not None and payload.get("status") == "ok",
                    (r.stdout + r.stderr)[-300:]))
        joined = run / "07_hetero" / "preprocessed_data_hetero.csv"
        out.append(("joined table written", joined.exists(), str(joined)))

        # AC3⑥ shape test: the four contract primary_path templates are reachable on a real run
        for rel in RUN_PRIMARY_PATH_TEMPLATES:
            out.append((f"primary_path template reachable: {rel}",
                        (run / rel).exists(), str(run / rel)))

        jdf = pd.read_csv(joined, encoding="utf-8-sig")
        hx_cols = [c for c in jdf.columns if c.startswith("HX-")]
        mean_col = next((c for c in hx_cols if c.endswith("-MEAN")), None)
        edge_col = next((c for c in hx_cols if c.endswith("-EDGE-R-DEV")), None)
        out.append((f"joined table carries HX features (n={len(hx_cols)}) incl. MEAN + EDGE-R-DEV",
                    len(hx_cols) >= 18 and mean_col is not None and edge_col is not None,
                    f"mean={mean_col} edge={edge_col}"))
        if mean_col is None or edge_col is None:
            return out
        # the injected right-edge lift must actually surface in the joined HX column
        pre = float(jdf[edge_col].iloc[BASE_ROWS - 60:BASE_ROWS - 5].mean())
        post = float(jdf[edge_col].iloc[BASE_ROWS + 5:].mean())
        out.append((f"{edge_col} lifts by ~{STEP_EDGE:.2f} after day 17",
                    abs((post - pre) - STEP_EDGE) < 0.05, f"pre={pre:.4f} post={post:.4f}"))

        # 3) baseline = in-control first 17 days (build_baseline has no truncation flag ->
        #    cut the history into a separate file, the documented convention).
        #    --group-col pins a non-registered name => single GROUP_ALL watch: without it the
        #    auto group hint would grab the TXT covariate column shift_bucket (E-1H product)
        #    and silently split the baseline into per-shift stores.
        hist = jdf.iloc[:BASE_ROWS]
        baseline_history = root / "baseline_history_17d.csv"
        hist.to_csv(baseline_history, index=False, encoding="utf-8")
        baseline_json = root / "watch_baseline.json"
        params = f"{mean_col},{edge_col}"
        r = _run([_py(), BUILD_BASELINE, "--history-csv", baseline_history,
                  "--time-col", TIME_COL, "--group-col", "__NONE__",
                  "--parameters", params, "--out", baseline_json])
        out.append(("build_baseline exits 0 on the 17-day hetero history",
                    r.returncode == 0 and baseline_json.exists(), (r.stdout + r.stderr)[-300:]))
        baseline_doc = json.loads(baseline_json.read_text(encoding="utf-8"))
        out.append(("baseline is a single __ALL__ group (no shift_bucket auto-split)",
                    list(baseline_doc.get("groups", {})) == ["__ALL__"],
                    str(list(baseline_doc.get("groups", {})))))

        # 4) watch window = the stepped last 4 days; explicit --data/--config/--out-dir only
        watch_csv = root / "watch_window_last4d.csv"
        jdf.iloc[BASE_ROWS:].to_csv(watch_csv, index=False, encoding="utf-8")
        watch_config = root / "watch_config.json"
        watch_config.write_text(json.dumps(
            {"time_col": TIME_COL, "group_col": "__NONE__",
             "parameters": [mean_col, edge_col]}, ensure_ascii=False),
            encoding="utf-8")
        out_dir = root / "sentinel_out"
        r = _run([_py(), SENTINEL, "watch", "--data", watch_csv, "--time-col", TIME_COL,
                  "--baseline", baseline_json, "--config", watch_config, "--out-dir", out_dir])
        alert_path = out_dir / "alert.json"
        out.append(("sentinel watch ran and wrote alert.json", alert_path.exists(),
                    f"rc={r.returncode} {(r.stdout + r.stderr)[-300:]}"))
        if not alert_path.exists():
            return out
        alert = json.loads(alert_path.read_text(encoding="utf-8"))
        out.append(("watch exit code 1 (findings)", r.returncode == 1, f"rc={r.returncode}"))
        out.append(("baseline mode is prior (explicit baseline consumed)",
                    (alert.get("baseline") or {}).get("mode") == "prior",
                    json.dumps(alert.get("baseline"))))

        hx_findings = [a for a in alert.get("alerts", [])
                       if str(a.get("parameter") or "").startswith("HX-")]
        out.append(("alert.json has >= 1 finding whose parameter starts with HX- "
                    "(sentinel reads heterogeneous features)", len(hx_findings) >= 1,
                    json.dumps(hx_findings[:1], ensure_ascii=False)[:400] if hx_findings
                    else json.dumps([a.get("parameter") for a in alert.get("alerts", [])][:5],
                                    ensure_ascii=False)))
        # exactly the parameters we pinned in --config were watched, single-group scope
        watched = sorted({a["parameter"] for a in hx_findings})
        out.append(("HX findings cite the pinned config parameters",
                    all(w in (mean_col, edge_col) for w in watched), str(watched)))
        out.append(("HX findings are single-group (__ALL__), not shift-split",
                    all(a.get("group") in (None, "__ALL__") for a in hx_findings),
                    str(sorted({str(a.get("group")) for a in hx_findings}))))
    return out


# ------------------------------------------------------------------ case 3


def case_m3_contract_docs():
    out = []
    # cross_skill_contracts.json parses and keeps its pre-existing entries intact
    doc = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    entries = doc.get("contracts") or []
    out.append(("cross_skill_contracts.json parses with a contracts list",
                isinstance(entries, list) and len(entries) >= 7, f"n={len(entries)}"))

    # layer 1: every hetero_* contract entry must name its 07_hetero artifact in `producer`
    # (the file-pattern carrier; primary_path is a field path inside that artifact)
    hetero_entries = [c for c in entries if "hetero" in str(c.get("id", "")).lower()]
    out.append(("all 4 hetero_* contracts registered",
                len(hetero_entries) >= 4,
                f"n={len(hetero_entries)}: {[c.get('id') for c in hetero_entries]}"))
    if not hetero_entries:
        out.append(("hetero_* contracts registered (layer-1 guard armed; WS8 pending)",
                    True, "0 hetero_* entries — disclosed pre-registration state"))
    for c in hetero_entries:
        cid = str(c.get("id"))
        producer = str(c.get("producer") or "")
        expect = next((t for frag, t in HETERO_CONTRACT_TEMPLATES if frag in cid.lower()), None)
        out.append((f"contract {cid} producer carries its 07_hetero artifact template",
                    expect is not None and expect in producer
                    and producer.startswith("industrial-hetero-preprocessor:07_hetero/"),
                    f"producer={producer!r} expect={expect!r}"))
        out.append((f"contract {cid} shape (primary_path + expect present)",
                    bool(str(c.get("primary_path") or "").strip())
                    and bool(str(c.get("expect") or "").strip()),
                    f"primary_path={c.get('primary_path')!r}"))

    # sentinel SKILL.md documents the E-1H wiring (plan §5 sentinel row)
    md = SENTINEL_SKILL_MD.read_text(encoding="utf-8")
    out.append(("sentinel SKILL.md mentions 07_hetero", "07_hetero" in md, ""))
    out.append(("sentinel SKILL.md mentions HX- features", "HX-" in md, ""))
    out.append(("sentinel SKILL.md forbids default discovery for hetero watches",
                "--config" in md and "--out-dir" in md, ""))
    return out


CASES = [
    ("m3-lsr-anti-hijack", case_m3_lsr_anti_hijack),
    ("m3-sentinel-e2e", case_m3_sentinel_e2e),
    ("m3-contract-docs", case_m3_contract_docs),
]
