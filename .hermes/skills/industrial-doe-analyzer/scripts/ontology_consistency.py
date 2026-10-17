#!/usr/bin/env python
"""ontology_consistency.py — advisory ontology-vs-effects consistency check (P1-8).

Answers one question: does the SIGN of the deterministic effect table agree with
the direction the ontology predicted? (contracts §7.2, OD-06 / OD-10)

Participation rules (frozen):
  * only `causal` / `physical` relationships take part — `correlative` and
    `control` relationships are never used to contradict anything;
  * the expected sign must be normalisable (`+`/`positive`/`increase`/… or
    `-`/`negative`/`decrease`/…) AND the factor must be numeric — a categorical
    factor has no monotone direction and lands in `not_estimable`;
  * the observed sign comes from the effect-table coefficient of the factor's
    main term in the same response family; a non-estimable term (aliased /
    saturated / zero variance) lands in `not_estimable`.

**Advisory only**: this module never writes into effect_table/model/effect
conclusions. It emits `01_ontology/ontology_feedback.json` (+ optionally
`02_analysis/ontology_consistency.json`) for the report and the watchlist.
`contradictions[].severity` defaults to `advisory`.

CLI:
  python ontology_consistency.py --run-dir DIR [--effect-table PATH] [--context PATH]
      [--brief PATH] [--consistency-json]
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path

FEEDBACK_CONTRACT_VERSION = "1.0"
PROFILE = "doe"
PARTICIPATING_RELATIONS = ("causal", "physical")

POSITIVE_TOKENS = {"+", "positive", "pos", "increase", "increases", "higher",
                   "up", "直接正相关", "正", "正相关", "增大", "上升", "提高"}
NEGATIVE_TOKENS = {"-", "−", "negative", "neg", "decrease", "decreases", "lower",
                   "down", "反", "负", "负相关", "减小", "下降", "降低"}


# ---------------------------------------------------------------- path utils

def _contained(candidate, extra_root=None):
    cand = os.path.normpath(os.path.abspath(str(candidate)))
    if any(seg == ".." for seg in cand.replace("/", os.sep).split(os.sep)):
        raise ValueError(f"traversal segment rejected in path: {candidate}")
    if extra_root is not None:
        root = os.path.normpath(os.path.abspath(str(extra_root)))
        if not (cand == root or cand.startswith(root + os.sep)):
            raise ValueError(f"path outside allowed root: {candidate}")
    return Path(cand)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, payload):
    out = _contained(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
                   encoding="utf-8")
    return out


def _sha256_file(path):
    p = Path(path)
    if not p.is_file():
        return None
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ------------------------------------------------------------- sign handling

def normalize_sign(value):
    """Normalise a declared direction → 'positive' | 'negative' | None.

    None means "not normalisable" — that relationship is excluded from the check
    (never guessed, never treated as a contradiction).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if value > 0:
            return "positive"
        if value < 0:
            return "negative"
        return None
    token = str(value).strip().lower()
    if not token:
        return None
    if token in POSITIVE_TOKENS:
        return "positive"
    if token in NEGATIVE_TOKENS:
        return "negative"
    # substring fallback for prose ("正向影响" / "negative effect"), longest match wins
    for neg in ("negativ", "decreas", "lower", "negative"):
        if neg in token:
            return "negative"
    for pos in ("positiv", "increas", "higher", "positive"):
        if pos in token:
            return "positive"
    return None


def _observed_sign(coefficient):
    if coefficient is None:
        return None
    try:
        value = float(coefficient)
    except (TypeError, ValueError):
        return None
    if value == 0:
        return "zero"
    return "positive" if value > 0 else "negative"


# ------------------------------------------------------------ effect lookup

def _main_effects(effect_table):
    """{response: {factor: row}} from the effect-table families."""
    out = {}
    families = (effect_table or {}).get("families") or []
    for family in families:
        if not isinstance(family, dict):
            continue
        response = family.get("response")
        if response is None:
            continue
        rows = {}
        for test in family.get("tests") or []:
            if not isinstance(test, dict):
                continue
            term = test.get("term")
            if term and term not in rows:
                rows[term] = test
        out[response] = rows
    return out


def _relationship_pairs(brief, ctx):
    """Every relationship of the brief (causal/physical AND the rest).

    Non-participating relations are returned too so the ledger can record *why*
    they were skipped (`not_estimable_detail`) — nothing is silently dropped.
    """
    brief = brief if isinstance(brief, dict) else {}
    ctx = ctx if isinstance(ctx, dict) else {}
    pairs = []
    for rel in brief.get("relationships") or []:
        if not isinstance(rel, dict):
            continue
        pairs.append({
            "factor": rel.get("from"),
            "response": rel.get("to"),
            "relation": str(rel.get("relation") or "").lower() or None,
            "expected_sign": rel.get("expected_sign"),
            "evidence_level": rel.get("evidence_level"),
            "mechanism": rel.get("mechanism"),
        })
    declared = {str(f.get("col") or f.get("name")): f for f in (brief.get("factors") or [])
                if isinstance(f, dict)}
    for pair in pairs:
        factor_meta = declared.get(str(pair.get("factor")))
        if pair.get("expected_sign") is None and isinstance(factor_meta, dict):
            pair["expected_sign"] = factor_meta.get("expected_sign")
        if isinstance(factor_meta, dict) and pair.get("evidence_level") is None:
            pair["evidence_level"] = ("physics_prior"
                                      if pair.get("relation") in PARTICIPATING_RELATIONS else None)
    return pairs


def _factor_meta(brief, ctx, col):
    for source in (brief.get("factors") if isinstance(brief, dict) else None,
                   ctx.get("factors") if isinstance(ctx, dict) else None):
        for item in source or []:
            if isinstance(item, dict) and (item.get("col") or item.get("name")) == col:
                return item
    return {}


def check(effect_table, ctx, brief):
    """Return the §7.2-shaped consistency result (advisory; no mutation)."""
    effect_table = effect_table if isinstance(effect_table, dict) else {}
    ctx = ctx if isinstance(ctx, dict) else {}
    brief = brief if isinstance(brief, dict) else {}
    effects = _main_effects(effect_table)

    pairs = []
    not_estimable_detail = []
    contradictions = []
    checked = 0
    matched = 0

    for pair in _relationship_pairs(brief, ctx):
        factor = str(pair.get("factor") or "")
        response = str(pair.get("response") or "")
        row = {
            "factor": factor, "response": response, "relation": pair.get("relation"),
            "expected_sign": None, "observed_sign": None, "coefficient": None,
            "estimable": None, "evidence_level": pair.get("evidence_level"),
            "verdict": "not_estimable", "reason": "",
        }
        if not factor or not response:
            row["reason"] = "relationship endpoint missing (from/to)"
        elif pair.get("relation") not in PARTICIPATING_RELATIONS:
            row["reason"] = (f"relation '{pair.get('relation')}' does not participate — only "
                             f"causal/physical relationships are judged (advisory ledger)")
        else:
            meta = _factor_meta(brief, ctx, factor)
            expected = normalize_sign(pair.get("expected_sign") or meta.get("expected_sign"))
            row["expected_sign"] = expected
            if expected is None:
                row["reason"] = ("expected sign is absent or not normalisable — excluded from the "
                                 "check (advisory ledger, no guessing)")
            elif str(meta.get("type") or "").lower().startswith("cat"):
                row["reason"] = f"factor '{factor}' is categorical — no monotone expected direction"
            else:
                test = (effects.get(response) or {}).get(factor)
                if test is None:
                    row["reason"] = (f"factor '{factor}' main term absent from the '{response}' "
                                     f"effect family")
                elif not test.get("estimable", False) or test.get("coefficient") is None:
                    row["reason"] = (f"term not estimable in '{response}' "
                                     f"(reason_code={test.get('reason_code')})")
                else:
                    observed = _observed_sign(test.get("coefficient"))
                    row["observed_sign"] = observed
                    row["coefficient"] = test.get("coefficient")
                    row["estimable"] = True
                    if observed is None:
                        row["reason"] = "coefficient not a finite number"
                    elif observed == "zero":
                        row["reason"] = "estimated coefficient is exactly zero — direction not supported"
                    elif observed == expected:
                        row["verdict"] = "matched"
                        row["reason"] = (f"observed sign {observed} agrees with the ontology-expected "
                                         f"direction")
                        checked += 1
                        matched += 1
                    else:
                        row["verdict"] = "contradicted"
                        row["reason"] = (f"observed sign {observed} is opposite to the ontology-expected "
                                         f"direction {expected}")
                        checked += 1
                        contradictions.append({
                            "factor": factor,
                            "response": response,
                            "expected_sign": expected,
                            "observed_sign": observed,
                            "severity": "advisory",  # frozen default: advisory only
                            "note": (f"effect-table coefficient {test.get('coefficient')} for "
                                     f"'{factor}' → '{response}' contradicts the ontology-predicted "
                                     f"{expected} direction; advisory — statistical conclusions are "
                                     f"NOT rewritten (check confounders / aliasing before acting)"),
                        })
        if row["verdict"] == "not_estimable":
            not_estimable_detail.append({
                "factor": factor, "response": response, "reason": row["reason"],
            })
        pairs.append(row)

    pairs.sort(key=lambda p: (p["factor"], p["response"]))
    result = {
        "contract_version": FEEDBACK_CONTRACT_VERSION,
        "artifact": "ontology_consistency",
        "profile": PROFILE,
        "scene_key": brief.get("scene_key"),
        "context_fp": brief.get("context_fp"),
        "ontology_version": brief.get("ontology_version"),
        "ontology_sha256": brief.get("ontology_sha256"),
        "checked": checked,
        "matched": matched,
        "not_estimable": len(not_estimable_detail),
        "not_estimable_detail": not_estimable_detail,
        "contradictions": contradictions,
        "advisory_only": True,
        "pairs": pairs,
        "generated_at": _now(),
    }
    return result


# ------------------------------------------------------------------- writers

def write_feedback(run_dir, ontology_meta, result):
    """Write `01_ontology/ontology_feedback.json` (§7.2); returns its path."""
    run_dir_v = _contained(run_dir)
    meta = ontology_meta if isinstance(ontology_meta, dict) else {}
    result = result if isinstance(result, dict) else {}
    payload = {
        "contract_version": FEEDBACK_CONTRACT_VERSION,
        "artifact": "ontology_feedback",
        "ontology_version": meta.get("ontology_version", result.get("ontology_version")),
        "ontology_sha256": meta.get("ontology_sha256", result.get("ontology_sha256")),
        "scene_key": meta.get("scene_key", result.get("scene_key")),
        "profile": PROFILE,
        "context_fp": meta.get("context_fp", result.get("context_fp")),
        "checked": int(result.get("checked", 0)),
        "matched": int(result.get("matched", 0)),
        "not_estimable": int(result.get("not_estimable", 0)),
        "not_estimable_detail": result.get("not_estimable_detail", []),
        "contradictions": result.get("contradictions", []),
        "advisory_only": True,
        "checked_at": result.get("generated_at") or _now(),
    }
    out = _write_json(run_dir_v / "01_ontology" / "ontology_feedback.json", payload)
    return str(out)


def write_consistency(run_dir, result, effect_table_path=None):
    """Write `02_analysis/ontology_consistency.json`; returns its path."""
    run_dir_v = _contained(run_dir)
    payload = dict(result or {})
    payload["effect_table_sha256"] = _sha256_file(effect_table_path) if effect_table_path else None
    out = _write_json(run_dir_v / "02_analysis" / "ontology_consistency.json", payload)
    return str(out)


# ------------------------------------------------------------------------ CLI

def _cli():
    ap = argparse.ArgumentParser(description="Advisory ontology-vs-effects consistency check (DOE)")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--effect-table", default=None,
                    help="default: RUN_DIR/02_analysis/effect_table.json")
    ap.add_argument("--context", default=None,
                    help="default: RUN_DIR/00_input/analysis_context.json")
    ap.add_argument("--brief", default=None,
                    help="default: RUN_DIR/01_ontology/ontology_brief.json")
    ap.add_argument("--consistency-json", action="store_true",
                    help="also write 02_analysis/ontology_consistency.json")
    args = ap.parse_args()

    run_dir = _contained(args.run_dir)
    effect_path = Path(args.effect_table) if args.effect_table else run_dir / "02_analysis" / "effect_table.json"
    ctx_path = Path(args.context) if args.context else run_dir / "00_input" / "analysis_context.json"
    brief_path = Path(args.brief) if args.brief else run_dir / "01_ontology" / "ontology_brief.json"
    effect_table = _read_json(effect_path) if effect_path.exists() else {}
    ctx = _read_json(ctx_path) if ctx_path.exists() else {}
    brief = _read_json(brief_path) if brief_path.exists() else {}
    result = check(effect_table, ctx, brief)
    feedback_path = write_feedback(run_dir, {
        "ontology_version": brief.get("ontology_version"),
        "ontology_sha256": brief.get("ontology_sha256"),
        "scene_key": brief.get("scene_key"),
        "context_fp": brief.get("context_fp"),
    }, result)
    out = {
        "feedback_path": feedback_path,
        "checked": result["checked"],
        "matched": result["matched"],
        "not_estimable": result["not_estimable"],
        "contradictions": len(result["contradictions"]),
        "advisory_only": True,
    }
    if args.consistency_json:
        out["consistency_path"] = write_consistency(run_dir, result, effect_path)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
