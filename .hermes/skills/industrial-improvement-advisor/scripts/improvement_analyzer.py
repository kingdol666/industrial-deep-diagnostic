#!/usr/bin/env python
"""improvement_analyzer.py — industrial-improvement-advisor core CLI.

Flow (deterministic; zero LLM):
  Phase 0.5  ontology prepare (profile=improvement; auto unless --ontology-mode off)
  Phase 1    goal resolution (explicit objective.json or deterministic inference)
  Phase 2    evidence legs (dose-response / window contrast / attribution)
  Phase 3    triple-gate assembly -> advisory_actions.json + evidence + charts
             + objective_resolved.json + optimizer_seed.json

Exit codes: 0 actionable & clean | 1 actionable with degradations |
            2 not_actionable (prescriptions only) | 3 input/objective/gate fail

CLI:
  python improvement_analyzer.py analyze --run-dir DIR [--data PATH]
      [--time-col COL] [--doe-run-dir DIR] [--action-log PATH]
      [--objective PATH] [--max-actions N]
      [--ontology PATH] [--ontology-mode auto|full|reuse|extend|off]
      [--scene KEY] [--store-dir DIR]
"""

import argparse
import math
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import imacore  # noqa: E402
from imacore import _io, objective as objective_mod, levers as levers_mod  # noqa: E402
from imacore import evidence, actions, charts, chains  # noqa: E402


def _load_dataframe(run_dir, data_arg, context):
    path = None
    if data_arg:
        path = Path(data_arg)
        if not path.is_absolute():
            path = run_dir / path
    else:
        finder = getattr(_io, "find_data_file", None)
        found = finder(str(run_dir)) if finder else None
        path = Path(found) if found else None
        if path is None:
            fallback = run_dir / "00_input" / "data.csv"
            path = fallback if fallback.is_file() else None
    if path is None or not Path(path).is_file():
        raise SystemExit(f"NO_DATA_FILE: run-dir={run_dir} data={data_arg}")
    if _io.load_table is None:
        raise SystemExit("REUSE_UNAVAILABLE: lstcore._io.load_table 不可用，无法读表")
    df = _io.load_table(str(path))
    return df, Path(path)


def _apply_time(df, preferred):
    if _io.pick_time_col is not None and _io.parse_time is not None:
        try:
            time_col = _io.pick_time_col(df, preferred)
        except Exception:
            time_col = preferred if preferred in df.columns else None
        if time_col:
            try:
                df, resolved = _io.parse_time(df, time_col)
                return df, resolved or time_col
            except Exception:
                return df, time_col
    return df, preferred if preferred in df.columns else None


def _read_context(run_dir):
    path = run_dir / "00_input" / "report_context.json"
    if path.is_file():
        try:
            return _io.read_json(path)
        except (OSError, ValueError):
            return {}
    return {}


def _kpi_windows_from_doe(doe_leg):
    out = {}
    for factor, win in (doe_leg.get("windows") or {}).items():
        response = win.get("response")
        if response:
            out.setdefault(str(response), win.get("range"))
    return out


def _quick_lever_effects(df, lever_cols, kpi_cols, dead_time):
    """{(lever,kpi): {ok,r,p,fdr_q,slope}} for inference/conflict resolution."""
    effects = {}
    for kpi in kpi_cols:
        if kpi not in df.columns:
            continue
        ccf_by_lever = {}
        pairs = {}
        for lever in lever_cols:
            max_lag = int(max(1, math.ceil(dead_time))) if dead_time is not None else 3
            ccf_by_lever[lever] = evidence.peak_ccf(df, lever, kpi, max_lag)
            pairs[lever] = evidence.pair_stats(df, lever, kpi)
        q_map = evidence.fdr_q_for_levers(ccf_by_lever)
        for lever in lever_cols:
            pair = pairs[lever]
            slope = None
            sub = df[[lever, kpi]].dropna()
            if len(sub) > 2 and float(np.ptp(sub[lever].to_numpy())) > 1e-12:
                try:
                    slope = float(np.polyfit(sub[lever].to_numpy(),
                                             sub[kpi].to_numpy(), 1)[0])
                except Exception:
                    slope = None
            q = q_map.get(lever)
            r_ok = abs(pair.get("r") or 0.0) >= _io.CONSTANTS["min_effect_r"]
            effects[(lever, kpi)] = {
                "ok": bool(pair.get("ok") and r_ok
                           and q is not None and q < _io.CONSTANTS["fdr_q"]),
                "r": pair.get("r"), "p": pair.get("p"),
                "fdr_q": q, "slope": slope,
            }
    return effects


def _memory_conflicts(run_dir, levers_like):
    """Strong line-memory consensus (≥3 independent observations) about a lever,
    mapped to the historical move direction ('increase'/'decrease').

    Reads 00_input/context/line_memory.json when present (platform snapshot or
    a user-provided brief payload). Absence is normal, never a degradation.
    actions.build caps/evicts any recommendation that contradicts such a
    consensus (method_notes 处方触发⑤ / memory_conflict_strong).
    """
    path = run_dir / "00_input" / "context" / "line_memory.json"
    if not path.is_file():
        return {}
    try:
        data = _io.read_json(path)
    except (OSError, ValueError):
        return {}
    entries = []
    sources = []
    if isinstance(data, dict):
        sources.append(data)
        if isinstance(data.get("payload"), dict):
            sources.append(data["payload"])
    elif isinstance(data, list):
        entries = data
    for src in sources:
        for key in ("entries", "consensus"):
            if isinstance(src.get(key), list):
                entries = src[key]
                break
        if entries:
            break
    lever_set = {str(x) for x in levers_like}
    direction_map = {"up": "increase", "increase": "increase", "+": "increase",
                     "rising": "increase", "down": "decrease",
                     "decrease": "decrease", "-": "decrease", "falling": "decrease"}
    out = {}
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        if entry.get("grade") != "consensus" or entry.get("stale"):
            continue
        subject = entry.get("subject") or entry.get("signal") or entry.get("param")
        if not subject or str(subject) not in lever_set:
            continue
        for d in entry.get("directions") or []:
            if not isinstance(d, dict):
                continue
            try:
                independent = int(d.get("independent") or 0)
            except (TypeError, ValueError):
                independent = 0
            if independent < 3 or d.get("status") == "refuted":
                continue
            mapped = direction_map.get(str(d.get("direction") or "").lower())
            if mapped:
                out[str(subject)] = mapped
                break
    return out


def _degradations_for(doe_arg, doe_leg, attr_leg, dead_time, ontology_meta):
    degradations = []
    for leg_name, status in _io.REUSE_STATUS.items():
        if status != "ok":
            degradations.append({"leg": f"reuse:{leg_name}", "status": "failed",
                                 "reason": status})
    if doe_arg:
        degradations.append({"leg": "doe_windows", "status": doe_leg.get("status", "failed"),
                             "reason": doe_leg.get("reason", "used")})
    else:
        degradations.append({"leg": "doe_windows", "status": "skipped",
                             "reason": "not requested"})
    attr_status = attr_leg.get("status", "absent")
    # honest mapping to the degradations enum (absent = not requested/supplied)
    if attr_status == "absent":
        attr_status = "skipped"
    degradations.append({"leg": "tuning_memory_attribution",
                         "status": attr_status,
                         "reason": attr_leg.get("reason", "used")})
    if dead_time is None:
        degradations.append({"leg": "temporal_precedence", "status": "not_estimable",
                             "reason": "dead_time 缺省：时间先后条件 not_assessable"
                                       "（禁假设 0 放行），相关动作封顶 B"})
    if ontology_meta and ontology_meta.get("action") == "skipped":
        degradations.append({"leg": "ontology", "status": "skipped",
                             "reason": "ontology mode=off"})
    return degradations


def run_analyze(args):
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"RUN_DIR_NOT_FOUND: {run_dir}")
    context = _read_context(run_dir)
    df, data_path = _load_dataframe(run_dir, args.data, context)
    time_col, resolved_time = _apply_time(df, args.time_col or context.get("time_col"))
    time_col = resolved_time or time_col
    group_col = context.get("group_col")
    if group_col not in df.columns:
        group_col = None

    min_rows = int(getattr(args, "min_rows", 0)
                   or _io.CONSTANTS["min_analysis_rows"])
    if len(df) < min_rows:
        report = _minimal_report(run_dir, data_path, df,
                                 reason=f"n_rows={len(df)} < {min_rows}",
                                 kind="data")
        _write_outputs(run_dir, report, None, {"kpi_series": [], "dose_response": [],
                                               "windows": [], "levers": []})
        return 2

    # ---- Phase 0.5 ontology
    ontology_meta = None
    ontology = {}
    ontology_mode = args.ontology_mode
    ontology_path = run_dir / "01_ontology" / "ontology.json"
    explicit_ont = Path(args.ontology) if args.ontology else None
    if explicit_ont and explicit_ont.is_file():
        ontology = _io.read_json(explicit_ont)
        ontology_meta = {"action": "adopted", "path": str(explicit_ont)}
    elif ontology_mode != "off":
        if not ontology_path.is_file():
            try:
                sys.path.insert(0, str(SCRIPT_DIR))
                import ontology_prepare  # noqa: E402
                prepared = ontology_prepare.prepare(
                    str(run_dir), data=str(data_path), mode=ontology_mode,
                    scene_key=args.scene, store_dir=args.store_dir)
                ontology_meta = prepared
            except SystemExit as exc:
                raise SystemExit(f"ONTOLOGY_PREPARE_FAILED: {exc}")
            except Exception as exc:
                ontology_meta = {"action": "failed", "reason": str(exc)}
        if ontology_path.is_file():
            try:
                ontology = _io.read_json(ontology_path)
            except (OSError, ValueError):
                ontology = {}

    # ---- objective resolution
    objective_path = Path(args.objective) if args.objective else None
    if objective_path and not objective_path.is_absolute():
        objective_path = run_dir / objective_path
    raw_obj = None
    if objective_path and objective_path.is_file():
        try:
            raw_obj = _io.read_json(objective_path)
        except (OSError, ValueError) as exc:
            raise SystemExit(f"OBJECTIVE_INVALID: {objective_path} — {exc}")
    elif objective_path is None:
        raw_obj = objective_mod.load_objective(run_dir)

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    roles = levers_mod.classify(df, time_col, group_col, ontology, raw_obj, context)

    if raw_obj and isinstance(raw_obj, dict) and raw_obj.get("targets"):
        validated = objective_mod.validate_objective(raw_obj, numeric_cols)
        targets = validated["targets"]
        goal_mode = "explicit"
        dead_time = validated.get("dead_time")
        constraints = validated.get("constraints") or []
        if validated.get("levers"):
            roles["levers"] = [c for c in validated["levers"] if c in df.columns]
        inference_rationale = None
        candidates = []
    else:
        dead_time = _dead_time_from(raw_obj)
        constraints = []
        goal_mode = "inferred"
        doe_leg_early = (evidence.load_doe_windows(args.doe_run_dir)
                         if args.doe_run_dir else {"status": "skipped", "windows": {}})
        specs = context.get("spec_limits") or {}
        kpi_windows = _kpi_windows_from_doe(doe_leg_early)
        metadata = {c for c in roles["metadata"] if c} | {c for c in (time_col, group_col) if c}
        kpi_candidates = list(roles["kpis"])
        if not kpi_candidates:
            kpi_candidates = [c for c in numeric_cols if c not in metadata]
        effects = {}
        for kpi in kpi_candidates:
            levers_k = [c for c in numeric_cols if c != kpi and c not in metadata]
            effects.update(_quick_lever_effects(df, levers_k, [kpi], dead_time))
        inferred = objective_mod.infer_targets(df, kpi_candidates, effects,
                                               kpi_windows, specs)
        if not inferred["targets"]:
            report = _minimal_report(run_dir, data_path, df,
                                     reason="no inferable KPI (need spec/window or operable lever)",
                                     kind="data")
            _write_outputs(run_dir, report, None,
                           {"kpi_series": [], "dose_response": [], "windows": [],
                            "levers": roles["levers"]})
            return 2
        targets = inferred["targets"]
        candidates = inferred["candidates"]
        inference_rationale = inferred["rationale"]
        target_metrics = {t["metric"] for t in targets}
        roles["kpis"] = kpi_candidates
        roles["levers"] = [c for c in numeric_cols
                           if c not in target_metrics and c not in metadata]

    # ---- evidence legs
    doe_leg = (evidence.load_doe_windows(args.doe_run_dir)
               if args.doe_run_dir else {"status": "skipped", "windows": {}})
    doe_effects = evidence.load_doe_effects(args.doe_run_dir or run_dir, df)
    target_kpis = [t["metric"] for t in targets]
    data_rel = "00_input/data.csv"
    try:
        rel = data_path.resolve().relative_to(run_dir)
        data_rel = str(rel)
    except ValueError:
        pass
    attr_leg = evidence.attribution_leg(run_dir, data_rel, time_col, target_kpis,
                                        dead_time, args.action_log)

    # conflicts (explicit multi-target or inferred top-2)
    effects = _quick_lever_effects(df, roles["levers"], target_kpis, dead_time)
    conflicts = objective_mod.detect_conflicts(targets, effects)
    conflict_levers = {c["lever"] for c in conflicts}

    degradations = _degradations_for(args.doe_run_dir, doe_leg, attr_leg,
                                     dead_time, ontology_meta)
    limitations = [
        "线性剂量响应假设（分箱中位 OLS 斜率）；非线性/阈值效应需设计试验确认。",
        "观察性结论为相关级；A 级需归因或设计窗的干预性证据。",
    ]
    if goal_mode == "inferred":
        limitations.append("目标为系统推断（偏离度×传导强度×数据充分度），未确认前全建议封顶 B。")
    if dead_time is None:
        limitations.append("dead_time 未提供：时间先后条件未评估，滞后关系可能错配。")

    lever_stats = {lv: levers_mod.variance_stats(df, lv) for lv in roles["levers"]}
    state = {
        "df": df, "run_dir": run_dir, "data_path": data_path,
        "data_rel": data_rel,
        "data_sha256": _sha(data_path),
        "time_col": time_col, "group_col": group_col,
        "roles": roles, "ontology": ontology, "ontology_meta": ontology_meta,
        "targets": targets, "goal_mode": goal_mode,
        "inferred_candidates": candidates,
        "inference_rationale": inference_rationale,
        "dead_time": dead_time, "constraints": constraints,
        "doe_leg": doe_leg, "attr_leg": attr_leg, "doe_effects": doe_effects,
        "degradations": degradations, "limitations": limitations,
        "specs": context.get("spec_limits") or {},
        "windows": _kpi_windows_from_doe(doe_leg),
        "conflicts": conflicts, "conflict_levers": conflict_levers,
        "memory_conflicts": _memory_conflicts(run_dir, roles["levers"]),
    }
    report = actions.build(state)
    report["data"]["n_rows_used"] = int(len(df))
    report["goal"]["inferred_candidates"] = candidates

    seed = actions.build_optimizer_seed(report, lever_stats)
    chart_bundle = charts.build_charts(df, targets,
                                       (report.get("evidence") or {}).get("dose_response"),
                                       (report.get("evidence") or {}).get("window_notes"),
                                       report["data"]["levers"])
    ev_dir = run_dir / "02_evidence"
    _io.write_json(ev_dir / "dose_response.json", {
        "contract_version": "improvement-evidence/1.0",
        "leg": "dose_response",
        "pairs": (report.get("evidence") or {}).get("pairs") or [],
        "dose_leg": (report.get("evidence") or {}).get("dose_response") or [],
        "fdr_alpha": _io.CONSTANTS["fdr_q"],
        "family_rule": "BH family = 每 KPI 内全部 (杠杆×滞后) 检验对",
    })
    _io.write_json(ev_dir / "window_check.json", {
        "contract_version": "improvement-evidence/1.0",
        "leg": "window_contrast",
        "doe_status": doe_leg.get("status"),
        "analysis_mode": doe_leg.get("analysis_mode"),
        "design_type": doe_leg.get("design_type"),
        "windows": list((doe_leg.get("windows") or {}).values()),
        "contrasts": (report.get("evidence") or {}).get("window_contrasts") or [],
    })
    _write_outputs(run_dir, report, seed, chart_bundle,
                   objective_resolved=_objective_resolved(report, candidates,
                                                          inference_rationale))

    # exit code
    if report["status"] == "not_actionable":
        return 2
    degraded = any(d.get("status") in ("failed", "not_estimable")
                   and str(d.get("reason")) not in ("used", "not requested")
                   for d in degradations)
    null_gain = any(a["expected_gain"]["method"] == "none" for a in report["actions"])
    return 1 if (degraded or null_gain) else 0


# ------------------------------------------------------------------ helpers

def _dead_time_from(raw_obj):
    if isinstance(raw_obj, dict):
        dt = raw_obj.get("dead_time")
        if isinstance(dt, (int, float)) and dt >= 0:
            return float(dt)
    return None


def _sha(path):
    if _io.sha256_file is None:
        return "sha256:" + "0" * 64
    try:
        value = str(_io.sha256_file(str(path)))
        return value if value.startswith("sha256:") else "sha256:" + value
    except Exception:
        return "sha256:" + "0" * 64


def _objective_resolved(report, candidates, rationale):
    return {
        "contract_version": "1.0",
        "artifact": "objective_resolved",
        "mode": report["goal"]["mode"],
        "inferred": report["goal"]["mode"] == "inferred",
        "targets": report["goal"]["targets"],
        "candidates": candidates or [],
        "conflicts": report["goal"].get("conflicts") or [],
        "rationale": rationale,
        "note": ("系统推断目标未确认前全部建议封顶 B；用户显式声明目标重跑可解锁 A 级路径"
                 if report["goal"]["mode"] == "inferred" else "显式目标（objective.json）"),
    }


def _write_outputs(run_dir, report, seed, chart_bundle, objective_resolved=None):
    advisory_dir = run_dir / "advisory"
    _io.write_json(advisory_dir / "advisory_actions.json", report)
    if objective_resolved is not None:
        _io.write_json(advisory_dir / "objective_resolved.json", objective_resolved)
    _io.write_json(advisory_dir / "charts.json", chart_bundle)
    if seed is not None:
        _io.write_json(advisory_dir / "optimizer_seed.json", seed)


def _minimal_report(run_dir, data_path, df, reason, kind):
    """Honest not_actionable report skeleton (schema-shaped)."""
    return {
        "contract_version": "improvement-advisory/1.0",
        "report_id": "IMA-0-" + (str(abs(hash(reason))) or "0")[-6:],
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "mode": "advisory",
        "status": "not_actionable",
        "goal": {"mode": "inferred", "targets": [], "conflicts": [],
                 "inferred_rationale": reason},
        "data": {
            "path": str(data_path), "sha256": _sha(data_path),
            "n_rows": int(len(df)), "n_rows_used": int(len(df)),
            "time_col": None, "levers": [], "kpis": [], "sampled": False,
        },
        "waterline": {"max_achievable_grade": "none",
                      "factors": {"attribution_available": False,
                                  "mechanism_edges": 0,
                                  "dead_time_provided": False,
                                  "designed_window_available": False,
                                  "objective_confirmed": False},
                      "note": reason},
        "actions": [],
        "prescriptions": [{"prescription_id": "PRE-GLOBAL-DATA",
                           "kind": kind,
                           "detail": reason,
                           "addresses": []}],
        "excluded_levers": [],
        "degradations": [{"leg": "analysis", "status": "not_estimable",
                          "reason": reason}],
        "provenance": {"authored_by": "imacore",
                       "engine": "industrial-improvement-advisor",
                       "ontology": None,
                       "reuses": [f"{k}: {v}" for k, v in _io.REUSE_STATUS.items()],
                       "data_source": "raw"},
        "limitations": [reason],
        "evidence": {"dose_response": [], "window_notes": []},
    }


def build_parser():
    ap = argparse.ArgumentParser(description="improvement advisory deterministic core")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="run the full advisory analysis")
    a.add_argument("--run-dir", required=True)
    a.add_argument("--data", default=None)
    a.add_argument("--time-col", default=None)
    a.add_argument("--doe-run-dir", default=None)
    a.add_argument("--action-log", default=None)
    a.add_argument("--objective", default=None)
    a.add_argument("--max-actions", type=int, default=None)
    a.add_argument("--min-rows", dest="min_rows", type=int, default=None,
                   help="override the dataset row floor (designed DOE tables are "
                        "legitimately ~20 rows; the relation-level floor still applies)")
    a.add_argument("--ontology", default=None)
    a.add_argument("--ontology-mode", default="auto",
                   choices=["auto", "full", "reuse", "extend", "off"])
    a.add_argument("--scene", default=None)
    a.add_argument("--store-dir", default=None)
    return ap


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    if args.max_actions:
        _io.CONSTANTS["max_actions"] = int(args.max_actions)
    if getattr(args, "min_rows", None):
        _io.CONSTANTS["min_analysis_rows"] = max(12, int(args.min_rows))
    if args.cmd == "analyze":
        return run_analyze(args)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
