"""closedloop_common — shared runtime primitives for the closed-loop skill suite
(industrial-sentinel / industrial-tuning-memory / industrial-optimizer-loop).

Single-source rules (plan: industrial-closedloop-skills-v1.md §2, v1.1):
- Enum literals live in `.claude/shared/schemas/closedloop_enums.json`;
  `enums.py` mirrors them for the python side. quality_gate.mjs of all three
  skills reads the JSON — never hardcode literals in gates or scripts.
- Dependency direction: closed-loop skills → closedloop_common → existing
  assets (doe-analyzer doestats, data-processor stats). Existing assets are
  NEVER modified to depend on this package.
"""

from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[1]
ENUMS_PATH = SHARED_DIR / "schemas" / "closedloop_enums.json"

_enum_cache = None


def load_enums():
    """Load closedloop_enums.json (cached)."""
    global _enum_cache
    if _enum_cache is None:
        import json

        with open(ENUMS_PATH, encoding="utf-8") as f:
            _enum_cache = json.load(f)
    return _enum_cache


def severity_levels():
    return list(load_enums()["severity"])


def autonomy_levels():
    return list(load_enums()["autonomy_levels"])


def evidence_grades():
    return list(load_enums()["evidence_grades"].keys())


def validate_literal(family: str, value, key=None) -> bool:
    """True iff `value` is an allowed literal in enums[family] (or enums[family][key])."""
    e = load_enums()
    node = e.get(family)
    if node is None:
        return False
    if key is not None:
        node = node.get(key, {})
    if isinstance(node, dict):
        return value in node
    return value in node
