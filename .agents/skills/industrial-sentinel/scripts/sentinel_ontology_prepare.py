#!/usr/bin/env python
"""sentinel_ontology_prepare.py — sentinel ontology stage (profile=sentinel).

The watch-family twin of doe_ontology_prepare.py, built on the shared core
`.claude/shared/scripts/ontology_prepare_common.py` (single copy, NOT mirrored):
fingerprint → store lookup → reuse/extend/build → 01_ontology 四件套 → store
publish (the store is the single write path).

Declaration sources (decided-prior — a prior build never claims measured
behaviour, `observed_data_behavior="NOT_APPLICABLE"` / `behavior_match=
"UNVERIFIED"` are baked in by common.make_watch_signal):
  1. report_context declarations — `parameter_cols` / `inspection_cols` /
     `units` / `spec_limits`; adopted as knowledge_source="user_provided",
     confidence="KNOWN" when present;
  2. data-table header probe (common.load_table_columns, csv/tsv only) —
     structural time/group/id columns from name conventions;
  3. shipped physics dictionary (common.match_physics_entry — unique candidate
     only) — unit / physical_meaning / governing_law as
     knowledge_source="auto_inferred", confidence="INFERRED". The dictionary's
     `typical_ranges` are REFERENCE BANDS (watch block only, brief shows
     “参考区间（非规格）”) — never normal_range, never a spec (plan v2
     principle 2).

Ontology shape: standard schema (common.empty_ontology_skeleton) —
parameter columns → signals.process_parameters (schema_role=predictor);
inspection/quality columns → signals.inspection_signals (schema_role=target);
time/group/id columns → signals.metadata_columns; user/context spec_limits are
the ONLY source of normal_range ([lsl, usl]); relationships stay EMPTY (no
direction declaration → no causal edges invented). A free `watch` block carries
the profile-specific declarations (roles / units / reference_bands /
column_mapping / declared_windows).

`--ontology <path>` (explicit adoption): when the stage builds, the named asset
is adopted verbatim (valid JSON with `scene` + `signals` objects) instead of
the deterministic prior — build_mode="full", source_note names the adoption;
the store publish still runs. Missing/invalid asset → SystemExit with a clear
error. mode=off writes nothing.

Gate: CP-2 — `node .claude/shared/scripts/validate.mjs <ontology_schema>
<ontology.json>` exit 0 AND size >= 1024B, else SystemExit.

Result contract (mirrors the DOE stage): action / ontology_path / brief_json /
brief_md / coverage_path / version / context_fp / scene_key / data_stage /
elapsed_ms / rag_used / web_used / build_mode / source_note / ontology_bytes /
cp2_floor_ok / store / coverage / lookup / mode / wrote /
rag_used_by_prepare=False / web_used_by_prepare=False / store_dir.

CLI:
  python sentinel_ontology_prepare.py --run-dir DIR [--data PATH]
      [--context PATH] [--mode auto|full|reuse|extend|off] [--scene KEY]
      [--store-dir DIR] [--ontology PATH] [--json]

ZERO LLM / ZERO NETWORK on this path — rag_used/web_used are reported from the
ontology provenance, never invented (the deterministic stage always reports
False; an adopted asset's flags are passed through as-is).
"""

import copy
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]          # …/industrial-sentinel/scripts → repo root
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

import ontology_prepare_common as oc  # noqa: E402

PROFILE = "sentinel"
ENGINE = "industrial-ontology-builder"


def append_pipeline_event(run_dir, event, detail):
    """Append one JSON Lines event to <run_dir>/.pipeline_events.jsonl."""
    path = Path(run_dir) / ".pipeline_events.jsonl"
    payload = {"timestamp": oc.now_iso(), "event": event,
               "run_dir": str(run_dir), "detail": detail or {}}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
BRIEF_CONTRACT_VERSION = "1.0"
CONTEXT_FILENAME = "report_context.json"
# fixed candidate names in 00_input (declaration-first; never a free scan):
# data.csv (generic) / preprocessed_data.csv (preprocessor single-primary
# output) / history.csv (the watch family's canonical baseline source name)
DATA_CANDIDATES = ("data.csv", "preprocessed_data.csv", "history.csv")
VALIDATOR_JS = SHARED_SCRIPTS / "validate.mjs"

# header-level structural roles (same hint families as sentinelcore._io —
# kept local so the prepare stage stays pandas-free)
_TIME_HINTS = re.compile(r"(time|date|timestamp|时刻|时间|日期)", re.IGNORECASE)
_GROUP_HINTS = re.compile(r"(group|line|batch|shift|product|机组|产线|批次|班组|产品|线体)", re.IGNORECASE)
_ID_HINTS = re.compile(r"(^id$|_id$|^no$|_no$|编号|序号|^index$|^row$)", re.IGNORECASE)

_SCHEMA_ROLE_FOR_METADATA = {"time": "timestamp", "group": "batch_id", "id": "batch_id"}


def _sanitize_scene_key(value):
    if value in (None, ""):
        return None
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value))


# ────────────────────────────────────────────── 声明收集与列分类（decided-prior）

def normalize_spec_limits(raw):
    """context spec_limits → {col: [lsl, usl]}; accepts {col:{lsl,usl}} and
    {col:[lsl,usl]}. The ONLY feed for normal_range (user/context declared)."""
    specs = {}
    if not isinstance(raw, dict):
        return specs
    for col, value in raw.items():
        if isinstance(value, dict):
            lo, hi = value.get("lsl"), value.get("usl")
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            lo, hi = value[0], value[1]
        else:
            continue
        if lo is None and hi is None:
            continue
        specs[str(col)] = [lo, hi]
    return specs


def structural_role(col):
    """time/group/id from the column NAME only; None = not structural."""
    if _TIME_HINTS.search(col):
        return "time"
    if _GROUP_HINTS.search(col):
        return "group"
    if _ID_HINTS.search(col):
        return "id"
    return None


def build_prior_ontology(ctx, table, *, scene_key):
    """Deterministic declaration-only ontology (zero fabrication).

    Returns (ontology, mapping_rows, limitations). `mapping_rows` carries one
    explicit entry per table column (plus declared-but-absent columns) —
    nothing silent: matched / inferred / unmatched, each with a reason.
    """
    ctx = ctx if isinstance(ctx, dict) else {}
    parameter_cols = [str(c) for c in (ctx.get("parameter_cols") or [])]
    inspection_cols = [str(c) for c in (ctx.get("inspection_cols") or [])]
    units_declared = {str(k): str(v) for k, v in (ctx.get("units") or {}).items()
                      if v not in (None, "")}
    specs = normalize_spec_limits(ctx.get("spec_limits"))
    columns = [str(c) for c in (table or {}).get("columns") or []]

    declared_role = {}
    for col in inspection_cols:
        declared_role[col] = "inspection"
    for col in parameter_cols:
        declared_role.setdefault(col, "parameter")

    dictionary = oc.load_physics_dictionary()
    families = dictionary.get("parameters") if isinstance(dictionary.get("parameters"), dict) \
        else dictionary

    rows = []
    process_parameters = []
    inspection_signals = []
    metadata_columns = []
    units = {}
    reference_bands = {}
    declared_windows = []
    limitations = [
        "声明式先验：本本体只记录声明（角色/单位/规格），不声称任何实测行为"
        "（observed_data_behavior=NOT_APPLICABLE / behavior_match=UNVERIFIED）",
        "词典 typical_ranges 仅作参考区间展示（watch.reference_bands），"
        "永不写入 normal_range / 规格 / Cpk",
        "relationships 留空：无方向声明，不造因果边",
    ]

    def declared_signal(col, kind):
        spec = specs.get(col)
        sig = oc.make_watch_signal(
            column=col, role=kind, schema_role="target" if kind == "inspection" else "predictor",
            unit=units_declared.get(col),
            normal_range=[spec[0], spec[1]] if spec else None,
            knowledge_source="user_provided", confidence="KNOWN",
            inference_basis=f"declared in report_context as {kind} column")
        if col in units_declared:
            units[col] = units_declared[col]
        if spec:
            declared_windows.append({"factor": col, "lo": spec[0], "hi": spec[1]})
        return sig

    for col in columns:
        role = declared_role.get(col)
        spec = specs.get(col)
        if role:
            sig = declared_signal(col, role)
            (inspection_signals if role == "inspection" else process_parameters).append(sig)
            rows.append({
                "col": col, "role": role, "unit": units_declared.get(col),
                "spec": spec, "knowledge_source": "user_provided", "confidence": "KNOWN",
                "mapping_status": "matched",
                "mapping_reason": f"declared as {role} column in report_context",
                "physical_meaning": None, "governing_law": None, "reference_band": False,
            })
            continue
        struct = structural_role(col)
        if struct:
            metadata_columns.append({
                "name": col, "column": col,
                "role": _SCHEMA_ROLE_FOR_METADATA[struct],
                "description": f"watch 角色 {struct}（列名结构识别，未经数据验证）",
            })
            rows.append({
                "col": col, "role": struct, "unit": units_declared.get(col),
                "spec": spec, "knowledge_source": "auto_inferred", "confidence": "INFERRED",
                "mapping_status": "inferred",
                "mapping_reason": f"structural role '{struct}' from column-name convention",
                "physical_meaning": None, "governing_law": None, "reference_band": False,
            })
            if col in units_declared:
                units[col] = units_declared[col]
            continue
        match = oc.match_physics_entry(families, col)
        if match:
            entry = match["entry"]
            unit = entry.get("physical_unit_SI")
            sig = oc.make_watch_signal(
                column=col, role="parameter", schema_role="predictor",
                unit=unit,
                physical_meaning=entry.get("physical_quantity"),
                governing_law=entry.get("governing_law"),
                knowledge_source="auto_inferred", confidence="INFERRED",
                inference_basis=f"unique dictionary entry '{match['family']}'")
            process_parameters.append(sig)
            band = oc.dictionary_reference_band(entry)
            if band is not None:
                reference_bands[col] = band
            if unit:
                units[col] = str(unit)
            rows.append({
                "col": col, "role": "parameter", "unit": unit,
                "spec": spec, "knowledge_source": "auto_inferred", "confidence": "INFERRED",
                "mapping_status": "inferred",
                "mapping_reason": f"unique dictionary entry '{match['family']}' "
                                  f"(unit/meaning/law only; typical_ranges kept as reference band)",
                "physical_meaning": entry.get("physical_quantity"),
                "governing_law": entry.get("governing_law"), "reference_band": band is not None,
            })
            continue
        rows.append({
            "col": col, "role": "unmapped", "unit": units_declared.get(col),
            "spec": spec, "knowledge_source": None, "confidence": "UNKNOWN",
            "mapping_status": "unmatched",
            "mapping_reason": "no context declaration and no unique dictionary entry — "
                              "role/unit undeclared（单位未声明）",
            "physical_meaning": None, "governing_law": None, "reference_band": False,
        })

    # declared columns absent from the (probe-able) table → explicit unmatched
    table_cols = set(columns)
    for col in sorted({*parameter_cols, *inspection_cols} - table_cols):
        reason = ("declared in report_context but the data table could not be probed "
                  "(csv/tsv header probe only)" if table is None
                  else f"declared as {declared_role[col]} column in report_context but "
                       f"not present in the data table")
        rows.append({
            "col": col, "role": declared_role[col], "unit": units_declared.get(col),
            "spec": specs.get(col), "knowledge_source": "user_provided",
            "confidence": "KNOWN", "mapping_status": "unmatched",
            "mapping_reason": reason, "physical_meaning": None, "governing_law": None,
            "reference_band": False,
        })
        if table is None:
            # keep the declaration itself (semantics, not presence) as a signal
            sig = declared_signal(col, declared_role[col])
            (inspection_signals if declared_role[col] == "inspection"
             else process_parameters).append(sig)

    if table is None:
        limitations.append("数据表不可探测（缺失或非 csv/tsv）——列角色仅来自上下文声明，"
                           "未经数据表表头核对")
    n_unmatched = sum(1 for r in rows if r["mapping_status"] == "unmatched")
    if n_unmatched:
        limitations.append(f"{n_unmatched} 列未解决映射（见 watch.column_mapping.unmatched）——"
                           "这些列不参与任何角色驱动的判断")

    watch_block = {
        "profile": PROFILE,
        "scene_key": scene_key,
        "roles": {r["col"]: r["role"] for r in rows},
        "units": dict(units),
        "undeclared_units": sorted(r["col"] for r in rows if not r["unit"]),
        "reference_bands": reference_bands,
        "declared_windows": declared_windows,
        "column_mapping": {
            "matched": [{"col": r["col"], "reason": r["mapping_reason"]}
                        for r in rows if r["mapping_status"] == "matched"],
            "inferred": [{"col": r["col"], "reason": r["mapping_reason"]}
                         for r in rows if r["mapping_status"] == "inferred"],
            "unmatched": [{"col": r["col"], "reason": r["mapping_reason"]}
                          for r in rows if r["mapping_status"] == "unmatched"],
        },
    }

    ontology = oc.empty_ontology_skeleton(
        scene_name=scene_key,
        process_type=str(ctx.get("line_id") or ctx.get("product_id") or "production_watch"))
    production_goal = ctx.get("objective") or ctx.get("notes")
    if production_goal:
        ontology["scene"]["production_goal"] = str(production_goal)
    ontology["signals"]["process_parameters"] = process_parameters
    ontology["signals"]["inspection_signals"] = inspection_signals
    ontology["signals"]["metadata_columns"] = metadata_columns
    ontology["relationships"] = []
    ontology["metadata"]["units"] = dict(units)
    ontology["watch"] = watch_block
    ontology["limitations"] = limitations
    ontology["provenance"] = oc.standard_provenance(
        profile=PROFILE, engine=ENGINE, build_mode="prior_knowledge",
        data_stage="collected",
        source="report_context declarations + data-table header probe + shipped "
               "physics dictionary (unit/role/meaning/law only)")
    ontology["provenance"]["context_fp_version"] = oc.WATCH_CONTEXT_FP_VERSION
    return ontology, rows, limitations


def extend_ontology(stored, prior):
    """Merge a stored ontology with the current declarations (additive).

    Existing signals are never re-pointed: the current declaration is
    authoritative only for unit / declared spec (when present), absent fields
    are filled, new columns are appended. The `watch` block always reflects the
    CURRENT declarations (it is a projection, not accumulated knowledge).
    """
    merged = copy.deepcopy(stored if isinstance(stored, dict) else {})
    merged.setdefault("scene", copy.deepcopy(prior.get("scene") or {}))
    merged.setdefault("signals", {})
    for key in ("inspection_signals", "process_parameters", "control_variables",
                "events", "metadata_columns"):
        merged["signals"].setdefault(key, [])
    merged.setdefault("relationships", [])
    merged.setdefault("metadata", {})
    merged["metadata"].setdefault("units", {})

    added = {"inspection_signals": 0, "process_parameters": 0, "metadata_columns": 0}
    for key, incoming in (("process_parameters", prior["signals"]["process_parameters"]),
                          ("inspection_signals", prior["signals"]["inspection_signals"]),
                          ("metadata_columns", prior["signals"]["metadata_columns"])):
        existing = {s.get("column") or s.get("name"): s
                    for s in merged["signals"][key] if isinstance(s, dict)}
        for sig in incoming:
            col = sig.get("column") or sig.get("name")
            target = existing.get(col)
            if target is None:
                merged["signals"][key].append(copy.deepcopy(sig))
                added[key] += 1
                continue
            if sig.get("unit"):
                target["unit"] = sig["unit"]
            if sig.get("normal_range") is not None:
                target["normal_range"] = sig["normal_range"]
            for field in ("physical_meaning", "governing_law"):
                if not target.get(field) and sig.get(field):
                    target[field] = sig[field]
            if not target.get("knowledge_source") and sig.get("knowledge_source"):
                target["knowledge_source"] = sig["knowledge_source"]
    merged_units = dict(merged["metadata"].get("units") or {})
    merged_units.update(prior.get("metadata", {}).get("units") or {})
    merged["metadata"]["units"] = merged_units
    merged["watch"] = copy.deepcopy(prior.get("watch") or {})
    merged.setdefault("limitations", [])
    for lim in prior.get("limitations") or []:
        if lim not in merged["limitations"]:
            merged["limitations"].append(lim)
    merged["provenance"] = dict(merged.get("provenance") or {})
    merged["provenance"].update(copy.deepcopy(prior.get("provenance") or {}))
    merged["provenance"]["build_mode"] = "extend"
    merged["_extend_note"] = {
        "added_process_parameters": added["process_parameters"],
        "added_inspection_signals": added["inspection_signals"],
        "added_metadata_columns": added["metadata_columns"],
    }
    return merged


# ────────────────────────────────────────────────────────────── brief（中文）

def _fmt(value):
    return "—" if value in (None, "", []) else str(value)


def build_brief(ontology, mapping_rows, *, scene_key, context_fp, data_path,
                limitations):
    """Sentinel brief (profile-specific; the DOE brief builder reads the doe
    block and is deliberately NOT shared). Zero silent columns: coverage.ratio
    == 1.0 ⟺ no unmatched column remains."""
    rows = mapping_rows
    n_matched = sum(1 for r in rows if r["mapping_status"] == "matched")
    n_inferred = sum(1 for r in rows if r["mapping_status"] == "inferred")
    n_unmatched = sum(1 for r in rows if r["mapping_status"] == "unmatched")
    n_total = len(rows)
    watch_block = ontology.get("watch") if isinstance(ontology.get("watch"), dict) else {}
    prov = ontology.get("provenance") if isinstance(ontology.get("provenance"), dict) else {}
    scene = ontology.get("scene") if isinstance(ontology.get("scene"), dict) else {}
    specs = [{"col": r["col"], "normal_range": r["spec"],
              "source": "report_context.spec_limits"}
             for r in rows if r["spec"]]
    bands = [{"col": col, "band": band,
              "note": "词典参考区间（非规格）——仅展示，永不参与告警阈值/规格/Cpk"}
             for col, band in sorted((watch_block.get("reference_bands") or {}).items())]
    open_items = [{"col": r["col"], "reason": r["mapping_reason"]}
                  for r in rows if r["mapping_status"] == "unmatched"]

    return {
        "contract_version": BRIEF_CONTRACT_VERSION,
        "artifact": "ontology_brief",
        "profile": PROFILE,
        "scene_key": scene_key,
        "data_stage": "collected",
        "ontology_version": None,          # store version filled by the caller
        "ontology_sha256": oc.sha256_text(
            json.dumps(ontology, ensure_ascii=False, sort_keys=True)),
        "context_fp": context_fp,
        "scene": {
            "name": scene.get("name") or scene_key,
            "process_type": scene.get("process_type"),
            "production_goal": scene.get("production_goal"),
        },
        "data_table": {"path": str(data_path) if data_path else None,
                       "n_columns": 0},   # probed header count, filled by prepare
        "columns": [dict(r) for r in rows],
        "spec_and_reference": {"declared_specs": specs, "reference_bands": bands},
        "limitations": list(limitations),
        "open_items": open_items,
        "column_mapping": {
            "matched": [{"col": r["col"], "reason": r["mapping_reason"]}
                        for r in rows if r["mapping_status"] == "matched"],
            "inferred": [{"col": r["col"], "reason": r["mapping_reason"]}
                         for r in rows if r["mapping_status"] == "inferred"],
            "unmatched": [{"col": r["col"], "reason": r["mapping_reason"]}
                          for r in rows if r["mapping_status"] == "unmatched"],
        },
        "coverage": {
            # ratio == 1.0 ⟺ nothing silent/unresolved: every column is matched
            # or explicitly inferred; any unmatched column pulls it below 1.0.
            "n_columns": n_total,
            "n_matched": n_matched,
            "n_inferred": n_inferred,
            "n_unmatched": n_unmatched,
            "n_silent": 0,
            "ratio": ((n_matched + n_inferred) / n_total) if n_total else 1.0,
        },
        "provenance": {
            "build_mode": prov.get("build_mode") or "prior_knowledge",
            "engine": prov.get("engine") or ENGINE,
            "profile": prov.get("profile") or PROFILE,
            "rag_used": bool(prov.get("rag_used", False)),
            "web_used": bool(prov.get("web_used", False)),
            "physics_prior_used": bool(prov.get("physics_prior_used", True)),
        },
    }


def render_markdown(brief):
    cov = brief.get("coverage") or {}
    cm = brief.get("column_mapping") or {}
    prov = brief.get("provenance") or {}
    lines = [f"# 本体简报 · {brief.get('scene_key') or 'sentinel_scene'}（sentinel 哨兵快筛）", ""]
    lines.append(f"- 契约版本：{brief.get('contract_version')}（profile={brief.get('profile')}）")
    lines.append(f"- 数据阶段：`{brief.get('data_stage')}`　本体版本：{_fmt(brief.get('ontology_version'))}")
    lines.append(f"- 上下文指纹 context_fp：`{_fmt(brief.get('context_fp'))}`")
    lines.append("")
    lines.append("## 1. 场景理解")
    lines.append("")
    scene = brief.get("scene") or {}
    lines.append(f"- 场景：{_fmt(scene.get('name'))}　工艺类型：{_fmt(scene.get('process_type'))}"
                 f"　生产目标：{_fmt(scene.get('production_goal'))}")
    dt = brief.get("data_table") or {}
    lines.append(f"- 数据表：`{_fmt(dt.get('path'))}`（探测到 {_fmt(dt.get('n_columns'))} 个数据列）")
    lines.append("- 本体只承载声明（角色/单位/规格）；越界判断所用的声明窗口一律封顶 warn，"
                 "统计量只来自实测数据。")
    lines.append("")
    lines.append("## 2. 列角色与单位")
    lines.append("")
    lines.append("| 列 | 角色 | 单位 | 规格 | 映射 | 来源 | 置信 | 物理含义 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in brief.get("columns") or []:
        spec = (f"[{r['spec'][0]}, {r['spec'][1]}]" if r.get("spec") else "—")
        lines.append(f"| `{_fmt(r.get('col'))}` | {_fmt(r.get('role'))} | "
                     f"{_fmt(r.get('unit')) if r.get('unit') else '单位未声明'} | {spec} | "
                     f"{_fmt(r.get('mapping_status'))} | {_fmt(r.get('knowledge_source'))} | "
                     f"{_fmt(r.get('confidence'))} | {_fmt(r.get('physical_meaning'))} |")
    lines.append("")
    lines.append("## 3. 规格与参考区间")
    lines.append("")
    declared = (brief.get("spec_and_reference") or {}).get("declared_specs") or []
    if declared:
        for s in declared:
            lines.append(f"- 声明规格 `{s['col']}`：normal_range={s['normal_range']}"
                         f"（来源：{s['source']}；仅用户/上下文声明可写入 normal_range）")
    else:
        lines.append("- 无用户/上下文声明规格（normal_range 全部为空；"
                     "C2 窗口需基线构建时传入 --ontology 才能启用）")
    bands = (brief.get("spec_and_reference") or {}).get("reference_bands") or []
    for b in bands:
        lines.append(f"- 参考区间（非规格）`{b['col']}`：{json.dumps(b['band'], ensure_ascii=False)}"
                     f"——{b['note']}")
    lines.append("")
    lines.append("## 4. 混杂与局限")
    lines.append("")
    for lim in brief.get("limitations") or ["（无）"]:
        lines.append(f"- {lim}")
    lines.append("")
    lines.append("## 5. 列映射与覆盖（0 静默）")
    lines.append("")
    lines.append(f"- matched: {len(cm.get('matched') or [])}　"
                 f"inferred: {len(cm.get('inferred') or [])}　"
                 f"unmatched: {len(cm.get('unmatched') or [])}")
    lines.append(f"- coverage.ratio = {cov.get('ratio')}"
                 f"（1.0 当且仅当无静默列/未解决项）")
    for status in ("inferred", "unmatched"):
        for row in cm.get(status) or []:
            lines.append(f"- [{status}] `{_fmt(row.get('col'))}`：{_fmt(row.get('reason'))}")
    lines.append("")
    lines.append("## 6. 未解决项")
    lines.append("")
    open_items = brief.get("open_items") or []
    if open_items:
        for item in open_items:
            lines.append(f"- `{_fmt(item.get('col'))}`：{_fmt(item.get('reason'))}")
    else:
        lines.append("- （无）")
    lines.append("")
    lines.append("## 7. 来源")
    lines.append("")
    lines.append(f"- build_mode={_fmt(prov.get('build_mode'))}　engine={_fmt(prov.get('engine'))}")
    lines.append(f"- rag_used={prov.get('rag_used')}　web_used={prov.get('web_used')}　"
                 f"physics_prior_used={prov.get('physics_prior_used')}")
    lines.append("")
    lines.append("> 本简报由确定性脚本生成（零 RAG/零网络）；watch 消费本体声明窗口时"
                 "一律 `window_source=ontology_declared` 且告警封顶 warn。")
    lines.append("")
    return "\n".join(lines)


def write_brief(run_dir, brief):
    run_dir_v = oc.contained(run_dir)
    out_dir = run_dir_v / "01_ontology"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = oc.write_json_strict(out_dir / "ontology_brief.json", brief)
    md_path = out_dir / "ontology_brief.md"
    md_path.write_text(render_markdown(brief), encoding="utf-8")
    return str(json_path), str(md_path)


# ──────────────────────────────────────────────────────────────────── CP-2

def cp2_check(ontology_path):
    """CP-2: schema-valid (validate.mjs exit 0) AND >= ONTOLOGY_MIN_BYTES."""
    proc = subprocess.run(
        ["node", str(VALIDATOR_JS), str(oc.ONTOLOGY_SCHEMA), str(ontology_path)],
        capture_output=True, text=True, timeout=120, shell=False, cwd=str(REPO_ROOT))
    schema_ok = proc.returncode == 0
    bytes_ok = Path(ontology_path).stat().st_size >= oc.ONTOLOGY_MIN_BYTES
    detail = (proc.stdout or proc.stderr or "").strip()[-500:]
    return schema_ok and bytes_ok, detail


# ────────────────────────────────────────────────────────────────── prepare

def _skipped_result(elapsed_ms):
    return {
        "action": oc.ACTION_SKIPPED,
        "reason": "ontology mode off — the ontology stage is disabled for this run",
        "ontology_path": None, "brief_json": None, "brief_md": None, "coverage_path": None,
        "version": None, "context_fp": None, "scene_key": None, "data_stage": None,
        "elapsed_ms": elapsed_ms, "rag_used": False, "web_used": False,
        "build_mode": None, "source_note": None, "ontology_bytes": None,
        "cp2_floor_ok": None,
        "rag_used_by_prepare": False, "web_used_by_prepare": False,
        "store": {"lookup": "not_attempted", "published": False},
        "coverage": None, "lookup": "not_attempted", "mode": "off", "wrote": [],
        "store_dir": None,
    }


def _resolve_explicit_asset(ontology):
    """--ontology explicit adoption: valid JSON with scene+signals, verbatim."""
    asset_path = oc.contained(ontology)
    if not asset_path.is_file():
        raise SystemExit(f"EXPLICIT_ONTOLOGY_INVALID: --ontology asset not found: {asset_path}")
    try:
        doc = oc.read_json(asset_path)
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"EXPLICIT_ONTOLOGY_INVALID: --ontology asset is not valid JSON: "
                         f"{asset_path}: {exc}")
    if not (isinstance(doc, dict) and isinstance(doc.get("scene"), dict)
            and isinstance(doc.get("signals"), dict)):
        raise SystemExit(
            f"EXPLICIT_ONTOLOGY_INVALID: --ontology asset must be an ontology JSON with "
            f"'scene' and 'signals' objects: {asset_path}")
    return doc


def _commit(run_dir_v, *, store, store_dir, action, lookup, scene, context_fp,
            build_mode, data_path):
    """Action-driven store commit (single write path: ontology_store.mjs).

    reused        → verbatim reuse-copy of the exact hit (common.commit_to_store)
    built/extended → publish the run's 01_ontology/ontology.json (content-based
                     dedupe collapses identical payloads)

    common.commit_to_store branches on lookup_status, which equals the action
    only in auto mode: mode=full can build despite an exact hit (explicit
    --ontology adoption / explicit rebuild), and a fresh build must never be
    clobbered by the reuse-copy — so the publish branch is driven by the action
    here, on top of the same shared primitives.
    """
    if action == oc.ACTION_REUSED:
        return oc.commit_to_store(
            run_dir_v, store=store, store_dir=store, profile=PROFILE, scene=scene,
            context_fp=context_fp, build_mode=build_mode, data_stage="collected",
            data_path=data_path, lookup_status=lookup["status"],
            lookup_entry=lookup["entry"])
    store_result = {"lookup": lookup["status"], "published": False,
                    "entry_version": lookup["entry"].get("version") if lookup["entry"] else None}
    publish_args = ["publish", "--run-dir", str(run_dir_v), "--scene", scene,
                    "--profile", PROFILE, "--context-fp", context_fp,
                    "--build-mode", str(build_mode), "--data-stage", "collected"]
    if data_path is not None and Path(data_path).suffix.lower() in (".csv", ".tsv"):
        publish_args += ["--data-file", str(data_path)]
    try:
        published = oc.store_call(*publish_args, store_dir=store)
        store_result.update({"published": True, "entry_version": published.get("version"),
                             "deduped": bool(published.get("deduped"))})
        return store_result, published.get("version")
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        # the ontology is already in the run dir — the store is an optimisation, not a gate
        store_result.update({"published": False, "error": str(exc)})
        return store_result, None


def prepare(run_dir, *, data=None, context=None, mode="auto", scene_key=None,
            store_dir=None, ontology=None):
    """Sentinel ontology stage entry point. See module docstring."""
    started = time.perf_counter()
    run_dir_v = oc.contained(run_dir)
    ontology_dir = run_dir_v / "01_ontology"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    store = oc.resolve_store_dir(store_dir)

    ctx_path = Path(context) if context else run_dir_v / "00_input" / CONTEXT_FILENAME
    ctx = oc.read_json(ctx_path) if Path(ctx_path).is_file() else {}
    ctx = copy.deepcopy(ctx) if isinstance(ctx, dict) else {}

    # mode resolution: explicit arg > ctx.ontology.mode > "auto"
    ont_ctx = ctx.get("ontology") if isinstance(ctx.get("ontology"), dict) else {}
    resolved_mode = mode if mode in oc.VALID_MODES else "auto"
    if resolved_mode == "auto" and ont_ctx.get("mode") in oc.VALID_MODES:
        resolved_mode = ont_ctx["mode"]
    if resolved_mode == "off":
        return _skipped_result(oc.timed_result(started))

    explicit_asset = _resolve_explicit_asset(ontology) if ontology else None

    table = None
    data_path = oc.resolve_data_path(run_dir_v, data, ctx, DATA_CANDIDATES)
    if data_path is not None:
        table = oc.load_table_columns(data_path)

    scene = _sanitize_scene_key(scene_key) or _sanitize_scene_key(ont_ctx.get("scene_key")) \
        or _sanitize_scene_key(ctx.get("scene") if isinstance(ctx.get("scene"), str) else None) \
        or _sanitize_scene_key(ctx.get("line_id")) \
        or _sanitize_scene_key(run_dir_v.name) or "sentinel_scene"

    prior, mapping_rows, limitations = build_prior_ontology(ctx, table, scene_key=scene)
    context_fp = oc.compute_watch_context_fp({
        "columns": [{"col": r["col"], "role": r["role"], "unit": r["unit"] or "",
                     "lsl": r["spec"][0] if r["spec"] else None,
                     "usl": r["spec"][1] if r["spec"] else None}
                    for r in mapping_rows],
        "windows": [{"factor": w["factor"], "lo": w["lo"], "hi": w["hi"]}
                    for w in prior["watch"]["declared_windows"]],
    })

    lookup = oc.lookup(store, profile=PROFILE, scene_key=scene, context_fp=context_fp)
    action, state_note = oc.resolve_action(resolved_mode, lookup["status"])

    run_ontology_path = ontology_dir / "ontology.json"
    ontology = None
    build_mode = None
    source_note = state_note

    if action == oc.ACTION_REUSED:
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        ontology = oc.read_json(stored_path) if stored_path.is_file() else {}
        build_mode = lookup["entry"].get("build_mode") or "reuse"
        source_note = source_note or f"reused store asset {lookup['entry'].get('path')}"
    elif action == oc.ACTION_EXTENDED:
        stored_path = Path(store) / str(lookup["entry"].get("path") or "")
        stored = oc.read_json(stored_path) if stored_path.is_file() else {}
        ontology = extend_ontology(stored, prior)
        build_mode = "extend"
        source_note = source_note or f"extended store asset {lookup['entry'].get('path')}"
    else:  # built
        if explicit_asset is not None:
            ontology = copy.deepcopy(explicit_asset)
            build_mode = "full"
            source_note = ("adopted explicit ontology asset (--ontology); declarations "
                           "adopted verbatim, store publish still runs")
        elif run_ontology_path.is_file() and resolved_mode in ("auto", "full"):
            try:
                candidate = oc.read_json(run_ontology_path)
            except (json.JSONDecodeError, OSError):
                candidate = None
            if isinstance(candidate, dict) and candidate.get("scene") and candidate.get("signals"):
                ontology = candidate
                prov = ontology.get("provenance") if isinstance(ontology.get("provenance"), dict) else {}
                build_mode = prov.get("build_mode") or "full"
                source_note = source_note or "adopted the ontology already written in this run dir"
        if ontology is None:
            ontology = prior
            build_mode = "prior_knowledge"
            source_note = source_note or ("declaration-only build (report_context + data header "
                                          "probe + shipped dictionary; no RAG/web)")

    ontology_for_run = copy.deepcopy(ontology)
    ontology_text = json.dumps(ontology_for_run, ensure_ascii=False, indent=2)
    ontology_bytes = len(ontology_text.encode("utf-8"))

    if action == oc.ACTION_REUSED:
        cp2_ok = True   # store assets passed CP-2 at publish time
    else:
        oc.write_json_strict(run_ontology_path, ontology_for_run)
        ok, detail = cp2_check(run_ontology_path)
        if not ok:
            raise SystemExit(
                f"CP2_ONTOLOGY_INVALID: {run_ontology_path} failed the CP-2 gate "
                f"(schema validation + {oc.ONTOLOGY_MIN_BYTES}B floor): {detail}")
        cp2_ok = True
    store_result, version = _commit(
        run_dir_v, store=store, store_dir=store_dir, action=action, lookup=lookup,
        scene=scene, context_fp=context_fp, build_mode=build_mode, data_path=data_path)

    elapsed_ms = oc.timed_result(started)
    brief = build_brief(ontology_for_run, mapping_rows, scene_key=scene,
                        context_fp=context_fp, data_path=data_path, limitations=limitations)
    brief["ontology_version"] = version
    brief["data_table"]["n_columns"] = len(table["columns"]) if table else 0
    brief["provenance"].update({
        "store_version": version,
        "store_profile": PROFILE,
        "source_note": source_note,
        "lookup_status": lookup["status"],
        "build_seconds": round(elapsed_ms / 1000.0, 3),
    })
    brief_json, brief_md = write_brief(run_dir_v, brief)

    coverage = {
        "contract_version": brief["contract_version"],
        "artifact": "ontology_coverage",
        "scene_key": brief["scene_key"],
        "profile": PROFILE,
        "data_stage": "collected",
        "context_fp": context_fp,
        "ontology_version": version,
        "ontology_sha256": brief.get("ontology_sha256"),
        "generated_by": "sentinel_ontology_prepare.py",
        "columns": [{"col": r["col"], "role": r["role"], "status": r["mapping_status"],
                     "reason": r["mapping_reason"], "unit": r["unit"],
                     "knowledge_source": r["knowledge_source"], "confidence": r["confidence"]}
                    for r in mapping_rows],
        "column_mapping": brief.get("column_mapping"),
        "coverage": brief.get("coverage"),
        "elapsed_ms": elapsed_ms,
        "generated_at": oc.now_iso(),
    }
    coverage_path = oc.write_json_strict(ontology_dir / "ontology_coverage.json", coverage)

    prov = ontology_for_run.get("provenance") if isinstance(ontology_for_run.get("provenance"), dict) else {}
    rag_used = bool(prov.get("rag_used", False))
    web_used = bool(prov.get("web_used", False))

    append_pipeline_event(run_dir_v, "prepare_done", {
        "action": action, "scene_key": brief["scene_key"], "version": version,
        "build_mode": build_mode, "lookup": lookup["status"],
    })

    return {
        "action": action,
        "ontology_path": str(run_ontology_path),
        "brief_json": brief_json,
        "brief_md": brief_md,
        "coverage_path": str(coverage_path),
        "version": version,
        "context_fp": context_fp,
        "scene_key": brief["scene_key"],
        "data_stage": "collected",
        "elapsed_ms": elapsed_ms,
        "rag_used": rag_used,
        "web_used": web_used,
        "build_mode": build_mode,
        "source_note": source_note,
        "ontology_bytes": ontology_bytes,
        "cp2_floor_ok": cp2_ok and ontology_bytes >= oc.ONTOLOGY_MIN_BYTES,
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

def _cli_prepare(args):
    """cli_main hands over the parsed args namespace (shared driver contract)."""
    return prepare(args.run_dir, data=args.data, context=args.context,
                   mode=args.mode, scene_key=args.scene, store_dir=args.store_dir,
                   ontology=args.ontology)


if __name__ == "__main__":
    raise SystemExit(oc.cli_main(
        _cli_prepare,
        prog_desc="sentinel ontology stage: lookup → reuse/extend/build (profile=sentinel)",
        extra_args=(
            (("--ontology",),
             {"default": None,
              "help": "explicit ontology asset to adopt when the stage builds "
                      "(valid JSON with scene+signals; adopted verbatim, build_mode=full)"}),
        )))
