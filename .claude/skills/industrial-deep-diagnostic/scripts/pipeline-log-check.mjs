#!/usr/bin/env node
// pipeline-log-check.mjs — Validate that the pipeline event log proves the run
// actually executed in a disciplined order rather than only producing files.
//
// Usage: node pipeline-log-check.mjs <run_dir>

import fs from 'fs';
import { join } from 'path';

const args = process.argv.slice(2);
const runDir = args[0];

if (!runDir) {
  console.error('Usage: node pipeline-log-check.mjs <run_dir>');
  process.exit(1);
}

const logPath = join(runDir, '.pipeline_events.jsonl');
const knownAgents = [
  'context-builder',
  'data-processor',
  'diagnostician',
  'judge',
  'reporter',
  'report-reviewer'
];

const orderedSteps = [
  'setup',
  'inspect',
  'context_builder',
  'clarification_gate',
  'data_processor',
  'diagnostician',
  'judge',
  'reporter',
  'audit',
  'present'
];

const agentToStep = {
  'context-builder': 'context_builder',
  'data-processor': 'data_processor',
  diagnostician: 'diagnostician',
  judge: 'judge',
  reporter: 'reporter',
  'report-reviewer': 'audit'
};

const agentArtifactHints = {
  'context-builder': ['01_ontology/ontology.json', '00_input/extracted_knowledge.json'],
  'data-processor': ['02_processed/feature_summary.json', '03_figures/plot_manifest.json'],
  diagnostician: ['04_diagnostics/diagnosis.json'],
  judge: ['05_review/judge_feedback.json'],
  reporter: ['report.md', 'run_summary.json'],
  'report-reviewer': ['optimizer.md']
};

function exists(pathLike) {
  return fs.existsSync(join(runDir, pathLike));
}

function readJson(pathLike, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(pathLike, 'utf8'));
  } catch (_) {
    return fallback;
  }
}

function requiredAgentsForObservedArtifacts() {
  return knownAgents.filter((agent) => {
    const hints = agentArtifactHints[agent] || [];
    return hints.some((hint) => exists(hint));
  });
}

function buildMissingLogReport(requiredAgents, critical = true) {
  return {
    log_path: logPath,
    validation: 'FAIL',
    summary: {
      required_agents: requiredAgents,
      missing_log: true,
      malformed_lines: 0,
      repair_spawn_count: 0
    },
    issues: [
      {
        severity: critical ? 'critical' : 'warning',
        code: 'PIPELINE_LOG_MISSING',
        message: '.pipeline_events.jsonl is missing, so step-by-step execution cannot be proven.'
      }
    ]
  };
}

if (!fs.existsSync(logPath)) {
  console.log(JSON.stringify(buildMissingLogReport(requiredAgentsForObservedArtifacts()), null, 2));
  process.exit(1);
}

const raw = fs.readFileSync(logPath, 'utf8');
const lines = raw.split('\n').filter((line) => line.trim().length > 0);
const events = [];
const issues = [];
const manifest = readJson(join(runDir, 'run_manifest.json'), {});

for (let index = 0; index < lines.length; index += 1) {
  const line = lines[index];
  try {
    const parsed = JSON.parse(line);
    parsed.__line = index + 1;
    events.push(parsed);
  } catch (error) {
    issues.push({
      severity: 'critical',
      code: 'PIPELINE_LOG_INVALID_JSON',
      line: index + 1,
      message: `Invalid JSONL line: ${error.message}`
    });
  }
}

const requiredAgents = requiredAgentsForObservedArtifacts();
const agentState = new Map();

for (const agent of knownAgents) {
  agentState.set(agent, {
    starts: [],
    completes: []
  });
}

let repairSpawnCount = 0;
let repairCapReachedCount = 0;
let runInitializedSeen = false;
let artifactFinalizeSeen = false;
let artifactCheckSeen = false;

for (const event of events) {
  if (event.event === 'run_initialized') {
    runInitializedSeen = true;
  }
  if (event.event === 'repair_spawn') {
    repairSpawnCount += 1;
  }
  if (event.event === 'repair_cap_reached') {
    repairCapReachedCount += 1;
  }
  if (event.event === 'artifact_finalize_complete') {
    artifactFinalizeSeen = true;
  }
  if (event.event === 'artifact_check_complete') {
    artifactCheckSeen = true;
  }
  if ((event.event === 'agent_start' || event.event === 'agent_complete') && knownAgents.includes(event.agent)) {
    const bucket = agentState.get(event.agent);
    if (event.event === 'agent_start') {
      bucket.starts.push(event);
    } else {
      bucket.completes.push(event);
    }
  }
}

if (!runInitializedSeen) {
  issues.push({
    severity: 'critical',
    code: 'RUN_INITIALIZED_MISSING',
    message: 'run_initialized event missing; run bootstrap is not proven.'
  });
}

for (const agent of requiredAgents) {
  const bucket = agentState.get(agent);
  if (bucket.starts.length === 0) {
    issues.push({
      severity: 'critical',
      code: 'AGENT_START_MISSING',
      agent,
      message: `Required agent "${agent}" has output artifacts but no agent_start event.`
    });
  }
  if (bucket.completes.length === 0) {
    issues.push({
      severity: 'critical',
      code: 'AGENT_COMPLETE_MISSING',
      agent,
      message: `Required agent "${agent}" has output artifacts but no agent_complete event.`
    });
  }
  if (bucket.starts.length > 0 && bucket.completes.length > 0) {
    const firstStartLine = bucket.starts[0].__line;
    const lastCompleteLine = bucket.completes[bucket.completes.length - 1].__line;
    if (firstStartLine > lastCompleteLine) {
      issues.push({
        severity: 'critical',
        code: 'AGENT_EVENT_ORDER_INVALID',
        agent,
        message: `Agent "${agent}" completes before its start event in the log.`
      });
    }
    const firstStart = bucket.starts[0];
    const lastComplete = bucket.completes[bucket.completes.length - 1];
    const filesWritten = Array.isArray(lastComplete.files_written) ? lastComplete.files_written : [];
    const missingOutputs = filesWritten.filter((filePath) => !exists(filePath));
    if (missingOutputs.length > 0) {
      issues.push({
        severity: 'critical',
        code: 'AGENT_DECLARED_OUTPUT_MISSING',
        agent,
        message: `Agent "${agent}" declared missing output files.`,
        missing_outputs: missingOutputs
      });
    }
    const stepName = agentToStep[agent];
    if (stepName) {
      const previousSteps = orderedSteps.slice(0, orderedSteps.indexOf(stepName));
      const previousAgentSteps = previousSteps.filter((step) => Object.values(agentToStep).includes(step));
      const missingPrereqs = previousAgentSteps.filter((step) => {
        const prereqAgent = Object.keys(agentToStep).find((key) => agentToStep[key] === step);
        return prereqAgent && agentState.get(prereqAgent)?.completes?.length === 0;
      });
      if (missingPrereqs.length > 0) {
        issues.push({
          severity: 'critical',
          code: 'AGENT_STARTED_BEFORE_PREREQUISITE',
          agent,
          message: `Agent "${agent}" started before prerequisite steps were completed.`,
          missing_prerequisites: missingPrereqs
        });
      }
    }
  }
}

if (repairSpawnCount > 5) {
  issues.push({
    severity: 'critical',
    code: 'REPAIR_CAP_EXCEEDED',
    message: `repair_spawn count is ${repairSpawnCount}, exceeding the global cap of 5.`
  });
}

if (repairCapReachedCount > 0 && repairSpawnCount < 5) {
  issues.push({
    severity: 'warning',
    code: 'REPAIR_CAP_LOG_INCONSISTENT',
    message: 'repair_cap_reached was logged before five repair spawns were recorded.'
  });
}

if ((exists('report.md') || exists('run_summary.json')) && !artifactFinalizeSeen) {
  issues.push({
    severity: 'warning',
    code: 'FINALIZE_EVENT_MISSING',
    message: 'Final artifacts exist but artifact_finalize_complete was not logged.'
  });
}

if (exists('run_summary.json') && !artifactCheckSeen) {
  issues.push({
    severity: 'warning',
    code: 'ARTIFACT_CHECK_EVENT_MISSING',
    message: 'run_summary.json exists but artifact_check_complete was not logged.'
  });
}

if (manifest?.pipeline?.diag_iters_total != null && manifest.pipeline.diag_iters_total !== repairSpawnCount) {
  issues.push({
    severity: 'warning',
    code: 'MANIFEST_REPAIR_COUNT_MISMATCH',
    message: 'run_manifest.json diag_iters_total does not match repair_spawn count in log.',
    detail: {
      manifest_diag_iters_total: manifest.pipeline.diag_iters_total,
      repair_spawn_count: repairSpawnCount
    }
  });
}

if (Array.isArray(manifest?.steps)) {
  for (const step of manifest.steps) {
    if (step.owner === 'main-agent') continue;
    const mappedAgent = Object.keys(agentToStep).find((agent) => agentToStep[agent] === step.step);
    if (!mappedAgent) continue;
    const bucket = agentState.get(mappedAgent);
    if (step.status === 'completed' && (!bucket || bucket.completes.length === 0)) {
      issues.push({
        severity: 'warning',
        code: 'MANIFEST_LOG_COMPLETION_MISMATCH',
        step: step.step,
        message: `run_manifest marks ${step.step} completed but log lacks agent_complete.`
      });
    }
  }
}

for (let index = 1; index < events.length; index += 1) {
  const previous = events[index - 1];
  const current = events[index];
  if (previous.timestamp && current.timestamp && previous.timestamp > current.timestamp) {
    issues.push({
      severity: 'warning',
      code: 'TIMESTAMP_NON_MONOTONIC',
      line: current.__line,
      message: 'Timestamps are not monotonic; investigate whether events were appended out of order.'
    });
    break;
  }
}

const validation = issues.some((issue) => issue.severity === 'critical') ? 'FAIL' : 'PASS';

const report = {
  log_path: logPath,
  validation,
  summary: {
    required_agents: requiredAgents,
    total_lines: lines.length,
    parsed_events: events.length,
    malformed_lines: lines.length - events.length,
    repair_spawn_count: repairSpawnCount,
    repair_cap_reached_count: repairCapReachedCount
  },
  agent_counts: Object.fromEntries(
    knownAgents.map((agent) => {
      const bucket = agentState.get(agent);
      return [agent, { starts: bucket.starts.length, completes: bucket.completes.length }];
    })
  ),
  issues
};

console.log(JSON.stringify(report, null, 2));
process.exit(validation === 'PASS' ? 0 : 1);
