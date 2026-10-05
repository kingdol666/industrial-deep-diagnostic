"""Incident-level aggregation of episode alerts (fieldtest-20261004 finding R2).

merge_by_key never swallows a persistent condition BY DESIGN: same-key
triggers farther apart than the suppression window re-alert, so one sustained
excursion on a 60-day autocorrelated watch surfaces as hundreds of `alerts`
entries (measured: 3,564). The `events` layer groups those entries into
digestible incidents WITHOUT touching the `alerts` contract — pure
post-process over the already-merged list, zero recomputation, deterministic
ordering (first appearance, like merge_by_key).

Grouping rule: consecutive same-(group, check_type, parameter) alerts whose
observed.index gap is within EVENT_GAP_ROWS belong to one event.
"""

from collections import OrderedDict

# Row-space image of 2h at the canonical 1 sample/minute cadence: a pause
# shorter than this between two same-key triggers is one continuing incident.
EVENT_GAP_ROWS = 120

_EVENT_FIELDS = ("family", "parameter", "group", "severity_peak",
                 "first_index", "last_index", "span_rows", "alert_count",
                 "rules", "max_abs_statistic", "suppression_key")


def make_event_id(generated_at, serial):
    """EVT-YYYYMMDDHHMMSS-nnn — same stamp convention as make_alert_id."""
    stamp = "".join((generated_at or "")[:19].replace("T", "").split("-")) \
        if generated_at else ""
    stamp = "".join(ch for ch in stamp if ch.isdigit())[:14] \
        .ljust(14, "0")
    return f"EVT-{stamp}-{serial:03d}"


def aggregate_events(alerts, generated_at=None, event_gap_rows=None):
    """Collapse an alert list into incident-level events.

    Returns a list of dicts (new list; inputs are not mutated):
      family, parameter, group          — the grouping key
      severity_peak                     — highest severity in the event
      first_index / last_index          — observed.index span
      span_rows                         — last_index - first_index
      alert_count                       — alerts folded into this event
      rules                             — unique rule_names, first-seen order
      max_abs_statistic                 — strongest |observed.statistic|
      suppression_key                   — the shared key
    """
    gap = EVENT_GAP_ROWS if event_gap_rows is None else event_gap_rows

    def _idx(a):
        idx = (a.get("observed") or {}).get("index")
        return idx if isinstance(idx, (int, float)) else None

    def _stat(a):
        st = (a.get("observed") or {}).get("statistic")
        return abs(st) if isinstance(st, (int, float)) else 0.0

    groups = OrderedDict()  # key -> [last_idx, event_dict]
    out = []
    for a in sorted(alerts, key=lambda x: (_idx(x) if _idx(x) is not None
                                           else -1)):
        key = (str(a.get("group")), str(a.get("check_type")),
               str(a.get("parameter")))
        idx = _idx(a)
        ev = groups.get(key)
        # last_index None (a prior index-less alert on this key) cannot host a
        # gap subtraction — start a fresh event instead of raising TypeError
        can_fold = ev is not None and idx is not None \
            and ev["last_index"] is not None
        if can_fold and idx - ev["last_index"] <= gap:
            ev["last_index"] = max(ev["last_index"], idx)
            ev["alert_count"] += 1
            if a.get("severity") == "critical":
                ev["severity_peak"] = "critical"
            elif a.get("severity") == "high" and \
                    ev["severity_peak"] != "critical":
                ev["severity_peak"] = "high"
            if a.get("rule_name") and a["rule_name"] not in ev["rules"]:
                ev["rules"].append(a["rule_name"])
            ev["max_abs_statistic"] = max(ev["max_abs_statistic"], _stat(a))
            continue
        ev = {
            "family": a.get("check_type"),
            "parameter": a.get("parameter"),
            "group": a.get("group"),
            "severity_peak": a.get("severity"),
            "first_index": idx,
            "last_index": idx,
            "span_rows": 0,
            "alert_count": 1,
            "rules": [a.get("rule_name")] if a.get("rule_name") else [],
            "max_abs_statistic": _stat(a),
            "suppression_key": a.get("suppression_key"),
        }
        groups[key] = ev
        out.append(ev)

    for ev in out:
        ev["span_rows"] = (ev["last_index"] - ev["first_index"]
                           if ev["first_index"] is not None
                           and ev["last_index"] is not None else 0)
    for i, ev in enumerate(out, 1):
        ev["event_id"] = make_event_id(generated_at, i)
    return [{k: ev[k] for k in _EVENT_FIELDS} | {"event_id": ev["event_id"]}
            for ev in out]
