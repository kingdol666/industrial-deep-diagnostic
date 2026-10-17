"""Initial DOE construction (Phase 3 / P3-2, contract §9 + §8.2 methods).

`build_design(spec, *, seed=None)` returns the contract-shaped dict:
`{contract_version, design_type, seed, run_table, coded, properties,
  randomization, notes}`.

Supported `spec.design_type`
---------------------------
`full_factorial`      product-of-levels grid (2..8 levels per factor)
`fractional_factorial` 2-level regular fraction, resolution-driven generator
                      selection (R=3/4/5, minimal runs, verified word group)
`rsm_ccd`             central composite: 2^k cube + 2k axial (alpha numeric or
                      "rotatable") + n_center
`rsm_bbd`             Box-Behnken: 2k(k-1) edge runs + n_center
`orthogonal_array`    strength-2 array from a small GF-built library (L9/L27 3-level,
                      L18 mixed, L8/L16 2-level)
`latin_hypercube`     centered (maximally stratified) LHS, best of N deterministic
                      restarts, mixed numeric/categorical supported
`d_optimal`           coordinate-exchange optimum over a full-factorial candidate
                      set (deterministic given `seed`), D-efficiency reported

Design decisions that a reader must know
----------------------------------------
- **Determinism**: every random path is driven by `numpy.random.default_rng(seed)`.
  `seed=None` means "no randomization": run_order is the natural generation order
  and `randomization.randomized=false` (a seed is required to randomize).
- **MDE convention** follows `effects_anova.mde_coded(sigma, n, df)` verbatim —
  it is the *coded contrast* MDE (the +1 vs -1 difference of means) for a
  unit-variance design: `(t_{1-a/2,df} + t_{power,df}) * sigma * 2 / sqrt(n)`.
  `properties.mde.value` therefore means "in units of sigma, on the coded
  contrast scale"; `mde_by_term` generalizes it to unequal leverage via
  `2 * se(beta_hat)` and reduces to the library value on orthogonal designs.
- **D-efficiency** = `det(X'X)^(1/p) / n` for the coded model matrix (p = number
  of model columns including the intercept); an orthogonal design of unit-norm
  columns attains 1.0 (det = n^p).
- **Round-trip self-check**: the produced run table is fed back through
  `doestats.design_detect.detect_design` and the recovered type is recorded in
  `properties.roundtrip` (DS-01 / DS-12). The check never raises: a detector
  error is recorded as `detector_error` so a first-round design is never lost.

CLI: `--spec FILE [--out FILE] [--seed N]` (`.csv` out = the run table only,
anything else = the full JSON payload).
"""

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats as sps

if __package__ in (None, ""):                 # `python <this file>` (CLI invocation)
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "doestats"                  # enables the relative imports below

CONTRACT_VERSION = "1.0"

DESIGN_TYPES = ("full_factorial", "fractional_factorial", "rsm_ccd", "rsm_bbd",
                "orthogonal_array", "latin_hypercube", "d_optimal")
MODELS = ("linear", "quadratic")

# What `detect_design` is expected to recover for each declared type. `d_optimal`
# has no detector class of its own (the frozen detector classifies by structure),
# so any designed classification is accepted and the recovered type is recorded.
EXPECTED_DETECTED = {
    "full_factorial": ["full_factorial"],
    "fractional_factorial": ["fractional_factorial"],
    "rsm_ccd": ["rsm_ccd"],
    "rsm_bbd": ["rsm_bbd"],
    "orthogonal_array": ["orthogonal_array"],
    "latin_hypercube": ["latin_hypercube"],
    "d_optimal": ["full_factorial", "fractional_factorial", "orthogonal_array",
                  "rsm_ccd", "rsm_bbd", "latin_hypercube"],
}

# Stable code emitted when a declared type cannot be recovered by the frozen
# detector. `rsm_bbd` is the only known case: design_detect's BBD rule demands
# that every factor pair carries all 9 level combinations *equally often*, but a
# Box-Behnken's edge combinations necessarily occur 2(k-2)x more often than its
# corner combinations (corner combos live only in their own pair block, edge
# combos are contributed by every other block). The rule is unsatisfiable for
# any BBD, so a canonical BBD is classified "observational" (or claimed by the
# strength-2 OA rule when its pair counts happen to be equal, which for a BBD
# requires 1 == 2(k-2) == n_center — impossible). Fixing it belongs to
# `design_detect.py`, which Phase 3 does not own.
GAP_BBD_RULE_UNSATISFIABLE = "design_detect_bbd_rule_unsatisfiable"

MAX_FRACTION_FACTORS = 16      # 2^k subset enumeration guard (word group)
MAX_SEARCH_NODES = 20000       # generator-search node budget (deterministic cap)
MAX_LEVELS = 8
MAX_CANDIDATES = 1024          # d_optimal candidate-set guard

# OA library: (runs, column level-vectors built by the GF construction below)
_OA_LIBRARY = (
    ("L4(2^3)", 2, 2), ("L8(2^7)", 3, 2), ("L16(2^15)", 4, 2),
    ("L9(3^4)", 2, 3), ("L27(3^13)", 3, 3), ("L18(2^1x3^7)", None, None),
)


# ------------------------------------------------------------------ utilities

def _fail(msg):
    raise ValueError(f"design_build: {msg}")


def _r(v, nd=10):
    if v is None:
        return None
    if isinstance(v, (int, np.integer)):
        return int(v)
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd)


def _eq(a, b, atol=1e-9):
    return abs(float(a) - float(b)) <= atol


# ------------------------------------------------------------------ factors

def _normalize_factors(spec):
    """spec.factors -> [{name, type, levels, low, high, center, unit}]."""
    raw = spec.get("factors")
    if not isinstance(raw, list) or len(raw) < 2:
        _fail("spec.factors must be a list with at least 2 entries")
    out = []
    seen = set()
    for f in raw:
        if not isinstance(f, dict) or not f.get("name"):
            _fail("every factor needs a 'name'")
        name = str(f["name"])
        if name in seen:
            _fail(f"duplicate factor '{name}'")
        seen.add(name)
        levels = f.get("levels")
        lo, hi = f.get("low"), f.get("high")
        ftype = f.get("type")
        if ftype is None:
            numeric_levels = (isinstance(levels, list) and levels
                              and all(isinstance(v, (int, float))
                                      and not isinstance(v, bool) for v in levels))
            ftype = "numeric" if (lo is not None and hi is not None) or numeric_levels \
                else "categorical"
        if ftype not in ("numeric", "categorical"):
            _fail(f"factor '{name}': type must be numeric|categorical, got {ftype!r}")
        if ftype == "numeric":
            if levels:
                lv = sorted({float(v) for v in levels})
            elif lo is not None and hi is not None:
                lv = sorted({float(lo), float(hi)})
            else:
                _fail(f"numeric factor '{name}' needs levels or low/high")
            if len(lv) < 2:
                _fail(f"numeric factor '{name}' needs at least 2 distinct levels")
            if len(lv) > MAX_LEVELS:
                _fail(f"numeric factor '{name}' has {len(lv)} levels (max {MAX_LEVELS})")
            out.append({"name": name, "type": "numeric", "levels": lv,
                        "low": lv[0], "high": lv[-1],
                        "center": (lv[0] + lv[-1]) / 2.0, "unit": f.get("unit")})
        else:
            if not levels or len(set(str(v) for v in levels)) < 2:
                _fail(f"categorical factor '{name}' needs >=2 distinct levels")
            lv = [str(v) for v in levels]
            if len(lv) > MAX_LEVELS:
                _fail(f"categorical factor '{name}' has {len(lv)} levels (max {MAX_LEVELS})")
            out.append({"name": name, "type": "categorical", "levels": lv,
                        "low": None, "high": None, "center": None,
                        "unit": f.get("unit")})
    return out


def _center_point(factors):
    return {f["name"]: (f["center"] if f["type"] == "numeric" else f["levels"][0])
            for f in factors}


# ------------------------------------------------------------------ coding

def _coded_row(raw, factors):
    """Coded value: numeric -> (x - mid)/half_range in [-1, 1]; categorical -> level."""
    row = {}
    for f in factors:
        v = raw.get(f["name"])
        if f["type"] == "numeric":
            hr = (f["high"] - f["low"]) / 2.0
            row[f["name"]] = _r((float(v) - f["center"]) / hr) if hr > 0 else 0.0
        else:
            row[f["name"]] = v
    return row


def _model_matrix(coded_rows, factors, model):
    """(X, term_names) on the coded matrix. Deviation coding for categoricals."""
    names = ["(intercept)"]
    cols = [np.ones(len(coded_rows))]
    num = [f for f in factors if f["type"] == "numeric"]
    for f in factors:
        if f["type"] == "numeric":
            cols.append(np.array([float(r[f["name"]]) for r in coded_rows]))
            names.append(f["name"])
        else:
            ref = f["levels"][-1]
            for lv in f["levels"][:-1]:
                cols.append(np.array([1.0 if str(r[f["name"]]) == lv else (
                    -1.0 if str(r[f["name"]]) == str(ref) else 0.0)
                    for r in coded_rows]))
                names.append(f"{f['name']}[{lv}]")
    if model == "quadratic":
        for f in num:
            cols.append(np.array([float(r[f["name"]]) ** 2 for r in coded_rows]))
            names.append(f"{f['name']}^2")
        for a, b in itertools.combinations([f["name"] for f in num], 2):
            cols.append(np.array([float(r[a]) * float(r[b]) for r in coded_rows]))
            names.append(f"{a}:{b}")
    X = np.column_stack(cols) if cols else np.zeros((len(coded_rows), 0))
    return X, names


# ------------------------------------------------------------------ word group

def _word_group(pm1, names, max_factors=MAX_FRACTION_FACTORS):
    """All non-empty factor subsets whose +-1 column product is the all-ones vector.

    This is the multiplicative kernels ("defining relation") of a 2-level design;
    its minimum word length is the resolution. Returns (words, resolution).
    """
    k = pm1.shape[1]
    if k < 2 or k > max_factors:
        return [], None
    words = []
    for r in range(2, k + 1):
        for combo in itertools.combinations(range(k), r):
            prod = np.ones(pm1.shape[0])
            for j in combo:
                prod = prod * pm1[:, j]
            if np.allclose(prod, 1.0, atol=1e-9):
                words.append(combo)
    if not words:
        return [], None
    return words, min(len(w) for w in words)


def _word_name(word, names):
    return "".join(names[j] for j in word)


def _generator_strings(words, names):
    """A minimal independent generator set, written as 'C = AB' strings."""
    generators = []
    for w in sorted(words, key=lambda x: (len(x), x)):
        span = {frozenset()}
        for g in generators:
            span |= {frozenset(s ^ frozenset(g)) for s in list(span)}
        if frozenset(w) not in span:
            generators.append(tuple(w))
    out = []
    for g in generators:
        if len(g) < 2:
            continue
        out.append(f"{names[g[-1]]} = " + "".join(names[j] for j in g[:-1]))
    return out


def _alias_chains(k, words, names, max_order=2):
    """Effects of order <= max_order -> their alias partners (S ^ W)."""
    word_sets = [set(w) for w in words]
    chains = {}
    for r in range(1, max_order + 1):
        for combo in itertools.combinations(range(k), r):
            s = set(combo)
            aliases = set()
            for ws in word_sets:
                alias = s ^ ws
                if alias == s or not alias:
                    continue
                aliases.add("".join(sorted(names[j] for j in alias)))
            chains[_word_name(combo, names)] = sorted(aliases)
    return chains


def _frac_ok(n_basics, subsets, resolution):
    """Exact check: does this generator set reach >= `resolution`?

    Word for generated factor i is {basics index m+i} U subset_i; the kernel is
    the multiplicative span of those words, so EVERY non-empty subset J of
    generators must give a word of length >= resolution. |word| = |J| +
    |symmetric difference of the subsets in J| (the m+i letters are distinct).
    """
    ng = len(subsets)
    for r in range(1, ng + 1):
        for J in itertools.combinations(range(ng), r):
            diff = set()
            for i in J:
                diff ^= set(subsets[i])
            if len(J) + len(diff) < resolution:
                return False
    return True


def _plan_fraction(k, resolution, max_runs=128):
    """Minimal-run 2-level fraction generator plan -> (m_basics, [subsets])."""
    if resolution not in (3, 4, 5):
        _fail(f"fractional_factorial resolution must be 3|4|5, got {resolution!r}")
    if k < 3:
        _fail("fractional_factorial needs at least 3 factors (use full_factorial)")
    for m in range(2, k + 1):
        p = k - m
        runs = 2 ** m
        if p <= 0:
            break
        if runs > max_runs:
            break
        if runs < k + 1:
            continue                      # cannot support k main effects + intercept
        cands = [s for r in range(2, m + 1) for s in itertools.combinations(range(m), r)]
        if resolution >= 4:
            cands = [s for s in cands if len(s) >= 3]
        if resolution >= 5:
            cands = [s for s in cands if len(s) >= 4]
        if len(cands) < p:
            continue
        plan = _search_generators(m, p, cands, resolution)
        if plan is not None:
            return m, plan
    _fail(f"no 2-level fraction with k={k} and resolution {resolution} "
          f"(<= {max_runs} runs) — lower the resolution or the factor count")


def _search_generators(m, p, cands, resolution):
    """Deterministic bounded DFS for p valid generator subsets."""
    nodes = [0]

    def dfs(chosen, start):
        if len(chosen) == p:
            return list(chosen) if _frac_ok(m, chosen, resolution) else None
        for i in range(start, len(cands)):
            nodes[0] += 1
            if nodes[0] > MAX_SEARCH_NODES:
                return None
            chosen.append(cands[i])
            if _frac_ok(m, chosen, resolution):
                got = dfs(chosen, i + 1)
                if got is not None:
                    return got
            chosen.pop()
        return None

    return dfs([], 0)


# ------------------------------------------------------------------ properties

def _vif(X, names):
    """VIF per non-intercept coded column (null when not estimable)."""
    if X.shape[1] < 2:
        return {}
    out = {}
    for j in range(1, X.shape[1]):
        others = [c for c in range(X.shape[1]) if c != j and c != 0]
        y = X[:, j]
        if len(others) == 0:
            out[names[j]] = 1.0
            continue
        A = np.column_stack([np.ones(X.shape[0])] + [X[:, c] for c in others])
        if np.linalg.matrix_rank(A) < A.shape[1]:
            out[names[j]] = None
            continue
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ beta
        tss = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - float(resid @ resid) / tss if tss > 0 else 0.0
        out[names[j]] = None if r2 >= 1.0 - 1e-12 else _r(1.0 / (1.0 - r2), 6)
    return out


def _d_efficiency(X):
    """{value, det, optimal_det, ratio, theorem_attainable, note}."""
    n, p = X.shape
    if p < 2 or n < p:
        return {"value": None, "det": None, "optimal_det": None, "ratio": None,
                "theorem_attainable": None,
                "note": "model not estimable (n < params or no predictors)"}
    try:
        sign, logdet = np.linalg.slogdet(X.T @ X)
    except np.linalg.LinAlgError:
        return {"value": None, "det": None, "optimal_det": None, "ratio": None,
                "theorem_attainable": None, "note": "singular X'X"}
    if sign <= 0:
        return {"value": None, "det": 0.0, "optimal_det": float(n) ** p, "ratio": 0.0,
                "theorem_attainable": None, "note": "singular X'X (det=0)"}
    det = float(math.exp(logdet))
    eff = det ** (1.0 / p) / n
    unit_norm = all(_eq(float(X[:, j] @ X[:, j]), n, atol=1e-6 * max(1.0, n))
                    for j in range(1, p))
    return {"value": _r(eff), "det": _r(det, 6), "optimal_det": _r(float(n) ** p, 6),
            "ratio": _r(det / (float(n) ** p)),
            "theorem_attainable": bool(unit_norm),
            "note": ("D-efficiency det(X'X)^(1/p)/n; 1.0 is attained by an orthogonal "
                     "design with unit-norm columns (det = n^p)" if unit_norm else
                     "some model columns are not unit-norm on this design — the "
                     "Hadamard bound n^p is not attainable; compare ratios across "
                     "candidates only")}


def _power_at(delta, se, t_a, df):
    """Two-sided t power for a coded contrast `delta` with standard error `se`.

    Guards against scipy's noncentral-t returning NaN at large noncentrality
    (a JSON artifact must never carry NaN/Infinity): falls back to the normal
    approximation.
    """
    if delta is None or se is None or se <= 0 or df < 1:
        return None
    ncp = float(delta) / float(se)
    try:
        v = float(sps.nct.sf(t_a, df, ncp) + sps.nct.cdf(-t_a, df, ncp))
    except (ValueError, OverflowError, RuntimeError):
        v = float("nan")
    if not np.isfinite(v):
        v = float(sps.norm.sf(t_a - ncp))
    return _r(v, 6)


def _power_and_mde(X, term_names, *, sigma=1.0, alpha=0.05, power_target=0.8,
                   power_delta=None):
    """MDE (coded contrast) + power at 2xMDE / 2-sigma / requested delta."""
    n, p = X.shape
    names = term_names[1:]
    df = n - int(np.linalg.matrix_rank(X)) if X.size else 0
    out = {"sigma": _r(sigma), "alpha": alpha, "power_target": power_target,
           "n": int(n), "df_resid": int(df), "method": "effects_anova.mde_coded"}
    mde = _mde_coded(sigma, n, df, alpha=alpha, power=power_target)
    out["value"] = mde
    out["note"] = ("coded-contrast MDE (+1 vs -1 difference of means) in sigma units; "
                   "effects_anova.mde_coded convention "
                   "(t_{1-a/2,df}+t_{power,df})*sigma*2/sqrt(n); per-term values "
                   "generalize it via 2*se(beta_hat) and reduce to it on orthogonal "
                   "designs")
    empty = {"by_term": {}, "min": None, "mean": None}
    if df < 1 or p < 2:
        out["by_term"] = {}
        out["power"] = {"at_2mde": dict(empty), "at_2_sigma": dict(empty),
                        "note": "no residual df — power/MDE not estimable"}
        return out
    try:
        xtx_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        out["by_term"] = {}
        out["power"] = {"at_2mde": dict(empty), "at_2_sigma": dict(empty),
                        "note": "X'X singular — per-term values unavailable"}
        out["note"] += "; X'X singular — per-term values unavailable"
        return out
    t_a = float(sps.t.ppf(1 - alpha / 2.0, df))
    t_p = float(sps.t.ppf(power_target, df))
    by_term, se_of = {}, {}
    for j, nm in enumerate(names, start=1):
        v = float(xtx_inv[j, j])
        if v <= 0 or not np.isfinite(v):
            by_term[nm] = None
            se_of[nm] = None
            continue
        se_of[nm] = sigma * math.sqrt(v)
        by_term[nm] = _r((t_a + t_p) * 2.0 * se_of[nm])
    out["by_term"] = by_term
    deltas = {"at_2mde": (2 * mde if mde is not None else None),
              "at_2_sigma": 2.0 * sigma}
    if power_delta is not None:
        deltas["at_requested"] = float(power_delta)
    power = {}
    for label, delta in deltas.items():
        vals, per_term = [], {}
        for nm in names:
            v = _power_at(delta, se_of.get(nm), t_a, df)
            per_term[nm] = v
            if v is not None:
                vals.append(v)
        power[label] = {"delta_coded_contrast": _r(delta), "by_term": per_term,
                        "min": _r(min(vals), 6) if vals else None,
                        "mean": _r(float(np.mean(vals)), 6) if vals else None}
    power["note"] = ("coded contrast delta = high - low level difference; "
                     "at_2_sigma = a 2*sigma contrast (sigma=1 -> 2 coded units)")
    out["power"] = power
    return out


def _mde_coded(sigma, n, df, alpha=0.05, power=0.8):
    """effects_anova.mde_coded when importable (contract: reuse, don't restate)."""
    try:
        from .effects_anova import mde_coded as _lib
        return _lib(sigma, n, df, alpha=alpha, power=power)
    except Exception:  # pragma: no cover - library always present in-repo
        if not sigma or sigma <= 0 or not n or n < 4 or not df or df < 1:
            return None
        return _r((float(sps.t.ppf(1 - alpha / 2, df)) + float(sps.t.ppf(power, df)))
                  * sigma * 2.0 / math.sqrt(n))


# ------------------------------------------------------------------ OA library

def _gf_columns(m, q):
    """Columns of the standard OA(3^m / 2^m) from GF(q) linear forms."""
    if q == 2:
        vecs = [v for v in itertools.product(range(2), repeat=m) if any(v)]
    else:
        seen, vecs = set(), []
        for v in itertools.product(range(q), repeat=m):
            if not any(v):
                continue
            norm = [x for x in v if x != 0][0]
            inv = pow(norm, q - 2, q)
            canonical = tuple((x * inv) % q for x in v)
            if canonical not in seen:
                seen.add(canonical)
                vecs.append(v)
    rows = []
    for pt in itertools.product(range(q), repeat=m):
        rows.append([float(sum(a * b for a, b in zip(v, pt)) % q) for v in vecs])
    return np.array(rows)


def _oa_columns(k, q):
    """Smallest GF-built OA with >= k columns and >= k+1 rows. Levels are 0..q-1."""
    m = 2
    while m <= 4:
        cols = _gf_columns(m, q)
        if cols.shape[1] >= k and cols.shape[0] >= k + 1:
            return cols[:, :k], f"L{cols.shape[0]}({q}^{cols.shape[1]})"
        m += 1
    return None, None


def _l18_mixed(k):
    """L18(2^1 x 3^7): one 2-level column + seven 3-level columns."""
    base = _gf_columns(2, 3)                      # 9 rows x 4 cols
    rows = []
    for i in range(9):
        for half in (0, 1):
            r = [float(half)]
            for j in range(4):
                r.append(base[i, j] if half == 0 else (base[i, j] + 1) % 3 + 3)
            rows.append(r)
    arr = np.array(rows)
    # fold the second 3-level block (values 3..5) into 0..2 to keep 7 columns
    arr[:, 5:] = (arr[:, 5:] - 3.0) % 3.0
    if k > arr.shape[1]:
        return None
    return arr[:, :k], "L18(2^1x3^7)"


# ------------------------------------------------------------------ designs

def _rows_from_combos(combos, factors):
    return [dict(zip([f["name"] for f in factors], c)) for c in combos]


def _build_full_factorial(factors):
    combos = list(itertools.product(*[f["levels"] for f in factors]))
    return _rows_from_combos(combos, factors), []


def _build_fractional(factors, spec):
    k = len(factors)
    res = spec.get("resolution")
    if res is None:
        res = 4
    m, subsets = _plan_fraction(k, int(res))
    names = [f["name"] for f in factors]
    basic = list(itertools.product([-1.0, 1.0], repeat=m))
    rows = []
    for c in basic:
        raw = {}
        for j in range(m):
            f = factors[j]
            raw[f["name"]] = f["high"] if c[j] > 0 else f["low"]
        for i, S in enumerate(subsets):
            f = factors[m + i]
            p = 1.0
            for j in S:
                p *= c[j]
            raw[f["name"]] = f["high"] if p > 0 else f["low"]
        rows.append(raw)
    return rows, [f"2^({k}-{k - m})", f"resolution_requested={res}"]


def _build_ccd(factors, spec):
    k = len(factors)
    alpha = spec.get("alpha", "rotatable")
    n_center = spec.get("n_center")
    n_center = 3 if n_center is None else int(n_center)
    if n_center < 0:
        _fail("rsm_ccd n_center must be >= 0")
    cube = 2 ** k
    if alpha == "rotatable":
        a = cube ** 0.25
    else:
        try:
            a = float(alpha)
        except (TypeError, ValueError):
            _fail(f"rsm_ccd alpha must be 'rotatable' or numeric, got {alpha!r}")
    if a < 0.5:
        _fail("rsm_ccd alpha must be >= 0.5 (1.0 = face-centred, 'rotatable' = "
              "(number of cube points)^(1/4))")
    rows = []
    for c in itertools.product([-1.0, 1.0], repeat=k):
        rows.append({f["name"]: f["high"] if c[j] > 0 else f["low"]
                     for j, f in enumerate(factors)})
    for j, f in enumerate(factors):
        for s in (-1.0, 1.0):
            raw = {g["name"]: g["center"] for g in factors}
            raw[f["name"]] = f["center"] + s * a * (f["high"] - f["low"]) / 2.0
            rows.append(raw)
    for _ in range(n_center):
        rows.append(_center_point(factors))
    n_axial = 2 * k
    if n_center < 2:
        _fail("rsm_ccd needs n_center >= 2 (design_detect CCD rule: >=2 centre + "
              ">=2k axial points)")
    return rows, [f"alpha={_r(a, 6)}", f"n_axial={n_axial}", f"n_center={n_center}"]


def _build_bbd(factors, spec):
    k = len(factors)
    if k < 3:
        _fail("rsm_bbd needs at least 3 factors (2-factor Box-Behnken is the "
              "full 3^2 grid — use full_factorial)")
    n_center = spec.get("n_center")
    # 1 centre point is the *statistically minimal* choice and the only one that
    # keeps every level pair equally frequent; larger pure-error blocks are the
    # caller's explicit choice (disclosed in notes).
    n_center = 1 if n_center is None else int(n_center)
    if n_center < 1:
        _fail("rsm_bbd n_center must be >= 1")
    rows = []
    for i, j in itertools.combinations(range(k), 2):
        for a, b in itertools.product([-1.0, 1.0], repeat=2):
            raw = {f["name"]: f["center"] for f in factors}
            raw[factors[i]["name"]] = factors[i]["high"] if a > 0 else factors[i]["low"]
            raw[factors[j]["name"]] = factors[j]["high"] if b > 0 else factors[j]["low"]
            rows.append(raw)
    for _ in range(n_center):
        rows.append(_center_point(factors))
    return rows, [f"n_edge={2 * k * (k - 1)}", f"n_center={n_center}"]


def _build_oa(factors, spec):
    """Library strength-2 array.

    A 2-level strength-2 array IS a regular resolution-III fraction (Hadamard
    rows), so it is built through the same generator machinery — this keeps the
    defining relation sign-consistent (an arbitrary GF sign convention can land
    on I = -ABC, which carries no recoverable word). >=3-level arrays come from
    the GF library and are classified `orthogonal_array` by design_detect.
    """
    runs = spec.get("runs")
    lvl_counts = {len(f["levels"]) for f in factors}
    if lvl_counts == {2}:
        m, subsets = _plan_fraction(len(factors), 3)
        basic = list(itertools.product([-1.0, 1.0], repeat=m))
        rows = []
        for c in basic:
            raw = {factors[j]["name"]: (factors[j]["high"] if c[j] > 0 else factors[j]["low"])
                   for j in range(m)}
            for i, S in enumerate(subsets):
                f = factors[m + i]
                p = 1.0
                for j in S:
                    p *= c[j]
                raw[f["name"]] = f["high"] if p > 0 else f["low"]
            rows.append(raw)
        label = f"L{2 ** m}(2^{len(factors)})"
        note = ("2-level strength-2 array == regular resolution-III fraction; "
                "design_detect classifies it as fractional_factorial")
        return rows, [f"array={label}", note]
    if all(lc in (2, 3) for lc in lvl_counts) and len(factors) <= 8 \
            and 2 in lvl_counts and 3 in lvl_counts:
        cols, label = _l18_mixed(len(factors))
    else:
        cols, label = _oa_columns(len(factors), 3)
    if cols is None or (runs is not None and len(cols) < int(runs)):
        _fail(f"orthogonal_array: no library array for k={len(factors)} with the "
              f"requested levels ({sorted(lvl_counts)}) — supply explicit levels or "
              f"fewer factors")
    rows = []
    for r in range(cols.shape[0]):
        rows.append({f["name"]: f["levels"][int(cols[r, j]) % len(f["levels"])]
                     for j, f in enumerate(factors)})
    return rows, [f"array={label}"]


def _build_lhs(factors, spec, rng):
    n = spec.get("runs")
    n = max(int(n) if n is not None else 0, 2, 2 * len(factors))
    restarts = int(spec.get("lhs_restarts", 8))
    jitter = float(spec.get("lhs_jitter", 0.0) or 0.0)
    if not (0.0 <= jitter < 0.5):
        _fail("lhs_jitter must be in [0, 0.5)")
    num = [f for f in factors if f["type"] == "numeric"]
    best, best_state = None, None
    for restart in range(max(1, restarts)):
        r = np.random.default_rng(int(rng.integers(1 << 30)))
        perm = {f["name"]: r.permutation(n) for f in num}
        offs = {f["name"]: r.uniform(0.5 - jitter, 0.5 + jitter, n) for f in num}
        pts = []
        for i in range(n):
            raw = {}
            for f in factors:
                if f["type"] == "numeric":
                    u = (perm[f["name"]][i] + offs[f["name"]][i]) / n
                    raw[f["name"]] = f["low"] + u * (f["high"] - f["low"])
                else:
                    lv = f["levels"]
                    raw[f["name"]] = lv[(i + restart) % len(lv)]
            pts.append(raw)
        md = _min_distance(pts, num)
        if best is None or md > best:
            best, best_state = md, pts
    return best_state or [], [f"n={n}", f"min_distance={_r(best, 6)}",
                              f"jitter={jitter}", f"restarts={max(1, restarts)}",
                              "centred strata (maximally stratified LHS: 1-D "
                              "stratification occupancy 1.0, design_detect LHS rule "
                              "0.85 threshold); set spec.lhs_jitter>0 to randomize "
                              "inside the strata"]


def _min_distance(pts, num):
    if not num or len(pts) < 2:
        return 0.0
    A = np.array([[float(p[f["name"]]) for f in num] for p in pts])
    span = np.ptp(A, axis=0)
    A = (A - A.min(0)) / np.where(span == 0, 1.0, span)
    d = np.inf
    for i, j in itertools.combinations(range(len(A)), 2):
        d = min(d, float(np.linalg.norm(A[i] - A[j])))
    return 0.0 if not np.isfinite(d) else d


def _build_d_optimal(factors, spec, rng):
    k = len(factors)
    model = spec.get("model") or "linear"
    if model == "quadratic" and any(f["type"] == "numeric" and len(f["levels"]) < 3
                                    for f in factors):
        _fail("d_optimal with model='quadratic' needs >=3 levels per numeric factor")
    cand_combos = list(itertools.product(*[f["levels"] for f in factors]))
    if len(cand_combos) > MAX_CANDIDATES:
        _fail(f"d_optimal candidate set has {len(cand_combos)} points "
              f"(>{MAX_CANDIDATES}) — reduce levels/factors")
    cand_raw = _rows_from_combos(cand_combos, factors)
    cand_coded = [_coded_row(r, factors) for r in cand_raw]
    Xc, names = _model_matrix(cand_coded, factors, model)
    p = Xc.shape[1]
    n = spec.get("runs")
    n = int(n) if n is not None else min(len(cand_raw), max(p, 2 * k))
    if n < p:
        _fail(f"d_optimal runs={n} < model parameters={p}")
    if n > len(cand_raw):
        _fail(f"d_optimal runs={n} exceeds the {len(cand_raw)} candidate points")
    restarts = max(1, int(spec.get("d_restarts", 6)))
    idx = _coordinate_exchange(Xc, n, rng, restarts)
    rows = [dict(cand_raw[i]) for i in idx]
    return rows, [f"criterion=D", f"model={model}", f"n_params={p}",
                  f"candidates={len(cand_raw)}", f"restarts={restarts}",
                  f"model_terms={','.join(names[1:])}"]


def _coordinate_exchange(Xc, n, rng, restarts):
    """Deterministic (diagnostic seed only) coordinate exchange for max |X'X|.

    Swaps candidate points in/out by the rank-2 determinant update; the accepted
    det is always recomputed exactly (update drift never decides a swap).
    Ties break on the lower candidate index -> deterministic for a given start.
    """
    ncand, p = Xc.shape
    if rng is None:
        starts = [list(range(n))]
    else:
        starts = []
        for _ in range(restarts):
            starts.append(list(rng.choice(ncand, size=n, replace=False)))
    best_idx, best_det = None, -1.0
    for start in starts:
        idx = list(start)
        X = Xc[idx]
        det = _det_xtx(X)
        for _pass in range(20):
            improved = False
            for pos in range(n):
                old = idx[pos]
                xo = Xc[old]
                det_wo, inv_wo = _det_without(X, xo)
                if det_wo is None or inv_wo is None:
                    continue
                best_local, best_ci = det, old
                for ci in range(ncand):
                    if ci in idx and ci != old:
                        continue
                    xc = Xc[ci]
                    q = float(xc @ (inv_wo @ xc))
                    if q <= -1.0 + 1e-12:
                        continue
                    cand_det = det_wo * (1.0 + q)
                    if cand_det > best_local + 1e-12:
                        best_local, best_ci = cand_det, ci
                if best_ci != old:
                    idx[pos] = best_ci
                    X = Xc[idx]
                    det = _det_xtx(X)
                    improved = True
            if not improved:
                break
        if det > best_det + 1e-12:
            best_idx, best_det = list(idx), det
    return sorted(best_idx) if best_idx is not None else list(range(n))


def _det_xtx(X):
    try:
        sign, logdet = np.linalg.slogdet(X.T @ X)
    except np.linalg.LinAlgError:
        return 0.0
    if sign <= 0:
        return 0.0
    return float(math.exp(logdet))


def _det_without(X, xo):
    """det(X'X - xo xo') and the matching inverse (Sherman-Morrison)."""
    A = X.T @ X
    try:
        Ainv = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        return None, None
    c = float(xo @ (Ainv @ xo))
    if 1.0 - c <= 1e-12:
        return None, None
    det_wo = _det_xtx(X) * (1.0 - c)
    A1 = A - np.outer(xo, xo)
    try:
        A1inv = np.linalg.inv(A1)
    except np.linalg.LinAlgError:
        return None, None
    return det_wo, A1inv


# ------------------------------------------------------------------ assembly

def _assign_runs(rows, factors, spec, seed):
    """run_id / design_point_id / replicate group / block / run_order."""
    names = [f["name"] for f in factors]
    key_of = lambda r: tuple(str(r[n]) for n in names)

    point_ids, seen = {}, {}
    for r in rows:
        key = key_of(r)
        if key not in point_ids:
            point_ids[key] = f"dp-{len(point_ids) + 1:02d}"
        seen.setdefault(key, []).append(r)

    n = len(rows)
    blocks_spec = spec.get("blocks")
    if blocks_spec is None or blocks_spec is False:
        labels, policy = [None] * n, "single_block"
    elif isinstance(blocks_spec, (list, tuple)) and not blocks_spec:
        labels, policy = [None] * n, "single_block"
    else:
        if isinstance(blocks_spec, int) and not isinstance(blocks_spec, bool):
            labels_list = [f"block-{i + 1}" for i in range(int(blocks_spec))]
        elif isinstance(blocks_spec, (list, tuple)):
            labels_list = [str(b) for b in blocks_spec]
        else:
            _fail("spec.blocks must be an int count or a non-empty list of labels")
        if len(labels_list) < 1:
            _fail("spec.blocks produced no block labels")
        labels = [labels_list[i % len(labels_list)] for i in range(n)]
        policy = f"round_robin_by_design_point({len(labels_list)})"

    randomize = bool(spec.get("randomize", True)) and seed is not None
    order = list(range(n))
    if randomize:
        rng = np.random.default_rng(int(seed))
        if labels[0] is None:
            order = list(rng.permutation(n).tolist())
        else:
            order = []
            for label in sorted(set(labels)):
                members = [i for i in range(n) if labels[i] == label]
                order.extend(rng.permutation(members).tolist())
        policy += " + randomized_within_block"
    else:
        policy += " + natural_order"

    records = []
    for seq, i in enumerate(order, start=1):
        r = rows[i]
        key = key_of(r)
        rec = {"run_id": f"doerun-{seq:02d}", "design_point_id": point_ids[key],
               "run_order": seq, "block": labels[i]}
        grp = seen[key]
        if len(grp) > 1:
            rec["replicate_group"] = f"rg-{point_ids[key][3:]}"
            is_center = all(f["type"] != "numeric"
                            or _eq(float(r[f["name"]]), float(f["center"]))
                            for f in factors)
            rec["replicate_kind"] = "center" if is_center else "replicate"
        for nm in names:
            rec[nm] = r[nm]
        records.append(rec)
    return records, policy, randomize


def _roundtrip(records, factors, declared):
    """Feed the run table back through detect_design and classify the outcome."""
    expected = list(EXPECTED_DETECTED[declared])
    if declared == "orthogonal_array" and all(len(f["levels"]) == 2 for f in factors):
        expected = ["orthogonal_array", "fractional_factorial"]
    out = {"declared": declared, "expected_detected_types": expected,
           "detected_type": None, "detected_mode": None, "match": None,
           "detector_error": None, "gap": None, "note": None}
    try:
        import pandas as pd
        from .design_detect import detect_design
        df = pd.DataFrame([{f["name"]: rec[f["name"]] for f in factors} for rec in records])
        det = detect_design(df, [f["name"] for f in factors])
        out["detected_type"] = det.get("design_type")
        out["detected_mode"] = det.get("mode")
        out["match"] = det.get("design_type") in expected
    except Exception as exc:            # a detector crash must not lose the design
        out["detector_error"] = f"{type(exc).__name__}: {exc}"
        out["match"] = None
        out["note"] = ("round-trip check could not complete (detector raised) — the "
                       "design itself is unaffected")
        return out
    if out["match"]:
        out["note"] = "declared design type recovered by design_detect"
        return out
    if declared == "rsm_bbd":
        out["gap"] = GAP_BBD_RULE_UNSATISFIABLE
        out["note"] = (
            "design_detect's BBD rule requires every factor pair to carry all 9 level "
            "combinations equally often, but a Box-Behnken's edge pairs occur "
            "2(k-2)x more often than its corner pairs (corners appear only in their "
            "own pair block, edges in every other block) — the rule is unsatisfiable "
            "for any BBD, and the strength-2 OA rule shadows it whenever pair counts "
            "do match. Fixing the rule is a design_detect.py change (not owned by "
            "P3-2); the emitted design is a statistically canonical Box-Behnken.")
    elif declared == "d_optimal":
        out["note"] = ("design_detect has no d_optimal class; the recovered structural "
                       "type is recorded above (expected for a D-optimal design)")
    else:
        out["note"] = (f"design_detect classified the table as "
                       f"{out['detected_type']!r}; expected {expected}")
    return out


def _seed_rng(seed, offset):
    """Construction RNG. `seed=None` still yields a fixed construction seed (0)
    so the design is deterministic; only run-order randomization needs a seed."""
    return np.random.default_rng((0 if seed is None else int(seed)) + offset)


def build_design(spec, *, seed=None):
    """Build a deterministic initial design (contract §9)."""
    if not isinstance(spec, dict):
        _fail("spec must be a dict")
    design_type = spec.get("design_type")
    if design_type not in DESIGN_TYPES:
        _fail(f"design_type must be one of {list(DESIGN_TYPES)}, got {design_type!r}")
    if seed is not None and not isinstance(seed, (int, np.integer)):
        _fail("seed must be an integer or None")
    seed = None if seed is None else int(seed)
    factors = _normalize_factors(spec)
    notes = []
    extra = []

    if design_type == "full_factorial":
        rows, extra = _build_full_factorial(factors)
    elif design_type == "fractional_factorial":
        rows, extra = _build_fractional(factors, spec)
    elif design_type == "rsm_ccd":
        if any(f["type"] != "numeric" for f in factors):
            _fail("rsm_ccd needs numeric factors")
        rows, extra = _build_ccd(factors, spec)
    elif design_type == "rsm_bbd":
        if any(f["type"] != "numeric" for f in factors):
            _fail("rsm_bbd needs numeric factors")
        rows, extra = _build_bbd(factors, spec)
    elif design_type == "orthogonal_array":
        rows, extra = _build_oa(factors, spec)
    elif design_type == "latin_hypercube":
        rows, extra = _build_lhs(factors, spec, _seed_rng(seed, 991))
    else:  # d_optimal
        rows, extra = _build_d_optimal(factors, spec, _seed_rng(seed, 313))

    reps = int(spec.get("replicates") or 1)
    if reps < 1:
        _fail("replicates must be >= 1")
    if reps > 1:
        rows = rows * reps
        notes.append(f"replicates={reps} — the point list is repeated {reps}x "
                     f"(randomization spreads the copies)")

    records, policy, randomized = _assign_runs(rows, factors, spec, seed)
    coded = [dict({"run_id": rec["run_id"]}, **_coded_row(rec, factors)) for rec in records]

    model = spec.get("model") or "linear"
    if model not in MODELS:
        _fail(f"model must be one of {list(MODELS)}, got {model!r}")
    X, names = _model_matrix([_coded_row(r, factors) for r in rows], factors, model)
    rank = int(np.linalg.matrix_rank(X)) if X.size else 0
    df_resid = len(rows) - rank
    sigma = float(spec.get("sigma") or 1.0)

    props = {
        "resolution": None,
        "defining_relation": [],
        "generators": [],
        "alias_chains": {},
        "vif": {},
        "power": {},
        "mde": {},
        "d_efficiency": _d_efficiency(X),
        "n_runs": len(records),
        "n_distinct_combos": len({tuple(str(r[f["name"]]) for f in factors) for r in rows}),
        "n_params": int(X.shape[1]),
        "df_resid": int(df_resid),
        "model": model,
        "model_terms": names,
        "strength": None,
        "min_distance": None,
    }
    props["vif"] = _vif(X, names)
    power_block = _power_and_mde(X, names, sigma=sigma,
                                 power_delta=spec.get("power_delta"))
    props["power"] = power_block.pop("power", {})
    props["mde"] = power_block

    pm1 = None
    if all(f["type"] == "numeric" and len(f["levels"]) == 2 for f in factors) \
            and len(factors) <= MAX_FRACTION_FACTORS:
        lut = {f["name"]: {f["low"]: -1.0, f["high"]: 1.0} for f in factors}
        coded_pm1, ok = [], True
        for rec in records:
            row = []
            for f in factors:
                v = lut[f["name"]].get(float(rec[f["name"]]))
                if v is None:      # not a 2-level point (e.g. CCD axial row)
                    ok = False
                    break
                row.append(v)
            if not ok:
                break
            coded_pm1.append(row)
        if ok and coded_pm1:
            pm1 = np.array(coded_pm1)
    if pm1 is not None:
        words, resolution = _word_group(pm1, [f["name"] for f in factors])
        props["resolution"] = resolution
        props["defining_relation"] = [_word_name(w, [f["name"] for f in factors])
                                      for w in words]
        props["generators"] = _generator_strings(words, [f["name"] for f in factors])
        props["alias_chains"] = _alias_chains(len(factors), words,
                                              [f["name"] for f in factors]) if words else {}
    if design_type == "orthogonal_array":
        props["strength"] = 2
    if design_type == "latin_hypercube":
        props["min_distance"] = _r(_min_distance(rows, [f for f in factors
                                                        if f["type"] == "numeric"]), 6)

    if design_type == "fractional_factorial" and props["resolution"] is not None \
            and props["resolution"] < int(spec.get("resolution") or 4):
        _fail(f"generator search produced resolution {props['resolution']} < requested "
              f"{spec.get('resolution')}")
    if design_type == "rsm_bbd":
        notes.append("n_center defaults to 1 (the statistically minimal pure-error "
                     "block that also keeps every level pair balanced); pass "
                     "n_center explicitly for a larger centre block")
    notes.extend(extra)

    out = {
        "contract_version": CONTRACT_VERSION,
        "design_type": design_type,
        "seed": seed,
        "factors": [{"name": f["name"], "type": f["type"], "levels": f["levels"],
                     "low": f["low"], "high": f["high"], "unit": f["unit"]}
                    for f in factors],
        "run_table": records,
        "coded": coded,
        "properties": props,
        "randomization": {"randomized": bool(randomized), "seed": seed,
                          "block_policy": policy},
        "notes": notes,
    }
    out["properties"]["roundtrip"] = _roundtrip(records, factors, design_type)
    if not randomized:
        out["notes"].append(
            "seed=None or randomize=false: run_order is the natural generation order "
            "and randomization.randomized=false (pass --seed to randomize)")
    return out


# ------------------------------------------------------------------ CLI

def _load_spec(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"SPEC_INVALID_JSON: {path}: {exc}") from exc


def _write_out(path, payload):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() == ".csv":
        cols = list(payload["run_table"][0].keys())
        lines = [",".join(cols)]
        for rec in payload["run_table"]:
            lines.append(",".join("" if rec.get(c) is None else str(rec.get(c))
                                  for c in cols))
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                     encoding="utf-8")
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic DOE design builder (P3-2)")
    ap.add_argument("--spec", required=True, help="JSON spec file")
    ap.add_argument("--out", default=None, help="output file (.csv = run table only)")
    ap.add_argument("--seed", type=int, default=None, help="randomization seed")
    ap.add_argument("--json", action="store_true", help="print the payload to stdout")
    args = ap.parse_args(argv)
    payload = build_design(_load_spec(args.spec), seed=args.seed)
    if args.out:
        print(f"[design_build] wrote {_write_out(args.out, payload)}")
    if args.json or not args.out:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    rt = payload["properties"]["roundtrip"]
    print(f"[design_build] {payload['design_type']}: n_runs="
          f"{payload['properties']['n_runs']} detected={rt['detected_type']} "
          f"match={rt['match']} gap={rt['gap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
