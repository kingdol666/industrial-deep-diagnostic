#!/usr/bin/env node
// Verifies the shutdown path that SIGINT/SIGTERM handlers call:
// start a REAL engine run, grab its child query, run shutdownAllEngines(),
// and assert the child was terminated (not merely detached).
//
// Why not test the signal itself? On Windows, process.kill(pid,'SIGINT') does
// not invoke JS signal handlers (console Ctrl+C is required); Linux/macOS
// deliver SIGTERM normally. Testing the handler's target function is the
// portable proof.
import Database from 'file:///D:/codes/myskills/idd-doe-impl/app/backend/node_modules/better-sqlite3/lib/index.js';

const { createDiagnosisRun, triggerDiagnosis, shutdownAllEngines } = await import('../../app/backend/src/services/diagnosis.service.mjs');
const { getChild } = await import('../../app/backend/src/engine/diagnosis-engine.mjs');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const check = (name, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  ${String(detail).slice(0, 200)}` : ''}`);
  if (!ok) failures += 1;
};

const scene = `shutdown_probe_${Date.now().toString(36).slice(-5)}`;
const created = createDiagnosisRun({
  dataPath: 'data/lsr_demo/line_demo.csv',
  sceneName: scene,
  harness: 'omp',
  analysisIntent: 'stability-report',
  userQuestion: 'shutdown probe',
  timeoutMinutes: 1,
});
const runId = created.runId;
check('run created', !!runId, runId);
triggerDiagnosis(runId);

let child = null;
for (let i = 0; i < 60 && !child; i += 1) {
  await sleep(200);
  child = getChild(runId);
}
check('real engine child spawned', !!child, child ? 'query attached' : 'no child');

const closed = shutdownAllEngines();
check('shutdownAllEngines returned run count', closed >= 1, String(closed));
if (child) {
  const killedImmediately = child.killed === true || child.exitCode !== null;
  await sleep(2500);
  const exited = child.exitCode !== null || child.killed === true;
  check('engine child terminated', killedImmediately || exited,
    JSON.stringify({ killed: child.killed, exitCode: child.exitCode }));
}
check('child reference cleared', getChild(runId) == null);

// The probe run never executes to completion; remove its row so it does not
// show up as an interrupted run on the next boot.
try {
  const db = new Database('D:/codes/myskills/idd-doe-impl/data/diagnostic.db');
  db.prepare('DELETE FROM diagnosis_event_stream WHERE run_id = ?').run(runId);
  db.prepare('DELETE FROM diagnosis_logs WHERE run_id = ?').run(runId);
  db.prepare('DELETE FROM diagnostic_runs WHERE run_id = ?').run(runId);
  db.close();
  check('probe run row cleaned up', true);
} catch (err) {
  check('probe run row cleaned up', false, err.message);
}

console.log(`\n[RESULT] failures=${failures}`);
process.exit(failures ? 1 : 0);
