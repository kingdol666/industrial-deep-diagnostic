#!/usr/bin/env python
"""doe_ontology_prepare.py — DOE ontology stage: lookup → reuse/extend/build (P1-3).

Implements the frozen interface of `docs/plans/contracts/README.md` §9:

    prepare(run_dir, *, data=None, context=None, mode="auto", scene_key=None,
            store_dir=None, seed=None) -> dict
        -> {action: "reused"|"extended"|"built"|"skipped", ontology_path,
            brief_json, brief_md, coverage_path, version, context_fp, scene_key,
            data_stage, elapsed_ms, rag_used, web_used}

    enforce_gate(run_dir, ctx, *, subcommand=None) -> None
        # key missing, or ctx["ontology"]["mode"] in (None, "off")  → no-op (gate off)
        # mode != off and no brief                → SystemExit("ONTOLOGY_BRIEF_REQUIRED: …")
        # mode != off and no analysis_plan.md     → SystemExit("ANALYSIS_PLAN_REQUIRED: …")
        # design_only + all responses empty + statistics subcommand
        #                                         → SystemExit("DESIGN_ONLY_NO_RESPONSE: …")

Flow (contracts §3 Phase A):

  1. context_fp = fingerprint(declared columns / ranges / units / specs / design type)
     (mirrored 1:1 by computeContextFingerprint() in ontology_store.mjs);
  2. store lookup (profile=doe, scene_key, context_fp):
       exact      → reuse the stored ontology verbatim (fast path, zero RAG/web)
       scene_only → extend the stored ontology (context changed: columns/ranges/specs)
       miss       → build — from an ontology an agent already wrote into the run dir,
                    or (design_only / no prior) deterministically from prior knowledge;
  3. write 01_ontology/ontology.json + ontology_brief.json/.md + ontology_coverage.json;
     publish/extend the store entry (single write path: ontology_store.mjs).

Honesty rules:
  * a prior-knowledge build never claims measured behaviour — design_only responses
    carry observed_data_behavior = "NOT_APPLICABLE" and behavior_match = "UNVERIFIED";
  * `rag_used` / `web_used` are reported from the ontology provenance, never invented —
    the deterministic paths always report False;
  * the ontology content contains no wall clock (stable content → stable store dedupe);
    timestamps live in the brief/coverage artifacts only.

CLI:
  python doe_ontology_prepare.py --run-dir DIR [--data PATH] [--context PATH]
      [--mode auto|full|reuse|extend|off] [--scene KEY] [--store-dir DIR] [--seed N] [--json]
"""

import argparse
import copy
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]          # …/industrial-doe-analyzer/scripts → repo root
STORE_JS = REPO_ROOT / ".claude" / "shared" / "scripts" / "ontology_store.mjs"
ONTOLOGY_SCHEMA = (REPO_ROOT / ".claude" / "skills" / "industrial-ontology-builder"
                   / "schemas" / "ontology_schema.json")
DEFAULT_STORE_DIR = REPO_ROOT / "data" / "ontology_store"
ONTOLOGY_MIN_BYTES = 1024                  # CP-2 floor (same constant as the store)

sys.path.insert(0, str(SCRIPT_DIR))
from ontology_brief import build_brief, write_brief, _sanitize_scene_key  # noqa: E402

CONTEXT_FP_VERSION = "doe-context-v1"
CONTEXT_FP_ABS_CUTOFF = 1e15
PROFILE = "doe"
ENGINE = "industrial-ontology-builder"
ACTION_REUSED, ACTION_EXTENDED, ACTION_BUILT, ACTION_SKIPPED = "reused", "extended", "built", "skipped"

GATE_BRIEF_REQUIRED = "ONTOLOGY_BRIEF_REQUIRED"
GATE_PLAN_REQUIRED = "ANALYSIS_PLAN_REQUIRED"
GATE_DESIGN_ONLY_NO_RESPONSE = "DESIGN_ONLY_NO_RESPONSE"

# Subcommands that consume measured responses. Pass one of these to enforce_gate()
# to enable the design-only block; the frozen 2-arg call never guesses.
STATS_SUBCOMMANDS = {"all", "run", "analyze", "stats", "report"}


# ---------------------------------------------------------------- path utils

def _contained(candidate, extra_root=None):
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    if extra_root is not None:
        root = os.path.normpath(os.path.abspath(str(extra_root)))
        if not (cand == root or cand.startswith(root + os.sep)):
            raise ValueError(f"path outside allowed root: {candidate}")
    return Path(cand)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, payload):
    out = _contained(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
                   encoding="utf-8")
    return out


def _sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ───────────────────────── context 指纹（与 ontology_store.mjs 同源） ─────────

def canonical_number_token(value):
    """Canonical decimal token — must stay identical to canonicalNumberToken()
    in ontology_store.mjs ('' for absent, never 'null')."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return str(value)
    if abs(number) >= CONTEXT_FP_ABS_CUTOFF:
        return repr(number)
    text = f"{number:.9f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-0"):
        text = "0"
    return text


def _levels_token(levels):
    if levels is None or levels == "":
        return ""
    if isinstance(levels, (list, tuple)):
        return ",".join(str(v) for v in levels)
    return str(levels)


def _context_fp(ctx):
    """The frozen context fingerprint (contracts §9). Sorted keys, no clock."""
    ctx = ctx if isinstance(ctx, dict) else {}
    factors = [f for f in (ctx.get("factors") or []) if isinstance(f, dict)]
    responses = [r for r in (ctx.get("responses") or []) if isinstance(r, dict)]
    factor_lines = sorted("|".join([
        "F",
        str(f.get("col") if f.get("col") is not None else (f.get("name") or "")),
        str(f.get("type") or ""),
        str(f.get("unit") or ""),
        canonical_number_token(f.get("min")),
        canonical_number_token(f.get("max")),
        _levels_token(f.get("levels")),
    ]) for f in factors)
    response_lines = sorted("|".join([
        "R",
        str(r.get("col") if r.get("col") is not None else (r.get("name") or "")),
        str(r.get("unit") or ""),
        str(r.get("goal") or ""),
        canonical_number_token(r.get("lsl")),
        canonical_number_token(r.get("usl")),
        canonical_number_token(r.get("target")),
    ]) for r in responses)
    design_region = ctx.get("design_region") if isinstance(ctx.get("design_region"), dict) else {}
    design_type = ctx.get("design_type_declared") or ctx.get("design_type") \
        or design_region.get("design_hull") or ""
    payload = "\n".join([
        f"v={CONTEXT_FP_VERSION}",
        f"D|{design_type}",
        *factor_lines,
        *response_lines,
    ])
    return _sha256_text(payload)


# ───────────────────────────────── store（读 index 就地；写走唯一写入口） ─────

def resolve_store_dir(store_dir=None):
    if store_dir:
        return _contained(store_dir)
    env = os.environ.get("ONTOLOGY_STORE_DIR")
    if env:
        return _contained(env)
    return DEFAULT_STORE_DIR


def _read_store_index(store_dir):
    path = Path(store_dir) / "index.json"
    if not path.is_file():
        return {"version": 1, "entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "entries": []}
    entries = data.get("entries") if isinstance(data, dict) else None
    return {"version": data.get("version", 1) if isinstance(data, dict) else 1,
            "entries": entries if isinstance(entries, list) else []}


def _entry_profile(entry):
    value = entry.get("profile") if isinstance(entry, dict) else None
    return (value or "diagnosis").strip() if isinstance(value, str) and value.strip() else "diagnosis"


def _lookup(store_dir, *, profile, scene_key, context_fp):
    """profile+scene+context_fp lookup. exact | scene_only | miss (frozen enum).

    exact is matched across ALL scenes first: the same data context can be
    published under different scene keys (run name vs derived key), and a
    scene-first filter turns that into an avoidable miss + duplicate build.
    """
    entries = [e for e in _read_store_index(store_dir)["entries"]
               if isinstance(e, dict)
               and _entry_profile(e) == profile
               and e.get("quality") != "deprecated"]
    if context_fp:
        exact = [e for e in entries if (e.get("context_fp") or None) == context_fp]
        if exact:
            best = sorted(exact, key=lambda e: (-int(e.get("version") or 0), str(e.get("path") or "")))[0]
            return {"status": "exact", "entry": best,
                    "cross_scene": bool(scene_key) and best.get("scene_key") != scene_key}
    scoped = [e for e in entries if not scene_key or e.get("scene_key") == scene_key]
    if scene_key and scoped:
        best = sorted(scoped, key=lambda e: (-int(e.get("version") or 0), str(e.get("path") or "")))[0]
        return {"status": "scene_only", "entry": best}
    return {"status": "miss", "entry": None}


def _store_call(*argv, store_dir, timeout=180):
    """Run ontology_store.mjs with an argument LIST (never a shell string).

    The store is the single write path for ontology assets — prepare never
    writes index.json itself.
    """
    env = dict(os.environ)
    env["ONTOLOGY_STORE_DIR"] = str(store_dir)
    argv = ["node", str(STORE_JS), *argv]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          shell=False, cwd=str(REPO_ROOT), env=env)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()[-800:])
    return json.loads(proc.stdout)


# ───────────────────────────────────────────── 数据表探测（design_only / 缺列） ─

def _load_table_columns(path):
    """Minimal CSV header + response-emptiness probe (no pandas dependency)."""
    p = Path(path)
    if not p.is_file():
        return None
    header_text = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if not header_text:
        return None
    header = [h.strip() for h in header_text[0].split(",")]
    empty_counts = {h: 0 for h in header}
    total = {h: 0 for h in header}
    for line in header_text[1:]:
        if not line.strip():
            continue
        cells = line.split(",")
        for idx, name in enumerate(header):
            total[name] += 1
            if idx >= len(cells) or not cells[idx].strip():
                empty_counts[name] += 1
    return {"columns": header, "total": total, "empty": empty_counts}


def _resolve_data_path(run_dir, data, ctx):
    if data:
        return _contained(data, run_dir)
    declared = ctx.get("data_path") if isinstance(ctx, dict) else None
    if declared:
        candidate = Path(declared)
        if not candidate.is_absolute():
            candidate = run_dir / declared
        if candidate.is_file():
            return _contained(candidate, run_dir)
    for name in ("run_table.csv", "data.csv"):
        candidate = run_dir / "00_input" / name
        if candidate.is_file():
            return candidate
    return None


def _resolve_data_stage(ctx, table):
    ont = ctx.get("ontology") if isinstance(ctx, dict) and isinstance(ctx.get("ontology"), dict) else {}
    for declared in (ont.get("data_stage"), ctx.get("data_stage")):
        if declared in ("design_only", "collected"):
            return declared
    if table is not None:
        response_cols = [r.get("col") or r.get("name") for r in (ctx.get("responses") or [])
                         if isinstance(r, dict)]
        present = [c for c in response_cols if c in table["columns"]]
        if present:
            all_empty = all(table["empty"].get(c, 0) >= table["total"].get(c, 0)
                            for c in present)
            if all_empty:
                return "design_only"
            return "collected"
        return "design_only"          # no response column at all → nothing measured
    return "collected"


def _missing_columns(ctx, table):
    if table is None:
        return []
    declared = [(f.get("col") or f.get("name")) for f in (ctx.get("factors") or [])
                if isinstance(f, dict)]
    declared += [(r.get("col") or r.get("name")) for r in (ctx.get("responses") or [])
                 if isinstance(r, dict)]
    return sorted({c for c in declared if c and c not in table["columns"]})


# ──────────────────────────────────────────────── 先验本体（design_only 可建） ─

def _signal_confidence(item):
    if item.get("physical_meaning") and item.get("ontology_signal"):
        return "KNOWN"
    if item.get("physical_meaning") or item.get("ontology_signal"):
        return "INFERRED"
    return "INFERRED" if item.get("unit") or item.get("min") is not None else "UNKNOWN"


def _knowledge_source(item):
    return "user_provided" if (item.get("physical_meaning") or item.get("ontology_signal")) \
        else "auto_inferred"


def build_prior_ontology(ctx, *, scene_key, data_stage, design_type=None):
    """Deterministic prior-knowledge ontology (design_only able, zero fabrication).

    Everything written here is traceable to a declaration in `doe_context` /
    `analysis_context` or to a named physical prior — no measured behaviour is
    ever claimed (observed_data_behavior = NOT_APPLICABLE / UNVERIFIED).
    """
    ctx = ctx if isinstance(ctx, dict) else {}
    kn = CONTEXT_FP_VERSION
    factors = [f for f in (ctx.get("factors") or []) if isinstance(f, dict)]
    responses = [r for r in (ctx.get("responses") or []) if isinstance(r, dict)]
    covariates = [str(c) for c in (ctx.get("covariates") or [])]
    blocks = [str(b) for b in (ctx.get("blocks") or [])]
    objective = ctx.get("objective")
    design_type = design_type or ctx.get("design_type_declared") \
        or (ctx.get("design_region") or {}).get("design_hull")

    def base_signal(item, role):
        col = item.get("col") or item.get("name")
        return {
            "name": item.get("name") or col,
            "column": col,
            "unit": item.get("unit"),
            "role": role,
            "physical_meaning": item.get("physical_meaning") or (
                f"{col}（由分析上下文声明；未提供独立物理机理描述）"),
            "physical_meaning_confidence": _signal_confidence(item),
            "auto_inferred": not bool(item.get("physical_meaning")),
            "inference_basis": (f"declared in analysis_context/doe_context as {role}"
                                + (f"; ontology_signal={item.get('ontology_signal')}"
                                   if item.get("ontology_signal") else "")),
            "expected_sign": item.get("expected_sign"),
            "knowledge_source": _knowledge_source(item),
        }

    control_variables = []
    for f in factors:
        sig = base_signal(f, "control")
        sig.update({
            "control_type": "setpoint",
            "normal_range": [f.get("min"), f.get("max")],
            "setpoint": f.get("setpoint"),
            "expected_data_behavior": (
                f"先验声明：{f.get('min')}~{f.get('max')} {f.get('unit') or ''} 区间内可设定；"
                f"方向预期 {f.get('expected_sign') or '未声明'}"),
            "observed_data_behavior": "NOT_APPLICABLE" if data_stage == "design_only" else None,
            "behavior_match": "UNVERIFIED",
            "governing_law": f.get("governing_law"),
        })
        control_variables.append(sig)

    inspection_signals = []
    for r in responses:
        sig = base_signal(r, "target")
        sig.update({
            "target": r.get("target"),
            "tolerance": (abs(float(r["usl"]) - float(r["lsl"])) / 2.0
                          if r.get("usl") is not None and r.get("lsl") is not None else None),
            "expected_data_behavior": None,
            "observed_data_behavior": "NOT_APPLICABLE" if data_stage == "design_only" else None,
            "behavior_match": "UNVERIFIED",
        })
        inspection_signals.append(sig)

    process_parameters = []
    for name in covariates:
        process_parameters.append({
            "name": name, "column": name, "role": "confounder",
            "physical_meaning": f"{name}（分析上下文声明的协变量；可能同时影响因子与响应）",
            "physical_meaning_confidence": "INFERRED",
            "inference_basis": "declared in analysis_context.covariates",
            "knowledge_source": "user_provided",
        })

    metadata_columns = []
    for name in blocks:
        metadata_columns.append({
            "name": name, "column": name, "role": "batch_id",
            "description": f"{name}（分析上下文声明的区组列）",
        })

    relationships = []
    for f in factors:
        if not f.get("expected_sign"):
            continue                      # 无方向声明 → 不编造因果边
        for r in responses:
            relationships.append({
                "from": f.get("col") or f.get("name"),
                "to": r.get("col") or r.get("name"),
                "type": "causal",
                "strength": "moderate",
                "mechanism": (f"{f.get('physical_meaning') or f.get('col') or f.get('name')} 对 "
                              f"{r.get('physical_meaning') or r.get('col') or r.get('name')} 的先验影响"
                              f"（方向声明 {f.get('expected_sign')}；机理来自用户/上下文声明，尚未实测）"),
                "inferred": True,
                "expected_sign": f.get("expected_sign"),
                "predicted_functional_form": "unknown",
                "rag_validated": False,
                "data_direction_validated": "untested",
                "lag_detection_method": "not_applicable",
            })

    limitations = []
    if data_stage == "design_only":
        limitations.append(
            "design_only：响应尚未测量；所有 observed_data_behavior 均为 NOT_APPLICABLE，"
            "依赖实测行为的统计结论不得由本本体直接推导")
    limitations.append("先验本体：关系方向来自上下文声明与物理先验，未经实测数据验证")
    if not relationships:
        limitations.append("未声明任何 expected_sign —— 未生成因子→响应关系，一致性检查将如实记为 not_estimable")

    units = {}
    for item in factors + responses:
        col = item.get("col") or item.get("name")
        if col and item.get("unit"):
            units[col] = item["unit"]

    ontology = {
        "ontology_version": None,          # store version is assigned by publish
        "scene": {
            "name": scene_key,
            "process_type": ctx.get("line_id") or ctx.get("product_id") or "designed_experiment",
            "production_goal": ctx.get("objective"),
            "equipment": [],
            "stages": [],
            "objectives": [o for o in [objective] if o],
        },
        "signals": {
            "inspection_signals": inspection_signals,
            "process_parameters": process_parameters,
            "control_variables": control_variables,
            "events": [],
            "metadata_columns": metadata_columns,
        },
        "parameter_groups": ({"factors": [f.get("col") or f.get("name") for f in factors]}
                             if factors else {}),
        "relationships": relationships,
        "confounders": [
            {"variable": name,
             "why": "declared as covariate in analysis_context (may co-move with factors and responses)",
             "controlled": False}
            for name in covariates
        ],
        "metadata": {
            "units": units,
            "sampling_rate": None,
            "batch_id": blocks[0] if blocks else None,
            "timezone": None,
        },
        "doe": {
            "profile": PROFILE,
            "scene_key": scene_key,
            "data_stage": data_stage,
            "design_type": design_type,
            "design_region": ctx.get("design_region"),
            "constraints": ctx.get("constraints") or [],
            "objectives": [o for o in [objective] if o],
            "factors": [{
                "col": f.get("col") or f.get("name"),
                "name": f.get("name") or f.get("col"),
                "expected_sign": f.get("expected_sign"),
                "physical_meaning": f.get("physical_meaning"),
                "ontology_signal": f.get("ontology_signal"),
                "unit": f.get("unit"),
                "min": f.get("min"),
                "max": f.get("max"),
                "levels": f.get("levels"),
                "confidence": _signal_confidence(f),
            } for f in factors],
            "responses": [{
                "col": r.get("col") or r.get("name"),
                "name": r.get("name") or r.get("col"),
                "unit": r.get("unit"),
                "goal": r.get("goal"),
                "lsl": r.get("lsl"),
                "usl": r.get("usl"),
                "target": r.get("target"),
                "ontology_signal": r.get("ontology_signal"),
                "confidence": _signal_confidence(r),
            } for r in responses],
            "limitations": limitations,
        },
        "limitations": limitations,
        "provenance": {
            "engine": ENGINE,
            "profile": PROFILE,
            "build_mode": "prior_knowledge",
            "data_stage": data_stage,
            "rag_used": False,
            "web_used": False,
            "physics_prior_used": True,
            "source": "doe_context / analysis_context declarations + physics priors",
            "context_fp_version": kn,
        },
    }
    return ontology


def extend_ontology(stored, ctx, *, scene_key, data_stage, design_type=None):
    """Merge a stored ontology with the current context declarations.

    Additive by construction: new signals/relationships are appended, declared
    ranges/units update the signal, and an existing role is never re-pointed
    (builder extend rule). `observed_data_behavior` is only refreshed when the
    run actually has measurements.
    """
    merged = copy.deepcopy(stored if isinstance(stored, dict) else {})
    merged.setdefault("scene", {})
    merged.setdefault("signals", {})
    for key in ("inspection_signals", "process_parameters", "control_variables", "events",
                "metadata_columns"):
        merged["signals"].setdefault(key, [])
    merged.setdefault("relationships", [])
    merged.setdefault("confounders", [])
    merged.setdefault("metadata", {})

    ctx = ctx if isinstance(ctx, dict) else {}
    prior = build_prior_ontology(ctx, scene_key=scene_key, data_stage=data_stage,
                                design_type=design_type)
    merged["doe"] = dict(merged.get("doe") or {})

    def merge_signals(kind_key, incoming, role_default):
        existing = {s.get("column") or s.get("name"): s for s in merged["signals"].get(kind_key, [])
                    if isinstance(s, dict)}
        added = []
        for sig in incoming:
            col = sig.get("column") or sig.get("name")
            if col in existing:
                target = existing[col]
                # context declaration is authoritative for unit / declared range
                if sig.get("unit"):
                    target["unit"] = sig["unit"]
                if sig.get("role") and not target.get("role"):
                    target["role"] = sig["role"]
                if sig.get("normal_range") is not None and kind_key == "control_variables":
                    target["normal_range"] = sig["normal_range"]
                if data_stage != "design_only":
                    target["observed_data_behavior"] = target.get("observed_data_behavior")
                else:
                    target["observed_data_behavior"] = "NOT_APPLICABLE"
                if not target.get("expected_sign") and sig.get("expected_sign"):
                    target["expected_sign"] = sig["expected_sign"]
                if not target.get("physical_meaning") and sig.get("physical_meaning"):
                    target["physical_meaning"] = sig["physical_meaning"]
            else:
                sig = dict(sig)
                if not sig.get("role"):
                    sig["role"] = role_default
                added.append(sig)
        if added:
            merged["signals"][kind_key] = list(merged["signals"].get(kind_key, [])) + added
        return added

    added_controls = merge_signals("control_variables", prior["signals"]["control_variables"], "control")
    added_targets = merge_signals("inspection_signals", prior["signals"]["inspection_signals"], "target")
    merge_signals("process_parameters", prior["signals"]["process_parameters"], "confounder")
    merge_signals("metadata_columns", prior["signals"]["metadata_columns"], "batch_id")

    existing_rels = {(r.get("from"), r.get("to")) for r in merged["relationships"]
                     if isinstance(r, dict)}
    added_rels = 0
    for rel in prior["relationships"]:
        if (rel.get("from"), rel.get("to")) not in existing_rels:
            merged["relationships"].append(rel)
            added_rels += 1

    prior_doe = prior["doe"]
    for key in ("factors", "responses"):
        existing = {item.get("col") or item.get("name"): item
                    for item in merged["doe"].get(key) or [] if isinstance(item, dict)}
        merged_list = list(merged["doe"].get(key) or [])
        for item in prior_doe[key]:
            col = item.get("col") or item.get("name")
            if col in existing:
                # never re-point an existing declaration's sign / semantics
                for field in ("unit", "min", "max", "levels", "goal", "lsl", "usl", "target"):
                    if existing[col].get(field) in (None, "") and item.get(field) not in (None, ""):
                        existing[col][field] = item.get(field)
            else:
                merged_list.append(item)
        merged["doe"][key] = merged_list

    merged["doe"].update({
        "profile": PROFILE,
        "scene_key": scene_key,
        "data_stage": data_stage,
        "design_type": design_type or merged["doe"].get("design_type"),
        "extended_from": {"scene_key": (merged.get("scene") or {}).get("name"),
                          "context_fp_version": CONTEXT_FP_VERSION},
    })
    limitations = list(merged.get("limitations") or [])
    for lim in prior["limitations"]:
        if lim not in limitations:
            limitations.append(lim)
    merged["limitations"] = limitations
    merged["doe"]["limitations"] = limitations
    merged.setdefault("provenance", {})
    merged["provenance"].update({
        "engine": ENGINE,
        "profile": PROFILE,
        "build_mode": "extend",
        "data_stage": data_stage,
        "rag_used": False,
        "web_used": False,
        "physics_prior_used": True,
        "context_fp_version": CONTEXT_FP_VERSION,
    })
    merged["_extend_note"] = {
        "added_control_variables": len(added_controls),
        "added_inspection_signals": len(added_targets),
        "added_relationships": added_rels,
    }
    return merged


# ────────────────────────────────────────────────────────────────── prepare

def _skipped_result(elapsed_ms):
    return {
        "action": ACTION_SKIPPED,
        "reason": "ontology mode off — the ontology stage is disabled for this run",
        "ontology_path": None, "brief_json": None, "brief_md": None, "coverage_path": None,
        "version": None, "context_fp": None, "scene_key": None, "data_stage": None,
        "elapsed_ms": elapsed_ms, "rag_used": False, "web_used": False,
        "rag_used_by_prepare": False, "web_used_by_prepare": False,
        "store": {"lookup": "not_attempted", "published": False},
        "wrote": [],
    }


def prepare(run_dir, *, data=None, context=None, mode="auto", scene_key=None,
            store_dir=None, seed=None):
    """DOE ontology stage entry point (contracts §9). See module docstring."""
    started = time.perf_counter()
    run_dir_v = _contained(run_dir)
    ontology_dir = run_dir_v / "01_ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    store = resolve_store_dir(store_dir)

    ctx_path = Path(context) if context else run_dir_v / "00_input" / "analysis_context.json"
    ctx = _read_json(ctx_path) if Path(ctx_path).is_file() else {}
    ctx = copy.deepcopy(ctx) if isinstance(ctx, dict) else {}

    # mode resolution: explicit arg > ctx.ontology.mode > "auto"
    ont_ctx = ctx.get("ontology") if isinstance(ctx.get("ontology"), dict) else {}
    resolved_mode = mode if mode in ("off", "auto", "full", "reuse", "extend") else "auto"
    if resolved_mode == "auto" and ont_ctx.get("mode") in ("off", "full", "auto", "reuse", "extend"):
        resolved_mode = ont_ctx["mode"]
    if resolved_mode == "off":
        return _skipped_result(int((time.perf_counter() - started) * 1000))

    context_fp = _context_fp(ctx)
    scene = _sanitize_scene_key(scene_key) or _sanitize_scene_key(ont_ctx.get("scene_key")) \
        or _sanitize_scene_key(ctx.get("experiment_id")) \
        or _sanitize_scene_key(ctx.get("line_id")) \
        or _sanitize_scene_key(run_dir_v.name) or "doe_scene"

    table = None
    data_path = _resolve_data_path(run_dir_v, data, ctx)
    if data_path is not None:
        table = _load_table_columns(data_path)
    missing = _missing_columns(ctx, table)
    if missing:
        ctx["_missing_columns"] = missing
    data_stage = _resolve_data_stage(ctx, table)
    design_region = ctx.get("design_region") if isinstance(ctx.get("design_region"), dict) else {}
    design_type = ctx.get("design_type_declared") or design_region.get("design_hull") or None

    run_ontology_path = ontology_dir / "ontology.json"
    # an ontology an agent already wrote into this run (builder profile=doe) is adopted
    pending_agent_ontology = None
    if run_ontology_path.is_file() and resolved_mode in ("auto", "full"):
        try:
            candidate = _read_json(run_ontology_path)
            if isinstance(candidate, dict) and candidate.get("scene") and candidate.get("signals"):
                pending_agent_ontology = candidate
        except (json.JSONDecodeError, OSError):
            pending_agent_ontology = None

    lookup = _lookup(store, profile=PROFILE, scene_key=scene, context_fp=context_fp)
    action = None
    build_mode = None
    source_note = None

    if resolved_mode == "reuse":
        action = ACTION_REUSED if lookup["status"] == "exact" else ACTION_BUILT
        if action == ACTION_BUILT:
            source_note = "mode=reuse requested but no exact store match — fell back to build"
    elif resolved_mode == "extend":
        action = ACTION_EXTENDED if lookup["status"] in ("exact", "scene_only") else ACTION_BUILT
    elif resolved_mode == "full":
        action = ACTION_BUILT
        source_note = "mode=full — reuse skipped by explicit request"
    else:
        action = { "exact": ACTION_REUSED, "scene_only": ACTION_EXTENDED, "miss": ACTION_BUILT
                  }[lookup["status"]]

    # an agent-authored ontology wins over the deterministic prior build
    if action == ACTION_BUILT and pending_agent_ontology is not None:
        ontology = pending_agent_ontology
        ontology_prov = ontology.get("provenance") if isinstance(ontology.get("provenance"), dict) else {}
        build_mode = ontology_prov.get("build_mode") or "full"
        source_note = source_note or "adopted the ontology already written in this run dir"
    elif action == ACTION_BUILT:
        ontology = build_prior_ontology(ctx, scene_key=scene, data_stage=data_stage,
                                        design_type=design_type)
        build_mode = "prior_knowledge"
        source_note = source_note or ("design_only prior-knowledge build" if data_stage == "design_only"
                                      else "prior-knowledge build from declarations (no RAG/web)")
    elif action == ACTION_REUSED:
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        ontology = _read_json(stored_path) if stored_path.is_file() else {}
        build_mode = lookup["entry"].get("build_mode") or "reuse"
        source_note = f"reused store asset {lookup['entry'].get('path')}"
    else:  # extended
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        stored = _read_json(stored_path) if stored_path.is_file() else {}
        ontology = extend_ontology(stored, ctx, scene_key=scene, data_stage=data_stage,
                                  design_type=design_type)
        build_mode = "extend"
        source_note = f"extended store asset {lookup['entry'].get('path')}"

    # ── write ontology.json ──
    ontology_for_run = copy.deepcopy(ontology)
    ontology_text = json.dumps(ontology_for_run, ensure_ascii=False, indent=2)
    ontology_bytes = len(ontology_text.encode("utf-8"))

    store_result = {"lookup": lookup["status"], "published": False,
                    "entry_version": lookup["entry"].get("version") if lookup["entry"] else None}

    if action == ACTION_REUSED:
        store_result["reuse"] = _store_call("reuse", "--source",
                                            str(Path(store) / str(lookup["entry"].get("path"))),
                                            "--run-dir", str(run_dir_v), store_dir=store)
        store_result["published"] = True          # the asset already lives in the store
        version = int(lookup["entry"].get("version") or 0) or None
    else:
        _write_json(run_ontology_path, ontology_for_run)
        publish_args = ["publish", "--run-dir", str(run_dir_v), "--scene", scene,
                        "--profile", PROFILE, "--context-fp", context_fp,
                        "--build-mode", str(build_mode), "--data-stage", data_stage]
        if data_path is not None and data_path.suffix.lower() in (".csv", ".tsv"):
            publish_args += ["--data-file", str(data_path)]
        try:
            published = _store_call(*publish_args, store_dir=store)
            store_result.update({"published": True, "entry_version": published.get("version"),
                                 "deduped": bool(published.get("deduped"))})
            version = published.get("version")
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            # the ontology is already in the run dir — the store is an optimisation, not a gate
            store_result.update({"published": False, "error": str(exc)})
            version = None

    # ── brief + coverage (elapsed measured after the ontology work, so a reuse
    #    path can be proven ≤60s with rag_used=false / web_used=false) ──
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    brief = build_brief(ontology_for_run, ctx, context_fp=context_fp)
    brief["scene_key"] = brief.get("scene_key") or scene
    brief["data_stage"] = data_stage
    brief["ontology_version"] = version
    brief["provenance"] = dict(brief.get("provenance") or {})
    brief["provenance"].update({
        "build_mode": build_mode or brief["provenance"].get("build_mode") or "prior_knowledge",
        "engine": ENGINE,
        "store_version": version,
        "store_profile": PROFILE,
        "source_note": source_note,
        "lookup_status": lookup["status"],
        "seed": seed,
        "build_seconds": round(elapsed_ms / 1000.0, 3),
    })
    brief_json, brief_md = write_brief(run_dir_v, brief)

    coverage = {
        "contract_version": brief["contract_version"],
        "artifact": "ontology_coverage",
        "scene_key": brief["scene_key"],
        "profile": PROFILE,
        "data_stage": data_stage,
        "context_fp": context_fp,
        "ontology_version": version,
        "ontology_sha256": brief.get("ontology_sha256"),
        "generated_by": "doe_ontology_prepare.py",
        "factors": [{"col": f.get("col"), "name": f.get("name"), "status": f.get("mapping_status"),
                     "reason": f.get("mapping_reason"), "unit": f.get("unit"),
                     "ontology_signal": f.get("ontology_signal")}
                    for f in brief.get("factors", [])],
        "responses": [{"col": r.get("col"), "name": r.get("name"), "status": r.get("mapping_status"),
                       "reason": r.get("mapping_reason"), "unit": r.get("unit"),
                       "ontology_signal": r.get("ontology_signal")}
                      for r in brief.get("responses", [])],
        "column_mapping": brief.get("column_mapping"),
        "coverage": brief.get("coverage"),
        "elapsed_ms": elapsed_ms,
        "generated_at": _now(),
    }
    coverage_path = _write_json(ontology_dir / "ontology_coverage.json", coverage)

    prov = ontology_for_run.get("provenance") if isinstance(ontology_for_run.get("provenance"), dict) else {}
    rag_used = bool(prov.get("rag_used", False))
    web_used = bool(prov.get("web_used", False))

    return {
        "action": action,
        "ontology_path": str(run_ontology_path),
        "brief_json": brief_json,
        "brief_md": brief_md,
        "coverage_path": str(coverage_path),
        "version": version,
        "context_fp": context_fp,
        "scene_key": brief["scene_key"],
        "data_stage": data_stage,
        "elapsed_ms": elapsed_ms,
        "rag_used": rag_used,
        "web_used": web_used,
        "build_mode": build_mode,
        "source_note": source_note,
        "ontology_bytes": ontology_bytes,
        "cp2_floor_ok": ontology_bytes >= ONTOLOGY_MIN_BYTES,
        "store": store_result,
        "coverage": brief.get("coverage"),
        "lookup": lookup["status"],
        "seed": seed,
        "mode": resolved_mode,
        "wrote": [str(run_ontology_path), brief_json, brief_md, str(coverage_path)],
        "rag_used_by_prepare": False,   # the deterministic stage never calls RAG/web
        "web_used_by_prepare": False,
        "store_dir": str(store),
    }


# ─────────────────────────────────────────────────────────────── Phase 0 门禁

def _table_of(run_dir, ctx):
    data_path = _resolve_data_path(_contained(run_dir), None, ctx)
    return _load_table_columns(data_path) if data_path else None


def _responses_unmeasured(run_dir, ctx):
    """True when no declared response has a single measured cell.

    Either the run table cannot be located (statistics would fail later with a
    less informative error) or every declared response column is entirely empty
    / absent. No declared responses at all → False (not our call to block).
    """
    ctx = ctx if isinstance(ctx, dict) else {}
    response_cols = [r.get("col") or r.get("name") for r in (ctx.get("responses") or [])
                     if isinstance(r, dict)]
    if not response_cols:
        return False
    table = _table_of(run_dir, ctx)
    if table is None:
        return True
    present = [c for c in response_cols if c in table["columns"]]
    if not present:
        return True
    return all(table["empty"].get(c, 0) >= table["total"].get(c, 0) for c in present)


def _is_stats_call(subcommand, ctx):
    if subcommand is not None:
        return str(subcommand).lower() in STATS_SUBCOMMANDS
    ont = ctx.get("ontology") if isinstance(ctx, dict) and isinstance(ctx.get("ontology"), dict) else {}
    return bool(ont.get("stats_requested")) or str(ctx.get("subcommand") or "").lower() in STATS_SUBCOMMANDS


def enforce_gate(run_dir, ctx, *, subcommand=None):
    """DOE analyzer Phase 0 gate (contracts §9 / §7.3).

    Frozen semantics:
      * `ctx["ontology"]` missing, or `mode` in (None, "off") → no-op (gate off).
        This keeps every pre-ontology fixture (F1–F12 carry no `ontology` key) green.
      * mode != off and `01_ontology/ontology_brief.json` missing
          → SystemExit("ONTOLOGY_BRIEF_REQUIRED: …")
      * mode != off and `01_profile/analysis_plan.md` missing
          → SystemExit("ANALYSIS_PLAN_REQUIRED: …")
      * data_stage == "design_only" with no measured response cell (all response
        columns empty, absent, or no run table), on a statistics call
        → SystemExit("DESIGN_ONLY_NO_RESPONSE: …")

    `subcommand` is the analyze.py subcommand ("profile" | "run" | "all" | …). It is
    keyword-only so the frozen `enforce_gate(run_dir, ctx)` call keeps working; when
    omitted the design-only block applies only if the ctx explicitly says statistics
    are being requested (`ontology.stats_requested` / `ctx["subcommand"]`) — an
    unqualified call must never block the allowed `profile`/`ontology`/`build`
    subcommands of a design-only run.
    """
    if not isinstance(ctx, dict):
        return
    ont = ctx.get("ontology")
    if not isinstance(ont, dict):
        return
    mode = ont.get("mode")
    data_stage = ont.get("data_stage") or ctx.get("data_stage")
    run_dir_v = _contained(run_dir)

    # Design-only is a property of the DATA, not of the ontology mode: a design
    # matrix with no measured response must never reach the statistics path,
    # whether or not an ontology was requested. This is the one guard that stays
    # armed with mode=off (contract §7.3 item 4).
    if data_stage == "design_only" and _is_stats_call(subcommand, ctx) \
            and _responses_unmeasured(run_dir_v, ctx):
        raise SystemExit(
            f"{GATE_DESIGN_ONLY_NO_RESPONSE}: data_stage=design_only and no declared response has a "
            f"measured cell — only the ontology/profile/build subcommands may run; collect response "
            f"measurements before executing statistics"
        )

    if mode in (None, "off"):
        return

    brief = run_dir_v / "01_ontology" / "ontology_brief.json"
    if not brief.is_file():
        raise SystemExit(
            f"{GATE_BRIEF_REQUIRED}: ontology mode='{mode}' requires "
            f"{run_dir_v / '01_ontology' / 'ontology_brief.json'} — run the ontology stage "
            f"(doe_ontology_prepare.py) before profiling/analyzing"
        )
    plan = run_dir_v / "01_profile" / "analysis_plan.md"
    if not plan.is_file():
        raise SystemExit(
            f"{GATE_PLAN_REQUIRED}: read 01_ontology/ontology_brief.json and write "
            f"{plan} (scene / factors / responses / units / expected directions / "
            f"confounders / limitations) before running statistics"
        )
    return None


# ------------------------------------------------------------------------ CLI

def _cli():
    ap = argparse.ArgumentParser(description="DOE ontology stage: lookup → reuse/extend/build")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--data", default=None, help="run table path (default: context data_path / 00_input)")
    ap.add_argument("--context", default=None,
                    help="analysis_context.json path (default: RUN_DIR/00_input/analysis_context.json)")
    ap.add_argument("--mode", default="auto", choices=["auto", "full", "reuse", "extend", "off"])
    ap.add_argument("--scene", default=None, help="scene_key override")
    ap.add_argument("--store-dir", default=None, help="ontology store root (default: data/ontology_store)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--json", action="store_true", help="print the full result JSON")
    args = ap.parse_args()

    result = prepare(args.run_dir, data=args.data, context=args.context, mode=args.mode,
                     scene_key=args.scene, store_dir=args.store_dir, seed=args.seed)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary_keys = ("action", "scene_key", "data_stage", "version", "context_fp",
                        "elapsed_ms", "rag_used", "web_used", "lookup", "store",
                        "brief_json", "coverage_path", "reason")
        print(json.dumps({k: result.get(k) for k in summary_keys if k in result},
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
