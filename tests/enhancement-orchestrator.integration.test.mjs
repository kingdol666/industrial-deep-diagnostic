import assert from 'node:assert/strict';
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const orchestrator = path.join(repo, '.claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs');
const autoSkill = path.join(repo, '.claude/skills/industrial-analysis-auto');

function putJson(file, value) {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(value, null, 2));
}

function makeBaseline(runDir) {
  const required = [
    '01_ontology/ontology.json',
    '02_processed/cleaned_data.csv',
    '02_processed/feature_summary.json',
    '02_processed/validate_report.json',
    '02_processed/data_analysis_conclusion.json',
    '02_processed/analysis_parameter_selection.json',
    '04_diagnostics/diagnosis.json',
    '04_diagnostics/evidence.json',
    '04_diagnostics/confidence.json',
    '04_diagnostics/reasoning_chain.json',
    '03_figures/plot_manifest.json',
    '03_figures/visual_analysis.json',
  ];
  for (const file of required) {
    const target = path.join(runDir, file);
    mkdirSync(path.dirname(target), { recursive: true });
    if (file.endsWith('.csv')) writeFileSync(target, 'x\n1\n');
    else putJson(target, {});
  }
  mkdirSync(path.join(runDir, '00_input'), { recursive: true });
  putJson(path.join(runDir, '00_input/run_config.json'), { data_path: path.join(runDir, '02_processed/cleaned_data.csv'), run_mode: 'fast' });
  writeFileSync(path.join(runDir, '00_input/input_manifest.json'), '{}');
  putJson(path.join(runDir, 'run_manifest.json'), { run_id: 'orchestration-test', steps: [], pipeline: {} });
  mkdirSync(path.join(runDir, 'enhancement'), { recursive: true });
  putJson(path.join(runDir, 'enhancement/enhanced_knowledge.json'), { enhancement_status: 'READY', relationship_graph: { edges: [] } });
}

test('Mode A carries fast mode through preprocessing into the final run config', () => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), 'idd-entry-a-mode-'));
  try {
    const data = path.join(sandbox, 'input.csv');
    const baseDir = path.join(sandbox, 'runs');
    writeFileSync(data, 'timestamp,feed_rate,conversion\n2026-01-01T00:00:00Z,10,95\n2026-01-01T01:00:00Z,11,94\n2026-01-01T02:00:00Z,12,93\n');
    const result = spawnSync(process.execPath, [
      path.join(repo, '.claude/skills/industrial-analysis-enhance-auto/scripts/entry_a_init.mjs'),
      '--data-path', data, '--name', 'mode-propagation', '--mode', 'fast', '--base-dir', baseDir,
    ], { cwd: repo, encoding: 'utf8', timeout: 120000 });
    assert.equal(result.status, 0, result.stdout + result.stderr);
    const output = JSON.parse(result.stdout.trim().split(/\\r?\\n/).at(-1));
    const config = JSON.parse(readFileSync(path.join(output.run_dir, '00_input/run_config.json'), 'utf8'));
    const manifest = JSON.parse(readFileSync(path.join(output.run_dir, 'run_manifest.json'), 'utf8'));
    assert.equal(config.run_mode, 'fast');
    assert.equal(manifest.execution_policy.run_mode, 'fast');
  } finally {
    rmSync(sandbox, { recursive: true, force: true });
  }
});

test('a failed current enhancement run writes FAILED despite a previous READY knowledge artifact', () => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), 'idd-enhance-test-'));
  try {
    const runDir = path.join(sandbox, 'run');
    makeBaseline(runDir);
    const stubPython = path.join(sandbox, 'python-fail.cmd');
    writeFileSync(stubPython, '@echo off\necho injected E1 failure 1>&2\nexit /b 7\n');
    chmodSync(stubPython, 0o755);
    const env = { ...process.env, HARNESS_TEST_PYTHON: stubPython };
    const result = spawnSync(process.execPath, [orchestrator, '--run-dir', runDir], { cwd: repo, env, encoding: 'utf8' });
    assert.notEqual(result.status, 0, result.stdout + result.stderr);
    const status = JSON.parse(readFileSync(path.join(runDir, 'enhancement/enhancement_status.json'), 'utf8'));
    assert.equal(status.status, 'FAILED');
    assert.equal(status.launch_results[0].phase, 'E1');
    assert.equal(status.launch_results[0].status, 'failed');
  } finally {
    rmSync(sandbox, { recursive: true, force: true });
  }
});
