#!/usr/bin/env python
"""artifact_manifest.py — single source for the DOE artifact manifest (contract §4).

The same payload is consumed by the tasks API and the external API, so a run's
artifact set has exactly one definition (AR-01 "tasks + external 同源").

Shape: docs/plans/contracts/artifact_manifest.schema.json.
Deterministic: no timestamps, sorted artifact order, sha256 of the file bytes.

Usage:
    python artifact_manifest.py --run-dir <DIR> [--out <PATH>] [--json]
Writes <run_dir>/artifact_manifest.json by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST_VERSION = "1.1"
MANIFEST_NAME = "artifact_manifest.json"

# (kind, run-dir-relative path, produced_by)
ARTIFACTS = [
    ("ontology", "01_ontology/ontology.json", "doe_ontology_prepare"),
    ("ontology_brief", "01_ontology/ontology_brief.json", "ontology_brief"),
    ("ontology_coverage", "01_ontology/ontology_coverage.json", "doe_ontology_prepare"),
    ("ontology_feedback", "01_ontology/ontology_feedback.json", "ontology_consistency"),
    ("ontology_consistency", "02_analysis/ontology_consistency.json", "ontology_consistency"),
    ("data_profile", "01_profile/data_profile.json", "analyze.py:profile"),
    ("analysis_plan", "01_profile/analysis_plan.md", "agent (Phase B)"),
    ("effect_table", "02_analysis/effect_table.json", "analyze.py:run"),
    ("model", "02_analysis/model.json", "analyze.py:run"),
    ("association_screen", "02_analysis/association_screen.json", "association_screen"),
    ("doe_conclusion", "conclusions/doe_conclusion.json", "conclusion_template"),
    ("recommendations", "conclusions/recommendations.json", "analyze.py:run"),
    ("next_design", "conclusions/next_design.json", "design_next"),
    ("optimization_guidance", "conclusions/optimization_guidance.json", "optimization_guidance"),
    ("report", "report.html", "analyze.py:report"),
]

# Always expected once a run completes, regardless of mode.
_BASE_EXPECTED = [
    "data_profile", "association_screen", "doe_conclusion", "recommendations",
    "next_design", "optimization_guidance",
]
_DESIGNED_EXPECTED = ["effect_table", "model"]
# Expected only when the ontology stage actually ran (mode != off).
_ONTOLOGY_EXPECTED = ["ontology", "ontology_brief", "ontology_coverage"]
_FEEDBACK_EXPECTED = ["ontology_feedback", "ontology_consistency"]
# Agent-authored (Phase B): expected only when the ontology gate is armed.
_PLAN_EXPECTED = ["analysis_plan"]

# NOT expected (report.md is optional; report.html is the built deliverable)
_NEVER_EXPECTED = {"report"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _contract_version(path: Path) -> str | None:
    """schema_version of an artifact = its own contract_version when it has one."""
    if path.suffix.lower() != ".json":
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(doc, dict) and isinstance(doc.get("contract_version"), str):
        return doc["contract_version"]
    return None


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _expected_kinds(run_dir: Path) -> set[str]:
    ctx = _read_json(run_dir / "00_input" / "analysis_context.json")
    profile = _read_json(run_dir / "01_profile" / "data_profile.json")
    mode = ((profile.get("design") or {}).get("mode")
            or (ctx.get("mode_override") or "observational"))
    ont = ctx.get("ontology") if isinstance(ctx.get("ontology"), dict) else {}
    gate_on = ont and ont.get("mode") not in (None, "off")

    expected = set(_BASE_EXPECTED) | {"report"}
    if mode == "designed":
        expected |= set(_DESIGNED_EXPECTED)
    if gate_on:
        expected |= set(_ONTOLOGY_EXPECTED) | set(_PLAN_EXPECTED)
        # Consistency/feedback are designed-mode artifacts (contract §3.5: only
        # causal/physical relationships with an estimable effect are checked).
        # An observational run must not be reported as "missing" them.
        if mode == "designed" and (run_dir / "01_ontology" / "ontology_brief.json").is_file():
            expected |= set(_FEEDBACK_EXPECTED)
    return expected - _NEVER_EXPECTED


def build_manifest(run_dir, *, run_id=None, analysis_intent=None) -> dict:
    """Build the contract manifest for a completed (or partial) run directory."""
    run_dir = Path(run_dir).resolve()
    ctx = _read_json(run_dir / "00_input" / "analysis_context.json")
    doe = _read_json(run_dir / "00_input" / "doe_context.json")
    brief = _read_json(run_dir / "01_ontology" / "ontology_brief.json")
    ontology_version = brief.get("ontology_version") if isinstance(brief, dict) else None

    expected = _expected_kinds(run_dir)
    artifacts, missing = [], []
    for kind, rel, produced_by in ARTIFACTS:
        path = run_dir / rel
        if path.is_file():
            entry = {
                "kind": kind,
                "path": rel,
                "url": None,
                "sha256": _sha256(path),
                "schema_version": _contract_version(path),
                "bytes": int(path.stat().st_size),
                "produced_by": produced_by,
            }
            if ontology_version:
                entry["ontology_version"] = ontology_version
            artifacts.append(entry)
        elif kind in expected:
            missing.append({"kind": kind, "reason": f"expected artifact absent: {rel}"})

    return {
        "contract_version": MANIFEST_VERSION,
        "schema_version": MANIFEST_VERSION,
        "run_id": run_id or doe.get("experiment_id") or ctx.get("experiment_id") or run_dir.name,
        "run_dir": str(run_dir),
        "analysis_intent": analysis_intent,
        "artifacts": artifacts,
        "missing": missing,
    }


def write_manifest(run_dir, *, out=None, run_id=None, analysis_intent=None) -> Path:
    run_dir = Path(run_dir).resolve()
    payload = build_manifest(run_dir, run_id=run_id, analysis_intent=analysis_intent)
    target = Path(out) if out else run_dir / MANIFEST_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="artifact_manifest.py")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--intent", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"ERROR: run dir not found: {run_dir}", file=sys.stderr)
        return 2
    target = Path(args.out).resolve() if args.out else None
    if target is not None and run_dir not in target.parents and target.parent != run_dir:
        print(f"ERROR: --out must stay inside the run dir: {target}", file=sys.stderr)
        return 2
    out = write_manifest(run_dir, out=target, run_id=args.run_id,
                         analysis_intent=args.intent)
    payload = json.loads(out.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps({"manifest": str(out),
                          "n_artifacts": len(payload["artifacts"]),
                          "n_missing": len(payload["missing"]),
                          "missing": payload["missing"]}, ensure_ascii=False))
    else:
        print(f"[manifest] {out} artifacts={len(payload['artifacts'])} "
              f"missing={len(payload['missing'])}")
        for m in payload["missing"]:
            print(f"[manifest] MISSING {m['kind']}: {m['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
