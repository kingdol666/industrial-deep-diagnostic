#!/usr/bin/env node
// setup.mjs — Create run directory structure for a diagnostic session
// Usage: node setup.mjs --name <run_name> [--base-dir ./workspace/diagnostic-runs]

import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const nameIdx = args.indexOf('--name');
const baseIdx = args.indexOf('--base-dir');

const name = nameIdx !== -1 ? args[nameIdx + 1] : `run_${Date.now()}`;
const baseDir = baseIdx !== -1 ? args[baseIdx + 1] : './workspace/diagnostic-runs';

const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 15);
const runDir = path.join(baseDir, `${timestamp}_${name}`);

const subdirs = [
  '00_input',
  '01_ontology',
  '02_processed',
  '03_figures',
  '04_diagnostics',
  '05_review',
  '06_scripts',
];

const pipelineSteps = [
  { step: 'setup', owner: 'main-agent' },
  { step: 'inspect', owner: 'main-agent' },
  { step: 'context_builder', owner: 'context-builder' },
  { step: 'clarification_gate', owner: 'main-agent' },
  { step: 'data_processor', owner: 'data-processor' },
  { step: 'diagnostician', owner: 'diagnostician' },
  { step: 'judge', owner: 'judge' },
  { step: 'reporter', owner: 'reporter' },
  { step: 'audit', owner: 'report-reviewer' },
  { step: 'present', owner: 'main-agent' },
];

fs.mkdirSync(runDir, { recursive: true });
for (const sub of subdirs) {
  fs.mkdirSync(path.join(runDir, sub), { recursive: true });
}

const defaultRunConfig = {
  data_path: '',
  interaction_mode: 'auto',
  process_description: '',
  user_objective: '',
  analysis_constraints: {
    max_web_research_queries: 5,
    judge_score_threshold: 90,
    max_judge_iterations: 3,
    max_reviewer_iterations: 2,
    global_max_iterations: 5
  }
};

const manifest = {
  run_id: `${timestamp}_${name}`,
  created: new Date().toISOString(),
  run_dir: path.resolve(runDir),
  status: 'initialized',
  steps: pipelineSteps.map((item, index) => ({
    index,
    step: item.step,
    owner: item.owner,
    status: item.step === 'setup' ? 'completed' : 'pending',
    attempts: item.step === 'setup' ? 1 : 0,
    started_at: item.step === 'setup' ? new Date().toISOString() : null,
    completed_at: item.step === 'setup' ? new Date().toISOString() : null,
    last_event: item.step === 'setup' ? 'run_initialized' : null,
    outputs: [],
    notes: []
  })),
  delivery_contract: {
    strict_pipeline_required: true,
    evidence_closure_required: true,
    required_runtime_artifacts: [
      '00_input/run_config.json',
      '00_input/input_manifest.json',
      '01_ontology/ontology.json',
      '02_processed/scenario_classification.json',
      '02_processed/anomaly_report.json',
      '02_processed/data_analysis_conclusion.json',
      '03_figures/plot_manifest.json',
      '03_figures/visual_analysis.json',
      '03_figures/image_captions.json',
      '04_diagnostics/diagnosis.json',
      '04_diagnostics/evidence.json',
      '04_diagnostics/confidence.json',
      '04_diagnostics/reasoning_chain.json',
      '05_review/judge_feedback.json',
      'report.md',
      'run_summary.json',
      'optimizer.md',
      'evidence_closure_report.json'
    ]
  },
  pipeline: {
    version: 'v6.5',
    current_step: 'inspect',
    current_owner: 'main-agent',
    diag_iters_total: 0,
    repair_spawn_count: 0,
    artifact_finalize_runs: 0,
    integrity: {
      event_log_bootstrapped: true,
      evidence_closure_last_status: 'not_checked'
    }
  },
};

fs.writeFileSync(path.join(runDir, 'run_manifest.json'), JSON.stringify(manifest, null, 2));
fs.writeFileSync(path.join(runDir, '00_input', 'run_config.json'), JSON.stringify(defaultRunConfig, null, 2));
const logPath = path.join(runDir, '.pipeline_events.jsonl');
const initEvent = {
  event: 'run_initialized',
  step: 'setup',
  agent: 'main-agent',
  timestamp: new Date().toISOString(),
  run_id: manifest.run_id,
  run_dir: manifest.run_dir,
  files_written: ['run_manifest.json', '00_input/run_config.json'],
  status: 'completed'
};
fs.writeFileSync(logPath, `${JSON.stringify(initEvent)}\n`);

// Output the run directory path for the caller
console.log(JSON.stringify({ run_dir: path.resolve(runDir), manifest }));
