#!/usr/bin/env python3
"""
Literature-to-Lab Bridge Pipeline Orchestrator

Manages the two-phase bridge pipeline:
  Phase 1: Literature search & experiment extraction (domain-literature skill)
  Quality Gate: Data sufficiency check
  Transform: Schema mapping (literature → lab format)
  Phase 2: Lab analysis & recommendations (chem-auto-lab skill)
  Finalize: Generate bridge manifest

Modes:
  full          — Run complete bridge pipeline
  quality-gate  — Check Phase 1 data sufficiency only
  finalize      — Generate bridge manifest from existing outputs
  status        — Report current bridge state
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def find_skill_dir(skill_name: str, base_path: Path) -> Optional[Path]:
    candidate = base_path / skill_name
    if candidate.exists() and (candidate / 'SKILL.md').exists():
        return candidate.resolve()
    return None


def write_event(log_path: Path, event: dict):
    event['timestamp'] = datetime.now(timezone.utc).isoformat()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def run_quality_gate(phase1_dir: Path, min_records: int, min_confidence: float, min_papers: int) -> dict:
    run_summary_path = phase1_dir / 'run_summary.json'
    if not run_summary_path.exists():
        return {
            'passed': False,
            'checks': [],
            'warnings': ['Phase 1 run_summary.json not found. Has Phase 1 completed?'],
            'fatal': True,
        }

    with open(run_summary_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    stats = summary.get('statistics', summary)
    records = stats.get('experiments_extracted', stats.get('experiments_after_dedup', 0))
    mean_conf = stats.get('mean_confidence', 0)
    papers = stats.get('papers_processed', 0)

    checks = []
    passed = True
    warnings = []

    check1 = {
        'check': 'min_records',
        'value': records,
        'threshold': min_records,
        'passed': records >= min_records,
        'message': f'Records extracted: {records} (threshold: {min_records})'
    }
    checks.append(check1)
    if not check1['passed']:
        passed = False
        warnings.append(f'Insufficient records ({records} < {min_records})')

    check2 = {
        'check': 'mean_confidence',
        'value': round(mean_conf, 3) if isinstance(mean_conf, (int, float)) else mean_conf,
        'threshold': min_confidence,
        'passed': isinstance(mean_conf, (int, float)) and mean_conf >= min_confidence,
        'message': f'Mean confidence: {mean_conf} (threshold: {min_confidence})'
    }
    checks.append(check2)
    if not check2['passed']:
        passed = False
        warnings.append(f'Low mean confidence ({mean_conf} < {min_confidence})')

    check3 = {
        'check': 'min_papers',
        'value': papers,
        'threshold': min_papers,
        'passed': papers >= min_papers,
        'message': f'Unique papers: {papers} (threshold: {min_papers})'
    }
    checks.append(check3)
    if not check3['passed']:
        passed = False
        warnings.append(f'Insufficient papers ({papers} < {min_papers})')

    return {
        'passed': passed,
        'checks': checks,
        'warnings': warnings,
        'fatal': False,
        'phase1_stats': {
            'papers_processed': papers,
            'experiments_extracted': records,
            'mean_confidence': mean_conf,
        }
    }


def run_transform(input_path: Path, output_path: Path, domain: str,
                  include_spectral: bool, confidence_threshold: float,
                  bridge_skill_dir: Path) -> dict:
    script = bridge_skill_dir / 'scripts' / 'transform_literature_to_lab.py'
    cmd = [
        sys.executable, str(script),
        '--input', str(input_path),
        '--output', str(output_path),
        '--domain', domain,
        '--confidence-threshold', str(confidence_threshold),
    ]
    if include_spectral:
        cmd.append('--include-spectral')

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            'status': 'error',
            'error': result.stderr.strip(),
            'stdout': result.stdout.strip(),
        }

    try:
        stats = json.loads(result.stdout.strip())
        return {'status': 'success', **stats}
    except json.JSONDecodeError:
        return {
            'status': 'error',
            'error': 'Failed to parse transformer output',
            'stdout': result.stdout.strip(),
        }


def run_phase1(literature_skill_dir: Path, input_dir: Path, output_dir: Path,
               domain: str, keywords: str, mode: str = 'full') -> dict:
    manifest = {
        'pipeline_id': f'lit_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}',
        'mode': mode,
        'domain': domain,
        'search_terms': [k.strip() for k in keywords.split(',') if k.strip()],
        'classified_inputs': {
            'papers': [],
            'web_articles': [],
            'supplementary_tables': [],
            'supplementary_docs': [],
            'pre_extracted_data': [],
            'unrecognized': [],
        },
    }
    manifest_path = input_dir / 'pipeline_manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    script = literature_skill_dir / 'scripts' / 'run_pipeline.py'
    cmd = [
        sys.executable, str(script),
        '--manifest', str(manifest_path),
        '--output-dir', str(output_dir),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        'returncode': result.returncode,
        'stdout': result.stdout.strip(),
        'stderr': result.stderr.strip(),
    }


def run_phase2(chem_lab_skill_dir: Path, input_dir: Path, output_dir: Path,
               mode: str = 'clean-and-report') -> dict:
    script = chem_lab_skill_dir / 'scripts' / 'run_pipeline.py'
    cmd = [
        sys.executable, str(script),
        '--input-dir', str(input_dir),
        '--output-dir', str(output_dir),
        '--mode', mode,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        'returncode': result.returncode,
        'stdout': result.stdout.strip(),
        'stderr': result.stderr.strip(),
    }


def generate_bridge_manifest(run_dir: Path, bridge_id: str, domain: str,
                             mode: str, status: str, phases: dict,
                             summary: dict = None) -> dict:
    manifest = {
        'bridge_id': bridge_id,
        'domain': domain,
        'mode': mode,
        'status': status,
        'phases': phases,
        'run_dir': str(run_dir.resolve()),
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    if summary:
        manifest['summary'] = summary
    return manifest


def detect_spectral_from_phase1(phase1_dir: Path) -> bool:
    candidates = [
        phase1_dir / '03_normalized' / 'experiments_normalized.json',
        phase1_dir / 'normalized_results.json',
        phase1_dir / 'experiments_normalized.json',
        phase1_dir / 'experiments.json',
    ]
    normalized_path = None
    for c in candidates:
        if c.exists():
            normalized_path = c
            break

    if normalized_path is None:
        return False

    with open(normalized_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = data if isinstance(data, list) else data.get('experiments', data.get('data', []))

    spectral_properties = {
        'FTIR', 'RAMAN', 'NMR', 'UV-VIS', 'UVVIS', 'HPLC', 'GC-MS', 'GCMS',
        'XRD', 'XPS', 'EDS', 'EDX'
    }

    for record in records:
        for i in range(1, 6):
            suffix = '' if i == 1 else f'_{i}'
            prop = str(record.get(f'measured_property{suffix}', '')).upper().strip()
            if prop in spectral_properties:
                return True

    return False


def main():
    parser = argparse.ArgumentParser(
        description='Literature-to-Lab Bridge Pipeline Orchestrator'
    )
    parser.add_argument(
        '--mode', required=True,
        choices=['full', 'quality-gate', 'finalize', 'status'],
        help='Bridge execution mode'
    )
    parser.add_argument('--run-dir', help='Bridge run directory')
    parser.add_argument('--phase1-output', help='Phase 1 output directory')
    parser.add_argument('--phase2-output', help='Phase 2 output directory')
    parser.add_argument('--domain', default='', help='Domain name')
    parser.add_argument('--search-keywords', default='', help='Literature search keywords')
    parser.add_argument('--min-records', type=int, default=10, help='Minimum experiment records')
    parser.add_argument('--min-confidence', type=float, default=0.5, help='Minimum mean confidence')
    parser.add_argument('--min-papers', type=int, default=3, help='Minimum unique papers')
    parser.add_argument('--skip-phase1', action='store_true', help='Skip Phase 1 (use existing output)')
    parser.add_argument('--skip-phase2', action='store_true', help='Skip Phase 2 (literature only)')
    parser.add_argument('--confidence-threshold', type=float, default=0.3,
                        help='Filter records below this confidence in transformer')
    args = parser.parse_args()

    # Resolve skill directories
    bridge_skill_dir = Path(__file__).resolve().parent.parent
    skills_base = bridge_skill_dir.parent
    literature_skill_dir = find_skill_dir(
        'domain-literature-experiment-extraction-ontology-skill', skills_base
    )
    chem_lab_skill_dir = find_skill_dir('chem-auto-lab-skill', skills_base)

    if not literature_skill_dir:
        print(json.dumps({
            'status': 'error',
            'error': 'domain-literature-experiment-extraction-ontology-skill not found',
            'searched_at': str(skills_base),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not chem_lab_skill_dir:
        print(json.dumps({
            'status': 'error',
            'error': 'chem-auto-lab-skill not found',
            'searched_at': str(skills_base),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    if args.mode == 'quality-gate':
        if not args.phase1_output:
            print(json.dumps({
                'status': 'error',
                'error': '--phase1-output is required for quality-gate mode',
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        phase1_dir = Path(args.phase1_output)
        result = run_quality_gate(
            phase1_dir, args.min_records, args.min_confidence, args.min_papers
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result['passed'] else 1)

    elif args.mode == 'finalize':
        if not args.run_dir:
            print(json.dumps({
                'status': 'error',
                'error': '--run-dir is required for finalize mode',
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        run_dir = Path(args.run_dir)
        manifest_path = run_dir / 'bridge_manifest.json'

        if not manifest_path.exists():
            print(json.dumps({
                'status': 'error',
                'error': f'bridge_manifest.json not found at {manifest_path}',
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Update status
        manifest['status'] = 'completed'
        manifest['completed_at'] = datetime.now(timezone.utc).isoformat()

        # Collect summary statistics
        phase1_summary_path = run_dir / 'phase1_output' / 'run_summary.json'
        if phase1_summary_path.exists():
            with open(phase1_summary_path, 'r', encoding='utf-8') as f:
                p1_summary = json.load(f)
            manifest['phases']['phase1']['statistics'] = p1_summary.get('statistics', p1_summary)

        phase2_manifest_path = run_dir / 'phase2_output' / 'pipeline_manifest.json'
        if phase2_manifest_path.exists():
            with open(phase2_manifest_path, 'r', encoding='utf-8') as f:
                p2_manifest = json.load(f)
            manifest['phases']['phase2']['statistics'] = p2_manifest.get('summary', p2_manifest)

        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(json.dumps({
            'status': 'success',
            'message': f'Bridge manifest finalized: {manifest_path}',
            'bridge_id': manifest['bridge_id'],
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    elif args.mode == 'status':
        if not args.run_dir:
            print(json.dumps({
                'status': 'error',
                'error': '--run-dir is required for status mode',
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        run_dir = Path(args.run_dir)
        manifest_path = run_dir / 'bridge_manifest.json'

        if not manifest_path.exists():
            print(json.dumps({
                'status': 'not_found',
                'error': f'No bridge manifest found at {manifest_path}',
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        print(json.dumps({
            'status': manifest.get('status', 'unknown'),
            'bridge_id': manifest.get('bridge_id'),
            'domain': manifest.get('domain'),
            'phases': manifest.get('phases', {}),
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    elif args.mode == 'full':
        # Full pipeline execution
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        bridge_id = f'bridge_{timestamp}'
        slug = args.domain or 'literature_lab'
        run_dir = Path(args.run_dir) if args.run_dir else (
            Path(__file__).resolve().parent.parent.parent.parent.parent /
            'workspace' / 'bridge-runs' / f'{bridge_id}_{slug}'
        )

        phase1_input = run_dir / 'phase1_input'
        phase1_output = run_dir / 'phase1_output'
        phase2_input = run_dir / 'phase2_input'
        phase2_output = run_dir / 'phase2_output'
        events_log = run_dir / '.bridge_events.jsonl'

        run_dir.mkdir(parents=True, exist_ok=True)

        phases_status = {
            'phase1': {'status': 'pending', 'skill': 'domain-literature-experiment-extraction-ontology-skill'},
            'quality_gate': {'status': 'pending'},
            'transform': {'status': 'pending'},
            'phase2': {'status': 'pending', 'skill': 'chem-auto-lab-skill'},
        }

        write_event(events_log, {
            'event': 'bridge_start',
            'bridge_id': bridge_id,
            'mode': 'full',
            'domain': args.domain,
        })

        # Phase 1
        if not args.skip_phase1:
            write_event(events_log, {
                'event': 'phase_start', 'phase': 1,
                'skill': 'domain-literature-experiment-extraction-ontology-skill',
            })

            p1_result = run_phase1(
                literature_skill_dir=literature_skill_dir,
                input_dir=phase1_input,
                output_dir=phase1_output,
                domain=args.domain,
                keywords=args.search_keywords,
            )

            if p1_result['returncode'] != 0:
                phases_status['phase1']['status'] = 'failed'
                phases_status['phase1']['error'] = p1_result['stderr'][:500]
                write_event(events_log, {
                    'event': 'phase_error', 'phase': 1,
                    'error': p1_result['stderr'][:500],
                })
                manifest = generate_bridge_manifest(
                    run_dir, bridge_id, args.domain, 'full', 'failed', phases_status
                )
                manifest_path = run_dir / 'bridge_manifest.json'
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)

                print(json.dumps({
                    'status': 'error',
                    'phase': 1,
                    'error': 'Phase 1 (literature extraction) failed',
                    'details': p1_result['stderr'][:1000],
                    'bridge_id': bridge_id,
                    'run_dir': str(run_dir),
                }, ensure_ascii=False, indent=2))
                sys.exit(1)

            phases_status['phase1']['status'] = 'completed'
            write_event(events_log, {
                'event': 'phase_complete', 'phase': 1,
            })
        else:
            phases_status['phase1']['status'] = 'skipped'

        # Quality Gate
        write_event(events_log, {'event': 'gate_start'})
        gate_result = run_quality_gate(
            phase1_output, args.min_records, args.min_confidence, args.min_papers
        )
        phases_status['quality_gate'] = {
            'status': 'passed' if gate_result['passed'] else 'failed',
            'checks': gate_result['checks'],
            'warnings': gate_result['warnings'],
        }
        write_event(events_log, {
            'event': 'gate_complete',
            'passed': gate_result['passed'],
            'checks': gate_result['checks'],
        })

        if not gate_result['passed'] and not gate_result.get('fatal'):
            manifest = generate_bridge_manifest(
                run_dir, bridge_id, args.domain, 'full', 'gate_failed', phases_status
            )
            manifest_path = run_dir / 'bridge_manifest.json'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            print(json.dumps({
                'status': 'gate_failed',
                'bridge_id': bridge_id,
                'run_dir': str(run_dir),
                'gate_result': gate_result,
                'message': 'Quality gate failed. Review the checks and re-run with adjusted parameters or more data.',
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        # Transform
        write_event(events_log, {'event': 'transform_start'})

        normalized_input_candidates = [
            phase1_output / '03_normalized' / 'experiments_normalized.json',
            phase1_output / 'normalized_results.json',
            phase1_output / 'experiments_normalized.json',
            phase1_output / 'experiments.json',
        ]
        normalized_input = None
        for candidate in normalized_input_candidates:
            if candidate.exists():
                normalized_input = candidate
                break

        if normalized_input is None:
            print(json.dumps({
                'status': 'error',
                'phase': 'transform',
                'error': 'No normalized experiment data found in Phase 1 output. '
                         f'Searched: {[str(c) for c in normalized_input_candidates]}',
                'bridge_id': bridge_id,
                'run_dir': str(run_dir),
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        spectral_detected = detect_spectral_from_phase1(phase1_output) if not args.skip_phase1 else False

        transform_result = run_transform(
            input_path=normalized_input,
            output_path=phase2_input / 'lab_experiments.json',
            domain=args.domain,
            include_spectral=spectral_detected,
            confidence_threshold=args.confidence_threshold,
            bridge_skill_dir=bridge_skill_dir,
        )

        phases_status['transform'] = {
            'status': transform_result['status'],
            'records_input': transform_result.get('records_input', 0),
            'records_output': transform_result.get('records_output', 0),
            'records_filtered': transform_result.get('records_filtered', 0),
            'spectral_detected': transform_result.get('spectral_detected', False),
        }
        write_event(events_log, {
            'event': 'transform_complete',
            'status': transform_result['status'],
        })

        if transform_result['status'] == 'error':
            print(json.dumps({
                'status': 'error',
                'phase': 'transform',
                'error': transform_result.get('error', 'Unknown transform error'),
                'bridge_id': bridge_id,
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        # Export CSV copy for chem-auto-lab scanner compatibility
        lab_json_path = phase2_input / 'lab_experiments.json'
        lab_csv_path = phase2_input / 'lab_experiments.csv'
        try:
            import csv as _csv_mod
            with open(lab_json_path, 'r', encoding='utf-8') as f:
                lab_data = json.load(f)
            experiments = lab_data.get('experiments', [])
            if experiments:
                all_keys = set()
                for exp in experiments:
                    all_keys.update(exp.get('variables', {}).keys())
                all_keys = sorted(all_keys)
                with open(lab_csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = _csv_mod.writer(f)
                    writer.writerow(['experiment_id', 'batch_id'] + all_keys)
                    for exp in experiments:
                        row = [exp.get('experiment_id', ''), exp.get('batch_id', '')]
                        for key in all_keys:
                            val = exp.get('variables', {}).get(key)
                            if isinstance(val, dict):
                                row.append(str(val.get('value', '')))
                            else:
                                row.append(str(val) if val is not None else '')
                        writer.writerow(row)
                write_event(events_log, {
                    'event': 'csv_export',
                    'path': str(lab_csv_path),
                    'rows': len(experiments),
                })
        except Exception as e:
            write_event(events_log, {
                'event': 'csv_export_error',
                'error': str(e),
            })

        # Phase 2
        if not args.skip_phase2:
            write_event(events_log, {
                'event': 'phase_start', 'phase': 2,
                'skill': 'chem-auto-lab-skill',
            })

            p2_result = run_phase2(
                chem_lab_skill_dir=chem_lab_skill_dir,
                input_dir=phase2_input,
                output_dir=phase2_output,
            )

            if p2_result['returncode'] != 0:
                phases_status['phase2']['status'] = 'failed'
                phases_status['phase2']['error'] = p2_result['stderr'][:500]
                write_event(events_log, {
                    'event': 'phase_error', 'phase': 2,
                    'error': p2_result['stderr'][:500],
                })
                manifest = generate_bridge_manifest(
                    run_dir, bridge_id, args.domain, 'full', 'phase2_failed', phases_status
                )
                manifest_path = run_dir / 'bridge_manifest.json'
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)

                print(json.dumps({
                    'status': 'partial_success',
                    'phase': 2,
                    'error': 'Phase 2 (lab analysis) failed, but Phase 1 outputs are preserved',
                    'details': p2_result['stderr'][:1000],
                    'bridge_id': bridge_id,
                    'run_dir': str(run_dir),
                }, ensure_ascii=False, indent=2))
                sys.exit(1)

            phases_status['phase2']['status'] = 'completed'
            write_event(events_log, {
                'event': 'phase_complete', 'phase': 2,
            })
        else:
            phases_status['phase2']['status'] = 'skipped'

        # Finalize
        phases_status['bridge'] = {'status': 'completed'}

        summary = {
            'total_papers': gate_result.get('phase1_stats', {}).get('papers_processed', 0),
            'total_experiments_analyzed': transform_result.get('records_output', 0),
            'spectral_analysis': spectral_detected,
            'key_outputs': [
                'phase1_output/03_normalized/experiments_normalized.json',
                'phase2_input/lab_experiments.json',
                'phase2_input/lab_experiments.csv',
            ],
        }
        if not args.skip_phase2:
            summary['key_outputs'].extend([
                'phase2_output/report.md',
                'phase2_output/recommendations.json',
                'phase2_output/figures/',
            ])

        manifest = generate_bridge_manifest(
            run_dir, bridge_id, args.domain, 'full', 'completed',
            phases_status, summary
        )
        manifest['completed_at'] = datetime.now(timezone.utc).isoformat()

        manifest_path = run_dir / 'bridge_manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        write_event(events_log, {
            'event': 'bridge_complete',
            'status': 'completed',
        })

        print(json.dumps({
            'status': 'success',
            'bridge_id': bridge_id,
            'run_dir': str(run_dir),
            'phases': {k: v.get('status') for k, v in phases_status.items()},
            'summary': summary,
        }, ensure_ascii=False, indent=2))
        sys.exit(0)


if __name__ == '__main__':
    main()