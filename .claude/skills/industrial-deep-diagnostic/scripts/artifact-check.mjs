#!/usr/bin/env node
// artifact-check.mjs — Verify all required pipeline artifacts exist
// Run at pipeline completion to validate integrity.
//
// Usage: node artifact-check.mjs <run_dir> [skill_path]
//   Returns exit code 0 if all required files exist, 1 otherwise.
//   Prints missing files report to stdout.

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];
const skillPath = args[1] || '.';

if (!runDir) {
  console.error('Usage: node artifact-check.mjs <run_dir> [skill_path]');
  process.exit(1);
}

function exists(p) {
  return fs.existsSync(join(runDir, p));
}

function check(label, filePath, critical = true) {
  const fullPath = join(runDir, filePath);
  if (!fs.existsSync(fullPath)) {
    return { label, path: filePath, status: critical ? 'MISSING (critical)' : 'MISSING', critical };
  }
  const stat = fs.statSync(fullPath);
  const sizeKb = (stat.size / 1024).toFixed(1);
  return { label, path: filePath, status: `OK (${sizeKb} KB)`, critical };
}

// Define required artifacts per pipeline stage
const checks = [
  // Stage 1: Input
  check('Input Manifest', '00_input/input_manifest.json', false),
  check('User Context', '00_input/user_context.json', false),

  // Stage 2: Context
  check('Ontology', '01_ontology/ontology.json'),
  check('Schema', '01_ontology/schema.json'),

  // Stage 3: Data Processing
  check('Data JSON', '02_processed/data.json', false),
  check('Cleaned Data CSV', '02_processed/cleaned_data.csv', false),
  check('Cleaned Data JSON', '02_processed/cleaned_data.json', false),
  check('Feature Summary', '02_processed/feature_summary.json'),
  check('Validate Report', '02_processed/validate_report.json'),
  check('Data Quality Report', '02_processed/data_quality_report.json', false),
  check('Plot Manifest', '03_figures/plot_manifest.json'),

  // Stage 4: Diagnosis
  check('Diagnosis', '04_diagnostics/diagnosis.json'),
  check('Evidence', '04_diagnostics/evidence.json'),
  check('Confidence', '04_diagnostics/confidence.json'),

  // Stage 5: Judge
  check('Judge Feedback', '05_review/judge_feedback.json', false),

  // Stage 6: Report
  check('Report', 'report.md', false),
  check('Run Summary', 'run_summary.json', false),

  // Stage 7: Optimizer
  check('Optimizer', 'optimizer.md', false),
];

// Count figures
let figureCount = 0;
const figuresDir = join(runDir, '03_figures');
if (fs.existsSync(figuresDir)) {
  try {
    const entries = fs.readdirSync(figuresDir);
    figureCount = entries.filter(f => f.endsWith('.png')).length;
  } catch (_) {}
}

const missing = checks.filter(c => c.status.startsWith('MISSING'));
const criticalMissing = missing.filter(c => c.critical);
const warnings = checks.filter(c => c.status.startsWith('MISSING') && !c.critical);

const report = {
  run_dir: runDir,
  verified_at: new Date().toISOString(),
  figure_count: figureCount,
  integrity_check: criticalMissing.length === 0 ? 'PASS' : 'FAIL',
  summary: {
    total_checks: checks.length,
    ok: checks.length - missing.length,
    missing_critical: criticalMissing.length,
    missing_optional: warnings.length,
    figures_generated: figureCount
  },
  critical_gaps: criticalMissing.map(c => ({ file: c.path, stage: c.label })),
  details: checks
};

console.log(JSON.stringify(report, null, 2));
process.exit(report.integrity_check === 'PASS' ? 0 : 1);
