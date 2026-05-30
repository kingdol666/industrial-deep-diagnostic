#!/usr/bin/env python3
"""
Integration tests for the Literature-to-Lab Bridge Skill.

Tests:
  1. Transformer: basic field mapping
  2. Transformer: spectral data detection
  3. Transformer: confidence filtering
  4. Transformer: empty input handling
  5. Bridge pipeline: quality gate logic
  6. Bridge pipeline: manifest generation
  7. Schema validation: bridge_manifest.schema.json
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

from transform_literature_to_lab import (
    map_literature_to_lab,
    detect_spectral_data,
    slugify,
    is_spectral_property,
    transform,
)


def test_slugify():
    assert slugify('Light Transmittance') == 'transmittance'
    assert slugify('Tensile Strength') == 'tensile_strength'
    assert slugify('Young\'s Modulus') == 'youngs_modulus'
    assert slugify('Water Vapor Transmission Rate') == 'wvtr'
    assert slugify('') == 'unknown_property'
    assert slugify('   Haze   ') == 'haze'
    print('  ✓ test_slugify')


def test_is_spectral_property():
    assert is_spectral_property({'measured_property': 'FTIR'})
    assert is_spectral_property({'measured_property': 'Raman'})
    assert is_spectral_property({'measured_property': 'NMR'})
    assert is_spectral_property({'measured_property_2': 'XRD'})
    assert not is_spectral_property({'measured_property': 'Tensile Strength'})
    assert not is_spectral_property({})
    print('  ✓ test_is_spectral_property')


def test_detect_spectral_data():
    records_spectral = [
        {'measured_property': 'Tensile Strength', 'measured_value': 85},
        {'measured_property': 'FTIR', 'measured_value': 0.85},
    ]
    assert detect_spectral_data(records_spectral) is True

    records_non_spectral = [
        {'measured_property': 'Tensile Strength', 'measured_value': 85},
        {'measured_property': 'Haze', 'measured_value': 3.2},
    ]
    assert detect_spectral_data(records_non_spectral) is False

    records_with_wavenumber = [
        {'wavenumber': 3340, 'intensity': 0.85},
    ]
    assert detect_spectral_data(records_with_wavenumber) is True

    print('  ✓ test_detect_spectral_data')


def test_map_basic_record():
    record = {
        'experiment_id': 'SRC_001_E001',
        'source_id': 'SRC_001',
        'paper_title': 'Test Paper',
        'year': 2023,
        'source_doi': '10.1234/test',
        'material_system': 'PVA/CNC composite',
        'film_thickness': 50,
        'film_thickness_unit': 'μm',
        'drying_temperature': 60,
        'drying_temperature_unit': '°C',
        'measured_property': 'Light Transmittance',
        'measured_value': 92.3,
        'measured_unit': '%',
        'confidence': 0.9,
        'source_snippet': 'The film exhibited light transmittance of 92.3%',
        'extraction_method': 'table_parse',
    }

    lab_record = map_literature_to_lab(record)

    assert lab_record['experiment_id'] == 'SRC_001_E001'
    assert lab_record['batch_id'] == 'SRC_001'
    assert lab_record['variables']['material_system'] == 'PVA/CNC composite'
    assert lab_record['variables']['film_thickness'] == {'value': 50, 'unit': 'μm'}
    assert lab_record['variables']['drying_temperature'] == {'value': 60, 'unit': '°C'}
    assert lab_record['variables']['transmittance'] == {'value': 92.3, 'unit': '%'}
    assert lab_record['observations']['source_text'] == 'The film exhibited light transmittance of 92.3%'
    assert lab_record['observations']['paper_ref'] == 'Test Paper, (2023), doi:10.1234/test'
    assert lab_record['observations']['extraction_method'] == 'table_parse'
    assert lab_record['observations']['source_confidence'] == 0.9
    assert lab_record['low_confidence'] is False

    print('  ✓ test_map_basic_record')


def test_map_additive_record():
    record = {
        'experiment_id': 'SRC_002_E005',
        'source_id': 'SRC_002',
        'material_system': 'PVA film',
        'additive': 'CNC',
        'additive_concentration': 5,
        'additive_concentration_unit': 'wt%',
        'plasticizer': 'Glycerol',
        'plasticizer_concentration': 10,
        'plasticizer_concentration_unit': 'wt%',
        'crosslinker': 'Boric Acid',
        'crosslinker_concentration': 2,
        'crosslinker_concentration_unit': 'wt%',
        'confidence': 0.8,
    }

    lab_record = map_literature_to_lab(record)

    assert lab_record['variables']['additive'] == {
        'name': 'CNC',
        'concentration': {'value': 5, 'unit': 'wt%'}
    }
    assert lab_record['variables']['plasticizer'] == {
        'name': 'Glycerol',
        'concentration': {'value': 10, 'unit': 'wt%'}
    }
    assert lab_record['variables']['crosslinker'] == {
        'name': 'Boric Acid',
        'concentration': {'value': 2, 'unit': 'wt%'}
    }

    print('  ✓ test_map_additive_record')


def test_map_low_confidence():
    record = {
        'experiment_id': 'SRC_003_E001',
        'source_id': 'SRC_003',
        'material_system': 'Unknown',
        'confidence': 0.25,
    }

    lab_record = map_literature_to_lab(record)
    assert lab_record['low_confidence'] is True

    print('  ✓ test_map_low_confidence')


def test_map_multiple_properties():
    record = {
        'experiment_id': 'SRC_004_E001',
        'source_id': 'SRC_004',
        'measured_property': 'Tensile Strength',
        'measured_value': 85.4,
        'measured_unit': 'MPa',
        'measured_property_2': 'Elongation at Break',
        'measured_value_2': 120,
        'measured_unit_2': '%',
        'measured_property_3': 'Young\'s Modulus',
        'measured_value_3': 2.5,
        'measured_unit_3': 'GPa',
        'confidence': 0.9,
    }

    lab_record = map_literature_to_lab(record)

    assert lab_record['variables']['tensile_strength'] == {'value': 85.4, 'unit': 'MPa'}
    assert lab_record['variables']['elongation'] == {'value': 120, 'unit': '%'}
    assert lab_record['variables']['youngs_modulus'] == {'value': 2.5, 'unit': 'GPa'}

    print('  ✓ test_map_multiple_properties')


def test_transform_with_filtering():
    records = [
        {'experiment_id': 'SRC_001_E001', 'material_system': 'PVA', 'confidence': 0.9, 'measured_property': 'Haze', 'measured_value': 3.0, 'measured_unit': '%'},
        {'experiment_id': 'SRC_001_E002', 'material_system': 'PVA', 'confidence': 0.2, 'measured_property': 'Haze', 'measured_value': 4.0, 'measured_unit': '%'},
        {'experiment_id': 'SRC_001_E003', 'material_system': 'PVA', 'confidence': 0.8, 'measured_property': 'Haze', 'measured_value': 2.5, 'measured_unit': '%'},
        {'experiment_id': 'SRC_001_E004', 'material_system': 'PVA', 'confidence': 0.1, 'measured_property': 'Haze', 'measured_value': 5.0, 'measured_unit': '%'},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / 'input.json'
        output_path = Path(tmpdir) / 'output.json'

        with open(input_path, 'w') as f:
            json.dump(records, f)

        stats = transform(input_path, output_path, confidence_threshold=0.3)

        assert stats['records_input'] == 4
        assert stats['records_output'] == 2
        assert stats['records_filtered'] == 2

        with open(output_path, 'r') as f:
            output = json.load(f)

        assert len(output['experiments']) == 2
        experiment_ids = [e['experiment_id'] for e in output['experiments']]
        assert 'SRC_001_E001' in experiment_ids
        assert 'SRC_001_E002' not in experiment_ids
        assert 'SRC_001_E003' in experiment_ids
        assert 'SRC_001_E004' not in experiment_ids

        assert output['metadata']['rows_input'] == 4
        assert output['metadata']['rows_output'] == 2
        assert output['metadata']['rows_filtered'] == 2

    print('  ✓ test_transform_with_filtering')


def test_transform_empty_input():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / 'empty.json'
        output_path = Path(tmpdir) / 'output.json'

        with open(input_path, 'w') as f:
            json.dump([], f)

        try:
            transform(input_path, output_path)
            assert False, 'Should have raised ValueError'
        except ValueError as e:
            assert 'No experiment records' in str(e)

    print('  ✓ test_transform_empty_input')


def test_transform_file_not_found():
    try:
        transform(Path('/nonexistent/path.json'), Path('/tmp/output.json'))
        assert False, 'Should have raised FileNotFoundError'
    except FileNotFoundError:
        pass

    print('  ✓ test_transform_file_not_found')


def test_quality_gate_logic():
    from bridge_pipeline import run_quality_gate

    with tempfile.TemporaryDirectory() as tmpdir:
        phase1_dir = Path(tmpdir)

        # Test passing
        summary = {
            'statistics': {
                'experiments_extracted': 100,
                'mean_confidence': 0.85,
                'papers_processed': 15,
            }
        }
        with open(phase1_dir / 'run_summary.json', 'w') as f:
            json.dump(summary, f)

        result = run_quality_gate(phase1_dir, min_records=10, min_confidence=0.5, min_papers=3)
        assert result['passed'] is True
        assert len(result['checks']) == 3
        assert all(c['passed'] for c in result['checks'])

        # Test failing: too few records
        summary['statistics']['experiments_extracted'] = 5
        with open(phase1_dir / 'run_summary.json', 'w') as f:
            json.dump(summary, f)

        result = run_quality_gate(phase1_dir, min_records=10, min_confidence=0.5, min_papers=3)
        assert result['passed'] is False
        assert any('Insufficient records' in w for w in result['warnings'])

        # Test failing: low confidence
        summary['statistics']['experiments_extracted'] = 100
        summary['statistics']['mean_confidence'] = 0.35
        with open(phase1_dir / 'run_summary.json', 'w') as f:
            json.dump(summary, f)

        result = run_quality_gate(phase1_dir, min_records=10, min_confidence=0.5, min_papers=3)
        assert result['passed'] is False
        assert any('Low mean confidence' in w for w in result['warnings'])

        # Test failing: too few papers
        summary['statistics']['mean_confidence'] = 0.85
        summary['statistics']['papers_processed'] = 1
        with open(phase1_dir / 'run_summary.json', 'w') as f:
            json.dump(summary, f)

        result = run_quality_gate(phase1_dir, min_records=10, min_confidence=0.5, min_papers=3)
        assert result['passed'] is False
        assert any('Insufficient papers' in w for w in result['warnings'])

    print('  ✓ test_quality_gate_logic')


def test_bridge_manifest_generation():
    from bridge_pipeline import generate_bridge_manifest

    manifest = generate_bridge_manifest(
        run_dir=Path('/tmp/test_bridge'),
        bridge_id='bridge_20260530000001',
        domain='pva_bopet',
        mode='full',
        status='initialized',
        phases={
            'phase1': {'status': 'pending', 'skill': 'test'},
            'quality_gate': {'status': 'pending'},
            'transform': {'status': 'pending'},
            'phase2': {'status': 'pending', 'skill': 'test'},
        },
    )

    assert manifest['bridge_id'] == 'bridge_20260530000001'
    assert manifest['domain'] == 'pva_bopet'
    assert manifest['mode'] == 'full'
    assert manifest['status'] == 'initialized'
    assert 'phase1' in manifest['phases']
    assert 'quality_gate' in manifest['phases']
    assert 'transform' in manifest['phases']
    assert 'phase2' in manifest['phases']
    assert 'created_at' in manifest

    print('  ✓ test_bridge_manifest_generation')


def test_schema_validation():
    schema_path = Path(__file__).resolve().parent.parent / 'schemas' / 'bridge_manifest.schema.json'

    assert schema_path.exists(), f'Schema file not found: {schema_path}'

    with open(schema_path, 'r') as f:
        schema = json.load(f)

    assert schema['$id'] == 'https://literature-to-lab-bridge.skill/schemas/bridge_manifest.schema.json'
    assert schema['title'] == 'Bridge Manifest'
    assert 'bridge_id' in schema['required']
    assert 'phases' in schema['required']

    # Validate a valid manifest against schema
    try:
        import jsonschema
    except ImportError:
        print('  ⚠ jsonschema not installed, skipping validation test')
        return

    valid_manifest = {
        'bridge_id': 'bridge_20260530000001',
        'domain': 'pva_bopet',
        'mode': 'full',
        'status': 'initialized',
        'phases': {
            'phase1': {'status': 'pending', 'skill': 'test'},
            'quality_gate': {'status': 'pending', 'checks': []},
            'transform': {'status': 'pending'},
            'phase2': {'status': 'pending', 'skill': 'test'},
        },
        'run_dir': '/tmp/test',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }

    jsonschema.validate(valid_manifest, schema)
    print('  ✓ test_schema_validation (valid manifest)')

    # Invalid manifest (missing required phase)
    invalid_manifest = {
        'bridge_id': 'bridge_20260530000001',
        'domain': 'pva_bopet',
        'mode': 'full',
        'status': 'initialized',
        'phases': {
            'phase1': {'status': 'pending', 'skill': 'test'},
        },
        'run_dir': '/tmp/test',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }

    try:
        jsonschema.validate(invalid_manifest, schema)
        assert False, 'Should have raised ValidationError'
    except jsonschema.ValidationError:
        pass

    print('  ✓ test_schema_validation (invalid manifest rejected)')


def test_slugify_special_cases():
    assert slugify('  Oxygen Transmission Rate  ') == 'otr'
    assert slugify('Glass Transition Temperature') == 'tg'
    assert slugify('Melting Temperature') == 'tm'
    assert slugify('Decomposition Temperature') == 'td'
    assert slugify('Contact Angle') == 'contact_angle'
    assert slugify('Crystallinity') == 'crystallinity'
    assert slugify('SomeCustomProperty') == 'somecustomproperty'
    print('  ✓ test_slugify_special_cases')


def main():
    print('\n=== Literature-to-Lab Bridge Integration Tests ===\n')

    test_slugify()
    test_slugify_special_cases()
    test_is_spectral_property()
    test_detect_spectral_data()
    test_map_basic_record()
    test_map_additive_record()
    test_map_low_confidence()
    test_map_multiple_properties()
    test_transform_with_filtering()
    test_transform_empty_input()
    test_transform_file_not_found()
    test_quality_gate_logic()
    test_bridge_manifest_generation()
    test_schema_validation()

    print('\n=== All tests passed ✓ ===\n')


if __name__ == '__main__':
    main()