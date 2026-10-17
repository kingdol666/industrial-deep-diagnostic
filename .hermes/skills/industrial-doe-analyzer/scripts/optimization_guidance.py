"""Platform optimization handoff (Phase 3 / P3-5, contract §8.3 / OD-11 / XR-03).

`build(run_dir) -> dict`

Reads the completed run's artifacts (`conclusions/recommendations.json`,
`conclusions/next_design.json`, `01_ontology/ontology_brief.json` when present,
`00_input/analysis_context.json`, `00_input/doe_context.json` when present) and
emits `conclusions/optimization_guidance.json`:

    {contract_version, schema_version, run_id, experiment_id,
     ontology_basis{profile, scene_key, version, sha256, reused, brief_ref},
     objective, recipe_patch[], node_setpoints[], constraints,
     next_design{ref, primary_action_id, n_runs}, lineage, provenance}

Two hard rules implemented here:

1. **platform_ref is mandatory** (OD-11): a factor whose `platform_ref` is
   missing (or carries neither `recipe_param` nor `node_id`) is marked in
   `platform_ref_missing[]` and REMOVED from `recipe_patch[]`; a response whose
   `platform_metric_ref.node_id` is missing is removed from `node_setpoints[]`
   the same way. Nothing is silently kept.
2. **`unit_conversion` and `rounding` are applied to the emitted values** and
   `within_limits` is computed against `platform_ref.hard_limits` (platform
   units). A missing `unit_conversion`/`rounding` is disclosed, and a missing
   unit blocks `actionable` (contract §5.2 / DS-06), never the value itself.

Values are never fabricated: the recommended point comes from an actionable
`joint_setpoints[]` entry, else the legacy `setpoints[MULTI]`, else per-factor
window centres — the chosen source is recorded per patch entry and a patch
derived from a non-actionable source carries `actionable=false` with blockers.
"""

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path

CONTRACT_VERSION = "1.0"
SCHEMA_VERSION = "1.0"

BLOCKERS = ("unit_missing", "unit_conflict", "constraint_infeasible", "extrapolation",
            "design_hull_low_confidence", "trend_confounded",
            "non_randomized_confirmation_pending", "no_prediction_interval",
            "no_actionable_setpoint", "platform_ref_incomplete")


# ------------------------------------------------------------------ io helpers

def _read_json(path):
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _num(v):
    try:
        if v is None or isinstance(v, bool):
            return None
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _convert(value, conversion, rounding):
    """Apply platform_ref unit_conversion (scale/offset) then rounding.

    `rounding` semantics: a number is a STEP (round to the nearest multiple —
    `0.1` -> one decimal, `1` -> integer); a dict may say
    `{"mode": "step"|"decimals", "value": n}`. Returns (value, notes).
    """
    notes = []
    v = _num(value)
    if v is None:
        return None, notes
    scale, offset = 1.0, 0.0
    if conversion is None:
        notes.append("unit_conversion 缺省按 1.0 处理（未声明换算）")
    elif isinstance(conversion, dict):
        scale = _num(conversion.get("scale", conversion.get("factor", 1.0))) or 1.0
        offset = _num(conversion.get("offset", 0.0)) or 0.0
    else:
        got = _num(conversion)
        if got is None:
            notes.append(f"unit_conversion={conversion!r} 不可解析，按 1.0 处理")
        else:
            scale = got
    v = v * scale + offset
    if rounding is None:
        notes.append("rounding 未声明：保留换算后的原始值")
        return v, notes
    mode, step, decimals = "step", None, None
    if isinstance(rounding, dict):
        mode = rounding.get("mode") or "step"
        step = _num(rounding.get("value", rounding.get("step")))
        decimals = int(rounding["value"]) if mode == "decimals" and \
            _num(rounding.get("value")) is not None else None
    else:
        step = _num(rounding)
    if mode == "decimals" and decimals is not None:
        return round(v, decimals), notes
    if step is None or step <= 0:
        notes.append(f"rounding={rounding!r} 不可解析：保留换算后的原始值")
        return v, notes
    return round(round(v / step) * step, 10), notes


def _within(value, limits):
    """(bool|None, violations) against {'min':.., 'max':..} (platform units)."""
    if not isinstance(limits, dict) or value is None:
        return None, []
    lo, hi = _num(limits.get("min")), _num(limits.get("max"))
    if lo is None and hi is None:
        return None, []
    bad = []
    if lo is not None and value < lo - 1e-9:
        bad.append({"limit": "min", "value": value, "min": lo})
    if hi is not None and value > hi + 1e-9:
        bad.append({"limit": "max", "value": value, "max": hi})
    return (not bad), bad


# ------------------------------------------------------------------ inputs

def _load(run_dir):
    """All inputs the guidance can read (missing files are None, never fatal)."""
    paths = {
        "recommendations": run_dir / "conclusions" / "recommendations.json",
        "next_design": run_dir / "conclusions" / "next_design.json",
        "ontology_brief": run_dir / "01_ontology" / "ontology_brief.json",
        "analysis_context": run_dir / "00_input" / "analysis_context.json",
        "doe_context": run_dir / "00_input" / "doe_context.json",
        "data_profile": run_dir / "01_profile" / "data_profile.json",
        "run_manifest": run_dir / "run_manifest.json",
    }
    return {k: _read_json(p) for k, p in paths.items()}, paths


def _factor_history(factor, ctx, doe):
    """({unit, platform_ref, source}) for a factor across the two contexts."""
    for src, doc in (("analysis_context.factors", ctx), ("doe_context.factors", doe)):
        for f in (doc or {}).get("factors") or []:
            if not isinstance(f, dict):
                continue
            if str(f.get("col") or f.get("name")) != factor:
                continue
            return {"unit": f.get("unit"),
                    "platform_ref": f.get("platform_ref"),
                    "low": _num(f.get("low", f.get("min"))),
                    "high": _num(f.get("high", f.get("max"))),
                    "source": src}
    return {"unit": None, "platform_ref": None, "low": None, "high": None,
            "source": None}


def _response_history(metric, ctx, doe, brief, recs=None):
    for src, doc in (("analysis_context.responses", ctx), ("doe_context.responses", doe)):
        for r in (doc or {}).get("responses") or []:
            if isinstance(r, dict) and str(r.get("col") or r.get("name")) == metric:
                return _merge_specs({"unit": r.get("unit"),
                                     "platform_metric_ref": r.get("platform_metric_ref"),
                                     "goal": r.get("goal"), "lsl": _num(r.get("lsl")),
                                     "usl": _num(r.get("usl")), "target": _num(r.get("target")),
                                     "source": src}, metric, recs)
    for r in (brief or {}).get("responses") or []:
        if isinstance(r, dict) and str(r.get("col") or r.get("name")) == metric:
            return _merge_specs({"unit": r.get("unit"),
                                 "platform_metric_ref": r.get("platform_metric_ref"),
                                 "goal": r.get("goal"), "lsl": _num(r.get("lsl")),
                                 "usl": _num(r.get("usl")), "target": _num(r.get("target")),
                                 "source": "ontology_brief.responses"}, metric, recs)
    return _merge_specs({"unit": None, "platform_metric_ref": None, "goal": None,
                         "lsl": None, "usl": None, "target": None,
                         "source": None}, metric, recs)


def _merge_specs(hist, metric, recs):
    """Fill missing spec limits from recommendations.response_specs (never overwrite)."""
    spec = _get(recs, "response_specs", metric) if recs else None
    if isinstance(spec, dict):
        for key in ("lsl", "usl", "target"):
            if hist.get(key) is None:
                hist[key] = _num(spec.get(key))
        if hist.get("goal") is None:
            hist["goal"] = spec.get("goal")
    return hist


def _recommended_point(recs):
    """(factors dict, source, actionable, blockers, predicted, window_ids)."""
    for sp in (recs or {}).get("joint_setpoints") or []:
        if not isinstance(sp, dict):
            continue
        if sp.get("actionable") is True and isinstance(sp.get("factors"), dict) \
                and sp["factors"]:
            return (dict(sp["factors"]), f"joint_setpoints[{sp.get('id')}]", True,
                    list(sp.get("blockers") or []), dict(sp.get("predicted") or {}),
                    list(sp.get("window_ids") or []))
    for sp in (recs or {}).get("setpoints") or []:
        if isinstance(sp, dict) and sp.get("factor") == "MULTI":
            raw = ((sp.get("expected_response") or {}).get("raw")) or {}
            if raw:
                conf = sp.get("confidence")
                blockers = [] if conf in ("high", "medium") else ["no_actionable_setpoint"]
                return (dict(raw), "setpoints[MULTI] (legacy)",
                        conf in ("high", "medium"), blockers, {}, [])
    centres, ids = {}, []
    for w in (recs or {}).get("operating_windows") or []:
        if not isinstance(w, dict):
            continue
        rng = w.get("range")
        f = w.get("factor")
        if not f or not isinstance(rng, (list, tuple)) or len(rng) != 2:
            continue
        lo, hi = _num(rng[0]), _num(rng[1])
        if lo is None or hi is None:
            continue
        role = w.get("window_role")
        if role is not None and role != "marginal_diagnostic" and w.get("actionable") is not True:
            continue
        centres.setdefault(str(f), (lo + hi) / 2.0)
        ids.append(w.get("id"))
    if centres:
        blockers = ["no_actionable_setpoint"]
        for w in (recs or {}).get("operating_windows") or []:
            blockers.extend(w.get("actionable_blockers") or [])
        return (centres, "operating_windows midpoints (marginal_diagnostic)",
                False, sorted(set(blockers)), {}, [i for i in ids if i])
    return {}, None, False, ["no_actionable_setpoint"], {}, []


def _predicted_for(metric, predicted, recs):
    """Predicted response value at the recommended point (never fabricated)."""
    entry = (predicted or {}).get(metric)
    if isinstance(entry, dict):
        for key in ("mean", "median"):
            v = _num(entry.get(key))
            if v is not None:
                return v, "joint_setpoints[].predicted.mean"
    for w in (recs or {}).get("operating_windows") or []:
        if isinstance(w, dict) and str(w.get("response")) == metric:
            v = _num(_get(w, "predicted_at_center", "mean"))
            if v is not None:
                return v, "operating_windows[].predicted_at_center.mean"
    for key, label in (("current", "response_specs[].current"), ("target", "response_specs[].target")):
        v = _num(_get(recs, "response_specs", metric, key))
        if v is not None:
            return v, label
    return None, None


# ------------------------------------------------------------------ build

def build(run_dir):
    """Build the platform optimization guidance for a completed run (contract §8.3)."""
    run_dir = Path(run_dir).resolve()
    docs, paths = _load(run_dir)
    recs = docs["recommendations"] or {}
    next_design = docs["next_design"] or {}
    ctx = docs["analysis_context"] or {}
    doe = docs["doe_context"] or {}
    brief = docs["ontology_brief"] or {}
    manifest = docs["run_manifest"] or {}
    notes = []

    run_id = (doe.get("run_id") or ctx.get("run_id") or manifest.get("run_id")
              or run_dir.name)
    experiment_id = (doe.get("experiment_id") or ctx.get("experiment_id")
                     or manifest.get("experiment_id"))

    # ---- ontology basis -------------------------------------------------
    if brief:
        basis = {
            "profile": brief.get("profile"),
            "scene_key": brief.get("scene_key") or _get(ctx, "ontology", "scene_key"),
            "version": brief.get("ontology_version"),
            "sha256": brief.get("ontology_sha256"),
            "reused": (_get(brief, "provenance", "build_mode") == "reused"),
            "brief_ref": "01_ontology/ontology_brief.json",
        }
        if basis["reused"] is None:
            notes.append("ontology_brief.provenance.build_mode 缺失：reused 记为 null")
    else:
        basis = {
            "profile": _get(ctx, "ontology", "profile") or "doe",
            "scene_key": _get(ctx, "ontology", "scene_key"),
            "version": _get(ctx, "ontology", "version"),
            "sha256": None, "reused": None, "brief_ref": None,
        }
        notes.append("ontology_brief.json 缺失：ontology_basis 仅含 analysis_context 字段")

    objective = (doe.get("objective") or ctx.get("objective")
                 or doe.get("experiment_objective") or ctx.get("experiment_objective"))
    if objective is None:
        notes.append("objective 未在 doe_context/analysis_context 中声明")

    point, point_source, actionable, blockers, predicted, window_ids = _recommended_point(recs)
    if point_source is None:
        notes.append("recommendations.json 没有可用的推荐点：recipe_patch 为空（不编造数值）")
    if not actionable and point:
        notes.append(f"推荐点来自非 actionable 来源（{point_source}）：patch 条目 "
                     f"actionable=false 并披露 blockers")

    # ---- recipe_patch (platform_ref mandatory, OD-11) --------------------
    recipe_patch, missing, constraint_echo = [], [], []
    for c in ctx.get("constraints") or doe.get("constraints") or []:
        if isinstance(c, dict) and c.get("factor"):
            constraint_echo.append({"factor": c.get("factor"), "type": c.get("type"),
                                    "min": _num(c.get("min")), "max": _num(c.get("max")),
                                    "hard": bool(c.get("hard", True)),
                                    "source": c.get("source")})
    for factor in sorted(point):
        target_raw = _num(point[factor])
        hist = _factor_history(factor, ctx, doe)
        pref = hist["platform_ref"] if isinstance(hist["platform_ref"], dict) else None
        usable = bool(pref and (pref.get("recipe_param") or pref.get("node_id")))
        if not usable:
            missing.append({"kind": "recipe_patch", "factor": factor, "value": target_raw,
                            "unit": hist["unit"],
                            "reason": "platform_ref_missing" if pref is None
                                      else "platform_ref_unusable",
                            "platform_ref": pref})
            notes.append(f"因子 {factor} 缺少可用 platform_ref：已从 recipe_patch 移除（OD-11）")
            continue
        conversion = pref.get("unit_conversion")
        rounding = pref.get("rounding")
        to_v, conv_notes = _convert(target_raw, conversion, rounding)
        from_raw = _num(_get(recs, "current_baseline", "point", factor))
        if from_raw is None:
            from_raw = _num(_get(ctx, "current_setpoint", factor))
        if from_raw is None:
            from_raw = _num(_get(doe, "current_setpoint", factor))
        from_v = None
        if from_raw is not None:
            from_v, _ = _convert(from_raw, conversion, rounding)
        else:
            notes.append(f"因子 {factor} 无当前值（current_baseline/current_setpoint 均缺失）："
                         f"from=null")
        limits = pref.get("hard_limits") if isinstance(pref.get("hard_limits"), dict) else None
        in_limits, violations = _within(to_v, limits)
        if limits is None:
            notes.append(f"因子 {factor} 未声明 platform_ref.hard_limits：within_limits=null")
        unit = hist["unit"]
        entry_blockers = list(blockers)
        if not unit:
            entry_blockers.append("unit_missing")
            notes.append(f"因子 {factor} 单位缺失：actionable=false（DS-06）")
        if in_limits is False:
            entry_blockers.append("constraint_infeasible")
        entry = {
            "factor": factor,
            "from": from_v,
            "to": to_v,
            "unit": unit,
            "platform_ref": {
                "recipe_param": pref.get("recipe_param"),
                "node_id": pref.get("node_id"),
                "plc_tag": pref.get("plc_tag"),
                "unit_conversion": conversion if conversion is not None else 1.0,
                "rounding": rounding,
            },
            "hard_limits": limits,
            "within_limits": in_limits,
            "actionable": bool(actionable and not entry_blockers),
            "actionable_blockers": sorted(set(entry_blockers)),
            "source": point_source,
            "window_ids": window_ids,
            "value_analysis_units": target_raw,
            "unit_conversion_notes": conv_notes,
            "limit_violations": violations,
            "unit_status": "valid" if unit else "missing",
        }
        recipe_patch.append(entry)

    # ---- node_setpoints --------------------------------------------------
    node_setpoints = []
    metrics = []
    for r in ctx.get("responses") or doe.get("responses") or []:
        if isinstance(r, dict) and (r.get("col") or r.get("name")):
            metrics.append(str(r.get("col") or r.get("name")))
    for m in (brief.get("responses") or []):
        if isinstance(m, dict) and (m.get("col") or m.get("name")):
            metrics.append(str(m.get("col") or m.get("name")))
    for metric in sorted(set(metrics)):
        hist = _response_history(metric, ctx, doe, brief, recs)
        pmr = hist["platform_metric_ref"] if isinstance(hist["platform_metric_ref"], dict) else None
        value, v_source = _predicted_for(metric, predicted, recs)
        if not (pmr and pmr.get("node_id")):
            missing.append({"kind": "node_setpoint", "metric": metric, "value": value,
                            "unit": hist["unit"],
                            "reason": "platform_ref_missing" if pmr is None
                                      else "platform_ref_unusable",
                            "platform_ref": pmr})
            notes.append(f"响应 {metric} 缺少 platform_metric_ref.node_id：已从 node_setpoints "
                         f"移除（OD-11）")
            continue
        if value is None:
            notes.append(f"响应 {metric} 无可用的预测/现值：node_setpoints 跳过该指标")
            continue
        node_setpoints.append({
            "node_id": pmr.get("node_id"),
            "metric": metric,
            "value": value,
            "unit": hist["unit"],
            "aggregation": pmr.get("aggregation"),
            "value_source": v_source,
            "response_goal": hist["goal"],
            "spec_limits": {"lsl": hist["lsl"], "usl": hist["usl"],
                            "target": hist["target"]},
        })

    # ---- next design + lineage ------------------------------------------
    nd_primary = next_design.get("primary_action_id")
    nd_action = next_design.get("recommended_action")
    nd_runs = None
    for act in next_design.get("actions") or []:
        if act.get("id") == nd_primary:
            nd_runs = act.get("n_runs")
            break
    if next_design and nd_runs is None:
        notes.append("next_design 中未找到 primary_action_id 对应的动作：n_runs=null")
    if not next_design:
        notes.append("next_design.json 缺失：next_design 块为指针+null（Phase 2 产物）")

    round_v = _num(ctx.get("round") if ctx.get("round") is not None else doe.get("round"))
    if round_v is None:
        round_v = _num(_get(doe, "optimization", "round"))
    lineage = {
        "parent_run_id": (ctx.get("parent_run_id") or doe.get("parent_run_id")
                          or manifest.get("parent_run_id")),
        "round": int(round_v) if round_v is not None and float(round_v).is_integer()
                 else round_v,
        "campaign_id": (ctx.get("campaign_id") or doe.get("campaign_id")
                        or _get(doe, "optimization", "campaign_id")),
    }
    if all(v is None for v in lineage.values()):
        notes.append("lineage 全部为 null（doe_context/analysis_context 未带 parent_run_id/"
                     "round/campaign_id）")

    inputs = []
    for key, p in sorted(paths.items()):
        if p.is_file():
            inputs.append({"key": key, "path": p.relative_to(run_dir).as_posix(),
                           "sha256": _sha256(p), "bytes": p.stat().st_size})

    out = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "run_id": run_id,
        "experiment_id": experiment_id,
        "ontology_basis": basis,
        "objective": objective,
        "recipe_patch": recipe_patch,
        "node_setpoints": node_setpoints,
        "constraints": constraint_echo,
        "next_design": {
            "ref": "conclusions/next_design.json" if paths["next_design"].is_file() else None,
            "primary_action_id": nd_primary,
            "recommended_action": nd_action,
            "n_runs": nd_runs,
        },
        "lineage": lineage,
        "provenance": {
            "authored_by": "script",
            "script_version": CONTRACT_VERSION,
            "recommended_point_source": point_source,
            "actionable": actionable,
            "actionable_blockers": sorted(set(blockers)),
            "inputs": inputs,
            "notes": notes,
        },
        "platform_ref_missing": missing,
        "value_semantics": ("recipe_patch.to 已应用 platform_ref.unit_conversion 与 rounding"
                            "（平台单位）；value_analysis_units 为分析单位原值；"
                            "within_limits 依据 platform_ref.hard_limits 计算"),
    }
    return out


# ------------------------------------------------------------------ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="Platform optimization handoff (P3-5)")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=None,
                    help="default: <run-dir>/conclusions/optimization_guidance.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    payload = build(run_dir)
    out = Path(args.out) if args.out else run_dir / "conclusions" / "optimization_guidance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[optimization_guidance] patch={len(payload['recipe_patch'])} "
          f"node_setpoints={len(payload['node_setpoints'])} "
          f"platform_ref_missing={len(payload['platform_ref_missing'])} -> {out}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
