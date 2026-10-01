"""Python mirror of closedloop_enums.json — the ONLY literals scripts may use.

Usage:
    from closedloop_common.enums import SEVERITY, AUTONOMY, SENTINEL_RULES
"""

import json
from pathlib import Path

_ENUMS_PATH = Path(__file__).resolve().parents[2] / "schemas" / "closedloop_enums.json"

with open(_ENUMS_PATH, encoding="utf-8") as _f:
    _E = json.load(_f)

CONTRACT_VERSIONS = _E["contract_versions"]

SEVERITY = list(_E["severity"])
URGENCY = list(_E["urgency"])
EVIDENCE_GRADES = list(_E["evidence_grades"].keys())
# v1.4: dispatch-autonomy enum retired from IDD scope — evidence grades are
# advisory strength; dispatch policy is decided by the AWS side exclusively.

SENTINEL_MODES = list(_E["sentinel"]["modes"])
SENTINEL_STATUS = list(_E["sentinel"]["status"])
SENTINEL_CHECK_TYPES = list(_E["sentinel"]["check_types"])
SENTINEL_RULES = list(_E["sentinel"]["rule_names"])
SENTINEL_NEXT_SKILL = _E["sentinel"]["suggested_next_skill"]
SENTINEL_SUPPRESSION = _E["sentinel"]["suppression"]
SENTINEL_BASELINE = _E["sentinel"]["baseline"]
SENTINEL_EXIT_CODES = _E["sentinel"]["exit_codes"]

TRIGGER_TYPES = list(_E["tuning_memory"]["trigger_types"])
ACTOR_TYPES = list(_E["tuning_memory"]["actor_types"])
OBSERVED_TRAJECTORIES = list(_E["tuning_memory"]["observed_trajectories"])
ATTRIBUTION_STATUS = list(_E["tuning_memory"]["attribution_status"])
NOT_ESTIMABLE_REASONS = list(_E["tuning_memory"]["not_estimable_reason_codes"])
EXPERIENCE_TYPES = list(_E["tuning_memory"]["experience_types"])
FEEDBACK_RESULTS = list(_E["tuning_memory"]["feedback_results"])
MATCH_SCOPES = list(_E["tuning_memory"]["match_scopes"])
RECOMMENDATION_STATUS = list(_E["tuning_memory"]["recommendation_status"])

OPTIMIZER_PHASES = list(_E["optimizer"]["phases"])
OPTIMIZER_METHODS = list(_E["optimizer"]["methods"])
OPTIMIZER_GOALS = list(_E["optimizer"]["goals"])
TRIAL_STATUS = list(_E["optimizer"]["trial_status"])
OPTIMIZER_NEXT_ACTIONS = list(_E["optimizer"]["next_actions"])
OPTIMIZER_CONSTANTS = _E["optimizer"]["constants"]

ACK_STATUSES = list(_E["ack"]["statuses"])
INBOX_TYPES = list(_E["inbox"]["types"])
