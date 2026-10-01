"""Designed-mode deterministic statistics (plan §3 C1-C5, C8, C9).

Everything here is numpy/scipy-only and reproducible. Key conventions:
- C1 deviation coding (dummy coding forbidden); continuous factors centered and
  scaled by half-range; quadratic terms only for continuous factors.
- C2 extra-SS ANOVA via reduced-model refit. The emitted field is `ss_extra_ss`,
  deliberately NOT "Type-II": on orthogonal (balanced) designs single-deletion
  extra-SS coincides exactly with Type-II; on unbalanced designs (deviation
  coding keeps interactions containing the tested term in the reduced model) it
  is Type-III-style and p values are coding-dependent — the profile emits an
  UNBALANCED_DESIGN caveat there.
- C3 saturation strategy: pure error -> pool highest-order terms -> report
  pooled rows with reason_code "pooled"/"saturated"; never invent df.
- C4 pure-error df from replicate groups; lack-of-fit only when df_resid > df_pe > 0.
- C5 BH-FDR per response family; aliased/saturated/pooled rows never enter the family.

Blocks and covariates are modeled as factor_info entries flagged `is_block` /
`is_covariate`: they enter the model (occupy df) but never produce windows.
"""

import itertools
import math
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats as sps

from ._stats_util import bh_adjust

ALIAS_ATOL = 1e-9


# ---------------------------------------------------------------- factor coding

def build_factor_info(df, columns_spec, max_levels=12):
    """Per-factor coding metadata.

    columns_spec: list of {col, type?, is_block?, is_covariate?}
    """
    infos = []
    for spec in columns_spec:
        col = spec["col"]
        if col not in df.columns:
            continue
        ftype = spec.get("type")
        raw = df[col]
        if ftype is None:
            ftype = "categorical" if raw.dropna().nunique() <= max_levels else "numeric"
        info = {"col": col, "type": ftype,
                "is_block": bool(spec.get("is_block")),
                "is_covariate": bool(spec.get("is_covariate"))}
        if ftype == "numeric":
            vals = pd.to_numeric(raw, errors="coerce")
            lo, hi = float(vals.min()), float(vals.max())
            hr = (hi - lo) / 2.0
            info.update(mean=(lo + hi) / 2.0, half_range=hr, zero_variance=hr <= 0)
        else:
            levels = sorted(raw.dropna().unique(), key=str)
            info.update(levels=[str(v) for v in levels], zero_variance=len(levels) <= 1)
        infos.append(info)
    return infos


def base_column_specs(factor_info):
    """Base coded column definitions (no products): name -> spec."""
    cols = {}
    for info in factor_info:
        if info["zero_variance"]:
            continue
        if info["type"] == "numeric":
            cols[info["col"]] = {"kind": "numeric_main", "factor": info["col"],
                                 "info": info}
        else:
            for lv in info["levels"][:-1]:  # deviation coding, reference = last level
                cols[f"{info['col']}[{lv}]"] = {"kind": "level", "factor": info["col"],
                                                "level": lv, "info": info}
    return cols


def code_base_columns(df, base_specs):
    """Materialize base coded columns (deviation coding, C1)."""
    out = {}
    for name, spec in base_specs.items():
        info = spec["info"]
        raw = df[info["col"]]
        if spec["kind"] == "numeric_main":
            x = pd.to_numeric(raw, errors="coerce")
            out[name] = (x - info["mean"]) / info["half_range"]
        else:
            s = raw.astype(str)
            ref = info["levels"][-1]
            out[name] = pd.Series(
                np.where(s == str(spec["level"]), 1.0,
                         np.where(s == str(ref), -1.0, 0.0)),
                index=df.index)
    return pd.DataFrame(out, index=df.index)


# ---------------------------------------------------------------- term building

def build_terms(factor_info, include_2fi=True, include_quadratic=False,
                include_higher=False):
    """Ordered term specs: mains (1) -> quadratic (2) -> 2FI (2) -> kFI (3+).

    Blocks/covariates contribute main terms only (flagged), never interactions.
    """
    terms = []
    modelable = [i for i in factor_info if not i["zero_variance"]]
    core = [i for i in modelable if not (i.get("is_block") or i.get("is_covariate"))]
    for info in core:
        terms.append({"name": info["col"], "order": 1, "kind": "main",
                      "factors": [info["col"]]})
    for info in modelable:
        if info.get("is_block") or info.get("is_covariate"):
            terms.append({"name": info["col"], "order": 1, "kind": "block" if info.get("is_block") else "covariate",
                          "factors": [info["col"]]})
    if include_quadratic:
        for info in core:
            if info["type"] == "numeric":
                terms.append({"name": f"{info['col']}^2", "order": 2, "kind": "quad",
                              "factors": [info["col"]]})
    if include_2fi:
        for a, b in itertools.combinations(core, 2):
            terms.append({"name": f"{a['col']}:{b['col']}", "order": 2, "kind": "2fi",
                          "factors": [a["col"], b["col"]]})
    if include_higher:
        for r in range(3, len(core) + 1):
            for combo in itertools.combinations(core, r):
                terms.append({"name": ":".join(i["col"] for i in combo), "order": r,
                              "kind": "fi", "factors": [i["col"] for i in combo]})
    return terms


def _factor_base_names(factor, base_specs):
    return [n for n, s in base_specs.items()
            if s["factor"] == factor and s["kind"] in ("numeric_main", "level")]


def term_column_specs(term, base_specs):
    """Concrete column specs for a term (products over base columns of its factors)."""
    if term["kind"] in ("main", "block", "covariate"):
        names = _factor_base_names(term["factors"][0], base_specs)
        return [{"name": n, "fn": "identity", "inputs": [n]} for n in names]
    if term["kind"] == "quad":
        f = term["factors"][0]
        return [{"name": f"{f}^2", "fn": "square", "inputs": [f]}]
    if term["kind"] == "2fi":
        prods = []
        for n1 in _factor_base_names(term["factors"][0], base_specs):
            for n2 in _factor_base_names(term["factors"][1], base_specs):
                prods.append({"name": f"{n1}*{n2}", "fn": "product", "inputs": [n1, n2]})
        return prods
    # k-way FI (k >= 3): one base column per factor
    per_factor = [_factor_base_names(f, base_specs)[:1] for f in term["factors"]]
    out = []
    for combo in itertools.product(*per_factor):
        out.append({"name": "*".join(combo), "fn": "product", "inputs": list(combo)})
    return out


def materialize_columns(base_df, specs):
    """Expand base columns into term columns per specs. Returns {colname: Series}."""
    out = {}
    for spec in specs:
        if spec["fn"] == "identity":
            out[spec["name"]] = base_df[spec["inputs"][0]]
        elif spec["fn"] == "square":
            v = base_df[spec["inputs"][0]]
            out[spec["name"]] = v * v
        else:
            a = base_df[spec["inputs"][0]]
            b = base_df[spec["inputs"][1]]
            out[spec["name"]] = a * b
    return out


# ---------------------------------------------------------------- design matrix

class DesignMatrix:
    """Column-deduplicating design matrix builder (aliasing detection)."""

    def __init__(self):
        self.names = []          # kept column names (order preserved)
        self.values = None       # (n, p)
        self.term_of = []        # term name per column
        self.kind_of = []        # term kind per column
        self.alias_map = defaultdict(list)  # dropped term -> kept terms it duplicates
        self.name_spec = {}      # colname -> spec
        self.term_specs_kept = []  # (term, specs) kept, in order

    def _dup_of(self, vec):
        if self.values is None:
            return None
        for j in range(self.values.shape[1]):
            if np.allclose(vec, self.values[:, j], atol=ALIAS_ATOL, rtol=0):
                return self.names[j]
        return None

    def add_term(self, term, specs, materialized):
        """Returns True if the term contributed at least one unique column."""
        dup_targets, usable = [], []
        for spec in specs:
            vec = np.asarray(materialized[spec["name"]], dtype=float)
            dup = self._dup_of(vec)
            if dup is None:
                usable.append((spec, vec))
            else:
                dup_targets.append(dup)
        if not usable:
            self.alias_map[term["name"]].extend(sorted(set(dup_targets)))
            return False
        for spec, vec in usable:
            self.names.append(spec["name"])
            self.term_of.append(term["name"])
            self.kind_of.append(term["kind"])
            self.name_spec[spec["name"]] = spec
            col = vec.reshape(-1, 1)
            self.values = col if self.values is None else np.hstack([self.values, col])
        self.term_specs_kept.append((term, [s for s, _ in usable]))
        if dup_targets:
            self.alias_map[term["name"]].extend(sorted(set(dup_targets)))
        return True


# ---------------------------------------------------------------- fitting

def fit_design(df, response, factor_info, terms, base_df, base_specs):
    """Fit one response. Returns (tests, model, meta).

    model carries an in-memory `predict_raw(dict)` closure for windows/rsm/figures.
    """
    kept = DesignMatrix()
    for term in terms:
        specs = term_column_specs(term, base_specs)
        kept.add_term(term, specs, materialize_columns(base_df, specs))

    y_all = pd.to_numeric(df[response], errors="coerce")
    frame = pd.DataFrame(kept.values, columns=[f"c{j}" for j in range(kept.values.shape[1])],
                         index=df.index)
    frame["_y"] = y_all
    frame = frame.dropna()
    y = frame["_y"].to_numpy()
    X = frame.drop(columns=["_y"]).to_numpy()
    n = X.shape[0]

    beta, rank, rss, xtx_inv, Xa = _lstsq(X, y)
    df_resid = n - rank
    ss_total = float(((y - y.mean()) ** 2).sum())
    saturated = False
    pooled = []
    keep_idx = list(range(X.shape[1]))
    term_order = {t["name"]: t["order"] for t in terms}
    pool_prio = {"fi": 0, "2fi": 1, "quad": 2, "main": 3,
                 "block": 4, "covariate": 5}

    # --- C3 saturation pooling (highest order first, then 2FI before quad) ---
    if df_resid <= 0:
        saturated = True
        guard = 0
        while df_resid <= 0 and guard < 64:
            guard += 1
            candidates = [j for j in keep_idx if term_order.get(kept.term_of[j], 9) >= 2
                          and kept.kind_of[j] in ("fi", "2fi", "quad")]
            if not candidates:
                break
            worst = max(candidates,
                        key=lambda j: (term_order.get(kept.term_of[j], 9),
                                       -pool_prio.get(kept.kind_of[j], 0)))
            drop_term = kept.term_of[worst]
            keep_idx = [j for j in keep_idx if kept.term_of[j] != drop_term]
            pooled.append(drop_term)
            beta, rank, rss, xtx_inv, Xa = _lstsq(X[:, keep_idx], y)
            df_resid = n - rank

    X_use = Xa[:, 1:] if Xa.shape[1] > 1 else np.zeros((n, 0))
    mse = rss / df_resid if df_resid > 0 else None

    # --- C4 pure error / lack-of-fit ---
    df_pe, ss_pe, df_lof, ss_lof, f_lof, p_lof = _pure_error(X_use, y, rss, df_resid)
    sigma_pe = float(np.sqrt(ss_pe / df_pe)) if df_pe and df_pe > 0 else None

    # --- C2 extra-SS ANOVA via reduced-model refit ---
    # ss_extra_ss = RSS(reduced model without the tested term's columns) - RSS(full),
    # df = rank difference. Semantics: on ORTHOGONAL (balanced) designs this is
    # exactly classical Type-II; on unbalanced designs the reduced model retains
    # interactions containing the tested term (deviation coding), so the value is
    # the Type-III-style single-deletion extra-SS and p values are coding-dependent
    # (profile emits an UNBALANCED_DESIGN caveat in that case).
    kept_names = [kept.names[j] for j in keep_idx]
    kept_term_of = [kept.term_of[j] for j in keep_idx]
    kept_kind_of = [kept.kind_of[j] for j in keep_idx]
    tests = []
    seen = []
    for j, tname in enumerate(kept_term_of):
        if tname in seen or tname in pooled:
            continue
        seen.append(tname)
        cols_j = [i for i, tn in enumerate(kept_term_of) if tn == tname]
        sub = [i for i in range(X_use.shape[1]) if i not in cols_j]
        _, rank_red, rss_red, _, _ = _lstsq(X_use[:, sub], y)
        ss = max(rss_red - rss, 0.0)
        df_t = rank - rank_red
        tinfo = next(t for t in terms if t["name"] == tname)
        coef_val = float(beta[cols_j[0] + 1]) if len(cols_j) == 1 else None
        se_val = None
        if len(cols_j) == 1 and xtx_inv is not None:
            se_val = float(np.sqrt(max(mse or 0, 0) * xtx_inv[cols_j[0] + 1, cols_j[0] + 1]))
        row = {
            "term": tname, "order": tinfo["order"],
            "coefficient": _r(coef_val), "std_err": _r(se_val),
            "df": int(df_t), "ss_extra_ss": _r(ss), "n": int(n),
            "estimable": True, "reason_code": None,
            "alias_chain": _term_level_alias(tname, kept.alias_map.get(tname, [])),
        }
        if df_t > 0 and mse and mse > 0 and df_resid > 0:
            f_stat = (ss / df_t) / mse
            row["f_stat"] = _r(f_stat)
            row["p_value"] = float(sps.f.sf(f_stat, df_t, df_resid))
            row["eta_squared"] = _r(ss / ss_total) if ss_total > 0 else None
            row["partial_eta_squared"] = _r(ss / (ss + rss))
            row["effect_size_std"] = _r(abs(coef_val) / sigma_pe) if (sigma_pe and coef_val is not None) else None
        else:
            row["p_value"] = None
            row["reason_code"] = "saturated"
        tests.append(row)

    # pooled terms: coefficient-only rows, never in the family (C3/C5)
    for tname in pooled:
        tinfo = next(t for t in terms if t["name"] == tname)
        tests.append({
            "term": tname, "order": tinfo["order"], "coefficient": None,
            "std_err": None, "df": None, "ss_extra_ss": None, "n": int(n),
            "estimable": False, "reason_code": "pooled",
            "alias_chain": _term_level_alias(tname, kept.alias_map.get(tname, [])),
        })

    # BH within family (C5)
    p_idx = [i for i, t in enumerate(tests) if t.get("p_value") is not None]
    qs = bh_adjust([tests[i]["p_value"] for i in p_idx])
    for i, q in zip(p_idx, qs):
        tests[i]["q_value_bh"] = q

    # Pareto rank by |t| among rows with a usable SE
    rankable = [t for t in tests if t.get("std_err") not in (None, 0)]
    rankable.sort(key=lambda t: abs((t["coefficient"] or 0) / t["std_err"]), reverse=True)
    for rk, t in enumerate(rankable, start=1):
        t["pareto_rank"] = rk

    # --- in-memory model for windows / rsm / figures ---
    kept_specs = [(t, specs) for (t, specs) in kept.term_specs_kept
                  if t["name"] not in pooled]
    model = {
        "response": response,
        "n": int(n),
        "df_resid": int(df_resid),
        "mse": mse,
        "sigma_pe": sigma_pe,
        "df_pure_error": df_pe,
        "r_squared": _r(1 - rss / ss_total) if ss_total > 0 else 0.0,
        # P0-3: ss_total=0 (constant response) makes this 0/0 -> non-finite; guard
        # to None in the same style as the r_squared guard next to it
        "adj_r_squared": _r(1 - (rss / df_resid) / (ss_total / (n - 1)))
                         if df_resid > 0 and n > 1 and ss_total > 0 else None,
        "saturated": saturated,
        "pooled_terms": pooled,
        "kept_terms": [t for t, _ in kept_specs],
        "colnames": kept_names,
        "term_of": kept_term_of,
        "beta": beta,
        "xtx_inv": xtx_inv,
        "alias_map": dict(kept.alias_map),
        "base_specs": base_specs,
        "factor_info": factor_info,
        "kept_specs": kept_specs,
    }
    model["predict_raw"] = _make_predictor(model)
    fitted = Xa @ beta
    resid = y - fitted
    model["_residuals"] = resid.tolist()
    model["_fitted"] = fitted.tolist()
    # hat diagonal computed ONCE here: Q² reuse + leverage/Cook's D diagnostics.
    h_diag = None
    if xtx_inv is not None and Xa.shape[1] > 0:
        h_diag = np.clip(np.einsum("ij,jk,ik->i", Xa, xtx_inv, Xa), 0.0, 0.999999)
    q2, q2_note = _q_squared_hat(X_use, y, xtx_inv, model, h_diag=h_diag)
    model["q_squared_loo"] = q2
    model["q_squared_note"] = q2_note
    model["residual_diagnostics"] = _residual_diagnostics(
        Xa, y, resid, h_diag, mse, frame.index)

    lack = {
        "estimable": bool(df_pe and df_pe > 0 and df_lof and df_lof > 0),
        "reason": None if (df_pe and df_pe > 0) else "no pure-error replicates",
        "f_stat": _r(f_lof) if f_lof is not None else None,
        "p_value": float(p_lof) if p_lof is not None else None,
    }
    meta = {
        "n": int(n),
        "df_resid": int(df_resid),
        "df_pure_error": int(df_pe) if df_pe else 0,
        "df_lack_of_fit": int(df_lof) if df_lof else 0,
        "mse": _r(mse),
        "mse_pure_error": _r(ss_pe / df_pe) if df_pe else None,
        "sigma_pure_error": _r(sigma_pe) if sigma_pe else None,
        "saturated": saturated,
        "pooled_terms": pooled,
        "lack_of_fit": lack,
        "r_squared": model["r_squared"],
        "adj_r_squared": model["adj_r_squared"],
        "q_squared_loo": q2,
        "q_squared_note": q2_note,
    }
    return tests, model, meta


def _make_predictor(model):
    """Closure: raw factor/block/covariate values dict -> predicted y."""
    base_specs = model["base_specs"]
    kept_specs = model["kept_specs"]
    beta = model["beta"]
    factor_info = {i["col"]: i for i in model["factor_info"]}

    def predict_raw(raw):
        base_vals = {}
        for name, spec in base_specs.items():
            info = factor_info[spec["factor"]]
            v = raw.get(info["col"])
            if spec["kind"] == "numeric_main":
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return None
                base_vals[name] = (float(v) - info["mean"]) / info["half_range"]
            else:
                sv = str(v) if v is not None else None
                if sv is None:
                    return None
                base_vals[name] = 1.0 if sv == str(spec["level"]) else (
                    -1.0 if sv == str(info["levels"][-1]) else 0.0)
        acc = beta[0]
        for term, specs in kept_specs:
            for spec in specs:
                if spec["fn"] == "identity":
                    val = base_vals[spec["inputs"][0]]
                elif spec["fn"] == "square":
                    val = base_vals[spec["inputs"][0]] ** 2
                else:
                    val = base_vals[spec["inputs"][0]] * base_vals[spec["inputs"][1]]
                j = model["colnames"].index(spec["name"]) + 1
                acc += beta[j] * val
        return float(acc)

    def se_predict_raw(raw):
        if model["xtx_inv"] is None or model["mse"] in (None, 0):
            return None
        base_vals = {}
        for name, spec in base_specs.items():
            info = factor_info[spec["factor"]]
            v = raw.get(info["col"])
            if spec["kind"] == "numeric_main":
                if v is None:
                    return None
                base_vals[name] = (float(v) - info["mean"]) / info["half_range"]
            else:
                sv = str(v) if v is not None else None
                if sv is None:
                    return None
                base_vals[name] = 1.0 if sv == str(spec["level"]) else (
                    -1.0 if sv == str(info["levels"][-1]) else 0.0)
        x0 = np.ones(len(model["colnames"]) + 1)
        for term, specs in kept_specs:
            for spec in specs:
                if spec["fn"] == "identity":
                    val = base_vals[spec["inputs"][0]]
                elif spec["fn"] == "square":
                    val = base_vals[spec["inputs"][0]] ** 2
                else:
                    val = base_vals[spec["inputs"][0]] * base_vals[spec["inputs"][1]]
                x0[model["colnames"].index(spec["name"]) + 1] = val
        var = float(x0 @ model["xtx_inv"] @ x0) * model["mse"]
        return float(np.sqrt(max(var, 0.0)))

    model["se_predict_raw"] = se_predict_raw
    return predict_raw


def _lstsq(X, y):
    """OLS with intercept. Returns (beta, rank, rss, xtx_inv or None, X_with_intercept)."""
    n = X.shape[0]
    Xa = np.column_stack([np.ones(n), X])
    beta, _, rank, _ = np.linalg.lstsq(Xa, y, rcond=None)
    resid = y - Xa @ beta
    rss = float(resid @ resid)
    xtx_inv = None
    if rank == Xa.shape[1]:
        try:
            xtx_inv = np.linalg.inv(Xa.T @ Xa)
        except np.linalg.LinAlgError:
            xtx_inv = None
    return beta, rank, rss, xtx_inv, Xa


def _term_level_alias(term_name, alias_terms):
    """Alias chain at factor level: strip base-column decoration (F[lv]*G, A^2)."""
    out = set()
    for t in alias_terms or []:
        for part in t.split("*"):
            part = part.split("[")[0]
            if part.endswith("^2"):
                part = part[:-2]
            if part:
                out.add(part)
    out.discard(term_name)
    return sorted(out)


def _pure_error(X, y, rss_full, df_resid):
    """Pure-error df from replicate rows in design space (rounded coded rows)."""
    if X.shape[1] == 0:
        return 0, None, None, None, None, None
    keys = [tuple(np.round(row, 4)) for row in X]
    groups = defaultdict(list)
    for i, key in enumerate(keys):
        groups[key].append(float(y[i]))
    df_pe = sum(len(g) - 1 for g in groups.values() if len(g) > 1)
    if df_pe <= 0:
        return 0, None, None, None, None, None
    ss_pe = float(sum(((np.array(g) - np.mean(g)) ** 2).sum()
                      for g in groups.values() if len(g) > 1))
    df_lof = df_resid - df_pe
    ss_lof = rss_full - ss_pe
    f_lof = p_lof = None
    if df_lof and df_lof > 0 and ss_pe > 0:
        mse_pe = ss_pe / df_pe
        f_lof = (ss_lof / df_lof) / mse_pe
        p_lof = float(sps.f.sf(f_lof, df_lof, df_pe))
    return int(df_pe), float(max(ss_pe, 0.0)), int(max(df_lof, 0)), float(max(ss_lof, 0.0)), f_lof, p_lof


def _q_squared_hat(X, y, xtx_inv, model, h_diag=None):
    """LOO Q² via hat matrix (discloses twin-point leakage instead of hiding it)."""
    if xtx_inv is None or X.shape[1] == 0:
        return None, "xtx singular or empty design — Q² not available"
    Xa = np.column_stack([np.ones(X.shape[0]), X])
    if h_diag is None:
        h_diag = np.einsum("ij,jk,ik->i", Xa, xtx_inv, Xa)
        h_diag = np.clip(h_diag, 0.0, 0.999999)
    resid = y - Xa @ model["beta"]
    press = float(np.sum((resid / (1 - h_diag)) ** 2))
    tss = float(((y - y.mean()) ** 2).sum())
    if tss <= 0:
        return None, "zero variance response"
    note = ("hat-matrix LOO; replicate (twin) rows can leak — treat as optimistic bound"
            if model["df_pure_error"] and model["df_pure_error"] > 0 else None)
    return _r(1 - press / tss), note


RESIDUAL_PREVIEW_MAX = 2000  # persisted preview rows cap (equal-stride downsample)


def _residual_diagnostics(Xa, y, resid, h_diag, mse, row_index):
    """Hat-matrix diagnostics persisted per response (HTML residual quad input).

    Returns a JSON-ready dict; arrays are downsampled by an equal stride when
    n > RESIDUAL_PREVIEW_MAX so the HTML page never re-derives rows (row_index
    keeps the ORIGINAL dataframe positions, avoiding refit misalignment).
    """
    n, p_params = Xa.shape
    out = {"n": int(n), "n_params": int(p_params)}
    sigma_resid = float(np.sqrt(mse)) if (mse is not None and mse > 0) else None
    out["sigma_residual"] = _r(sigma_resid) if sigma_resid is not None else None
    out["n_high_residual_abs_gt3sigma"] = (
        int((np.abs(resid) > 3.0 * sigma_resid).sum()) if sigma_resid else None)
    if h_diag is not None:
        out["max_leverage"] = _r(float(h_diag.max()))
        cutoff = 2.0 * p_params / n if n > 0 else None
        out["leverage_cutoff_2p_over_n"] = _r(cutoff) if cutoff else None
        out["n_leverage_gt"] = int((h_diag > cutoff).sum()) if cutoff else None
        if mse is not None and mse > 0:
            cooks = (resid ** 2 / (p_params * mse)) * h_diag / (1.0 - h_diag) ** 2
            out["max_cooks_d"] = _r(float(cooks.max()))
        else:
            out["max_cooks_d"] = None
    else:
        out["max_leverage"] = None
        out["leverage_cutoff_2p_over_n"] = None
        out["n_leverage_gt"] = None
        out["max_cooks_d"] = None
    stride = 1
    if n > RESIDUAL_PREVIEW_MAX:
        stride = int(math.ceil(n / RESIDUAL_PREVIEW_MAX))
    idx = range(0, n, stride)
    out["preview_stride"] = stride
    out["preview_truncated"] = stride > 1
    out["residuals_preview"] = [
        {"row_index": int(row_index[i]), "y": _r(float(y[i])),
         "yhat": _r(float(y[i] - resid[i])), "resid": _r(float(resid[i]))}
        for i in idx]
    return out


def serialize_predictor(model):
    """JSON-safe predictor spec (model.json `predictor` block).

    Carries the coded base columns, kept term column specs and per-column beta
    so the report renderer can rebuild `predict_raw` from model.json alone —
    no refit, no divergent numbers.
    """
    base = {}
    for name, spec in model["base_specs"].items():
        info = spec["info"]
        entry = {"kind": spec["kind"], "factor": info["col"]}
        if spec["kind"] == "numeric_main":
            entry["mean"] = _r(info["mean"])
            entry["half_range"] = _r(info["half_range"])
        else:
            entry["level"] = str(spec["level"])
            entry["reference"] = str(info["levels"][-1])
        base[name] = entry
    terms = [{"term": t["name"],
              "specs": [{"name": s["name"], "fn": s["fn"], "inputs": list(s["inputs"])}]}
             for t, specs in model["kept_specs"] for s in specs]
    coefficients = {cname: _r(float(model["beta"][j + 1]))
                    for j, cname in enumerate(model["colnames"])}
    return {"base": base, "terms": terms, "coefficients": coefficients,
            "intercept": _r(float(model["beta"][0]))}


def rebuild_predictor(predictor):
    """Inverse of serialize_predictor: raw factor dict -> predicted y (or None)."""
    if not predictor:
        return None
    base = predictor["base"]
    terms = predictor["terms"]
    coefs = predictor["coefficients"]
    b0 = predictor["intercept"]

    def predict_raw(raw):
        bv = {}
        for name, spec in base.items():
            v = raw.get(spec["factor"])
            if spec["kind"] == "numeric_main":
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return None
                bv[name] = (float(v) - spec["mean"]) / spec["half_range"]
            else:
                sv = str(v) if v is not None else None
                if sv is None:
                    return None
                bv[name] = 1.0 if sv == str(spec["level"]) else (
                    -1.0 if sv == str(spec["reference"]) else 0.0)
        acc = b0
        for t in terms:
            for s in t["specs"]:
                if s["fn"] == "identity":
                    val = bv[s["inputs"][0]]
                elif s["fn"] == "square":
                    val = bv[s["inputs"][0]] ** 2
                else:
                    val = bv[s["inputs"][0]] * bv[s["inputs"][1]]
                acc += coefs[s["name"]] * val
        return float(acc)

    return predict_raw


def mde_coded(sigma, n, df, alpha=0.05, power=0.8):
    """Minimum detectable effect for a 2-level coded main effect (C8)."""
    if not sigma or sigma <= 0 or not n or n < 4 or not df or df < 1:
        return None
    return _r((sps.t.ppf(1 - alpha / 2, df) + sps.t.ppf(power, df)) * sigma * 2.0 / np.sqrt(n))


def _r(v):
    return round(float(v), 6) if v is not None else None
