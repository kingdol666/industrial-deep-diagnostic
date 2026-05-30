#!/usr/bin/env python3
"""
Literature-to-Lab Data Transformer

Maps literature-extracted experiment records (domain-literature-experiment-extraction-ontology-skill)
into chem-auto-lab-skill compatible input format.

Schema mapping:
  literature experiment_record → lab experiment_record
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPECTRAL_INDICATORS = {
    'wavenumber', 'wavelength', 'chemical_shift', 'mz',
    'retention_time', 'absorbance', 'transmittance_percent',
    'intensity', 'raman_shift', 'peak_position', 'peak_area'
}

SPECTRAL_PROPERTIES = {
    'FTIR', 'RAMAN', 'NMR', 'UV-VIS', 'UVVIS', 'UV-VIS-NIR',
    'HPLC', 'GC-MS', 'GCMS', 'XRD', 'XPS', 'EDS', 'EDX',
    'MASS SPECTROMETRY', 'MASS SPECTROSCOPY'
}

PROPERTY_SLUG_MAP = {
    'light_transmittance': 'transmittance',
    'elongation_at_break': 'elongation',
    'tensile_strength': 'tensile_strength',
    'young_s_modulus': 'youngs_modulus',
    'water_vapor_transmission_rate': 'wvtr',
    'oxygen_transmission_rate': 'otr',
    'contact_angle': 'contact_angle',
    'haze': 'haze',
    'crystallinity': 'crystallinity',
    'glass_transition_temperature': 'tg',
    'melting_temperature': 'tm',
    'decomposition_temperature': 'td',
}


def slugify(name: str) -> str:
    if not name:
        return 'unknown_property'
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = re.sub(r'_+', '_', slug)
    slug = slug.strip('_')
    return PROPERTY_SLUG_MAP.get(slug, slug)


def is_spectral_property(record: dict) -> bool:
    measured = str(record.get('measured_property', '')).upper().strip()
    if measured in SPECTRAL_PROPERTIES:
        return True

    measured_2 = str(record.get('measured_property_2', '')).upper().strip()
    if measured_2 in SPECTRAL_PROPERTIES:
        return True

    for key in record:
        key_lower = key.lower()
        for indicator in SPECTRAL_INDICATORS:
            if indicator in key_lower:
                return True

    return False


def extract_spectral_peaks(record: dict) -> list[dict]:
    peaks = []
    for key in record:
        key_lower = key.lower()
        if any(ind in key_lower for ind in ('wavenumber', 'wavelength', 'peak')):
            value = record.get(key)
            if value is not None and isinstance(value, (int, float)):
                peaks.append({
                    'position': value,
                    'position_type': 'wavenumber' if 'wavenumber' in key_lower else 'wavelength',
                    'source_key': key
                })
    return peaks if peaks else []


def map_literature_to_lab(record: dict, include_spectral: bool = False) -> dict:
    lab_record: dict[str, Any] = {
        'experiment_id': record.get('experiment_id', ''),
        'timestamp': None,
        'variables': {},
        'observations': {},
        'batch_id': record.get('source_id', None),
        'source_file': 'experiments_normalized.json',
        'source_sheet': None,
        'source_row': None,
        'low_confidence': False,
    }

    confidence = record.get('confidence')
    if confidence is not None and confidence < 0.5:
        lab_record['low_confidence'] = True

    if record.get('source_confidence'):
        lab_record['observations']['source_confidence'] = record['source_confidence']

    # Material info
    if record.get('material_system'):
        lab_record['variables']['material_system'] = record['material_system']
    if record.get('material_grade'):
        lab_record['variables']['material_grade'] = record['material_grade']

    # Simple field mappings: (literature_field, lab_variable_name)
    simple_mappings = [
        ('film_preparation_method', 'preparation_method'),
        ('instrument', 'instrument'),
        ('stretching_ratio', 'stretching_ratio'),
        ('result_direction', 'result_direction'),
    ]
    for lit_field, lab_var in simple_mappings:
        value = record.get(lit_field)
        if value is not None:
            lab_record['variables'][lab_var] = value

    # Value + Unit field mappings: (literature_value_field, literature_unit_field, lab_variable_name)
    value_unit_mappings = [
        ('film_thickness', 'film_thickness_unit', 'film_thickness'),
        ('drying_temperature', 'drying_temperature_unit', 'drying_temperature'),
        ('drying_time', 'drying_time_unit', 'drying_time'),
        ('heat_treatment_temperature', 'heat_treatment_temperature_unit', 'heat_treatment_temp'),
        ('heat_treatment_time', 'heat_treatment_time_unit', 'heat_treatment_time'),
        ('stretching_temperature', 'stretching_temperature_unit', 'stretching_temp'),
        ('solution_concentration', 'solution_concentration_unit', 'solution_concentration'),
    ]
    for val_field, unit_field, lab_var in value_unit_mappings:
        value = record.get(val_field)
        if value is not None:
            entry: dict[str, Any] = {'value': value}
            unit = record.get(unit_field)
            if unit is not None:
                entry['unit'] = unit
            lab_record['variables'][lab_var] = entry

    # Additive
    if record.get('additive'):
        additive_entry: dict[str, Any] = {'name': record['additive']}
        conc = record.get('additive_concentration')
        if conc is not None:
            additive_entry['concentration'] = {
                'value': conc,
                'unit': record.get('additive_concentration_unit')
            }
        lab_record['variables']['additive'] = additive_entry

    # Plasticizer
    if record.get('plasticizer'):
        plast_entry: dict[str, Any] = {'name': record['plasticizer']}
        conc = record.get('plasticizer_concentration')
        if conc is not None:
            plast_entry['concentration'] = {
                'value': conc,
                'unit': record.get('plasticizer_concentration_unit')
            }
        lab_record['variables']['plasticizer'] = plast_entry

    # Crosslinker
    if record.get('crosslinker'):
        xlink_entry: dict[str, Any] = {'name': record['crosslinker']}
        conc = record.get('crosslinker_concentration')
        if conc is not None:
            xlink_entry['concentration'] = {
                'value': conc,
                'unit': record.get('crosslinker_concentration_unit')
            }
        lab_record['variables']['crosslinker'] = xlink_entry

    # Measured properties 1-5
    for i in range(1, 6):
        suffix = '' if i == 1 else f'_{i}'
        prop = record.get(f'measured_property{suffix}')
        val = record.get(f'measured_value{suffix}')
        if prop and val is not None:
            slug = slugify(str(prop))
            entry: dict[str, Any] = {'value': val}
            unit = record.get(f'measured_unit{suffix}')
            if unit is not None:
                entry['unit'] = unit
            if record.get('error_value') is not None:
                entry['error'] = record['error_value']
            lab_record['variables'][slug] = entry

    # Error bars
    if record.get('error_type') and record.get('error_value'):
        lab_record['variables']['_error_type'] = record['error_type']
        lab_record['variables']['_error_value'] = record['error_value']

    # Value range
    if record.get('value_min') is not None or record.get('value_max') is not None:
        lab_record['variables']['_value_range'] = {
            'min': record.get('value_min'),
            'max': record.get('value_max')
        }

    # Observations (provenance)
    observations = lab_record['observations']
    if record.get('source_snippet'):
        observations['source_text'] = record['source_snippet']
    if record.get('paper_title'):
        paper_ref_parts = [record['paper_title']]
        if record.get('year'):
            paper_ref_parts.append(f"({record['year']})")
        if record.get('source_doi'):
            paper_ref_parts.append(f"doi:{record['source_doi']}")
        observations['paper_ref'] = ', '.join(paper_ref_parts)
    if record.get('extraction_method'):
        observations['extraction_method'] = record['extraction_method']
    if record.get('source_page') is not None:
        observations['source_page'] = record['source_page']
    if record.get('source_location'):
        observations['source_location'] = record['source_location']

    if confidence is not None:
        observations['source_confidence'] = confidence

    # Spectral data
    if include_spectral:
        peaks = extract_spectral_peaks(record)
        if peaks:
            lab_record['spectral_peaks'] = peaks
        if is_spectral_property(record):
            lab_record['_has_spectral_data'] = True

    # Notes
    if record.get('notes'):
        observations['notes'] = record['notes']

    # Author conclusions
    if record.get('conclusion_author'):
        observations['author_conclusion'] = record['conclusion_author']

    return lab_record


def detect_spectral_data(records: list[dict]) -> bool:
    for record in records:
        if is_spectral_property(record):
            return True
        for key in record:
            key_lower = key.lower()
            if any(ind in key_lower for ind in SPECTRAL_INDICATORS):
                return True
    return False


def transform(
    input_path: Path,
    output_path: Path,
    domain: str = '',
    include_spectral: bool = False,
    confidence_threshold: float = 0.3,
) -> dict:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    if isinstance(raw_data, list):
        records = raw_data
    elif isinstance(raw_data, dict):
        records = raw_data.get('experiments', raw_data.get('data', []))
        if not records and isinstance(raw_data, dict):
            records = [raw_data]
    else:
        raise ValueError(f"Unexpected input format: {type(raw_data)}")

    if not records:
        raise ValueError("No experiment records found in input")

    if include_spectral:
        spectral_detected = detect_spectral_data(records)
    else:
        spectral_detected = False

    transformed = []
    filtered_count = 0
    unmapped_fields: set[str] = set()
    field_counts: dict[str, int] = {}

    known_lit_fields = {
        'experiment_id', 'source_id', 'paper_title', 'year', 'source_doi',
        'sample_name', 'material_system', 'material_grade',
        'additive', 'additive_concentration', 'additive_concentration_unit', 'additive_subtype',
        'plasticizer', 'plasticizer_concentration', 'plasticizer_concentration_unit',
        'crosslinker', 'crosslinker_concentration', 'crosslinker_concentration_unit',
        'solvent', 'solution_concentration', 'solution_concentration_unit',
        'film_preparation_method', 'drying_temperature', 'drying_temperature_unit',
        'drying_time', 'drying_time_unit', 'heat_treatment_temperature',
        'heat_treatment_temperature_unit', 'heat_treatment_time', 'heat_treatment_time_unit',
        'stretching_ratio', 'stretching_temperature', 'stretching_temperature_unit',
        'film_thickness', 'film_thickness_unit', 'instrument',
        'measured_property', 'measured_value', 'measured_unit',
        'measured_property_2', 'measured_value_2', 'measured_unit_2',
        'measured_property_3', 'measured_value_3', 'measured_unit_3',
        'measured_property_4', 'measured_value_4', 'measured_unit_4',
        'measured_property_5', 'measured_value_5', 'measured_unit_5',
        'comparison_baseline', 'result_direction',
        'error_type', 'error_value', 'value_type', 'value_min', 'value_max',
        'conclusion_author', 'alternative_values',
        'source_page', 'source_location', 'source_snippet',
        'extraction_method', 'confidence', 'record_confidence',
        'notes', 'ambiguous_naming', 'secondary_source', 'preparation_only',
        'name_original', 'name_canonical', 'metadata',
    }

    for i, record in enumerate(records):
        confidence = record.get('confidence', 0.5)
        if isinstance(confidence, (int, float)) and confidence < confidence_threshold:
            filtered_count += 1
            continue

        lab_record = map_literature_to_lab(record, include_spectral=spectral_detected)
        lab_record['source_row'] = i
        transformed.append(lab_record)

        for field in record:
            if field not in known_lit_fields:
                unmapped_fields.add(field)

        for var_key in lab_record['variables']:
            field_counts[var_key] = field_counts.get(var_key, 0) + 1

    output = {
        'metadata': {
            'script': 'transform_literature_to_lab.py',
            'version': '1.0.0',
            'source': 'literature_extraction',
            'domain': domain,
            'processing_timestamp': datetime.now(timezone.utc).isoformat(),
            'rows_input': len(records),
            'rows_output': len(transformed),
            'rows_filtered': filtered_count,
            'filter_reason': f'confidence < {confidence_threshold}' if filtered_count > 0 else None,
            'confidence_threshold': confidence_threshold,
            'spectral_data_present': spectral_detected,
        },
        'experiments': transformed,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return {
        'records_input': len(records),
        'records_output': len(transformed),
        'records_filtered': filtered_count,
        'spectral_detected': spectral_detected,
        'field_counts': field_counts,
        'unmapped_fields': sorted(unmapped_fields),
    }


def main():
    parser = argparse.ArgumentParser(
        description='Transform literature-extracted experiment records to chem-auto-lab format'
    )
    parser.add_argument('--input', required=True, help='Path to experiments_normalized.json')
    parser.add_argument('--output', required=True, help='Output path for lab_experiments.json')
    parser.add_argument('--domain', default='', help='Domain name (e.g., pva_bopet)')
    parser.add_argument(
        '--include-spectral',
        action='store_true',
        help='Include spectral peak extraction in output'
    )
    parser.add_argument(
        '--confidence-threshold',
        type=float,
        default=0.3,
        help='Filter records with confidence below threshold (default: 0.3)'
    )
    args = parser.parse_args()

    try:
        stats = transform(
            input_path=Path(args.input),
            output_path=Path(args.output),
            domain=args.domain,
            include_spectral=args.include_spectral,
            confidence_threshold=args.confidence_threshold,
        )

        print(json.dumps({
            'status': 'success',
            'records_input': stats['records_input'],
            'records_output': stats['records_output'],
            'records_filtered': stats['records_filtered'],
            'spectral_detected': stats['spectral_detected'],
            'field_counts': stats['field_counts'],
            'unmapped_fields': stats['unmapped_fields'],
        }, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()