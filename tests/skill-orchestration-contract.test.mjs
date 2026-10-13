import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  preAuditPolicyValid,
  requiredArtifactsForMode,
  validateSkippedStageEvidence,
  visualEvidenceSatisfied,
} from '../.claude/skills/industrial-analysis-auto/scripts/execution_policy.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const setup = path.join(repo, '.claude/skills/industrial-analysis-auto/scripts/setup.mjs');
const enhancementEntry = path.join(repo, '.claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs');
const enhancementInit = path.join(repo, '.claude/skills/industrial-analysis-enhance-auto/scripts/entry_a_init.mjs');

function runSetup(extraArgs = []) {
  const base = mkdtempSync(path.join(os.tmpdir(), 'idd-skill-setup-'));
  try {
    const result = spawnSync(process.execPath, [setup, '--name', 'contract-test', '--base-dir', base, ...extraArgs], {
      cwd: repo,
      encoding: 'utf8',
    });
    const runDir = path.join(base, '');
    return { result, base, runDir };
  } catch (error) {
    rmSync(base, { recursive: true, force: true });
    throw error;
  }
}

test('setup stores the explicitly selected fast mode', () => {
  const { result, base } = runSetup(['--mode', 'fast']);
  try {
    assert.equal(result.status, 0, result.stderr);
    const out = JSON.parse(result.stdout.trim());
    const configPath = path.join(out.run_dir, '00_input/run_config.json');
    const config = JSON.parse(readFileSync(configPath, 'utf8'));
    const validator = path.join(repo, '.claude/shared/scripts/validate.mjs');
    const schema = path.join(repo, '.claude/shared/schemas/run_config_schema.json');
    const validation = spawnSync(process.execPath, [validator, schema, configPath], { cwd: repo, encoding: 'utf8' });
    assert.equal(validation.status, 0, validation.stdout + validation.stderr);
    assert.equal(config.run_mode, 'fast');
    assert.equal(out.manifest.execution_policy.run_mode, 'fast');
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});

test('setup defaults to full for benchmark/backward compatibility', () => {
  const { result, base } = runSetup();
  try {
    assert.equal(result.status, 0, result.stderr);
    const out = JSON.parse(result.stdout.trim());
    const configPath = path.join(out.run_dir, '00_input/run_config.json');
    const config = JSON.parse(readFileSync(configPath, 'utf8'));
    const validator = path.join(repo, '.claude/shared/scripts/validate.mjs');
    const schema = path.join(repo, '.claude/shared/schemas/run_config_schema.json');
    const validation = spawnSync(process.execPath, [validator, schema, configPath], { cwd: repo, encoding: 'utf8' });
    assert.equal(validation.status, 0, validation.stdout + validation.stderr);
    assert.equal(config.run_mode, 'full');
    assert.equal(out.manifest.execution_policy.run_mode, 'full');
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});

test('setup rejects an unknown run mode before creating a run', () => {
  const { result, base } = runSetup(['--mode', 'turbo']);
  try {
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /mode|fast|full/i);
    assert.equal(readdirSync(base).length, 0, 'invalid run mode must fail before creating a run directory');
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});

test('enhancement entry points reject an invalid mode before touching data or a RUN_DIR', () => {
  const entry = spawnSync(process.execPath, [enhancementEntry, '--run-dir', 'missing-run', '--mode', 'turbo'], { cwd: repo, encoding: 'utf8' });
  const init = spawnSync(process.execPath, [enhancementInit, '--data-path', 'missing.csv', '--name', 'invalid-mode', '--mode', 'turbo'], { cwd: repo, encoding: 'utf8' });
  assert.equal(entry.status, 2, entry.stdout + entry.stderr);
  assert.equal(init.status, 2, init.stdout + init.stderr);
  assert.match(entry.stderr, /fast or full/i);
  assert.match(init.stderr, /fast or full/i);
});

test('skipped stages require a matching artifact-check event and reason', () => {
  const skipped = [{ stage: 'pre_report_audit', reason: 'fast_mode', event: 'artifact_check_complete' }];
  const matching = [{
    event: 'artifact_check_complete',
    skipped_stage: 'pre_report_audit',
    reason: 'fast_mode',
  }];
  assert.deepEqual(validateSkippedStageEvidence(skipped, matching), []);
  assert.equal(validateSkippedStageEvidence(skipped, [])[0], 'pre_report_audit');
  assert.equal(validateSkippedStageEvidence([{ ...skipped[0], reason: '' }], matching)[0], 'pre_report_audit');
});

test('fast/full pre-audit policy requires the matching run artifact or skip', () => {
  assert.equal(preAuditPolicyValid({ runMode: 'fast', preAuditExists: false, preAuditSkipped: true }), true);
  assert.equal(preAuditPolicyValid({ runMode: 'fast', preAuditExists: true, preAuditSkipped: true }), false);
  assert.equal(preAuditPolicyValid({ runMode: 'full', preAuditExists: true, preAuditSkipped: false }), true);
  assert.equal(preAuditPolicyValid({ runMode: 'full', preAuditExists: false, preAuditSkipped: true }), false);
});

test('fast mode can use captions only when VLM was explicitly skipped', () => {
  assert.equal(visualEvidenceSatisfied({ runMode: 'fast', visualExists: false, captionsExist: true, vlmSkipped: true }), true);
  assert.equal(visualEvidenceSatisfied({ runMode: 'fast', visualExists: false, captionsExist: false, vlmSkipped: true }), false);
  assert.equal(visualEvidenceSatisfied({ runMode: 'fast', visualExists: false, captionsExist: true, vlmSkipped: false }), false);
  assert.equal(visualEvidenceSatisfied({ runMode: 'full', visualExists: false, captionsExist: true, vlmSkipped: true }), false);
});

test('HTML opt-out removes only the two HTML delivery artifacts', () => {
  const required = ['report.md', 'diagnostic-report.html', '05_review/html_review.json', 'optimizer.md'];
  assert.deepEqual(requiredArtifactsForMode(required, { htmlOptOut: true }), ['report.md', 'optimizer.md']);
  assert.deepEqual(requiredArtifactsForMode(required), required);
});

test('artifact check event atomically records its skipped-stage reason in the manifest', () => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), 'idd-skip-event-'));
  try {
    const runDir = path.join(sandbox, 'run');
    mkdirSync(runDir, { recursive: true });
    const manifest = {
      run_id: 'skip-contract', status: 'initialized',
      steps: [{ step: 'present', status: 'pending' }],
      pipeline: { integrity: {} },
      execution_policy: { run_mode: 'fast', audit: { skipped_stages: [] } },
    };
    writeFileSync(path.join(runDir, 'run_manifest.json'), JSON.stringify(manifest));
    writeFileSync(path.join(runDir, '.pipeline_events.jsonl'), '');
    const logger = path.join(repo, '.claude/shared/scripts/append-pipeline-event.mjs');
    const result = spawnSync(process.execPath, [
      logger, runDir, '--event', 'artifact_check_complete', '--agent', 'main-agent', '--step', 'present',
      '--data', JSON.stringify({ skipped_stage: 'pre_report_audit', reason: 'fast_mode' }),
    ], { cwd: repo, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stdout + result.stderr);
    const updated = JSON.parse(readFileSync(path.join(runDir, 'run_manifest.json'), 'utf8'));
    assert.deepEqual(updated.execution_policy.audit.skipped_stages, [
      { stage: 'pre_report_audit', reason: 'fast_mode', event: 'artifact_check_complete' },
    ]);
    const events = readFileSync(path.join(runDir, '.pipeline_events.jsonl'), 'utf8').trim().split(/\\r?\\n/).map(JSON.parse);
    assert.equal(validateSkippedStageEvidence(updated.execution_policy.audit.skipped_stages, events).length, 0);
  } finally {
    rmSync(sandbox, { recursive: true, force: true });
  }
});
