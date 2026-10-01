#!/usr/bin/env python
"""analyze.py — the single deterministic entry of industrial-doe-analyzer.

Subcommands:
  profile  --run-dir RUN_DIR [--data PATH]     Phase 0+1: manifest, context, profile, design detect
  run      --run-dir RUN_DIR                   Phase 2(+3/4 baseline): all statistics + artifacts
  report   --run-dir RUN_DIR                   Phase R: render report.html from the 9 artifacts
  all      --run-dir RUN_DIR [--data PATH]     profile + run + report (headless mode)

Everything is numpy/scipy/pandas-deterministic; zero LLM. The gate
(quality_gate.mjs) validates the artifacts afterwards — this script never
self-declares success beyond writing what it computed.

File-IO discipline: every path passes through `_contained()` (normpath +
traversal-segment rejection + repo-root prefix whitelist) and all reads/writes
use pathlib methods — there is no raw open() in this module.
"""

import argparse
import datetime
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parents[2]
REPO_ROOT_NORM = os.path.normpath(os.path.abspath(str(REPO_ROOT)))
IDP_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "industrial-data-processor" / "scripts"
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"

sys.path.insert(0, str(SCRIPT_DIR))

from doestats import VERSION  # noqa: E402
from doestats import correlation as corr_mod  # noqa: E402
from doestats import design_detect  # noqa: E402
from doestats import effects_anova  # noqa: E402
from doestats import figures as figs_mod  # noqa: E402
from doestats import rsm as rsm_mod  # noqa: E402
from doestats import stability as stab_mod  # noqa: E402
from doestats import windows as wins_mod  # noqa: E402
from doestats._stats_util import sha256_file  # noqa: E402
from conclusion_template import build as build_conclusion  # noqa: E402

RESPONSE_HINTS = re.compile(
    r"(^(y|y\d|quality|target|result|yield|response)$)|"
    r"(强度|合格|能耗|纯度|良率|产量|粘度|水分|质量|结果|目标)", re.IGNORECASE)
ID_HINTS = re.compile(r"(^id$|_id$|^no$|_no$|编号|序号|^index$)", re.IGNORECASE)
# P0-6: word-boundary time names — "Runtime (s)" must NOT hit ("time" is preceded
# by a letter), while "timestamp"/"datetime" still match as whole tokens
# (alternation order + the (?![a-z]) lookahead keep their inner parts from
# double-triggering). Chinese keywords match as substrings by design.
TIME_HINTS = re.compile(
    r"(?<![a-z])(?:timestamp|datetime|time|date|时刻|时间|日期)(?![a-z])", re.IGNORECASE)
TIME_PARSE_SAMPLE = 200
TIME_PARSE_MIN_RATE = 0.8
DATA_SUFFIXES = (".csv", ".xlsx", ".xls", ".parquet", ".feather", ".json", ".tsv")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _contained(candidate, extra_root=None):
    """Return `candidate` normalized as a Path, enforcing containment inline:
    normpath -> reject any traversal segment -> repo-root prefix whitelist."""
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    roots = [REPO_ROOT_NORM]
    if extra_root is not None:
        roots.append(os.path.normpath(os.path.abspath(str(extra_root))))
    for root in roots:
        if cand == root or cand.startswith(root + os.sep):
            return Path(cand)
    raise ValueError(f"path outside allowed roots: {candidate}")


def _json_clean(v):
    """Deterministically replace non-finite floats with null (strict-JSON safe).

    Pure structural rewrite — no randomness; finite payloads pass through
    byte-identical. numpy floating scalars included via np.floating.
    """
    if isinstance(v, dict):
        return {k: _json_clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_clean(x) for x in v]
    if isinstance(v, (float, np.floating)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    return v


def _write_json(path, payload):
    out = _contained(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    clean = _json_clean(payload)
    # allow_nan=False: if a non-finite value ever survives cleaning, fail loudly
    # here instead of writing an Infinity/NaN file that breaks Node downstream.
    out.write_text(json.dumps(clean, ensure_ascii=False, indent=2, default=float,
                              allow_nan=False),
                   encoding="utf-8")


def _read_json(path):
    return json.loads(_contained(path).read_text(encoding="utf-8"))


def _load_df(run_dir, data_path):
    safe = _contained(data_path, run_dir)
    sys.path.insert(0, str(IDP_SCRIPTS))
    from file_inspect import load_file  # reused loader (multi-format)
    return load_file(str(safe))


def _numeric_cols(df):
    cols = []
    for c in df.columns:
        coerced = pd.to_numeric(df[c], errors="coerce")
        if coerced.notna().mean() > 0.7:
            cols.append(c)
    return cols


def _time_parse_rate(values):
    """Share of sampled non-null values that parse as plausible datetimes.

    Plausibility window (1950-2100) guards against dateutil artifacts: numeric
    strings like "1,534.6" DO parse (as year 1534) but are not observation dates.
    """
    sample = [v for v in values if v is not None and str(v).strip() != ""]
    if not sample:
        return 0.0
    s = pd.Series(sample[:TIME_PARSE_SAMPLE]).astype(str)
    parsed = pd.to_datetime(s, errors="coerce")
    if not parsed.notna().any():
        return 0.0
    return float(parsed.dt.year.between(1950, 2100).sum()) / float(len(parsed))


def _unix_ts_share(vals):
    """Share of numeric values in plausible Unix-timestamp ranges (s or ms)."""
    v = pd.to_numeric(pd.Series(vals), errors="coerce").dropna()
    if v.empty:
        return 0.0
    as_s = v.between(1e8, 4.1e9)       # ~1973..2100 in seconds
    as_ms = v.between(1e11, 4.1e12)    # ~2001..2100 in milliseconds
    return float((as_s | as_ms).mean())


def _detect_time_column(df, numeric):
    """P0-6: time-column inference behind two gates.

    A name hit alone is never enough: numeric-dtype columns must look like Unix
    timestamps (s/ms), string columns must parse (>=0.8 success on a <=200-row
    sample). The shared detect_time_column fallback (substring-based, weaker)
    is subjected to the same gates before adoption. Returns (time_col, notes);
    every acceptance AND rejection reason lands in the notes for data_profile.
    """
    notes = []
    for c in df.columns:
        if not TIME_HINTS.search(str(c)):
            continue
        if c in numeric:
            share = _unix_ts_share(df[c])
            if share >= TIME_PARSE_MIN_RATE:
                notes.append(f"time_col: '{c}' accepted (name hit + Unix-timestamp-like "
                             f"numeric values, share={share:.2f})")
                return c, notes
            notes.append(f"time_col: '{c}' rejected (name hit but numeric dtype without "
                         f"Unix-timestamp-like values, share={share:.2f}) — not a time axis")
            continue
        rate = _time_parse_rate(df[c].dropna().tolist())
        if rate >= TIME_PARSE_MIN_RATE:
            notes.append(f"time_col: '{c}' accepted (name hit + parseable values, "
                         f"rate={rate:.2f})")
            return c, notes
        notes.append(f"time_col: '{c}' rejected (name hit but parse rate {rate:.2f} < "
                     f"{TIME_PARSE_MIN_RATE}) — not a time axis")
    try:
        sys.path.insert(0, str(IDP_SCRIPTS))
        from file_inspect import detect_time_column
        fb = detect_time_column(df)
    except Exception:
        fb = None
    if fb is None or fb not in df.columns:
        return None, notes
    if fb in numeric:
        share = _unix_ts_share(df[fb])
        if share >= TIME_PARSE_MIN_RATE:
            notes.append(f"time_col: '{fb}' accepted via content fallback "
                         f"(Unix-timestamp-like numeric values, share={share:.2f})")
            return fb, notes
        notes.append(f"time_col: '{fb}' rejected (content fallback: numeric dtype without "
                     f"Unix-timestamp-like values) — not a time axis")
        return None, notes
    rate = _time_parse_rate(df[fb].dropna().tolist())
    if rate >= TIME_PARSE_MIN_RATE:
        notes.append(f"time_col: '{fb}' accepted via content fallback (parse rate={rate:.2f})")
        return fb, notes
    notes.append(f"time_col: '{fb}' rejected (content fallback: parse rate {rate:.2f} < "
                 f"{TIME_PARSE_MIN_RATE}) — not a time axis")
    return None, notes


def _default_context(run_dir, data_path, df):
    numeric = _numeric_cols(df)
    cols = list(df.columns)
    time_col, time_notes = _detect_time_column(df, numeric)
    id_like = [c for c in cols if ID_HINTS.search(str(c))
               or (df[c].nunique() >= 0.98 * len(df) and c not in numeric)]
    response_candidates = [c for c in numeric if RESPONSE_HINTS.search(str(c))]
    if not response_candidates:
        response_candidates = numeric[-1:]
    responses = response_candidates[:3]
    factors = [c for c in numeric if c not in responses and c != time_col
               and not ID_HINTS.search(str(c))]
    factor_types = {c: ("categorical" if df[c].nunique() <= 12 else "numeric")
                    for c in factors}
    low_card_obj = [c for c in cols if c not in numeric and df[c].nunique() <= 12
                    and c != time_col and c not in id_like]
    return {
        "data_path": str(_contained(data_path, run_dir)),
        "mode_override": None,
        "responses": [{"col": c, "goal": None, "lsl": None, "usl": None,
                       "target": None, "weight": None} for c in responses],
        "factors": [{"col": c, "type": factor_types.get(c)} for c in factors]
        + [{"col": c, "type": "categorical"} for c in low_card_obj],
        "blocks": [], "covariates": [], "index_cols": id_like,
        "time_col": time_col, "group_col": None, "run_order_col": None,
        "max_lag": 20, "alpha": 0.05, "effect_size_threshold": 0.01,
        "constraints": [],
        "inference": {"assigned_by": "auto",
                      "notes": ["analysis_context.json was absent — fields auto-inferred; "
                                "review responses/factors before trusting windows"]
                               + time_notes},
    }


def _run_manifest(run_dir):
    return {"run_id": Path(run_dir).name, "scene": "doe_condition_analysis",
            "created_at": now(), "skill": "industrial-doe-analyzer",
            "script_version": VERSION, "steps": []}


def _find_data(run_dir, data_path):
    run_dir_v = _contained(run_dir)
    if data_path:
        return _contained(data_path, run_dir_v)
    in_dir = run_dir_v / "00_input"
    for p in sorted(in_dir.iterdir()):
        if p.suffix.lower() in DATA_SUFFIXES and p.name != "analysis_context.json":
            return _contained(p, run_dir_v)
    raise FileNotFoundError(f"no data file under {in_dir}")


# ------------------------------------------------------------------ profile

def cmd_profile(run_dir, data_path=None, context_path=None):
    run_dir_v = _contained(run_dir)
    (run_dir_v / "00_input").mkdir(parents=True, exist_ok=True)
    _write_json(run_dir_v / "run_manifest.json", _run_manifest(run_dir_v))
    data_file = _find_data(run_dir_v, data_path)
    df = _load_df(run_dir_v, data_file)
    if len(df) < 5 or df.shape[1] < 2:
        raise SystemExit(f"INSUFFICIENT_DATA: only {len(df)} rows x {df.shape[1]} cols "
                         f"in {data_file.name} — need >=5 rows and >=2 columns")
    if not _numeric_cols(df):
        raise SystemExit(f"NO_NUMERIC_COLUMNS: {data_file.name} has no usable numeric "
                         f"column — analysis aborted")

    ctx_path = Path(context_path) if context_path else \
        run_dir_v / "00_input" / "analysis_context.json"
    if ctx_path.exists():
        ctx = _read_json(ctx_path)
        ctx.setdefault("inference", {})["assigned_by"] = "user"
    else:
        ctx = _default_context(run_dir_v, data_file, df)
        _write_json(ctx_path, ctx)

    factor_cols = [f["col"] for f in ctx.get("factors", []) if f["col"] in df.columns]
    response_cols = [r["col"] for r in ctx.get("responses", []) if r["col"] in df.columns]
    if not response_cols:
        auto = _default_context(run_dir_v, data_file, df)
        response_cols = [r["col"] for r in auto["responses"]]
        ctx["responses"] = auto["responses"]

    design = design_detect.detect_design(df, factor_cols, ctx.get("time_col"))
    if ctx.get("mode_override") in ("designed", "observational"):
        design["mode"] = ctx["mode_override"]
        design["mode_overridden"] = True
        design["detection_notes"].append(
            f"mode overridden by user context to {ctx['mode_override']} "
            "(the evidence grade is NOT overridden)")

    # P0-6: surface the auto time-column decision (and every rejection reason)
    # in the profile, next to the design detection notes
    for note in (ctx.get("inference") or {}).get("notes", []):
        if isinstance(note, str) and note.startswith("time_col:"):
            design.setdefault("detection_notes", []).append(note)

    numeric = set(_numeric_cols(df))
    columns_block, caveats = [], []
    roles = {"responses": response_cols,
             "factors": factor_cols,
             "blocks": [b for b in ctx.get("blocks", []) if b in df.columns],
             "covariates": [c for c in ctx.get("covariates", []) if c in df.columns],
             "index": [c for c in ctx.get("index_cols", []) if c in df.columns],
             "ignore": []}
    for c in df.columns:
        role = "ignore"
        if c in response_cols:
            role = "response"
        elif c in factor_cols:
            role = "factor"
        elif c in roles["blocks"]:
            role = "block"
        elif c in roles["covariates"]:
            role = "covariate"
        elif c in roles["index"] or c == ctx.get("time_col"):
            role = "index"
        n_unique = int(df[c].nunique())
        n_missing = int(df[c].isna().sum())
        columns_block.append({
            "name": c, "dtype": str(df[c].dtype), "role": role,
            "role_assigned_by": "user" if ctx.get("inference", {}).get("assigned_by") == "user"
            else "auto",
            "n_unique": n_unique, "n_missing": n_missing,
            "n_valid": int(len(df) - n_missing),
            "notes": ""})
        if role == "ignore" and c not in roles["index"] and c != ctx.get("time_col"):
            roles["ignore"].append(c)

    # randomization check (C8): factor-vs-run-order association
    order_col = ctx.get("run_order_col") or ctx.get("time_col")
    if order_col and order_col in df.columns and design["mode"] == "designed":
        from scipy import stats as sps
        order = pd.to_numeric(df[order_col], errors="coerce")
        for f in factor_cols:
            if f not in numeric:
                continue
            m = order.notna()
            if m.sum() < 20:
                continue
            rho = sps.spearmanr(pd.to_numeric(df.loc[m, f], errors="coerce").fillna(0),
                                order[m]).statistic
            if rho is not None and abs(rho) > 0.5:
                caveats.append({
                    "code": "NON_RANDOMIZED",
                    "message": f"因子 {f} 与运行顺序的 Spearman ρ={rho:.2f} — 未随机化，"
                               f"效应与时序混杂，证据等级降级并强制确认试验",
                    "severity": "warn", "evidence": {"spearman_rho": round(float(rho), 4)}})
    constant = [c for c in factor_cols if df[c].nunique() <= 1]
    if constant:
        caveats.append({"code": "ZERO_VARIANCE_FACTORS",
                        "message": f"零方差因子: {constant}", "severity": "warn"})
    # P0-5: honest extra-SS semantics disclosure — on unbalanced (non-orthogonal)
    # designs the single-deletion extra-SS is Type-III-style (coding-dependent),
    # only orthogonal designs carry classical Type-II semantics. Applies to
    # factorial-structure effect tables only: CCD/BBD/LHS replicate centers and
    # axials by design, so unequal combo counts there are intentional, not
    # "unbalanced". Note the detection dict may lack `balanced` (observational
    # fallthrough returns a fresh dict), so recompute the combo-count balance
    # for the disclosure.
    if design.get("mode") == "designed" and \
            design.get("design_type") not in ("rsm_ccd", "rsm_bbd", "latin_hypercube"):
        balanced_flag = design.get("balanced")
        if balanced_flag is None and factor_cols:
            sub_bal = df[factor_cols].dropna()
            if len(sub_bal):
                counts = sub_bal[factor_cols].astype(str).apply(
                    lambda r: tuple(r), axis=1).value_counts()
                balanced_flag = bool(counts.min() == counts.max())
        if balanced_flag is False:
            caveats.append({
                "code": "UNBALANCED_DESIGN",
                "message": "设计不平衡：effect_table 采用 extra-SS ANOVA 语义"
                           "（正交设计下等价经典 Type-II；不平衡时为偏差编码下的单删法 extra-SS，"
                           "p 值依赖编码方式）",
                "severity": "warn",
                "evidence": {"balanced": False,
                             "balance_ratio": design.get("balance_ratio")}})
    dup_rows = int(df.duplicated().sum())
    high_missing = [c["name"] for c in columns_block if (c["n_missing"] or 0) > 0.3 * len(df)]
    if high_missing:
        caveats.append({"code": "HIGH_MISSING",
                        "message": f"缺失率>30% 的列: {high_missing}", "severity": "warn"})

    profile = {
        "generated_at": now(),
        "data_path": str(data_file),
        "n_rows": int(len(df)), "n_cols": int(df.shape[1]),
        "columns": columns_block, "roles": roles,
        "design": design,
        "quality": {"duplicate_rows": dup_rows, "constant_cols": constant,
                    "high_missing_cols": high_missing,
                    "rows_dropped_missing_targets": 0},
        "caveats": caveats,
    }
    _write_json(run_dir_v / "01_profile" / "data_profile.json", profile)
    ctx["_predictor_cols"] = factor_cols
    _write_json(ctx_path, ctx)
    print(f"[profile] rows={len(df)} cols={df.shape[1]} "
          f"mode={design['mode']} design={design['design_type']} "
          f"responses={response_cols} factors={len(factor_cols)}")
    return profile, ctx, df


# ------------------------------------------------------------------ run

def cmd_run(run_dir):
    run_dir_v = _contained(run_dir)
    ctx_path = run_dir_v / "00_input" / "analysis_context.json"
    ctx = _read_json(ctx_path)
    profile = _read_json(run_dir_v / "01_profile" / "data_profile.json")
    data_file = _contained(profile["data_path"], run_dir_v)
    df = _load_df(run_dir_v, data_file)
    mode = profile["design"]["mode"]
    sha = sha256_file(data_file)
    fig_dir = run_dir_v / "03_figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    if mode == "designed":
        artifacts = _run_designed(run_dir_v, ctx, profile, df, fig_dir)
    else:
        artifacts = _run_observational(run_dir_v, ctx, profile, df, fig_dir)

    recommendations = wins_mod.assemble(
        mode, artifacts["windows"], artifacts["interactions"],
        artifacts["confirmations"], artifacts["watchlist"], artifacts.get("setpoints", []),
        ctx, df, profile, artifacts.get("stability"), sha, VERSION,
        ctx.get("seed"))
    _write_json(run_dir_v / "conclusions" / "recommendations.json", recommendations)

    plot_manifest = {"generated_at": now(), "mode": mode,
                     "plots": artifacts["plots"]}
    if not artifacts["plots"]:
        # P0-4: an empty manifest is legal (tiny/degenerate data) — disclose the
        # downgrade instead of failing the schema gate on minItems
        plot_manifest["notes"] = (
            "0 figures produced: data too small or not plottable — figure gate "
            "passes vacuously; treat all conclusions as numbers-only evidence")
    _write_json(fig_dir / "plot_manifest.json", plot_manifest)

    conclusion = build_conclusion(profile, artifacts.get("effect_table"),
                                  artifacts.get("correlation"),
                                  artifacts.get("stability"),
                                  recommendations, plot_manifest,
                                  models=artifacts.get("models_json"))
    _write_json(run_dir_v / "conclusions" / "doe_conclusion.json", conclusion)

    print(f"[run] mode={mode} windows={len(recommendations['operating_windows'])} "
          f"confirmations={len(recommendations['confirmations'])} "
          f"plots={len(artifacts['plots'])}")
    print(f"[contract] v{recommendations['contract_version']} | "
          f"grade={conclusion['evidence_grade']} | authored_by=script")
    print("[downstream-usage-card] " + json.dumps(
        conclusion["downstream_usage_card"], ensure_ascii=False))
    return 0


def _apply_alias_downgrade(fam, design):
    """Dangerous-alias rule (plan §2.5): a kept effect whose design alias chain
    contains another effect of the SAME OR LOWER order is not causally quotable
    -> estimable:false, p/q null, reason_code "aliased", excluded from the BH
    family (family recomputed without it)."""
    chains = design.get("alias_chains") or {}
    changed = False
    for t in fam["tests"]:
        if not t.get("estimable"):
            continue
        letters = t["term"].replace(":", "")
        chain = chains.get(letters) or []
        order = len(letters)
        if any(len(a) <= order for a in chain):
            t["estimable"] = False
            t["reason_code"] = "aliased"
            t["p_value"] = None
            t["q_value_bh"] = None
            t["f_stat"] = None
            t["partial_eta_squared"] = None
            changed = True
    if changed:
        from doestats._stats_util import bh_adjust
        p_idx = [i for i, t in enumerate(fam["tests"]) if t.get("p_value") is not None]
        qs = bh_adjust([fam["tests"][i]["p_value"] for i in p_idx])
        for i, q in zip(p_idx, qs):
            fam["tests"][i]["q_value_bh"] = q


def _run_designed(run_dir, ctx, profile, df, fig_dir):
    design = profile["design"]
    factor_types = {f["col"]: f.get("type") for f in ctx.get("factors", [])}
    columns_spec = [{"col": f["col"], "type": factor_types.get(f["col"])}
                    for f in ctx.get("factors", []) if f["col"] in df.columns]
    for b in profile["roles"]["blocks"]:
        columns_spec.append({"col": b, "type": None, "is_block": True})
    for c in profile["roles"]["covariates"]:
        columns_spec.append({"col": c, "type": "numeric", "is_covariate": True})
    factor_info = effects_anova.build_factor_info(df, columns_spec)
    base_specs = effects_anova.base_column_specs(factor_info)
    base_df = effects_anova.code_base_columns(df, base_specs)

    include_quad = design.get("design_type") in ("rsm_ccd", "rsm_bbd") or \
        (design.get("center_points") or 0) >= 3
    include_higher = design.get("design_type") == "full_factorial"
    terms = effects_anova.build_terms(factor_info, include_2fi=True,
                                      include_quadratic=include_quad,
                                      include_higher=include_higher)

    responses = profile["roles"]["responses"]
    families, models, metas = [], {}, {}
    for resp in responses:
        y = pd.to_numeric(df[resp], errors="coerce")
        if y.notna().sum() < 5:
            continue
        tests, model, meta = effects_anova.fit_design(
            df, resp, factor_info, terms, base_df, base_specs)
        sigma_pe = meta.get("sigma_pure_error")
        df_pe = meta.get("df_pure_error")
        mde = effects_anova.mde_coded(sigma_pe, meta["n"],
                                      df_pe if df_pe else meta["df_resid"])
        families.append({
            "response": resp,
            "n": meta["n"], "df_resid": meta["df_resid"],
            "df_pure_error": meta["df_pure_error"],
            "df_lack_of_fit": meta["df_lack_of_fit"],
            "mse": meta["mse"], "mse_pure_error": meta["mse_pure_error"],
            "sigma_pure_error": meta["sigma_pure_error"],
            "r_squared": meta["r_squared"], "adj_r_squared": meta["adj_r_squared"],
            "q_squared_loo": meta["q_squared_loo"],
            "mde": mde,
            "mde_note": ("2 水平编码主效应的最小可检效应（α=0.05, power=0.8）" if mde else None),
            "saturated": meta["saturated"],
            "lack_of_fit": meta["lack_of_fit"],
            "tests": tests,
        })
        models[resp] = model
        metas[resp] = meta

    for fam in families:
        _apply_alias_downgrade(fam, profile["design"])

    effect_table = {
        "generated_at": now(), "mode": "designed",
        "model_spec": {
            "main_effects": [t["name"] for t in terms if t["kind"] == "main"],
            "interactions": [t["name"] for t in terms if t["kind"] in ("2fi", "fi")],
            "quadratic": [t["name"] for t in terms if t["kind"] == "quad"],
            "blocks": [t["name"] for t in terms if t["kind"] == "block"],
            "covariates": [t["name"] for t in terms if t["kind"] == "covariate"],
            "pooled_terms": sorted({p for m in models.values() for p in m["pooled_terms"]}),
        },
        "coding": {
            "method": "deviation",
            "continuous_scaling": "(x - mean) / half_range (coded to [-1, 1])",
            "columns": {i["col"]: {"type": i["type"],
                                   "zero_variance": i["zero_variance"]}
                        for i in factor_info},
        },
        "families": families,
        "multiple_testing": {
            "method": "BH", "n_families": len(families),
            "total_tests": sum(len(f["tests"]) for f in families),
            "total_significant_q05": sum(
                1 for f in families for t in f["tests"]
                if (t.get("q_value_bh") is not None and t["q_value_bh"] < 0.05)),
            "excluded_from_family": sum(
                1 for f in families for t in f["tests"] if not t.get("estimable")),
        },
    }
    _write_json(run_dir / "02_analysis" / "effect_table.json", effect_table)

    from scipy import stats as sps
    model_out = []
    for resp, model in models.items():
        st = rsm_mod.stationary_point(model) if include_quad else None
        model["stationary_point"] = st
        resid = np.array(model["_residuals"])
        rd = dict(model.get("residual_diagnostics") or {})
        rd["normality"] = {
            "skew": _r(float(sps.skew(resid))) if resid.size > 2 else None,
            "excess_kurtosis": _r(float(sps.kurtosis(resid)))
            if resid.size > 3 else None,
        }
        model_out.append({
            "response": resp, "n": model["n"], "df_resid": model["df_resid"],
            "mse": _r(model["mse"]),
            "coded_coefficients": {t["term"]: t["coefficient"]
                                   for t in next(f["tests"] for f in families
                                                 if f["response"] == resp)
                                   if t["coefficient"] is not None},
            "r_squared": model["r_squared"], "adj_r_squared": model["adj_r_squared"],
            "q_squared_loo": model["q_squared_loo"], "q_squared_note": model["q_squared_note"],
            "saturated": model["saturated"], "pooled_terms": model["pooled_terms"],
            "lack_of_fit": metas[resp]["lack_of_fit"],
            "residual_diagnostics": rd,
            "predictor": effects_anova.serialize_predictor(model),
            "stationary_point": st,
        })
    _write_json(run_dir / "02_analysis" / "model.json", model_out)

    windows, interactions, confirmations, watchlist, setpoints = \
        wins_mod.designed_windows(models, effect_table, profile, ctx, df)
    plots = figs_mod.designed_figures(models, effect_table, profile, fig_dir, df)
    return {"effect_table": effect_table, "models": models, "models_json": model_out,
            "windows": windows, "interactions": interactions,
            "confirmations": confirmations, "watchlist": watchlist,
            "setpoints": setpoints, "plots": plots, "stability": None}


def _run_observational(run_dir, ctx, profile, df, fig_dir):
    correlation, val = corr_mod.analyze_observational(df, run_dir, ctx, IDP_SCRIPTS)
    _write_json(run_dir / "02_analysis" / "correlation_report.json", correlation)
    stability = stab_mod.analyze_stability(df, run_dir, ctx, IDP_SCRIPTS)
    _write_json(run_dir / "02_analysis" / "stability_report.json", stability)
    windows, interactions, confirmations, watchlist, setpoints = \
        wins_mod.observational_windows(stability, profile, ctx, df,
                                       correlation=correlation)
    plots = figs_mod.observational_figures(correlation, stability, df, fig_dir)
    return {"correlation": correlation, "stability": stability,
            "windows": windows, "interactions": interactions,
            "confirmations": confirmations, "watchlist": watchlist,
            "setpoints": setpoints, "plots": plots}


# ------------------------------------------------------------------ report

def cmd_report(run_dir):
    """Phase R: deterministic single-file HTML report from the 9 artifacts."""
    from doestats.report_html import build as build_report
    out = build_report(run_dir)
    print(f"[report] wrote {out} ({out.stat().st_size} bytes, "
          f"charts={out.read_text(encoding='utf-8').count('class=\"chart-body')} ")
    return 0


def _r(v):
    return round(float(v), 6) if v is not None else None


def main():
    ap = argparse.ArgumentParser(description="industrial-doe-analyzer deterministic core")
    ap.add_argument("subcommand", choices=["profile", "run", "report", "all"])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--data", default=None)
    ap.add_argument("--context", default=None)
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    try:
        if args.subcommand in ("profile", "all"):
            cmd_profile(run_dir, args.data, args.context)
        if args.subcommand in ("run", "all"):
            cmd_run(run_dir)
        if args.subcommand in ("report", "all"):
            cmd_report(run_dir)
        sys.exit(0)
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError) as exc:
        # clean operator-facing exit for rejected paths / missing data
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
