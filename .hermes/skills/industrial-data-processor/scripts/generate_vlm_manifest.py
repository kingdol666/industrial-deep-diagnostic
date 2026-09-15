#!/usr/bin/env python3
"""
generate_vlm_manifest.py — Build VLM image filter manifest.

Not all generated images should be sent to VLM. Only spatio-temporally aligned
images carry diagnostic value for VLM. This script classifies each image and
produces vlm_input_manifest.json that tells VLM which images to read.

Classification rules (per visual_analysis_framework.md §VLM Image Dispatch Rules):
- MANDATORY: temporal overlays with shared time axis + z-score normalization
- SUPPLEMENTARY: scatter plots colored by confounder (Simpson check)
- NOT_FOR_VLM: single-param trends, bar charts, non-aligned plots

Usage:
    python generate_vlm_manifest.py <run_dir>
    
Outputs:
    03_figures/vlm_input_manifest.json  — Image selection manifest for VLM
    Updates plot_manifest.json with vlm_priority field
"""

import argparse, json, os, sys, re
from pathlib import Path


def classify_image(filename, title, plot_type, params):
    """
    Classify an image for VLM priority based on its type and content.
    
    Returns: 'MANDATORY' | 'SUPPLEMENTARY' | 'NOT_FOR_VLM'
    """
    fname_lower = filename.lower()
    title_lower = title.lower() if title else ''
    plot_type_lower = plot_type.lower() if plot_type else ''
    
    # MANDATORY: temporal overlay charts (explicitly named for VLM)
    if fname_lower.startswith('fig_vlm_temporal') or 'vlm_temporal_overlay' in fname_lower:
        return 'MANDATORY'
    if fname_lower.startswith('fig_vlm_per_product') or 'per_product_overlay' in fname_lower:
        return 'MANDATORY'
    
    # MANDATORY: any chart explicitly designed for VLM
    if 'vlm' in fname_lower or 'vlm' in plot_type_lower:
        return 'MANDATORY'
    
    # SUPPLEMENTARY: scatter plots with confounder coloring (for Simpson check)
    is_scatter = 'scatter' in plot_type_lower or 'scatter' in fname_lower
    has_group = len(params) > 2  # scatter with color grouping has at least x,y+group
    if is_scatter and has_group:
        return 'SUPPLEMENTARY'
    
    # SUPPLEMENTARY: event response plots
    if 'event_response' in fname_lower or 'event' in plot_type_lower:
        return 'SUPPLEMENTARY'
    
    # SUPPLEMENTARY: Simpson Paradox specific plots
    if 'simpson' in fname_lower or 'simpson' in title_lower:
        return 'SUPPLEMENTARY'
    
    # NOT_FOR_VLM: bar charts (VLM can't read numerical values from bar heights)
    if 'bar' in plot_type_lower or 'bar' in fname_lower:
        return 'NOT_FOR_VLM'
    if 'correlation' in fname_lower and 'bar' in title_lower:
        return 'NOT_FOR_VLM'
    
    # NOT_FOR_VLM: single-parameter time series (no cross-param alignment)
    if 'trend' in fname_lower and 'time_series' in plot_type_lower:
        return 'NOT_FOR_VLM'
    
    # NOT_FOR_VLM: histogram, distribution, heatmap (not useful for root cause VLM)
    if any(t in fname_lower for t in ['histogram', 'distribution', 'heatmap', 'causal_evidence']):
        return 'NOT_FOR_VLM'
    
    # Default: single-param or simple dual-axis charts without normalization
    if len(params) <= 2:
        return 'NOT_FOR_VLM'
    
    return 'SUPPLEMENTARY'


def main():
    parser = argparse.ArgumentParser(description='Build VLM image filter manifest')
    parser.add_argument('run_dir', help='Run directory')
    parser.add_argument('--plot-manifest', default=None, help='Path to plot_manifest.json (default: run_dir/03_figures/plot_manifest.json)')
    
    args = parser.parse_args()
    run_dir = args.run_dir
    fig_dir = os.path.join(run_dir, '03_figures')
    
    # Default plot manifest path
    pm_path = args.plot_manifest or os.path.join(fig_dir, 'plot_manifest.json')
    
    if not os.path.exists(pm_path):
        print(f'ERROR: plot_manifest.json not found at {pm_path}')
        sys.exit(1)
    
    with open(pm_path, 'rb') as f:
        pm = json.load(f)
    
    # Classify each plot
    vlm_images = []
    for plot in pm.get('plots', []):
        filename = plot.get('filename', plot.get('file', ''))
        title = plot.get('title', '')
        plot_type = plot.get('plot_type', plot.get('type', ''))
        params = plot.get('params', [])
        
        priority = classify_image(filename, title, plot_type, params)
        plot['vlm_priority'] = priority
        
        if priority != 'NOT_FOR_VLM':
            entry = {
                'filename': filename,
                'title': title,
                'plot_type': plot_type,
                'vlm_priority': priority,
            }
            
            if priority == 'MANDATORY':
                is_main = 'per_product' not in filename
                entry['vlm_read_order'] = 1 if is_main else 2
                entry['diagnostic_questions_for_vlm'] = [
                    'Which parameters move synchronously?',
                    'What is the temporal precedence? (which changes first)',
                    'At event markers, is there visible response?',
                    'Is degradation linear, stepwise, or accelerating?'
                ]
            else:  # SUPPLEMENTARY
                entry['vlm_read_order'] = 3
                entry['diagnostic_questions_for_vlm'] = [
                    'Do different groups form separate clusters?',
                    'Are within-group slopes consistent? (Simpson check)'
                ]
            
            vlm_images.append(entry)
    
    # Build manifest
    vlm_manifest = {
        'generated_at': '',  # set below
        'total_images_available': len(pm['plots']),
        'total_images_for_vlm': len(vlm_images),
        'total_images_excluded': len(pm['plots']) - len(vlm_images),
        'filtering_principle': (
            'Only images with true spatio-temporal alignment are sent to VLM. '
            'Single-parameter trends, bar charts, and non-aligned plots are excluded '
            'because VLM cannot extract cross-parameter temporal precedence or synchrony from them.'
        ),
        'selection_criteria': [
            'MANDATORY: temporal overlays with shared time axis + z-score normalization',
            'MANDATORY: per-group temporal overlays (when product grouping exists)',
            'SUPPLEMENTARY: scatter plots colored by confounder (Simpson Paradox check)',
            'EXCLUDED: single-parameter trends (no cross-parameter alignment)',
            'EXCLUDED: bar charts (VLM cannot read numerical values from bars)',
            'EXCLUDED: non-aligned basic charts (no diagnostic insight beyond numbers)'
        ],
        'vlm_images': vlm_images
    }
    
    # Add timestamp
    from datetime import datetime, timezone
    vlm_manifest['generated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Write vlm_input_manifest.json
    manifest_path = os.path.join(fig_dir, 'vlm_input_manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(vlm_manifest, f, indent=2, ensure_ascii=False)
    
    # Update plot_manifest.json with vlm_priority
    with open(pm_path, 'w', encoding='utf-8') as f:
        json.dump(pm, f, indent=2, ensure_ascii=False)
    
    print(f'VLM Input Manifest: {vlm_manifest["total_images_available"]} total, '
          f'{vlm_manifest["total_images_for_vlm"]} for VLM, '
          f'{vlm_manifest["total_images_excluded"]} excluded')
    print(f'  -> {manifest_path}')
    
    for img in vlm_images:
        p = img['vlm_priority']
        r = img.get('vlm_read_order', '?')
        fname = img['filename']
        print(f'  [{p}] order={r}: {fname}')


if __name__ == '__main__':
    from datetime import datetime, timezone
    main()
