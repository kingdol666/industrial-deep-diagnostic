"""Batch identity integrity check.

Ported from cleaning_integrity_check.py (Phase 2.2.5 gate).
Detects split/duplicate batch records.

Usage: Typically called from stats/run.py; also usable standalone:
    python stats/batch_integrity.py <cleaned_data.csv>
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path


# ── Batch ID column name candidates (order = search priority) ──
BATCH_ID_COL_CANDIDATES = (
    'batch_id', 'batch', 'lot', 'lot_id', 'batchno',
    '\u6279\u6b21',  # 批次
)


def _infer_batch_col(columns):
    """Find the batch ID column from candidate names."""
    col_lower = {c.lower(): c for c in columns}
    for candidate in BATCH_ID_COL_CANDIDATES:
        if candidate in col_lower:
            return col_lower[candidate]
    return None


def check_batch_identity(rows, batch_col=None):
    """Detect split/duplicate batch records.

    Args:
        rows: list of dicts (data rows)
        batch_col: explicit batch column name; auto-detected if None

    Returns: (batch_dup dict, severe bool)
    """
    batch_dup = {
        'applicable': False,
        'id_col': None,
        'duplicate_batches': [],
        'split_record_count': 0,
        'action': 'none',
    }

    if not rows:
        return batch_dup, False

    columns = list(rows[0].keys())

    if batch_col is None:
        batch_col = _infer_batch_col(columns)

    if batch_col is None or batch_col not in columns:
        return batch_dup, False

    # Count occurrences of each batch ID
    batch_values = [str(row.get(batch_col, '')).strip() for row in rows]
    counter = Counter(v for v in batch_values if v)
    dups = [k for k, v in counter.items() if v > 1]

    batch_dup = {
        'applicable': True,
        'id_col': batch_col,
        'duplicate_batches': dups,
        'split_record_count': sum(v - 1 for k, v in counter.items() if v > 1),
        'action': 'merge_or_flag' if dups else 'none',
    }

    # Note: batch identity is a data-quality FIX, not a damage trigger for raw_fallback
    return batch_dup, False


def run_batch_checks(rows, run_dir, batch_col=None):
    """Run batch identity integrity check and write reports.

    Args:
        rows: list of dicts (data rows)
        run_dir: Path to run directory
        batch_col: explicit batch column name

    Returns: batch_dup dict
    """
    batch_dup, severe = check_batch_identity(rows, batch_col)

    # Write report
    processed_dir = run_dir / '02_processed' if isinstance(run_dir, Path) else Path(run_dir) / '02_processed'
    processed_dir.mkdir(parents=True, exist_ok=True)

    # If duplicates found, write duplicate batch CSV
    if batch_dup['duplicate_batches'] and batch_dup['id_col']:
        dup_rows = [r for r in rows if str(r.get(batch_dup['id_col'], '')).strip() in batch_dup['duplicate_batches']]
        if dup_rows:
            out_csv = processed_dir / 'duplicate_batch_report.csv'
            if dup_rows:
                with open(out_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=list(dup_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(dup_rows)
                print(f"Duplicate batch report written to {out_csv}")

    # Also write JSON report
    out_json = processed_dir / 'batch_integrity.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(batch_dup, f, ensure_ascii=False, indent=2)

    return batch_dup


def main():
    ap = argparse.ArgumentParser(description='Batch identity integrity check')
    ap.add_argument('cleaned_path', help='Path to cleaned data (CSV or JSON)')
    ap.add_argument('--run-dir', default=None, help='Run directory for output')
    ap.add_argument('--batch-col', default=None, help='Explicit batch column name')
    args = ap.parse_args()

    path = Path(args.cleaned_path)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)

    # Load data
    if path.suffix == '.csv':
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    else:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            rows = data.get('data', data.get('rows', data.get('preview', [])))
        else:
            rows = data

    run_dir = Path(args.run_dir) if args.run_dir else path.parent

    result = run_batch_checks(rows, run_dir, args.batch_col)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
