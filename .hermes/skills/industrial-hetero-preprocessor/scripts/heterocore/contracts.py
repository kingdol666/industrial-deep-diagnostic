"""contracts.py — deterministic consumers of column_contract.json.

The ontology builder, data processor and optimizer-loop never guess HX
semantics: they read the contract, or call these helpers. Nothing here uses an
LLM; the mapping below is what makes `physical_meaning_confidence=UNKNOWN`
(→ diagnosis confidence capped at 50) structurally impossible for HX columns.
"""
from __future__ import annotations


def derive_explicit_cols(contract: dict) -> dict:
    """Frozen interface I7: {targets, predictors, excludes} — the deterministic
    column lists the stats layer consumes via --target-cols/--predictor-cols/
    --exclude-cols. sparse / insufficient / metadata / model-derived / staleness
    columns are always excluded from core_stats (its <50% coverage filter would
    silently drop them anyway — plan R2)."""
    targets: list[str] = []
    predictors: list[str] = []
    excludes: list[str] = []
    for col in contract.get("columns", []):
        name = col["column"]
        if col.get("insufficient_data") or col.get("model_derived") or not col.get("stats_eligible", False):
            excludes.append(name)
            continue
        if name.startswith("HX-IDX-") or col.get("role") == "metadata":
            excludes.append(name)
        elif col.get("role") == "target_candidate":
            targets.append(name)
        else:
            predictors.append(name)
    return {"targets": targets, "predictors": predictors, "excludes": excludes}


def _confidence_for(column_name: str) -> str:
    from .naming import is_geometry_feature

    return "INFERRED" if is_geometry_feature(column_name) else "KNOWN"


def to_ontology_signals(contract: dict) -> dict:
    """Map contract columns onto ontology_schema.json signal slots.

    - PROF/MAP/IMG features → process_parameters (role=predictor)
    - TXT event-window 0/1 columns → events (event_values [0,1])
    - everything else (staleness/covariates) → metadata_columns
    Every entry carries physical_meaning_confidence KNOWN|INFERRED (never
    UNKNOWN) plus formula/physics_basis/evidence fields copied from the
    contract, with auto_inferred=true and knowledge_source=user_provided.
    """
    process, events, metadata = [], [], []
    for col in contract.get("columns", []):
        name = col["column"]
        base = {
            "name": col.get("tag_en") or name,
            "column": name,
            "unit": col.get("unit"),
            # ontology_schema signal_v6_3 requires `role`; HX features default to
            # predictor, covariates/staleness carry role=metadata (same enum)
            "role": "metadata" if (col.get("role") == "metadata" or name.startswith("HX-IDX-")) else "predictor",
            "physical_meaning": col["physical_meaning"],
            "physical_meaning_confidence": _confidence_for(name),
            "auto_inferred": True,
            "inference_basis": col.get("physics_basis") or col.get("formula", ""),
            "evidence_level": col.get("evidence_level"),
            "derived": {"formula": col.get("formula"), "method": col.get("method"),
                        "n_inputs": col.get("n_inputs"), "source_sha256": col.get("source_sha256"),
                        "model_derived": bool(col.get("model_derived"))},
            "knowledge_source": "user_provided",
        }
        if col.get("physics_basis"):
            base["governing_law"] = col["physics_basis"]
        if name.startswith("HX-TXT-") and "-EVT-" in name:
            events.append({
                "name": col.get("tag_en") or name,
                "column": name,
                "description": col["physical_meaning"],
                "event_values": [0, 1],
                "event_meanings": {"0": "no", "1": col.get("tag_cn") or name},
            })
        elif base["role"] == "metadata":
            # metadata_columns role enum is batch_id/product_code/timestamp/operator
            # only — covariates/staleness do not fit, so they stay in
            # process_parameters with signal role=metadata (V2 handover fix)
            process.append(base)
        else:
            if col.get("normal_range"):
                base["normal_range"] = list(col["normal_range"])
            process.append(base)
    return {
        "process_parameters": process,
        "events": events,
        "metadata_columns": [],  # covariates ride in process_parameters with role=metadata (schema enum safety)
        "_note": "deterministic mapping from 07_hetero/column_contract.json — merge, never re-infer",
    }
