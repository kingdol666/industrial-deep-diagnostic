#!/usr/bin/env python3
"""
generate_vlm_charts.py — Generate VLM-optimized temporal overlay charts.

Follows visual_analysis_framework.md design specs:
- All parameters z-score normalized
- Negatively correlated params reversed (quality-degradation direction aligned)
- Shared x-axis (time)
- Event markers as red dashed lines
- Large fonts (>=12pt), high contrast
- English axis labels (compatible with matplotlib rendering)

Usage:
    python generate_vlm_charts.py <run_dir> \
        --target-cols col1,col2 \
        --key-params p1,p2,p3 \
        --group-col <group_col> \
        --time-col <time_col> \
        [--events '[{"day":30,"label":"event1"},...]']

Outputs:
    03_figures/fig_vlm_temporal_overlay.png  — Main temporal overlay (all params)
    03_figures/fig_vlm_per_product_overlay.png — Per-group temporal overlay (if group exists)
"""

import argparse, json, os, sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_data(run_dir):
    """Load cleaned data and ontology."""
    cleaned_csv = os.path.join(run_dir, '02_processed', 'cleaned_data.csv')
    df = pd.read_csv(cleaned_csv)
    
    ontology_path = os.path.join(run_dir, '01_ontology', 'ontology.json')
    if os.path.exists(ontology_path):
        with open(ontology_path, 'rb') as f:
            ontology = json.load(f)
    else:
        ontology = None
    
    return df, ontology


def parse_events(events_str, day_col='day'):
    """Parse events from JSON string or user_context.json."""
    if events_str:
        return json.loads(events_str)
    return []


def plot_temporal_overlay(df, targets, key_params, time_col, events, fig_dir, group_col=None, group_val=None):
    """
    Generate VLM temporal overlay chart.
    
    Design (per visual_analysis_framework.md):
    - All params z-score normalized
    - Negative correlations reversed so all lines point in quality-degradation direction
    - Shared x-axis (time)
    - Event markers: red dashed lines + annotations
    - Font >= 12pt, high contrast, English labels
    """
    fig, ax = plt.subplots(figsize=(20, 9))
    
    # Colors for each param type
    colors_map = {}
    palette = ['#1a3a5c', '#e85d04', '#2d6a4f', '#52b788', '#9b2226', 
               '#e9c46a', '#7b2cbf', '#457b9d', '#f4a261', '#2a9d8f',
               '#e76f51', '#264653', '#8338ec', '#ff006e', '#3a86ff']
    
    # Quality targets get darker/more prominent colors
    for i, col in enumerate(targets + key_params):
        colors_map[col] = palette[i % len(palette)]
    
    # Determine which params to reverse based on correlation with first quality target
    primary = targets[0] if targets else key_params[0]
    reverse_params = set()
    for col in key_params:
        if col in df.columns and primary in df.columns:
            r = df[col].corr(df[primary])
            if not pd.isna(r) and r < -0.3:
                reverse_params.add(col)
    # Also reverse secondary quality targets that are negatively correlated with primary
    for col in targets[1:]:
        if col in df.columns and primary in df.columns:
            r = df[col].corr(df[primary])
            if not pd.isna(r) and r < -0.3:
                reverse_params.add(col)
    
    # Filter data by group if specified
    plot_df = df.copy()
    suffix = ''
    if group_col and group_val:
        plot_df = df[df[group_col] == group_val].copy()
        suffix = f' — {group_col}={group_val}'
    
    # Extract time values
    if time_col and time_col in plot_df.columns:
        time_vals = pd.to_datetime(plot_df[time_col])
        day0 = time_vals.min()
        x_vals = (time_vals - day0).dt.total_seconds() / 86400  # days from start
        x_label = f'Time (days from {day0.strftime("%Y-%m-%d")})'
    else:
        x_vals = plot_df.index.values
        x_label = 'Row Index'
    
    # Plot each parameter
    for col in targets + key_params:
        if col not in plot_df.columns:
            continue
        values = (plot_df[col] - plot_df[col].mean()) / plot_df[col].std()
        label_suffix = ''
        if col in reverse_params:
            values = -values
            label_suffix = ' (rev)'
        lw = 2.5 if col in targets else 1.5
        ls = '-' if col in targets else '--'
        alpha = 0.9 if col in targets else 0.7
        
        ax.plot(x_vals, values, color=colors_map.get(col, '#666666'),
                linewidth=lw, label=f'{col}{label_suffix}', alpha=alpha, linestyle=ls)
    
    # Event markers
    for evt in events:
        day = evt.get('day', evt.get('time', 0))
        label = evt.get('label', evt.get('event', ''))
        ax.axvline(day, color='#e63946', linestyle='--', linewidth=2, alpha=0.7)
        if label:
            ax.text(day, ax.get_ylim()[1]*0.92, label, rotation=90,
                    va='top', ha='right', fontsize=11, color='#e63946', fontweight='bold')
    
    ax.set_xlabel(x_label, fontsize=14)
    ax.set_ylabel('Normalized Value (z-score, quality-degradation direction aligned)', fontsize=13)
    ax.set_title(f'VLM Temporal Alignment — All Parameters Normalized & Direction-Aligned{suffix}',
                 fontsize=15, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left', ncol=2)
    ax.grid(True, alpha=0.25)
    
    plt.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description='Generate VLM-optimized temporal overlay charts')
    parser.add_argument('run_dir', help='Run directory')
    parser.add_argument('--target-cols', help='Comma-separated quality target columns')
    parser.add_argument('--key-params', help='Comma-separated key process parameter columns')
    parser.add_argument('--group-col', default=None, help='Group/confounder column')
    parser.add_argument('--time-col', default=None, help='Time column name')
    parser.add_argument('--events', default=None, help='JSON string of events [{"day":N,"label":"..."}]')
    
    args = parser.parse_args()
    run_dir = args.run_dir
    fig_dir = os.path.join(run_dir, '03_figures')
    os.makedirs(fig_dir, exist_ok=True)
    
    targets = args.target_cols.split(',') if args.target_cols else []
    key_params = args.key_params.split(',') if args.key_params else []
    events = parse_events(args.events)
    
    df, ontology = load_data(run_dir)

    # Direction alignment (data-driven, shared with plot_temporal_overlay):
    # reverse a parameter ONLY when it correlates negatively (r < -0.3) with
    # the primary quality target — never by position in the target list.
    primary = targets[0] if targets else (key_params[0] if key_params else None)
    reverse_params = set()
    if primary and primary in df.columns:
        for col in targets + key_params:
            if col in df.columns and col != primary:
                r = df[col].corr(df[primary])
                if not pd.isna(r) and r < -0.3:
                    reverse_params.add(col)
    
    # If events not provided, try to extract from user_context
    if not events:
        ctx_path = os.path.join(run_dir, '00_input', 'user_context.json')
        if os.path.exists(ctx_path):
            with open(ctx_path, 'rb') as f:
                ctx = json.loads(f.read().decode('utf-8'))
            events = ctx.get('known_events', [])
    
    # Generate main temporal overlay
    print(f'Generating VLM temporal overlay: {len(targets)} targets, {len(key_params)} params')
    fig = plot_temporal_overlay(df, targets, key_params, args.time_col, events, fig_dir)
    fig.savefig(os.path.join(fig_dir, 'fig_vlm_temporal_overlay.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  -> fig_vlm_temporal_overlay.png')
    size = os.path.getsize(os.path.join(fig_dir, 'fig_vlm_temporal_overlay.png'))
    print(f'  Size: {size} bytes (need >51200 for VLM readability)')
    
    # Generate per-group overlays
    if args.group_col and args.group_col in df.columns:
        group_vals = df[args.group_col].unique()
        if len(group_vals) <= 6:  # Don't generate for too many groups
            fig, axes = plt.subplots(len(group_vals), 1, figsize=(20, 5*len(group_vals)), sharex=True)
            if len(group_vals) == 1:
                axes = [axes]
            
            for idx, (gv, ax_i) in enumerate(zip(group_vals, axes)):
                sub = df[df[args.group_col] == gv]
                time_vals = pd.to_datetime(sub[args.time_col]) if args.time_col and args.time_col in sub.columns else None
                if time_vals is not None:
                    day0 = time_vals.min()
                    x_vals = (time_vals - day0).dt.total_seconds() / 86400
                else:
                    x_vals = sub.index.values
                
                for col in targets + key_params:
                    if col not in sub.columns or sub[col].nunique() < 5:
                        continue
                    values = (sub[col] - sub[col].mean()) / sub[col].std()
                    label_suffix = ''
                    if col in reverse_params:  # data-driven reversal (r < -0.3 vs primary)
                        values = -values
                        label_suffix = ' (rev)'
                    lw = 2.0 if col in targets else 1.2
                    ax_i.plot(x_vals, values, color=colors[col] if 'colors' in dir() else '#666',
                              linewidth=lw, label=f'{col}{label_suffix}', alpha=0.8)
                
                for evt in events:
                    day = evt.get('day', evt.get('time', 0))
                    ax_i.axvline(day, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
                
                ax_i.set_ylabel('z-score', fontsize=13)
                ax_i.set_title(f'{args.group_col} = {gv} ({len(sub)} rows)', fontsize=13, fontweight='bold')
                ax_i.legend(fontsize=9, loc='upper left', ncol=2)
                ax_i.grid(True, alpha=0.25)
            
            axes[-1].set_xlabel('Time (days)', fontsize=14)
            plt.tight_layout()
            plt.savefig(os.path.join(fig_dir, 'fig_vlm_per_product_overlay.png'), dpi=150, bbox_inches='tight')
            plt.close()
            print('  -> fig_vlm_per_product_overlay.png')
    
    print('VLM chart generation complete.')


# Color palette for charts (used in per-product overlay)
colors = ['#1a3a5c', '#e85d04', '#2d6a4f', '#52b788', '#9b2226',
          '#e9c46a', '#7b2cbf', '#457b9d', '#f4a261', '#2a9d8f']


if __name__ == '__main__':
    main()
