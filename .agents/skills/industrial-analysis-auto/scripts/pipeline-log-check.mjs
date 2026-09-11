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
  'vlm-visual-analyzer',
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
  'vlm-visual-analyzer': 'data_processor',
  diagnostician: 'diagnostician',
  judge: 'judge',
  reporter: 'reporter',
  'report-reviewer': 'audit'
};

const agentArtifactHints = {
  'context-builder': ['01_ontology/ontology.json', '00_input/extracted_knowledge.json'],
  'data-processor': ['02_processed/feature_summary.json', '03_figures/plot_manifest.json'],
  'vlm-visual-analyzer': ['03_figures/visual_analysis.json', '03_figures/image_captions.json'],
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

function nonEmptyArray(value) {
  return Array.isArray(value) && value.length > 0;
}

function requiredAgentsForObservedArtifacts() {
  const required = new Set(knownAgents.filter((agent) => {
    const hints = agentArtifactHints[agent] || [];
    return hints.some((hint) => exists(hint));
  }));

  if (exists('report.md') || exists('run_summary.json')) {
    required.add('judge');
    required.add('reporter');
  }
  if (exists('optimizer.md')) {
    required.add('judge');
    required.add('reporter');
    required.add('report-reviewer');
  }

  // metadata_backed_inference mode = VLM intentionally not dispatched; its
  // agent events cannot be expected when it never ran.
  if (exists('03_figures/visual_analysis.json')) {
    try {
      const va = readJson(join(runDir, '03_figures', 'visual_analysis.json'), null) || {};
      const stage = (va.analysis_provenance || {}).stage || '';
      if (va.observation_mode === 'metadata_backed_inference' || stage === 'metadata_backed_inference') {
        required.delete('vlm-visual-analyzer');
      }
    } catch (e) { /* unreadable VA handled elsewhere */ }
  }

  return Array.from(required);
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
let runCompletedSeen = false;

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
  if (event.event === 'run_completed') {
    runCompletedSeen = true;
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

function isPreReportAuditEvent(event) {
  return event?.agent === 'report-reviewer' && event?.step === 'audit' &&
    (event?.audit_mode === 'pre_report' || event?.PRE_REPORT_AUDIT === true);
}

function requiredPreviousStepsForAgent(agent, startEvent) {
  if (agent === 'data-processor') {
    return ['inspect'];
  }
  if (agent === 'report-reviewer' && isPreReportAuditEvent(startEvent)) {
    return ['diagnostician'];
  }
  const stepName = agentToStep[agent];
  if (!stepName) return [];
  return orderedSteps
    .slice(0, orderedSteps.indexOf(stepName))
    .filter((step) => Object.values(agentToStep).includes(step));
}

if (!runInitializedSeen) {
  issues.push({
    severity: 'critical',
    code: 'RUN_INITIALIZED_MISSING',
    message: 'run_initialized event missing; run bootstrap is not proven.'
  });
}

const visualAnalysis = readJson(join(runDir, '03_figures', 'visual_analysis.json'), null);

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
      const previousAgentSteps = requiredPreviousStepsForAgent(agent, firstStart);
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
      if (agent === 'vlm-visual-analyzer') {
        const dpStartLine = agentState.get('data-processor')?.starts?.[0]?.__line || null;
        const vlmStartLine = bucket.starts[0]?.__line || null;
        if (dpStartLine && vlmStartLine && vlmStartLine < dpStartLine) {
          issues.push({
            severity: 'critical',
            code: 'VLM_STARTED_BEFORE_DATA_PROCESSOR',
            agent,
            message: 'vlm-visual-analyzer started before data-processor had started.'
          });
        }
      }
    }
  }
}

if (exists('03_figures/visual_analysis.json')) {
  if (!visualAnalysis || typeof visualAnalysis !== 'object') {
    issues.push({
      severity: 'critical',
      code: 'VISUAL_ANALYSIS_UNREADABLE',
      message: 'visual_analysis.json exists but is unreadable or not valid JSON.'
    });
  } else {
    if (visualAnalysis.observation_mode === 'skeleton_pre_vlm') {
      issues.push({
        severity: 'critical',
        code: 'VLM_SKELETON_NOT_OVERWRITTEN',
        message: 'visual_analysis.json is still in skeleton_pre_vlm mode; vlm-visual-analyzer did not complete final enrichment.'
      });
    }

    const provenance = visualAnalysis.analysis_provenance || {};
    // metadata_backed_inference is the explicit NON-VLM mode (VLM intentionally
    // not dispatched — no images yet). It must still prove data-processor
    // authored it; the full VLM chain requirements do not apply.
    const metadataBacked = visualAnalysis.observation_mode === 'metadata_backed_inference'
      || provenance.stage === 'metadata_backed_inference';
    if (metadataBacked) {
      if (!String(provenance.source_agent || '').startsWith('data-processor')) {
        issues.push({
          severity: 'critical',
          code: 'METADATA_BACKED_SOURCE_MISSING',
          message: 'metadata_backed visual_analysis.json must identify data-processor as the source agent.'
        });
      }
      // skip VLM-specific gates in this explicit mode
    } else {
      if (provenance.source_agent !== 'vlm-visual-analyzer') {
        issues.push({
          severity: 'critical',
          code: 'VLM_SOURCE_AGENT_MISSING',
          message: 'visual_analysis.json does not identify vlm-visual-analyzer as the source agent.'
        });
      }
    if (provenance.stage !== 'final_vlm_output') {
      issues.push({
        severity: 'critical',
        code: 'VLM_STAGE_INVALID',
        message: 'visual_analysis.json analysis_provenance.stage must be final_vlm_output.'
      });
    }
    if (provenance.skeleton_overwritten !== true) {
      issues.push({
        severity: 'critical',
        code: 'VLM_SKELETON_OVERWRITE_NOT_PROVEN',
        message: 'visual_analysis.json does not prove that the pre-VLM skeleton was overwritten.'
      });
    }
    if (!nonEmptyArray(provenance.context_files_read)) {
      issues.push({
        severity: 'critical',
        code: 'VLM_CONTEXT_LOAD_NOT_PROVEN',
        message: 'visual_analysis.json is missing analysis_provenance.context_files_read.'
      });
    }
    if (!nonEmptyArray(provenance.figure_inputs_attempted)) {
      issues.push({
        severity: 'critical',
        code: 'VLM_IMAGE_INPUT_NOT_PROVEN',
        message: 'visual_analysis.json is missing analysis_provenance.figure_inputs_attempted, so no figure-reading attempt is proven.'
      });
    }
    }
    if (visualAnalysis.observation_mode === 'direct_image_reading' && !nonEmptyArray(provenance.figure_inputs_read_successfully)) {
      issues.push({
        severity: 'critical',
        code: 'VLM_DIRECT_READ_NOT_PROVEN',
        message: 'observation_mode is direct_image_reading but no successfully read figures were recorded.'
      });
    }

    const allObservations = (visualAnalysis.visual_observations || []).flatMap((item) => item?.observations || []);
    const groundedObservations = allObservations.filter((item) => {
      const meanings = item?.ontology_context?.parameter_physical_meanings;
      const stage = item?.ontology_context?.process_stage;
      return (meanings && Object.keys(meanings).length > 0) || stage;
    });
    if (groundedObservations.length < 2) {
      issues.push({
        severity: 'critical',
        code: 'VLM_ONTOLOGY_GROUNDING_WEAK',
        message: 'Fewer than two visual observations contain ontology grounding context.'
      });
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

if (exists('run_summary.json') && !runCompletedSeen) {
  issues.push({
    severity: 'warning',
    code: 'RUN_COMPLETED_EVENT_MISSING',
    message: 'run_summary.json exists but run_completed was not logged.'
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
