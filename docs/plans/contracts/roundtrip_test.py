#!/usr/bin/env python
"""Phase 0 contract round-trip test (P0-2).

Verifies the frozen contracts in docs/plans/contracts/ are executable:
  * examples/ are deterministic (regenerating yields identical bytes)
  * doe_context.json + run_table.csv -> analysis_context.json via the adapter
  * every minimum provenance path from contracts README §3.1 is present
  * declared values are carried through verbatim (XR-01: no auto-infer fallback)
  * negative paths fail explicitly (missing column, duplicate run_id, aux file)

Runs the adapter in-process (no subprocess, no shell): it is the same code path
the CLI uses, with argv supplied directly.

Usage:
    uv run --project .claude/shared/scripts python docs/plans/contracts/roundtrip_test.py
Exit: 0 all green, 1 any failure.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

CONTRACTS = Path(__file__).resolve().parent
REPO = CONTRACTS.parents[2]
EXAMPLES = CONTRACTS / "examples"
SCRIPTS = REPO / ".claude" / "skills" / "industrial-doe-analyzer" / "scripts"

RESULTS: list[tuple[str, bool, str]] = []


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ADAPTER = _load("doe_context_adapter", SCRIPTS / "doe_context_adapter.py")
GEN = _load("contract_examples_gen", EXAMPLES / "generate_examples.py")


def record(cid: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((cid, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {cid}" + (f"  {detail}" if detail and not ok else ""))


def call_adapter(run_dir: Path) -> tuple[int, str, str]:
    """Invoke the adapter CLI entry point in-process; return (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = ADAPTER.main(["--run-dir", str(run_dir), "--json"])
        except SystemExit as exc:
            rc = int(exc.code) if isinstance(exc.code, int) else 1
    return rc, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------- determinism
def check_examples_deterministic() -> None:
    globs = ("*.csv", "*.json")
    before: dict[str, bytes] = {}
    for g in globs:
        for p in EXAMPLES.glob(g):
            before[p.name] = p.read_bytes()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = GEN.main()
    record("rt.generator_exit0", rc == 0, out.getvalue()[-300:])
    after: dict[str, bytes] = {}
    for g in globs:
        for p in EXAMPLES.glob(g):
            after[p.name] = p.read_bytes()
    same = before.keys() == after.keys() and all(before[k] == after[k] for k in before)
    record("rt.examples_deterministic", same, "generated examples differ between runs")


def prepare_run(tmp: Path, ctx_name: str, table_name: str) -> Path:
    run_dir = tmp / f"run-{ctx_name.replace('.json', '')}"
    (run_dir / "00_input").mkdir(parents=True, exist_ok=True)
    shutil.copy(EXAMPLES / ctx_name, run_dir / "00_input" / "doe_context.json")
    shutil.copy(EXAMPLES / table_name, run_dir / "00_input" / table_name)
    return run_dir


def check_design_only(tmp: Path) -> None:
    run_dir = prepare_run(tmp, "doe_context.json", "run_table.csv")
    code, _stdout, stderr = call_adapter(run_dir)
    record("rt.design_only_adapter_exit0", code == 0, stderr[-300:])
    ctx_file = run_dir / "00_input" / "analysis_context.json"
    if code != 0 or not ctx_file.is_file():
        record("rt.design_only_context_written", False, "analysis_context.json missing")
        return
    ctx = json.loads(ctx_file.read_text(encoding="utf-8"))

    record("rt.design_only_stage", ctx.get("data_stage") == "design_only",
           f"got {ctx.get('data_stage')}")
    record("rt.data_path_contract", ctx.get("data_path") == "00_input/run_table.csv",
           f"got {ctx.get('data_path')}")

    f0 = {f["col"]: f for f in ctx["factors"]}
    record("rt.unit_carried", f0["zone1_temp"]["unit"] == "\u00b0C",
           f"got {f0['zone1_temp']['unit']}")
    record("rt.constraints_carried", len(ctx.get("constraints") or []) == 3,
           f"got {len(ctx.get('constraints') or [])}")
    record("rt.hard_flag_carried",
           len([c for c in ctx["constraints"] if c.get("hard")]) == 2,
           "hard flags lost")
    record("rt.platform_ref_carried",
           (f0["zone1_temp"].get("platform_ref") or {}).get("plc_tag") == "TDO_Z4_SP",
           "platform_ref lost in adapter")
    record("rt.design_region_carried",
           (ctx.get("design_region") or {}).get("design_hull") == "ccd_star",
           "design_region lost")
    record("rt.ontology_mode_carried",
           (ctx.get("ontology") or {}).get("mode") == "auto",
           f"got {(ctx.get('ontology') or {}).get('mode')}")

    assigned = (ctx.get("provenance") or {}).get("assigned_by") or {}
    required = ["data_path", "ontology.data_stage", "constraints", "blocks", "covariates",
                "replicates_col", "run_order_col", "time_col"]
    for col in ("zone1_temp", "line_speed", "tdo_ratio"):
        required += [f"factors[{col}].col", f"factors[{col}].unit"]
    for col in ("thickness_um", "haze_pct"):
        required += [f"responses[{col}].col", f"responses[{col}].unit",
                     f"responses[{col}].lsl", f"responses[{col}].usl",
                     f"responses[{col}].target"]
    missing = [k for k in required if k not in assigned]
    record("rt.assigned_by_complete", not missing, f"missing: {missing}")
    record("rt.assigned_by_user_for_declared",
           assigned.get("factors[zone1_temp].unit") == "user",
           f"got {assigned.get('factors[zone1_temp].unit')}")
    record("rt.ontology_scene_key_user", assigned.get("ontology.scene_key") == "user",
           f"got {assigned.get('ontology.scene_key')}")

    hdr = (EXAMPLES / "run_table.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    cols = [f["col"] for f in ctx["factors"]] + [r["col"] for r in ctx["responses"]]
    record("rt.columns_match_table", all(c in hdr for c in cols),
           f"not in header: {[c for c in cols if c not in hdr]}")
    record("rt.units_block_present",
           (ctx.get("units") or {}).get("factors", {}).get("zone1_temp", {}).get("unit_status") == "valid",
           "units block missing/invalid")


def check_collected(tmp: Path) -> None:
    run_dir = prepare_run(tmp, "doe_context_collected.json", "run_table_collected.csv")
    code, _stdout, stderr = call_adapter(run_dir)
    record("rt.collected_adapter_exit0", code == 0, stderr[-300:])
    ctx_file = run_dir / "00_input" / "analysis_context.json"
    if code != 0 or not ctx_file.is_file():
        return
    txt = ctx_file.read_text(encoding="utf-8")
    ctx = json.loads(txt)
    record("rt.collected_stage", ctx.get("data_stage") == "collected",
           f"got {ctx.get('data_stage')}")
    record("rt.collected_data_path",
           ctx.get("data_path") == "00_input/run_table_collected.csv",
           f"got {ctx.get('data_path')}")
    record("rt.collected_replicates_col", ctx.get("replicates_col") == "replicate_group",
           f"got {ctx.get('replicates_col')}")
    record("rt.collected_index_cols", ctx.get("index_cols") == ["run_id", "design_point_id"],
           f"got {ctx.get('index_cols')}")

    code2, _, _ = call_adapter(run_dir)
    txt2 = ctx_file.read_text(encoding="utf-8")
    record("rt.adapter_deterministic", code2 == 0 and txt == txt2,
           "adapter output changed between runs")


def check_negatives(tmp: Path) -> None:
    # missing column -> explicit failure
    run_dir = prepare_run(tmp, "doe_context_collected.json", "run_table_collected.csv")
    ctx_path = run_dir / "00_input" / "doe_context.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    ctx["factors"][0]["col"] = "no_such_column"
    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False), encoding="utf-8")
    rc, _out, err = call_adapter(run_dir)
    record("rt.missing_column_rejected", rc == 2 and "MISSING_COLUMN" in err,
           f"rc={rc} err={err[-200:]}")

    # duplicate run_id -> explicit failure
    run_dir2 = prepare_run(tmp, "doe_context_collected.json", "run_table_collected.csv")
    tbl = run_dir2 / "00_input" / "run_table_collected.csv"
    lines = tbl.read_text(encoding="utf-8").splitlines()
    tbl.write_text("\n".join([lines[0], lines[1], lines[2], lines[2]] + lines[3:]) + "\n",
                   encoding="utf-8")
    rc2, _out2, err2 = call_adapter(run_dir2)
    record("rt.duplicate_run_id_rejected", rc2 == 2 and "DUPLICATE_RUN_ID" in err2,
           f"rc={rc2} err={err2[-200:]}")

    # no doe_context -> explicit failure
    run_dir3 = tmp / "run-empty"
    (run_dir3 / "00_input").mkdir(parents=True, exist_ok=True)
    rc3, _out3, _err3 = call_adapter(run_dir3)
    record("rt.no_context_rejected", rc3 == 2, f"rc={rc3}")

    # declared data_file that does not exist -> MISSING_RUN_TABLE, never a silent fallback
    run_dir4 = tmp / "run-auxonly"
    (run_dir4 / "00_input" / "exclusions").mkdir(parents=True, exist_ok=True)
    shutil.copy(EXAMPLES / "doe_context.json", run_dir4 / "00_input" / "doe_context.json")
    (run_dir4 / "00_input" / "exclusions" / "run_exclusions.csv").write_text(
        "run_id,reason\ndoerun-99,outlier\n", encoding="utf-8")
    rc4, _out4, err4 = call_adapter(run_dir4)
    record("rt.declared_table_missing_rejected", rc4 == 2 and "MISSING_RUN_TABLE" in err4,
           f"rc={rc4} err={err4[-200:]}")

    # no data_file declared, 00_input holds only aux files + exclusions/ -> NO_RUN_TABLE
    run_dir6 = tmp / "run-scan"
    (run_dir6 / "00_input" / "exclusions").mkdir(parents=True, exist_ok=True)
    ctx6 = json.loads((EXAMPLES / "doe_context.json").read_text(encoding="utf-8"))
    ctx6.pop("data_file", None)
    (run_dir6 / "00_input" / "doe_context.json").write_text(
        json.dumps(ctx6, ensure_ascii=False), encoding="utf-8")
    (run_dir6 / "00_input" / "run_manifest.json").write_text("{}", encoding="utf-8")
    (run_dir6 / "00_input" / "exclusions" / "run_exclusions.csv").write_text(
        "run_id,reason\ndoerun-99,outlier\n", encoding="utf-8")
    rc6, _out6, err6 = call_adapter(run_dir6)
    record("rt.aux_not_treated_as_data", rc6 == 2 and "NO_RUN_TABLE" in err6,
           f"rc={rc6} err={err6[-200:]}")

    # design_only declared but responses filled -> still respects declaration
    run_dir5 = tmp / "run-stage-declared"
    (run_dir5 / "00_input").mkdir(parents=True, exist_ok=True)
    ctx5 = json.loads((EXAMPLES / "doe_context_collected.json").read_text(encoding="utf-8"))
    ctx5["data_stage"] = "collected"
    (run_dir5 / "00_input" / "doe_context.json").write_text(
        json.dumps(ctx5, ensure_ascii=False), encoding="utf-8")
    shutil.copy(EXAMPLES / "run_table_collected.csv",
                run_dir5 / "00_input" / "run_table_collected.csv")
    rc5, _out5, _err5 = call_adapter(run_dir5)
    ctx5_out = json.loads((run_dir5 / "00_input" / "analysis_context.json").read_text(encoding="utf-8")) \
        if rc5 == 0 else {}
    record("rt.declared_stage_not_overridden",
           rc5 == 0 and ctx5_out.get("data_stage") == "collected",
           f"rc={rc5} stage={ctx5_out.get('data_stage')}")


def main() -> int:
    print("== contract round-trip (docs/plans/contracts) ==")
    check_examples_deterministic()
    with tempfile.TemporaryDirectory(prefix="doe-rt-") as td:
        tmp = Path(td)
        check_design_only(tmp)
        check_collected(tmp)
        check_negatives(tmp)

    failed = [c for c, ok, _ in RESULTS if not ok]
    print(f"\n[ROUNDTRIP] {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
          + (f" — FAILED: {failed}" if failed else " — ALL GREEN"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
