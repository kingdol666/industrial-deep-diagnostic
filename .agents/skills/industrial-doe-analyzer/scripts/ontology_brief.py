#!/usr/bin/env python
"""ontology_brief.py — the Agent understanding contract of a DOE run (P1-4).

Builds `01_ontology/ontology_brief.json` + `01_ontology/ontology_brief.md`
(contracts §7.1) from an ontology + the run's `analysis_context`-shaped
context. The brief is what the DOE Phase 0 gate (`enforce_gate`) requires and
what the analysis agent must read before writing `01_profile/analysis_plan.md`.

Discipline:
  * deterministic — same (ontology, ctx, context_fp) → same JSON (no wall clock
    in the hashed/compared content; `provenance.build_seconds` is inherited from
    the ontology and may be overwritten by the caller with its own measurement);
  * zero silent column mappings (OD-09) — every declared factor/response lands in
    `column_mapping.matched | inferred | unmatched`, inferred/unmatched carry a
    `reason`, and `coverage.ratio == 1.0` means "nothing silent";
  * no bare `open()` — pathlib only (repo convention), `..` segments rejected.

CLI:  python ontology_brief.py --run-dir DIR --ontology PATH [--context PATH]
      python ontology_brief.py --run-dir DIR --ontology PATH [--context PATH] --json
"""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

BRIEF_CONTRACT_VERSION = "1.0"
PROFILE = "doe"

SIGNALS_OF_INTEREST = ("control_variables", "process_parameters", "inspection_signals")


# ---------------------------------------------------------------- path utils

def _contained(candidate, extra_root=None):
    """normalize → reject traversal segments → (optionally) enforce a root."""
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


def _sha256_file(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sanitize_scene_key(value):
    if value in (None, ""):
        return None
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value))


# ------------------------------------------------------------ ontology views

def _doe_block(ontology):
    block = ontology.get("doe") if isinstance(ontology, dict) else None
    return block if isinstance(block, dict) else {}


def _provenance_block(ontology, ctx):
    """provenance: ontology block > ctx.ontology.provenance > defaults."""
    prov = ontology.get("provenance") if isinstance(ontology, dict) else None
    if isinstance(prov, dict):
        return prov
    ctx_prov = (ctx.get("ontology") or {}).get("provenance") if isinstance(ctx, dict) else None
    return ctx_prov if isinstance(ctx_prov, dict) else {}


def _signals(ontology):
    """Flatten every signal list into {column_or_name: signal} (first wins)."""
    out = {}
    signals = ontology.get("signals") if isinstance(ontology, dict) else None
    if not isinstance(signals, dict):
        return out
    for key in SIGNALS_OF_INTEREST:
        for sig in signals.get(key) or []:
            if not isinstance(sig, dict):
                continue
            for alias in (sig.get("column"), sig.get("name")):
                if alias and alias not in out:
                    out[alias] = sig
    return out


def _doe_declared(ontology, kind):
    """The ontology doe block's own factor/response declarations (col-keyed)."""
    block = _doe_block(ontology)
    out = {}
    for item in block.get(kind) or []:
        if isinstance(item, dict) and (item.get("col") or item.get("name")):
            out[item.get("col") or item.get("name")] = item
    return out


def _confidence_for(signal, declared):
    for src in (signal, declared):
        if isinstance(src, dict):
            conf = src.get("confidence") or src.get("physical_meaning_confidence")
            if conf:
                return str(conf)
    return "UNKNOWN"


def _expected_sign(factor, signal, declared):
    for src in (factor, declared, signal):
        if isinstance(src, dict) and src.get("expected_sign"):
            return str(src["expected_sign"])
    return None


# ------------------------------------------------------------- classification

def _classify(kind, item, ctx, ontology):
    """Classify ONE declared factor/response → (status, reason).

    matched  : a direct column (or ontology_signal) binding exists in the ontology
    inferred : no explicit ontology signal, but the context declares it (semantics
               inferred from the declaration only — always carries a reason)
    unmatched: cannot be bound to a column / absent from the run table — always
               carries a reason (never dropped silently)
    """
    col = item.get("col") or item.get("name")
    if not col:
        return "unmatched", f"{kind} declared without a column name (col/name empty)"
    signals = _signals(ontology)
    declared = _doe_declared(ontology, "factors" if kind == "factor" else "responses")
    sig = signals.get(col) or declared.get(col)
    if sig is None:
        wanted_signal = item.get("ontology_signal")
        if wanted_signal:
            for candidate in signals.values():
                if candidate.get("ontology_signal") == wanted_signal \
                        or candidate.get("name") == wanted_signal:
                    sig = candidate
                    break
    if isinstance(sig, dict):
        bound_col = sig.get("column") or sig.get("name")
        return "matched", f"{kind} '{col}' bound to ontology signal '{sig.get('name') or bound_col}'"
    missing_cols = ctx.get("_missing_columns") if isinstance(ctx, dict) else None
    if isinstance(missing_cols, (list, set)) and col in missing_cols:
        return "unmatched", f"{kind} column '{col}' is not present in the run table"
    return "inferred", (f"{kind} '{col}' declared in analysis_context but absent from the "
                        f"ontology signals — semantics inferred from the declaration "
                        f"(no measured behaviour is claimed)")


def _entry(kind, item, ctx, ontology):
    col = item.get("col") or item.get("name")
    signals = _signals(ontology)
    declared = _doe_declared(ontology, "factors" if kind == "factor" else "responses")
    sig = signals.get(col) or declared.get(col)
    status, reason = _classify(kind, item, ctx, ontology)
    mapped = {
        "name": item.get("name") or col,
        "col": col,
        "type": item.get("type"),
        "unit": item.get("unit"),
        "expected_sign": _expected_sign(item, sig, declared.get(col)),
        "physical_meaning": (
            (item.get("physical_meaning") if isinstance(item, dict) else None)
            or (sig or {}).get("physical_meaning")
            or (declared.get(col) or {}).get("physical_meaning")
        ),
        "ontology_signal": item.get("ontology_signal") or (sig or {}).get("ontology_signal")
        or (sig or {}).get("name"),
        "confidence": _confidence_for(sig, declared.get(col)),
        "mapping_status": status,
        "mapping_reason": reason,
        # extras (additive) — kept small and deterministic
        "role": item.get("role"),
        "min": item.get("min"),
        "max": item.get("max"),
        "levels": item.get("levels"),
        "expected_data_behavior": (sig or {}).get("expected_data_behavior"),
        "observed_data_behavior": (sig or {}).get("observed_data_behavior"),
        "governing_law": (sig or {}).get("governing_law"),
    }
    if kind == "response":
        mapped.update({
            "goal": item.get("goal"),
            "lsl": item.get("lsl"),
            "usl": item.get("usl"),
            "target": item.get("target"),
            "weight": item.get("weight"),
        })
    return mapped


def _relationship_entry(rel):
    return {
        "from": rel.get("from"),
        "to": rel.get("to"),
        "relation": rel.get("type") or rel.get("relation"),
        "mechanism": rel.get("mechanism") or rel.get("governing_equation"),
        "confidence": rel.get("strength") or rel.get("confidence"),
        "evidence_level": rel.get("evidence_level") or ("physics_prior" if rel.get("type") in ("causal", "physical") else "statistical_prior"),
        "expected_sign": rel.get("expected_sign"),
        "predicted_functional_form": rel.get("predicted_functional_form"),
    }


def _dedupe_confounders(ontology, ctx):
    """One entry per confounder: the ontology row wins, context-only covariates
    are appended. The prior builder already materialises declared covariates,
    so a blind concatenation double-listed every one of them."""
    out, seen = [], set()
    for c in ontology.get("confounders") or []:
        if not isinstance(c, dict):
            continue
        var = c.get("variable")
        if not var or var in seen:
            continue
        out.append({"variable": var, "why": c.get("why"),
                    "controlled": c.get("controlled")})
        seen.add(var)
    for var in ctx.get("covariates") or []:
        if var in seen:
            continue
        out.append({"variable": var,
                    "why": "listed in analysis_context.covariates (measured, not controlled)",
                    "controlled": False})
        seen.add(var)
    return out


# ------------------------------------------------------------------- builder

def build_brief(ontology, ctx, *, context_fp=None):
    """Build the ontology brief (contracts §7.1).

    `factors`/`responses` are enumerated from the context declarations (the
    authoritative column list) enriched with ontology semantics; any ontology
    declaration missing from the context is listed in `column_mapping.unmatched`.
    `provenance.build_seconds` is inherited from `ontology.provenance` — a caller
    that measured the real build time (prepare) may overwrite it.
    """
    ontology = ontology if isinstance(ontology, dict) else {}
    ctx = ctx if isinstance(ctx, dict) else {}
    factors_in = [f for f in (ctx.get("factors") or []) if isinstance(f, dict)]
    responses_in = [r for r in (ctx.get("responses") or []) if isinstance(r, dict)]

    factors = [_entry("factor", f, ctx, ontology) for f in factors_in]
    responses = [_entry("response", r, ctx, ontology) for r in responses_in]

    # Ontology-only declarations (declared in the ontology, absent from context)
    ctx_factor_cols = {f.get("col") or f.get("name") for f in factors_in}
    ctx_response_cols = {r.get("col") or r.get("name") for r in responses_in}
    seen = set()
    ontology_extras = []
    for col, item in sorted(_doe_declared(ontology, "factors").items()):
        if col not in ctx_factor_cols and col not in seen:
            seen.add(col)
            ontology_extras.append(("factor", item))
    for col, item in sorted(_doe_declared(ontology, "responses").items()):
        if col not in ctx_response_cols and col not in seen:
            seen.add(col)
            ontology_extras.append(("response", item))

    matched, inferred, unmatched = [], [], []
    for kind, entry in [("factor", e) for e in factors] + [("response", e) for e in responses]:
        row = {
            "kind": kind,
            "col": entry.get("col"),
            "name": entry.get("name"),
            "status": entry.get("mapping_status"),
            "reason": entry.get("mapping_reason"),
        }
        {"matched": matched, "inferred": inferred, "unmatched": unmatched}[row["status"]].append(row)
    for kind, item in ontology_extras:
        unmatched.append({
            "kind": kind,
            "col": item.get("col") or item.get("name"),
            "name": item.get("name") or item.get("col"),
            "status": "unmatched",
            "reason": (f"{kind} '{item.get('col') or item.get('name')}' is declared in the ontology "
                       f"but not in analysis_context — no run-table column to bind"),
        })

    n_factors_declared = len(factors)
    n_responses_declared = len(responses)
    n_factors_matched = sum(1 for e in factors if e["mapping_status"] == "matched")
    n_responses_matched = sum(1 for e in responses if e["mapping_status"] == "matched")
    n_covered = (n_factors_matched + n_responses_matched
                 + sum(1 for e in factors if e["mapping_status"] == "inferred")
                 + sum(1 for e in responses if e["mapping_status"] == "inferred"))
    n_total = n_factors_declared + n_responses_declared

    ont_ctx = ctx.get("ontology") or {}
    data_stage = (ont_ctx.get("data_stage")
                  or ctx.get("data_stage")
                  or _doe_block(ontology).get("data_stage")
                  or "collected")
    scene_key = _sanitize_scene_key(
        ctx.get("ontology", {}).get("scene_key")
        if isinstance(ctx.get("ontology"), dict) else None
    ) or _sanitize_scene_key(ctx.get("experiment_id")) \
        or _sanitize_scene_key((ontology.get("scene") or {}).get("name")) \
        or _sanitize_scene_key(_doe_block(ontology).get("scene_key")) \
        or "doe_scene"

    prov = _provenance_block(ontology, ctx)
    scene = ontology.get("scene") if isinstance(ontology.get("scene"), dict) else {}
    doe = _doe_block(ontology)

    limitations = [str(x) for x in (ontology.get("limitations") or doe.get("limitations") or []) if x]
    if data_stage == "design_only":
        limitations.append(
            "data_stage=design_only: responses are not measured yet — every response behaviour "
            "field is NOT_APPLICABLE and no statistical conclusion may be derived from this brief")

    brief = {
        "contract_version": BRIEF_CONTRACT_VERSION,
        "artifact": "ontology_brief",
        "scene_key": scene_key,
        "profile": PROFILE,
        "data_stage": data_stage,
        "ontology_version": (doe.get("ontology_version") or prov.get("ontology_version")
                             or ontology.get("ontology_version")),
        "ontology_sha256": _sha256_text(json.dumps(ontology, ensure_ascii=False, sort_keys=True)),
        "context_fp": context_fp,
        "scene": {
            "name": scene.get("name") or scene_key,
            "process_type": scene.get("process_type"),
            "production_goal": scene.get("production_goal"),
            "objective": ctx.get("objective"),
            "equipment": scene.get("equipment") or [],
            "stages": scene.get("stages") or [],
            "design_type": (ctx.get("design_type_declared") or doe.get("design_type")
                            or (ctx.get("design_region") or {}).get("design_hull")),
            "design_region": ctx.get("design_region"),
            "experiment_id": ctx.get("experiment_id"),
            "line_id": ctx.get("line_id"),
            "product_id": ctx.get("product_id"),
            "recipe_id": ctx.get("recipe_id"),
        },
        "factors": factors,
        "responses": responses,
        "relationships": [_relationship_entry(r) for r in (ontology.get("relationships") or [])
                          if isinstance(r, dict)],
        "confounders": _dedupe_confounders(ontology, ctx),
        "limitations": limitations,
        "column_mapping": {"matched": matched, "inferred": inferred, "unmatched": unmatched},
        "coverage": {
            # ratio == 1.0 ⟺ nothing silent: every declared factor/response is
            # either directly matched or explicitly inferred with a reason.
            "n_factors_matched": n_factors_matched,
            "n_responses_matched": n_responses_matched,
            "n_factors_covered": n_factors_matched + sum(1 for e in factors if e["mapping_status"] == "inferred"),
            "n_responses_covered": n_responses_matched + sum(1 for e in responses if e["mapping_status"] == "inferred"),
            "n_factors_declared": n_factors_declared,
            "n_responses_declared": n_responses_declared,
            "n_unmatched": len(unmatched),
            "ratio": (n_covered / n_total) if n_total else 1.0,
            "matched_ratio": ((n_factors_matched + n_responses_matched) / n_total) if n_total else 1.0,
        },
        "provenance": {
            "build_mode": prov.get("build_mode") or doe.get("build_mode") or "prior_knowledge",
            "build_seconds": prov.get("build_seconds", 0.0),
            "rag_used": bool(prov.get("rag_used", False)),
            "web_used": bool(prov.get("web_used", False)),
            "physics_prior_used": bool(prov.get("physics_prior_used", True)),
            "engine": prov.get("engine") or doe.get("engine") or "industrial-ontology-builder",
        },
    }
    return brief


# ------------------------------------------------------------------- markdown

def _fmt(value):
    return "—" if value in (None, "", []) else str(value)


def _scene_key_of(brief):
    return brief.get("scene_key") or "doe_scene"


def render_markdown(brief):
    """Human/agent-readable scene + data-model explanation (Chinese narrative)."""
    scene = brief.get("scene") or {}
    cov = brief.get("coverage") or {}
    prov = brief.get("provenance") or {}
    lines = []
    lines.append(f"# 本体简报 · {_scene_key_of(brief)}")
    lines.append("")
    lines.append(f"- 契约版本：{brief.get('contract_version')}（profile={brief.get('profile')}）")
    lines.append(f"- 数据阶段：`{brief.get('data_stage')}`")
    lines.append(f"- 本体版本：{_fmt(brief.get('ontology_version'))}　本体哈希：`{_fmt(brief.get('ontology_sha256'))}`")
    lines.append(f"- 上下文指纹 context_fp：`{_fmt(brief.get('context_fp'))}`")
    lines.append(f"- 工艺类型：{_fmt(scene.get('process_type'))}　产线/实验：{_fmt(scene.get('line_id'))} / {_fmt(scene.get('experiment_id'))}")
    lines.append(f"- 目标：{_fmt(scene.get('production_goal'))}　分析目的：{_fmt(scene.get('objective'))}")
    lines.append(f"- 设计类型：{_fmt(scene.get('design_type'))}")
    lines.append("")

    lines.append("## 1. 场景解释")
    lines.append("")
    if scene.get("stages"):
        for st in scene["stages"]:
            if isinstance(st, dict):
                lines.append(f"- {st.get('sequence', '?')}. {_fmt(st.get('name'))}"
                             f"（{_fmt(st.get('typical_duration'))}）关键物理：{_fmt(st.get('key_physics'))}")
            else:
                lines.append(f"- {st}")
    else:
        lines.append("- （本体未给出工序分解；以列语义与因子/响应表为准）")
    if brief.get("confounders"):
        lines.append("")
        lines.append("**已知混杂/协变量**：")
        for c in brief["confounders"]:
            lines.append(f"- `{_fmt(c.get('variable'))}`：{_fmt(c.get('why'))}"
                         f"（受控={c.get('controlled')}）")
    lines.append("")

    lines.append("## 2. 因子（可控参数）")
    lines.append("")
    lines.append("| 列 | 名称 | 类型 | 单位 | 范围 | 预期方向 | 映射 | 置信 | 物理含义 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for f in brief.get("factors", []):
        rng = f"{_fmt(f.get('min'))} ~ {_fmt(f.get('max'))}"
        lines.append(f"| `{_fmt(f.get('col'))}` | {_fmt(f.get('name'))} | {_fmt(f.get('type'))} | "
                     f"{_fmt(f.get('unit'))} | {rng} | {_fmt(f.get('expected_sign'))} | "
                     f"{_fmt(f.get('mapping_status'))} | {_fmt(f.get('confidence'))} | "
                     f"{_fmt(f.get('physical_meaning'))} |")
    lines.append("")

    lines.append("## 3. 响应（被优化目标）")
    lines.append("")
    lines.append("| 列 | 名称 | 单位 | 目标 | LSL | USL | Target | 映射 | 置信 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in brief.get("responses", []):
        lines.append(f"| `{_fmt(r.get('col'))}` | {_fmt(r.get('name'))} | {_fmt(r.get('unit'))} | "
                     f"{_fmt(r.get('goal'))} | {_fmt(r.get('lsl'))} | {_fmt(r.get('usl'))} | "
                     f"{_fmt(r.get('target'))} | {_fmt(r.get('mapping_status'))} | "
                     f"{_fmt(r.get('confidence'))} |")
    lines.append("")

    lines.append("## 4. 关系（预期机理）")
    lines.append("")
    if brief.get("relationships"):
        for rel in brief["relationships"]:
            lines.append(f"- `{_fmt(rel.get('from'))}` → `{_fmt(rel.get('to'))}`"
                         f"（{_fmt(rel.get('relation'))}，证据={_fmt(rel.get('evidence_level'))}）："
                         f"{_fmt(rel.get('mechanism'))}")
    else:
        lines.append("- （本体未声明显式关系；一致性检查将跳过，不会编造方向）")
    lines.append("")

    lines.append("## 5. 局限")
    lines.append("")
    for lim in brief.get("limitations") or ["（无）"]:
        lines.append(f"- {lim}")
    lines.append("")

    lines.append("## 6. 列映射覆盖（0 静默）")
    lines.append("")
    cm = brief.get("column_mapping") or {}
    lines.append(f"- matched: {len(cm.get('matched', []))}　inferred: {len(cm.get('inferred', []))}　"
                 f"unmatched: {len(cm.get('unmatched', []))}")
    lines.append(f"- coverage.ratio = {cov.get('ratio')}"
                 f"（1.0 = 每个已声明因子/响应都有 matched 或 inferred+reason）")
    for status in ("inferred", "unmatched"):
        for row in cm.get(status, []):
            lines.append(f"- [{status}] {row.get('kind')} `{_fmt(row.get('col'))}`：{_fmt(row.get('reason'))}")
    lines.append("")

    lines.append("## 7. 来源")
    lines.append("")
    lines.append(f"- build_mode={_fmt(prov.get('build_mode'))}　engine={_fmt(prov.get('engine'))}")
    lines.append(f"- rag_used={prov.get('rag_used')}　web_used={prov.get('web_used')}　"
                 f"physics_prior_used={prov.get('physics_prior_used')}")
    lines.append(f"- build_seconds={prov.get('build_seconds')}")
    lines.append("")
    lines.append("> 本简报由确定性脚本生成；Agent 必须阅读本文件后写出 "
                 "`01_profile/analysis_plan.md` 才能进入统计阶段（门禁 "
                 "`ONTOLOGY_BRIEF_REQUIRED` / `ANALYSIS_PLAN_REQUIRED`）。")
    lines.append("")
    return "\n".join(lines)


def write_brief(run_dir, brief):
    """Write `01_ontology/ontology_brief.json` + `.md`; returns (json_path, md_path)."""
    run_dir_v = _contained(run_dir)
    out_dir = run_dir_v / "01_ontology"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = _write_json(out_dir / "ontology_brief.json", brief)
    md_path = out_dir / "ontology_brief.md"
    md_path.write_text(render_markdown(brief), encoding="utf-8")
    return str(json_path), str(md_path)


# ------------------------------------------------------------------------ CLI

def _cli():
    ap = argparse.ArgumentParser(description="Build ontology_brief.json/.md (DOE, contracts §7.1)")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--ontology", required=True, help="ontology.json path")
    ap.add_argument("--context", default=None,
                    help="analysis_context.json path (default: RUN_DIR/00_input/analysis_context.json)")
    ap.add_argument("--context-fp", default=None, help="precomputed context fingerprint")
    ap.add_argument("--json", action="store_true", help="print the brief JSON to stdout")
    args = ap.parse_args()

    run_dir = _contained(args.run_dir)
    ontology = _read_json(args.ontology)
    ctx_path = Path(args.context) if args.context else run_dir / "00_input" / "analysis_context.json"
    ctx = _read_json(ctx_path) if Path(ctx_path).exists() else {}
    brief = build_brief(ontology, ctx, context_fp=args.context_fp)
    json_path, md_path = write_brief(run_dir, brief)
    result = {"json_path": json_path, "md_path": md_path,
              "scene_key": brief["scene_key"],
              "coverage_ratio": brief["coverage"]["ratio"],
              "factors": len(brief["factors"]), "responses": len(brief["responses"])}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
