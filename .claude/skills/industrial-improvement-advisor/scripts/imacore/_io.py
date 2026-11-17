"""imacore._io — repo bootstrap, family-module imports, JSON/table IO.

Every reuse import is guarded: a missing leg flips REUSE_STATUS[leg] to a
failure string and the calling module records a degradation instead of
crashing (method_notes §7 degradation chain).

Artifact writes delegate to the family's contained strict writer
(`ontology_prepare_common.write_json_strict`: repo-containment check +
allow_nan=False) — no ad-hoc open() in this package.
"""

import json
import math
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
# repo/.claude/skills/industrial-improvement-advisor/scripts/imacore/_io.py
REPO_ROOT = _THIS.parents[5]
SKILLS_DIR = _THIS.parents[3]
SHARED_SCRIPTS = _THIS.parents[4] / "shared" / "scripts"

_PATHS = {
    "shared": SHARED_SCRIPTS,
    "material": SKILLS_DIR / "industrial-data-processor" / "scripts",
    "doe": SKILLS_DIR / "industrial-doe-analyzer" / "scripts",
    "lst": SKILLS_DIR / "industrial-line-stability-report" / "scripts",
    "tuning": SKILLS_DIR / "industrial-tuning-memory" / "scripts",
}
for _p in _PATHS.values():
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

REUSE_STATUS = {}


def _leg(name, fn):
    try:
        value = fn()
        REUSE_STATUS[name] = "ok"
        return value
    except Exception as exc:  # pragma: no cover - degraded path exercised by tests
        REUSE_STATUS[name] = f"unavailable: {type(exc).__name__}: {exc}"
        return None


core_stats = _leg("core_stats", lambda: __import__(
    "stats.core_stats", fromlist=["core_stats"]))
_doe_util = _leg("doestats", lambda: __import__(
    "doestats._stats_util", fromlist=["_stats_util"]))
_lst_io = _leg("lstcore_io", lambda: __import__(
    "lstcore._io", fromlist=["_io"]))
_enums = _leg("closedloop_enums", lambda: __import__(
    "closedloop_common.enums", fromlist=["enums"]))
_oc = _leg("ontology_common", lambda: __import__(
    "ontology_prepare_common", fromlist=["ontology_prepare_common"]))
tune_stats = _leg("tune_stats", lambda: __import__("tune_stats"))
_spurious = _leg("anti_spurious", lambda: __import__(
    "stats.anti_spurious", fromlist=["anti_spurious"]))

bh_adjust = getattr(_doe_util, "bh_adjust", None)
welch_delta_ci = getattr(_doe_util, "welch_delta_ci", None)
effective_n = getattr(_doe_util, "effective_n", None)
lag1_autocorr = getattr(_doe_util, "lag1_autocorr", None)
ols_fit = getattr(_doe_util, "ols_fit", None)

load_table = getattr(_lst_io, "load_table", None)
pick_time_col = getattr(_lst_io, "pick_time_col", None)
parse_time = getattr(_lst_io, "parse_time", None)
sha256_file = getattr(_lst_io, "sha256_file", None)
find_data_file = getattr(_lst_io, "find_data_file", None)

_CONST_DEFAULTS = {
    "min_analysis_rows": 50,
    "min_relation_points": 10,
    "dose_bins_min": 5,
    "dose_bins_max": 8,
    "dose_bin_min_n": 8,
    "min_effect_r": 0.2,
    "fdr_q": 0.05,
    "monotonicity_alpha": 0.05,
    "extrapolation_coded_distance": 0.8,
    "max_actions": 12,
    "html_c_shown": 6,
    "a_grade_sentinel": 3,
}
CONSTANTS = dict(_CONST_DEFAULTS)
if _enums is not None:
    CONSTANTS.update(getattr(_enums, "IMPROVEMENT_CONSTANTS", {}) or {})

GRADES = getattr(_enums, "IMPROVEMENT_GRADES", ["A", "B", "C"])
PRESCRIPTION_KINDS = getattr(_enums, "IMPROVEMENT_PRESCRIPTION_KINDS",
                             ["data", "experiment", "dead_time", "ontology"])
EXCLUDED_LEVER_REASONS = getattr(_enums, "IMPROVEMENT_EXCLUDED_LEVER_REASONS",
                                 ["reverse_causality", "no_variance",
                                  "insufficient_data", "user_excluded"])
NOT_ESTIMABLE_REASONS = getattr(_enums, "IMPROVEMENT_NOT_ESTIMABLE_REASONS",
                                ["lever_no_variance", "no_significant_relation",
                                 "window_truncated", "confound_unresolvable",
                                 "reuse_leg_unavailable"])


def write_json(path, payload):
    """Artifact writes go through the family's contained strict writer
    (repo-containment check + allow_nan=False; no ad-hoc open() here)."""
    if _oc is None:
        raise RuntimeError("JSON writer unavailable: ontology_prepare_common "
                           "import failed — cannot write artifacts")
    return str(_oc.write_json_strict(path, payload))


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def finite(value, ndigits=6):
    """Round for JSON, keep None for non-finite."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return round(v, ndigits)
