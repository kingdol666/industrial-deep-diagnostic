#!/usr/bin/env node
/**
 * generate_captions.mjs — Zero-dependency Node.js script
 * Generates structured image_captions.json from plot_manifest.json + feature_summary.json + validate_report.json
 * Provides fallback for Reporter when PNG rendering is unavailable.
 *
 * Usage: node generate_captions.mjs <RUN_DIR>
 */

import fs from 'fs';
import path from 'path';

const RUN_DIR = process.argv[2];
if (!RUN_DIR) {
  console.error('Usage: node generate_captions.mjs <RUN_DIR>');
  process.exit(1);
}

function loadJSON(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch {
    return null;
  }
}

function main() {
  const manifestPath = path.join(RUN_DIR, '03_figures', 'plot_manifest.json');
  const featurePath = path.join(RUN_DIR, '02_processed', 'feature_summary.json');
  const validatePath = path.join(RUN_DIR, '02_processed', 'validate_report.json');
  const outputPath  = path.join(RUN_DIR, '03_figures', 'image_captions.json');

  // ── Load inputs ──
  const manifest = loadJSON(manifestPath);
  if (!manifest || !manifest.plots || !Array.isArray(manifest.plots)) {
    console.error('ERROR: plot_manifest.json not found or has no "plots" array at', manifestPath);
    process.exit(1);
  }

  const featureSummary = loadJSON(featurePath);
  const validateReport = loadJSON(validatePath);

  // ── Extract validation issues for cross-referencing ──
  const validationIssues = [];
  if (validateReport) {
    // gather issues from various sections
    const sections = [
      validateReport.simpsons_paradox,
      validateReport.trend_confounding,
      validateReport.outlier_sensitivity,
      validateReport.change_points,
      validateReport.pearson_spearman_divergence,
    ];
    for (const sec of sections) {
      if (sec && Array.isArray(sec.findings)) {
        for (const f of sec.findings) {
          if (f.description) validationIssues.push(f.description);
          if (f.summary)   validationIssues.push(f.summary);
        }
      }
      if (sec && typeof sec.summary === 'string') {
        validationIssues.push(sec.summary);
      }
    }
  }

  // ── Top correlations for key_observations cross-referencing ──
  const topCorrs = [];
  if (featureSummary?.pearson_correlations) {
    const entries = [];
    const corrs = featureSummary.pearson_correlations;
    if (Array.isArray(corrs)) {
      for (const c of corrs) {
        if (c.pair && typeof c.r === 'number') {
          entries.push({ pair: c.pair, r: c.r });
        }
      }
    } else if (typeof corrs === 'object') {
      for (const [key, val] of Object.entries(corrs)) {
        if (typeof val === 'number') entries.push({ pair: key, r: val });
        else if (val && typeof val.r === 'number') entries.push({ pair: key, ...val });
      }
    }
    entries.sort((a, b) => Math.abs(b.r) - Math.abs(a.r));
    for (const e of entries.slice(0, 10)) {
      topCorrs.push(`${e.pair} r=${e.r?.toFixed?.(3) ?? e.r}`);
    }
  }

  if (featureSummary?.spearman_correlations) {
    // also note if there's Pearson-Spearman divergence
  }

  // ── Chart type mapping from plot_type ──
  const plotTypeToChart = {
    correlation_heatmap: 'heatmap',
    top_correlation_bar: 'bar',
    param_timeseries: 'line',
    quality_timeseries: 'line',
    normalized_overlay: 'overlay',
    scatter_plot: 'scatter',
    coupling_scatter: 'scatter',
    stratified_correlation: 'heatmap',
    detrended_comparison: 'scatter',
    outlier_sensitivity: 'scatter',
    product_timeseries: 'line',
    product_param_profile: 'scatter',
    within_product_correlation: 'heatmap',
    product_defect_scatter: 'scatter',
    cross_product_consistency: 'bar',
    product_switch_timeline: 'line',
    param_defect_aligned: 'scatter',
    stage_aligned_timeseries: 'line',
    physical_coupling: 'scatter',
    physical_mechanism: 'scatter',
    physical_cascade: 'scatter',
  };

  // ── Build figure captions ──
  const figures = {};

  for (const plot of manifest.plots) {
    const fname = plot.filename;
    const figId = fname.replace(/^fig_(\d+)_.*\.png$/, 'fig_$1');
    const plotType = plot.plot_type || 'unknown';

    // Derive chart_type
    const chartType = plotTypeToChart[plotType] || plotType;

    // Derive axes from generation_method or plot_type
    let axes = {};
    if (plot.generation_method) {
      const gm = plot.generation_method;
      if (gm.function === 'plot_correlation_heatmap') {
        axes = { x: `${gm.n_cols || 'N'} numeric columns`, y: `${gm.n_cols || 'N'} numeric columns`, color: 'Pearson r' };
      } else if (gm.function?.includes('timeseries')) {
        axes = { x: 'time', y: gm.targets || gm.params || 'value' };
      } else if (gm.function?.includes('scatter')) {
        axes = { x: gm.x_param || gm.x || 'Parameter', y: gm.y_param || gm.y || 'Quality metric' };
      } else {
        axes = { ...gm, function: undefined };
        delete axes.function;
        delete axes.library;
      }
    }

    // Key observations from plot's own key_features
    const keyObs = plot.key_features
      ? plot.key_features.split(/[;；]\s*/).filter(Boolean).map(s => s.trim())
      : [];

    // Trend shapes inference from plot_type and key_features
    let trendShapes = '';
    if (plotType.includes('timeseries') || plotType.includes('time')) {
      trendShapes = '时间序列随时间漂移，含潜在趋势变化';
    } else if (plotType.includes('heatmap') || plotType.includes('correlation')) {
      trendShapes = '相关矩阵呈现聚类结构，可观察参数分群';
    } else if (plotType.includes('scatter')) {
      trendShapes = '散点图分布，可观察线性/非线性关系和离群点';
    } else if (plotType.includes('bar')) {
      trendShapes = '条形图排序，可观察参数相对重要性';
    }

    // Cross-reference validation issues
    const plotValidationIssues = [];
    if (plot.anomaly_highlighted) {
      plotValidationIssues.push('此图标注了异常区域');
    }
    // match validation issues that mention keywords from this plot's description
    const descLower = (plot.description || '').toLowerCase();
    for (const vi of validationIssues) {
      if (vi && descLower && plotValidationIssues.length < 3) {
        // simple keyword-based matching
        const viLower = vi.toLowerCase();
        const words = ['hardness', 'simpson', 'paradox', 'outlier', 'detrend', 'change', 'regime', 'sorting'];
        for (const w of words) {
          if (descLower.includes(w) && viLower.includes(w)) {
            plotValidationIssues.push(vi);
            break;
          }
        }
      }
    }

    // Build description: one-paragraph summary
    const fullDesc = plot.description || `${plotType} of ${fname}`;

    figures[fname] = {
      figure_id: figId,
      title: plot.title || fname,
      chart_type: chartType,
      axes,
      key_observations: keyObs.length > 0 ? keyObs : [fullDesc],
      trend_shapes: trendShapes || '参见 key_observations',
      validation_issues: plotValidationIssues,
      description: fullDesc,
    };
  }

  // ── Build output ──
  const output = {
    generated_at: new Date().toISOString(),
    source_files: {
      plot_manifest: '03_figures/plot_manifest.json',
      feature_summary: featureSummary ? '02_processed/feature_summary.json' : null,
      validate_report: validateReport ? '02_processed/validate_report.json' : null,
    },
    total_figures: Object.keys(figures).length,
    figures,
  };

  // ── Write ──
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2), 'utf-8');
  console.log(`Generated ${outputPath} with ${output.total_figures} figure captions`);
}

main();
