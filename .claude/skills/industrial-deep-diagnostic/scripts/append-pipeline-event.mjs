#!/usr/bin/env node
// append-pipeline-event.mjs — Append structured pipeline events and keep
// run_manifest.json in sync with execution state.
//
// Usage examples:
//   node append-pipeline-event.mjs <run_dir> --event agent_start --agent data-processor
//   node append-pipeline-event.mjs <run_dir> --event agent_complete --agent reporter --files report.md,run_summary.json
//   node append-pipeline-event.mjs <run_dir> --event repair_spawn --agent main-agent --step diagnostician --data '{"source":"judge","diag_iters_total":1}'

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];

const VALID_EVENTS = new Set([
  'run_initialized',
  'step_start',
  'step_complete',
  'agent_start',
  'agent_complete',
  'dependency_wait',
  'dependency_ready',
  'clarification_auto_inferred',
  'clarification_user_confirmed',
  'repair_spawn',
  'repair_cap_reached',
  'artifact_finalize_start',
  'artifact_finalize_complete',
  'artifact_check_complete',
  'run_completed',
  'run_failed'
]);

const AGENT_TO_STEP = {
  'context-builder': 'context_builder',
  'data-processor': 'data_processor',
  diagnostician: 'diagnostician',
  judge: 'judge',
  reporter: 'reporter',
  'report-reviewer': 'audit',
  'main-agent': null
};

const STEP_PREREQUISITES = {
  inspect: ['setup'],
  context_builder: ['inspect'],
  clarification_gate: ['context_builder'],
  data_processor: ['inspect'],
  diagnostician: ['data_processor'],
  judge: ['diagnostician'],
  reporter: ['judge'],
  audit: ['reporter'],
  present: ['audit']
};

function flag(name) {
  const index = args.indexOf(name);
  return index === -1 ? undefined : args[index + 1];
}

function readJson(pathLike, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function writeJson(pathLike, data) {
  fs.writeFileSync(pathLike, `${JSON.stringify(data, null, 2)}\n`);
}

function ensureArray(value) {
  if (Array.isArray(value)) return value;
  if (value == null) return [];
  return [value];
}

function parseJsonFlag(name, fallback = {}) {
  const raw = flag(name);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error(`Invalid JSON for ${name}: ${error.message}`);
    process.exit(1);
  }
}

function parseFiles(value) {
  if (!value) return [];
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function upsertNote(stepRecord, note) {
  stepRecord.notes = ensureArray(stepRecord.notes);
  if (!stepRecord.notes.includes(note)) {
    stepRecord.notes.push(note);
  }
}

function getStepRecord(manifest, step) {
  const steps = ensureArray(manifest.steps);
  return steps.find((item) => item.step === step) || null;
}

function stepStatus(manifest, step) {
  const record = getStepRecord(manifest, step);
  return record?.status || 'missing';
}

function isPreReportAudit(step, agent, extraData) {
  if (step !== 'audit' || agent !== 'report-reviewer') return false;
  return extraData.audit_mode === 'pre_report' || extraData.PRE_REPORT_AUDIT === true;
}

function prerequisitesFor(step, agent, extraData) {
  if (isPreReportAudit(step, agent, extraData)) {
    return ['diagnostician'];
  }
  return STEP_PREREQUISITES[step] || [];
}

function enforceStepPrerequisites(manifest, step, eventName, agent, extraData) {
  if (!step || !['step_start', 'agent_start'].includes(eventName)) return;
  const prerequisites = prerequisitesFor(step, agent, extraData);
  const incomplete = prerequisites.filter((requiredStep) => stepStatus(manifest, requiredStep) !== 'completed');
  if (incomplete.length > 0) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: 'PIPELINE_ORDER_VIOLATION',
          step,
          agent,
          missing_prerequisites: incomplete
        },
        null,
        2
      )
    );
    process.exit(1);
  }
}

if (!runDir) {
  console.error('Usage: node append-pipeline-event.mjs <run_dir> --event <event> [--agent <agent>] [--step <pipeline_step>] [--files a,b] [--data <json>] [--errors <text>]');
  process.exit(1);
}

const eventName = flag('--event');
if (!eventName || !VALID_EVENTS.has(eventName)) {
  console.error(`Missing or invalid --event. Supported events: ${Array.from(VALID_EVENTS).join(', ')}`);
  process.exit(1);
}

const manifestPath = join(runDir, 'run_manifest.json');
const manifest = readJson(manifestPath, null);
if (!manifest) {
  console.error(`Missing or unreadable run_manifest.json at ${manifestPath}`);
  process.exit(1);
}
manifest.steps = ensureArray(manifest.steps);
manifest.pipeline = manifest.pipeline || {
  version: 'v6.5',
  current_step: null,
  current_owner: null,
  diag_iters_total: 0,
  repair_spawn_count: 0,
  artifact_finalize_runs: 0,
  integrity: {}
};
manifest.pipeline.integrity = manifest.pipeline.integrity || {};

const logPath = join(runDir, '.pipeline_events.jsonl');
const agent = flag('--agent') || 'main-agent';
const explicitStep = flag('--step');
const inferredStep = explicitStep || AGENT_TO_STEP[agent] || null;
const filesWritten = parseFiles(flag('--files'));
const extraData = parseJsonFlag('--data', {});
const errors = flag('--errors');
const status = flag('--status');
const allowMissingFiles = args.includes('--allow-missing-files');
const event = {
  event: eventName,
  agent,
  timestamp: new Date().toISOString(),
  ...extraData
};

if (inferredStep) {
  event.step = inferredStep;
}
if (filesWritten.length > 0) {
  event.files_written = filesWritten;
}
if (errors !== undefined) {
  event.errors = errors;
}
if (status) {
  event.status = status;
}

enforceStepPrerequisites(manifest, inferredStep, eventName, agent, extraData);

if (filesWritten.length > 0 && ['agent_complete', 'step_complete', 'artifact_finalize_complete'].includes(eventName) && !allowMissingFiles) {
  const missingFiles = filesWritten.filter((filePath) => !fs.existsSync(join(runDir, filePath)));
  if (missingFiles.length > 0) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: 'PIPELINE_OUTPUT_MISSING',
          step: inferredStep,
          missing_files: missingFiles
        },
        null,
        2
      )
    );
    process.exit(1);
  }
}

const shouldUpdateStepRecord = !isPreReportAudit(inferredStep, agent, extraData);
const stepRecord = inferredStep && shouldUpdateStepRecord ? getStepRecord(manifest, inferredStep) : null;

if (stepRecord) {
  if (eventName === 'dependency_wait') {
    upsertNote(stepRecord, `dependency_wait:${extraData.waiting_for || 'unknown'}`);
  }

  if (eventName === 'dependency_ready') {
    upsertNote(stepRecord, `dependency_ready:${extraData.dependency || extraData.waiting_for || 'unknown'}`);
  }

  if (['step_start', 'agent_start'].includes(eventName)) {
    stepRecord.status = 'in_progress';
    stepRecord.started_at = stepRecord.started_at || event.timestamp;
    stepRecord.attempts = (stepRecord.attempts || 0) + 1;
    stepRecord.last_event = eventName;
    manifest.pipeline.current_step = inferredStep;
    manifest.pipeline.current_owner = agent;
  }

  if (['step_complete', 'agent_complete'].includes(eventName)) {
    stepRecord.status = errors ? 'completed_with_errors' : 'completed';
    stepRecord.completed_at = event.timestamp;
    stepRecord.last_event = eventName;
    stepRecord.outputs = Array.from(new Set([...(stepRecord.outputs || []), ...filesWritten]));
    if (errors) {
      upsertNote(stepRecord, `errors:${errors}`);
    }
  }
}

if (eventName === 'repair_spawn') {
  manifest.pipeline.diag_iters_total = (manifest.pipeline.diag_iters_total || 0) + 1;
  manifest.pipeline.repair_spawn_count = (manifest.pipeline.repair_spawn_count || 0) + 1;
}

if (eventName === 'repair_cap_reached') {
  manifest.pipeline.integrity.repair_cap_reached = true;
}

if (eventName === 'artifact_finalize_start') {
  manifest.pipeline.artifact_finalize_runs = (manifest.pipeline.artifact_finalize_runs || 0) + 1;
}

if (eventName === 'artifact_finalize_complete') {
  manifest.pipeline.current_step = 'present';
  manifest.pipeline.current_owner = 'main-agent';
}

if (eventName === 'artifact_check_complete') {
  manifest.pipeline.integrity.last_artifact_check = status || extraData.integrity_check || 'unknown';
}

if (eventName === 'run_completed') {
  manifest.status = 'completed';
  const presentStep = getStepRecord(manifest, 'present');
  if (presentStep) {
    presentStep.status = 'completed';
    presentStep.completed_at = event.timestamp;
    presentStep.last_event = eventName;
  }
}

if (eventName === 'run_failed') {
  manifest.status = 'failed';
}

if (eventName.startsWith('clarification_')) {
  const clarificationStep = getStepRecord(manifest, 'clarification_gate');
  if (clarificationStep) {
    clarificationStep.status = 'completed';
    clarificationStep.completed_at = event.timestamp;
    clarificationStep.last_event = eventName;
    clarificationStep.attempts = Math.max(clarificationStep.attempts || 0, 1);
  }
}

manifest.updated_at = event.timestamp;
fs.appendFileSync(logPath, `${JSON.stringify(event)}\n`);
writeJson(manifestPath, manifest);

console.log(JSON.stringify({ ok: true, log_path: logPath, manifest_path: manifestPath, event }, null, 2));
