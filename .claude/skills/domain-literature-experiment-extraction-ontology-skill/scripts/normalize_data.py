#!/usr/bin/env python3
"""
Normalizer: canonicalizes names, converts units, flags missing/ambiguous values.
Uses assets/synonym_map.json and assets/unit_conversions.json.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

SKILL_DIR = Path(__file__).resolve().parent.parent


class Normalizer:
    def __init__(self, synonym_path: Path = None, unit_path: Path = None):
        self.synonym_path = synonym_path or (SKILL_DIR / "assets" / "synonym_map.json")
        self.unit_path = unit_path or (SKILL_DIR / "assets" / "unit_conversions.json")
        self.synonym_map = self._load_json(self.synonym_path)
        self.unit_map = self._load_json(self.unit_path)
        self._build_reverse_synonym_map()

    def _load_json(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_reverse_synonym_map(self):
        self._reverse_map = {}
        for category, mappings in self.synonym_map.get("mappings", {}).items():
            for canonical, synonyms in mappings.items():
                for syn in synonyms:
                    key = syn.lower().strip()
                    self._reverse_map[key] = (canonical, category)

    def normalize_name(self, value: str, category_hint: Optional[str] = None) -> tuple:
        if not value:
            return value, 0.0
        key = value.lower().strip()
        if key in self._reverse_map:
            canonical, category = self._reverse_map[key]
            return canonical, 1.0
        for (syn_lower, (canonical, category)) in self._reverse_map.items():
            if len(syn_lower) < 3:
                continue
            if syn_lower in key or key in syn_lower:
                return canonical, 0.8
        return value, 0.5

    def convert_unit(self, value: float, from_unit: str, to_unit: str,
                     category: str) -> tuple:
        if from_unit == to_unit:
            return value, 1.0
        conversions = self.unit_map.get(category, [])
        for conv in conversions:
            if conv.get("from") == from_unit and conv.get("to") == to_unit:
                multiplier = conv["multiplier"]
                offset = conv.get("offset", 0)
                if multiplier is None:
                    return value, 0.3
                result = value * multiplier + offset
                warning = conv.get("warning", "")
                return result, 0.85 if warning else 1.0
        return value, 0.4

    def normalize_record(self, record: dict, field_definitions: list) -> dict:
        stats = {
            "synonyms_normalized": 0,
            "units_converted": 0,
            "missing_flagged": 0,
            "ambiguous_flagged": 0
        }
        normalized = dict(record)

        for field_def in field_definitions:
            field_name = field_def["field_name"]
            data_type = field_def["data_type"]
            unit_field = field_def.get("unit_field")
            canonical_unit = field_def.get("canonical_unit")

            current_value = record.get(field_name)
            if current_value is None or current_value == "" or current_value == "N/A":
                normalized[field_name] = None
                stats["missing_flagged"] += 1
                continue

            if data_type in ("string", "enum"):
                category = "materials" if "material" in field_name.lower() else None
                canonical, conf = self.normalize_name(str(current_value), category)
                if canonical != current_value:
                    normalized[field_name] = canonical
                    stats["synonyms_normalized"] += 1

            elif data_type in ("number", "integer"):
                try:
                    num_val = float(current_value) if isinstance(current_value, str) else current_value
                except (ValueError, TypeError):
                    stats["ambiguous_flagged"] += 1
                    normalized[field_name] = None
                    continue

                if unit_field and canonical_unit:
                    current_unit = record.get(unit_field, canonical_unit)
                    if current_unit and current_unit != canonical_unit:
                        category_map = {
                            "temperature_unit": "temperature",
                            "film_thickness_unit": "film_thickness",
                            "concentration_unit": "concentration",
                            "pressure_unit": "pressure",
                            "tensile_strength_unit": "mechanical",
                            "youngs_modulus_unit": "mechanical",
                            "wvtr_unit": "barrier_wvtr",
                            "otr_unit": "barrier_otr",
                            "drying_time_unit": "time",
                        }
                        conv_category = category_map.get(unit_field, "temperature")
                        converted, conv_conf = self.convert_unit(
                            num_val, str(current_unit), canonical_unit, conv_category
                        )
                        normalized[field_name] = converted
                        normalized[unit_field] = canonical_unit
                        stats["units_converted"] += 1

        if "normalization_stats" not in normalized:
            normalized["normalization_stats"] = stats
        else:
            for k, v in stats.items():
                normalized["normalization_stats"][k] = \
                    normalized["normalization_stats"].get(k, 0) + v

        return normalized

    def normalize_batch(self, records: list, field_definitions: list) -> list:
        return [self.normalize_record(r, field_definitions) for r in records]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Normalize experiment records")
    parser.add_argument("--input", required=True, help="Path to extraction results JSON")
    parser.add_argument("--config", required=True, help="Path to extraction config JSON")
    parser.add_argument("--output", required=True, help="Output path for normalized JSON")

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    normalizer = Normalizer()
    experiments = data.get("experiments", [])
    fields = config.get("fields", [])

    normalized = normalizer.normalize_batch(experiments, fields)

    result = {"experiments": normalized, "meta": {
        "total": len(normalized),
        "synonyms_normalized": sum(
            r.get("normalization_stats", {}).get("synonyms_normalized", 0) for r in normalized
        ),
        "units_converted": sum(
            r.get("normalization_stats", {}).get("units_converted", 0) for r in normalized
        ),
        "missing_flagged": sum(
            r.get("normalization_stats", {}).get("missing_flagged", 0) for r in normalized
        ),
    }}

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Normalized {len(normalized)} records -> {output_path}")


if __name__ == "__main__":
    main()