#!/usr/bin/env python3
"""Cleaning Integrity Verification — Phase 2.2.5 gate extracted from data-processor protocol.

Verifies that data cleaning did not damage the dataset, and auto-falls-back to the
raw data source when severe damage is detected. Handles four integrity checks:

1. row_count_check     — cleaned rows <= raw rows, drop_rate < threshold
2. type_integrity      — numeric columns actually numeric; repairs string-type leakage
3. range_fidelity      — cleaned min/max/mean vs raw; flags drift beyond threshold
4. batch_identity      — detects split/duplicate batch records (v6.6)

Auto-decides data_source (cleaned | raw_fallback). Result is written into
data_quality_report.json as the cleaning_integrity block. Downstream agents
read this single block instead of re-running cleaning verification.

Usage:
    uv run python cleaning_integrity_check.py <run_dir> <data_path> [<cleaned_csv>] \\
        [--numeric-cols A,B,C] [--group-col G] [--drop-threshold 0.20] \\
        [--range-threshold 0.10]

Outputs:
    02_processed/data_quality_report.json (cleaning_integrity block updated)
    02_processed/cleaning_integrity.json   (standalone copy)
    02_processed/duplicate_batch_report.csv (if split batches detected)
"""
import argparse
import json
import os
import sys

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed in venv. Run node scripts/uv_env_setup.mjs first.", file=sys.stderr)
    sys.exit(2)


BATCH_ID_COL_CANDIDATES = ('batch_id', 'batch', 'lot', 'lot_id', 'batchno', '批次')


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _resolve_numeric_cols(cleaned, ontology_path, input_manifest_path, explicit):
    """Resolve which columns SHOULD be numeric from explicit list, ontology, or input_manifest."""
    if explicit:
        return [c.strip() for c in explicit.split(',') if c.strip()]

    # Try ontology.json
    onto = _load_json(ontology_path)
    if onto and isinstance(onto.get('parameters'), list):
        cols = [p.get('name') for p in onto['parameters']
                if p.get('name') and p.get('type', '').lower() in ('number', 'float', 'int', 'integer', 'numeric')]
        if cols:
            return [c for c in cols if c in cleaned.columns]

    # Try input_manifest.json
    im = _load_json(input_manifest_path)
    if im and isinstance(im.get('columns'), list):
        return [c.get('name') for c in im['columns']
                if c.get('name') and c.get('type', '').lower() in ('number', 'float', 'int', 'integer', 'numeric')
                and c.get('name') in cleaned.columns]

    # Fallback: detect numeric columns heuristically from cleaned data
    inferred = []
    for c in cleaned.columns:
        coerced = pd.to_numeric(cleaned[c], errors='coerce')
        if coerced.notna().mean() >= 0.5:
            inferred.append(c)
    return inferred


def check_row_count(raw_df, cleaned_df, drop_threshold):
    raw_n = len(raw_df)
    cleaned_n = len(cleaned_df)
    dropped = raw_n - cleaned_n
    drop_rate = round(dropped / max(raw_n, 1), 4)
    severe = drop_rate > drop_threshold
    return {
        'raw_rows': raw_n,
        'cleaned_rows': cleaned_n,
        'dropped': dropped,
        'drop_rate': drop_rate,
        'threshold_exceeded': severe,
    }, severe


def check_type_integrity(cleaned_df, numeric_cols):
    """Detect string-type leakage; repair in place when ≥50% coercible."""
    issues = {}
    repaired_cols = []
    for c in numeric_cols:
        if c not in cleaned_df.columns:
            continue
        if cleaned_df[c].dtype not in ('float64', 'int64', 'float32', 'int32'):
            coerced = pd.to_numeric(cleaned_df[c], errors='coerce')
            ok_rate = float(coerced.notna().mean()) if len(coerced) else 0.0
            if ok_rate >= 0.5:
                # in-place repair
                stray_count = int(cleaned_df[c].isna().sum()) if hasattr(cleaned_df[c], 'isna') else 0
                cleaned_df[c] = coerced
                issues[c] = {'leaked': True, 'repaired': True, 'ok_rate': round(ok_rate, 3),
                             'stray_tokens_repaired': stray_count}
                repaired_cols.append(c)
            else:
                issues[c] = {'leaked': True, 'repaired': False, 'ok_rate': round(ok_rate, 3)}
    severe = any(v.get('leaked') and not v.get('repaired') for v in issues.values())
    return issues, repaired_cols, severe


def check_range_fidelity(raw_df, cleaned_df, numeric_cols, range_threshold):
    """Flag columns where cleaned mean drifts > threshold from raw mean."""
    drift = {}
    severe_cols = []
    for c in numeric_cols:
        if c not in cleaned_df.columns or c not in raw_df.columns:
            continue
        if cleaned_df[c].dtype not in ('float64', 'int64', 'float32', 'int32'):
            continue
        raw_n = pd.to_numeric(raw_df[c], errors='coerce')
        if raw_n.empty or raw_n.mean() in (None, 0) or abs(raw_n.mean()) < 1e-9:
            drift[c] = 0.0
            continue
        rel = abs(cleaned_df[c].mean() - raw_n.mean()) / (abs(raw_n.mean()) + 1e-9)
        drift[c] = round(float(rel), 4)
        if rel > range_threshold:
            severe_cols.append(c)
    return drift, severe_cols


def check_batch_identity(cleaned_df, run_dir):
    """Detect split/duplicate batch records (v6.6). Returns batch_dup dict + severe flag."""
    batch_dup = {'applicable': False, 'id_col': None, 'duplicate_batches': [],
                 'split_record_count': 0, 'action': 'none'}
    batch_cols = [c for c in cleaned_df.columns
                  if str(c).lower() in BATCH_ID_COL_CANDIDATES]
    if not batch_cols:
        return batch_dup, False

    bid = batch_cols[0]
    vc = cleaned_df[bid].astype(str).value_counts()
    dups = vc[vc > 1].index.tolist()
    batch_dup = {
        'applicable': True,
        'id_col': bid,
        'duplicate_batches': dups,
        'split_record_count': int(vc[vc > 1].sum() - len(dups)),
        'action': 'merge_or_flag' if dups else 'none',
    }
    if dups:
        dup_rows = cleaned_df[cleaned_df[bid].astype(str).isin(dups)].sort_values(bid)
        out_csv = os.path.join(run_dir, '02_processed', 'duplicate_batch_report.csv')
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)
        dup_rows.to_csv(out_csv, index=False)
        # NOTE: batch identity is a data-quality FIX, not a damage trigger for raw_fallback
        return batch_dup, False
    return batch_dup, False


def main():
    ap = argparse.ArgumentParser(description='Cleaning integrity verification (Phase 2.2.5 gate)')
    ap.add_argument('run_dir')
    ap.add_argument('data_path', help='raw data CSV path (DATA_PATH)')
    ap.add_argument('cleaned_csv', nargs='?', default=None,
                    help='cleaned data CSV; default <run_dir>/02_processed/cleaned_data.csv')
    ap.add_argument('--numeric-cols', default=None, help='comma-separated numeric column names (overrides ontology/input_manifest)')
    ap.add_argument('--group-col', default=None, help='group/batch column (overrides auto-detection)')
    ap.add_argument('--drop-threshold', type=float, default=0.20, help='drop_rate above this triggers raw_fallback')
    ap.add_argument('--range-threshold', type=float, default=0.10, help='mean drift above this triggers raw_fallback')
    ap.add_argument('--ontology', default=None, help='ontology.json path (default <run_dir>/01_ontology/ontology.json)')
    ap.add_argument('--input-manifest', default=None, help='input_manifest.json path (default <run_dir>/00_input/input_manifest.json)')
    args = ap.parse_args()

    run_dir = args.run_dir
    data_path = args.data_path
    cleaned_csv = args.cleaned_csv or os.path.join(run_dir, '02_processed', 'cleaned_data.csv')
    ontology_path = args.ontology or os.path.join(run_dir, '01_ontology', 'ontology.json')
    input_manifest_path = args.input_manifest or os.path.join(run_dir, '00_input', 'input_manifest.json')

    if not os.path.exists(cleaned_csv):
        # No cleaned data yet — skip gate, mark data_source as raw
        result = {
            'data_source': 'raw_fallback',
            'data_source_reason': f'cleaned_data.csv not found at {cleaned_csv}',
            'integrity_checks': {},
            'cleaning_operations': [],
            'repair_attempts': [],
        }
        _save_json(os.path.join(run_dir, '02_processed', 'cleaning_integrity.json'), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    raw_df = pd.read_csv(data_path)
    cleaned_df = pd.read_csv(cleaned_csv)

    numeric_cols = _resolve_numeric_cols(cleaned_df, ontology_path, input_manifest_path, args.numeric_cols)

    row_check, row_severe = check_row_count(raw_df, cleaned_df, args.drop_threshold)
    type_issues, repaired_cols, type_severe = check_type_integrity(cleaned_df, numeric_cols)
    range_drift, range_severe_cols = check_range_fidelity(raw_df, cleaned_df, numeric_cols, args.range_threshold)
    batch_dup, _ = check_batch_identity(cleaned_df, run_dir)

    # Determine data source — batch identity is a FIX, not a damage trigger
    trigger_fallback = row_severe or type_severe or bool(range_severe_cols)

    if repaired_cols:
        # Persist in-place repairs back to cleaned CSV
        cleaned_df.to_csv(cleaned_csv, index=False)

    fallback_reason = None
    if row_severe:
        fallback_reason = f'row_count drop_rate {row_check["drop_rate"]} > {args.drop_threshold}'
    elif type_severe:
        leaky = [c for c, v in type_issues.items() if v.get('leaked') and not v.get('repaired')]
        fallback_reason = f'type_integrity unrepaired leaky cols: {leaky}'
    elif range_severe_cols:
        fallback_reason = f'range_fidelity drift > {args.range_threshold} on: {range_severe_cols}'

    result = {
        'data_source': 'raw_fallback' if trigger_fallback else 'cleaned',
        'data_source_reason': fallback_reason or 'passed Phase 2.2.5 integrity checks',
        'integrity_checks': {
            'row_count_check': row_check,
            'type_integrity': type_issues,
            'range_fidelity': range_drift,
            'batch_identity_integrity': batch_dup,
        },
        'cleaning_operations': [],  # populated by data-processor agent in data_analysis_conclusion.json
        'repair_attempts': [f'in-place type_coerce on {c}' for c in repaired_cols],
    }

    out_json = os.path.join(run_dir, '02_processed', 'cleaning_integrity.json')
    _save_json(out_json, result)

    # Merge into data_quality_report.json if it exists
    dq_path = os.path.join(run_dir, '02_processed', 'data_quality_report.json')
    dq = _load_json(dq_path, default={})
    dq['cleaning_integrity'] = result
    _save_json(dq_path, dq)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not trigger_fallback else 0)  # exit 0 even on fallback — flagging, not erroring


if __name__ == '__main__':
    main()
