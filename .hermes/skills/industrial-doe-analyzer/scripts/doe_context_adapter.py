#!/usr/bin/env python
"""doe_context.json -> analysis_context.json adapter (contracts v1.1, Phase 0 P0-2).

Single entry point for turning a platform-authored `doe_context.json` (or a
hand-written one) plus its `run_table.csv` into the canonical resolved
`analysis_context.json` that the DOE analyzer consumes.

Contract: docs/plans/contracts/README.md §2/§3, run_table.md.
No auto-infer fallback for declared fields (XR-01): anything present in
doe_context.json is carried through verbatim and marked `assigned_by: user`.
Anything the script derives is marked `auto` and noted.

Usage:
    python doe_context_adapter.py --run-dir <DIR> [--context <doe_context.json>]
                                  [--data <run_table.csv>] [--out <analysis_context.json>]
                                  [--json]
Exit codes: 0 ok, 2 contract violation (missing column / duplicate run_id / bad json).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ADAPTER_VERSION = "1.1.0"

DATA_SUFFIXES = {".csv", ".tsv", ".json", ".xlsx", ".xls", ".parquet", ".feather"}
AUX_NAMES = {"doe_context.json", "analysis_context.json", "analysis_context.merged.json"}


def is_aux_name(name: str) -> bool:
    """Files that live in 00_input but are never the run table (contract §3)."""
    low = name.lower()
    return (name in AUX_NAMES
            or low.endswith("_manifest.json")
            or low.startswith("readme")
            or low.startswith("."))


def _contained(path: Path, root: Path) -> Path:
    """Resolve `path` and require it to stay inside `root` (defence in depth)."""
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    r = root.resolve()
    if r != p and r not in p.parents:
        raise ValueError(f"path outside run dir rejected: {path}")
    return p


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"BAD_JSON: {path}: {exc}") from exc


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def find_run_table(run_dir: Path, declared: str | None) -> Path:
    """Resolve the run table. An explicitly declared file always wins — but a declared
    file that does not exist is a hard contract violation, never a silent fallback.
    Without a declaration, scan 00_input skipping aux files and subdirectories."""
    in_dir = run_dir / "00_input"
    if declared:
        candidate = _contained(
            declared if Path(declared).is_absolute() else in_dir / declared, run_dir)
        if not candidate.is_file():
            raise SystemExit(f"MISSING_RUN_TABLE: {declared} (declared by doe_context.data_file) "
                             f"not found under {in_dir}")
        return candidate
    if not in_dir.is_dir():
        raise SystemExit(f"NO_INPUT_DIR: {in_dir}")
    for p in sorted(in_dir.iterdir()):
        if p.is_dir():
            continue
        if is_aux_name(p.name):
            continue
        if p.suffix.lower() in DATA_SUFFIXES:
            return p.resolve()
    raise SystemExit(f"NO_RUN_TABLE: no data file under {in_dir}")


def read_table(path: Path) -> tuple[list[str], list[dict]]:
    sep = "\t" if path.suffix.lower() == ".tsv" else ","
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines(), delimiter=sep)
    fields = list(reader.fieldnames or [])
    rows = [dict(r) for r in reader]
    return fields, rows


def infer_type(values: list[str]) -> str:
    seen = 0
    for v in values:
        s = (v or "").strip()
        if not s:
            continue
        seen += 1
        try:
            float(s)
        except ValueError:
            return "categorical"
    return "numeric" if seen else "numeric"


def build_analysis_context(doe_ctx: dict, run_dir: Path, run_table: Path,
                           run_dir_relative: str) -> dict:
    fields, rows = read_table(run_table)
    field_set = set(fields)
    assigned: dict[str, str] = {}
    notes: list[str] = []

    factors_in = doe_ctx.get("factors") or []
    responses_in = doe_ctx.get("responses") or []
    if len(factors_in) < 2:
        raise SystemExit("CONTRACT_VIOLATION: need >= 2 factors")
    if len(responses_in) < 1:
        raise SystemExit("CONTRACT_VIOLATION: need >= 1 response")

    # --- column presence (缺列拒绝) ---------------------------------------
    missing = []
    for f in factors_in:
        col = f.get("col") or f.get("name")
        if col not in field_set:
            missing.append(col)
    for r in responses_in:
        col = r.get("col") or r.get("name")
        if col not in field_set:
            missing.append(col)
    if missing:
        raise SystemExit("MISSING_COLUMN: " + ", ".join(str(m) for m in missing))

    # --- run_id uniqueness -------------------------------------------------
    run_id_col = "run_id" if "run_id" in field_set else None
    if run_id_col:
        seen: set[str] = set()
        for row in rows:
            rid = (row.get("run_id") or "").strip()
            if rid in seen:
                raise SystemExit(f"DUPLICATE_RUN_ID: {rid}")
            seen.add(rid)

    # --- factors -----------------------------------------------------------
    factors_out = []
    for f in factors_in:
        col = f.get("col") or f.get("name")
        col_values = [row.get(col, "") for row in rows]
        declared_type = f.get("type")
        ftype = declared_type or infer_type(col_values)
        if declared_type:
            assigned[f"factors[{col}].type"] = "user"
        else:
            assigned[f"factors[{col}].type"] = "auto"
            notes.append(f"factor {col}: type inferred as {ftype}")

        unit = f.get("unit")
        assigned[f"factors[{col}].unit"] = "user" if unit is not None else "auto"
        if unit is None:
            notes.append(f"factor {col}: unit not declared -> unit_status=missing")

        lo, hi = f.get("min"), f.get("max")
        numeric_vals = []
        for v in col_values:
            s = (v or "").strip()
            if not s:
                continue
            try:
                numeric_vals.append(float(s))
            except ValueError:
                pass
        if lo is None and numeric_vals:
            lo = min(numeric_vals)
        if hi is None and numeric_vals:
            hi = max(numeric_vals)

        factors_out.append({
            "col": col,
            "name": f.get("name") or col,
            "type": ftype,
            "unit": unit,
            "min": lo,
            "max": hi,
            "levels": f.get("levels"),
            "role": f.get("role"),
            "expected_sign": f.get("expected_sign"),
            "physical_meaning": f.get("physical_meaning"),
            "ontology_signal": f.get("ontology_signal"),
            "platform_ref": f.get("platform_ref"),
        })
        assigned[f"factors[{col}].col"] = "user"

    # --- responses ---------------------------------------------------------
    responses_out = []
    empty_responses = []
    for r in responses_in:
        col = r.get("col") or r.get("name")
        col_values = [row.get(col, "") for row in rows]
        non_empty = [v for v in col_values if (v or "").strip()]
        if not non_empty:
            empty_responses.append(col)
        unit = r.get("unit")
        assigned[f"responses[{col}].unit"] = "user" if unit is not None else "auto"
        if unit is None:
            notes.append(f"response {col}: unit not declared -> unit_status=missing")
        for bound in ("lsl", "usl", "target"):
            assigned[f"responses[{col}].{bound}"] = "user" if bound in r else "auto"
        responses_out.append({
            "col": col,
            "name": r.get("name") or col,
            "unit": unit,
            "goal": r.get("goal"),
            "lsl": r.get("lsl"),
            "usl": r.get("usl"),
            "target": r.get("target"),
            "weight": r.get("weight"),
            "ontology_signal": r.get("ontology_signal"),
            "platform_metric_ref": r.get("platform_metric_ref"),
        })
        assigned[f"responses[{col}].col"] = "user"

    # --- design-stage ------------------------------------------------------
    declared_stage = doe_ctx.get("data_stage") or (doe_ctx.get("ontology") or {}).get("data_stage")
    if declared_stage:
        data_stage = declared_stage
        assigned["ontology.data_stage"] = "user"
    else:
        data_stage = "design_only" if len(empty_responses) == len(responses_out) else "collected"
        assigned["ontology.data_stage"] = "auto"
        notes.append(f"data_stage inferred as {data_stage}")

    if empty_responses and data_stage == "collected":
        notes.append("responses with no measured cells: " + ", ".join(empty_responses))

    # --- constraints -------------------------------------------------------
    constraints = doe_ctx.get("constraints") or []
    assigned["constraints"] = "user" if constraints else "auto"

    # --- units roll-up -----------------------------------------------------
    f_units, r_units, conflicts = {}, {}, []
    for f in factors_out:
        f_units[f["col"]] = {
            "canonical": f["unit"], "display": f["unit"],
            "unit_status": "valid" if f["unit"] else "missing",
            "source": "doe_context" if f["unit"] else None,
        }
    for r in responses_out:
        r_units[r["col"]] = {
            "canonical": r["unit"], "display": r["unit"],
            "unit_status": "valid" if r["unit"] else "missing",
            "source": "doe_context" if r["unit"] else None,
        }
    # conflicting declarations between factor block and platform_ref hard_limits units
    for f in factors_out:
        ref = f.get("platform_ref") or {}
        if f["unit"] and ref.get("unit") and ref["unit"] != f["unit"]:
            conflicts.append({"factor_or_response": f["col"], "from": f["unit"],
                              "to": ref["unit"], "reason": "factor.unit != platform_ref.unit"})

    # --- ontology ----------------------------------------------------------
    ont_in = doe_ctx.get("ontology") or {}
    ontology = {
        "profile": ont_in.get("profile") or "doe",
        "mode": ont_in.get("mode") or "off",
        "scene_key": ont_in.get("scene_key"),
        "version": ont_in.get("version"),
        "data_stage": data_stage,
    }
    assigned["ontology.scene_key"] = "user" if ont_in.get("scene_key") else "auto"

    # --- derived grouping columns -----------------------------------------
    blocks = doe_ctx.get("blocks") or []
    covariates = doe_ctx.get("covariates") or []
    replicates_col = doe_ctx.get("replicates_col")
    run_order_col = doe_ctx.get("run_order_col")
    group_col = doe_ctx.get("group_col") or ("run_id" if run_id_col else None)
    time_col = doe_ctx.get("time_col")
    for key, val in (("blocks", blocks), ("covariates", covariates),
                     ("replicates_col", replicates_col), ("run_order_col", run_order_col),
                     ("group_col", group_col), ("time_col", time_col)):
        assigned[key] = "user" if val not in (None, []) else "auto"
    if not replicates_col and "replicate_group" in field_set:
        replicates_col = "replicate_group"
        assigned["replicates_col"] = "auto"
        notes.append("replicates_col defaulted to replicate_group")
    if not run_order_col and "run_order" in field_set:
        run_order_col = "run_order"
        assigned["run_order_col"] = "auto"
        notes.append("run_order_col defaulted to run_order")

    rel = f"00_input/{run_dir_relative}"
    assigned["data_path"] = "auto" if rel else "auto"

    raw = run_table.read_bytes()
    ctx = {
        "contract_version": "1.1",
        "experiment_id": doe_ctx.get("experiment_id"),
        "line_id": doe_ctx.get("line_id"),
        "product_id": doe_ctx.get("product_id"),
        "recipe_id": doe_ctx.get("recipe_id"),
        "objective": doe_ctx.get("objective"),
        "data_path": rel,
        "data_stage": data_stage,
        "design_type_declared": doe_ctx.get("design_type_declared"),
        "mode_override": doe_ctx.get("mode_override"),
        "factors": factors_out,
        "responses": responses_out,
        "blocks": blocks,
        "covariates": covariates,
        "index_cols": [c for c in ("run_id", "design_point_id") if c in field_set],
        "time_col": time_col,
        "group_col": group_col,
        "run_order_col": run_order_col,
        "replicates_col": replicates_col,
        "design_region": doe_ctx.get("design_region"),
        "constraints": constraints,
        "current_setpoint": doe_ctx.get("current_setpoint"),
        "baseline_source": doe_ctx.get("baseline_source"),
        "units": {"factors": f_units, "responses": r_units, "conflicts": conflicts},
        "ontology": ontology,
        "provenance": {
            "assigned_by": assigned,
            "platform": (doe_ctx.get("provenance") or {}).get("platform"),
            "created_by": (doe_ctx.get("provenance") or {}).get("created_by"),
            "created_at": (doe_ctx.get("provenance") or {}).get("created_at"),
            "adapter_version": ADAPTER_VERSION,
        },
        "inference": {"assigned_by": "user", "notes": notes},
        "_source": {"run_table_sha256": _sha256_bytes(raw),
                    "n_rows": len(rows), "columns": fields},
    }
    return ctx


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="doe_context_adapter.py")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--context", default=None,
                    help="doe_context.json (default: <run-dir>/00_input/doe_context.json)")
    ap.add_argument("--data", default=None, help="run table override")
    ap.add_argument("--out", default=None,
                    help="output path (default: <run-dir>/00_input/analysis_context.json)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"ERROR: run dir not found: {run_dir}", file=sys.stderr)
        return 2

    ctx_path = (_contained(args.context, run_dir) if args.context
                else run_dir / "00_input" / "doe_context.json")
    if not ctx_path.is_file():
        print(f"ERROR: doe_context not found: {ctx_path}", file=sys.stderr)
        return 2

    try:
        doe_ctx = _read_json(ctx_path)
        declared_data = args.data or doe_ctx.get("data_file")
        # data_file is relative to 00_input per contract
        run_table = find_run_table(run_dir, declared_data)
        run_table.relative_to(run_dir.resolve())
    except (ValueError, SystemExit) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rel = run_table.relative_to(run_dir.resolve()).as_posix()
    if not rel.startswith("00_input/"):
        rel = "00_input/" + run_table.name
    rel_name = rel[len("00_input/"):]

    try:
        ctx = build_analysis_context(doe_ctx, run_dir, run_table, rel_name)
    except SystemExit as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    out_path = _contained(args.out, run_dir) if args.out else run_dir / "00_input" / "analysis_context.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {"out": str(out_path), "data_path": ctx["data_path"],
               "n_factors": len(ctx["factors"]), "n_responses": len(ctx["responses"]),
               "data_stage": ctx["data_stage"],
               "unit_status": {"factors": {k: v["unit_status"] for k, v in ctx["units"]["factors"].items()},
                               "responses": {k: v["unit_status"] for k, v in ctx["units"]["responses"].items()}}}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"[adapter] {ctx['data_path']} -> {out_path}")
        print(f"[adapter] factors={summary['n_factors']} responses={summary['n_responses']} "
              f"stage={ctx['data_stage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
