#!/usr/bin/env python
"""ontology_prepare.py — stability-report ontology stage: lookup → reuse/extend/build.

The watch-family twin of the DOE ontology stage (doe_ontology_prepare.py), built
on the shared core in `.claude/shared/scripts/ontology_prepare_common.py`:

    prepare(run_dir, *, data=None, context=None, mode="auto", scene_key=None,
            store_dir=None, ontology=None) -> dict
        -> {action: "reused"|"extended"|"built"|"skipped", ontology_path,
            brief_json, brief_md, coverage_path, version, context_fp, scene_key,
            data_stage, elapsed_ms, rag_used, web_used, build_mode, source_note,
            ontology_bytes, cp2_floor_ok, store, coverage, lookup, mode, wrote,
            rag_used_by_prepare, web_used_by_prepare, store_dir}

Flow:
  1. declarations from `report_context` (spec_limits / parameter_cols /
     inspection_cols / units / time_col / group_col) + a header probe of the
     run table (load_table_columns) + unique-hit physics-dictionary matching;
  2. context_fp = watch-context fingerprint of that declaration contract
     (mirrored 1:1 by computeWatchContextFingerprint() in ontology_store.mjs);
  3. store lookup (profile=stability, scene_key, context_fp):
       exact      → reuse the stored ontology verbatim (fast path, zero RAG/web)
       scene_only → extend the stored ontology (declarations changed)
       miss       → build a deterministic declared-prior ontology;
  4. CP-2 gate: `validate.mjs ontology_schema.json ontology.json` exit 0 AND
     ≥1024 bytes, else SystemExit;
  5. write the 01_ontology/ four-piece (ontology.json + ontology_brief.json/.md
     + ontology_coverage.json); store publish is the single write path
     (ontology_store.mjs). Store commit is ACTION-DRIVEN: only action=reused
     goes through commit_to_store — a fresh build/extend must never be
     silently overwritten by an old store asset on an exact lookup.

Dictionary discipline (plan v2 principle 2 — do NOT weaken):
  * `parameter_to_physics.json` contributes physical_unit_SI / physical_quantity
    / governing_law ONLY, on a unique normalized candidate (zero or multiple
    candidates → mapping_status="unmatched", never a guess);
  * its `typical_ranges` are textbook REFERENCE BANDS: they land in the
    ontology's free `watch.reference_bands` block and the brief's
    "参考区间（非规格）" section — never in normal_range, never in a Cpk spec;
  * only user/context-declared spec_limits become signal normal_range
    (knowledge_source="user_provided", confidence="KNOWN").

Honesty rules:
  * a prior build never claims measured behaviour (`observed_data_behavior =
    "NOT_APPLICABLE"`, `behavior_match = "UNVERIFIED"`);
  * `rag_used` / `web_used` are always False on these deterministic paths and
    are reported from the ontology provenance, never invented;
  * relationships stay EMPTY — with no direction declaration no causal edge is
    fabricated; columns with no declaration and no dictionary hit are disclosed
    as unmatched (unit undeclared), not silently dropped.

CLI:
  python ontology_prepare.py --run-dir DIR [--data PATH] [--context PATH]
      [--ontology PATH] [--mode auto|full|reuse|extend|off] [--scene KEY]
      [--store-dir DIR] [--json]
"""

import copy
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]          # …/industrial-line-stability-report/scripts → repo root
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))

import ontology_prepare_common as oc  # noqa: E402

PROFILE = "stability"
ENGINE = "industrial-ontology-builder"
BRIEF_CONTRACT_VERSION = "1.0"
DATA_STAGE = "collected"
DATA_CANDIDATES = ("data.csv", "preprocessed_data.csv")

# keep in sync with lstcore/_io.py INSPECTOR_COLUMNS (structural time names);
# "t" is added for header probes — it is this skill's conventional bare axis
# name (template/fixtures) and must never fall through to dictionary matching
TIME_COLUMN_NAMES = ("time", "timestamp", "ts", "datetime", "date", "_dt", "t")

VALIDATOR = SHARED_SCRIPTS / "validate.mjs"


# ---------------------------------------------------------------- path utils

def _sanitize_scene_key(value):
    if value in (None, ""):
        return None
    key = re.sub(r"[^A-Za-z0-9._-]", "_", str(value)).strip("_")
    return key or None


def _strip_bom(table):
    """load_table_columns reads utf-8 (not utf-8-sig): the preprocessor writes
    utf-8-sig CSVs, so a leading BOM would corrupt the first header name."""
    if not isinstance(table, dict):
        return table
    cols = table.get("columns") or []
    if cols and isinstance(cols[0], str) and cols[0].startswith("\ufeff"):
        rename = {cols[0]: cols[0].lstrip("\ufeff")}
        table = dict(table)
        table["columns"] = [rename.get(c, c) for c in cols]
        table["total"] = {rename.get(k, k): v for k, v in (table.get("total") or {}).items()}
        table["empty"] = {rename.get(k, k): v for k, v in (table.get("empty") or {}).items()}
    return table


# ─────────────────────────────────────────── 声明先验本体（deterministic） ────

def _physics_entries():
    """match_physics_entry iterates {family: entry}; parameter_to_physics.json
    nests those families under `parameters` (the other top-level keys are file
    metadata). Fields used per family: physical_unit_SI / physical_quantity /
    governing_law / synonyms / typical_ranges."""
    data = oc.load_physics_dictionary()
    if not isinstance(data, dict):
        return {}
    params = data.get("parameters")
    return params if isinstance(params, dict) else data


def _user_spec(spec_limits, col):
    s = spec_limits.get(col)
    if not isinstance(s, dict):
        return None
    if s.get("lsl") is None and s.get("usl") is None and s.get("target") is None:
        return None
    return {"lsl": s.get("lsl"), "usl": s.get("usl"), "target": s.get("target")}


def build_prior_ontology(ctx, table, *, scene_key, build_mode):
    """Deterministic declared-prior ontology (zero fabrication).

    Column precedence (declaration first, then dictionary, then disclosure):
      1. context inspection_cols / parameter_cols → user_provided signals
         (normal_range ONLY from the context's own spec_limits);
      2. context time_col / group_col (+ structural time names) →
         metadata columns (schema role: timestamp / batch_id);
      3. unique physics-dictionary hit → auto_inferred signal (unit / meaning /
         governing law only; typical_ranges stay a watch reference band);
      4. everything else → NO signal, disclosed as unmatched (unit undeclared).

    Returns (ontology, rows) — `rows` is the per-column mapping ledger the
    brief/coverage artifacts are projected from.
    """
    ctx = ctx if isinstance(ctx, dict) else {}
    spec_limits = {str(k): v for k, v in (ctx.get("spec_limits") or {}).items()
                   if isinstance(v, dict)}
    units_decl = {str(k): str(v) for k, v in (ctx.get("units") or {}).items()
                  if v not in (None, "")}
    declared_insp = [str(c) for c in (ctx.get("inspection_cols") or [])]
    declared_param = [str(c) for c in (ctx.get("parameter_cols") or [])]
    time_col = str(ctx["time_col"]) if ctx.get("time_col") else None
    group_col = str(ctx["group_col"]) if ctx.get("group_col") else None
    dictionary = _physics_entries()

    table_cols = [str(c) for c in (table or {}).get("columns") or []]
    table_set = set(table_cols)

    signals = {"inspection_signals": [], "process_parameters": [],
               "control_variables": [], "events": [], "metadata_columns": []}
    rows = []
    reference_bands = {}
    units_effective = {}

    def record(col, *, watch_role, schema_role, unit, unit_status, ks, conf,
               spec, meaning, law, status, reason, in_ontology):
        rows.append({
            "col": col, "watch_role": watch_role, "schema_role": schema_role,
            "in_ontology": in_ontology,
            "unit": unit, "unit_status": unit_status,
            "knowledge_source": ks, "confidence": conf,
            "spec": spec, "reference_band": reference_bands.get(col),
            "physical_meaning": meaning, "governing_law": law,
            "mapping_status": status, "mapping_reason": reason,
        })
        if unit:
            units_effective[col] = unit

    def attach_reference_band(col):
        """watch.reference_bands is the ONLY home of dictionary typical_ranges."""
        if col in reference_bands:
            return
        match = oc.match_physics_entry(dictionary, col)
        if not match:
            return
        bands = oc.dictionary_reference_band(match["entry"])
        if bands:
            reference_bands[col] = {
                "family": match["family"],
                "bands": bands,
                "source": "parameter_to_physics.json (typical_ranges)",
                "note": "参考区间（非规格）——来自教科书先验，永不进入 normal_range/spec/Cpk",
            }

    declared = [(c, "inspection", "target", "inspection_signals") for c in declared_insp]
    declared += [(c, "parameter", "predictor", "process_parameters") for c in declared_param]
    seen_declared = set()

    for col, watch_role, schema_role, bucket in declared:
        if col in seen_declared:
            continue
        seen_declared.add(col)
        spec = _user_spec(spec_limits, col)
        unit = units_decl.get(col)
        if col not in table_set and table_cols:
            record(col, watch_role=watch_role, schema_role=schema_role, unit=unit,
                   unit_status="declared" if unit else "undeclared",
                   ks="user_provided", conf="KNOWN", spec=spec, meaning=None, law=None,
                   status="unmatched",
                   reason=(f"上下文声明的{watch_role}列 '{col}' 不在本期数据表中"
                           "（declared but absent from the run table）"),
                   in_ontology=False)
            continue
        sig = oc.make_watch_signal(
            column=col, role=watch_role, schema_role=schema_role, unit=unit,
            normal_range=([spec["lsl"], spec["usl"]] if spec and spec["lsl"] is not None
                          and spec["usl"] is not None else None),
            knowledge_source="user_provided", confidence="KNOWN",
            inference_basis=f"declared in report_context as {watch_role} column")
        signals[bucket].append(sig)
        attach_reference_band(col)
        record(col, watch_role=watch_role, schema_role=schema_role, unit=unit,
               unit_status="declared" if unit else "undeclared",
               ks="user_provided", conf="KNOWN", spec=spec, meaning=None, law=None,
               status="matched",
               reason=f"上下文声明为{watch_role}列（report_context declaration）",
               in_ontology=True)

    meta_names = {n for n in (time_col, group_col) if n}
    meta_names.update(TIME_COLUMN_NAMES)
    for col in table_cols:
        if col in seen_declared:
            continue
        # a context units entry is a user declaration about this column even
        # when its role stays unmapped — it flows into the row (and thus the
        # reuse fingerprint + metadata.units) instead of being dropped
        declared_unit = units_decl.get(col)
        if col in meta_names:
            role = "timestamp" if col == time_col or col in TIME_COLUMN_NAMES else "batch_id"
            signals["metadata_columns"].append({
                "name": col, "column": col, "role": role,
                "description": ("时间轴列（watch role: time）" if role == "timestamp"
                                else "分组列（watch role: group）"),
            })
            record(col, watch_role=("time" if role == "timestamp" else "group"),
                   schema_role=None, unit=declared_unit,
                   unit_status="declared" if declared_unit else "undeclared",
                   ks=None, conf=None, spec=None, meaning=None, law=None,
                   status="matched",
                   reason="结构列（时间轴/分组），不参与稳定性评分",
                   in_ontology=True)
            continue
        match = oc.match_physics_entry(dictionary, col)
        if match:
            entry = match["entry"]
            dict_unit = str(entry.get("physical_unit_SI")) if entry.get("physical_unit_SI") else None
            unit = declared_unit or dict_unit
            meaning = str(entry.get("physical_quantity")) if entry.get("physical_quantity") else None
            law = str(entry.get("governing_law")) if entry.get("governing_law") else None
            sig = oc.make_watch_signal(
                column=col, role="parameter", schema_role="predictor", unit=unit,
                physical_meaning=meaning, governing_law=law,
                knowledge_source="auto_inferred", confidence="INFERRED",
                inference_basis=f"unique hit in shipped physics dictionary ({match['family']})")
            signals["process_parameters"].append(sig)
            attach_reference_band(col)
            record(col, watch_role="parameter", schema_role="predictor", unit=unit,
                   unit_status=("declared" if declared_unit
                                else "dictionary_inferred" if unit else "undeclared"),
                   ks="auto_inferred", conf="INFERRED", spec=None,
                   meaning=meaning, law=law, status="inferred",
                   reason=f"词典唯一命中（{match['family']}）：仅单位/物理含义/控制方程，"
                          "typical_ranges 只作参考区间展示",
                   in_ontology=True)
            continue
        record(col, watch_role="parameter", schema_role=None, unit=declared_unit,
               unit_status="declared" if declared_unit else "undeclared",
               ks=None, conf=None, spec=None,
               meaning=None, law=None, status="unmatched",
               reason=(("数据列未声明角色且物理词典未唯一命中——仅采用上下文声明的单位，"
                        "不赋予物理语义") if declared_unit else
                       ("数据列未声明角色/单位，且物理词典未唯一命中——"
                        "单位未声明（unit undeclared），按启发式参数列处理，不赋予语义")),
               in_ontology=False)

    matched = [r for r in rows if r["mapping_status"] == "matched"]
    inferred = [r for r in rows if r["mapping_status"] == "inferred"]
    unmatched = [r for r in rows if r["mapping_status"] == "unmatched"]
    universe = list(dict.fromkeys(table_cols + [c for c, *_ in declared]))

    limitations = [
        "声明先验本体：全部字段来自 report_context 声明、数据表头探测或物理词典唯一命中，"
        "不含任何实测行为（observed_data_behavior=NOT_APPLICABLE / behavior_match=UNVERIFIED）",
        "词典纪律：parameter_to_physics.json 的 typical_ranges 是参考区间（非规格），"
        "只展示在本体 watch.reference_bands 与简报中，永不写入 normal_range/spec/Cpk",
        "关系边留空：无方向声明不造因果边（relationships=[]），"
        "相关性发现的机理校验将按 unknown 处理并打 [MECHANISM_UNKNOWN]",
    ]
    undeclared_units = [r["col"] for r in rows if r["unit_status"] == "undeclared"]
    if undeclared_units:
        limitations.append(
            f"{len(undeclared_units)} 列单位未声明（unit undeclared）：{'、'.join(undeclared_units[:20])}"
            + ("…" if len(undeclared_units) > 20 else ""))
    if unmatched:
        limitations.append(
            f"{len(unmatched)} 列未获得语义映射（unmatched，原因见 column_mapping）——"
            "这些列仍按数值参数参与启发式评估，但报告必须如实标注其单位/语义缺失")
    if not table_cols:
        limitations.append("数据表头不可探测（缺失或非 CSV/TSV）：先验仅来自上下文声明")

    ontology = oc.empty_ontology_skeleton(
        scene_name=scene_key,
        process_type=str(ctx.get("scenario") or "production_line"))
    if ctx.get("objective"):
        ontology["scene"]["production_goal"] = str(ctx["objective"])
        ontology["scene"]["objectives"] = [str(ctx["objective"])]
    else:
        # schema: production_goal is type string (no null) — omit instead
        ontology["scene"].pop("production_goal", None)
        ontology["scene"]["objectives"] = []
    ontology["signals"] = signals
    # declared units are authoritative context truth — they land in
    # metadata.units even for columns whose role mapping stayed unmatched, so
    # the analyzer's condition understanding can surface them
    ontology["metadata"]["units"] = {**units_effective, **units_decl}
    ontology["watch"] = {
        "profile": PROFILE,
        "scene_key": scene_key,
        "roles": {r["col"]: r["watch_role"] for r in rows},
        "units": {r["col"]: r["unit"] for r in rows if r["unit"]},
        "reference_bands": reference_bands,
        "column_mapping": {
            "matched": [{"col": r["col"], "reason": r["mapping_reason"]} for r in matched],
            "inferred": [{"col": r["col"], "reason": r["mapping_reason"]} for r in inferred],
            "unmatched": [{"col": r["col"], "reason": r["mapping_reason"]} for r in unmatched],
        },
    }
    ontology["limitations"] = limitations
    ontology["provenance"] = oc.standard_provenance(
        profile=PROFILE, engine=ENGINE, build_mode=build_mode, data_stage=DATA_STAGE,
        source="report_context declarations + table header probe + shipped physics "
               "dictionary (unique hits only; typical_ranges = reference bands)")
    return ontology, rows


def extend_ontology(stored, prior, *, scene_key):
    """Merge the current declaration prior into a stored ontology (additive).

    Builder extend rule: new signals are appended; a declaration is
    authoritative for units / user spec ranges on columns it redeclares; an
    existing role is never re-pointed and stored relationships are kept as-is.
    """
    merged = copy.deepcopy(stored if isinstance(stored, dict) else copy.deepcopy(prior))
    merged.setdefault("scene", {})
    merged.setdefault("signals", {})
    for key in ("inspection_signals", "process_parameters", "control_variables",
                "events", "metadata_columns"):
        merged["signals"].setdefault(key, [])
    merged.setdefault("metadata", {})
    merged.setdefault("limitations", [])

    for field in ("production_goal", "objectives"):
        if not merged["scene"].get(field) and (prior.get("scene") or {}).get(field):
            merged["scene"][field] = prior["scene"][field]

    added = {}
    for key in ("inspection_signals", "process_parameters", "control_variables",
                "events", "metadata_columns"):
        existing = {s.get("column") or s.get("name"): s
                    for s in merged["signals"][key] if isinstance(s, dict)}
        count = 0
        for sig in prior["signals"].get(key) or []:
            col = sig.get("column") or sig.get("name")
            target = existing.get(col)
            if target is None:
                merged["signals"][key].append(copy.deepcopy(sig))
                existing[col] = sig
                count += 1
                continue
            if sig.get("unit") and not target.get("unit"):
                target["unit"] = sig["unit"]
            if sig.get("normal_range") is not None:
                target["normal_range"] = sig["normal_range"]
            for field in ("physical_meaning", "governing_law", "knowledge_source",
                          "physical_meaning_confidence", "inference_basis"):
                if not target.get(field) and sig.get(field):
                    target[field] = sig[field]
        if count:
            added[key] = count

    merged["watch"] = copy.deepcopy(prior.get("watch") or {})
    merged["watch"]["extended_from_scene"] = merged["scene"].get("name")
    for lim in prior.get("limitations") or []:
        if lim not in merged["limitations"]:
            merged["limitations"].append(lim)
    merged.setdefault("provenance", {})
    merged["provenance"].update(prior.get("provenance") or {})
    merged["provenance"]["build_mode"] = "extend"
    merged["_extend_note"] = added
    return merged


def _rows_from_ontology(ontology, table):
    """Per-column ledger for an ADOPTED ontology (its own signals are truth)."""
    table_cols = [str(c) for c in (table or {}).get("columns") or []]
    rows, covered = [], set()
    buckets = (("inspection_signals", "inspection", "target"),
               ("process_parameters", "parameter", "predictor"))
    signals = (ontology.get("signals") or {}) if isinstance(ontology, dict) else {}
    for bucket, watch_role, schema_role in buckets:
        for sig in signals.get(bucket) or []:
            if not isinstance(sig, dict):
                continue
            col = str(sig.get("column") or sig.get("name") or "")
            if not col or col in covered:
                continue
            covered.add(col)
            spec = None
            nr = sig.get("normal_range")
            if isinstance(nr, list) and len(nr) == 2:
                spec = {"lsl": nr[0], "usl": nr[1], "target": sig.get("target")}
            unit = sig.get("unit")
            ks = sig.get("knowledge_source")
            rows.append({
                "col": col, "watch_role": watch_role, "schema_role": schema_role,
                "in_ontology": True, "unit": unit,
                "unit_status": ("declared" if unit and ks == "user_provided"
                                else "dictionary_inferred" if unit
                                else "undeclared"),
                "knowledge_source": ks,
                "confidence": sig.get("physical_meaning_confidence"),
                "spec": spec, "reference_band": None,
                "physical_meaning": sig.get("physical_meaning"),
                "governing_law": sig.get("governing_law"),
                "mapping_status": "matched",
                "mapping_reason": "绑定显式采纳本体（--ontology）中的信号声明",
            })
    for sig in signals.get("metadata_columns") or []:
        if not isinstance(sig, dict):
            continue
        col = str(sig.get("column") or sig.get("name") or "")
        if not col or col in covered:
            continue
        covered.add(col)
        rows.append({
            "col": col,
            "watch_role": ("time" if sig.get("role") == "timestamp" else "group"),
            "schema_role": None, "in_ontology": True, "unit": None,
            "unit_status": "undeclared", "knowledge_source": None, "confidence": None,
            "spec": None, "reference_band": None,
            "physical_meaning": sig.get("description"), "governing_law": None,
            "mapping_status": "matched",
            "mapping_reason": "绑定显式采纳本体的元数据列声明",
        })
    for col in table_cols:
        if col in covered:
            continue
        covered.add(col)
        rows.append({
            "col": col, "watch_role": "parameter", "schema_role": None,
            "in_ontology": False, "unit": None, "unit_status": "undeclared",
            "knowledge_source": None, "confidence": None, "spec": None,
            "reference_band": None, "physical_meaning": None, "governing_law": None,
            "mapping_status": "unmatched",
            "mapping_reason": "数据列未被采纳本体覆盖——单位未声明（unit undeclared），按启发式参数列处理",
        })
    return rows


# ──────────────────────────────────────────────────────────────────── brief

def _coverage_of(rows):
    matched = [r for r in rows if r["mapping_status"] == "matched"]
    inferred = [r for r in rows if r["mapping_status"] == "inferred"]
    unmatched = [r for r in rows if r["mapping_status"] == "unmatched"]
    total = len(rows)
    return {
        "n_columns_total": total,
        "n_columns_mapped": total,
        "n_matched": len(matched),
        "n_inferred": len(inferred),
        "n_unmatched": len(unmatched),
        # ratio == 1.0 ⟺ 无静默列：每一列（表列 ∪ 声明列）都在 column_mapping
        # 里带状态与原因出现——unmatched 是"已披露的缺失"，不是静默。
        "ratio": round(total / total, 6) if total else 1.0,
        "matched_ratio": round((len(matched) + len(inferred)) / total, 6) if total else 1.0,
    }


def build_brief(ontology, rows, *, scene_key, context_fp, build_mode, source_note,
                lookup_status, version, elapsed_ms):
    """The stability understanding brief (01_ontology/ontology_brief.json)."""
    scene = (ontology.get("scene") or {}) if isinstance(ontology, dict) else {}
    prov = (ontology.get("provenance") or {}) if isinstance(ontology, dict) else {}
    specs_user = [{"col": r["col"], **r["spec"], "source": r["knowledge_source"]}
                  for r in rows if r["spec"]]
    bands = [{"col": col, **payload} for col, payload
             in sorted(((r["col"], r["reference_band"]) for r in rows if r["reference_band"]),
                       key=lambda item: item[0])]
    unmatched = [{"col": r["col"], "reason": r["mapping_reason"]}
                 for r in rows if r["mapping_status"] == "unmatched"]
    brief = {
        "contract_version": BRIEF_CONTRACT_VERSION,
        "artifact": "ontology_brief",
        "profile": PROFILE,
        "scene_key": scene_key,
        "data_stage": DATA_STAGE,
        "ontology_version": version,
        "ontology_sha256": oc.sha256_text(
            json.dumps(ontology, ensure_ascii=False, sort_keys=True)),
        "context_fp": context_fp,
        "scene": {
            "name": scene.get("name") or scene_key,
            "process_type": scene.get("process_type"),
            "production_goal": scene.get("production_goal"),
            "objectives": scene.get("objectives") or [],
            "line_id": scene.get("line_id"),
            "product": scene.get("product"),
            "scenario": scene.get("scenario"),
        },
        "columns": rows,
        "specs_user": specs_user,
        "reference_bands": bands,
        "units_declared": {r["col"]: r["unit"] for r in rows
                           if r["unit"] and r["unit_status"] == "declared"},
        "units_undeclared": [r["col"] for r in rows if r["unit_status"] == "undeclared"],
        "limitations": list((ontology.get("limitations") or []) if isinstance(ontology, dict) else []),
        "column_mapping": ((ontology.get("watch") or {}).get("column_mapping")
                           if isinstance(ontology, dict) else None) or {
            "matched": [{"col": r["col"], "reason": r["mapping_reason"]}
                        for r in rows if r["mapping_status"] == "matched"],
            "inferred": [{"col": r["col"], "reason": r["mapping_reason"]}
                         for r in rows if r["mapping_status"] == "inferred"],
            "unmatched": [{"col": r["col"], "reason": r["mapping_reason"]}
                          for r in rows if r["mapping_status"] == "unmatched"]},
        "unresolved": unmatched,
        "coverage": _coverage_of(rows),
        "provenance": {
            "build_mode": build_mode,
            "build_seconds": round(elapsed_ms / 1000.0, 3),
            "rag_used": False,
            "web_used": False,
            "physics_prior_used": True,
            "engine": ENGINE,
            "store_version": version,
            "store_profile": PROFILE,
            "source_note": source_note,
            "lookup_status": lookup_status,
        },
    }
    return brief


def _fmt(value):
    return "—" if value in (None, "", []) else str(value)


def render_markdown(brief):
    """Chinese brief for the agent: scene / roles+units / specs vs reference
    bands / limitations / column mapping / unresolved / provenance."""
    scene = brief.get("scene") or {}
    cov = brief.get("coverage") or {}
    prov = brief.get("provenance") or {}
    lines = []
    ap = lines.append
    ap(f"# 本体简报 · {_fmt(brief.get('scene_key'))}（stability）")
    ap("")
    ap(f"- 契约版本：{brief.get('contract_version')}（profile={brief.get('profile')}）"
       f"　数据阶段：`{_fmt(brief.get('data_stage'))}`")
    ap(f"- 上下文指纹 context_fp：`{_fmt(brief.get('context_fp'))}`")
    ap(f"- 本体版本：{_fmt(brief.get('ontology_version'))}　"
       f"本体哈希：`{_fmt(brief.get('ontology_sha256'))}`")
    ap("")
    ap("## 1. 场景理解")
    ap("")
    ap(f"- 场景：{_fmt(scene.get('name'))}（工艺类型：{_fmt(scene.get('process_type'))}）")
    ap(f"- 生产目标：{_fmt(scene.get('production_goal'))}　"
       f"分析目的：{_fmt(scene.get('objectives') or '—')}")
    ap("")
    ap("## 2. 列角色与单位")
    ap("")
    ap("| 列 | 角色语义 | 本体角色 | 单位 | 单位来源 | knowledge_source | 置信 |")
    ap("|---|---|---|---|---|---|---|")
    for r in brief.get("columns") or []:
        unit_cell = _fmt(r.get("unit")) if r.get("unit") else "单位未声明（unit undeclared）"
        ap(f"| `{_fmt(r.get('col'))}` | {_fmt(r.get('watch_role'))} | "
           f"{_fmt(r.get('schema_role')) or '—'} | {unit_cell} | "
           f"{_fmt(r.get('unit_status'))} | {_fmt(r.get('knowledge_source')) or '—'} | "
           f"{_fmt(r.get('confidence')) or '—'} |")
    ap("")
    ap("## 3. 规格与参考区间")
    ap("")
    ap("### 3.1 用户/上下文声明规格（可作判定边界）")
    ap("")
    if brief.get("specs_user"):
        ap("| 列 | LSL | USL | Target | 来源 |")
        ap("|---|---|---|---|---|")
        for s in brief["specs_user"]:
            ap(f"| `{_fmt(s.get('col'))}` | {_fmt(s.get('lsl'))} | {_fmt(s.get('usl'))} | "
               f"{_fmt(s.get('target'))} | {_fmt(s.get('source'))} |")
    else:
        ap("- （无用户声明规格——Cpk 将不计算，不做规格罚分）")
    ap("")
    ap("### 3.2 词典参考区间（非规格）")
    ap("")
    if brief.get("reference_bands"):
        ap("以下区间来自 `parameter_to_physics.json` 的 typical_ranges，**仅作阅读参考，"
           "永不进入 normal_range / spec / Cpk**：")
        ap("")
        ap("| 列 | 词典族 | 参考带 |")
        ap("|---|---|---|")
        for b in brief["reference_bands"]:
            ap(f"| `{_fmt(b.get('col'))}` | {_fmt(b.get('family'))} | "
               f"`{json.dumps(b.get('bands'), ensure_ascii=False)}` |")
    else:
        ap("- （无词典参考带）")
    ap("")
    ap("## 4. 混杂与局限")
    ap("")
    for lim in brief.get("limitations") or ["（无）"]:
        ap(f"- {lim}")
    ap("")
    ap("## 5. 列映射覆盖（0 静默）")
    ap("")
    cm = brief.get("column_mapping") or {}
    ap(f"- matched: {len(cm.get('matched') or [])}　inferred: {len(cm.get('inferred') or [])}　"
       f"unmatched: {len(cm.get('unmatched') or [])}")
    ap(f"- coverage.ratio = {cov.get('ratio')}"
       f"（1.0 ⟺ 无静默列：每列都带状态与原因出现；unmatched 是已披露的缺失，不是静默）")
    ap(f"- matched_ratio = {cov.get('matched_ratio')}"
       f"（matched+inferred 占比；unmatched 越多，语义覆盖越弱）")
    ap("")
    ap("## 6. 未解决项")
    ap("")
    if brief.get("unresolved"):
        for row in brief["unresolved"]:
            ap(f"- `{_fmt(row.get('col'))}`：{_fmt(row.get('reason'))}")
    else:
        ap("- （无）")
    ap("")
    ap("## 7. 来源（provenance）")
    ap("")
    ap(f"- build_mode={_fmt(prov.get('build_mode'))}　engine={_fmt(prov.get('engine'))}　"
       f"store=v{_fmt(prov.get('store_version'))}（profile={_fmt(prov.get('store_profile'))}）")
    ap(f"- rag_used={prov.get('rag_used')}　web_used={prov.get('web_used')}　"
       f"physics_prior_used={prov.get('physics_prior_used')}（确定性路径，未调用 RAG/网络）")
    ap(f"- source_note：{_fmt(prov.get('source_note'))}　lookup={_fmt(prov.get('lookup_status'))}　"
       f"build_seconds={prov.get('build_seconds')}")
    ap("")
    ap("> 本简报由确定性脚本生成（零 RAG、零网络）。分析器在 mode≠off 时要求本文件存在"
       "（门禁 `ONTOLOGY_BRIEF_REQUIRED`）；agent 阅读本文件后再进入统计解读。")
    ap("")
    return "\n".join(lines)


def _write_brief(run_dir, brief):
    run_dir_v = oc.contained(run_dir)
    out_dir = run_dir_v / "01_ontology"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = oc.write_json_strict(out_dir / "ontology_brief.json", brief)
    md_path = out_dir / "ontology_brief.md"
    md_path.write_text(render_markdown(brief), encoding="utf-8")
    return str(json_path), str(md_path)


# ──────────────────────────────────────────────────────────── CP-2（硬闸） ────

def _cp2_check(ontology_file):
    """CP-2 floor: schema-valid (shared validate.mjs) AND ≥ ONTOLOGY_MIN_BYTES."""
    try:
        size = Path(ontology_file).stat().st_size
    except OSError as exc:
        return False, f"ontology.json unreadable: {exc}"
    size_ok = size >= oc.ONTOLOGY_MIN_BYTES
    proc = subprocess.run(
        ["node", str(VALIDATOR), str(oc.ONTOLOGY_SCHEMA), str(ontology_file)],
        capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT))
    schema_ok = proc.returncode == 0
    if size_ok and schema_ok:
        return True, None
    detail = [] if size_ok else [f"ontology.json {size}B < {oc.ONTOLOGY_MIN_BYTES}B floor"]
    if not schema_ok:
        detail.append((proc.stdout or proc.stderr or "schema validation failed").strip()[-600:])
    return False, "; ".join(detail)


# ─────────────────────────────────────────────────────────────────── prepare

def _skipped_result(elapsed_ms, mode):
    return {
        "action": oc.ACTION_SKIPPED,
        "reason": f"ontology mode {mode} — the ontology stage is disabled for this run",
        "ontology_path": None, "brief_json": None, "brief_md": None, "coverage_path": None,
        "version": None, "context_fp": None, "scene_key": None, "data_stage": None,
        "elapsed_ms": elapsed_ms, "rag_used": False, "web_used": False,
        "build_mode": None, "source_note": None, "ontology_bytes": None,
        "cp2_floor_ok": None,
        "store": {"lookup": "not_attempted", "published": False},
        "coverage": None, "lookup": "not_attempted", "mode": mode, "wrote": [],
        "rag_used_by_prepare": False, "web_used_by_prepare": False,
        "store_dir": str(oc.resolve_store_dir()),
    }


def _declaration_fingerprint(rows):
    """watch-context fingerprint over the mapped declaration contract."""
    columns = [{
        "col": r["col"],
        "role": r["watch_role"] if r["in_ontology"] else "undeclared",
        "unit": r["unit"] or "",
        "lsl": (r["spec"] or {}).get("lsl"),
        "usl": (r["spec"] or {}).get("usl"),
    } for r in rows]
    return oc.compute_watch_context_fp({"columns": columns, "windows": []})


def prepare(run_dir, *, data=None, context=None, mode="auto", scene_key=None,
            store_dir=None, ontology=None):
    """Stability ontology stage entry point. See the module docstring."""
    started = time.perf_counter()
    run_dir_v = oc.contained(run_dir)
    ontology_dir = run_dir_v / "01_ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    store = oc.resolve_store_dir(store_dir)

    ctx_path = Path(context) if context else run_dir_v / "00_input" / "report_context.json"
    ctx = oc.read_json(ctx_path) if Path(ctx_path).is_file() else {}
    ctx = copy.deepcopy(ctx) if isinstance(ctx, dict) else {}

    ont_ctx = ctx.get("ontology") if isinstance(ctx.get("ontology"), dict) else {}
    resolved_mode = mode if mode in oc.VALID_MODES else "auto"
    if resolved_mode == "auto" and ont_ctx.get("mode") in oc.VALID_MODES:
        resolved_mode = ont_ctx["mode"]
    if resolved_mode == "off":
        return _skipped_result(oc.timed_result(started), "off")

    scene = (_sanitize_scene_key(scene_key)
             or _sanitize_scene_key(ont_ctx.get("scene_key"))
             or _sanitize_scene_key(ctx.get("scenario"))
             or _sanitize_scene_key(run_dir_v.name)
             or "stability_scene")

    data_path = oc.resolve_data_path(run_dir_v, data, ctx, candidate_names=DATA_CANDIDATES)
    table = _strip_bom(oc.load_table_columns(data_path)) if data_path is not None else None

    prior, rows = build_prior_ontology(ctx, table, scene_key=scene, build_mode="prior_knowledge")
    context_fp = _declaration_fingerprint(rows)

    # explicit adoption (--ontology): a real, shape-valid ontology asset wins
    adopted = None
    if ontology:
        opath = Path(ontology)
        if not opath.is_file():
            raise SystemExit(f"ONTOLOGY_NOT_FOUND: explicit --ontology file not found: {ontology}")
        try:
            candidate = oc.read_json(opath)
        except (json.JSONDecodeError, OSError) as exc:
            raise SystemExit(f"ONTOLOGY_INVALID: explicit --ontology is not readable JSON "
                             f"({exc}): {ontology}")
        if not (isinstance(candidate, dict) and candidate.get("scene") and candidate.get("signals")):
            raise SystemExit(f"ONTOLOGY_INVALID: explicit --ontology must be a JSON object with "
                             f"'scene' and 'signals': {ontology}")
        adopted = candidate

    lookup = oc.lookup(store, profile=PROFILE, scene_key=scene, context_fp=context_fp)
    action, source_note = oc.resolve_action(resolved_mode, lookup["status"])
    if adopted is not None:
        action, source_note = oc.ACTION_BUILT, (
            source_note or f"adopted explicit --ontology ({ontology})")

    run_ontology_path = ontology_dir / "ontology.json"
    store_result = {"lookup": lookup["status"], "published": False,
                    "entry_version": lookup["entry"].get("version") if lookup["entry"] else None}

    if action == oc.ACTION_REUSED:
        # action-driven store commit: ONLY a genuine reuse copies from the store
        store_result, version = oc.commit_to_store(
            run_dir_v, store=store, store_dir=store, profile=PROFILE, scene=scene,
            context_fp=context_fp, build_mode="reuse", data_stage=DATA_STAGE,
            data_path=data_path, lookup_status=lookup["status"], lookup_entry=lookup["entry"])
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        ontology_for_run = oc.read_json(stored_path) if stored_path.is_file() else prior
        build_mode = lookup["entry"].get("build_mode") or "reuse"
        source_note = f"reused store asset {lookup['entry'].get('path')}"
    elif action == oc.ACTION_EXTENDED:
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        stored = oc.read_json(stored_path) if stored_path.is_file() else {}
        ontology_for_run = extend_ontology(stored, prior, scene_key=scene)
        build_mode = "extend"
        source_note = source_note or f"extended store asset {lookup['entry'].get('path')}"
    elif adopted is not None:
        ontology_for_run = adopted
        build_mode = "full"
    else:
        ontology_for_run = prior
        build_mode = "prior_knowledge"
        source_note = source_note or (
            "declared-prior build (report_context declarations + table probe + "
            "physics dictionary unique hits; no RAG/web)")

    if action != oc.ACTION_REUSED:
        oc.write_json_strict(run_ontology_path, ontology_for_run)

    ontology_text = json.dumps(ontology_for_run, ensure_ascii=False, indent=2)
    ontology_bytes = len(ontology_text.encode("utf-8"))

    # CP-2 gate BEFORE the store sees the asset (reuse re-checks the copied file)
    cp2_ok, cp2_detail = _cp2_check(run_ontology_path)
    if not cp2_ok:
        raise SystemExit(f"ONTOLOGY_CP2_FAILED: {run_ontology_path} — {cp2_detail}")

    if action == oc.ACTION_REUSED:
        version = store_result.get("entry_version") or version
    else:
        publish_args = ["publish", "--run-dir", str(run_dir_v), "--scene", scene,
                        "--profile", PROFILE, "--context-fp", context_fp,
                        "--build-mode", str(build_mode), "--data-stage", DATA_STAGE]
        if data_path is not None and Path(data_path).suffix.lower() in (".csv", ".tsv"):
            publish_args += ["--data-file", str(data_path)]
        try:
            published = oc.store_call(*publish_args, store_dir=store)
            store_result.update({"published": True, "entry_version": published.get("version"),
                                 "deduped": bool(published.get("deduped"))})
            version = published.get("version")
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            # the ontology is already in the run dir — the store is an
            # optimisation, not a gate
            store_result.update({"published": False, "error": str(exc)})
            version = None

    elapsed_ms = oc.timed_result(started)
    brief = build_brief(ontology_for_run, rows, scene_key=scene, context_fp=context_fp,
                        build_mode=build_mode, source_note=source_note,
                        lookup_status=lookup["status"], version=version,
                        elapsed_ms=elapsed_ms)
    brief_json, brief_md = _write_brief(run_dir_v, brief)

    coverage = {
        "contract_version": BRIEF_CONTRACT_VERSION,
        "artifact": "ontology_coverage",
        "scene_key": scene,
        "profile": PROFILE,
        "data_stage": DATA_STAGE,
        "context_fp": context_fp,
        "ontology_version": version,
        "ontology_sha256": brief.get("ontology_sha256"),
        "generated_by": "ontology_prepare.py",
        "columns": [{"col": r["col"], "watch_role": r["watch_role"],
                     "status": r["mapping_status"], "reason": r["mapping_reason"],
                     "unit": r["unit"], "unit_status": r["unit_status"],
                     "knowledge_source": r["knowledge_source"]}
                    for r in rows],
        "column_mapping": brief.get("column_mapping"),
        "coverage": brief.get("coverage"),
        "elapsed_ms": elapsed_ms,
        "generated_at": oc.now_iso(),
    }
    coverage_path = oc.write_json_strict(ontology_dir / "ontology_coverage.json", coverage)

    prov = ontology_for_run.get("provenance") if isinstance(ontology_for_run.get("provenance"), dict) else {}
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
        "rag_used": bool(prov.get("rag_used", False)),
        "web_used": bool(prov.get("web_used", False)),
        "build_mode": build_mode,
        "source_note": source_note,
        "ontology_bytes": ontology_bytes,
        "cp2_floor_ok": bool(cp2_ok),
        "store": store_result,
        "coverage": brief.get("coverage"),
        "lookup": lookup["status"],
        "mode": resolved_mode,
        "wrote": [str(run_ontology_path), brief_json, brief_md, str(coverage_path)],
        "rag_used_by_prepare": False,   # the deterministic stage never calls RAG/web
        "web_used_by_prepare": False,
        "store_dir": str(store),
    }


# ------------------------------------------------------------------------ CLI

def _cli():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    return oc.cli_main(
        lambda args: prepare(args.run_dir, data=args.data, context=args.context,
                             mode=args.mode, scene_key=args.scene,
                             store_dir=args.store_dir, ontology=args.ontology),
        prog_desc="stability-report ontology stage: lookup → reuse/extend/build",
        extra_args=((("--ontology",),
                     {"default": None,
                      "help": "adopt this ontology.json verbatim (must exist, be valid "
                              "JSON and carry scene+signals; otherwise SystemExit)"}),),
    )


if __name__ == "__main__":
    raise SystemExit(_cli())
