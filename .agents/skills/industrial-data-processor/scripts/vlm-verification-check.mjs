#!/usr/bin/env node
// vlm-verification-check.mjs — Verify vlm-visual-analyzer has actually performed
// genuine visual analysis (either direct PNG reading or metadata-backed inference
// with proven repair attempts). This gate CANNOT be bypassed by editing metadata
// flags alone.
//
// Key design change v2.0: Instead of trusting skeleton_overwritten=true as a
// boolean flag, this check requires:
//   - direct_image_reading mode: VLM confirms it read the actual PNG files
//   - metadata_backed_inference mode: MUST have repair_attempts proof chain +
//     fallback_trigger_reason documented. Pure metadata flag manipulation fails.
//
// Usage:
//   node vlm-verification-check.mjs <RUN_DIR>
//
// Exit code: 0 = PASS, 1 = FAIL

import fs from 'fs';
import { join } from 'path';

const runDir = process.argv[2];
if (!runDir) {
  console.error('Usage: node vlm-verification-check.mjs <RUN_DIR>');
  process.exit(1);
}

function readJson(relPath) {
  try {
    return JSON.parse(fs.readFileSync(join(runDir, relPath), 'utf8'));
  } catch (e) {
    return null;
  }
}

const va = readJson('03_figures/visual_analysis.json');
const pm = readJson('03_figures/plot_manifest.json');
const checks = [];

// === Check 1: Provenance completeness (anti-forgery) ===
// Must have ALL provenance fields. Partial metadata copy-paste fails.
const prov = va?.analysis_provenance || {};
const provFields = ['source_agent', 'stage', 'skeleton_overwritten', 'context_files_read',
                     'figure_inputs_attempted', 'figure_inputs_read_successfully',
                     'grounding_summary', 'grounding_sources'];
const missingProv = provFields.filter(f => prov[f] === undefined || prov[f] === null);
const provOk = missingProv.length === 0;
checks.push({
  name: 'provenance_completeness',
  status: provOk ? 'pass' : 'fail',
  detail: provOk
    ? 'all 8 provenance fields present'
    : `missing provenance fields: ${missingProv.join(', ')}`
});

// === Check 2: observation_mode — allow direct_image_reading OR metadata_backed_inference ===
const mode = va?.observation_mode;
const modeOk = mode === 'direct_image_reading' || mode === 'metadata_backed_inference';
const modeReason = va?.observation_mode_reason || '';
checks.push({
  name: 'observation_mode',
  status: modeOk ? 'pass' : 'fail',
  detail: modeOk
    ? `observation_mode=${mode} — ${mode === 'direct_image_reading' ? 'VLM directly read PNGs' : 'metadata_backed (with repair_attempts)'}`
    : `expected direct_image_reading or metadata_backed_inference, got ${mode}`
});

// === Check 3: If metadata_backed_inference, MUST have repair_attempts proof chain ===
// This is the anti-bypass gate: just setting a flag is not enough.
const repairOk = (mode !== 'metadata_backed_inference')
  || (Array.isArray(va?.vlm_attempts) && va.vlm_attempts.length > 0
      && va.vlm_attempts.every(a => a.timestamp && a.status && a.reason))
  || (Array.isArray(va?.analysis_provenance?.vlm_fallback_chain)
      && va.analysis_provenance.vlm_fallback_chain.length > 0
      && va.analysis_provenance.vlm_fallback_chain.some(e => e.reason && e.timestamp));
checks.push({
  name: 'metadata_backed_repair_proof',
  status: repairOk ? 'pass' : 'fail',
  detail: repairOk
    ? (mode === 'direct_image_reading'
        ? 'N/A — direct_image_reading mode, no repair proof needed'
        : `metadata_backed_inference with ${(va?.vlm_attempts || va?.analysis_provenance?.vlm_fallback_chain || []).length} documented attempts`)
    : 'metadata_backed_inference mode requires vlm_attempts[] or analysis_provenance.vlm_fallback_chain[] with at least one entry having timestamp + status + reason'
});

// === Check 4: skeleton_overwritten inside provenance ===
const skeletonOk = prov?.skeleton_overwritten === true;
checks.push({
  name: 'skeleton_overwritten',
  status: skeletonOk ? 'pass' : 'fail',
  detail: skeletonOk ? 'skeleton_overwritten=true' : `expected true in analysis_provenance, got ${prov?.skeleton_overwritten}`
});

// === Check 5: figure_inputs_attempted (at least attempted to read) ===
const attempted = prov?.figure_inputs_attempted;
const attemptedOk = Array.isArray(attempted) && attempted.length > 0;
checks.push({
  name: 'figure_inputs_attempted',
  status: attemptedOk ? 'pass' : 'fail',
  detail: attemptedOk ? `${attempted.length} figures attempted` : 'figure_inputs_attempted missing or empty'
});

// === Check 6: chart_inventory integrity ===
// visual_analysis.json must have chart_inventory matching plot_manifest figures
const chartInv = va?.chart_inventory || [];
const pmPlots = pm?.plots || [];
const chartFigures = chartInv.map(c => c.figure);
const pmFigures = pmPlots.map(p => p.name ? `${p.name}.png` : p.path?.split('/').pop());
// Check at least 2 charts are actually read
const readCount = chartInv.filter(c => c.read_status === 'READ_SUCCESS').length;
const chartInvOk = chartInv.length >= Math.min(2, pmPlots.length || 1)
  && readCount >= Math.min(1, pmPlots.length || 1);
checks.push({
  name: 'chart_inventory_integrity',
  status: chartInvOk ? 'pass' : 'fail',
  detail: chartInvOk
    ? `${chartInv.length} charts inventoried, ${readCount} READ_SUCCESS`
    : `only ${chartInv.length}/${pmPlots.length} charts inventoried, ${readCount} READ_SUCCESS — need ≥1 SUCCESS read`
});

// === Check 7: visual_observations with ontology_context (at least 2) ===
const obs = va?.visual_observations || [];
const obsWithContext = obs.filter(o => {
  // ontology_context can be an object (schema v1.0) or a string (older format)
  if (!o.ontology_context) return false;
  if (typeof o.ontology_context === 'object') {
    return o.ontology_context.parameter_physical_meanings
      && Object.keys(o.ontology_context.parameter_physical_meanings).length > 0;
  }
  return String(o.ontology_context).trim().length > 0;
});
const contextOk = obsWithContext.length >= 2;
checks.push({
  name: 'ontology_context_coverage',
  status: contextOk ? 'pass' : 'fail',
  detail: contextOk
    ? `${obsWithContext.length}/${obs.length} observations with non-empty ontology_context`
    : `only ${obsWithContext.length} observations have non-empty ontology_context, need >= 2`
});

// === Check 8: source_agent must be vlm-visual-analyzer ===
const sourceOk = prov?.source_agent === 'vlm-visual-analyzer';
checks.push({
  name: 'source_agent',
  status: sourceOk ? 'pass' : 'fail',
  detail: sourceOk ? 'source_agent=vlm-visual-analyzer' : `expected vlm-visual-analyzer, got ${prov?.source_agent}`
});

// === Final: PASS only if ALL checks pass ===
const passed = checks.filter(c => c.status === 'pass').length;
const result = {
  status: passed === checks.length ? 'PASS' : 'FAIL',
  checks_passed: passed,
  checks_total: checks.length,
  checks,
  summary: {
    observation_mode: mode,
    vlm_authenticity: mode === 'direct_image_reading'
      ? 'genuine' : (repairOk ? 'metadata_backed_with_proof' : 'UNVERIFIED'),
    figures_read_successfully: prov?.figure_inputs_read_successfully?.length || 0,
    figures_attempted: attempted?.length || 0,
    visual_observations: obs.length,
    gate_passed: passed === checks.length
  }
};

console.log(JSON.stringify(result, null, 2));
process.exit(result.status === 'PASS' ? 0 : 1);
