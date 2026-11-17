// adoptCandidate path guard — runDir/runName arrive in the request body, so
// both are hostile input. Before the guard, `runName: '../../data'` escaped the
// runs root and `runDir` accepted ANY absolute path (arbitrary
// 01_ontology/ontology.json reads, attacker-chosen provenance). Containment is
// now proven with pathGuard and violations fail on the 400 path.
//
// The legitimate shapes are pinned without fixtures: they must pass the guard
// and then fail with the existing 404 (no such run), never with 400.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { tmpdir } from 'os';
import { join } from 'path';

const { adoptCandidate } = await import('../src/services/ontology.service.mjs');
const { PROJECT_ROOT } = await import('../../../config/loader.mjs');

const RUNS_ROOT = join(PROJECT_ROOT, 'workspace', 'diagnostic-runs');
const MISSING = `__no_such_run_${process.pid}__`;

function assertOutsideBaseError(err, input) {
  assert.equal(err.status, 400, `${input}: status`);
  assert.equal(err.code, 'PATH_OUTSIDE_BASE', `${input}: code`);
  return true;
}

describe('adoptCandidate — run location containment', () => {
  test('runName traversal (incl. encoded and backslash forms) is refused with 400', () => {
    const hostile = [
      '../../data',
      '..\\..\\data',
      'a/../../data',
      '..',
      '%2e%2e%2f%2e%2e%2fdata',
      'C:/Windows/Temp',
      '/etc',
      'x\0y',
    ];
    for (const runName of hostile) {
      assert.throws(() => adoptCandidate({ runName }), (e) => assertOutsideBaseError(e, runName), `runName=${runName}`);
    }
  });

  test('runDir outside the runs root is refused with 400 (absolute and relative)', () => {
    const hostile = [
      tmpdir(),                                   // absolute, outside the project
      join(tmpdir(), 'some-run'),
      '../../config',                             // parent traversal
      'data',                                     // inside the project, but not a run dir
      'workspace',                                // runs root's parent
    ];
    for (const runDir of hostile) {
      assert.throws(() => adoptCandidate({ runDir }), (e) => assertOutsideBaseError(e, runDir), `runDir=${runDir}`);
    }
  });

  test('legitimate run locations pass the guard (fail with the existing 404)', () => {
    const legit = [
      { runName: MISSING },                                      // a run directory name
      { runDir: join(RUNS_ROOT, MISSING) },                      // absolute — what /candidates returns
      { runDir: `workspace/diagnostic-runs/${MISSING}` },        // project-relative
    ];
    for (const input of legit) {
      assert.throws(() => adoptCandidate(input), (e) => {
        assert.equal(e.status, 404, `${JSON.stringify(input)}: containment must pass (404, not 400)`);
        assert.equal(e.code, 'ONTOLOGY_NOT_FOUND');
        return true;
      }, JSON.stringify(input));
    }
  });
});
