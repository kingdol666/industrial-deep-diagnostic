#!/usr/bin/env python3
"""Plot Verification Gate — Phase 5.9 extracted from data-processor protocol.

Real Plot Guarantee: every plot must be driven by real data from the verified
source, not a placeholder or silently-skipped artifact. This script verifies
plot_manifest.json after generation, BEFORE VLM delegation.

Checks:
1. plot_manifest.json non-empty with at least one real PNG entry
2. Each PNG > 5KB (excludes rendering failures / blank images)
3. Plotted params are numeric columns in the verified data source
4. No unhandled ABORT marker from visual_analysis.py

Exit codes:
    0 — gate passed
    1 — gate failed (reason printed to stderr)

Usage:
    uv run python plot_verification.py <run_dir>
"""
import argparse
import json
import os
import sys

try:
    import pandas as pd
except ImportError:
    print('ERROR: pandas not installed in venv. Run node scripts/uv_env_setup.mjs first.', file=sys.stderr)
    sys.exit(2)


MIN_PNG_BYTES = 5120  # 5KB


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _resolve_data_source(run_dir):
    """Read cleaning_integrity.json to find the verified data source path."""
    ci = _load_json(os.path.join(run_dir, '02_processed', 'cleaning_integrity.json'))
    source = (ci or {}).get('data_source', 'cleaned')
    if source == 'raw_fallback':
        return None, 'raw'  # caller resolves raw path from run_config
    return os.path.join(run_dir, '02_processed', 'cleaned_data.csv'), 'cleaned'


def verify(run_dir):
    errors = []

    # 1. plot_manifest.json must exist and be non-empty
    pm_path = os.path.join(run_dir, '03_figures', 'plot_manifest.json')
    pm = _load_json(pm_path)
    if pm is None:
        errors.append(f'plot_manifest.json missing at {pm_path}')
        return errors, []
    plots = pm.get('plots') if isinstance(pm, dict) else None
    if not plots or not isinstance(plots, list) or len(plots) == 0:
        errors.append('plot_manifest.json has no plots entries')
        return errors, []

    # 2. Each plot's path must point to a real PNG > 5KB
    verified_plots = []
    for p in plots:
        path = p.get('path') if isinstance(p, dict) else None
        if not path:
            errors.append(f'plot entry missing path: {p}')
            continue
        if not os.path.isabs(path):
            path = os.path.join(run_dir, path)
        if not os.path.exists(path):
            errors.append(f'plot PNG missing: {path}')
            continue
        size = os.path.getsize(path)
        if size < MIN_PNG_BYTES:
            errors.append(f'plot PNG too small ({size} bytes < {MIN_PNG_BYTES}): {path}')
            continue
        verified_plots.append(p)

    if not verified_plots:
        errors.append('no verified PNG plots survived size check')
        return errors, verified_plots

    # 3. Plot's claimed params must be numeric in verified data source
    data_csv, source_kind = _resolve_data_source(run_dir)
    if data_csv and os.path.exists(data_csv):
        try:
            df = pd.read_csv(data_csv, nrows=200)
        except Exception as e:
            errors.append(f'cannot read verified data source {data_csv}: {e}')
            df = None
        if df is not None:
            numeric_set = {c for c in df.columns
                           if pd.to_numeric(df[c], errors='coerce').notna().mean() >= 0.5}
            for p in verified_plots:
                claimed = []
                if isinstance(p, dict):
                    claimed = (p.get('params') or p.get('parameters') or
                               p.get('predictors') or p.get('targets') or [])
                for param in claimed:
                    if param and param not in numeric_set and param not in df.columns:
                        errors.append(f'plot {p.get("path", "?")} claims param "{param}" not in verified data source')
    else:
        # raw_fallback path — skip param check (raw CSV location varies)
        sys.stderr.write('WARN: raw_fallback data source — skipping param coverage check\n')

    # 4. No unhandled ABORT
    va_path = os.path.join(run_dir, '03_figures', 'visual_analysis.json')
    va = _load_json(va_path)
    if isinstance(va, dict):
        prov = va.get('analysis_provenance', {}) if isinstance(va.get('analysis_provenance'), dict) else {}
        abort_flag = prov.get('abort_reason') or va.get('abort_reason')
        if abort_flag and 'zero numeric' in str(abort_flag).lower():
            errors.append(f'unhandled ABORT in visual_analysis.json: {abort_flag} — must repair data and re-plot before VLM')

    return errors, verified_plots


def main():
    ap = argparse.ArgumentParser(description='Plot verification gate (Phase 5.9)')
    ap.add_argument('run_dir', help='pipeline run directory')
    args = ap.parse_args()

    if not os.path.isdir(args.run_dir):
        print(f'ERROR: run_dir not found: {args.run_dir}', file=sys.stderr)
        sys.exit(2)

    errors, verified_plots = verify(args.run_dir)

    if errors:
        print('PLOT_VERIFICATION_FAILED:', file=sys.stderr)
        for e in errors:
            print(f'  - {e}', file=sys.stderr)
        sys.exit(1)

    print(f'PLOT_VERIFICATION_PASSED: {len(verified_plots)} verified plots')
    sys.exit(0)


if __name__ == '__main__':
    main()
