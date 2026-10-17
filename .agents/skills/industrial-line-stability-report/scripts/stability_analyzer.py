#!/usr/bin/env python3
"""industrial-line-stability-report — deterministic stability analyzer.

Ontology-first (house rule): condition understanding is built BEFORE any
statistics — from an explicit ontology, the run's ontology-builder artifacts,
or the ontology asset store; fields the ontology does not cover fall back to
deterministic heuristics, every field carrying assigned_by provenance.

Usage:
  stability_analyzer.py analyze --run-dir R [--context C] [--out-dir D]
                                [--data PATH] [--time-col T] [--metric M]
                                [--baseline B] [--action-log A]
                                [--doe-run-dir D] [--attribution-json J]
                                [--ontology O] [--scene S]

Reuse (single source of truth, no reinvented wheels):
  - Nelson SPC episodes + robust z ....... industrial-sentinel sentinelcore
  - regime/change-point segmentation ..... industrial-sentinel regime_map (C3)
  - operating windows .................... industrial-doe-analyzer recommendations
  - action attribution ................... industrial-tuning-memory tune_stats

Exit codes: 0 ok | 1 report with findings | 2 not_assessable | 3 input error.
All numbers deterministic (numpy/scipy/pandas); zero LLM, zero network.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lstcore import __version__ as SCRIPT_VERSION  # noqa: E402
from lstcore import charts, drivers, findings, ontology, profile, score, subject as _subject  # noqa: E402
from lstcore import _io, regime, spc_adapter  # noqa: E402

REPORT_CONTRACT = "line-stability-report/1.0"
CHARTS_CONTRACT = "line-stability-charts/1.0"
MIN_ROWS = score.MIN_ROWS
MAX_PARAMS = 60
SAMPLE_MAX_ROWS = ontology.MAX_SAMPLE_ROWS if hasattr(ontology, "MAX_SAMPLE_ROWS") else 100_000


def _load_context(path: str | None, run_dir: str | None) -> dict:
    candidates = []
    if path:
        candidates.append(path)
    if run_dir:
        candidates.append(os.path.join(run_dir, "00_input", "report_context.json"))
        candidates.append(os.path.join(run_dir, "report_context.json"))
    for cand in candidates:
        if cand and os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def _resolve_data(args, context: dict) -> str:
    for cand in (args.data, context.get("data_path")):
        if cand and os.path.isfile(cand):
            return cand
    if args.run_dir:
        found = _io.find_data_file(args.run_dir)
        if found:
            return found
    raise ValueError("no data file found (pass --data, --run-dir with 00_input/, "
                     "or data_path in report_context.json)")


def _run_tuning_memory(args, work_dir: str) -> str | None:
    """Best-effort: build a minimal tuning-memory run layout and attribute."""
    tm_scripts = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "industrial-tuning-memory", "scripts"))
    tune_stats = os.path.join(tm_scripts, "tune_stats.py")
    if not os.path.isfile(tune_stats) or not args.run_dir:
        return None
    tm_run = os.path.join(work_dir, "tm_run")
    os.makedirs(os.path.join(tm_run, "00_input"), exist_ok=True)
    import shutil
    shutil.copyfile(args.data, os.path.join(tm_run, "00_input", "data.csv"))
    shutil.copyfile(args.action_log, os.path.join(tm_run, "00_input", "action_log.json"))
    cmd = [sys.executable, tune_stats, "attribute", "--run-dir", tm_run,
           "--data", "00_input/data.csv", "--action-log", "00_input/action_log.json",
           "--time-col", args.time_col or "t"]
    if args.metric:
        cmd += ["--metric", args.metric]
    try:
        subprocess.run(cmd, capture_output=True, timeout=180, check=False)
    except Exception:
        return None
    hits = sorted(glob.glob(os.path.join(tm_run, "06_experience", "attribution", "*.json")))
    return hits[0] if hits else None


def _run_doe_observational(args, work_dir: str) -> str | None:
    """Optional deep leg: run industrial-doe-analyzer observational analysis in
    a nested run dir; returns the doe run dir on success."""
    if not args.data:
        return None
    doe_scripts = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "industrial-doe-analyzer", "scripts"))
    analyze_py = os.path.join(doe_scripts, "analyze.py")
    if not os.path.isfile(analyze_py):
        return None
    doe_run = os.path.join(work_dir, "doe_auto_run")
    os.makedirs(os.path.join(doe_run, "00_input"), exist_ok=True)
    import shutil
    shutil.copyfile(args.data, os.path.join(doe_run, "00_input", "data.csv"))
    cmd = [sys.executable, analyze_py, "run", "--run-dir", doe_run]
    if args.time_col:
        cmd += ["--time-col", args.time_col]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=600, check=False)
    except Exception:
        return None
    ok = os.path.isfile(os.path.join(doe_run, "conclusions", "recommendations.json")) \
        or os.path.isfile(os.path.join(doe_run, "02_analysis", "correlation_report.json"))
    return doe_run if (proc.returncode == 0 and ok) else None


def _merge_attribution(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        att = json.load(f)
    reports = att.get("reports") or [att]
    estimable, statuses = [], {}
    for rep in reports if isinstance(reports, list) else []:
        status = rep.get("attribution_status") or rep.get("status")
        statuses[status] = statuses.get(status, 0) + 1
        if status == "estimable":
            effect = rep.get("effect") or {}
            estimable.append({
                "action_id": rep.get("action_id") or rep.get("action_log_id"),
                "parameter": (rep.get("action") or {}).get("parameter")
                             or rep.get("parameter"),
                "to": (rep.get("action") or {}).get("to") if isinstance(rep.get("action"), dict) else None,
                "delta_metric": effect.get("delta") if isinstance(effect, dict) else None,
                "direction": ("improved" if isinstance(effect, dict) and
                              ((effect.get("delta") or 0) * (1 if effect.get("higher_is_better", True) else -1)) > 0
                              else "degraded"),
                "status": "estimable",
                "derived": True,
            })
    return {"used": True, "source": os.path.basename(path),
            "n_actions": sum(statuses.values()) or len(reports),
            "status_counts": statuses, "estimable": estimable}


def _merge_doe(doe_run_dir: str, params: list[dict]) -> dict:
    out = {"used": False, "reason": None, "operating_windows": [], "violations": [],
           "confirmations": [], "joint_setpoints": [], "correlation_report": None}
    rec_path = os.path.join(doe_run_dir, "conclusions", "recommendations.json")
    corr_path = os.path.join(doe_run_dir, "02_analysis", "correlation_report.json")
    if not os.path.isfile(rec_path):
        out["reason"] = "conclusions/recommendations.json not found"
        return out
    with open(rec_path, "r", encoding="utf-8") as f:
        rec = json.load(f)
    medians = {p["name"]: p["median"] for p in params}
    out["used"] = True
    # v1.1 windows: factor + range + window_role/actionable; legacy v1.0 used
    # parameter + low/high. Accept both — a contract upgrade must not silently
    # turn every window into a null and every violation into "none".
    for w in (rec.get("operating_windows") or []):
        rng = w.get("range") if isinstance(w.get("range"), list) else None
        low = rng[0] if rng and len(rng) == 2 else w.get("low")
        high = rng[1] if rng and len(rng) == 2 else w.get("high")
        entry = {"parameter": w.get("factor") or w.get("parameter") or w.get("name"),
                 "low": low, "high": high,
                 "confidence": w.get("confidence"),
                 "window_id": w.get("id"),
                 "response": w.get("response"),
                 "window_role": w.get("window_role"),
                 "actionable": w.get("actionable")}
        out["operating_windows"].append(entry)
        med = medians.get(entry["parameter"])
        if med is not None and entry["low"] is not None and entry["high"] is not None \
                and not (entry["low"] <= med <= entry["high"]):
            out["violations"].append({**entry, "median": med, "derived": True})
    out["joint_setpoints"] = [j for j in (rec.get("joint_setpoints") or [])
                              if isinstance(j, dict)][:5]
    for c in (rec.get("confirmations") or [])[:10]:
        out["confirmations"].append({
            "parameter": c.get("parameter") or c.get("factor"),
            "note": c.get("note") or c.get("text") or c.get("status")})
    if os.path.isfile(corr_path):
        try:
            with open(corr_path, encoding="utf-8") as f:
                out["correlation_report"] = json.load(f)
        except Exception:
            out["correlation_report"] = None
    return out


def _build_limitations(prof: dict, roles: dict, understanding: dict,
                       sampled: bool, stride: int, params: list[dict],
                       max_lag: int) -> dict:
    """Data-truth mandate: explicit assumptions, limitations and confounders."""
    spec_sources = {
        "user": [p["name"] for p in params if (p["spec"] or {}).get("source") == "user"],
        "ontology": [p["name"] for p in params if (p["spec"] or {}).get("source") == "ontology"],
        "none": [p["name"] for p in params if not (p["spec"] or {}).get("source")],
    }
    return {
        "data_source": "raw (this skill never cleans or imputes; every number is recomputable from the raw table)",
        "sampling": {"n_rows_analyzed": prof["n_rows_used"], "sampled": sampled,
                     "stride": stride,
                     "note": "systematic stride sampling (>100k rows)" if sampled else None},
        "missing_rate": prof["missing_rate"],
        "sampling_interval_seconds": prof.get("sampling_interval_median_seconds"),
        "spec_coverage": spec_sources,
        "model_assumptions": [
            f"lag-compensated Spearman window 0–{max_lag} rows (lead/lag beyond this window is invisible)",
            "whole-period scoring assumes one dominant operating condition; use the regime table for segmented reading",
            "Cpk treats within-sigma as MR̄/1.128 moving-range estimate",
        ],
        "confounders": understanding.get("confounders") or [],
        "derived_fields": ["baseline_ref.robust_z", "correlations.contributions.share",
                           "correlations.pairs.best_abs_r"],
    }


def analyze(args) -> tuple[dict, dict, int]:
    context = _load_context(args.context, args.run_dir)
    data_path = _resolve_data(args, context)
    time_col = args.time_col or context.get("time_col") or None

    # ── Phase 0 本体优先：先理解工况，再碰统计 ─────────────────────────────
    ont = ontology.discover_ontology(args.run_dir,
                                     args.ontology or context.get("ontology_path"),
                                     args.scene or context.get("scene") or context.get("line_id"),
                                     _repo_root())
    df_raw = _io.load_table(data_path)
    time_col_resolved = _io.pick_time_col(df_raw, time_col)
    df, _mode = _io.parse_time(df_raw, time_col_resolved)
    df, requested = _io.slice_period(df, context.get("start"), context.get("end"))
    if context.get("group_col") and context.get("group_filter"):
        df = df[df[context["group_col"]] == context["group_filter"]].reset_index(drop=True)
        if df.empty:
            raise ValueError(f"group_filter '{context['group_filter']}' matched no rows")

    n_rows_full = len(df)
    stride = ontology.systematic_sample(n_rows_full, SAMPLE_MAX_ROWS)
    sampled = stride > 1
    if sampled:
        df = df.iloc[::stride].reset_index(drop=True)

    roles = _io.infer_roles(df, time_col_resolved, context)
    understanding = ontology.build_understanding(ont["ontology"],
                                                 roles["parameter_cols"], context)
    # ontology/user condition understanding overrides heuristic roles
    inspection_cols = list(roles["inspection_cols"])
    for col, doc in understanding["columns"].items():
        if doc["role"] == "inspection" and col in roles["parameter_cols"] \
                and col not in inspection_cols:
            inspection_cols.append(col)
    roles["inspection_cols"] = inspection_cols

    prof = profile.profile_period(df, roles, n_rows_full)
    interval = prof["sampling_interval_median_seconds"]
    # Degenerate-channel guard: a channel that never changes over the period
    # (frozen snapshot export / dead sensor) carries zero stability information.
    # Scoring it would fabricate a perfect grade, so it never enters `parameters`.
    all_numeric = list(roles["parameter_cols"])
    invariant_cols = list((prof.get("time_invariant_channels") or {}).get("examples") or [])
    if (prof.get("time_invariant_channels") or {}).get("count", 0) > len(invariant_cols):
        # examples list is capped; recompute the full list for the split below
        invariant_cols = [c for c in all_numeric
                          if pd.to_numeric(df[c], errors="coerce").dropna().nunique() < 2]
    varying_cols = [c for c in all_numeric if c not in invariant_cols]
    degradation = []
    if invariant_cols:
        degradation.append({
            "check": "time_invariant_channels",
            "reason": (f"{len(invariant_cols)}/{len(all_numeric)} numeric channels never change "
                       f"across the period (frozen snapshot export or dead/unused points); "
                       f"excluded from scoring"),
        })
    # assessment order: inspection/response signals first so the MAX_PARAMS cap
    # can never crowd the business-critical quality columns out of the report
    insp_set = set(roles["inspection_cols"])
    ordered_varying = ([c for c in varying_cols if c in insp_set]
                       + [c for c in varying_cols if c not in insp_set])
    param_cols = ordered_varying[:MAX_PARAMS]
    if len(varying_cols) > MAX_PARAMS:
        degradation.append({"check": "parameter_columns",
                            "reason": f"more than {MAX_PARAMS} varying numeric columns; "
                                      f"assessed the first {MAX_PARAMS} in file order"})
    if sampled:
        degradation.append({"check": "row_sampling",
                            "reason": f"{n_rows_full} rows systematically sampled with "
                                      f"stride {stride} (cap {SAMPLE_MAX_ROWS})"})

    # spec limits: user context wins, ontology normal_range is the fallback
    spec_map = context.get("spec_limits") or {}
    ontology_specs = {col: doc["spec"] for col, doc in understanding["columns"].items()
                      if doc.get("spec") and doc["spec"].get("source") == ontology.ONTOLOGY}

    def spec_for(col: str) -> dict:
        if col in spec_map:
            return {**spec_map[col], "source": "user"}
        if col in ontology_specs:
            return dict(ontology_specs[col])
        return {}

    weights = context.get("weights") or None
    weights_source = "user" if weights else "equal"
    if not weights:
        # Adaptive default: quality/inspection signals (user-declared or
        # ontology-typed) carry double weight — the composite then reflects
        # what the scenario actually cares about, not just channel count.
        role_weights = {col: 2.0 for col, doc in understanding["columns"].items()
                        if doc.get("role") == "inspection"}
        if role_weights:
            weights = role_weights
            weights_source = "role_weights"

    # Subject/scenario resolution — drives adaptive narrative (产线/系统/对象)
    subj = _subject.resolve_subject(context, understanding)

    # ── per-parameter stability (SPC via sentinelcore reuse) ──────────────
    baseline_refs = {}
    if args.baseline and os.path.isfile(args.baseline):
        try:
            baseline_refs = _baseline_reference(df, param_cols, args.baseline)
        except Exception as exc:
            degradation.append({"check": "sentinel_baseline", "reason": f"unreadable: {exc}"})
    elif args.baseline:
        degradation.append({"check": "sentinel_baseline", "reason": "file not found"})

    parameters = []
    for col in param_cols:
        x = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        clean = x[~np.isnan(x)]
        if len(clean) < 10:
            degradation.append({"check": f"param:{col}",
                                "reason": f"only {len(clean)} usable values; skipped"})
            continue
        mu = float(np.mean(clean))
        med = float(np.median(clean))
        sigma_overall = float(np.std(clean, ddof=1))
        sigma_within = spc_adapter.sigma_within_mr(clean) or sigma_overall
        episodes = spc_adapter.evaluate_episodes(clean, med, sigma_within)
        nelson: dict[str, dict] = {}
        for ep in episodes:
            rule = ep["rule_name"]
            bucket = nelson.setdefault(rule, {"n_episodes": 0, "indices": []})
            bucket["n_episodes"] += 1
            if len(bucket["indices"]) < 200:
                bucket["indices"].append(int(ep["index"]))
        n_vp = len(episodes)
        spec = spec_for(col)
        lsl, usl = spec.get("lsl"), spec.get("usl")
        cap = _capability(clean, lsl, usl)
        dr = _drift(clean, interval)
        doc = understanding["columns"].get(col, {})
        entry = {
            "name": col,
            "role": "inspection" if col in roles["inspection_cols"] else "parameter",
            "condition": {k: doc.get(k) for k in
                          ("label", "unit", "assigned_by", "governing_law",
                           "physical_meaning", "group", "stage", "equipment")},
            "n": int(len(clean)),
            "row_range": [0, int(len(clean) - 1)],
            "data_source": "raw",
            "mu": round(mu, 6), "median": round(med, 6),
            "sigma": round(sigma_overall, 6),
            "sigma_within_mr": round(sigma_within, 6) if sigma_within else None,
            "cv": round(float(np.std(clean) / abs(mu)), 6) if mu else None,
            "min": round(float(np.min(clean)), 6), "max": round(float(np.max(clean)), 6),
            "spec": {"lsl": lsl, "usl": usl, "target": spec.get("target"),
                     "source": spec.get("source")},
            "capability": cap,
            "nelson": nelson,
            "n_violation_points": n_vp,
            "drift": dr,
            "baseline_ref": baseline_refs.get(col),
        }
        entry.update(score.parameter_score(entry))
        parameters.append(entry)

    status = "ok"
    if prof["n_rows_used"] < MIN_ROWS or not parameters:
        status = "not_assessable"

    max_lag = drivers.DEFAULT_MAX_LAG
    corr = {"max_lag": max_lag, "pairs": [], "contributions": []}
    if status == "ok" and len(param_cols) >= 2:
        try:
            corr["pairs"] = drivers.pair_analysis(df, param_cols)
            # contributions need a declared target: guessing one (e.g. the first
            # column in file order) would attribute variance to an arbitrary,
            # uninterpretable variable — honest skip instead.
            targets = list(roles["inspection_cols"])
            if targets:
                corr["contributions"] = drivers.contribution_analysis(df, param_cols, targets)
            else:
                corr["contributions"] = []
                corr["contributions_skipped"] = (
                    "未声明检测/响应指标（inspection_cols 或本体 role=response），"
                    "贡献分析未执行——默认目标列不可解释")
        except Exception as exc:
            degradation.append({"check": "correlations", "reason": str(exc)})

    # ── working-condition segmentation (sentinel C3 reuse) ────────────────
    regimes_res = regime.detect_regimes(df, param_cols) if status == "ok" else {
        "available": False, "method": "not_assessable", "change_points": [],
        "regimes": [], "abnormal_ratio": None}

    condition = {
        "ontology": {"mode": understanding["mode"], "path": ont["path"],
                     "source": ont["source"], "reason": ont["reason"]},
        "scene": understanding["scene"],
        "columns": understanding["columns"],
        "relationships": understanding["relationships"],
        "regimes": regimes_res,
    }

    # Pure-snapshot input (every channel time-invariant): the only truthful
    # information left is the single instant itself. Expose ontology-documented
    # channels as an explicit snapshot table (instant values, NOT period stats)
    # so the report still says what the line was doing at export time — while
    # the verdict stays not_assessable.
    inv_prof = prof.get("time_invariant_channels") or {}
    if inv_prof.get("total") and inv_prof.get("count") == inv_prof.get("total"):
        snap = []
        for col, doc in understanding["columns"].items():
            if doc.get("assigned_by") != ontology.ONTOLOGY:
                continue
            v = pd.to_numeric(df[col], errors="coerce").dropna()
            if v.empty:
                continue
            snap.append({
                "column": col, "label": doc.get("label") or col,
                "unit": doc.get("unit"), "stage": doc.get("stage"),
                "value": round(float(v.iloc[0]), 6),
                "governing_law": doc.get("governing_law"),
            })
            if len(snap) >= 40:
                break
        condition["snapshot"] = snap

    integrations = {"sentinel_baseline": {"used": bool(baseline_refs),
                                          "path": args.baseline if baseline_refs else None},
                    "tuning_memory": {"used": False},
                    "doe_analyzer": {"used": False}}
    if args.action_log and args.run_dir and status == "ok":
        att_path = args.attribution_json or _run_tuning_memory(args, args.out_dir or ".")
        if att_path and os.path.isfile(att_path):
            try:
                integrations["tuning_memory"] = _merge_attribution(att_path)
            except Exception as exc:
                degradation.append({"check": "tuning_memory", "reason": str(exc)})
        else:
            integrations["tuning_memory"] = {
                "used": False, "reason": "attribution unavailable (tuning-memory "
                                         "scripts or estimation window)"}
    elif args.action_log and not args.run_dir:
        degradation.append({"check": "tuning_memory",
                            "reason": "--action-log requires --run-dir layout"})

    doe_run = args.doe_run_dir
    if args.doe_auto and status == "ok" and not doe_run:
        doe_run = _run_doe_observational(args, args.out_dir or ".")
        if not doe_run:
            degradation.append({"check": "doe_auto",
                                "reason": "industrial-doe-analyzer observational run "
                                          "did not produce artifacts"})
    if doe_run and status == "ok":
        try:
            integrations["doe_analyzer"] = _merge_doe(doe_run, parameters)
        except Exception as exc:
            degradation.append({"check": "doe_analyzer", "reason": str(exc)})

    report = {
        "contract_version": REPORT_CONTRACT,
        "report_id": "LSR-{ts}-{rand}".format(ts=int(time.time()),
                                              rand="".join(random.choices(
                                                  "abcdefghijklmnopqrstuvwxyz0123456789", k=6))),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "line": {"line_id": context.get("line_id"), "product": context.get("product")},
        "period": {
            "start": str(df["_dt"].iloc[0]) if len(df) else None,
            "end": str(df["_dt"].iloc[-1]) if len(df) else None,
            "requested": requested,
        },
        "data": {
            "path": data_path, "sha256": _io.sha256_file(data_path),
            "time_col": roles["time_col"], "group_col": roles["group_col"],
            "group_used": context.get("group_filter"),
            "parameter_cols": param_cols, "inspection_cols": roles["inspection_cols"],
            "ignored_cols": roles["ignored_cols"],
            "sampled": sampled, "stride": stride,
            **prof,
            # data traceability: carry the upstream preprocessing provenance
            # (raw export → tidy table) into the report verbatim
            **({"preprocessing": context["preprocessing"]}
               if context.get("preprocessing") is not None else {}),
        },
        "condition": condition,
        "parameters": parameters,
        "correlations": corr,
        "integrations": integrations,
        "degradations": degradation,
        "limitations": _build_limitations(prof, roles, understanding, sampled,
                                          stride, parameters, max_lag),
        "subject": subj,
        **({"objective": context["objective"]}
           if context.get("objective") else {}),
        "provenance": {
            "input_sha256": _io.sha256_file(data_path),
            "script_version": SCRIPT_VERSION,
            "authored_by": "lstcore/stability_analyzer.py",
            "zero_llm": True,
            "spc_source": spc_adapter.source_name(),
            "regime_method": regimes_res.get("method"),
            "ontology_source": ont["source"],
            "weights_source": weights_source,
            "python": sys.version.split()[0],
            "numpy": np.__version__, "pandas": pd.__version__,
            "methods": ["sentinelcore_nelson_episodes", "mrbar_sigma_1.128",
                        "cpk_within_ppk_overall", "theil_sen_mk_drift",
                        "lagged_spearman_max10", "contribution_r2_share",
                        "regime_segmentation_c3", "ontology_first_condition",
                        "weighted_penalty_score_v1", "data_truth_limitations"],
        },
    }

    if status == "ok":
        comp = score.composite(parameters, weights)
        grade, grade_key, label = score.grade_for(comp)
        report["findings"] = findings.generate(report)
        sev_counts = {"info": 0, "warn": 0, "high": 0, "critical": 0}
        for f in report["findings"]:
            sev_counts[f["severity"]] += 1
        top = [p["name"] for p in parameters if p["score"] < 70][:3]
        stmt = (f"{_subject.sentence_subject(subj['noun'])}在本时段总体运行{label}"
                f"（{comp} 分，{grade} 级）：评估 "
                f"{len(parameters)} 个参数，检出 {sum(p['n_violation_points'] for p in parameters)} 个 "
                f"SPC 违规剧集、{sum(1 for p in parameters if (p.get('drift') or {}).get('significant'))} 项显著漂移"
                + (f"；工况分段检出 {len(regimes_res.get('change_points', []))} 个显著变点"
                   if regimes_res.get("change_points") else "")
                + (f"；最需关注：{'、'.join(top)}" if top else "") + "。")
        report["conclusion"] = {
            "score": comp, "grade": grade, "grade_key": grade_key, "label": label,
            "statement": stmt,
            "n_parameters_assessed": len(parameters),
            "n_findings": len(report["findings"]),
            "findings_by_severity": sev_counts,
        }
        exit_code = 1 if report["findings"] else 0
    else:
        reasons = []
        if prof["n_rows_used"] < MIN_ROWS:
            reasons.append(f"时段内仅 {prof['n_rows_used']} 行（最少 {MIN_ROWS} 行）")
        if not parameters:
            inv = prof.get("time_invariant_channels") or {}
            if inv.get("count") and inv.get("total") and inv["count"] == inv["total"]:
                reasons.append(
                    f"全部 {inv['total']} 个数值通道在整个时段取值完全不变"
                    "（疑似单时刻快照导出或死点），没有任何历史波动可评估")
            else:
                reasons.append("无可评估的数值参数列")
        report["findings"] = []
        snapshot_block = any("快照" in r for r in reasons)
        advice = ("该文件疑似只固化了一个时刻的实时值：请从 DCS/历史站导出逐时刻的存档"
                  "历史值（每时刻一行、数值随时间变化）后重试。"
                  if snapshot_block else
                  "请补足时段数据或放宽时间过滤后重试。")
        report["conclusion"] = {
            "score": None, "grade": None, "grade_key": "not_assessable",
            "label": "无法评估",
            "statement": f"数据不足以产出稳定性结论：{'；'.join(reasons)}。{advice}",
            "n_parameters_assessed": len(parameters),
            "n_findings": 0,
            "findings_by_severity": {"info": 0, "warn": 0, "high": 0, "critical": 0},
        }
        exit_code = 2

    chart_bundle = charts.build_charts(report, df, roles) if parameters else {
        "contract_version": CHARTS_CONTRACT, "trend": [], "score_bars": [],
        "corr_heatmap": {"labels": [], "matrix": []}, "contribution_bar": []}
    return report, chart_bundle, exit_code


def _repo_root() -> str | None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, "..", "..", ".."))
    return root if os.path.isdir(os.path.join(root, "data", "ontology_store")) else None


def _baseline_reference(df: pd.DataFrame, param_cols: list[str],
                        baseline_path: str) -> dict:
    """sentinel watch_baseline.json → per-parameter robust z (sentinelcore.robust)."""
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    groups = baseline.get("groups") or {}
    grp = groups.get("__ALL__") or (next(iter(groups.values())) if groups else None)
    if not grp:
        return {}
    params = grp.get("parameters") or {}
    refs = {}
    for name, spec in params.items():
        if name not in param_cols:
            continue
        x = pd.to_numeric(df[name], errors="coerce").dropna()
        if x.empty:
            continue
        b_med, b_mad = spec.get("median"), spec.get("mad")
        if b_med is None or not b_mad:
            continue
        rz = spc_adapter.robust_z_value(x.to_numpy(dtype=float), b_med, b_mad)
        if rz is None:
            continue
        refs[name] = {
            "baseline_median": b_med, "baseline_mad": b_mad,
            "baseline_cv": spec.get("cv"), "robust_z": round(rz, 4),
            "deviation": ("none" if abs(rz) <= 3.5
                          else "low" if abs(rz) <= 6.7 else "high"),
            "derived": True,
        }
    return refs


def _capability(clean, lsl, usl):
    from lstcore import stability
    return stability.capability(np.asarray(clean, dtype=float), lsl, usl)


def _drift(clean, interval):
    from lstcore import stability
    return stability.drift(np.asarray(clean, dtype=float), interval)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="stability_analyzer.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--run-dir", default=None)
    a.add_argument("--data", default=None)
    a.add_argument("--context", default=None)
    a.add_argument("--out-dir", default=None)
    a.add_argument("--time-col", default=None)
    a.add_argument("--metric", default=None)
    a.add_argument("--baseline", default=None)
    a.add_argument("--action-log", default=None)
    a.add_argument("--doe-run-dir", default=None)
    a.add_argument("--attribution-json", default=None)
    a.add_argument("--ontology", default=None,
                   help="ontology.json path (else run_dir artifacts, else asset store)")
    a.add_argument("--scene", default=None,
                   help="scene key for ontology asset store lookup")
    a.add_argument("--doe-auto", action="store_true",
                   help="run industrial-doe-analyzer observational analysis when no "
                        "--doe-run-dir is given (deep leg)")
    args = ap.parse_args(argv)

    try:
        report, chart_bundle, code = analyze(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[line-stability] input error: {exc}", file=sys.stderr)
        return 3

    out_dir = args.out_dir or (os.path.join(args.run_dir, "line_report")
                               if args.run_dir else "line_report")
    os.makedirs(out_dir, exist_ok=True)
    rep_path = os.path.join(out_dir, "stability_report.json")
    chart_path = os.path.join(out_dir, "charts.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(chart_path, "w", encoding="utf-8") as f:
        json.dump(chart_bundle, f, ensure_ascii=False, indent=2)

    c = report["conclusion"]
    print(f"[line-stability] {report['status']} score={c['score']} grade={c['grade']} "
          f"params={c['n_parameters_assessed']} findings={c['n_findings']} "
          f"ontology={report['condition']['ontology']['mode']}")
    print(f"[line-stability] wrote {rep_path}")
    return code


if __name__ == "__main__":
    sys.exit(main())
