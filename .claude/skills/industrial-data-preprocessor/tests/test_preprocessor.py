#!/usr/bin/env python3
"""Unit tests for the adaptive data preprocessor (E-1).

Verifies the pipeline accepts ANY data source and yields the canonical
preprocessed_data.csv + report:

1.  single clean CSV            — passthrough
2.  GBK + semicolon + junk head — encoding/delimiter/header adaptation
3.  multi-sheet xlsx w/ junk    — main sheet selection
4.  xlsm workbook               — macro-enabled Excel support
5.  JSON record array           — json adaptation
6.  markdown tables / free text — table extraction vs context preservation
7.  mixed directory             — csv+xlsx+md+py → merge/largest + context
8.  batch data without time     — cross-sectional passthrough
9.  multi-block delimited file  — largest block wins
10. no-tabular directory        — graceful no_tabular_data report
11. quality flags / actual merge key / per-file exclusions (t12)
12. --integrate-merge csv+xlsx folder — merge + column_source (t13)
13. --integrate-merge cadence gate — default exclude vs opt-in (t14)
14. CLI — integrate-merge x stability-single-primary mutex, exit 0 (t15)
15. --integrate-merge strict exits — no primary / merged <50 rows (t16)
16. parquet in default mode + corrupt-source isolation (t17)
17. --integrate-merge duplicate-column semantics vetting (t18)

New tests scratch under the in-repo .tmp-fixtures-preprocessor/ directory
(never the system temp); it is removed again when the suite finishes.

Run: uv run --project .claude/shared/scripts python .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent / "scripts"
_REPO = _HERE.parents[3]
sys.path.insert(0, str(_SCRIPTS))

from data_preprocessor import (  # noqa: E402
    _preprocess_integrate_merge,
    _preprocess_stability_folder,
    preprocess,
)

_FAILURES: list[str] = []
_TMP: Path = Path(tempfile.mkdtemp(prefix="prep_test_"))
_INREPO_TMP: Path = _REPO / ".tmp-fixtures-preprocessor"


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        _FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL {name}: {detail}")
    else:
        print(f"  ok   {name}")


def run_case(data_path: Path, out_dir: Path, name: str = "t") -> dict:
    return preprocess(data_path, out_dir, name)


def _inrepo_case(name: str) -> tuple[Path, Path]:
    """Fresh in-repo scratch case dir; returns (case_dir, out_dir)."""
    d = _INREPO_TMP / name
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return d, d / "out"


def test_clean_csv() -> None:
    d = _TMP / "t1"
    out = d / "out"
    d.mkdir(parents=True)
    pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=100, freq="min"),
        "pressure_bar": np.random.normal(10, 1, 100),
        "temp_C": np.random.normal(200, 5, 100),
    }).to_csv(d / "data.csv", index=False)
    rep = run_case(d / "data.csv", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t1-csv-shape", df.shape == (100, 3), str(df.shape))
    check("t1-time-col", rep["quality"]["time_column"] == "timestamp",
          str(rep["quality"]["time_column"]))


def test_gbk_semicolon_junk() -> None:
    d = _TMP / "t2"
    out = d / "out"
    d.mkdir(parents=True)
    lines = [
        "设备运行数据导出报告",              # junk title
        "导出时间：2025-01-02",              # junk
        "温度(℃);压力(MPa);流量(m³/h);时间",  # header with semicolons
    ]
    for i in range(120):
        lines.append(f"{210 + i * 0.1:.1f};{8 + i * 0.01:.3f};{55 + i * 0.05:.2f};2025-01-02 0{i // 60}:{i % 60:02d}:00")
    (d / "设备导出.txt").write_bytes("\n".join(lines).encode("gb18030"))
    rep = run_case(d / "设备导出.txt", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t2-gbk-rows", df.shape[0] == 120, str(df.shape))
    check("t2-gbk-cols", df.shape[1] == 4, str(df.shape))
    check("t2-numeric", pd.to_numeric(df.iloc[0, 0], errors="coerce") == 210.0,
          str(df.iloc[0, 0]))


def test_multisheet_xlsx() -> None:
    d = _TMP / "t3"
    out = d / "out"
    d.mkdir(parents=True)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["junk"])
    ws2 = wb.create_sheet("YAMATAKE_QUERY")
    ws2.append(["a"])
    ws3 = wb.create_sheet("数据统计")
    ws3.append(["timestamp", "value_1", "value_2"])
    for i in range(300):
        ws3.append([f"2025-01-01 00:{i % 60:02d}:00", 1.0 + i, 2.0 * i])
    wb.save(d / "multi.xlsx")
    rep = run_case(d / "multi.xlsx", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t3-xlsx-shape", df.shape == (300, 3), str(df.shape))
    check("t3-sheet-selected", rep["selected_table"]["sheet"] == "数据统计",
          str(rep["selected_table"]))


def test_xlsm() -> None:
    d = _TMP / "t4"
    out = d / "out"
    d.mkdir(parents=True)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "宏数据"
    ws.append(["time", "temp", "torque"])
    for i in range(200):
        ws.append([f"2025-02-01 {i // 60:02d}:{i % 60:02d}:00", 30 + i * 0.1, 50 - i * 0.05])
    wb.save(d / "macro_data.xlsm")
    rep = run_case(d / "macro_data.xlsm", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t4-xlsm-shape", df.shape == (200, 3), str(df.shape))
    check("t4-xlsm-time", rep["quality"]["time_column"] == "time")


def test_json_records() -> None:
    d = _TMP / "t5"
    out = d / "out"
    d.mkdir(parents=True)
    rows = [{"ts": f"2025-03-01 00:{i // 60:02d}:{i % 60:02d}", "speed": 1000 + i, "load": i * 0.5}
            for i in range(150)]
    (d / "data.json").write_text(json.dumps(rows), encoding="utf-8")
    rep = run_case(d / "data.json", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t5-json-shape", df.shape == (150, 3), str(df.shape))
    check("t5-json-time", rep["quality"]["time_column"] == "ts")


def test_markdown() -> None:
    d = _TMP / "t6"
    out = d / "out"
    d.mkdir(parents=True)
    md = """# 工艺说明

本文件描述流程背景。

| 时间 | 温度 | 压力 |
|------|------|------|
| 2025-01-01 00:00:00 | 200 | 8 |
| 2025-01-01 00:01:00 | 201 | 8.1 |
| 2025-01-01 00:02:00 | 202 | 8.2 |
| 2025-01-01 00:03:00 | 203 | 8.3 |
| 2025-01-01 00:04:00 | 204 | 8.4 |
| 2025-01-01 00:05:00 | 205 | 8.5 |
"""
    (d / "process_table.md").write_text(md, encoding="utf-8")
    rep = run_case(d / "process_table.md", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t6-md-shape", df.shape == (6, 3), str(df.shape))

    # free-text md → context, no_tabular
    out2 = d / "out2"
    (d / "notes.md").write_text("# 说明\n没有表格的自由文本。", encoding="utf-8")
    rep2 = run_case(d / "notes.md", out2)
    check("t6-md-context", rep2["status"] == "no_tabular_data"
          and len(rep2["context_files"]) == 1, str(rep2["status"]))

    # tiny md table (<5 rows) → context, not data
    out3 = d / "out3"
    (d / "snippet.md").write_text("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n", encoding="utf-8")
    rep3 = run_case(d / "snippet.md", out3)
    check("t6-md-tiny-context", rep3["status"] == "no_tabular_data"
          and len(rep3["context_files"]) == 1, str(rep3["status"]))


def test_mixed_directory() -> None:
    d = _TMP / "t7"
    out = d / "out"
    d.mkdir(parents=True)
    # process csv
    pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=200, freq="min"),
        "pressure": np.random.normal(8, 0.5, 200),
    }).to_csv(d / "process.csv", index=False)
    # quality xlsx
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "quality"
    ws.append(["timestamp", "quality_score"])
    for i in range(200):
        ws.append([f"2025-01-01 {i // 60:02d}:{i % 60:02d}:00", 90 + i * 0.02])
    wb.save(d / "quality.xlsx")
    # context + skipped
    (d / "ground_truth.md").write_text("# 真值说明", encoding="utf-8")
    (d / "gen.py").write_text("print('x')", encoding="utf-8")
    rep = run_case(d, out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t7-merge", df.shape[0] >= 200 and "pressure" in df.columns
          and "quality_score" in df.columns, str(df.shape) + str(list(df.columns)))
    check("t7-context", any("ground_truth.md" in f for f in rep["context_files"]), str(rep["context_files"]))
    check("t7-skip", any(s["file"] == "gen.py" for s in rep["skipped_files"]), str(rep["skipped_files"]))


def test_batch_no_time() -> None:
    d = _TMP / "t8"
    out = d / "out"
    d.mkdir(parents=True)
    pd.DataFrame({
        "batch_id": [f"B{i}" for i in range(50)],
        "yield_pct": np.random.normal(85, 3, 50),
        "impurity_ppm": np.random.normal(20, 5, 50),
    }).to_csv(d / "batch.csv", index=False)
    rep = run_case(d / "batch.csv", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t8-batch-shape", df.shape == (50, 3), str(df.shape))
    check("t8-no-time", rep["quality"]["time_column"] is None)


def test_multiblock_delimited() -> None:
    d = _TMP / "t9"
    out = d / "out"
    d.mkdir(parents=True)
    big = ["a,b,c"] + [f"1,2,3"] * 400
    small = ["x,y"] + ["9,9"] * 10
    (d / "blocks.txt").write_text("\n".join(big + [""] + small), encoding="utf-8")
    rep = run_case(d / "blocks.txt", out)
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t9-block-largest", df.shape == (400, 3), str(df.shape))


def test_no_tabular_dir() -> None:
    d = _TMP / "t10"
    out = d / "out"
    d.mkdir(parents=True)
    (d / "notes.md").write_text("# 只有说明\n没有表格。", encoding="utf-8")
    (d / "plan.py").write_text("pass", encoding="utf-8")
    rep = run_case(d, out)
    check("t10-status", rep["status"] == "no_tabular_data", rep["status"])
    check("t10-context-kept", len(rep["context_files"]) == 1, str(rep["context_files"]))


def test_quality_flags_merge_key_exclusions() -> None:
    """t12: per-source quality_flags (duplicates/nulls/encoding/delimiter),
    the ACTUAL join column in merge info, and per-file merge-exclusion reasons."""
    d = _TMP / "t12"
    out = d / "out"
    d.mkdir(parents=True)
    ts = pd.date_range("2025-06-01", periods=120, freq="min").strftime("%Y-%m-%d %H:%M:%S")

    # a_batch.csv — FIRST alphabetically → its time col ("batch_time") becomes
    # the join key even though the primary is b_process.csv ("timestamp").
    # Injected: 2 exact duplicate rows (copies of rows 58/59) + 1 empty cell.
    batch = pd.DataFrame({
        "batch_time": ts,
        "moisture_pct": np.where(np.arange(120) == 57, np.nan,
                                 np.random.normal(12, 0.5, 120)),
    })
    pd.concat([batch.iloc[:60], batch.iloc[58:60], batch.iloc[60:]],
              ignore_index=True).to_csv(d / "a_batch.csv", index=False)

    # b_process.csv — most cols → primary; comma csv
    pd.DataFrame({
        "timestamp": ts,
        "temp_C": np.random.normal(200, 5, 120),
        "press_bar": np.random.normal(8, 0.2, 120),
        "flow_m3h": np.random.normal(55, 1, 120),
    }).to_csv(d / "b_process.csv", index=False)

    # c_lab.csv — 20 rows → below_min_rows
    pd.DataFrame({
        "timestamp": pd.date_range("2025-06-01", periods=20, freq="min").strftime("%Y-%m-%d %H:%M:%S"),
        "lab_ph": np.random.normal(7, 0.1, 20),
    }).to_csv(d / "c_lab.csv", index=False)

    # d_ambient.csv — GBK-encoded, disjoint June-vs-September time axis → low_overlap
    amb = pd.DataFrame({
        "timestamp": pd.date_range("2025-09-01", periods=120, freq="min").strftime("%Y-%m-%d %H:%M:%S"),
        "环境温度": np.random.normal(25, 2, 120),
    })
    amb.to_csv(d / "d_ambient.csv", index=False, encoding="gb18030")

    # e_notes.csv — 120 rows, no time column → no_timestamp
    pd.DataFrame({
        "operator": ["A", "B"] * 60,
        "shift_note": ["note"] * 120,
    }).to_csv(d / "e_notes.csv", index=False)

    rep = run_case(d, out, "t12")

    # (b) the ACTUAL join column: base table's time col, not the primary's
    mg = rep.get("merge") or {}
    check("t12-merge-key-actual", mg.get("key") == "batch_time", str(mg.get("key")))
    check("t12-merge-primary-time", mg.get("primary_time_column") == "timestamp",
          str(mg.get("primary_time_column")))
    check("t12-merge-source-time-cols",
          mg.get("source_time_columns", {}).get("a_batch.csv") == "batch_time"
          and mg.get("source_time_columns", {}).get("b_process.csv") == "timestamp",
          str(mg.get("source_time_columns")))
    check("t12-selected-is-primary", (rep["selected_table"] or {}).get("file") == "b_process.csv",
          str((rep["selected_table"] or {}).get("file")))

    # (a) per-source quality flags
    tabs = {t["file"]: t for t in rep["tables"]}
    q_batch = tabs["a_batch.csv"]["quality_flags"]
    check("t12-dup-count", q_batch["exact_duplicate_rows"]["count"] == 2,
          str(q_batch["exact_duplicate_rows"]))
    check("t12-dup-rows", q_batch["exact_duplicate_rows"]["row_indices_0based"] == [58, 59, 60, 61],
          str(q_batch["exact_duplicate_rows"]["row_indices_0based"]))
    check("t12-null-count", q_batch["null_cell_count"] == 1, str(q_batch["null_cell_count"]))
    check("t12-encoding-csv", q_batch["encoding"] in ("utf-8", "utf-8-sig"),
          str(q_batch["encoding"]))
    check("t12-delimiter-csv", q_batch["delimiter"] == ",", str(q_batch["delimiter"]))
    q_amb = tabs["d_ambient.csv"]["quality_flags"]
    check("t12-encoding-gbk", q_amb["encoding"] == "gb18030", str(q_amb["encoding"]))
    q_proc = tabs["b_process.csv"]["quality_flags"]
    check("t12-proc-clean", q_proc["exact_duplicate_rows"]["count"] == 0
          and q_proc["null_cell_count"] == 0, str(q_proc))

    # (c) per-file exclusion reasons
    excl = {e["file"]: e["reason_code"] for e in rep.get("merge_exclusions", [])}
    check("t12-excl-below-min", excl.get("c_lab.csv") == "below_min_rows", str(excl))
    check("t12-excl-low-overlap", excl.get("d_ambient.csv") == "low_overlap", str(excl))
    check("t12-excl-no-ts", excl.get("e_notes.csv") == "no_timestamp", str(excl))
    check("t12-excl-not-for-merged",
          "a_batch.csv" not in excl and "b_process.csv" not in excl, str(excl))
    check("t12-excl-details", all(e.get("detail") for e in rep.get("merge_exclusions", [])),
          str(rep.get("merge_exclusions")))


def test_stability_folder_adaptive_bc2_shape() -> None:
    repo = _HERE.parents[3]
    data = repo / "data" / "bopet_cases" / "bc2_filter_dp_cycles"
    out = _TMP / "stability-folder-bc2" / "00_input"
    rep = _preprocess_stability_folder(data, out, "BC2", recursive=True)
    check("folder-status", rep["status"] == "ok", rep.get("reason", rep["status"]))
    check("folder-recursive", rep["recursive_discovery"] is True, str(rep.get("recursive_discovery")))
    check("folder-primary-dcs", rep["selected_table"]["file"] == "dcs_melt_system_10min.csv",
          str(rep.get("selected_table")))
    check("folder-primary-row-count", rep["selected_table"]["n_rows"] == 3024,
          str(rep["selected_table"]["n_rows"]))
    check("folder-primary-time-detected", rep["selected_table"]["time_column"] == "时间",
          str(rep["selected_table"].get("time_column")))
    by_file = {item["relative_path"]: item for item in rep["source_dispositions"]}
    check("folder-qc-audit", by_file["qc_shift_8h.csv"]["role"] == "auxiliary"
          and by_file["qc_shift_8h.csv"]["disposition"] == "excluded_from_scoring",
          str(by_file.get("qc_shift_8h.csv")))
    check("folder-maintenance-audit", by_file["maintenance_log.csv"]["role"] == "event"
          and by_file["maintenance_log.csv"]["disposition"] == "excluded_from_scoring",
          str(by_file.get("maintenance_log.csv")))
    check("folder-context-manifest", by_file["generation_manifest.json"]["role"] == "metadata"
          and by_file["generation_manifest.json"]["disposition"] == "context_only",
          str(by_file.get("generation_manifest.json")))
    check("folder-ground-truth-protected", by_file["ground_truth.md"]["disposition"] == "protected_excluded",
          str(by_file.get("ground_truth.md")))
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("folder-canonical-only-dcs", df.shape == (3024, 8), str(df.shape))


def test_stability_folder_no_time_series() -> None:
    data = _TMP / "stability-no-time"
    data.mkdir(parents=True)
    pd.DataFrame({"batch": [f"B{i}" for i in range(60)], "yield_pct": np.arange(60)}).to_csv(data / "batch.csv", index=False)
    out = _TMP / "stability-no-time-out"
    rep = _preprocess_stability_folder(data, out, "NO-TIME", recursive=True)
    check("folder-no-time-status", rep["status"] == "no_time_series", str(rep["status"]))
    check("folder-no-time-no-output", not (out / "preprocessed_data.csv").exists(), "must not synthesize a series")


def test_integrate_merge_two_format_folder() -> None:
    """t13: --integrate-merge merges a csv+xlsx folder onto one primary and
    discloses column_source / per-source cadence in the merge block."""
    d, out = _inrepo_case("t13")
    data = d / "data"
    data.mkdir()
    ts = pd.date_range("2025-08-01", periods=150, freq="min").strftime("%Y-%m-%d %H:%M:%S")
    pd.DataFrame({
        "timestamp": ts,
        "temp_C": np.random.normal(200, 5, 150),
        "press_bar": np.random.normal(8, 0.2, 150),
    }).to_csv(data / "a_process.csv", index=False)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "quality"
    ws.append(["timestamp", "quality_score"])
    for i in range(150):
        ws.append([ts[i], 90 + i * 0.02])
    wb.save(data / "quality.xlsx")

    rep = _preprocess_integrate_merge(data, out, "t13")
    check("t13-status", rep["status"] == "ok", str(rep.get("reason", rep["status"])))
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t13-merged-shape", df.shape[0] == 150
          and all(c in df.columns for c in ("temp_C", "press_bar", "quality_score")),
          str(df.shape) + str(list(df.columns)))
    mg = rep["merge"]
    check("t13-merge-strategy", mg["strategy"] == "outer_merge_on_time_column", str(mg))
    check("t13-merge-key", mg["key"] == "timestamp", str(mg.get("key")))
    check("t13-column-source", mg["column_source"].get("temp_C") == "a_process.csv"
          and mg["column_source"].get("quality_score") == "quality.xlsx"
          and mg["column_source"].get("timestamp") == "a_process.csv",
          str(mg.get("column_source")))
    check("t13-cadence-map", mg["source_cadence_seconds"] == {"a_process.csv": 60.0, "quality.xlsx": 60.0},
          str(mg.get("source_cadence_seconds")))
    check("t13-cadence-ratio", mg["cadence_ratio"] == 1.0, str(mg.get("cadence_ratio")))
    check("t13-no-exclusions", rep["merge_exclusions"] == [], str(rep["merge_exclusions"]))


def test_integrate_merge_cadence_gate() -> None:
    """t14: cadence gate — an 11-min secondary against a 1-min primary is
    excluded as cadence_mismatch by default and merged with the opt-in flag."""
    d, out = _inrepo_case("t14")
    data = d / "data"
    data.mkdir()
    pd.DataFrame({
        "timestamp": pd.date_range("2025-08-01", periods=300, freq="min").strftime("%Y-%m-%d %H:%M:%S"),
        "fast_val": np.random.normal(50, 1, 300),
    }).to_csv(data / "b_fast.csv", index=False)
    pd.DataFrame({
        "timestamp": pd.date_range("2025-08-01", periods=120, freq="11min").strftime("%Y-%m-%d %H:%M:%S"),
        "slow_val": np.random.normal(10, 1, 120),
    }).to_csv(data / "c_slow.csv", index=False)

    rep = _preprocess_integrate_merge(data, out, "t14")
    check("t14-status", rep["status"] == "ok", str(rep.get("reason", rep["status"])))
    excl = {e["file"]: e["reason_code"] for e in rep["merge_exclusions"]}
    check("t14-cadence-excluded", excl.get("c_slow.csv") == "cadence_mismatch", str(excl))
    check("t14-neg-no-merge", rep["merge"]["strategy"] == "no_merge", str(rep["merge"]))
    disp = {x["relative_path"]: x.get("reason_code") for x in rep["source_dispositions"]}
    check("t14-disposition-code", disp.get("c_slow.csv") == "cadence_mismatch", str(disp))
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t14-slow-col-dropped", "slow_val" not in df.columns, str(list(df.columns)))

    out2 = d / "out2"
    rep2 = _preprocess_integrate_merge(data, out2, "t14-allow", allow_cadence_mismatch=True)
    check("t14-allow-status", rep2["status"] == "ok", str(rep2.get("reason", rep2["status"])))
    mg = rep2["merge"]
    df2 = pd.read_csv(out2 / "preprocessed_data.csv")
    check("t14-allow-merged", "slow_val" in df2.columns and df2.shape[0] == 392,
          str(df2.shape) + str(list(df2.columns)))
    check("t14-allow-cadence-map", mg["source_cadence_seconds"] == {"b_fast.csv": 60.0, "c_slow.csv": 660.0},
          str(mg.get("source_cadence_seconds")))
    check("t14-allow-ratio", mg["cadence_ratio"] == 11.0, str(mg.get("cadence_ratio")))
    check("t14-allow-disclosure", mg.get("cadence_mismatch_allowed") == ["c_slow.csv"],
          str(mg.get("cadence_mismatch_allowed")))


def test_cli_integrate_merge_mutex() -> None:
    """t15: --integrate-merge and --stability-single-primary are hard mutually
    exclusive (usage error, exit 2); --integrate-merge alone exits 0."""
    d, out = _inrepo_case("t15")
    data = d / "data"
    data.mkdir()
    pd.DataFrame({
        "timestamp": pd.date_range("2025-08-01", periods=80, freq="min").strftime("%Y-%m-%d %H:%M:%S"),
        "value": np.arange(80),
    }).to_csv(data / "only.csv", index=False)
    script = str(_SCRIPTS / "data_preprocessor.py")
    both = subprocess.run([sys.executable, script, "--data-path", str(data), "--output", str(out),
                           "--integrate-merge", "--stability-single-primary"],
                          capture_output=True, text=True)
    check("t15-mutex-exit2", both.returncode == 2,
          f"rc={both.returncode} err={(both.stderr or '')[:200]}")
    check("t15-mutex-usage", "usage" in (both.stderr or "").lower(), str((both.stderr or "")[:200]))
    single = subprocess.run([sys.executable, script, "--data-path", str(data), "--output", str(d / "out2"),
                             "--integrate-merge"], capture_output=True, text=True)
    check("t15-integrate-exit0", single.returncode == 0,
          f"rc={single.returncode} err={(single.stderr or '')[:200]}")


def test_integrate_merge_strict_exits() -> None:
    """t16: no eligible primary and a post-merge primary below 50 rows are the
    strict exit-2 statuses of --integrate-merge."""
    d, out = _inrepo_case("t16")
    # (a) no usable primary: only a tiny table without a time axis
    tiny = d / "tiny"
    tiny.mkdir()
    pd.DataFrame({"metric_0": np.arange(10), "metric_1": np.arange(10)}).to_csv(tiny / "small.csv", index=False)
    rep = _preprocess_integrate_merge(tiny, d / "out-tiny", "t16a")
    check("t16a-no-primary-status", rep["status"] == "no_usable_primary", str(rep["status"]))

    # (b) merge executes but the anti-bloat gate abandons it and the score
    # fallback restores a <50-row table → merged_primary_too_small → exit 2.
    # a_small_wide carries a time column (so it is a merge-pool candidate the
    # fallback can pick) but stays below the 50-row primary eligibility.
    data = d / "data"
    data.mkdir()
    small_ts = pd.date_range("2025-08-01", periods=30, freq="min").strftime("%Y-%m-%d %H:%M:%S")
    pd.DataFrame({"timestamp": small_ts,
                  **{f"metric_{i}": np.random.normal(0, 1, 30) for i in range(30)}}).to_csv(
        data / "a_small_wide.csv", index=False)
    pd.DataFrame({
        "timestamp": pd.date_range("2025-09-01", periods=60, freq="min").strftime("%Y-%m-%d %H:%M:%S"),
        "temp_C": np.random.normal(200, 5, 60),
        "press_bar": np.random.normal(8, 0.2, 60),
    }).to_csv(data / "b_primary.csv", index=False)
    pd.DataFrame({
        "timestamp": ["2025-09-01 00:00:00"] * 50 + ["2025-09-01 00:01:00"] * 50,
        "partner_val": np.arange(100),
    }).to_csv(data / "c_partner.csv", index=False)
    proc = subprocess.run([sys.executable, str(_SCRIPTS / "data_preprocessor.py"),
                           "--data-path", str(data), "--output", str(out), "--integrate-merge"],
                          capture_output=True, text=True)
    check("t16b-exit2", proc.returncode == 2,
          f"rc={proc.returncode} err={(proc.stderr or '')[:300]}")
    report = json.loads((out / "preprocessing_report.json").read_text(encoding="utf-8"))
    check("t16b-status", report["status"] == "merged_primary_too_small", str(report["status"]))
    check("t16b-abandoned", report["merge"]["strategy"] == "abandoned", str(report["merge"].get("strategy")))
    check("t16b-fallback-selected", report["selected_table"]["file"] == "a_small_wide.csv",
          str(report["selected_table"].get("file")))


def test_default_mode_parquet() -> None:
    """t17: parquet is a first-class default-mode table source; a corrupt
    parquet degrades to a per-source error instead of failing the run."""
    d, out = _inrepo_case("t17")
    pd.DataFrame({
        "timestamp": pd.date_range("2025-07-01", periods=120, freq="min"),
        "value": np.random.normal(10, 1, 120),
    }).to_parquet(d / "data.parquet")
    rep = run_case(d / "data.parquet", out)
    check("t17-parquet-status", rep["status"] == "ok", str(rep["status"]))
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t17-parquet-shape", df.shape == (120, 2), str(df.shape))
    check("t17-parquet-format", (rep["tables"][0] or {}).get("format") == "parquet", str(rep["tables"]))

    d2, out2 = _inrepo_case("t17b")
    pd.DataFrame({
        "timestamp": pd.date_range("2025-07-01", periods=120, freq="min").strftime("%Y-%m-%d %H:%M:%S"),
        "value": np.arange(120),
    }).to_csv(d2 / "good.csv", index=False)
    (d2 / "bad.parquet").write_bytes(b"definitely not a parquet file")
    rep2 = run_case(d2, out2)
    check("t17b-still-ok", rep2["status"] == "ok", str(rep2["status"]))
    roles = {s["file"]: s["role"] for s in rep2["sources"]}
    check("t17b-bad-parquet-isolated", roles.get("bad.parquet") == "error", str(rep2["sources"]))
    check("t17b-good-processed", any(t["file"] == "good.csv" for t in rep2["tables"]),
          str(rep2["tables"]))
    df2 = pd.read_csv(out2 / "preprocessed_data.csv")
    check("t17b-good-rows", df2.shape[0] == 120, str(df2.shape))


def test_integrate_merge_duplicate_columns() -> None:
    """t18: duplicated columns are vetted with _same_column_meaning on the
    aligned time axis — agreeing copies fill gaps, disagreeing copies are
    dropped with a duplicate_column_semantics_mismatch exclusion."""
    d, out = _inrepo_case("t18")
    data = d / "data"
    data.mkdir()
    ts = pd.date_range("2025-08-01", periods=150, freq="min").strftime("%Y-%m-%d %H:%M:%S")
    temp = [f"{200 + i * 0.1:.1f}" for i in range(150)]
    temp[10] = ""
    temp[20] = ""
    pd.DataFrame({"timestamp": ts, "temp_C": temp, "press_bar": np.random.normal(8, 0.2, 150),
                  "flow_m3h": np.random.normal(55, 1, 150)}).to_csv(data / "a_main.csv", index=False)
    agree = temp[:]
    agree[10] = f"{200 + 10 * 0.1:.1f}"
    agree[20] = f"{200 + 20 * 0.1:.1f}"
    pd.DataFrame({"timestamp": ts, "temp_C": agree,
                  "humidity_pct": np.random.normal(60, 2, 150)}).to_csv(data / "b_agree.csv", index=False)
    pd.DataFrame({"timestamp": ts,
                  "temp_C": [f"{300 + i * 0.1:.1f}" for i in range(150)]}).to_csv(data / "c_disagree.csv", index=False)

    rep = _preprocess_integrate_merge(data, out, "t18")
    check("t18-status", rep["status"] == "ok", str(rep.get("reason", rep["status"])))
    mismatches = {(e["file"], e.get("column")): e["reason_code"]
                  for e in rep["merge_exclusions"]
                  if e.get("reason_code") == "duplicate_column_semantics_mismatch"}
    check("t18-disagree-excluded", mismatches.get(("c_disagree.csv", "temp_C"))
          == "duplicate_column_semantics_mismatch", str(mismatches))
    check("t18-agree-not-excluded", ("b_agree.csv", "temp_C") not in mismatches, str(mismatches))
    df = pd.read_csv(out / "preprocessed_data.csv")
    check("t18-gap-filled", abs(float(df.loc[10, "temp_C"]) - 201.0) < 1e-9, str(df.loc[10, "temp_C"]))
    check("t18-primary-values-kept", abs(float(df.loc[0, "temp_C"]) - 200.0) < 1e-9,
          str(df.loc[0, "temp_C"]))
    cs = rep["merge"]["column_source"]
    check("t18-column-source", cs.get("humidity_pct") == "b_agree.csv"
          and cs.get("temp_C") == "a_main.csv", str(cs))


def main() -> None:
    print("preprocessor tests:")
    shutil.rmtree(_INREPO_TMP, ignore_errors=True)
    for fn in [
        test_clean_csv,
        test_gbk_semicolon_junk,
        test_multisheet_xlsx,
        test_xlsm,
        test_json_records,
        test_markdown,
        test_mixed_directory,
        test_batch_no_time,
        test_multiblock_delimited,
        test_no_tabular_dir,
        test_quality_flags_merge_key_exclusions,
        test_stability_folder_adaptive_bc2_shape,
        test_stability_folder_no_time_series,
        test_integrate_merge_two_format_folder,
        test_integrate_merge_cadence_gate,
        test_cli_integrate_merge_mutex,
        test_integrate_merge_strict_exits,
        test_default_mode_parquet,
        test_integrate_merge_duplicate_columns,
    ]:
        fn()
    shutil.rmtree(_TMP, ignore_errors=True)
    shutil.rmtree(_INREPO_TMP, ignore_errors=True)
    if _FAILURES:
        print(f"\n{len(_FAILURES)} FAILURES")
        sys.exit(1)
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
