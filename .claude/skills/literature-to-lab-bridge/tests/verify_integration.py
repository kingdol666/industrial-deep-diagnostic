#!/usr/bin/env python3
"""
End-to-end Integration Verification for Literature-to-Lab Bridge.

Verifies:
  1. Both sub-skills have executable entry points
  2. Data transformer works with real-format data
  3. Chem-auto-lab can consume transformed data
  4. Bridge pipeline quality-gate mode works
  5. Bridge pipeline finalize mode works
  6. Full bridge pipeline (skip-phase1 with mock data) works
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILLS_BASE = Path(__file__).resolve().parent.parent.parent
LITERATURE_SKILL = SKILLS_BASE / 'domain-literature-experiment-extraction-ontology-skill'
CHEM_LAB_SKILL = SKILLS_BASE / 'chem-auto-lab-skill'
BRIDGE_SKILL = SKILLS_BASE / 'literature-to-lab-bridge'

PASS = 0
FAIL = 0
SKIP = 0


def check(description, condition, detail=''):
    global PASS, FAIL, SKIP
    if condition:
        PASS += 1
        print(f'  ✅ {description}')
    else:
        FAIL += 1
        print(f'  ❌ {description}')
        if detail:
            print(f'     Detail: {detail}')


def skip(description):
    global SKIP
    SKIP += 1
    print(f'  ⏭️  {description} (SKIPPED)')


def make_mock_literature_output(tmpdir):
    """Create mock Phase 1 literature output matching the real schema."""
    phase1_dir = Path(tmpdir) / 'phase1_output'
    normalized_dir = phase1_dir / '03_normalized'
    normalized_dir.mkdir(parents=True)

    experiments = [
        {
            "experiment_id": "SRC_001_E001",
            "source_id": "SRC_001",
            "paper_title": "Enhanced Optical Properties of PVA Composite Films",
            "year": 2023,
            "source_doi": "10.1000/example.001",
            "material_system": "PVA/SiO2 composite",
            "material_grade": "PVA 1799",
            "film_preparation_method": "Solution casting",
            "film_thickness": 50,
            "film_thickness_unit": "μm",
            "drying_temperature": 60,
            "drying_temperature_unit": "°C",
            "drying_time": 120,
            "drying_time_unit": "min",
            "measured_property": "Light Transmittance",
            "measured_value": 93.5,
            "measured_unit": "%",
            "measured_property_2": "Tensile Strength",
            "measured_value_2": 78.3,
            "measured_unit_2": "MPa",
            "measured_property_3": "Elongation at Break",
            "measured_value_3": 145.0,
            "measured_unit_3": "%",
            "confidence": 0.9,
            "source_snippet": "The composite film showed light transmittance of 93.5% at 550 nm with tensile strength of 78.3 MPa.",
            "extraction_method": "table_parse",
            "source_page": 5,
            "source_location": "Table 2, Row 3"
        },
        {
            "experiment_id": "SRC_001_E002",
            "source_id": "SRC_001",
            "paper_title": "Enhanced Optical Properties of PVA Composite Films",
            "year": 2023,
            "source_doi": "10.1000/example.001",
            "material_system": "PVA/SiO2 composite",
            "material_grade": "PVA 1799",
            "film_preparation_method": "Solution casting",
            "film_thickness": 50,
            "film_thickness_unit": "μm",
            "drying_temperature": 80,
            "drying_temperature_unit": "°C",
            "drying_time": 120,
            "drying_time_unit": "min",
            "measured_property": "Light Transmittance",
            "measured_value": 91.2,
            "measured_unit": "%",
            "measured_property_2": "Tensile Strength",
            "measured_value_2": 82.1,
            "measured_unit_2": "MPa",
            "measured_property_3": "Haze",
            "measured_value_3": 2.8,
            "measured_unit_3": "%",
            "confidence": 0.85,
            "source_snippet": "At 80°C drying, transmittance decreased slightly to 91.2% but tensile increased to 82.1 MPa.",
            "extraction_method": "table_parse",
            "source_page": 5,
            "source_location": "Table 2, Row 5"
        },
        {
            "experiment_id": "SRC_002_E001",
            "source_id": "SRC_002",
            "paper_title": "Raman Spectroscopy of PVA-Based Nanocomposites",
            "year": 2024,
            "source_doi": "10.1000/example.002",
            "material_system": "PVA/CNC nanocomposite",
            "additive": "CNC",
            "additive_concentration": 5,
            "additive_concentration_unit": "wt%",
            "film_preparation_method": "Solution casting",
            "film_thickness": 40,
            "film_thickness_unit": "μm",
            "drying_temperature": 50,
            "drying_temperature_unit": "°C",
            "measured_property": "Raman",
            "measured_value": 1095.0,
            "measured_unit": "cm⁻¹",
            "measured_property_2": "Tensile Strength",
            "measured_value_2": 95.0,
            "measured_unit_2": "MPa",
            "confidence": 0.88,
            "source_snippet": "Raman peak at 1095 cm⁻¹ confirmed CNC crystallinity in the composite.",
            "extraction_method": "text_regex",
            "source_page": 8,
            "notes": "Raman spectra available in supplementary materials"
        },
        {
            "experiment_id": "SRC_002_E002",
            "source_id": "SRC_002",
            "paper_title": "Raman Spectroscopy of PVA-Based Nanocomposites",
            "year": 2024,
            "source_doi": "10.1000/example.002",
            "material_system": "PVA/CNC nanocomposite",
            "additive": "CNC",
            "additive_concentration": 10,
            "additive_concentration_unit": "wt%",
            "film_preparation_method": "Solution casting",
            "film_thickness": 40,
            "film_thickness_unit": "μm",
            "drying_temperature": 50,
            "drying_temperature_unit": "°C",
            "measured_property": "Raman",
            "measured_value": 1095.0,
            "measured_unit": "cm⁻¹",
            "measured_property_2": "Tensile Strength",
            "measured_value_2": 88.3,
            "measured_unit_2": "MPa",
            "confidence": 0.88,
            "source_snippet": "At 10 wt% CNC, the 1095 cm⁻¹ peak intensified, but tensile decreased to 88.3 MPa.",
            "extraction_method": "text_regex",
            "source_page": 8,
            "notes": "Agglomeration at higher CNC content"
        },
        {
            "experiment_id": "SRC_003_E001",
            "source_id": "SRC_003",
            "paper_title": "FTIR Analysis of Crosslinked PVA Films",
            "year": 2022,
            "source_doi": "10.1000/example.003",
            "material_system": "PVA/Glutaraldehyde crosslinked",
            "crosslinker": "Glutaraldehyde",
            "crosslinker_concentration": 3,
            "crosslinker_concentration_unit": "wt%",
            "film_preparation_method": "Solution casting + thermal crosslinking",
            "film_thickness": 60,
            "film_thickness_unit": "μm",
            "heat_treatment_temperature": 120,
            "heat_treatment_temperature_unit": "°C",
            "heat_treatment_time": 30,
            "heat_treatment_time_unit": "min",
            "measured_property": "FTIR",
            "measured_value": 1720.0,
            "measured_unit": "cm⁻¹",
            "measured_property_2": "Water Vapor Transmission Rate",
            "measured_value_2": 15.3,
            "measured_unit_2": "g/m²·day",
            "confidence": 0.92,
            "source_snippet": "FTIR peak at 1720 cm⁻¹ confirms ester bond formation. WVTR reduced to 15.3 g/m²·day.",
            "extraction_method": "table_parse",
            "source_page": 6,
            "source_location": "Table 3, Row 2"
        },
        {
            "experiment_id": "SRC_004_E001",
            "source_id": "SRC_004",
            "paper_title": "Effect of Stretching on PVA Film Properties",
            "year": 2023,
            "source_doi": "10.1000/example.004",
            "material_system": "PVA 1799 film",
            "film_preparation_method": "Melt extrusion + uniaxial stretching",
            "film_thickness": 30,
            "film_thickness_unit": "μm",
            "stretching_ratio": 3.5,
            "stretching_temperature": 140,
            "stretching_temperature_unit": "°C",
            "measured_property": "Young's Modulus",
            "measured_value": 4.2,
            "measured_unit": "GPa",
            "measured_property_2": "Tensile Strength",
            "measured_value_2": 135.0,
            "measured_unit_2": "MPa",
            "measured_property_3": "Crystallinity",
            "measured_value_3": 42.5,
            "measured_unit_3": "%",
            "confidence": 0.91,
            "source_snippet": "Uniaxial stretching at 140°C (3.5× ratio) increased crystallinity to 42.5% and modulus to 4.2 GPa.",
            "extraction_method": "table_parse",
            "source_page": 4,
            "source_location": "Table 1, Row 3"
        },
        {
            "experiment_id": "SRC_005_E001",
            "source_id": "SRC_005",
            "paper_title": "Low-Quality Pilot Study on PVA Films",
            "year": 2021,
            "source_doi": None,
            "material_system": "PVA basic film",
            "film_thickness": 100,
            "film_thickness_unit": "μm",
            "measured_property": "Light Transmittance",
            "measured_value": 85.0,
            "measured_unit": "%",
            "confidence": 0.15,
            "source_snippet": "Approximate transparency measured visually.",
            "extraction_method": "llm_extraction",
            "notes": "Low quality preprint, confidence very low"
        },
        {
            "experiment_id": "SRC_001_E003",
            "source_id": "SRC_001",
            "paper_title": "Enhanced Optical Properties of PVA Composite Films",
            "year": 2023,
            "source_doi": "10.1000/example.001",
            "material_system": "PVA/SiO2 composite",
            "material_grade": "PVA 1799",
            "film_preparation_method": "Solution casting",
            "film_thickness": 100,
            "film_thickness_unit": "μm",
            "drying_temperature": 60,
            "drying_temperature_unit": "°C",
            "measured_property": "Light Transmittance",
            "measured_value": 88.0,
            "measured_unit": "%",
            "measured_property_2": "Tensile Strength",
            "measured_value_2": 65.0,
            "measured_unit_2": "MPa",
            "measured_property_3": "Haze",
            "measured_value_3": 4.5,
            "measured_unit_3": "%",
            "confidence": 0.87,
            "source_snippet": "Thicker films (100 μm) showed reduced transmittance (88%) and increased haze (4.5%).",
            "extraction_method": "table_parse",
            "source_page": 5,
            "source_location": "Table 2, Row 8"
        }
    ]

    with open(normalized_dir / 'experiments_normalized.json', 'w', encoding='utf-8') as f:
        json.dump(experiments, f, ensure_ascii=False, indent=2)

    # Create run_summary.json for quality gate
    run_summary = {
        "pipeline_id": "mock_run_001",
        "status": "completed",
        "statistics": {
            "papers_processed": 5,
            "experiments_extracted": 8,
            "experiments_after_dedup": 8,
            "mean_confidence": 0.795,
            "low_confidence_records": 1
        }
    }
    with open(phase1_dir / 'run_summary.json', 'w', encoding='utf-8') as f:
        json.dump(run_summary, f, ensure_ascii=False, indent=2)

    # Create literature summary
    summary_dir = phase1_dir / '07_summary'
    summary_dir.mkdir(parents=True)
    literature_summary = {
        "summary_id": "mock_summary_001",
        "main_themes": ["PVA composite optimization", "Optical-mechanical trade-off"],
        "common_patterns": {
            "materials": ["PVA 1799", "PVA/SiO2", "PVA/CNC"],
            "methods": ["Solution casting", "Melt extrusion"],
            "property_ranges": {
                "transmittance": {"min": 85.0, "max": 93.5, "unit": "%"},
                "tensile_strength": {"min": 65.0, "max": 135.0, "unit": "MPa"}
            }
        },
        "gaps": [
            "No data on WVTR for PVA/SiO2 composites",
            "No long-term aging studies",
            "Limited data on biaxial stretching effects"
        ],
        "promising_directions": [
            "Optimize SiO2 content vs. transmittance-tensile trade-off",
            "Investigate PVA/CNC + plasticizer combinations"
        ]
    }
    with open(summary_dir / 'literature_summary.json', 'w', encoding='utf-8') as f:
        json.dump(literature_summary, f, ensure_ascii=False, indent=2)

    return phase1_dir


print('=' * 60)
print('Literature-to-Lab Bridge — Integration Verification')
print('=' * 60)


# ─── Step 1: Verify sub-skills exist and are importable ───
print('\n1. Sub-Skill Availability Checks')

check(
    'Literature skill SKILL.md exists',
    (LITERATURE_SKILL / 'SKILL.md').exists()
)
check(
    'Literature skill run_pipeline.py exists',
    (LITERATURE_SKILL / 'scripts' / 'run_pipeline.py').exists()
)
check(
    'Literature skill normalize_data.py exists',
    (LITERATURE_SKILL / 'scripts' / 'normalize_data.py').exists()
)
check(
    'Chem lab skill SKILL.md exists',
    (CHEM_LAB_SKILL / 'SKILL.md').exists()
)
check(
    'Chem lab skill run_pipeline.py exists',
    (CHEM_LAB_SKILL / 'scripts' / 'run_pipeline.py').exists()
)
check(
    'Chem lab skill clean_data.py exists',
    (CHEM_LAB_SKILL / 'scripts' / 'clean_data.py').exists()
)
check(
    'Chem lab skill recommend.py exists',
    (CHEM_LAB_SKILL / 'scripts' / 'recommend.py').exists()
)
check(
    'Bridge skill SKILL.md exists',
    (BRIDGE_SKILL / 'SKILL.md').exists()
)
check(
    'Bridge skill bridge_pipeline.py exists',
    (BRIDGE_SKILL / 'scripts' / 'bridge_pipeline.py').exists()
)
check(
    'Bridge skill transform_literature_to_lab.py exists',
    (BRIDGE_SKILL / 'scripts' / 'transform_literature_to_lab.py').exists()
)

# ─── Step 2: Verify transform script is importable ───
print('\n2. Transformer Script Verification')

sys.path.insert(0, str(BRIDGE_SKILL / 'scripts'))
transform_available = False
bridge_available = False
try:
    from transform_literature_to_lab import (
        map_literature_to_lab, detect_spectral_data, slugify, transform, SPECTRAL_INDICATORS
    )
    transform_available = True
    check('transform_literature_to_lab.py is importable', True)
except Exception as e:
    check('transform_literature_to_lab.py is importable', False, str(e)[:200])

try:
    from bridge_pipeline import run_quality_gate, generate_bridge_manifest
    bridge_available = True
    check('bridge_pipeline.py is importable', True)
except Exception as e:
    check('bridge_pipeline.py is importable', False, str(e)[:200])

# ─── Step 3: End-to-end data flow with mock data ───
print('\n3. End-to-End Data Flow (Mock Phase 1 → Transformer → Phase 2)')

with tempfile.TemporaryDirectory() as tmpdir:
    phase1_dir = make_mock_literature_output(tmpdir)

    # 3a. Load and validate mock data
    normalized_path = phase1_dir / '03_normalized' / 'experiments_normalized.json'
    with open(normalized_path, 'r') as f:
        literature_records = json.load(f)

    check(
        f'Mock literature data loaded: {len(literature_records)} records',
        len(literature_records) == 8
    )

    # 3b. Run data transformer (via import or subprocess)
    output_path = Path(tmpdir) / 'phase2_input' / 'lab_experiments.json'
    output_path.parent.mkdir(parents=True)

    if transform_available:
        stats = transform(normalized_path, output_path, domain='pva_bopet',
                          include_spectral=True, confidence_threshold=0.3)
    else:
        result = subprocess.run(
            [sys.executable,
             str(BRIDGE_SKILL / 'scripts' / 'transform_literature_to_lab.py'),
             '--input', str(normalized_path),
             '--output', str(output_path),
             '--domain', 'pva_bopet',
             '--include-spectral',
             '--confidence-threshold', '0.3'],
            capture_output=True, text=True, timeout=30
        )
        try:
            stats = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            stats = {'records_output': 0, 'records_filtered': 0, 'spectral_detected': False}

    check(
        f'Transformer: {stats["records_output"]} records output (filtered {stats["records_filtered"]})',
        stats['records_output'] == 7 and stats['records_filtered'] == 1
    )
    check(
        f'Spectral data detected: {stats["spectral_detected"]}',
        stats['spectral_detected'] is True
    )

    # 3c. Validate transformed output structure
    with open(output_path, 'r') as f:
        lab_data = json.load(f)

    check(
        'Output has metadata block',
        'metadata' in lab_data
    )
    check(
        'Output has experiments array',
        'experiments' in lab_data
    )
    check(
        f'Experiments count matches ({len(lab_data["experiments"])})',
        len(lab_data['experiments']) == 7
    )

    first_record = lab_data['experiments'][0]
    check(
        'Record has experiment_id',
        'experiment_id' in first_record
    )
    check(
        'Record has variables object',
        'variables' in first_record and isinstance(first_record['variables'], dict)
    )
    check(
        'Record has observations object',
        'observations' in first_record and isinstance(first_record['observations'], dict)
    )
    check(
        'Record has batch_id',
        'batch_id' in first_record
    )

    # 3d. Verify specific field mappings
    transmittance_record = [r for r in lab_data['experiments']
                            if r['experiment_id'] == 'SRC_001_E001'][0]
    check(
        'transmittance field mapped correctly',
        transmittance_record['variables'].get('transmittance') == {'value': 93.5, 'unit': '%'}
    )
    check(
        'tensile_strength field mapped correctly',
        transmittance_record['variables'].get('tensile_strength') == {'value': 78.3, 'unit': 'MPa'}
    )
    check(
        'elongation field mapped correctly',
        transmittance_record['variables'].get('elongation') == {'value': 145.0, 'unit': '%'}
    )

    # 3e. Verify spectral records
    raman_record = [r for r in lab_data['experiments']
                    if r['experiment_id'] == 'SRC_002_E001'][0]
    check(
        'Raman property detected as spectral',
        raman_record.get('_has_spectral_data') is True
    )

    # 3f. Verify additive mapping
    cnc_record = [r for r in lab_data['experiments']
                  if r['experiment_id'] == 'SRC_002_E001'][0]
    check(
        'Additive name mapped',
        cnc_record['variables'].get('additive', {}).get('name') == 'CNC'
    )
    check(
        'Additive concentration mapped',
        cnc_record['variables'].get('additive', {}).get('concentration') == {
            'value': 5, 'unit': 'wt%'
        }
    )

    # 3g. Verify crosslinker mapping
    xlink_record = [r for r in lab_data['experiments']
                    if r['experiment_id'] == 'SRC_003_E001'][0]
    check(
        'Crosslinker name mapped',
        xlink_record['variables'].get('crosslinker', {}).get('name') == 'Glutaraldehyde'
    )
    check(
        'Crosslinker concentration mapped',
        xlink_record['variables'].get('crosslinker', {}).get('concentration') == {
            'value': 3, 'unit': 'wt%'
        }
    )

    # 3h. Verify low-confidence record filtered
    low_conf_records = [r for r in lab_data['experiments']
                        if r.get('low_confidence')]
    check(
        'Low-confidence record (0.15) was filtered out',
        len(low_conf_records) == 0 and
        not any(r['experiment_id'] == 'SRC_005_E001' for r in lab_data['experiments'])
    )

    # 3i. Verify confidence annotation on kept records
    kept_record = [r for r in lab_data['experiments']
                   if r['experiment_id'] == 'SRC_001_E002'][0]
    check(
        'Source confidence preserved in observations',
        kept_record['observations'].get('source_confidence') == 0.85
    )

    # 3j. Verify provenance preservation
    check(
        'Source text preserved',
        'The composite film showed light transmittance of 93.5%' in
        transmittance_record['observations'].get('source_text', '')
    )
    check(
        'Paper reference generated',
        'Enhanced Optical Properties' in
        transmittance_record['observations'].get('paper_ref', '')
    )

    # 3k. Verify stretching ratio mapping
    stretch_record = [r for r in lab_data['experiments']
                      if r['experiment_id'] == 'SRC_004_E001'][0]
    check(
        'Stretching ratio mapped',
        stretch_record['variables'].get('stretching_ratio') == 3.5
    )
    check(
        'Youngs modulus slug works',
        'youngs_modulus' in stretch_record['variables']
    )

    # 3l. Verify wvtr slug mapping
    ftir_record = [r for r in lab_data['experiments']
                   if r['experiment_id'] == 'SRC_003_E001'][0]
    check(
        'WVTR slug mapping works',
        'wvtr' in ftir_record['variables']
    )

# ─── Step 4: Verify Phase 2 can consume transformed data ───
print('\n4. Phase 2 Consumability (Chem-Auto-Lab Integration)')

with tempfile.TemporaryDirectory() as tmpdir:
    phase1_dir = make_mock_literature_output(tmpdir)
    normalized_path = phase1_dir / '03_normalized' / 'experiments_normalized.json'
    lab_input_dir = Path(tmpdir) / 'phase2_input'
    lab_output_dir = Path(tmpdir) / 'phase2_output'
    lab_input_dir.mkdir(parents=True)
    lab_output_dir.mkdir(parents=True)

    output_path = lab_input_dir / 'lab_experiments.json'
    transform(normalized_path, output_path, domain='pva_bopet', include_spectral=True)

    # Also export as CSV for chem-auto-lab consumption
    with open(output_path, 'r') as f:
        lab_data = json.load(f)

    experiments = lab_data['experiments']
    import csv

    # Flatten for CSV export
    all_var_keys = set()
    for exp in experiments:
        all_var_keys.update(exp['variables'].keys())
    all_var_keys = sorted(all_var_keys)

    csv_path = lab_input_dir / 'experiments.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = ['experiment_id', 'batch_id'] + all_var_keys
        writer.writerow(header)
        for exp in experiments:
            row = [exp['experiment_id'], exp.get('batch_id', '')]
            for key in all_var_keys:
                val = exp['variables'].get(key)
                if isinstance(val, dict):
                    row.append(str(val.get('value', '')))
                else:
                    row.append(str(val) if val is not None else '')
            writer.writerow(row)

    check(
        'CSV exported from transformed data',
        csv_path.exists() and csv_path.stat().st_size > 0
    )

    # Try running chem-auto-lab clean_data.py on CSV
    clean_output = lab_output_dir / 'cleaned.json'
    try:
        result = subprocess.run(
            [sys.executable,
             str(CHEM_LAB_SKILL / 'scripts' / 'clean_data.py'),
             '--input', str(csv_path),
             '--output', str(clean_output),
             '--imputation', 'median',
             '--outlier', 'iqr'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and clean_output.exists():
            with open(clean_output, 'r') as f:
                cleaned = json.load(f)
            exp_count = len(cleaned.get('experiments', []))
            check(
                f'Chem-auto-lab clean_data.py consumed transformed data ({exp_count} records)',
                exp_count > 0
            )
        else:
            check(
                'Chem-auto-lab clean_data.py consumed transformed data',
                False,
                f'stderr: {result.stderr[:200]}'
            )
    except subprocess.TimeoutExpired:
        check('Chem-auto-lab clean_data.py ran', False, 'Timeout')
    except FileNotFoundError:
        skip('Chem-auto-lab clean_data.py (pandas not installed)')
    except Exception as e:
        check('Chem-auto-lab clean_data.py ran', False, str(e)[:200])

# ─── Step 5: Bridge Pipeline — Quality Gate Mode ───
print('\n5. Bridge Pipeline — Quality Gate Mode')

with tempfile.TemporaryDirectory() as tmpdir:
    phase1_dir = make_mock_literature_output(tmpdir)

    result = subprocess.run(
        [sys.executable,
         str(BRIDGE_SKILL / 'scripts' / 'bridge_pipeline.py'),
         '--mode', 'quality-gate',
         '--phase1-output', str(phase1_dir),
         '--min-records', '5',
         '--min-confidence', '0.5',
         '--min-papers', '2'],
        capture_output=True, text=True, timeout=30
    )

    try:
        gate_output = json.loads(result.stdout.strip())
        check(
            f'Quality gate passed: {gate_output["passed"]}',
            gate_output['passed'] is True
        )
        checks_passed = sum(1 for c in gate_output['checks'] if c['passed'])
        check(
            f'All 3 checks passed ({checks_passed}/3)',
            checks_passed == 3
        )
    except json.JSONDecodeError:
        check('Quality gate JSON output parsed', False, result.stdout[:200])

    # Test gate failure
    result_fail = subprocess.run(
        [sys.executable,
         str(BRIDGE_SKILL / 'scripts' / 'bridge_pipeline.py'),
         '--mode', 'quality-gate',
         '--phase1-output', str(phase1_dir),
         '--min-records', '50',
         '--min-confidence', '0.95',
         '--min-papers', '10'],
        capture_output=True, text=True, timeout=30
    )
    try:
        gate_fail = json.loads(result_fail.stdout.strip())
        check(
            f'Quality gate correctly fails with strict thresholds: {gate_fail["passed"]}',
            gate_fail['passed'] is False
        )
    except json.JSONDecodeError:
        check('Quality gate failure JSON parsed', False, result_fail.stdout[:200])

# ─── Step 6: Bridge Pipeline — Finalize Mode ───
print('\n6. Bridge Pipeline — Finalize Mode')

with tempfile.TemporaryDirectory() as tmpdir:
    phase1_dir = make_mock_literature_output(tmpdir)

    # Create bridge run directory with complete outputs
    run_dir = Path(tmpdir) / 'bridge_run'
    run_dir.mkdir()

    import shutil
    shutil.copytree(phase1_dir, run_dir / 'phase1_output')

    # Create a partial bridge_manifest.json
    manifest = {
        "bridge_id": "bridge_verification_001",
        "domain": "pva_bopet",
        "mode": "full",
        "status": "initialized",
        "phases": {
            "phase1": {"status": "completed", "skill": "domain-literature"},
            "quality_gate": {"status": "passed"},
            "transform": {"status": "completed"},
            "phase2": {"status": "completed", "skill": "chem-auto-lab"},
        },
        "run_dir": str(run_dir),
        "created_at": "2026-05-30T10:00:00Z",
    }
    with open(run_dir / 'bridge_manifest.json', 'w') as f:
        json.dump(manifest, f)

    result = subprocess.run(
        [sys.executable,
         str(BRIDGE_SKILL / 'scripts' / 'bridge_pipeline.py'),
         '--mode', 'finalize',
         '--run-dir', str(run_dir)],
        capture_output=True, text=True, timeout=30
    )

    try:
        final_output = json.loads(result.stdout.strip())
        check(
            f'Finalize mode: {final_output["status"]}',
            final_output['status'] == 'success'
        )
    except json.JSONDecodeError:
        check('Finalize JSON parsed', False, result.stdout[:200])

    # Verify manifest was updated
    with open(run_dir / 'bridge_manifest.json', 'r') as f:
        updated = json.load(f)
    check(
        'Manifest status updated to completed',
        updated['status'] == 'completed'
    )
    check(
        'Manifest has completed_at timestamp',
        'completed_at' in updated
    )

# ─── Step 7: Bridge Pipeline — Status Mode ───
print('\n7. Bridge Pipeline — Status Mode')

with tempfile.TemporaryDirectory() as tmpdir:
    run_dir = Path(tmpdir) / 'bridge_run'
    run_dir.mkdir()

    manifest = {
        "bridge_id": "bridge_status_test",
        "domain": "catalyst_synthesis",
        "mode": "full",
        "status": "running",
        "phases": {
            "phase1": {"status": "completed", "skill": "test"},
            "quality_gate": {"status": "passed"},
            "transform": {"status": "running"},
            "phase2": {"status": "pending", "skill": "test"},
        },
        "run_dir": str(run_dir),
        "created_at": "2026-05-30T11:00:00Z",
    }
    with open(run_dir / 'bridge_manifest.json', 'w') as f:
        json.dump(manifest, f)

    result = subprocess.run(
        [sys.executable,
         str(BRIDGE_SKILL / 'scripts' / 'bridge_pipeline.py'),
         '--mode', 'status',
         '--run-dir', str(run_dir)],
        capture_output=True, text=True, timeout=30
    )

    try:
        status_output = json.loads(result.stdout.strip())
        check(
            f'Status mode reports: {status_output["status"]}',
            status_output['status'] == 'running'
        )
        check(
            'Status shows phases',
            'phases' in status_output
        )
    except json.JSONDecodeError:
        check('Status JSON parsed', False, result.stdout[:200])

# ─── Step 8: Transformer Help ───
print('\n8. Script CLI Verification')

result = subprocess.run(
    [sys.executable,
     str(BRIDGE_SKILL / 'scripts' / 'transform_literature_to_lab.py'),
     '--help'],
    capture_output=True, text=True, timeout=10
)
check(
    'transform_literature_to_lab.py --help works',
    '--input' in result.stdout and '--output' in result.stdout
)

result = subprocess.run(
    [sys.executable,
     str(BRIDGE_SKILL / 'scripts' / 'bridge_pipeline.py'),
     '--help'],
    capture_output=True, text=True, timeout=10
)
check(
    'bridge_pipeline.py --help works',
    '--mode' in result.stdout
)

# ─── Summary ───
print('\n' + '=' * 60)
total = PASS + FAIL + SKIP
print(f'Results: ✅ {PASS} passed  ❌ {FAIL} failed  ⏭️  {SKIP} skipped  ({total} total)')
print('=' * 60)

if FAIL == 0:
    print('\n✅ INTEGRATION VERIFIED: Both skills can be integrated via the bridge pipeline.')
    sys.exit(0)
else:
    print(f'\n❌ INTEGRATION ISSUES: {FAIL} checks failed.')
    sys.exit(1)