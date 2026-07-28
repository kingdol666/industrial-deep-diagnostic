#!/usr/bin/env python3
"""Unified stats pipeline — single entry point for all statistical analysis.
Usage: python stats/run.py --run-dir <RUN_DIR> [--mode full|correlation|spurious|batch]
Input:  RUN_DIR/02_processed/cleaned_data.json
Output: RUN_DIR/02_processed/validate_report.json
"""
import argparse
import json
import sys
from pathlib import Path


# Ensure the package can be found when called directly
_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))


def main():
    parser = argparse.ArgumentParser(description="Unified stats pipeline")
    parser.add_argument('--run-dir', required=True, help="Run directory")
    parser.add_argument('--mode', default='full',
                        choices=['full', 'correlation', 'spurious', 'batch'],
                        help="Analysis mode (default: full)")
    parser.add_argument('--target-cols', default=None,
                        help="Comma-separated target column names")
    parser.add_argument('--predictor-cols', default=None,
                        help="Comma-separated predictor column names")
    parser.add_argument('--exclude-cols', default=None,
                        help="Comma-separated columns to exclude")
    parser.add_argument('--group-col', default=None,
                        help="Group/stratification column")
    parser.add_argument('--time-col', default=None,
                        help="Time column")
    parser.add_argument('--max-lag', type=int, default=20,
                        help="Maximum CCF lag (default: 20)")
    parser.add_argument('--alpha', type=float, default=0.05,
                        help="Significance level (default: 0.05)")
    parser.add_argument('--data-view-mode', default='unknown',
                        choices=['process_plus_inspection', 'process_only',
                                 'inspection_only', 'unknown'],
                        help="Data view mode")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    data_path = run_dir / '02_processed' / 'cleaned_data.json'

    if not data_path.exists():
        print(f"ERROR: {data_path} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(data_path.read_text(encoding='utf-8'))
    if isinstance(data, dict):
        data = data.get('data', data.get('rows', data.get('preview', [])))
    if not isinstance(data, list) or len(data) == 0:
        print("ERROR: Expected JSON array of objects", file=sys.stderr)
        sys.exit(1)

    rows = data

    # Parse column lists
    target_cols = [c.strip() for c in args.target_cols.split(',')] if args.target_cols else []
    predictor_cols = [c.strip() for c in args.predictor_cols.split(',')] if args.predictor_cols else []
    exclude_cols = set(c.strip() for c in args.exclude_cols.split(',')) if args.exclude_cols else set()

    results = {}

    # Use absolute imports (works when called from any directory)
    sys.path.insert(0, str(_script_dir))
    import core_stats, anti_spurious, batch_integrity as bi

    if args.mode in ('full', 'correlation'):
        results['correlation'] = core_stats.run_correlation_analysis(
            rows, run_dir,
            target_cols=target_cols,
            predictor_cols=predictor_cols,
            exclude_cols=exclude_cols,
            time_col=args.time_col,
            group_col=args.group_col,
            max_lag=args.max_lag,
            alpha=args.alpha,
            data_view_mode=args.data_view_mode,
        )

    if args.mode in ('full', 'spurious'):
        results['anti_spurious'] = anti_spurious.run_anti_spurious_checks(
            rows, run_dir,
            correlation_result=results.get('correlation'),
            target_cols=target_cols,
            group_col=args.group_col,
            time_col=args.time_col,
        )

    if args.mode in ('full', 'batch'):
        results['batch'] = bi.run_batch_checks(rows, run_dir)

    output = run_dir / '02_processed' / 'validate_report.json'
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Stats pipeline complete \u2192 {output}")


if __name__ == '__main__':
    main()
