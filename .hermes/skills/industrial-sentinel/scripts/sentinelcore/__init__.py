"""sentinelcore — deterministic check engine of industrial-sentinel.

Pure-analysis production sentinel: watch (batch) + fast_screen (incremental).
Every statistic is computed by numpy/scipy code in this package (zero LLM,
zero network). The agent only reads the emitted artifacts and may append
Chinese `interpretation` notes; numeric fields are never agent-authored.

Module map:
  _io         data loading + inline path containment + column identification
  spc         Nelson rules R1/R2/R3/R5/R6 (sigma = MRbar/1.128)
  projection  window drift projection (last-25% vs first-25% steady slope)
  regime_map  regime/steady mapping via in-process import of the
              data-processor fast detector + pure-Python fallback
  robust      robust z (0.6745*(x-median)/MAD) + Mahalanobis (Cholesky
              forward substitution, Wilson-Hilferty chi-square) with the
              four-level degradation ladder
  suppress    anti-storm: same-key merge, hysteresis downgrade,
              post-change-point quiet zone
"""

from sentinelcore._constants import (  # noqa: F401
    ALERT_CONTRACT_VERSION,
    BASELINE_CONTRACT_VERSION,
    BASELINE_DEFAULTS,
    CHECK,
    D2,
    EXIT_FINDINGS,
    EXIT_GATE_FAIL,
    EXIT_OK,
    EXIT_UNDETERMINED,
    MODE,
    NEXT_SKILL,
    NS,
    RULE,
    SCRIPT_VERSION,
    SEV,
    SEV_RANK,
    STATUS,
    SUPPRESSION_DEFAULTS,
    URG,
)

VERSION = SCRIPT_VERSION

__all__ = ["VERSION"]
