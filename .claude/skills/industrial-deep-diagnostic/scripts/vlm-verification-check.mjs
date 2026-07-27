#!/usr/bin/env node
// vlm-verification-check.mjs — Verify vlm-visual-analyzer has overwritten the
// skeleton and produced a genuine VLM output.
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
const checks = [];

// Check 1: skeleton_overwritten === true
const skeletonOk = va?.analysis_provenance?.skeleton_overwritten === true;
checks.push({
  name: 'skeleton_overwritten',
  status: skeletonOk ? 'pass' : 'fail',
  detail: skeletonOk ? 'skeleton_overwritten=true' : `expected true, got ${va?.analysis_provenance?.skeleton_overwritten}`
});

// Check 2: observation_mode === "final_vlm_output"
const modeOk = va?.observation_mode === 'final_vlm_output';
checks.push({
  name: 'observation_mode',
  status: modeOk ? 'pass' : 'fail',
  detail: modeOk ? 'observation_mode=final_vlm_output' : `expected final_vlm_output, got ${va?.observation_mode}`
});

// Check 3: figure_inputs_read_successfully is non-empty array
const inputsOk = Array.isArray(va?.analysis_provenance?.figure_inputs_read_successfully)
  && va.analysis_provenance.figure_inputs_read_successfully.length > 0;
checks.push({
  name: 'figure_inputs_read',
  status: inputsOk ? 'pass' : 'fail',
  detail: inputsOk
    ? `${va.analysis_provenance.figure_inputs_read_successfully.length} figures read`
    : 'figure_inputs_read_successfully missing or empty'
});

// Check 4: at least 2 visual_observations with non-empty ontology_context
const obsWithContext = (va?.visual_observations || [])
  .filter(o => o.ontology_context && String(o.ontology_context).trim().length > 0);
const contextOk = obsWithContext.length >= 2;
checks.push({
  name: 'ontology_context_coverage',
  status: contextOk ? 'pass' : 'fail',
  detail: contextOk
    ? `${obsWithContext.length} observations with ontology_context`
    : `only ${obsWithContext.length} observations have non-empty ontology_context, need >= 2`
});

// Check 5: source_agent === "vlm-visual-analyzer"
const sourceOk = va?.analysis_provenance?.source_agent === 'vlm-visual-analyzer';
checks.push({
  name: 'source_agent',
  status: sourceOk ? 'pass' : 'fail',
  detail: sourceOk ? 'source_agent=vlm-visual-analyzer' : `expected vlm-visual-analyzer, got ${va?.analysis_provenance?.source_agent}`
});

const passed = checks.filter(c => c.status === 'pass').length;
const result = {
  status: passed === checks.length ? 'PASS' : 'FAIL',
  checks_passed: passed,
  checks_total: checks.length,
  checks
};

console.log(JSON.stringify(result, null, 2));
process.exit(result.status === 'PASS' ? 0 : 1);
