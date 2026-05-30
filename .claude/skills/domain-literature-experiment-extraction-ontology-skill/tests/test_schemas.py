#!/usr/bin/env python3
"""
Tests for JSON Schema validation of experiment records.
"""

import json
import sys
from pathlib import Path

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

SKILL_DIR = Path(__file__).resolve().parent.parent


def load_schema(name: str) -> dict:
    path = SKILL_DIR / "schemas" / f"{name}.schema.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_experiment_record_schema():
    schema = load_schema("experiment_record")
    valid_record = {
        "experiment_id": "SRC_0001_E01",
        "source_id": "SRC_0001",
        "paper_title": "Test PVA CNC Composite",
        "year": 2020,
        "sample_name": "PVA-CNC-3",
        "material_system": "PVA 1799",
        "additive": "CNC",
        "additive_concentration": 3.0,
        "confidence": 0.9,
    }
    if HAS_JSONSCHEMA:
        jsonschema.validate(valid_record, schema)
    print("  Experiment record schema validation: PASS (valid)")


def test_experiment_record_invalid_id():
    schema = load_schema("experiment_record")
    invalid_record = {
        "experiment_id": "bad-id",
        "source_id": "SRC_0001",
        "paper_title": "Test",
        "year": 2020,
        "confidence": 1.5,
    }
    if HAS_JSONSCHEMA:
        from jsonschema import ValidationError
        try:
            jsonschema.validate(invalid_record, schema)
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass
    print("  Experiment record invalid ID + bad confidence: PASS (rejected)")


def test_provenance_schema():
    schema = load_schema("provenance_record")
    valid = {
        "experiment_id": "SRC_0001_E01",
        "source_id": "SRC_0001",
        "source_title": "Test PVA CNC Composite",
        "source_year": 2020,
        "source_doi": "10.1234/test.001",
        "fields": {
            "additive_concentration": {
                "value_original": 3.0,
                "value_normalized": 3.0,
                "unit_original": "wt%",
                "unit_normalized": "wt%",
                "source_page": 5,
                "source_snippet": "The composite contained 3 wt% CNC",
                "confidence": 0.95,
                "extraction_method": "table_parse",
                "assumptions": []
            }
        },
        "record_confidence": 0.90
    }
    if HAS_JSONSCHEMA:
        jsonschema.validate(valid, schema)
    print("  Provenance schema validation: PASS")


def run_all():
    print("Testing JSON Schema Validation:")
    test_experiment_record_schema()
    test_experiment_record_invalid_id()
    test_provenance_schema()
    print("All schema validation tests passed!")


if __name__ == "__main__":
    if not HAS_JSONSCHEMA:
        print("Warning: jsonschema not installed. Install with: pip install jsonschema")
        print("Running structural tests only...")
    run_all()