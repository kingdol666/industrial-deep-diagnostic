#!/usr/bin/env node
// schema-validation-loop.mjs — Run schema validation for a given agent's outputs.
//
// Usage:
//   node schema-validation-loop.mjs <RUN_DIR> <SKILL_PATH> <AGENT_NAME>
//
// AGENT_NAME: context-builder | data-processor | vlm-visual-analyzer | diagnostician | judge | reporter | html-reviewer
//
// Exit code: 0 = all PASS, 1 = partial, 2 = all FAIL

import fs from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const [runDir, skillPath, agentName] = process.argv.slice(2);

if (!runDir || !skillPath || !agentName) {
  console.error('Usage: node schema-validation-loop.mjs <RUN_DIR> <SKILL_PATH> <AGENT_NAME>');
  process.exit(2);
}

const SCHEMAS_DIR = join(skillPath, '../../shared/schemas');
const AGENT_MAP = {
  'context-builder': ['ontology_schema.json'],
  'data-processor': ['data_analysis_conclusion_schema.json'],
  'vlm-visual-analyzer': ['visual_analysis_schema.json', 'image_captions_schema.json'],
  diagnostician: ['diagnosis_schema.json', 'evidence_schema.json', 'confidence_schema.json', 'reasoning_chain_schema.json'],
  judge: ['judge_feedback_schema.json'],
  reporter: ['run_summary_schema.json'],
  'html-reviewer': ['html_review_schema.json'],
};

function resolveOutput(schemaFile) {
  const map = {
    ontology_schema_json: '01_ontology/ontology.json',
    data_analysis_conclusion_schema_json: '02_processed/data_analysis_conclusion.json',
    visual_analysis_schema_json: '03_figures/visual_analysis.json',
    image_captions_schema_json: '03_figures/image_captions.json',
    diagnosis_schema_json: '04_diagnostics/diagnosis.json',
    evidence_schema_json: '04_diagnostics/evidence.json',
    confidence_schema_json: '04_diagnostics/confidence.json',
    reasoning_chain_schema_json: '04_diagnostics/reasoning_chain.json',
    judge_feedback_schema_json: '05_review/judge_feedback.json',
    run_summary_schema_json: 'run_summary.json',
    html_review_schema_json: '05_review/html_review.json',
  };
  const key = schemaFile.replace(/\.json$/, '').replace(/\./g, '_');
  return map[key] || schemaFile.replace('_schema', '');
}

const schemas = AGENT_MAP[agentName];
if (!schemas) {
  console.error(`Unknown agent: ${agentName}. Valid: ${Object.keys(AGENT_MAP).join(', ')}`);
  process.exit(2);
}

const checks = [];

for (const schemaFile of schemas) {
  const schemaPath = join(SCHEMAS_DIR, schemaFile);
  const outputRel = resolveOutput(schemaFile);
  const outputPath = join(runDir, outputRel);

  if (!fs.existsSync(outputPath)) {
    checks.push({
      agent: agentName,
      schema: schemaFile,
      file: outputRel,
      valid: false,
      errors: `File not found: ${outputPath}`
    });
    continue;
  }

  const validateScript = join(skillPath, '../../shared/scripts', 'validate.mjs');
  if (!fs.existsSync(validateScript)) {
    checks.push({
      agent: agentName,
      schema: schemaFile,
      file: outputRel,
      valid: false,
      errors: `validate.mjs not found at ${validateScript}`
    });
    continue;
  }

  try {
    const cmd = `node "${validateScript}" "${schemaPath}" "${outputPath}"`;
    execSync(cmd, { stdio: ['pipe', 'pipe', 'pipe'], timeout: 15000 });
    checks.push({
      agent: agentName,
      schema: schemaFile,
      file: outputRel,
      valid: true
    });
  } catch (err) {
    const stderr = err.stderr?.toString() || err.message || '';
    checks.push({
      agent: agentName,
      schema: schemaFile,
      file: outputRel,
      valid: false,
      errors: stderr.substring(0, 500)
    });
  }
}

// Additional content checks for diagnostician
if (agentName === 'diagnostician') {
  try {
    const diagnosis = JSON.parse(fs.readFileSync(join(runDir, '04_diagnostics/diagnosis.json'), 'utf8'));
    const hypotheses = diagnosis.hypotheses?.surviving || [];
    if (hypotheses.length === 0) {
      checks.push({
        agent: 'diagnostician',
        schema: 'content_check',
        file: '04_diagnostics/diagnosis.json',
        valid: false,
        errors: 'hypotheses.surviving is empty — no surviving hypotheses'
      });
    }
  } catch (_) { /* skip */ }

  try {
    const evidence = JSON.parse(fs.readFileSync(join(runDir, '04_diagnostics/evidence.json'), 'utf8'));
    const inventory = evidence.evidence_inventory || {};
    const hasVisual = Array.isArray(inventory.visual_evidence) && inventory.visual_evidence.length > 0;
    const hasNumerical = Array.isArray(inventory.numerical_evidence) && inventory.numerical_evidence.length > 0;
    if (!hasVisual && !hasNumerical) {
      checks.push({
        agent: 'diagnostician',
        schema: 'content_check',
        file: '04_diagnostics/evidence.json',
        valid: false,
        errors: 'evidence_inventory has neither visual_evidence nor numerical_evidence'
      });
    }
  } catch (_) { /* skip */ }

  try {
    const confidence = JSON.parse(fs.readFileSync(join(runDir, '04_diagnostics/confidence.json'), 'utf8'));
    const breakdowns = confidence.confidence_breakdown || [];
    if (breakdowns.length === 0) {
      checks.push({
        agent: 'diagnostician',
        schema: 'content_check',
        file: '04_diagnostics/confidence.json',
        valid: false,
        errors: 'confidence_breakdown is empty — no hypothesis confidence scores'
      });
    }
  } catch (_) { /* skip */ }
}

const passedCount = checks.filter(c => c.valid === true).length;
const failedCount = checks.filter(c => c.valid === false).length;

const result = {
  status: failedCount === 0 ? 'PASS' : passedCount > 0 ? 'PARTIAL' : 'FAIL',
  checks
};

console.log(JSON.stringify(result, null, 2));

if (failedCount === 0) process.exit(0);
else if (passedCount > 0) process.exit(1);
else process.exit(2);
