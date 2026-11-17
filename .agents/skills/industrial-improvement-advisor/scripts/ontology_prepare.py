#!/usr/bin/env python
"""ontology_prepare.py — improvement-advisor ontology stage: lookup → reuse/extend/build.

Thin shell of the watch-family prepare built on
`.claude/shared/scripts/ontology_prepare_common.py` with PROFILE="improvement".

Declarations come from (all optional, deterministic):
  1. `00_input/objective.json` — targets[].metric → inspection_signals (role=target);
     levers[] → control_variables (role=control, control_type=setpoint);
     kpis[] → inspection_signals; constraints[].param → presence only.
  2. `00_input/report_context.json` (same shape the stability family reads) —
     units / spec_limits / parameter_cols / inspection_cols / time_col / group_col.
  3. Header probe of the run table + unique-hit physics-dictionary matching
     (contributes unit / physical_meaning / governing_law, knowledge_source=auto_inferred).

Dictionary discipline (do NOT weaken):
  * `parameter_to_physics.json` contributes physical_unit_SI / physical_quantity /
    governing_law ONLY on a unique normalized candidate (zero or multiple → unmatched,
    never a guess);
  * its `typical_ranges` are reference bands, never normal_range — only
    user/context-declared spec_limits become normal_range (knowledge_source=user_provided);
  * no direction declaration → relationships stay EMPTY (no invented causal edges);
  * rag_used / web_used are always False on this deterministic path.

Outputs: `01_ontology/{ontology.json, ontology_brief.json, ontology_brief.md,
ontology_coverage.json}`; store profile=improvement (publish on build/extend,
reuse on exact lookup).

CLI:
  python ontology_prepare.py --run-dir DIR [--data PATH] [--context PATH]
      [--ontology PATH] [--mode auto|full|reuse|extend|off] [--scene KEY]
      [--store-dir DIR] [--json]
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

import ontology_prepare_common as oc  # noqa: E402

PROFILE = "improvement"
ENGINE = "industrial-ontology-builder"
BRIEF_CONTRACT_VERSION = "1.0"
DATA_STAGE = "collected"
DATA_CANDIDATES = ("data.csv", "preprocessed_data.csv")
TIME_COLUMN_NAMES = ("time", "timestamp", "ts", "datetime", "date", "_dt", "t")
VALIDATOR = SHARED_SCRIPTS / "validate.mjs"
ONTOLOGY_SCHEMA = (REPO_ROOT / ".claude" / "skills" / "industrial-ontology-builder"
                   / "schemas" / "ontology_schema.json")


def _sanitize_scene_key(value):
    if value in (None, ""):
        return None
    key = re.sub(r"[^A-Za-z0-9._-]", "_", str(value)).strip("_")
    return key or None


def _read_json(path):
    return oc.read_json(path)


def _objective(run_dir):
    p = Path(run_dir) / "00_input" / "objective.json"
    return _read_json(p) if p.is_file() else {}


def _physics_entries():
    families = oc.load_physics_families()
    return families if isinstance(families, dict) else {}


def _match_entry(entries, col):
    """Unique-hit dictionary match (normalized); never a guess.

    `match_physics_entry` returns {"family","entry"} or None — unwrap to the
    entry dict so callers read physical_unit_SI/physical_quantity/governing_law.
    """
    hit = oc.match_physics_entry(entries, col)
    if not isinstance(hit, dict):
        return None
    entry = hit.get("entry")
    return entry if isinstance(entry, dict) else None


def _build_prior(run_dir, table, objective, context, scene_key, context_fp):
    """Deterministic declared-prior ontology from objective + context + header probe."""
    cols = [str(c) for c in (table.get("columns") or []) if str(c).strip()]
    units_decl = context.get("units") if isinstance(context.get("units"), dict) else {}
    spec_limits = context.get("spec_limits") if isinstance(context.get("spec_limits"), dict) else {}
    time_col = context.get("time_col") or next(
        (c for c in cols if c.strip().lower() in TIME_COLUMN_NAMES), None)
    group_col = context.get("group_col")
    target_cols = [t.get("metric") for t in (objective.get("targets") or [])
                   if isinstance(t, dict) and t.get("metric")]
    target_cols += list(context.get("inspection_cols") or [])
    target_cols += list(objective.get("kpis") or [])
    lever_cols = list(context.get("parameter_cols") or []) + list(objective.get("levers") or [])
    for c in (objective.get("constraints") or []):
        if isinstance(c, dict) and c.get("param") and c.get("param") not in lever_cols:
            lever_cols.append(c.get("param"))
    target_set = {str(c).strip() for c in target_cols if str(c).strip()}
    lever_set = {str(c).strip() for c in lever_cols if str(c).strip()} - target_set
    entries = _physics_entries()

    ont = oc.empty_ontology_skeleton(scene_name=scene_key,
                                     process_type=context.get("process_type") or "production_line")
    seen = set()
    for col in cols:
        if col == time_col or col == group_col:
            # metadata_columns role enum is [batch_id, product_code, timestamp, operator]
            meta_role = "timestamp" if col == time_col else "batch_id"
            ont["signals"]["metadata_columns"].append(
                {"name": col, "column": col, "role": meta_role})
            continue
        if col in seen:
            continue
        seen.add(col)
        is_target = col in target_set
        is_lever = col in lever_set and not is_target
        role_bucket = "inspection_signals" if is_target else (
            "control_variables" if is_lever else "process_parameters")
        schema_role = "target" if is_target else ("control" if is_lever else "predictor")
        unit = units_decl.get(col)
        hit = _match_entry(entries, col)
        knowledge_source = "auto_inferred"
        confidence = "INFERRED"
        physical_meaning = None
        governing_law = None
        if hit:
            unit = unit or hit.get("physical_unit_SI")
            physical_meaning = hit.get("physical_quantity")
            governing_law = hit.get("governing_law")
        normal_range = None
        if isinstance(spec_limits.get(col), (list, tuple)) and len(spec_limits[col]) == 2:
            normal_range = [spec_limits[col][0], spec_limits[col][1]]
            knowledge_source = "user_provided"
            confidence = "KNOWN"
        elif col in units_decl:
            knowledge_source = "user_provided" if is_target or is_lever else knowledge_source
        sig = oc.make_watch_signal(
            column=col, role=schema_role, unit=unit, normal_range=normal_range,
            physical_meaning=physical_meaning, governing_law=governing_law,
            knowledge_source=knowledge_source, confidence=confidence,
            inference_basis=("declared by objective.json / report_context"
                             if knowledge_source == "user_provided" else
                             "auto prior from shipped physics dictionary" if hit else
                             "declared by objective/context role, no dictionary hit"),
            schema_role=schema_role)
        if is_lever:
            sig["control_type"] = "setpoint"
        ont["signals"][role_bucket].append(sig)
        if unit:
            ont["metadata"]["units"][col] = unit
    ont["provenance"] = oc.standard_provenance(
        profile=PROFILE, engine=ENGINE, build_mode="prior_knowledge",
        data_stage=DATA_STAGE,
        source="declared prior from objective.json/report_context + table probe + "
               "physics dictionary unique hits; no RAG/web")
    ont["improvement"] = {
        "profile": PROFILE,
        "scene_key": scene_key,
        "data_stage": DATA_STAGE,
        "levers": sorted(lever_set & seen),
        "kpis": sorted(target_set & seen),
        "objective_present": bool(target_cols),
    }
    return ont


def _extend_ontology(stored, prior, scene_key):
    """Merge a stored asset with the new declaration prior (declarations win)."""
    merged = json.loads(json.dumps(prior))
    stored_signals = []
    if isinstance(stored, dict):
        for bucket in ("inspection_signals", "process_parameters", "control_variables",
                       "events", "metadata_columns"):
            stored_signals.extend((stored.get("signals") or {}).get(bucket) or [])
    prior_cols = {s.get("column") for bucket in merged["signals"].values() for s in bucket}
    for sig in stored_signals:
        col = sig.get("column")
        if col and col not in prior_cols:
            bucket = "metadata_columns" if sig.get("role") == "metadata" else (
                "control_variables" if sig.get("role") == "control" else (
                    "inspection_signals" if sig.get("role") == "target" else "process_parameters"))
            merged["signals"][bucket].append(sig)
            prior_cols.add(col)
    rels = stored.get("relationships") if isinstance(stored, dict) else []
    if rels:
        merged["relationships"] = rels
    merged["improvement"]["scene_key"] = scene_key
    if isinstance(stored.get("provenance"), dict):
        stored["provenance"]["build_mode"] = "extend"
        merged["provenance"] = stored["provenance"]
    return merged


def _cp2_check(ontology_path):
    if not ontology_path.is_file():
        return False, "ontology.json missing"
    raw = ontology_path.read_bytes()
    if len(raw) < 1024:
        return False, f"ontology.json too small ({len(raw)}B < 1024B)"
    try:
        proc = subprocess.run(
            ["node", str(VALIDATOR), str(ONTOLOGY_SCHEMA), str(ontology_path)],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"validator unavailable: {exc}"
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "").strip()[:400]
    return True, "schema ok"


def _build_brief(ontology, rows, scene_key, context_fp, build_mode, source_note,
                 lookup_status, version, elapsed_ms):
    cols = []
    for sig, bucket in ((s, b) for b in ("inspection_signals", "process_parameters",
                                         "control_variables") for s in
                        ontology["signals"].get(b) or []):
        col = sig.get("column")
        hit = sig.get("physical_meaning") or None
        status = "known" if (sig.get("knowledge_source") == "user_provided"
                             and sig.get("normal_range")) else (
            "same_domain" if hit else "unknown")
        cols.append({"col": col, "bucket": bucket, "schema_role": sig.get("role"),
                     "unit": sig.get("unit"), "unit_status": "declared" if sig.get("unit") else "undeclared",
                     "mechanism_status": status,
                     "knowledge_source": sig.get("knowledge_source"),
                     "normal_range": sig.get("normal_range")})
    declared = sum(1 for c in cols if c["knowledge_source"] == "user_provided")
    matched = sum(1 for c in cols if c["mechanism_status"] != "unknown")
    return {
        "contract_version": BRIEF_CONTRACT_VERSION,
        "artifact": "ontology_brief",
        "profile": PROFILE,
        "scene_key": scene_key,
        "context_fp": context_fp,
        "data_stage": DATA_STAGE,
        "build_mode": build_mode,
        "source_note": source_note,
        "lookup": lookup_status,
        "ontology_version": version,
        "elapsed_ms": elapsed_ms,
        "columns": cols,
        "coverage": {"declared_columns": declared, "total_columns": len(cols),
                     "mechanism_matched": matched,
                     "mechanism_unknown": len(cols) - matched},
        "limitations": [
            "声明先验本体：不声称已观测行为（observed_data_behavior=NOT_APPLICABLE）。",
            "relationships 为空 = 无方向声明，未造因果边。",
            "词典 typical_ranges 是参考区间（非规格）；normal_range 仅来自用户声明。",
            "rag_used/web_used 恒为 false（确定性路径）。",
        ],
        "generated_by": "ontology_prepare.py",
        "generated_at": oc.now_iso(),
    }


def _write_brief(run_dir, brief):
    out_dir = Path(run_dir) / "01_ontology"
    json_path = oc.write_json_strict(out_dir / "ontology_brief.json", brief)
    lines = [
        f"# 本体简报（profile={PROFILE}）",
        "",
        f"- 场景: {brief['scene_key']} · 构建方式: {brief['build_mode']} · lookup: {brief['lookup']}",
        f"- 覆盖: {brief['coverage']['mechanism_matched']}/{brief['coverage']['total_columns']} 列有机制先验",
        "",
        "## 列角色与单位",
        "",
        "| 列 | 角色 | 单位 | 机制先验 | 来源 |",
        "|---|---|---|---|---|",
    ]
    for c in brief["columns"]:
        lines.append(f"| {c['col']} | {c['schema_role']} | {c['unit'] or '未声明'} | "
                     f"{c['mechanism_status']} | {c['knowledge_source']} |")
    lines += ["", "## 局限", ""] + [f"- {x}" for x in brief["limitations"]]
    md_path = out_dir / "ontology_brief.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(json_path), str(md_path)


def prepare(run_dir, *, data=None, context=None, mode="auto", scene_key=None,
            store_dir=None, ontology=None):
    started = time.perf_counter()
    run_dir_v = Path(run_dir).resolve()
    out_dir = run_dir_v / "01_ontology"
    out_dir.mkdir(parents=True, exist_ok=True)

    if mode == "off":
        return {"action": "skipped", "mode": "off", "wrote": [], "elapsed_ms": 0,
                "reason": "ontology mode=off"}

    objective = _objective(run_dir_v)
    # Documented discovery order (first hit wins): explicit --ontology arg >
    # run 00_input/ontology.json (user/agent-supplied) > existing 01_ontology.
    if not ontology:
        for candidate in (run_dir_v / "00_input" / "ontology.json",
                          out_dir / "ontology.json"):
            if candidate.is_file():
                ontology = str(candidate)
                break
    context_path = Path(context) if context else (run_dir_v / "00_input" / "report_context.json")
    ctx = _read_json(context_path) if context_path.is_file() else {}
    data_path = oc.resolve_data_path(run_dir_v, data, ctx, candidate_names=DATA_CANDIDATES)
    table = oc.load_table_columns(str(data_path)) if data_path else {}
    if isinstance(table, dict):
        cols = table.get("columns") or []
        if cols and str(cols[0]).startswith("\ufeff"):
            cols[0] = cols[0].lstrip("\ufeff")

    scene = _sanitize_scene_key(
        scene_key or (ctx.get("scene_key") if isinstance(ctx, dict) else None)
        or (ctx.get("line_id") if isinstance(ctx, dict) else None)
        or (Path(data_path).stem if data_path
            and Path(data_path).stem not in ("data", "preprocessed_data", "run_table")
            else None)
        or run_dir_v.name)

    # declaration fingerprint (watch-context-v1, mirrored by ontology_store.mjs)
    decl_cols = []
    units_decl = ctx.get("units") if isinstance(ctx.get("units"), dict) else {}
    spec_limits = ctx.get("spec_limits") if isinstance(ctx.get("spec_limits"), dict) else {}
    targets = [t.get("metric") for t in (objective.get("targets") or [])
               if isinstance(t, dict) and t.get("metric")]
    levers = list(objective.get("levers") or [])
    for col in (table.get("columns") or []):
        role = "target" if col in targets else ("control" if col in levers else "parameter")
        lsl, usl = (spec_limits.get(col) or [None, None])[:2] if isinstance(
            spec_limits.get(col), (list, tuple)) else (None, None)
        decl_cols.append({"col": col, "role": role, "unit": units_decl.get(col),
                          "lsl": lsl, "usl": usl})
    context_fp = oc.compute_watch_context_fp({"columns": decl_cols, "windows": []})

    store = oc.resolve_store_dir(store_dir)
    lookup = oc.lookup(store, profile=PROFILE, scene_key=scene, context_fp=context_fp)
    action, action_note = oc.resolve_action(mode, lookup.get("status"))

    prior = _build_prior(run_dir_v, table or {}, objective, ctx, scene, context_fp)
    adopted = None
    if ontology:
        p = Path(ontology)
        if not p.is_file():
            raise SystemExit(f"ONTOLOGY_NOT_FOUND: {ontology}")
        adopted = _read_json(p)
        if not (isinstance(adopted, dict) and adopted.get("scene") and adopted.get("signals")):
            raise SystemExit(f"ONTOLOGY_INVALID: {ontology} (scene+signals required)")

    run_ontology_path = out_dir / "ontology.json"
    store_result, version = {}, None
    source_note = action_note
    if action == oc.ACTION_REUSED and lookup.get("entry"):
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        ontology_for_run = _read_json(stored_path) if stored_path.is_file() else prior
        version = lookup["entry"].get("version")
        build_mode = "reuse"
        source_note = source_note or f"reused store asset {lookup['entry'].get('path')}"
    elif action == oc.ACTION_EXTENDED and lookup.get("entry"):
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        stored = _read_json(stored_path) if stored_path.is_file() else {}
        ontology_for_run = _extend_ontology(stored, prior, scene)
        build_mode = "extend"
        source_note = source_note or f"extended store asset {lookup['entry'].get('path')}"
    elif adopted is not None:
        ontology_for_run = adopted
        build_mode = "full"
        source_note = source_note or "adopted explicit --ontology path"
    else:
        ontology_for_run = prior
        build_mode = "prior_knowledge"
        source_note = source_note or (
            "declared-prior build (objective.json/report_context declarations + "
            "table probe + physics dictionary unique hits; no RAG/web)")

    oc.write_json_strict(run_ontology_path, ontology_for_run)

    # CP-2 gate BEFORE the store sees the asset (an invalid build must never publish)
    cp2_ok, cp2_detail = _cp2_check(run_ontology_path)
    if not cp2_ok:
        raise SystemExit(f"ONTOLOGY_CP2_FAILED: {run_ontology_path} — {cp2_detail}")

    if action != oc.ACTION_REUSED:
        publish_args = ["publish", "--run-dir", str(run_dir_v), "--scene", scene,
                        "--profile", PROFILE, "--context-fp", context_fp,
                        "--build-mode", str(build_mode), "--data-stage", DATA_STAGE]
        if data_path and Path(data_path).suffix.lower() in (".csv", ".tsv"):
            publish_args += ["--data-file", str(data_path)]
        try:
            published = oc.store_call(*publish_args, store_dir=store)
            store_result = {"published": True,
                            "entry_version": published.get("version"),
                            "deduped": bool(published.get("deduped"))}
            version = published.get("version")
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            store_result = {"published": False, "error": str(exc)}
            version = None

    elapsed_ms = oc.timed_result(started)
    brief = _build_brief(ontology_for_run, decl_cols, scene, context_fp, build_mode,
                         source_note, lookup.get("status"), version, elapsed_ms)
    brief_json, brief_md = _write_brief(run_dir_v, brief)
    coverage_path = oc.write_json_strict(out_dir / "ontology_coverage.json", {
        "contract_version": BRIEF_CONTRACT_VERSION,
        "artifact": "ontology_coverage",
        "scene_key": scene,
        "profile": PROFILE,
        "context_fp": context_fp,
        "ontology_version": version,
        "columns": brief["columns"],
        "coverage": brief["coverage"],
        "generated_by": "ontology_prepare.py",
        "generated_at": oc.now_iso(),
    })
    prov = ontology_for_run.get("provenance") if isinstance(ontology_for_run, dict) else {}
    return {
        "action": action,
        "ontology_path": str(run_ontology_path),
        "brief_json": brief_json,
        "brief_md": brief_md,
        "coverage_path": str(coverage_path),
        "version": version,
        "context_fp": context_fp,
        "scene_key": scene,
        "data_stage": DATA_STAGE,
        "elapsed_ms": elapsed_ms,
        "rag_used": bool((prov or {}).get("rag_used", False)),
        "web_used": bool((prov or {}).get("web_used", False)),
        "build_mode": build_mode,
        "source_note": source_note,
        "cp2_floor_ok": bool(cp2_ok),
        "store": store_result,
        "coverage": brief["coverage"],
        "lookup": lookup.get("status"),
        "mode": mode,
        "wrote": [str(run_ontology_path), brief_json, brief_md, str(coverage_path)],
        "store_dir": str(store),
    }


def _cli():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    return oc.cli_main(
        lambda args: prepare(args.run_dir, data=args.data, context=args.context,
                             mode=args.mode, scene_key=args.scene,
                             store_dir=args.store_dir, ontology=args.ontology),
        prog_desc="improvement-advisor ontology stage: lookup → reuse/extend/build",
        extra_args=((("--ontology",),
                     {"default": None,
                      "help": "adopt this ontology.json verbatim (must exist, be valid "
                              "JSON and carry scene+signals; otherwise SystemExit)"}),),
    )


if __name__ == "__main__":
    raise SystemExit(_cli())
