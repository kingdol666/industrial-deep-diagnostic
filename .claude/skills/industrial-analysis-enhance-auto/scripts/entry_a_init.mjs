#!/usr/bin/env node
// entry_a_init.mjs — Entry-A initialization for the enhancement pipeline.
// Given a raw data file, performs the DETERMINISTIC part of the auto baseline:
//   setup.mjs → inspect.mjs → write input_manifest/user_context/run_config
// Then checks which baseline artifacts are missing and reports exactly what the
// orchestrator agent must still run (the LLM baseline steps).
//
// Usage:
//   node entry_a_init.mjs --data-path <data> --name <run_name>
//                          [--base-dir workspace/diagnostic-runs]
//                          [--process-description <text>] [--objective <text>]
// Output: JSON with { run_dir, input_mode: "A_new_data", initialized: true,
//                     missing_baseline: [...], next_steps: [...] }

import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const args = process.argv.slice(2);
function flag(name) {
  const i = args.indexOf(name);
  return i === -1 ? undefined : args[i + 1];
}

const dataPath = flag('--data-path');
const name = flag('--name');
const baseDir = flag('--base-dir') || 'workspace/diagnostic-runs';
const processDesc = flag('--process-description') || '';
const objective = flag('--objective') || '';

if (!dataPath || !name) {
  console.error('Usage: node entry_a_init.mjs --data-path <data> --name <run_name> [--base-dir <dir>]');
  process.exit(1);
}

const projectRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..');
const autoSkill = path.join(projectRoot, '.claude', 'skills', 'industrial-analysis-auto');
const sharedPath = path.join(projectRoot, '.claude', 'shared');
const dataAbs = path.resolve(projectRoot, dataPath);
if (!fs.existsSync(dataAbs)) {
  console.error(`ERROR: data file not found: ${dataAbs}`);
  process.exit(1);
}

function runScript(script, scriptArgs) {
  const out = execFileSync(process.execPath, [script, ...scriptArgs], {
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  });
  return out.trim();
}

// Step 1: setup run dir
let runDir = null;
try {
  const setupOut = runScript(path.join(autoSkill, 'scripts', 'setup.mjs'), ['--name', name, '--base-dir', baseDir]);
  const parsed = JSON.parse(setupOut);
  runDir = parsed.run_dir;
} catch (e) {
  console.error('ERROR: setup.mjs failed:', e.message);
  process.exit(1);
}

// Step 1.5: adaptive preprocessing — any file/directory/mixed-format input is
// normalized to 00_input/preprocessed_data.csv (+ report + context/).
// This is what makes the pipeline data-source agnostic: raw data may be a
// directory, CSV/TSV/delimited text (any encoding), xlsx/xlsm multi-sheet
// workbooks, JSON records, markdown/HTML tables, or free-text notes.
let inspectedPath = dataAbs;
let prepReport = null;
const prepScript = path.join(projectRoot, '.claude', 'skills', 'industrial-data-preprocessor', 'scripts', 'data_preprocessor.py');
// Resolve the uv execution environment via uv_env_setup.mjs (uv-first engine).
// Returns { uvCmd, python } — when uv is available, scripts run via `uv run --project`.
function resolvePythonEnv() {
  const sharedPath = path.join(projectRoot, '.claude', 'shared', 'scripts');
  try {
    const out = execFileSync(process.execPath, [
      path.join(sharedPath, 'uv_env_setup.mjs'),
    ], { encoding: 'utf-8', timeout: 60000 });
    const parsed = JSON.parse(out.trim());
    if (parsed.uv_cmd && parsed.uv_cmd.length) {
      return { uvCmd: parsed.uv_cmd, python: parsed.python };
    }
    if (parsed.python) return { uvCmd: null, python: parsed.python };
  } catch (_) { /* fall through */ }
  return { uvCmd: null, python: 'python' };
}
const PY_ENV = resolvePythonEnv();
const UV_CMD = PY_ENV.uvCmd ? PY_ENV.uvCmd[0] : PY_ENV.python;

/** Build argv for a Python script: uv run prefix when available, else venv python. */
function pythonArgs(scriptArgs) {
  if (PY_ENV.uvCmd) return [...PY_ENV.uvCmd.slice(1), 'python', ...scriptArgs];
  return scriptArgs;
}

try {
  const prepOut = execFileSync(UV_CMD, pythonArgs(['-W', 'ignore', prepScript, '--data-path', dataAbs, '--output', path.join(runDir, '00_input'), '--name', name]), {
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  });
  const prepJson = JSON.parse(prepOut.trim());
  prepReport = prepJson;
  const preprocessed = path.join(runDir, '00_input', 'preprocessed_data.csv');
  if (prepJson.status === 'ok' && fs.existsSync(preprocessed)) {
    inspectedPath = preprocessed;
  } else if (prepJson.status === 'no_tabular_data') {
    console.error('ERROR: preprocessing found no tabular data in input. Report:');
    console.error(fs.readFileSync(path.join(runDir, '00_input', 'preprocessing_report.json'), 'utf8'));
    process.exit(1);
  }
} catch (e) {
  console.error('ERROR: data preprocessing failed:', e.message);
  process.exit(1);
}

// Step 2: inspect data → write input_manifest / user_context / run_config
try {
  const inspectOut = runScript(path.join(autoSkill, 'scripts', 'inspect.mjs'), [inspectedPath]);
  const insp = JSON.parse(inspectOut);
  const manifest = {
    run_id: name,
    data_path: inspectedPath,
    raw_data_path: dataPath,
    reference_dir: 'data/references',
    preprocessing: prepReport
      ? {
          status: prepReport.status,
          selected: prepReport.selected || null,
          tables_found: prepReport.tables_found || 0,
          context_files: prepReport.context_files || 0,
          skipped_files: prepReport.skipped_files || 0,
          report: path.join(runDir, '00_input', 'preprocessing_report.json'),
        }
      : null,
    data_profile: {
      rows: insp.rows,
      columns: insp.columns,
      time_column: insp.time_column || null,
    },
    columns: (insp.column_details || []).map((c) => ({ name: c.name, type: c.type })),
    inspected_at: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(runDir, '00_input', 'input_manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  fs.writeFileSync(
    path.join(runDir, '00_input', 'user_context.json'),
    JSON.stringify(
      { run_id: name, user_objective: objective, process_description: processDesc },
      null, 2
    ) + '\n'
  );
  fs.writeFileSync(
    path.join(runDir, '00_input', 'run_config.json'),
    JSON.stringify(
      {
        data_path: inspectedPath,
        raw_data_path: dataPath,
        interaction_mode: 'auto',
        process_description: processDesc,
        user_objective: objective,
        analysis_constraints: {
          max_web_research_queries: 5,
          judge_score_threshold: 90,
          max_judge_iterations: 3,
          max_reviewer_iterations: 2,
          global_max_iterations: 5,
        },
      },
      null, 2
    ) + '\n'
  );
} catch (e) {
  console.error('ERROR: inspect/input-write failed:', e.message);
  process.exit(1);
}

// Log pipeline events for inspect step
try {
  runScript(path.join(sharedPath, 'scripts', 'append-pipeline-event.mjs'), [
    runDir, '--event', 'step_start', '--agent', 'main-agent', '--step', 'inspect',
    '--data', JSON.stringify({ data_path: inspectedPath, raw_data_path: dataPath }),
  ]);
  runScript(path.join(sharedPath, 'scripts', 'append-pipeline-event.mjs'), [
    runDir, '--event', 'step_complete', '--agent', 'main-agent', '--step', 'inspect',
    '--files', '00_input/input_manifest.json,00_input/user_context.json',
  ]);
} catch (e) {
  // non-fatal
}

// Step 3: baseline artifact check — what the orchestrator agent must still run
const BASELINE_CHECKS = [
  ['01_ontology', 'ontology.json'],
  ['02_processed', 'cleaned_data.csv'],
  ['02_processed', 'feature_summary.json'],
  ['02_processed', 'validate_report.json'],
  ['02_processed', 'data_analysis_conclusion.json'],
  ['02_processed', 'analysis_parameter_selection.json'],
  ['04_diagnostics', 'diagnosis.json'],
  ['04_diagnostics', 'evidence.json'],
  ['04_diagnostics', 'confidence.json'],
  ['04_diagnostics', 'reasoning_chain.json'],
  ['03_figures', 'plot_manifest.json'],
  ['03_figures', 'visual_analysis.json'],
];
const missing = BASELINE_CHECKS
  .filter(([d, f]) => !fs.existsSync(path.join(runDir, d, f)))
  .map(([d, f]) => `${d}/${f}`);

const baselineDone = missing.length === 0;

const output = {
  run_dir: runDir,
  input_mode: 'A_new_data',
  initialized: true,
  data_source: {
    file: dataPath,
    rows: null, // filled by inspect in input_manifest
  },
  baseline_complete: baselineDone,
  missing_baseline: missing,
  next_steps: baselineDone
    ? ['Baseline complete — run: node enhance_orchestrator.mjs --run-dir <run_dir>']
    : [
        `Run the auto baseline (Step 2-9) on ${runDir} before enhancement. Dispatch in order:`,
        '  context-builder (ontology) → data-processor → diagnostician',
        '  → judge + report-reviewer(pre-report, parallel) → reporter',
        '  → report-reviewer(final, ENDORSED) → html-visualizer → html-reviewer',
        'Or dispatch the enhance-orchestrator agent with DATA_PATH for fully automatic entry-A flow.',
      ],
};

console.log(JSON.stringify(output, null, 2));
