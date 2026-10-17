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

v1.1 additive layer (P2-3 / contract §5.1): `detect_design_hull` +
`hull_mask` (design-region containment: coded box, analytic CCD star hull, or the
convex hull of the run points via cached Qhull facets) and `leverage_stats`
(h_i = x_i'(X'X)^-1 x_i with the classic 2p/n threshold). Nothing here is called
by `detect_design` or by the legacy window entry points.
"""

import itertools
import math

import numpy as np
import pandas as pd


MAX_RECOVERY_FACTORS = 16  # guard: 2^k subset enumeration


def _is_discrete(series, max_unique=12):
    vals = series.dropna().unique()
    return len(vals) <= max_unique


def _ordered_levels(values):
    """Ascending order that is numeric when the values allow it.

    `sorted(..., key=str)` is fine for counting, but WRONG for the +-1 coding used
    by the BBD rule: with string order, 100.0 sorts after 110.0 and the design's
    center level would be coded as an extreme. Always prefer numeric ordering.
    """
    vals = list(values)
    try:
        return sorted(vals)
    except TypeError:
        return sorted(vals, key=str)


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
    gen_sets = []
    for w in sorted(words, key=lambda w: (len(w), w)):
        fw = frozenset(w)
        span = {frozenset()}
        for g in gen_sets:
            span |= {s ^ g for s in list(span)}
        if fw not in span:
            generators.append(w)
            gen_sets.append(fw)
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

        # BBD before CCD on purpose: in coded units a Box-Behnken's edge rows look
        # exactly like a CCD's axial rows (one factor extreme, the rest centered),
        # so the CCD rule would swallow them. The BBD signature below distinguishes
        # them: a BBD has no cube-corner row and runs all four corners of every
        # factor pair, while a CCD's cube corners carry every factor at once.
        # A CCD is 5-level per factor, so `three_level` is False for it.
        three_level = all(len(levels.get(c, [])) == 3 or _is_discrete(sub[c], 3) for c in cols)
        if three_level and k >= 3:
            lvl3 = {c: _ordered_levels(sub[c].unique())[:3] for c in cols}
            arr = np.column_stack([
                sub[c].map({v: i - 1 for i, v in enumerate(lvl3[c])}).to_numpy() for c in cols
            ])
            n_extreme = np.sum(np.abs(arr) == 1, axis=1)
            # A Box-Behnken run varies exactly one PAIR: 0 factors at an extreme
            # (center run) or exactly 2. One extreme is a CCD axial run; three or
            # more is a factorial corner or a full 3-level row. Requiring "0 or 2"
            # is what separates a BBD from an L9-type orthogonal array, whose
            # all-low / all-high rows carry k extremes.
            pair_structure = bool(np.all((n_extreme == 0) | (n_extreme == 2)))
            has_center_rows = bool(np.any(n_extreme == 0))
            corners_ok = True
            corner_detail = []
            for i, j in itertools.combinations(range(k), 2):
                mask = (np.abs(arr[:, i]) == 1) & (np.abs(arr[:, j]) == 1)
                idx = np.where(mask)[0]
                if idx.size == 0:
                    corners_ok = False
                    break
                counts = {}
                for r in idx:
                    key = (int(arr[r, i]), int(arr[r, j]))
                    counts[key] = counts.get(key, 0) + 1
                if len(counts) != 4 or len(set(counts.values())) != 1:
                    corners_ok = False
                    break
                corner_detail.append(len(idx))
            if pair_structure and has_center_rows and corners_ok:
                design["design_type"] = "rsm_bbd"
                design["mode"] = "designed"
                design["center_points"] = int(np.sum(n_extreme == 0))
                design["axial_points"] = 0  # BBD has no axial runs by construction
                notes.append(
                    "Box-Behnken signature: every run varies exactly one factor pair "
                    f"(0 or 2 extremes), all four corners per pair run "
                    f"{corner_detail[0] if corner_detail else 1}x, "
                    f"{design['center_points']} center run(s)")
                return design

        if n_center >= 2 and n_axial >= 2 * k:
            design["design_type"] = "rsm_ccd"
            design["mode"] = "designed"
            notes.append(f"{n_center} center points + {n_axial} axial points (alpha={alpha})")
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
        # A 2^2 factorial augmented with centre rows has only 4 non-centre rows;
        # requiring 6 made every 2-factor factorial+centre design fall through to
        # observational. The stripped table still has to be a real factorial grid
        # (>= 2^k, at least 4), so the retry itself remains conservative.
        if n_center >= 2 and (len(sub) - n_center) >= max(4, 2 * k):
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


# ==================================================================== v1.1 hull (P2-3)
# Design region / hull + leverage. Additive: nothing here is called by
# detect_design or by the legacy window entry points.

HULL_TYPES = ("box", "ccd_star", "convex_hull", "unbounded")
HULL_ATOL = 1e-6
_HULL_CHUNK = 2048         # query rows evaluated per pass (memory bound)
_HULL_FACET_BLOCK = 512    # facet rows applied per pass (memory bound)
# Exact convex-hull containment is only affordable inside these bounds (Qhull
# facets grow steeply with dimension/point count). Outside them the coded box is
# used instead, with the downgrade disclosed in design_region.note (confidence
# stays "medium": for a space-filling design the declared factor ranges ARE the
# region of interest, corners simply were not all run).
HULL_MAX_DIM = 8
HULL_MAX_BUILD_POINTS = 320

# Designs whose coded runs fill the whole observed box: the design region is the
# box spanned by the factor ranges (standard "region of interest").
_BOX_DESIGNS = {"full_factorial", "fractional_factorial", "orthogonal_array"}
_BOX_CONFIDENCE = {"full_factorial": "high", "fractional_factorial": "medium",
                   "orthogonal_array": "medium"}
# Space-filling / edge designs: the region covered is the convex hull of the run
# points, NOT the enclosing box (their corners were never run).
_HULL_DESIGNS = {"rsm_bbd", "latin_hypercube"}


def coded_columns(df, cols):
    """Coded matrix on the observed range: (x - mid) / half_range, [-1, 1].

    Identical convention to `effects_anova.build_factor_info` (C1), so coded
    coordinates here are directly comparable with model x0 vectors.
    """
    X = df[cols].astype(float)
    lo, hi = X.min(), X.max()
    mid = (lo + hi) / 2.0
    rng = (hi - lo).replace(0, np.nan)
    return ((X - mid) / (rng / 2.0)).to_numpy(), {c: (float(lo[c]), float(hi[c]))
                                                  for c in cols}


def _distinct_abs(coded, atol=1e-4):
    vals = np.abs(np.asarray(coded, dtype=float)).ravel()
    vals = vals[np.isfinite(vals)]
    vals.sort()
    out = []
    for v in vals:
        if not out or v - out[-1] > atol:
            out.append(float(v))
    return out


def detect_design_hull(df, factor_cols, design_block=None, mode="designed"):
    """Design-region hull descriptor (contract §5.1 `design_region.hull`).

    Returns {hull, factor_order, coded_bounds, axial_alpha, cube_corner_coded,
    design_hull_confidence, label, note}.

    Rules (documented, P2-3):
    - factorial / orthogonal-array designs -> "box" (the coded factor ranges are
      the region of interest; every corner of a full factorial was run).
    - CCD -> "ccd_star": the hull is conv(cube corners, axial points, centre).
      Coded coordinates use the observed range (axial points at +-1, cube corners
      at +-C<1, C = the corner magnitude in coded units), so the analytic test is
      `sum(|x_i/C|^2_face`) — see `hull_mask`.
    - BBD / LHS -> "convex_hull": containment by the Delaunay triangulation of the
      coded run points (their enclosing box corners were never run).
    - anything else (observational, non-numeric factors, too few rows) ->
      "unbounded" with confidence "low".

    `design_hull_confidence` is capped at "medium" for space-filling designs
    (LHS/BBD) and "low" for unbounded (plan §6.2 DS-11 / P2-3).
    """
    design_block = design_block or {}
    dtype = design_block.get("design_type")
    cols = [c for c in factor_cols if c in df.columns
            and pd.api.types.is_numeric_dtype(df[c])]
    out = {"hull": "unbounded", "factor_order": list(cols), "coded_bounds": {},
           "axial_alpha": None, "cube_corner_coded": None,
           "design_hull_confidence": "low", "label": dtype, "note": None}
    if mode != "designed" or not cols:
        out["note"] = ("no designed region (observational mode or no numeric "
                       "factors) — the hull is the observed range")
        return out
    sub = df[cols].dropna()
    if len(sub) < 3:
        out["note"] = "too few complete numeric rows for a hull"
        return out
    sub = sub.drop_duplicates()
    coded, bounds = coded_columns(sub, cols)
    out["coded_bounds"] = {c: {"min": bounds[c][0], "max": bounds[c][1],
                               "coded_min": -1.0, "coded_max": 1.0} for c in cols}
    out["_coded_points"] = coded  # internal: used by hull_mask(convex_hull)
    if dtype in _BOX_DESIGNS:
        out["hull"] = "box"
        out["design_hull_confidence"] = _BOX_CONFIDENCE.get(dtype, "medium")
        if dtype == "fractional_factorial":
            out["note"] = ("fractional factorial: the coded factor ranges define "
                           "the region of interest; unrun box corners are inside "
                           "the box (confidence capped at medium)")
        return out
    if dtype in _HULL_DESIGNS:
        out["hull"] = "convex_hull"
        out["design_hull_confidence"] = "medium"
        exact = hull_test_affordable(len(sub), len(cols))
        out["hull_exact"] = bool(exact)
        if exact:
            out["note"] = (f"{dtype}: design region = convex hull of the run points "
                           f"(enclosing box corners were never run); confidence capped "
                           f"at medium")
        else:
            out["note"] = (f"{dtype}: exact convex-hull containment not evaluated "
                           f"(k={len(cols)} > {HULL_MAX_DIM} or {len(sub)} run rows > "
                           f"{HULL_MAX_BUILD_POINTS} — Qhull facet cost); the coded "
                           f"factor-range box is used, unrun corners are NOT verified "
                           f"to be outside — treat extrapolation risk as elevated")
        return out
    if dtype == "rsm_ccd":
        absvals = _distinct_abs(coded)
        nonzero = [v for v in absvals if v > 0.02]
        corner_mask = np.abs(coded) > 0.02
        corner_rows = corner_mask.all(axis=1)
        cube_c = float(np.median(np.abs(coded[corner_rows]))) if corner_rows.any() else None
        if cube_c is not None and cube_c < 0.999:
            out["hull"] = "ccd_star"
            out["cube_corner_coded"] = round(cube_c, 6)
            out["axial_alpha"] = round(1.0 / cube_c, 6)
            out["design_hull_confidence"] = "high"
            out["note"] = (f"CCD: cube corners at +-{round(cube_c, 4)} coded, axial "
                           f"points at +-1 coded -> axial alpha {round(1.0 / cube_c, 4)} "
                           f"in cube units")
            # sanity: the detected levels must contain both axial and corner levels
            if not (nonzero and nonzero[-1] >= 0.999):
                out["hull"] = "box"
                out["note"] += " (axial level not at the observed range — box hull)"
                out["design_hull_confidence"] = "medium"
        else:
            out["hull"] = "box"
            out["design_hull_confidence"] = "medium"
            out["note"] = "CCD detected but no cube-corner level — box hull"
        return out
    out["hull"] = "convex_hull" if len(sub) > len(cols) else "box"
    out["design_hull_confidence"] = "medium"
    out["note"] = f"unclassified designed type {dtype!r} — convex-hull containment"
    return out


def _ccd_star_mask(coded, cube_c):
    """Analytic CCD hull test (documented choice — the box-face pyramid rule).

    Why this rule and not `sum((x_i/alpha)^2) <= 1`: the ellipsoid rule is the
    ROTATABLE-DESIGN sphere; for the actually-run CCD it is wrong. In coded units
    (axial points at +-1, cube corners at +-C) the sphere form `sum((x/alpha)^2)<=1`
    rejects the executed cube corners: for k=3, alpha=1.682 the corners give
    3/alpha^2 = 1.06 > 1. The convex hull of the executed points is instead
    cube u pyramids (u = x/C): `max|u_i| <= alpha` AND, when exactly one
    coordinate |u_j| > 1, `|u_i| <= (alpha - |u_j|)/(alpha - 1)` for all i != j.
    This accepts all 2^k cube corners (all |u_i| = 1), all 2k axial points
    (apex: the limit collapses to 0) and the centre, and rejects the unrun box
    corners at +-alpha in every coordinate — exactly the executed design.
    """
    u = coded / cube_c
    absu = np.abs(u)
    alpha = 1.0 / cube_c
    inside = absu.max(axis=1) <= alpha + HULL_ATOL
    j = np.argmax(absu, axis=1)
    a_j = absu[np.arange(len(u)), j]
    out = inside.copy()
    over = inside & (a_j > 1.0 + HULL_ATOL)
    if alpha > 1.0 + HULL_ATOL and over.any():
        limit = (alpha - a_j[over]) / (alpha - 1.0)
        others = np.delete(absu[over], j[over][:, None], axis=1)
        if others.shape[1]:
            out[over] = np.all(others <= limit[:, None] + HULL_ATOL, axis=1)
        out[over] &= (limit >= -HULL_ATOL)
    return out


def hull_test_affordable(n_points, k):
    """Can the exact convex-hull containment be built cheaply? (documented bound)"""
    return k <= HULL_MAX_DIM and n_points <= HULL_MAX_BUILD_POINTS


def _hull_equations(desc, pts):
    """Facet half-space rows [n | c] of conv(pts), cached in the descriptor.

    scipy's convention is `n·x + c <= 0` for every point of the convex hull (the
    facet normal `n` is unit length and `-c` is the signed distance from the
    origin). None when the point set is degenerate.
    """
    cached = desc.get("_hull_equations")
    if cached is not None:
        return cached
    try:
        from scipy.spatial import ConvexHull
        eq = ConvexHull(np.unique(np.round(pts, 9), axis=0)).equations
    except Exception:
        eq = None
    desc["_hull_equations"] = eq
    return eq


def hull_mask(desc, coded):
    """Boolean mask: is each coded point inside the design hull?

    `coded` is (m, k) with columns in `desc["factor_order"]` on the observed-range
    coding (see `coded_columns`). Points that cannot be tested (no hull, singular
    triangulation) fall back to True and the caller keeps the low-confidence
    disclosure in `design_region.design_hull_confidence`.

    convex_hull implementation (documented, P2-3 + RG-05): the convex hull is
    converted ONCE into its facet half-spaces (`n·x + c <= 0`, Qhull, cached in the
    descriptor) and tested by matrix products. This replaces the Delaunay
    `find_simplex` containment, which is 15x slower at k=8 (12s vs 0.8s per 4k
    queries) because every query walks the whole triangulation. The facet test
    runs BLOCK-WISE with early elimination: each pass keeps only the points that
    survived every facet so far, so the dominant cost is the first pass over the
    most constraining facets. Facets are ordered by ascending `c` (the plane
    furthest from the origin cuts most candidates first); the order only affects
    speed, never the result, and both stages share one tolerance.
    """
    coded = np.asarray(coded, dtype=float)
    if coded.size == 0:
        return np.ones(coded.shape[0], dtype=bool)
    hull = desc.get("hull")
    if hull == "unbounded":
        return np.ones(len(coded), dtype=bool)
    if hull == "box":
        return (np.abs(coded) <= 1.0 + HULL_ATOL).all(axis=1)
    if hull == "ccd_star" and desc.get("cube_corner_coded"):
        return _ccd_star_mask(coded, float(desc["cube_corner_coded"]))
    pts = np.asarray(desc.get("_coded_points"), dtype=float)
    k = coded.shape[1]
    if pts is None or pts.ndim != 2 or pts.shape[1] != k or len(pts) <= k:
        return np.ones(len(coded), dtype=bool)
    if desc.get("hull_exact") is False or not hull_test_affordable(len(pts), k):
        # disclosed downgrade (see HULL_MAX_* above): coded box, not the exact hull
        return (np.abs(coded) <= 1.0 + HULL_ATOL).all(axis=1)
    eq = _hull_equations(desc, pts)
    if eq is None or not len(eq):
        return np.ones(len(coded), dtype=bool)
    A, off = eq[:, :k], eq[:, k]
    order = np.lexsort((np.arange(len(eq)), off))   # deterministic, speed only
    A, off = A[order], off[order]
    m = len(coded)
    out = np.zeros(m, dtype=bool)
    for start in range(0, m, _HULL_CHUNK):
        blk = coded[start:start + _HULL_CHUNK]
        alive = np.arange(len(blk))
        for f0 in range(0, len(eq), _HULL_FACET_BLOCK):
            if not len(alive):
                break
            vals = blk[alive] @ A[f0:f0 + _HULL_FACET_BLOCK].T \
                + off[f0:f0 + _HULL_FACET_BLOCK]
            alive = alive[~np.any(vals > HULL_ATOL, axis=1)]
        if len(alive):
            out[start + alive] = True
    return out


def leverage_stats(model, df, factor_cols=None):
    """Hat-matrix leverage over the fitted design rows.

    h_i = x_i'(X'X)^-1 x_i with x_i the coded design row (intercept included);
    the classic screening threshold is 2p/n (p = parameters, n = fitted rows).
    Returns {max_leverage, mean_leverage, leverage_threshold, n_exceed,
    n_params, n_rows, leverage_per_point}.
    """
    from . import effects_anova as ea

    xtx_inv = model.get("xtx_inv")
    cols = model.get("colnames") or []
    empty = {"max_leverage": None, "mean_leverage": None, "leverage_threshold": None,
             "n_exceed": None, "n_params": None, "n_rows": 0,
             "leverage_per_point": None}
    if xtx_inv is None or not cols or df is None or not len(df):
        return empty
    X = ea.coded_design_matrix(model, df.to_dict("records"))
    good = np.isfinite(X).all(axis=1)
    X = X[good]
    n, ncols = X.shape
    if n == 0 or ncols == 0:
        return empty
    p = ncols + 1
    Xa = np.column_stack([np.ones(n), X])
    h = np.einsum("ij,jk,ik->i", Xa, xtx_inv, Xa)
    h = np.clip(h, 0.0, 1.0)
    thr = 2.0 * p / n
    return {"max_leverage": float(h.max()), "mean_leverage": float(h.mean()),
            "leverage_threshold": float(thr), "n_exceed": int((h > thr).sum()),
            "n_params": int(p), "n_rows": int(n),
            "leverage_per_point": [float(v) for v in h]}

