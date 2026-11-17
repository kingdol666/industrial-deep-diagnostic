"""imacore — deterministic core of industrial-improvement-advisor.

ZERO new statistics: this package orchestrates family modules only.
  * core_stats  (industrial-data-processor)  — pearson / t-pvalue / full_lag_ccf
  * doestats    (industrial-doe-analyzer)    — bh_adjust / welch_delta_ci /
                                                effective_n / lag1_autocorr / ols_fit
  * lstcore     (industrial-line-stability-report) — table IO / sha256
  * tune_stats  (industrial-tuning-memory)   — action->effect attribution CLI

Submodules: _io (bootstrap+IO), objective, levers, evidence, chains, actions,
rank, charts.
"""

from ._io import (  # noqa: F401
    REUSE_STATUS, REPO_ROOT, SHARED_SCRIPTS, bh_adjust, core_stats, effective_n,
    lag1_autocorr, load_table, ols_fit, parse_time, pick_time_col, sha256_file,
    welch_delta_ci, write_json, CONSTANTS, GRADES, PRESCRIPTION_KINDS,
    EXCLUDED_LEVER_REASONS, NOT_ESTIMABLE_REASONS,
)
