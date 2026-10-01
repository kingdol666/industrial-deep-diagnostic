"""Deterministic design detection (plan §2.5).

Rules, in order:
1. All factors discrete. C distinct combos == prod(levels) and balanced -> full_factorial.
2. Binary factors, C < 2^k, factor columns pairwise +-1-orthogonal -> fractional_factorial
   with deterministic generator recovery (defining relation word group, resolution,
   alias chains). Counting keys on DISTINCT COMBOS C, not run count N (replicated
   fractionals must not be misread as full factorials).
3. Center points >= 2 AND axial points >= 2k -> rsm_ccd (alpha from axial distance).
4. 3-level factors, every factor pair has all 9 combos equally often, no all-extreme
   corner rows -> rsm_bbd.
5. Every factor pair shows all level combos with equal frequency (strength 2) -> orthogonal_array.
6. All continuous, per-factor N-bin stratification occupancy ~1 per bin -> latin_hypercube.
7. Otherwise -> observational (conservative; caveats recorded).

Mixed designs (some discrete some continuous) fall through to observational unless
they hit rule 3/4 (RSM factors are continuous by construction).
"""

import itertools
import math

import numpy as np
import pandas as pd


MAX_RECOVERY_FACTORS = 16  # guard: 2^k subset enumeration


def _is_discrete(series, max_unique=12):
    vals = series.dropna().unique()
    return len(vals) <= max_unique


def _binary_pm1(levels, values):
    """Map a 2-level factor's values to +-1 (first level -> -1)."""
    lut = {levels[0]: -1.0, levels[1]: 1.0}
    return np.array([lut.get(v, np.nan) for v in values], dtype=float)


def _recover_generators(pm1_matrix, names):
    """Word-group recovery for a 2-level design.

    pm1_matrix: (n_combos, k) array of +-1. A word W (subset S) is in the defining
    relation iff the elementwise product of S's columns is the all-ones vector.
    Returns (defining_words, generators, resolution).
    """
    k = pm1_matrix.shape[1]
    if k < 3 or k > MAX_RECOVERY_FACTORS:
        return [], [], None
    words = []
    for r in range(2, k + 1):
        for combo in itertools.combinations(range(k), r):
            prod = np.ones(pm1_matrix.shape[0])
            for j in combo:
                prod = prod * pm1_matrix[:, j]
            if np.allclose(prod, 1.0, atol=1e-9):
                words.append(combo)
    if not words:
        return [], [], None
    # generators = minimal independent subset: a word joins the set only if it is
    # OUTSIDE the multiplicative span of the chosen ones. Product of two words =
    # symmetric difference of their factor sets (defining relation is a group).
    generators = []
    for w in sorted(words, key=len):
        fw = frozenset(w)
        span = {frozenset()}
        for g in generators:
            span |= {frozenset(s ^ g) for s in list(span)}
        if fw not in span:
            generators.append(w)
    resolution = min(len(w) for w in words)
    return words, generators, resolution


def _word_name(word, names):
    return "".join(names[j] for j in word)


def _alias_chains(k, words, names, max_order=2):
    """For effects of order <= max_order: aliases are S ^ W for W in defining relation."""
    chains = {}
    word_sets = [set(w) for w in words]
    for r in range(1, max_order + 1):
        for combo in itertools.combinations(range(k), r):
            s = set(combo)
            aliases = []
            for ws in word_sets:
                alias = s ^ ws
                if alias == s or not alias:
                    continue
                if len(alias) <= max_order or True:
                    aliases.append("".join(sorted((names[j] for j in alias))))
            chains[_word_name(combo, names)] = sorted(set(aliases))
    return chains


def _bin_occupancy(x, n_bins):
    """Fraction of n_bins equal-width bins holding exactly one sample."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size < n_bins:
        return 0.0
    lo, hi = float(x.min()), float(x.max())
    if hi - lo <= 0:
        return 0.0
    scaled = np.floor((x - lo) / (hi - lo) * n_bins)
    scaled[scaled >= n_bins] = n_bins - 1
    counts = np.bincount(scaled.astype(int), minlength=n_bins)
    return float((counts == 1).sum() / n_bins)


def _center_axial_counts(df, cols):
    """Count center rows, axial rows per factor, and axial alpha (coded units)."""
    X = df[cols].astype(float)
    lo, hi = X.min(), X.max()
    mid = (lo + hi) / 2.0
    rng = (hi - lo).replace(0, np.nan)
    coded = (X - mid) / rng * 2.0  # coded [-1, 1]
    arr = coded.to_numpy()
    is_center = np.all(np.abs(arr) <= 0.05, axis=1)
    n_center = int(is_center.sum())
    n_axial = 0
    alphas = []
    for j in range(len(cols)):
        extreme = np.abs(np.abs(arr[:, j]) - 1.0) <= 0.12
        others_center = np.all(np.abs(np.delete(arr, j, axis=1)) <= 0.05, axis=1)
        axial_rows = extreme & others_center & ~is_center
        n_axial += int(axial_rows.sum())
        vals = arr[axial_rows, j]
        if vals.size:
            alphas.extend(np.abs(vals).tolist())
    alpha = float(np.median(alphas)) if alphas else None
    return n_center, n_axial, alpha


def _discrete_detect(sub, combos, design, levels, notes, n):
    """Discrete-design rules on `sub` (mutates design/notes).

    Returns True when a discrete design type was classified: full factorial,
    fractional factorial (generator recovery), or orthogonal array.
    Guards: every factor <= 8 levels, product of levels <= 256, k >= 2 — without
    them a stripped continuous column (all combos unique once) reads as a
    "balanced full factorial".
    """
    k = len(levels)
    if k < 2 or any(len(v) > 8 for v in levels.values()):
        notes.append("discrete rules skipped (k<2 or a factor with >8 levels)")
        return False
    prod_levels = 1
    for c in levels:
        prod_levels *= len(levels[c])
    if prod_levels > 256:
        notes.append("discrete rules skipped (level product > 256)")
        return False
    n_distinct = int(combos.nunique())
    counts = combos.value_counts()
    min_c, max_c = int(counts.min()), int(counts.max())
    design["balance_ratio"] = round(min_c / max_c, 4) if max_c else None
    design["balanced"] = bool(min_c == max_c and min_c > 0)
    binary = all(len(levels[c]) == 2 for c in levels)
    design["n_distinct_combos"] = n_distinct

    if n_distinct == prod_levels and design["balanced"]:
        design["design_type"] = "full_factorial"
        design["mode"] = "designed"
        design["replicates"] = n // n_distinct if n_distinct else None
        notes.append(f"all {prod_levels} level combos present and balanced")
        return True

    if binary and n_distinct < 2 ** k:
        pm1 = np.column_stack([_binary_pm1(levels[c], sub[c].to_numpy()) for c in levels])
        combos_unique = sub.assign(_combo=combos.values).drop_duplicates("_combo")
        pm1_unique = np.column_stack(
            [_binary_pm1(levels[c], combos_unique[c].to_numpy()) for c in levels]
        )
        corr = np.corrcoef(pm1_unique, rowvar=False)
        off = corr[~np.eye(k, dtype=bool)]
        design["max_abs_factor_corr"] = round(float(np.nanmax(np.abs(off))), 4) if off.size else None
        if design["max_abs_factor_corr"] is not None and design["max_abs_factor_corr"] <= 0.05:
            words, generators, resolution = _recover_generators(pm1_unique, list(levels))
            if words:
                design["design_type"] = "fractional_factorial"
                design["mode"] = "designed"
                design["resolution"] = resolution
                design["defining_relation"] = [_word_name(w, list(levels)) for w in words]
                design["generators"] = [
                    f"{list(levels)[g[-1]]} = {''.join(list(levels)[j] for j in g[:-1])}"
                    for g in generators
                ]
                design["alias_chains"] = _alias_chains(k, words, list(levels))
                design["replicates"] = n // n_distinct if n_distinct else None
                notes.append(
                    f"generator recovery: defining relation {design['defining_relation']}, "
                    f"resolution {resolution}")
                if resolution is not None and resolution <= 4:
                    notes.append(
                        "resolution <= IV: aliased two-factor interactions are NOT causally "
                        "quotable; fold-over confirmation recommended")
                return True
            notes.append("binary orthogonal design but no defining relation found; falling through")
    elif binary:
        notes.append("binary design but factor columns not +-1-orthogonal")

    # orthogonal array (strength 2): every pair of columns has all combos equally often
    if prod_levels != n_distinct or not design["balanced"]:
        strength2 = True
        for c1, c2 in itertools.combinations(levels, 2):
            pair = sub[[c1, c2]].astype(str).apply(tuple, axis=1).value_counts()
            if len(pair) != len(levels[c1]) * len(levels[c2]) or pair.min() != pair.max():
                strength2 = False
                break
        if strength2 and k >= 3:
            design["design_type"] = "orthogonal_array"
            design["mode"] = "designed"
            notes.append("strength-2 orthogonality across all column pairs")
            notes.append(
                "mixed-level OA alias structure NOT fully disclosed in v1 — "
                "causal interpretation of effects restricted")
            return True
    return False


def detect_design(df, factor_cols, time_col=None):
    """Detect the experimental design. Returns the `design` block of data_profile.json."""
    notes = []
    cols = [c for c in factor_cols if c in df.columns]
    if not cols:
        return _observational("no factor columns identified", notes)
    n = len(df)
    sub = df[cols].dropna()
    if len(sub) < 3:
        return _observational("too few complete rows", notes)
    k = len(cols)
    discreteness = {c: _is_discrete(sub[c]) for c in cols}
    all_discrete = all(discreteness.values())
    levels = {c: sorted(sub[c].unique(), key=str) for c in cols if discreteness[c]}

    # --- counts ---
    combos = sub[cols].apply(lambda r: tuple(str(v) for v in r), axis=1)
    n_distinct = int(combos.nunique())
    design = {
        "n_runs": n,
        "n_factor_cols": k,
        "n_distinct_combos": n_distinct,
        "balanced": None,
        "balance_ratio": None,
        "max_abs_factor_corr": None,
        "resolution": None,
        "generators": [],
        "defining_relation": [],
        "alias_chains": {},
        "center_points": None,
        "axial_points": None,
        "alpha_axial": None,
        "replicates": None,
        "detection_notes": notes,
    }

    # --- orthogonality / balance (discrete) ---
    if all_discrete and _discrete_detect(sub, combos, design, levels, notes, n):
        return design
    elif not all_discrete:
        notes.append("continuous or mixed factors — discrete-design rules skipped")

    # --- RSM / LHS structure (runs on NUMERIC-DTYPE columns regardless of the
    # discrete level classification: a CCD's axial points make its factors look
    # "discrete" by uniqueness, but they are physically continuous) ---
    numeric_cols = [c for c in cols
                    if pd.api.types.is_numeric_dtype(sub[c])]
    if len(numeric_cols) == k and k >= 2:  # RSM/LHS need >= 2 factors; a single
        # continuous column over time is observational, never a 1-factor RSM
        n_center, n_axial, alpha = _center_axial_counts(sub, cols)
        design["center_points"] = n_center
        design["axial_points"] = n_axial
        design["alpha_axial"] = alpha
        if n_center >= 2 and n_axial >= 2 * k:
            design["design_type"] = "rsm_ccd"
            design["mode"] = "designed"
            notes.append(f"{n_center} center points + {n_axial} axial points (alpha={alpha})")
            return design

        # BBD: 3 levels, pairwise 9-combo balance, no all-extreme corners
        three_level = all(len(levels.get(c, [])) == 3 or _is_discrete(sub[c], 3) for c in cols)
        if three_level and k >= 2:
            lvl3 = {c: sorted(sub[c].unique(), key=str)[:3] for c in cols}
            ok_pairs = True
            for c1, c2 in itertools.combinations(cols, 2):
                pair = sub[[c1, c2]].astype(str).apply(tuple, axis=1).value_counts()
                if len(pair) != 9 or pair.min() != pair.max():
                    ok_pairs = False
                    break
            arr = np.column_stack([
                sub[c].map({v: i - 1 for i, v in enumerate(lvl3[c])}).to_numpy() for c in cols
            ])
            has_corner = bool(np.any(np.all(np.abs(arr) == 1, axis=1)))
            if ok_pairs and not has_corner:
                design["design_type"] = "rsm_bbd"
                design["mode"] = "designed"
                notes.append("3-level pairwise balance without factorial corners (BBD signature)")
                return design

        # LHS: 1-D stratification occupancy
        occ = [_bin_occupancy(sub[c].to_numpy(), min(n, 200)) for c in cols]
        mean_occ = float(np.mean([o for o in occ if o is not None])) if occ else 0.0
        if mean_occ >= 0.85:
            design["design_type"] = "latin_hypercube"
            design["mode"] = "designed"
            notes.append(f"LHS stratification occupancy {mean_occ:.2f} (>=0.85 threshold)")
            notes.append("space-filling design: effects estimated by regression, "
                         "no orthogonal contrast structure")
            return design
        notes.append(f"LHS occupancy only {mean_occ:.2f} (<0.85)")

    # --- pass 2: center-point stripping retry ---
    # A factorial augmented with center rows makes numeric columns 3-level, so
    # the prod(levels) check fails and mixed categorical+numeric designs (where
    # the RSM branch is skipped) would fall to observational. Strip rows where
    # ALL numeric factors sit at their midpoint and retry the discrete rules.
    num_for_centers = [c for c in cols if pd.api.types.is_numeric_dtype(sub[c])]
    if num_for_centers:
        mids = {c: (float(sub[c].min()) + float(sub[c].max())) / 2.0 for c in num_for_centers}
        rngs = {c: max(float(sub[c].max()) - float(sub[c].min()), 1e-12) for c in num_for_centers}
        is_center = np.ones(len(sub), dtype=bool)
        for c in num_for_centers:
            is_center &= (np.abs(sub[c].to_numpy(dtype=float) - mids[c]) / rngs[c]) <= 0.02
        n_center = int(is_center.sum())
        if n_center >= 2 and (len(sub) - n_center) >= max(6, 2 * k):
            sub2 = sub.loc[~is_center]
            levels2 = {c: sorted(sub2[c].unique(), key=str) for c in cols}
            design2 = dict(design)
            design2["detection_notes"] = []
            design2["center_points"] = n_center
            notes2 = []
            if _discrete_detect(sub2, sub2[cols].apply(lambda r: tuple(str(v) for v in r), axis=1),
                                design2, levels2, notes2, len(sub2)):
                design2["detection_notes"] = notes + notes2 + [
                    f"detected after stripping {n_center} center rows"]
                design2["center_points"] = n_center
                return design2
            notes.append(f"center-stripped retry did not match ({n_center} center rows)")

    return _observational("no designed-experiment signature matched", notes)


def _observational(reason, notes):
    notes.append(reason)
    return {
        "design_type": "observational",
        "mode": "observational",
        "resolution": None,
        "generators": [],
        "defining_relation": [],
        "alias_chains": {},
        "detection_notes": notes,
    }
