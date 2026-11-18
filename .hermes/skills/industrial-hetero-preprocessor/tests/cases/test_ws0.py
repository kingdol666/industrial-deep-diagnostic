"""test_ws0.py — WS0 frozen-interface acceptance cases.

Covers: naming contract, time_ingest (incl. the R4 trap), fingerprint
invariance under tail-appended HX columns, build.py no-op semantics (P9),
exit-4 raw-path semantics, gate exit-2 semantics.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tests/cases
SKILL = HERE.parent.parent                      # skill root
SCRIPTS = SKILL / "scripts"
REPO = SCRIPTS.parent.parent.parent.parent      # repo root (.claude/skills/<skill>/scripts → up 4)
SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "Scripts" / "python.exe"
if not SHARED_PY.exists():
    SHARED_PY = REPO / ".claude" / "shared" / "scripts" / ".venv" / "bin" / "python"
sys.path.insert(0, str(SCRIPTS))

from heterocore import naming  # noqa: E402
from heterocore import time_ingest as ting  # noqa: E402


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run a fixed argument-list command (never a shell string)."""
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                          shell=False, cwd=cwd, timeout=180)


def _build_py() -> str:
    return str(SHARED_PY if SHARED_PY.exists() else sys.executable)


def case_naming():
    out = []
    col = naming.feature_column("profile", "THKSCAN", "EDGE-L-DEV")
    out.append(("feature_column builds HX name", naming.validate_column_name(col), col))
    out.append(("rejects non-ASCII", not naming.validate_column_name("HX-PROF-THK-EVT-huan-gun"), ""))
    out.append(("rejects bad prefix", not naming.validate_column_name("HX-XXX-THK-MEAN"), ""))
    out.append(("slug collision uses path_sha6",
                naming.unique_slug("thk_scan", Path("a/thk_scan.csv"), {"THKSCAN": "zz"})[0] != "THKSCAN", ""))
    out.append(("forbidden tokens detected",
                "joined" in naming.check_file_name("joined_data.csv"), ""))
    return out


def case_time_ingest():
    out = []
    v = ting.parse_ts("2026-10-15 08:30:00")
    out.append(("R4 trap: full timestamp keeps time-of-day",
                v.ts == datetime(2026, 10, 15, 8, 30), repr(v.ts)))
    v2 = ting.parse_ts("2026/10/15 08:30")
    out.append(("slash format keeps 08:30", v2.ts is not None and v2.ts.hour == 8 and v2.ts.minute == 30, repr(v2.ts)))
    v3 = ting.parse_ts("2026年10月15日 8:30")
    out.append(("chinese format parses", v3.ts is not None and v3.ts.hour == 8, repr(v3.ts)))
    v4 = ting.parse_ts("20261015_083000")
    out.append(("compact filename format parses", v4.ts is not None and v4.ts.hour == 8, repr(v4.ts)))
    v5 = ting.parse_ts(46017.354)
    out.append(("excel serial parses", v5.ts is not None and v5.ts.year >= 2025, repr(v5.ts)))
    amb = ting.parse_series(["05/07/2026", "20/07/2026"])
    out.append(("unambiguous dayfirst series not flagged", amb["ambiguous"] == 0, str(amb["ambiguous"])))
    s = ting.parse_series(["2026-10-15 08:30:00"] * 5)
    out.append(("series midnight_only False when times present", s["midnight_only"] is False, str(s["midnight_only"])))
    s2 = ting.parse_series(["2026-10-15 00:00:00"] * 5)
    out.append(("all-midnight flagged (H6b feed)", s2["midnight_only"] is True, ""))
    fn = ting.extract_filename_timestamp("waxs_20261015_083000.png")
    out.append(("filename ts extracted", fn is not None and fn.hour == 8, repr(fn)))
    return out


def case_fingerprint_invariant():
    """schema_fp must not change when HX-* columns are appended at the tail (plan D6)."""
    import pandas as pd

    out = []
    with tempfile.TemporaryDirectory() as td:
        base = pd.DataFrame({
            "时间": ["2026-10-15 08:00:00", "2026-10-15 08:10:00", "2026-10-15 08:20:00"],
            "温度": [25.1, 25.2, 25.3],
        })
        p1 = Path(td) / "anchor.csv"
        p2 = Path(td) / "joined.csv"
        base.to_csv(p1, index=False, encoding="utf-8-sig")
        base.assign(**{"HX-PROF-T-MEAN": [1.0, 2.0, 3.0], "HX-PROF-T-P95": [1.1, 2.1, 3.1]}).to_csv(
            p2, index=False, encoding="utf-8-sig")
        js = (
            "import { computeFingerprint } from %s;\n"
            "const a = computeFingerprint(%s);\n"
            "const b = computeFingerprint(%s);\n"
            "console.log(JSON.stringify({same: a.schema_fp === b.schema_fp, a: a.schema_fp, b: b.schema_fp}));\n"
        ) % (json.dumps((REPO / ".claude/shared/scripts/ontology_store.mjs").as_uri()),
             json.dumps(str(p1)), json.dumps(str(p2)))
        r = _run(["node", "--input-type=module", "-e", js], cwd=str(REPO))
        try:
            data = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return [("fingerprint probe ran", False, (r.stdout + r.stderr)[-400:])]
        out.append(("schema_fp unchanged with tail HX columns", data.get("same") is True, json.dumps(data)))
    return out


def _make_run_dir(td: Path) -> tuple[Path, Path]:
    import pandas as pd

    run_dir = Path(td) / "run"
    (run_dir / "00_input").mkdir(parents=True)
    raw = Path(td) / "raw"
    raw.mkdir()
    pd.DataFrame({"时间": ["2026-10-15 08:00:00", "2026-10-15 08:10:00"], "温度": [25.1, 25.2]}).to_csv(
        run_dir / "00_input" / "preprocessed_data.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"时间": ["2026-10-15 08:00:00", "2026-10-15 08:10:00"], "温度": [25.1, 25.2]}).to_csv(
        raw / "plain_table.csv", index=False, encoding="utf-8-sig")
    return run_dir, raw


def case_build_noop():
    """P9: folder without hetero sources → only the marker is written; guards intact."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        run_dir, raw = _make_run_dir(Path(td))
        r = _run([_build_py(), str(SCRIPTS / "build.py"), "--raw-path", str(raw), "--run-dir", str(run_dir)])
        out.append(("build exits 0 on no_hetero_sources", r.returncode == 0, (r.stdout + r.stderr)[-300:]))
        try:
            payload = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return [("build stdout parseable", False, (r.stdout + r.stderr)[-300:])]
        out.append(("status no_hetero_sources", payload.get("status") == "no_hetero_sources", r.stdout))
        het = run_dir / "07_hetero"
        files = sorted(p.name for p in het.rglob("*") if p.is_file()) if het.exists() else []
        out.append(("only the marker written", files == ["hetero_manifest.json"], str(files)))
        g = _run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(run_dir)])
        out.append(("gate exit 0 on no-source run", g.returncode == 0, (g.stdout + g.stderr)[-300:]))
        anchor = run_dir / "00_input" / "preprocessed_data.csv"
        h = "sha256:" + hashlib.sha256(anchor.read_bytes()).hexdigest()
        m = json.loads((het / "hetero_manifest.json").read_text(encoding="utf-8"))
        pre = [f for f in m["h7_guard"]["files"] if f["path"].endswith("preprocessed_data.csv")]
        out.append(("guard recorded anchor hash", bool(pre) and pre[0]["sha256"] == h, json.dumps(pre)))
    return out


def case_exit4_and_gate2():
    out = []
    with tempfile.TemporaryDirectory() as td:
        r = _run([_build_py(), str(SCRIPTS / "build.py"), "--run-dir", str(Path(td) / "run")])
        out.append(("exit 4 when raw path unresolved", r.returncode == 4, f"rc={r.returncode} {r.stdout[-200:]}"))
        g = _run(["node", str(SCRIPTS / "quality_gate.mjs"), "--run-dir", str(Path(td) / "run")])
        out.append(("gate exit 2 when marker absent", g.returncode == 2, f"rc={g.returncode}"))
    return out


CASES = [
    ("ws0-naming", case_naming),
    ("ws0-time-ingest", case_time_ingest),
    ("ws0-fingerprint", case_fingerprint_invariant),
    ("ws0-build-noop", case_build_noop),
    ("ws0-exit4-gate2", case_exit4_and_gate2),
]
