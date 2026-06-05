#!/usr/bin/env node
// eval-assertions.mjs — Execute domain-specific eval assertions against a run
// and optionally emit skill-creator-compatible grading.json.
//
// Usage:
//   node eval-assertions.mjs <evals.json> <eval-id-or-name> <run_dir> [--write-grading]

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const evalsPath = args[0];
const evalSelector = args[1];
const runDir = args[2];
const writeGrading = args.includes('--write-grading');

if (!evalsPath || !evalSelector || !runDir) {
  console.error('Usage: node eval-assertions.mjs <evals.json> <eval-id-or-name> <run_dir> [--write-grading]');
  process.exit(1);
}

function safeReadJson(pathLike) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return null;
  }
}

function normalizeText(value) {
  return String(value).toLowerCase();
}

function flattenValues(values) {
  const out = [];
  for (const value of values) {
    if (Array.isArray(value)) {
      out.push(...flattenValues(value));
    } else if (value !== undefined) {
      out.push(value);
    }
  }
  return out;
}

function parseSegments(jsonPath) {
  if (!jsonPath.startsWith('$.')) {
    return [];
  }
  return jsonPath
    .slice(2)
    .split('.')
    .filter(Boolean);
}

function stepSegment(currentValues, segment) {
  const match = segment.match(/^([^\[]+)(?:\[(\*|\d+)])?$/);
  if (!match) {
    return [];
  }
  const property = match[1];
  const indexToken = match[2];
  const next = [];

  for (const current of currentValues) {
    if (current === null || current === undefined || typeof current !== 'object') {
      continue;
    }
    const value = current[property];
    if (indexToken === undefined) {
      if (value !== undefined) {
        next.push(value);
      }
      continue;
    }
    if (!Array.isArray(value)) {
      continue;
    }
    if (indexToken === '*') {
      next.push(...value);
      continue;
    }
    const numericIndex = Number(indexToken);
    if (Number.isInteger(numericIndex) && numericIndex >= 0 && numericIndex < value.length) {
      next.push(value[numericIndex]);
    }
  }

  return next;
}

function resolveJsonPath(context, jsonPath) {
  const segments = parseSegments(jsonPath);
  if (segments.length === 0) {
    return [];
  }
  let currentValues = [context];
  for (const segment of segments) {
    currentValues = stepSegment(currentValues, segment);
    if (currentValues.length === 0) {
      break;
    }
  }
  return currentValues;
}

function matchContains(actualValues, expectedValues) {
  const actualStrings = flattenValues(actualValues).map((value) => normalizeText(value));
  const expectedStrings = expectedValues.map((value) => normalizeText(value));
  for (const actual of actualStrings) {
    for (const expected of expectedStrings) {
      if (actual.includes(expected) || expected.includes(actual)) {
        return { passed: true, evidence: `Matched "${expected}" in "${actual}"` };
      }
    }
  }
  return {
    passed: false,
    evidence: `No match found. Actual values: ${JSON.stringify(flattenValues(actualValues))}`
  };
}

function evaluateAssertion(assertion, context) {
  const values = resolveJsonPath(context, assertion.jsonpath);
  const expectedValues = assertion.expected_values || [];
  const flattened = flattenValues(values);
  const type = assertion.expected_type;

  if (type === 'exists') {
    const passed = flattened.length > 0 && flattened.some((value) => value !== null && value !== undefined);
    return {
      passed,
      evidence: passed
        ? `Path ${assertion.jsonpath} exists.`
        : `Path ${assertion.jsonpath} missing or empty.`
    };
  }

  if (type === 'array_length_gte') {
    const threshold = Number(expectedValues[0] ?? 0);
    const candidateLengths = values.map((value) => (Array.isArray(value) ? value.length : 0));
    const maxLength = Math.max(flattened.length, ...candidateLengths, 0);
    const passed = maxLength >= threshold;
    return {
      passed,
      evidence: passed
        ? `Maximum observed length ${maxLength} >= ${threshold}.`
        : `Maximum observed length ${maxLength} < ${threshold}.`
    };
  }

  if (type === 'numeric_gte') {
    const threshold = Number(expectedValues[0] ?? 0);
    const numericValues = flattened.map((value) => Number(value)).filter((value) => !Number.isNaN(value));
    const maxValue = numericValues.length > 0 ? Math.max(...numericValues) : Number.NEGATIVE_INFINITY;
    const passed = maxValue >= threshold;
    return {
      passed,
      evidence: passed
        ? `Observed numeric value ${maxValue} >= ${threshold}.`
        : `Observed numeric values ${JSON.stringify(numericValues)} do not reach ${threshold}.`
    };
  }

  if (type === 'equals') {
    const normalizedExpected = expectedValues.map((value) => normalizeText(value));
    const matched = flattened.find((value) => normalizedExpected.includes(normalizeText(value)));
    const passed = matched !== undefined;
    return {
      passed,
      evidence: passed
        ? `Observed exact match: ${JSON.stringify(matched)}.`
        : `No exact match found. Actual values: ${JSON.stringify(flattened)}`
    };
  }

  if (type === 'contains' || type === 'contains_any') {
    return matchContains(values, expectedValues);
  }

  return {
    passed: false,
    evidence: `Unsupported expected_type: ${type}`
  };
}

function loadContext(dir) {
  const artifactMap = {
    diagnosis: '04_diagnostics/diagnosis.json',
    evidence: '04_diagnostics/evidence.json',
    confidence: '04_diagnostics/confidence.json',
    reasoning_chain: '04_diagnostics/reasoning_chain.json',
    anomaly_report: '02_processed/anomaly_report.json',
    data_analysis_conclusion: '02_processed/data_analysis_conclusion.json',
    scenario_classification: '02_processed/scenario_classification.json',
    feature_summary: '02_processed/feature_summary.json',
    validate_report: '02_processed/validate_report.json',
    causal_evidence_map: '02_processed/causal_evidence_map.json',
    visual_analysis: '03_figures/visual_analysis.json',
    image_captions: '03_figures/image_captions.json',
    ontology: '01_ontology/ontology.json'
  };

  const context = {};
  for (const [key, relativePath] of Object.entries(artifactMap)) {
    const loaded = safeReadJson(join(dir, relativePath));
    if (loaded !== null) {
      context[key] = loaded;
    }
  }
  return context;
}

function buildGrading(results) {
  const passed = results.filter((result) => result.passed).length;
  const failed = results.length - passed;
  return {
    expectations: results.map((result) => ({
      text: result.description,
      passed: result.passed,
      evidence: result.evidence
    })),
    summary: {
      passed,
      failed,
      total: results.length,
      pass_rate: results.length > 0 ? Number((passed / results.length).toFixed(4)) : 0
    }
  };
}

const evalSuite = safeReadJson(evalsPath);
if (!evalSuite || !Array.isArray(evalSuite.evals)) {
  console.error(`Could not read eval suite from ${evalsPath}`);
  process.exit(1);
}

const selectedEval = evalSuite.evals.find((entry) => {
  return String(entry.id) === evalSelector || entry.name === evalSelector;
});

if (!selectedEval) {
  console.error(`Eval ${evalSelector} not found in ${evalsPath}`);
  process.exit(1);
}

const context = loadContext(runDir);
const assertions = selectedEval.assertions || [];
const results = assertions.map((assertion) => {
  const evaluation = evaluateAssertion(assertion, context);
  return {
    name: assertion.name,
    description: assertion.description || assertion.name,
    passed: evaluation.passed,
    evidence: evaluation.evidence,
    expected_type: assertion.expected_type,
    jsonpath: assertion.jsonpath,
    weight: assertion.weight || 'medium'
  };
});

const grading = buildGrading(results);
const report = {
  eval_id: selectedEval.id,
  eval_name: selectedEval.name,
  run_dir: runDir,
  assertion_results: results,
  grading
};

if (writeGrading) {
  fs.writeFileSync(join(runDir, 'grading.json'), JSON.stringify(grading, null, 2) + '\n');
}

console.log(JSON.stringify(report, null, 2));
process.exit(results.every((result) => result.passed) ? 0 : 1);
