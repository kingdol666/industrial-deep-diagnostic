"""Enum-derived constants — the ONLY literal vocabulary sentinel scripts use.

Every severity / rule / check-type / mode / status literal referenced by the
logic is indexed through the mirrors built from
`.claude/shared/scripts/closedloop_common/enums.py`, which itself is a JSON
mirror of `.claude/shared/schemas/closedloop_enums.json`. Nothing here writes
a new literal into the contract; if the shared enum file renames a value the
KeyError below fails loudly instead of silently drifting, and the gate
(quality_gate.mjs S1) re-validates every emitted value against the JSON
source of truth.
"""

import sys
from pathlib import Path

# sentinelcore/ -> scripts/ -> industrial-sentinel/ -> skills/ -> .claude/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[5]
SHARED_SCRIPTS = REPO_ROOT / ".claude" / "shared" / "scripts"
SHARED_SCHEMAS = REPO_ROOT / ".claude" / "shared" / "schemas"
DP_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "industrial-data-processor" / "scripts"

if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from closedloop_common.enums import (  # noqa: E402
    CONTRACT_VERSIONS,
    SENTINEL_BASELINE,
    SENTINEL_CHECK_TYPES,
    SENTINEL_MODES,
    SENTINEL_NEXT_SKILL,
    SENTINEL_RULES,
    SENTINEL_STATUS,
    SENTINEL_SUPPRESSION,
    SEVERITY,
    URGENCY,
)

ALERT_CONTRACT_VERSION = CONTRACT_VERSIONS["sentinel_alert"]
BASELINE_CONTRACT_VERSION = CONTRACT_VERSIONS["sentinel_baseline"]

# Mirror dicts: enum literal -> enum literal (membership-checked vocabulary).
SEV = {s: s for s in SEVERITY}
SEV_RANK = {s: i for i, s in enumerate(SEVERITY)}
URG = {u: u for u in URGENCY}
RULE = {r: r for r in SENTINEL_RULES}
CHECK = {c: c for c in SENTINEL_CHECK_TYPES}
MODE = {m: m for m in SENTINEL_MODES}
STATUS = {s: s for s in SENTINEL_STATUS}
NS = {n: n for n in SENTINEL_NEXT_SKILL if n is not None}

# Suggested next skill per rule family (values are enum members).
NEXT_SKILL = {
    "spc": NS["industrial-diagnostician"],
    "regime": NS["industrial-diagnostician"],
    "multivariate": NS["industrial-diagnostician"],
    "window_projection": NS["industrial-doe-analyzer"],
    "baseline": None,
}

SUPPRESSION_DEFAULTS = dict(SENTINEL_SUPPRESSION)
BASELINE_DEFAULTS = dict(SENTINEL_BASELINE)

# Exit codes are keyed by decimal string in the enum file.
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_UNDETERMINED = 2
EXIT_GATE_FAIL = 3

# Nelson individuals-chart constants.
D2 = 1.128  # d2 for moving range of 2 — same-source convention as doe-analyzer

SCRIPT_VERSION = "1.0.0"
