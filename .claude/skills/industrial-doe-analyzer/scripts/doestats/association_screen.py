"""Design-adjusted association screen (Phase 3 / P3-1, contract §8.1 / DS-10).

`screen(df, factor_info, ctx, profile, responses)` classifies EVERY
(non-designed variable x response) and (designed factor x response) pair into
one of four `kind`s and one of four `verdict`s:

kind (what the variable is)              verdict (how the pair was assessed)
-------------------------------------    ------------------------------------
`designed_factor`  a declared factor     `design_adjusted`  OLS on the design
`non_factor`       a declared covariate                     columns + the
                   or block                                 variable
`held_constant`    zero variance, or     `marginal`         marginal only (no
                   collinear with another                      design-adjusted
                   design column                               estimate available)
`unmodeled`        a data column that    `unmodeled`        outside the design /
                   is neither a factor                      model declaration
                   nor a model term

A term the fit dropped (aliased / saturated / pooled) is carried in the pair
`note` + `model_term_status`; the column keeps its declared `kind`.
`marginal` is the verdict when no design-adjusted estimate exists (no design
columns, rank-deficient adjustment, or a saturated design with df_resid = 0).

Key correctness point (the reason this module exists): a pair whose MARGINAL
correlation is strong but which vanishes after adjusting for the design columns
must be reported as an adjusted null — `verdict="design_adjusted"`,
`design_adjusted.p` not significant, `confounded=true`, with the comparison in
`note`. `causal_claim` is ALWAYS the string `"none"`: this is a screening
artifact, never a causal statement, and it must never enter a window
(quality gate G8) — `assert_no_window_keys()` enforces that at emit time.

Statistics caliber: marginal r/p/n come from `stats.core_stats.pearson` (the
single r/p caliber of this repository — recomputing with np.corrcoef is
forbidden); the design-adjusted coefficient/p come from `_stats_util.ols_fit`
plus a two-sided t test. No statistics are re-implemented here.
"""

import argparse
import datetime
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

if __package__ in (None, ""):                 # `python <this file>` (CLI invocation)
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "doestats"                  # enables the relative imports below

CONTRACT_VERSION = "1.0"
CAUSAL_CLAIM = "none"

# Keys that would make this artifact mistakable for an operating window.
WINDOW_LIKE_KEYS = frozenset({
    "operating_windows", "window_id", "window_role", "windows", "setpoints",
    "joint_setpoints", "joint_windows", "expected_effect", "no_window_reason",
    "confirmation_needed", "constraints_applied", "actionable",
    "actionable_blockers", "priority", "range", "predicted_at_center",
    "factor_response_matrix", "actionable_summary", "desirability",
})

KINDS = ("designed_factor", "non_factor", "held_constant", "unmodeled")
VERDICTS = ("design_adjusted", "marginal", "held_constant", "unmodeled")

_IDP_SCRIPTS = (Path(__file__).resolve().parents[5]
                / ".claude" / "skills" / "industrial-data-processor" / "scripts")

AUX_INPUT_NAMES = {"doe_context.json", "analysis_context.json",
                   "analysis_context.merged.json"}
DATA_SUFFIXES = (".csv", ".tsv", ".json", ".parquet", ".feather", ".xlsx", ".xls")


# ------------------------------------------------------------------ helpers

def _load_core_stats():
    """Import the repository's only r/p caliber (core_stats)."""
    if str(_IDP_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_IDP_SCRIPTS))
    from stats import core_stats          # noqa: WPS433 (deliberate late import)
    return core_stats


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _r(v, nd=4):
    if v is None:
        return None
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd)


def assert_no_window_keys(payload, path="screen"):
    """Raise when the screen payload carries anything window-shaped (G8 red line)."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k in WINDOW_LIKE_KEYS:
                raise ValueError(f"association_screen must never emit {path}.{k} "
                                 f"(window-like key; gate G8 forbids it)")
            assert_no_window_keys(v, f"{path}.{k}")
    elif isinstance(payload, list):
        for i, v in enumerate(payload):
            assert_no_window_keys(v, f"{path}[{i}]")
    return True


def _numeric(series, min_valid=3):
    v = pd.to_numeric(series, errors="coerce")
    return v if int(v.notna().sum()) >= min_valid else None


def _normalize_factor_info(factor_info, df, ctx):
    """Accept the effects_anova factor_info list (or None) -> list of dicts."""
    if isinstance(factor_info, list) and factor_info:
        return [dict(i) for i in factor_info if isinstance(i, dict) and i.get("col")]
    if isinstance(factor_info, dict) and factor_info:
        if "factors" in factor_info and isinstance(factor_info["factors"], list):
            return _normalize_factor_info(factor_info["factors"], df, ctx)
        return [dict({"col": k}, **(v if isinstance(v, dict) else {}))
                for k, v in sorted(factor_info.items())]
    # rebuild the minimum needed from ctx (never silently empty)
    spec = [{"col": f["col"], "type": f.get("type")} for f in ctx.get("factors", [])
            if f.get("col") in df.columns]
    for b in ctx.get("blocks", []) or []:
        if b in df.columns:
            spec.append({"col": b, "type": None, "is_block": True})
    for c in ctx.get("covariates", []) or []:
        if c in df.columns:
            spec.append({"col": c, "type": "numeric", "is_covariate": True})
    try:
        from .effects_anova import build_factor_info
        return [dict(i) for i in build_factor_info(df, spec)]
    except Exception:
        pass
    out = []
    for s in spec:
        col = s["col"]
        raw = df[col]
        num = _numeric(raw, 1)
        if num is not None and not s.get("is_block") and s.get("type") != "categorical":
            lo, hi = float(num.min()), float(num.max())
            out.append({"col": col, "type": "numeric", "is_block": bool(s.get("is_block")),
                        "is_covariate": bool(s.get("is_covariate")),
                        "mean": (lo + hi) / 2.0, "half_range": (hi - lo) / 2.0,
                        "zero_variance": (hi - lo) <= 0})
        else:
            levels = sorted(raw.dropna().astype(str).unique())
            out.append({"col": col, "type": "categorical", "levels": levels,
                        "is_block": bool(s.get("is_block")),
                        "is_covariate": bool(s.get("is_covariate")),
                        "zero_variance": len(levels) <= 1})
    return out


def _coded_columns(df, info):
    """Deviation-coded main-effect columns of one factor (effects_anova C1 convention).

    Numeric: (x - mean)/half_range on the [-1, 1] range. Categorical: one column
    per non-reference level (+1 for the level, -1 for the reference, else 0).
    """
    col = info["col"]
    raw = df[col]
    out = {}
    if info.get("zero_variance"):
        return out
    if info.get("type") == "numeric":
        num = _numeric(raw, 2)
        if num is None:
            return out
        mean = info.get("mean")
        half = info.get("half_range")
        if mean is None or half is None or half <= 0:
            mean = (float(num.min()) + float(num.max())) / 2.0
            half = (float(num.max()) - float(num.min())) / 2.0
        if half <= 0:
            return out
        out[col] = (num - float(mean)) / float(half)
        return out
    levels = info.get("levels") or sorted(raw.dropna().astype(str).unique())
    if len(levels) < 2:
        return out
    s = raw.astype(str)
    ref = str(levels[-1])
    for lv in levels[:-1]:
        key = f"{col}[{lv}]"
        out[key] = pd.Series(np.where(s == str(lv), 1.0,
                                      np.where(s == ref, -1.0, 0.0)), index=df.index)
    return out


def _candidate_series(df, info, col):
    """(series, test_name, note) for screening; (None, None, reason) when not screenable.

    Numeric columns are used as-is; a 2-level categorical column is coded +-1
    (deviation coding) so it can carry a single coefficient; a >=3-level column
    is disclosed as not screenable here (its design-side story is the effect
    table's one-way terms).
    """
    num = _numeric(df[col], 3)
    if num is not None:
        return num, col, None
    if info and info.get("type") == "categorical":
        levels = info.get("levels") or sorted(df[col].dropna().astype(str).unique())
        if len(levels) == 2:
            ref = str(levels[-1])
            s = df[col].astype(str)
            return (pd.Series(np.where(s == str(levels[0]), 1.0, -1.0), index=df.index),
                    f"{col}[{levels[0]}]", "2 水平分类列按 -1/+1 偏差编码筛选")
        return None, None, f"categorical with {len(levels)} levels (>=3)"
    return None, None, "non_numeric_candidate"


def _ols_coef_test(y, X_cols, test_name, ols_fit):
    """Coefficient + two-sided p for `test_name` inside an OLS (design-adjusted)."""
    if not X_cols:
        return None
    try:
        M = np.column_stack([np.asarray(v, dtype=float) for v in X_cols.values()])
        yv = np.asarray(y, dtype=float)
        beta, rank, rss, xtx_inv, Xa = ols_fit(M, yv)
    except (ValueError, np.linalg.LinAlgError, KeyError):
        return None
    n = len(yv)
    if xtx_inv is None or rank < Xa.shape[1] or n - rank < 1:
        return None          # rank-deficient: the coefficient is not separable
    names = list(X_cols.keys())
    if test_name not in names:
        return None
    j = names.index(test_name) + 1          # +1 for the intercept column
    df = n - rank
    mse = rss / df
    se = math.sqrt(max(mse * float(xtx_inv[j, j]), 0.0))
    coef = float(beta[j])
    if se <= 0:
        return {"coef": _r(coef), "p": None, "n": int(n), "df": int(df)}
    t = coef / se
    p = 2.0 * float(sps.t.sf(abs(t), df))
    return {"coef": _r(coef), "p": _r(p), "n": int(n), "df": int(df),
            "std_err": _r(se), "t": _r(t)}


# ------------------------------------------------------------------ screen

def screen(df, factor_info, ctx, profile, responses):
    """Full association screen (contract §8.1). Deterministic, sorted iteration."""
    core_stats = _load_core_stats()
    ctx = ctx or {}
    profile = profile or {}
    factor_info = _normalize_factor_info(factor_info, df, ctx)
    responses = [r for r in (responses or []) if r in df.columns]
    if not responses:
        responses = [r["col"] for r in ctx.get("responses", []) if r.get("col") in df.columns]
    alpha = float(ctx.get("alpha") or 0.05)

    by_col = {i["col"]: i for i in factor_info}
    design_cols = [i["col"] for i in factor_info
                   if not i.get("is_block") and not i.get("is_covariate")]
    model_cols = [i["col"] for i in factor_info if i.get("is_block") or i.get("is_covariate")]
    zero_var = {i["col"] for i in factor_info if i.get("zero_variance")}
    for c in profile.get("quality", {}).get("constant_cols") or []:
        zero_var.add(c)
    for cav in profile.get("caveats") or []:
        if cav.get("code") == "ZERO_VARIANCE_FACTORS":
            ev = cav.get("evidence")
            if isinstance(ev, list):
                zero_var.update(str(x) for x in ev)
    # data-level constants count as held_constant whatever their declaration says
    for c in df.columns:
        if pd.to_numeric(df[c], errors="coerce").notna().sum() >= 1 \
                and df[c].dropna().nunique() <= 1:
            zero_var.add(c)

    unmodeled_terms = _unmodeled_terms(ctx)

    index_cols = set(ctx.get("index_cols") or [])
    # Only genuine identifiers are excluded here. `ignore` columns are NOT
    # metadata: a column outside the design/fitted model is exactly the
    # `unmodeled` class this screen exists to surface (DS-10) — dropping them
    # would leave the most dangerous confounder unscreened.
    index_cols.update(profile.get("roles", {}).get("index") or [])
    meta_cols = set(index_cols) | set(responses)
    for key in ("run_order_col", "group_col"):
        if ctx.get(key):
            meta_cols.add(ctx[key])

    # --- candidate columns: every non-designed variable present in the data ---
    id_like = re.compile(r"(^id$|_id$|^no$|_no$|编号|序号|^index$)", re.IGNORECASE)
    excluded, candidates = [], []
    for c in sorted(df.columns):
        if c in meta_cols or c in by_col:
            continue
        if id_like.search(str(c)):
            excluded.append({"column": c, "reason": "identifier-like column name"})
            continue
        s, name, why = _candidate_series(df, None, c)
        if s is None:
            excluded.append({"column": c, "reason": why})
        else:
            candidates.append(c)
    excluded.extend({"column": c, "reason": "design/model metadata column"}
                    for c in sorted(meta_cols) if c in df.columns)

    # --- coded design columns (adjustment set) ---
    coded_by_factor = {i["col"]: _coded_columns(df, i) for i in factor_info}
    design_coded_all = {}
    for c in design_cols + model_cols:
        design_coded_all.update(coded_by_factor.get(c, {}))

    def _adjustment_for(test_col):
        """Design columns (factors + blocks) minus the tested variable's own columns."""
        out = {}
        for name, series in design_coded_all.items():
            if name == test_col or name.startswith(f"{test_col}["):
                continue
            out[name] = series
        return out

    from ._stats_util import ols_fit

    def _collinear_with_design(s, test_col):
        """|r| >= 0.999 against any OTHER design column -> not separately screenable."""
        if s is None:
            return None
        vals = np.asarray(s, dtype=float)
        for name, dcol in _adjustment_for(test_col).items():
            dv = np.asarray(dcol, dtype=float)
            mask = np.isfinite(vals) & np.isfinite(dv)
            if int(mask.sum()) < 3:
                continue
            a, b = vals[mask], dv[mask]
            if float(np.std(a)) <= 0 or float(np.std(b)) <= 0:
                continue
            r = float(core_stats.pearson(a.tolist(), b.tolist()).get("r") or 0.0)
            if abs(r) >= 0.999:
                return name, r
        return None

    screenable = {}
    for col in sorted(set(candidates) | set(design_cols) | set(model_cols)):
        info = by_col.get(col) if by_col.get(col) else next(
            (i for i in factor_info if i["col"] == col), None)
        s, name, why = _candidate_series(df, info, col)
        if s is None and col in by_col:
            excluded.append({"column": col, "reason": why,
                             "note": "分类因子（>=3 水平）不在本表筛选；其效应见 effect_table"})
        screenable[col] = (s, name, why)

    pairs, n_confounded = [], 0
    for resp in responses:
        y = _numeric(df[resp], 3)
        for col in sorted(screenable):
            kind = _kind_of(col, design_cols, model_cols, zero_var)
            s, test_name, coding_note = screenable[col]
            term = unmodeled_terms.get(col)
            if term:
                extra = f"（{term.get('reason_code') or 'not_estimated'}）"
                coding_note = (coding_note + "；" if coding_note else "") + \
                    f"拟合模型未估计该项{extra}：本对仅作筛选线索"
            collinear = None
            if kind != "held_constant" and s is not None:
                collinear = _collinear_with_design(s, col)
                if collinear:
                    kind = "held_constant"
                    coding_note = (coding_note + "；" if coding_note else "") + \
                        (f"与设计列 {collinear[0]} 共线 (|r|={abs(round(collinear[1], 4))}) "
                         f"— 不可单独估计，按 held_constant 处理")
            if y is None:
                pairs.append(_pair(col, resp, kind, None, None, alpha,
                                   reason="RESPONSE_ALL_MISSING: 响应列全部缺失/非数值"))
                continue
            if s is None:
                pairs.append(_pair(col, resp, kind, None, None, alpha,
                                   reason="不可数值筛选（见 excluded）；仅有结构性分类"))
                continue
            valid = y.notna() & s.notna()
            const = bool(s[valid].nunique(dropna=True) <= 1) if int(valid.sum()) else True
            if const:
                marg = {"r": None, "p": None, "n": int(valid.sum()),
                        "method": "not_computable_constant"}
            else:
                got = core_stats.pearson(
                    [None if pd.isna(v) else float(v) for v in s[valid].tolist()],
                    [None if pd.isna(v) else float(v) for v in y[valid].tolist()])
                marg = {"r": got.get("r"), "p": got.get("p"),
                        "n": int(got.get("n") or 0), "method": "core_stats.pearson"}
            adj = None
            if not const and kind != "held_constant":
                adj_series = _adjustment_for(col)
                X_cols = dict(adj_series)
                X_cols[test_name] = s
                mask = valid.copy()
                for v in adj_series.values():
                    mask &= pd.Series(np.isfinite(np.asarray(v, dtype=float)),
                                      index=df.index)
                if int(mask.sum()) >= 4:
                    got = _ols_coef_test(
                        y[mask], {k: np.asarray(v, dtype=float)[mask.to_numpy()]
                                  for k, v in X_cols.items()}, test_name, ols_fit)
                    if got:
                        adj = {"coef": got["coef"], "p": got["p"], "n": got["n"],
                               "method": "ols_design_adjusted",
                               "strata": sorted(adj_series.keys())}
                        for extra in ("std_err", "t", "df"):
                            if got.get(extra) is not None:
                                adj[extra] = got[extra]
            pair = _pair(col, resp, kind, marg, adj, alpha, coding_note=coding_note,
                         term_status=term)
            pairs.append(pair)
            if pair.get("confounded"):
                n_confounded += 1

    pairs.sort(key=lambda p: (p["response"], p["factor"]))
    out = {
        "contract_version": CONTRACT_VERSION,
        # No wall-clock here on purpose: recommendations.association_screen_ref
        # carries this file's sha256, so a timestamp would make two identical runs
        # produce different refs (RG-03 determinism).
        "causal_claim": CAUSAL_CLAIM,
        "n_rows": int(len(df)),
        "n_pairs": len(pairs),
        "design_adjusted": any(p["verdict"] == "design_adjusted" for p in pairs),
        "alpha": alpha,
        "responses": sorted(responses),
        "design_columns": sorted(design_cols),
        "model_columns": sorted(model_cols),
        "adjustment_method": ("每对 (response, variable) 回归：y ~ 设计列(该变量自身列除外) + "
                              "该变量；报告该变量系数与双侧 t 检验 p（秩亏则不报告）"),
        "window_emission": "forbidden (gate G8: association pairs never enter a window)",
        "n_confounded_pairs": n_confounded,
        "excluded": excluded,
        "pairs": pairs,
    }
    assert_no_window_keys(out)
    return out


def _kind_of(col, design_cols, model_cols, zero_var):
    """kind = the variable's role in the design + fitted model declaration.

    `designed_factor` (a declared factor) and `non_factor` (a declared covariate
    or block) are the two modeled roles; `held_constant` (zero variance or
    collinear with another design column) and `unmodeled` (a data column that is
    neither a factor nor a model term) are the two structural exclusions. A term
    the fit dropped (aliased/saturated/pooled) is disclosed in the pair `note`
    and in `model_term_status`, not re-routed to `unmodeled` — the column is
    still a declared factor.
    """
    if col in zero_var:
        return "held_constant"
    if col in design_cols:
        return "designed_factor"
    if col in model_cols:
        return "non_factor"
    return "unmodeled"


def _unmodeled_terms(ctx):
    """{term: term_status} for terms the fitted model did NOT estimate."""
    et = ctx.get("_effect_table") or ctx.get("effect_table") or {}
    spec = (et or {}).get("model_spec") or {}
    out = {}
    for term, info in (spec.get("term_status") or {}).items():
        if isinstance(info, dict) and info.get("estimated") is False:
            out[str(term)] = info
    for t in spec.get("pooled_terms") or []:
        out.setdefault(str(t), {"estimated": False, "reason_code": "pooled"})
    return out


def _pair(col, resp, kind, marg, adj, alpha, reason=None, coding_note=None,
          term_status=None):
    """Assemble one pair record (contract §8.1 keys + additive flags)."""
    alpha = float(alpha or 0.05)
    marg_sig = bool(marg and marg.get("p") is not None and marg["p"] < alpha
                    and marg.get("r") is not None and abs(marg["r"]) >= 0.3)
    adj_sig = bool(adj and adj.get("p") is not None and adj["p"] < alpha)
    confounded = bool(marg_sig and adj and adj.get("p") is not None and not adj_sig)

    if kind == "held_constant":
        verdict = "held_constant"
    elif kind == "unmodeled":
        verdict = "unmodeled"
    elif adj is not None:
        verdict = "design_adjusted"
    else:
        verdict = "marginal"

    note_bits = []
    if reason:
        note_bits.append(reason)
    if verdict == "held_constant":
        note_bits.append("方差≈0 或与设计列共线：不可单独筛选（结构性结论，不含因果含义）")
    elif kind == "unmodeled":
        note_bits.append("该列未进入拟合模型（未建模）：只能作描述性线索，禁止进入任何窗口")
    if marg is not None:
        if marg.get("r") is None:
            note_bits.append(f"边际相关不可计算（{marg.get('method')}）")
        else:
            note_bits.append(f"边际 r={marg['r']} (p={marg['p']}, n={marg['n']}, "
                             f"core_stats)")
    else:
        note_bits.append("边际相关不可计算（有效样本不足或不可数值编码）")
    if adj is not None:
        note_bits.append(f"设计调整后 coef={adj['coef']} (p={adj['p']}, n={adj['n']}, "
                         f"调整列={len(adj['strata'])})")
        if confounded:
            note_bits.append("★混杂：边际强相关在设计调整后消失（边际强/调整零），"
                             "设计列解释了该相关，不得据此排序参数重要性")
    elif verdict == "marginal":
        note_bits.append("无设计调整估计（设计列不可用或秩亏），仅为边际线索")
    if coding_note:
        note_bits.append(coding_note)

    level = "L3" if (adj is not None or verdict == "held_constant") else "L4"
    out = {
        "factor": col,
        "response": resp,
        "kind": kind,
        "marginal": marg,
        "design_adjusted": adj,
        "verdict": verdict,
        "note": "；".join(note_bits),
        "confounded": confounded,
        "marginal_significant": marg_sig,
        "adjusted_significant": adj_sig,
        "evidence_level": level,
    }
    if term_status:
        out["model_term_status"] = {"estimated": bool(term_status.get("estimated")),
                                    "reason_code": term_status.get("reason_code")}
    return out


# ------------------------------------------------------------------ CLI

def _load_run(run_dir):
    run_dir_v = Path(run_dir).resolve()
    ctx_path = run_dir_v / "00_input" / "analysis_context.json"
    if not ctx_path.exists():
        raise SystemExit(f"ANALYSIS_CONTEXT_REQUIRED: {ctx_path} not found")
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    prof_path = run_dir_v / "01_profile" / "data_profile.json"
    profile = json.loads(prof_path.read_text(encoding="utf-8")) if prof_path.exists() else {}
    data_path = ctx.get("data_path")
    if data_path:
        p = Path(data_path)
        if not p.is_absolute():
            p = (run_dir_v / data_path).resolve()
    else:
        p = None
    if p is None or not p.is_file():
        for cand in sorted((run_dir_v / "00_input").iterdir()):
            if cand.is_file() and cand.name.lower() not in AUX_INPUT_NAMES \
                    and cand.suffix.lower() in DATA_SUFFIXES:
                p = cand
                break
    if p is None or not p.is_file():
        raise SystemExit(f"RUN_TABLE_REQUIRED: no data file under {run_dir_v / '00_input'}")
    if p.suffix.lower() in (".csv", ".txt"):
        df = pd.read_csv(p)
    elif p.suffix.lower() == ".tsv":
        df = pd.read_csv(p, sep="\t")
    elif p.suffix.lower() == ".json":
        df = pd.read_json(p)
    else:
        raise SystemExit(f"UNSUPPORTED_DATA_FORMAT: {p.suffix} ({p})")
    return run_dir_v, df, ctx, profile


def main(argv=None):
    ap = argparse.ArgumentParser(description="Design-adjusted association screen (P3-1)")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=None,
                    help="default: <run-dir>/02_analysis/association_screen.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    run_dir, df, ctx, profile = _load_run(args.run_dir)
    responses = [r["col"] for r in ctx.get("responses", []) if r.get("col") in df.columns]
    spec = [{"col": f["col"], "type": f.get("type")} for f in ctx.get("factors", [])
            if f.get("col") in df.columns]
    for b in ctx.get("blocks", []) or []:
        if b in df.columns:
            spec.append({"col": b, "type": None, "is_block": True})
    for c in ctx.get("covariates", []) or []:
        if c in df.columns:
            spec.append({"col": c, "type": "numeric", "is_covariate": True})
    try:
        from .effects_anova import build_factor_info
        factor_info = build_factor_info(df, spec)
    except Exception:
        factor_info = _normalize_factor_info(None, df, ctx)
    payload = screen(df, factor_info, ctx, profile, responses)
    out = Path(args.out) if args.out else run_dir / "02_analysis" / "association_screen.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[association_screen] {payload['n_pairs']} pairs "
          f"({payload['n_confounded_pairs']} confounded) -> {out}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
