#!/usr/bin/env node
// file-integrity-restorer.mjs — Auto-generate minimal valid versions of missing
// critical artifacts after data-processor completes.
//
// Usage:
//   node file-integrity-restorer.mjs <RUN_DIR> <SKILL_PATH>
//
// Exit code: 0 always (non-blocking by design)

import fs from 'fs';
import { join } from 'path';

const [runDir, skillPath] = process.argv.slice(2);
if (!runDir || !skillPath) {
  console.error('Usage: node file-integrity-restorer.mjs <RUN_DIR> <SKILL_PATH>');
  process.exit(1);
}

function readJson(relPath) {
  try {
    return JSON.parse(fs.readFileSync(join(runDir, relPath), 'utf8'));
  } catch { return null; }
}

const result = { restored: [], failed: [], already_exist: [] };

// 1. scenario_classification.json
const scPath = join(runDir, '02_processed/scenario_classification.json');
if (fs.existsSync(scPath)) {
  result.already_exist.push('scenario_classification.json');
} else {
  try {
    const ontology = readJson('01_ontology/ontology.json') || {};
    const processType = ontology.process_type || 'unknown';
    const classification = {
      scenario: processType,
      data_view_mode: readJson('02_processed/feature_summary.json')?.metadata?.data_view_mode || 'unknown',
      generated_by: 'file-integrity-restorer (auto-recovery)',
      generated_at: new Date().toISOString()
    };
    fs.writeFileSync(scPath, JSON.stringify(classification, null, 2));
    result.restored.push('scenario_classification.json');
  } catch (e) {
    result.failed.push({ file: 'scenario_classification.json', reason: e.message });
  }
}

// 2. anomaly_report.json
const arPath = join(runDir, '02_processed/anomaly_report.json');
if (fs.existsSync(arPath)) {
  result.already_exist.push('anomaly_report.json');
} else {
  try {
    const dataConc = readJson('02_processed/data_analysis_conclusion.json') || {};
    const anomaly = {
      status: 'auto_generated',
      anomaly_windows: dataConc.anomaly_highlights?.anomaly_windows || [],
      summary: {
        abnormal_params: dataConc.process_health?.abnormal_params || [],
        regime_shifts: dataConc.process_health?.regime_shifts_detected || false,
        steady_state_ratio: dataConc.process_health?.steady_state_ratio || 1
      },
      generated_by: 'file-integrity-restorer (auto-recovery)',
      generated_at: new Date().toISOString()
    };
    fs.writeFileSync(arPath, JSON.stringify(anomaly, null, 2));
    result.restored.push('anomaly_report.json');
  } catch (e) {
    result.failed.push({ file: 'anomaly_report.json', reason: e.message });
  }
}

// 3. plot_manifest.json
const pmPath = join(runDir, '03_figures/plot_manifest.json');
if (fs.existsSync(pmPath)) {
  result.already_exist.push('plot_manifest.json');
} else {
  try {
    const figuresDir = join(runDir, '03_figures');
    const plots = [];
    if (fs.existsSync(figuresDir)) {
      const files = fs.readdirSync(figuresDir).filter(f => f.endsWith('.png'));
      for (const f of files) {
        plots.push({
          file: `03_figures/${f}`,
          type: f.includes('timeseries') || f.includes('temporal') ? 'time_series' : 'correlation',
          purpose: 'auto-detected from filename',
          generated_by: 'file-integrity-restorer'
        });
      }
    }
    const manifest = { plots, generated_by: 'file-integrity-restorer', generated_at: new Date().toISOString() };
    fs.writeFileSync(pmPath, JSON.stringify(manifest, null, 2));
    result.restored.push('plot_manifest.json');
  } catch (e) {
    result.failed.push({ file: 'plot_manifest.json', reason: e.message });
  }
}

// 4. image_captions.json
const icPath = join(runDir, '03_figures/image_captions.json');
if (fs.existsSync(icPath)) {
  result.already_exist.push('image_captions.json');
} else {
  try {
    const pm = readJson('03_figures/plot_manifest.json') || {};
    const captions = (pm.plots || []).map(p => ({
      figure: p.file,
      caption: `Auto-generated caption for ${p.file}`,
      generated_by: 'file-integrity-restorer'
    }));
    const ic = { captions, generated_by: 'file-integrity-restorer', generated_at: new Date().toISOString() };
    fs.writeFileSync(icPath, JSON.stringify(ic, null, 2));
    result.restored.push('image_captions.json');
  } catch (e) {
    result.failed.push({ file: 'image_captions.json', reason: e.message });
  }
}

console.log(JSON.stringify(result, null, 2));
