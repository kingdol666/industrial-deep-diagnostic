#!/usr/bin/env python3
"""
ADAPTIVE VISUALIZATION TOOLKIT — Dimension-Driven, Time-Aligned
================================================================

NOT a fixed script. A LIBRARY of composable visualization primitives.

Agent workflow:
  1. Set INPUT_FILE, OUTPUT_DIR, TIME_COL (top of main)
  2. Call detect_data_pattern() → classify data dimensions
  3. Based on pattern, SELECT primitives from sections below
  4. Compose main() using selected primitives
  5. Call write_plot_manifest() → tells downstream agents HOW each plot was made

TIME ALIGNMENT:
  align_timeindex() resamples all signals to a common regular grid.
  Called automatically for irregular data, or manually for multi-rate signals.

DIMENSION PATTERNS → PRIMITIVES:
  1D Scalar  → multi_panel, overlay, anomaly_zoom, coupling_scatter, heatmap
  Multi-Axis → orbit, axis_ratio + all 1D primitives
  2D Profile → profile_evolution, position_time_heatmap, deviation_map
  Batch      → box_by_group, event_timeline
  Spectral   → spectrogram, dominant_frequency
  Mixed      → combine primitives from multiple patterns

DEPENDENCIES: matplotlib, pandas, numpy (seaborn optional for heatmaps)
"""

import json, sys, os, warnings, importlib
from pathlib import Path
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.gridspec as gridspec
    import numpy as np
    import pandas as pd
except ImportError:
    print("ERROR: pip install matplotlib numpy pandas", file=sys.stderr)
    sys.exit(1)

warnings.filterwarnings('ignore')

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


# ═══════════════════════════════════════════════════════════════
#  DATA UTILITIES
# ═══════════════════════════════════════════════════════════════

def load_data(csv_path, time_col=None):
    """Load CSV/Parquet/JSON, parse time column if present."""
    suffix = Path(csv_path).suffix.lower()
    if suffix == '.parquet':
        df = pd.read_parquet(csv_path)
    elif suffix == '.json':
        df = pd.read_json(csv_path)
    else:
        df = pd.read_csv(csv_path)
    if time_col and time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col])
    return df


def align_timeindex(df, time_col, target_freq=None, method='linear'):
    """
    Resample all numeric columns to a common regular time grid.

    Parameters
    ----------
    df : DataFrame with time_col as datetime
    time_col : str
    target_freq : str or None, e.g. '1s', '5min'. Auto-detected from median interval.
    method : 'linear' | 'nearest' | 'ffill'

    Returns
    -------
    DataFrame with regular time index, all numeric columns aligned.
    """
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col).sort_index()

    if target_freq is None:
        diffs = pd.Series(df.index).diff().dropna()
        if len(diffs) > 0:
            target_freq = str(diffs.median().total_seconds()) + 's'
        else:
            return df.reset_index()

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    cat_cols = [c for c in df.columns if c not in numeric_cols]

    regular_index = pd.date_range(df.index.min(), df.index.max(), freq=target_freq)

    df_num = df[numeric_cols].reindex(df.index.union(regular_index))
    df_num = df_num.interpolate(method=method)
    df_num = df_num.reindex(regular_index)

    if cat_cols:
        df_cat = df[cat_cols].reindex(regular_index, method='ffill')
        result = pd.concat([df_num, df_cat], axis=1)
    else:
        result = df_num

    return result.reset_index().rename(columns={'index': time_col})


def detect_data_pattern(df, time_col=None):
    """
    Classify DataFrame structure → dimension pattern + signal categories.

    Returns
    -------
    dict with:
        type: '1d_scalar' | 'multi_axis' | '2d_profile' | 'batch_event' | 'spectral' | 'mixed'
        dimensions: 1 or 2
        numeric_columns, categorical_columns
        axis_groups, spatial_columns, frequency_columns, batch_columns
        sampling_info, time_range, total_rows
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in numeric_cols and c != time_col]

    axis_groups = _detect_axis_groups(numeric_cols)
    multi_axis_groups = {k: v for k, v in axis_groups.items() if len(v) >= 2}

    spatial_kw = ['position', 'pos', 'zone', 'width', 'location', 'coord', 'x_', 'y_',
                  'distance', 'depth', 'height', 'layer', 'index_pos']
    spatial_cols = [c for c in df.columns
                    if any(kw in c.lower() for kw in spatial_kw)]

    freq_kw = ['freq', 'fft', 'spectral', 'harmonic', 'hz', 'rpm', 'cpsd', 'order']
    freq_cols = [c for c in df.columns
                 if any(kw in c.lower() for kw in freq_kw)]

    batch_kw = ['batch', 'lot', 'run', 'stage', 'phase', 'event', 'group', 'shift', 'recipe']
    batch_cols = [c for c in cat_cols
                  if any(kw in c.lower() for kw in batch_kw)]

    # Determine primary pattern
    indicators = {
        'spectral': bool(freq_cols),
        '2d_profile': bool(spatial_cols),
        'batch_event': bool(batch_cols),
        'multi_axis': bool(multi_axis_groups),
    }
    active = [k for k, v in indicators.items() if v]

    if len(active) > 1:
        pattern_type = 'mixed'
    elif active:
        pattern_type = active[0]
    else:
        pattern_type = '1d_scalar'

    dimensions = 2 if (spatial_cols or freq_cols) else 1

    sampling_info = {}
    time_range = None
    if time_col and time_col in df.columns:
        times = pd.to_datetime(df[time_col])
        diffs = times.diff().dropna()
        if len(diffs) > 0:
            sampling_info = {
                'median_interval_sec': round(diffs.dt.total_seconds().median(), 4),
                'min_interval_sec': round(diffs.dt.total_seconds().min(), 4),
                'max_interval_sec': round(diffs.dt.total_seconds().max(), 4),
                'is_regular': diffs.std().total_seconds() / max(diffs.mean().total_seconds(), 1e-9) < 0.1
            }
        time_range = {
            'start': str(times.min()),
            'end': str(times.max()),
        }

    return {
        'type': pattern_type,
        'dimensions': dimensions,
        'numeric_columns': numeric_cols,
        'categorical_columns': cat_cols,
        'axis_groups': multi_axis_groups,
        'spatial_columns': spatial_cols,
        'frequency_columns': freq_cols,
        'batch_columns': batch_cols,
        'sampling_info': sampling_info,
        'time_range': time_range,
        'total_rows': len(df),
    }


def _detect_axis_groups(columns):
    """Group columns sharing a common stem (e.g. vib_x, vib_y, vib_z)."""
    suffixes = ['_x', '_y', '_z', '_a', '_b', '_c', '_1', '_2', '_3',
                '_axial', '_radial', '_tangential', '_horiz', '_vert']
    stems = {}
    for col in columns:
        base = col
        for s in suffixes:
            if col.lower().endswith(s):
                base = col[:-len(s)]
                break
        stems.setdefault(base, []).append(col)
    return stems


def normalize_01(series):
    """Min-max normalize to [0, 1]."""
    s = np.array(series, dtype=float)
    rng = np.nanmax(s) - np.nanmin(s)
    if rng < 1e-12:
        return np.full_like(s, 0.5)
    return (s - np.nanmin(s)) / rng


# ═══════════════════════════════════════════════════════════════
#  1D SCALAR TIME-SERIES PRIMITIVES
# ═══════════════════════════════════════════════════════════════

def plot_multi_panel_timeseries(fig, axes, time, signals_dict, anomalies=None):
    """
    Multi-panel time-series with shared X axis.
    Each signal gets its own panel for clarity.

    Parameters
    ----------
    time : array-like (datetime)
    signals_dict : {label: array-like}
    anomalies : [{"start": ..., "end": ...}] or None

    Returns
    -------
    dict — generation metadata for manifest
    """
    if not isinstance(axes, np.ndarray):
        axes = np.array([axes])

    for idx, (label, values) in enumerate(signals_dict.items()):
        if idx >= len(axes):
            break
        ax = axes[idx]
        ax.plot(time, values, linewidth=0.8, label=label)
        ax.set_ylabel(label, fontsize=9)
        ax.legend(loc='upper right', fontsize=7)
        ax.grid(True, alpha=0.3)
        _highlight_anomalies(ax, anomalies)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    fig.autofmt_xdate()

    return {
        "function": "plot_multi_panel_timeseries",
        "time_alignment": "shared_x_axis",
        "panel_count": min(len(signals_dict), len(axes)),
        "signals": list(signals_dict.keys()),
        "anomaly_highlighting": bool(anomalies),
    }


def plot_normalized_overlay(ax, time, signals_dict, anomalies=None):
    """
    All signals min-max normalized to [0,1] on one axis.
    Reveals temporal coupling between signals.

    Returns dict — generation metadata
    """
    for label, values in signals_dict.items():
        normed = normalize_01(values)
        ax.plot(time, normed, linewidth=0.8, label=label, alpha=0.8)

    ax.set_ylabel('Normalized [0, 1]', fontsize=9)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=7)
    ax.grid(True, alpha=0.3)
    _highlight_anomalies(ax, anomalies)

    return {
        "function": "plot_normalized_overlay",
        "normalization": "min-max [0,1]",
        "signals": list(signals_dict.keys()),
        "anomaly_highlighting": bool(anomalies),
    }


def plot_anomaly_zoom(ax, time, values, onset_time, window_minutes=60, label=''):
    """
    Zoomed view around anomaly onset.

    Returns dict — generation metadata
    """
    onset = pd.to_datetime(onset_time)
    window = pd.Timedelta(minutes=window_minutes)
    t = pd.to_datetime(time)
    mask = (t >= onset - window) & (t <= onset + window)

    ax.plot(t[mask], np.array(values)[mask], linewidth=1.0)
    ax.axvline(onset, color='red', linestyle='--', alpha=0.7, label='Anomaly onset')
    ax.set_ylabel(label, fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

    return {
        "function": "plot_anomaly_zoom",
        "onset_time": str(onset),
        "window_minutes": window_minutes,
        "signal": label,
        "points_in_window": int(mask.sum()),
    }


def plot_coupling_scatter(ax, x, y, time=None, x_label='', y_label=''):
    """
    Scatter plot of two signals, optionally colored by time progression.

    Returns dict — generation metadata
    """
    if time is not None:
        sc = ax.scatter(x, y, c=range(len(x)), cmap='viridis', s=3, alpha=0.6)
        plt.colorbar(sc, ax=ax, label='Time progression')
    else:
        ax.scatter(x, y, s=3, alpha=0.6)

    ax.set_xlabel(x_label, fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.grid(True, alpha=0.3)

    return {
        "function": "plot_coupling_scatter",
        "x_signal": x_label,
        "y_signal": y_label,
        "time_colored": time is not None,
        "point_count": len(x),
    }


def plot_correlation_heatmap(ax, df, columns):
    """
    Pearson correlation heatmap.

    Returns dict — generation metadata
    """
    numeric_df = df[columns].select_dtypes(include=[np.number])
    if len(numeric_df.columns) < 2:
        return {"function": "plot_correlation_heatmap", "skipped": True, "reason": "< 2 numeric columns"}

    corr = numeric_df.corr()

    if HAS_SEABORN:
        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r',
                    center=0, vmin=-1, vmax=1, ax=ax, square=True,
                    linewidths=0.5, cbar_kws={"shrink": 0.8})
    else:
        im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr)))
        ax.set_yticks(range(len(corr)))
        ax.set_xticklabels(corr.columns, rotation=45, ha='right', fontsize=7)
        ax.set_yticklabels(corr.index, fontsize=7)
        plt.colorbar(im, ax=ax, shrink=0.8)
        for i in range(len(corr)):
            for j in range(len(corr)):
                ax.text(j, i, f'{corr.values[i, j]:.2f}', ha='center', va='center', fontsize=6)

    return {
        "function": "plot_correlation_heatmap",
        "method": "pearson",
        "columns": list(numeric_df.columns),
        "library": "seaborn" if HAS_SEABORN else "matplotlib",
    }


# ═══════════════════════════════════════════════════════════════
#  2D PROFILE / SPATIAL PRIMITIVES
# ═══════════════════════════════════════════════════════════════

def plot_profile_evolution(ax, positions, values_matrix, n_profiles=20, title='Profile Evolution'):
    """
    Each profile as a line, colored by time/index.

    Parameters
    ----------
    positions : 1D array (n_positions)
    values_matrix : 2D array (n_timepoints × n_positions)

    Returns dict — generation metadata
    """
    values_matrix = np.array(values_matrix)
    step = max(1, len(values_matrix) // n_profiles)
    indices = list(range(0, len(values_matrix), step))

    cmap = plt.cm.viridis
    for i, idx in enumerate(indices):
        color = cmap(i / max(len(indices) - 1, 1))
        ax.plot(positions, values_matrix[idx], color=color, alpha=0.6, linewidth=0.8)

    ax.set_xlabel('Position', fontsize=9)
    ax.set_ylabel('Value', fontsize=9)
    ax.set_title(title, fontsize=10)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, len(values_matrix)))
    plt.colorbar(sm, ax=ax, label='Time progression')

    return {
        "function": "plot_profile_evolution",
        "n_positions": len(positions),
        "n_profiles_drawn": len(indices),
        "total_profiles": len(values_matrix),
    }


def plot_position_time_heatmap(ax, positions, times, values, xlabel='Position', ylabel='Time'):
    """
    Position × Time heatmap.

    Parameters
    ----------
    positions : 1D array (n_positions)
    times : list of time labels
    values : 2D array (n_times × n_positions)

    Returns dict — generation metadata
    """
    im = ax.imshow(values, aspect='auto', cmap='RdBu_r', origin='lower')
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)

    n_pos = min(10, len(positions))
    pos_step = max(1, len(positions) // n_pos)
    ax.set_xticks(range(0, len(positions), pos_step))
    ax.set_xticklabels([f'{positions[i]:.1f}' for i in range(0, len(positions), pos_step)], fontsize=7)

    n_time = min(8, len(times))
    time_step = max(1, len(times) // n_time)
    ax.set_yticks(range(0, len(times), time_step))
    ax.set_yticklabels([str(times[i])[:16] for i in range(0, len(times), time_step)], fontsize=7)

    plt.colorbar(im, ax=ax, shrink=0.8)

    return {
        "function": "plot_position_time_heatmap",
        "n_positions": len(positions),
        "n_timepoints": len(times),
    }


def plot_deviation_from_target(ax, positions, times, values, target=None, xlabel='Position'):
    """
    Deviation from target profile over time.

    Parameters
    ----------
    target : 1D array or None (mean profile if None)
    values : 2D array (n_times × n_positions)

    Returns dict — generation metadata
    """
    values = np.array(values)
    if target is None:
        target = values.mean(axis=0)
    target = np.array(target)

    deviation = values - target
    vmax = np.abs(deviation).max()
    im = ax.imshow(deviation, aspect='auto', cmap='RdBu_r', origin='lower',
                   vmin=-vmax, vmax=vmax)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel('Time index', fontsize=9)
    ax.set_title('Deviation from Target', fontsize=10)
    plt.colorbar(im, ax=ax, label='Deviation')

    return {
        "function": "plot_deviation_from_target",
        "target_source": "computed_mean" if target is None else "provided",
        "n_positions": len(positions),
        "n_timepoints": len(times),
        "max_deviation": float(vmax),
    }


# ═══════════════════════════════════════════════════════════════
#  MULTI-AXIS PRIMITIVES
# ═══════════════════════════════════════════════════════════════

def plot_orbit(ax, x, y, time=None, x_label='X', y_label='Y', title='Orbit Plot'):
    """
    2D orbit/trajectory plot.

    Returns dict — generation metadata
    """
    if time is not None:
        sc = ax.scatter(x, y, c=range(len(x)), cmap='viridis', s=1, alpha=0.5)
        plt.colorbar(sc, ax=ax, label='Time progression')
    else:
        ax.plot(x, y, linewidth=0.5, alpha=0.7)

    ax.set_xlabel(x_label, fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    return {
        "function": "plot_orbit",
        "x_signal": x_label,
        "y_signal": y_label,
        "time_colored": time is not None,
    }


def plot_axis_ratio(ax, time, col_a, col_b, label_a='A', label_b='B'):
    """
    Ratio between two axes over time.
    Constant ratio → single source; changing ratio → multiple sources.

    Returns dict — generation metadata
    """
    ratio = np.array(col_a) / (np.array(col_b) + 1e-12)
    ax.plot(time, ratio, linewidth=0.8)
    ax.set_ylabel(f'{label_a} / {label_b}', fontsize=9)
    ax.set_title('Axis Ratio Over Time', fontsize=10)
    ax.grid(True, alpha=0.3)

    return {
        "function": "plot_axis_ratio",
        "numerator": label_a,
        "denominator": label_b,
    }


# ═══════════════════════════════════════════════════════════════
#  BATCH / EVENT PRIMITIVES
# ═══════════════════════════════════════════════════════════════

def plot_box_by_group(ax, df, signal_col, group_col):
    """
    Box plots per batch/group.

    Returns dict — generation metadata
    """
    groups = df.groupby(group_col)[signal_col]
    labels = sorted(groups.groups.keys())
    data = [groups.get_group(g).values for g in labels]

    bp = ax.boxplot(data, labels=labels, patch_artist=True)
    colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    ax.set_xlabel(group_col, fontsize=9)
    ax.set_ylabel(signal_col, fontsize=9)
    ax.set_title(f'{signal_col} by {group_col}', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    return {
        "function": "plot_box_by_group",
        "signal": signal_col,
        "group_column": group_col,
        "n_groups": len(labels),
    }


def plot_event_timeline(ax, df, time_col, event_col, signal_col=None):
    """
    Events on a timeline with optional signal overlay.

    Returns dict — generation metadata
    """
    events = df[df[event_col].notna()]

    if signal_col and signal_col in df.columns:
        ax.plot(df[time_col], df[signal_col], linewidth=0.8, alpha=0.5, label=signal_col)
        if len(events) > 0:
            ax.scatter(pd.to_datetime(events[time_col]), events[signal_col],
                       color='red', zorder=5, s=20, label='Events')
        ax.legend(fontsize=7)
    else:
        if len(events) > 0:
            for _, row in events.iterrows():
                ax.axvline(pd.to_datetime(row[time_col]), color='red', alpha=0.3)
        ax.set_yticks([])

    ax.set_xlabel('Time', fontsize=9)
    ax.set_title(f'Event Timeline ({event_col})', fontsize=10)
    ax.grid(True, alpha=0.3)

    return {
        "function": "plot_event_timeline",
        "event_column": event_col,
        "signal_overlay": signal_col,
        "n_events": len(events),
    }


# ═══════════════════════════════════════════════════════════════
#  SPECTRAL PRIMITIVES (numpy-only, no scipy)
# ═══════════════════════════════════════════════════════════════

def plot_spectrogram(ax, signal, fs=1.0, times=None, title='Spectrogram'):
    """
    Spectrogram via numpy STFT.

    Parameters
    ----------
    signal : 1D array
    fs : float, sampling frequency
    times : array, time values (for display)

    Returns dict — generation metadata
    """
    signal = np.array(signal, dtype=float)
    nperseg = min(256, len(signal) // 4)
    if nperseg < 4:
        return {"function": "plot_spectrogram", "skipped": True, "reason": "signal too short"}

    noverlap = nperseg // 2
    window = np.hanning(nperseg)
    step = nperseg - noverlap
    n_seg = (len(signal) - nperseg) // step + 1

    stft = np.zeros((nperseg // 2 + 1, n_seg))
    for i in range(n_seg):
        seg = signal[i * step : i * step + nperseg] * window
        stft[:, i] = np.abs(np.fft.rfft(seg))[:nperseg // 2 + 1]

    freqs = np.fft.rfftfreq(nperseg, 1.0 / fs)[:nperseg // 2 + 1]
    time_axis = np.arange(n_seg) * step / fs

    im = ax.pcolormesh(time_axis, freqs, 10 * np.log10(stft + 1e-12),
                       shading='auto', cmap='viridis')
    ax.set_ylabel('Frequency (Hz)', fontsize=9)
    ax.set_xlabel('Time (s)', fontsize=9)
    ax.set_title(title, fontsize=10)
    plt.colorbar(im, ax=ax, label='Power (dB)')

    return {
        "function": "plot_spectrogram",
        "nperseg": nperseg,
        "sampling_frequency": fs,
        "n_segments": n_seg,
    }


def plot_dominant_frequency(ax, signal, fs=1.0, title='Dominant Frequency'):
    """
    Peak frequency over time (numpy-only).

    Returns dict — generation metadata
    """
    signal = np.array(signal, dtype=float)
    nperseg = min(256, len(signal) // 4)
    if nperseg < 4:
        return {"function": "plot_dominant_frequency", "skipped": True, "reason": "signal too short"}

    step = nperseg // 2
    n_seg = (len(signal) - nperseg) // step + 1
    dom_freqs, time_pts = [], []

    for i in range(n_seg):
        seg = signal[i * step : i * step + nperseg] * np.hanning(nperseg)
        spectrum = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(nperseg, 1.0 / fs)
        dom_freqs.append(freqs[np.argmax(spectrum)])
        time_pts.append(i * step / fs)

    ax.plot(time_pts, dom_freqs, linewidth=0.8)
    ax.set_xlabel('Time (s)', fontsize=9)
    ax.set_ylabel('Dominant Freq (Hz)', fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3)

    return {
        "function": "plot_dominant_frequency",
        "sampling_frequency": fs,
        "n_segments": n_seg,
    }


# ═══════════════════════════════════════════════════════════════
#  MANIFEST GENERATION
# ═══════════════════════════════════════════════════════════════

def write_plot_manifest(output_dir, plot_records, data_pattern, insights=None,
                        time_alignment_info=None):
    """
    Write plot_manifest.json — the interface contract to the Diagnostician.

    Parameters
    ----------
    output_dir : str, path to 03_figures/
    plot_records : list of dicts per plot:
        filename, plot_type, description, generation_method (from primitive),
        panels (optional), key_features, anomaly_highlighted
    data_pattern : dict from detect_data_pattern()
    insights : dict with coupling_insights
    time_alignment_info : dict describing alignment strategy used
    """
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "data_dimensions": {
            "type": data_pattern.get('type', 'unknown'),
            "dimensions": data_pattern.get('dimensions', 1),
            "numeric_count": len(data_pattern.get('numeric_columns', [])),
            "total_rows": data_pattern.get('total_rows', 0),
            "time_range": data_pattern.get('time_range'),
            "sampling_info": data_pattern.get('sampling_info', {}),
            "axis_groups": data_pattern.get('axis_groups', {}),
            "spatial_columns": data_pattern.get('spatial_columns', []),
            "frequency_columns": data_pattern.get('frequency_columns', []),
            "batch_columns": data_pattern.get('batch_columns', []),
        },
        "time_alignment": time_alignment_info or {
            "applied": False,
            "method": "none",
            "reason": "regular sampling or single signal"
        },
        "plots": [],
        "coupling_insights": insights or {},
        "interpretation_hints": [],
    }

    for record in plot_records:
        entry = {
            "filename": record.get("filename"),
            "plot_type": record.get("plot_type", "unknown"),
            "description": record.get("description", ""),
            "generation_method": record.get("generation_method", {}),
            "key_features": record.get("key_features", ""),
            "anomaly_highlighted": record.get("anomaly_highlighted", False),
        }
        if "panels" in record:
            entry["panels"] = record["panels"]
        manifest["plots"].append(entry)

    # Auto-generate reading order hints
    if plot_records:
        hints = [f"Read {plot_records[0].get('filename', '?')} first — overview of all signals"]
        for r in plot_records[1:4]:
            feat = r.get('key_features', 'details')
            hints.append(f"Then check {r.get('filename', '?')} — {feat}")
        manifest["interpretation_hints"] = hints

    path = Path(output_dir) / "plot_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str))
    print(f"Manifest: {path}")
    return str(path)


# ═══════════════════════════════════════════════════════════════
#  HELPER
# ═══════════════════════════════════════════════════════════════

def _highlight_anomalies(ax, anomalies):
    """Draw red vertical spans for anomaly intervals."""
    if not anomalies:
        return
    for iv in anomalies:
        try:
            ax.axvspan(pd.to_datetime(iv['start']), pd.to_datetime(iv['end']),
                       alpha=0.15, color='red', zorder=0)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  AGENT COMPOSITION AREA
# ═══════════════════════════════════════════════════════════════
#
# INSTRUCTIONS FOR THE AGENT:
#
# 1. Set the variables below based on your data inspection.
# 2. detect_data_pattern() tells you the data dimension type.
# 3. Based on the type, call the appropriate primitives:
#
#    1d_scalar:
#      → plot_multi_panel_timeseries   (REQUIRED: overview)
#      → plot_correlation_heatmap       (REQUIRED: relationships)
#      → plot_anomaly_zoom              (if anomalies found)
#      → plot_normalized_overlay        (if 3+ coupled signals)
#      → plot_coupling_scatter          (top correlated pair)
#
#    multi_axis:
#      → All 1D plots PLUS:
#      → plot_orbit                     (per axis pair)
#      → plot_axis_ratio                (per axis pair)
#
#    2d_profile:
#      → plot_profile_evolution         (REQUIRED)
#      → plot_position_time_heatmap     (REQUIRED)
#      → plot_deviation_from_target     (if target known)
#
#    batch_event:
#      → plot_box_by_group              (key signal × batch)
#      → plot_event_timeline            (signal + events)
#      → Plus relevant 1D plots per batch
#
#    spectral:
#      → plot_spectrogram               (REQUIRED)
#      → plot_dominant_frequency        (REQUIRED)
#
#    mixed:
#      → Combine primitives from each applicable pattern
#
# 4. After each figure, build a plot_records entry with:
#    filename, plot_type, description, generation_method (return value
#    from the primitive), key_features, anomaly_highlighted
#
# 5. Call write_plot_manifest() at the end.
#

def main():
    # ═══ AGENT: SET THESE VALUES ═══
    INPUT_FILE = "{{INPUT_FILE}}"       # cleaned_data.csv path
    OUTPUT_DIR = "{{OUTPUT_DIR}}"       # RUN_DIR/03_figures
    TIME_COL = "{{TIME_COL}}"           # e.g., "timestamp"
    ANOMALY_INTERVALS = []              # from stats.mjs abnormal_intervals
    DPI = 150
    # ═══════════════════════════════

    out = Path(OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    # Load and classify
    df = load_data(INPUT_FILE, TIME_COL)
    pattern = detect_data_pattern(df, TIME_COL)
    print(f"Pattern: {pattern['type']}, {pattern['dimensions']}D, "
          f"{len(pattern['numeric_columns'])} numeric cols, {len(df)} rows")

    # Time alignment
    time_align_info = {"applied": False, "method": "none"}
    if TIME_COL and not pattern['sampling_info'].get('is_regular', True):
        print("Irregular sampling → aligning to common time grid...")
        df = align_timeindex(df, TIME_COL, method='linear')
        time_align_info = {"applied": True, "method": "linear interpolation",
                           "target_freq": "median interval"}

    all_numeric = [c for c in pattern['numeric_columns'] if c in df.columns]
    plot_records = []

    # ═══ AGENT: COMPOSE VISUALIZATION BELOW ═══
    #
    # This example handles 1d_scalar pattern.
    # Replace with appropriate primitives for your pattern type.
    # See the INSTRUCTIONS above for which primitives to use.
    #

    if pattern['type'] in ('1d_scalar', 'multi_axis', 'mixed'):

        # 1. Multi-panel aligned time-series
        signals = {c: df[c].values for c in all_numeric}
        n = len(signals)
        fig, axes = plt.subplots(n, 1, figsize=(20, 3 * max(n, 1)),
                                 sharex=True, squeeze=False)
        meta = plot_multi_panel_timeseries(fig, axes.flatten(), df[TIME_COL], signals,
                                           ANOMALY_INTERVALS)
        fig.suptitle('Aligned Time-Series Overview', fontweight='bold')
        fig.tight_layout()
        fig.savefig(out / "01_aligned_timeseries.png", dpi=DPI,
                    bbox_inches='tight', facecolor='white')
        plt.close(fig)
        plot_records.append({
            "filename": "01_aligned_timeseries.png",
            "plot_type": "multi_panel_timeseries",
            "description": "Multi-panel aligned time-series of all numeric signals",
            "generation_method": meta,
            "key_features": "Check which signal deviates first from baseline",
            "anomaly_highlighted": bool(ANOMALY_INTERVALS),
        })
        print("  → 01_aligned_timeseries.png")

        # 2. Correlation heatmap
        if len(all_numeric) >= 2:
            n_cols = len(all_numeric)
            fig, ax = plt.subplots(figsize=(max(8, n_cols * 0.8), max(6, n_cols * 0.7)))
            meta = plot_correlation_heatmap(ax, df, all_numeric)
            fig.tight_layout()
            fig.savefig(out / "02_correlation_heatmap.png", dpi=DPI,
                        bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plot_records.append({
                "filename": "02_correlation_heatmap.png",
                "plot_type": "correlation_heatmap",
                "description": "Pearson correlation matrix of all numeric signals",
                "generation_method": meta,
                "key_features": "Identify strongest correlations between process and quality signals",
                "anomaly_highlighted": False,
            })
            print("  → 02_correlation_heatmap.png")

        # 3. Normalized overlay
        if len(all_numeric) >= 3:
            fig, ax = plt.subplots(figsize=(16, 6))
            meta = plot_normalized_overlay(ax, df[TIME_COL], signals, ANOMALY_INTERVALS)
            fig.suptitle('Normalized Signal Overlay', fontweight='bold')
            fig.tight_layout()
            fig.savefig(out / "03_normalized_overlay.png", dpi=DPI,
                        bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plot_records.append({
                "filename": "03_normalized_overlay.png",
                "plot_type": "normalized_overlay",
                "description": "All signals normalized to [0,1] overlaid to reveal temporal coupling",
                "generation_method": meta,
                "key_features": "Aligned peaks/troughs suggest shared root cause",
                "anomaly_highlighted": bool(ANOMALY_INTERVALS),
            })
            print("  → 03_normalized_overlay.png")

        # 4. Anomaly zoom (if anomalies detected)
        if ANOMALY_INTERVALS:
            for a_idx, interval in enumerate(ANOMALY_INTERVALS[:3]):
                onset = interval.get('start_value') or interval.get('start_idx')
                signal_name = interval.get('column', all_numeric[0])
                if signal_name not in df.columns:
                    signal_name = all_numeric[0]
                fig, ax = plt.subplots(figsize=(14, 5))
                meta = plot_anomaly_zoom(ax, df[TIME_COL], df[signal_name],
                                         onset, window_minutes=60, label=signal_name)
                fig.suptitle(f'Anomaly Zoom — {signal_name}', fontweight='bold')
                fig.tight_layout()
                fname = f"04_anomaly_zoom_{a_idx}.png"
                fig.savefig(out / fname, dpi=DPI, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                plot_records.append({
                    "filename": fname,
                    "plot_type": "anomaly_zoom",
                    "description": f"Zoomed view around anomaly onset for {signal_name}",
                    "generation_method": meta,
                    "key_features": "Exact timing and shape of anomaly onset",
                    "anomaly_highlighted": True,
                })
                print(f"  → {fname}")

    # --- Multi-axis extras ---
    if pattern['type'] in ('multi_axis', 'mixed'):
        for stem, cols in pattern['axis_groups'].items():
            if len(cols) < 2:
                continue
            if len(cols) == 2:
                x_col, y_col = cols[0], cols[1]
                fig, ax = plt.subplots(figsize=(8, 8))
                meta = plot_orbit(ax, df[x_col], df[y_col], time=range(len(df)),
                                  x_label=x_col, y_label=y_col, title=f'{stem} Orbit')
                fig.tight_layout()
                fname = f"orbit_{stem}.png"
                fig.savefig(out / fname, dpi=DPI, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                plot_records.append({
                    "filename": fname,
                    "plot_type": "orbit",
                    "description": f"2D orbit plot for {stem} ({x_col} vs {y_col})",
                    "generation_method": meta,
                    "key_features": "Round orbit → single source; distorted → multiple sources",
                    "anomaly_highlighted": False,
                })

            for i in range(len(cols)):
                for j in range(i + 1, min(i + 2, len(cols))):
                    fig, ax = plt.subplots(figsize=(14, 4))
                    meta = plot_axis_ratio(ax, df[TIME_COL], df[cols[i]], df[cols[j]],
                                           cols[i], cols[j])
                    fig.tight_layout()
                    fname = f"axis_ratio_{cols[i]}_{cols[j]}.png"
                    fig.savefig(out / fname, dpi=DPI, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    plot_records.append({
                        "filename": fname,
                        "plot_type": "axis_ratio",
                        "description": f"Ratio {cols[i]}/{cols[j]} over time",
                        "generation_method": meta,
                        "key_features": "Constant ratio → single fault source",
                        "anomaly_highlighted": False,
                    })

    # --- 2D Profile ---
    if pattern['type'] in ('2d_profile', 'mixed') and pattern['spatial_columns']:
        # Agent: customize this section based on actual spatial column structure
        print("  [2D profile primitives available — customize in main()]")

    # --- Batch/Event ---
    if pattern['type'] in ('batch_event', 'mixed') and pattern['batch_columns']:
        batch_col = pattern['batch_columns'][0]
        for sig in all_numeric[:4]:
            fig, ax = plt.subplots(figsize=(12, 5))
            meta = plot_box_by_group(ax, df, sig, batch_col)
            fig.tight_layout()
            fname = f"box_{sig}_by_{batch_col}.png"
            fig.savefig(out / fname, dpi=DPI, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            plot_records.append({
                "filename": fname,
                "plot_type": "box_by_group",
                "description": f"Distribution of {sig} by {batch_col}",
                "generation_method": meta,
                "key_features": "Compare signal distributions across batches",
                "anomaly_highlighted": False,
            })

    # --- Spectral ---
    if pattern['type'] in ('spectral', 'mixed'):
        print("  [Spectral primitives available — customize in main()]")

    # ═══ Write manifest ═══
    write_plot_manifest(OUTPUT_DIR, plot_records, pattern,
                        time_alignment_info=time_align_info)
    print(f"Done: {len(plot_records)} plots generated.")


if __name__ == "__main__":
    main()
