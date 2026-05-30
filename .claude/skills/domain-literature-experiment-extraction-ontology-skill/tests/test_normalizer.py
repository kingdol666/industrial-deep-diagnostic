#!/usr/bin/env python3
"""
Tests for the Normalizer module.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from normalize_data import Normalizer


def test_synonym_normalization():
    n = Normalizer()

    canonical, conf = n.normalize_name("PVA-1799")
    assert canonical == "PVA 1799", f"Expected PVA 1799, got {canonical}"
    assert conf >= 0.8

    canonical, conf = n.normalize_name("poly(vinyl alcohol) 1799")
    assert canonical == "PVA 1799", f"Expected PVA 1799, got {canonical}"

    canonical, conf = n.normalize_name("cellulose nanocrystal")
    assert canonical == "CNC", f"Expected CNC, got {canonical}"

    canonical, conf = n.normalize_name("graphene oxide")
    assert canonical == "GO", f"Expected GO, got {canonical}"

    canonical, conf = n.normalize_name("Unknown Material XYZ")
    assert canonical == "Unknown Material XYZ"
    assert conf == 0.5

    canonical, conf = n.normalize_name("glycerin")
    assert canonical == "glycerol", f"Expected glycerol, got {canonical}"

    canonical, conf = n.normalize_name("borax")
    assert canonical == "boric acid", f"Expected boric acid, got {canonical}"

    print("  Synonym normalization: PASS")


def test_unit_conversion():
    n = Normalizer()

    val, conf = n.convert_unit(25, "°C", "°C", "temperature")
    assert val == 25
    assert conf == 1.0

    val, conf = n.convert_unit(298.15, "K", "°C", "temperature")
    assert abs(val - 25.0) < 0.1, f"Expected ~25°C, got {val}"

    val, conf = n.convert_unit(100, "μm", "μm", "film_thickness")
    assert val == 100
    assert conf == 1.0

    val, conf = n.convert_unit(0.1, "mm", "μm", "film_thickness")
    assert val == 100.0, f"Expected 100.0 μm, got {val}"

    val, conf = n.convert_unit(1, "min", "h", "time")
    assert abs(val - 0.0166667) < 0.001

    val, conf = n.convert_unit(1, "d", "h", "time")
    assert val == 24.0

    print("  Unit conversion: PASS")


def test_normalize_record():
    n = Normalizer()
    fields = [
        {"field_name": "sample_name", "data_type": "string", "required": True},
        {"field_name": "material_system", "data_type": "string", "required": True},
        {"field_name": "additive", "data_type": "string", "required": False},
        {"field_name": "film_thickness", "data_type": "number", "required": False,
         "unit_field": "film_thickness_unit", "canonical_unit": "μm"},
        {"field_name": "drying_temperature", "data_type": "number", "required": False,
         "unit_field": "drying_temperature_unit", "canonical_unit": "°C"},
    ]

    record = {
        "sample_name": "PVA-1799/CNC",
        "material_system": "poly(vinyl alcohol) 1799",
        "additive": "cellulose nanocrystal",
        "film_thickness": 0.1,
        "film_thickness_unit": "mm",
        "drying_temperature": 298.15,
        "drying_temperature_unit": "K",
    }

    normalized = n.normalize_record(record, fields)

    assert normalized["material_system"] == "PVA 1799"
    assert normalized["additive"] == "CNC"
    assert abs(normalized["film_thickness"] - 100.0) < 0.01
    assert normalized["film_thickness_unit"] == "μm"
    assert abs(normalized["drying_temperature"] - 25.0) < 0.1
    assert normalized["drying_temperature_unit"] == "°C"

    stats = normalized.get("normalization_stats", {})
    assert stats["synonyms_normalized"] >= 2
    assert stats["units_converted"] >= 2

    print("  Record normalization: PASS")


def test_missing_value_flagging():
    n = Normalizer()
    fields = [
        {"field_name": "sample_name", "data_type": "string", "required": True},
        {"field_name": "additive", "data_type": "string", "required": False},
    ]

    record = {
        "sample_name": "Test Film",
        "additive": None,
    }

    normalized = n.normalize_record(record, fields)
    assert normalized["additive"] is None
    stats = normalized.get("normalization_stats", {})
    assert stats["missing_flagged"] >= 1

    record2 = {
        "sample_name": "Test Film 2",
        "additive": "",
    }
    normalized2 = n.normalize_record(record2, fields)
    assert normalized2["additive"] is None

    print("  Missing value flagging: PASS")


if __name__ == "__main__":
    print("Testing Normalizer:")
    test_synonym_normalization()
    test_unit_conversion()
    test_normalize_record()
    test_missing_value_flagging()
    print("All Normalizer tests passed!")