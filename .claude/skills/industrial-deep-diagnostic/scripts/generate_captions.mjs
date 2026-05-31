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

  // ── Diagnostic implication per plot_type ──
  // Each implication tells the Diagnostician WHY this plot matters for root cause tracing
  const plotTypeToImplication = {
    correlation_heatmap: '显示所有参数间的线性关系强度，用于快速识别与质量目标高度相关的候选参数',
    top_correlation_bar: '按相关性排序的候选参数列表，用于优先筛选需要物理验证的根因候选',
    param_timeseries: '参数随时间的变化趋势，用于判断是否有漂移、阶跃或周期性模式——退化型根因表现为单调递增/减',
    quality_timeseries: '质量指标随时间的变化趋势，用于定位质量退化的起始点和恶化速度',
    normalized_overlay: '多参数归一化叠加对比，用于观察参数变化的时序先后关系——先变者可能是因，后变者可能是果',
    scatter_plot: '参数与质量指标的直接关联散点图，用于判断线性/非线性关系及是否存在阈值效应',
    coupling_scatter: '两个过程参数的耦合关系散点图——强耦合意味着共享上游退化机制',
    stratified_correlation: '按产品/批次分层的相关性对比，用于检测Simpson Paradox——全局高r但组内无关联说明不是因果',
    detrended_comparison: '去趋势前后的相关性对比，用于判断关联是否由共同时间趋势造成的伪相关',
    outlier_sensitivity: '去除离群点前后的相关性对比，用于判断关联是否由少数极端值驱动',
    product_timeseries: '按产品分层的质量时间序列，用于判断质量退化是否在所有产品上一致——通用退化 vs 产品特异',
    product_param_profile: '不同产品的参数分布对比，用于判断参数设定差异是否导致质量差异',
    within_product_correlation: '组内相关性矩阵，用于排除BETWEEN_PRODUCT_ONLY的伪因果',
    product_defect_scatter: '产品分组下的参数-缺陷散点图，用于验证关联是否在每个产品内都成立',
    cross_product_consistency: '跨产品的相关性方向和强度一致性条形图——UNIVERSAL因果的必经验证',
    product_switch_timeline: '产品切换时序图，用于观察切换瞬间质量是否有跳变——切换导致的质量变化说明参数设定影响质量',
    param_defect_aligned: '双Y轴时间对齐图，用于观察参数变化与缺陷的时序关系——参数变化先于缺陷=潜在因果，同步变化=相关但不一定因果',
    stage_aligned_timeseries: '按工艺阶段对齐的参数量纲图，用于将参数映射到具体工艺阶段——追踪根因在哪个阶段引入',
    physical_coupling: '两个物理量参数的耦合关系图，用于验证已知物理定律是否成立——如振动与温度通过轴承磨损耦合',
    physical_mechanism: '物理机制验证散点图，用于检验物理公式在实际数据中的适用性——如ΔL=α×L×ΔT是否成立',
    physical_cascade: '物理级联效应图，用于展现一个根因通过多级传递影响最终质量——如轴承磨损→振动↑→粗糙度↑→尺寸偏差↑',
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
      diagnostic_implication: plotTypeToImplication[plotType] || plotTypeToImplication[chartType] || '此图展示参数关联关系，用于辅助根因分析',
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
