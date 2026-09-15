// Runner — executes algorithms against cases, scores them, persists results.
//
// Separation of concerns that makes the truthfulness claim checkable:
//   1. the algorithm receives a SANITIZED case (paths.loadCaseForAlgorithm)
//   2. it runs and returns its own answer
//   3. ONLY THEN does the runner load truth and score
// Nothing an algorithm sees can depend on the truth.

import fs from 'node:fs';
import path from 'node:path';
import { RUNS_DIR, ensureDir, writeJson, loadCaseForAlgorithm, loadTruth, listCaseIds, readJsonSafe, exists, RESULTS_DIR } from './paths.mjs';
import { buildContext } from './algorithms/_shared.mjs';
import { getAlgorithm, listAlgorithms } from './registry.mjs';
import { scoreResult, aggregate } from './scoring.mjs';

export function newRunId(label = 'run') {
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '-');
  return `${stamp}-${label}`;
}

export function runDir(runId) {
  return path.join(RUNS_DIR, runId);
}

/**
 * Execute one algorithm on one case.
 * @returns {{case_id, algorithm, status, ok, output, scored, error?}}
 */
export async function runOne({ algorithmId, caseId, config = {}, options = {}, log = () => {} }) {
  const algo = getAlgorithm(algorithmId);
  const caseDef = loadCaseForAlgorithm(caseId); // sanitized — no truth fields
  const result = {
    case_id: caseId,
    dataset: caseDef.dataset,
    algorithm: algorithmId,
    algorithm_label: algo.meta.label,
    family: algo.meta.family,
    started_at: new Date().toISOString(),
  };

  if (algo.meta.domains && !algo.meta.domains.includes(caseDef.dataset)) {
    result.status = 'not_applicable';
    result.output = {
      status: 'not_applicable',
      top3: [],
      verdict: null,
      reasoning: `This algorithm declares domains [${algo.meta.domains.join(', ')}] and is therefore not applicable to '${caseDef.dataset}'.`,
    };
  } else {
    try {
      const ctx = buildContext(caseDef, { log });
      result.output = await algo.run(ctx, { ...options, config });
      result.status = result.output?.status || 'executed';
    } catch (err) {
      result.status = 'error';
      result.error = String(err && err.stack ? err.stack : err);
      result.output = {
        status: 'error',
        top3: [],
        verdict: null,
        reasoning: `Algorithm threw: ${String(err && err.message ? err.message : err)}`,
      };
    }
  }

  // ---- scoring happens AFTER the algorithm has finished and only here
  const truth = loadTruth(caseId);
  result.scored = scoreResult(truth, result.output);
  result.ok = result.status === 'executed' && (result.scored.strict_top1_hit || result.scored.control_pass === true);
  result.finished_at = new Date().toISOString();
  return result;
}

/**
 * Execute a matrix of algorithms × cases sequentially (deterministic order so
 * logs are comparable). Emits progress through `onProgress`.
 */
export async function runSweep({
  algorithms,
  cases = null,
  config = {},
  options = {},
  label = 'sweep',
  onProgress = () => {},
  log = () => {},
} = {}) {
  const runId = newRunId(label);
  const dir = ensureDir(runDir(runId));
  const caseIds = cases && cases.length ? cases : listCaseIds();
  const algoIds = algorithms && algorithms.length ? algorithms : listAlgorithms().map((a) => a.id);

  const all = [];
  for (const id of algoIds) getAlgorithm(id); // fail fast on unknown ids

  fs.writeFileSync(
    path.join(dir, 'sweep.json'),
    JSON.stringify({ run_id: runId, algorithms: algoIds, cases: caseIds, config, started_at: new Date().toISOString() }, null, 2),
    'utf8',
  );

  let done = 0;
  const total = algoIds.length * caseIds.length;
  for (const algorithmId of algoIds) {
    for (const caseId of caseIds) {
      onProgress({ phase: 'start', algorithmId, caseId, done, total });
      const r = await runOne({ algorithmId, caseId, config, options, log });
      all.push(r);
      done++;
      onProgress({ phase: 'done', algorithmId, caseId, done, total, result: r });
      // incremental persistence: a long LLM sweep survives an interruption
      writeJson(path.join(dir, 'results.json'), { run_id: runId, partial: done < total, results: all });
    }
  }

  const summary = summarize(all, algoIds, caseIds);
  writeJson(path.join(dir, 'summary.json'), summary);
  writeJson(path.join(dir, 'results.json'), { run_id: runId, partial: false, results: all });

  return { run_id: runId, dir, results: all, summary };
}

/** Aggregate per-algorithm headline metrics. */
export function summarize(results, algoIds, caseIds) {
  const byAlgo = {};
  for (const id of algoIds) {
    const rows = results.filter((r) => r.algorithm === id);
    const scored = {};
    for (const r of rows) scored[r.case_id] = r.scored;
    const anyExecuted = rows.some((r) => r.status === 'executed');
    const skipped = rows.filter((r) => r.status === 'skipped_no_provider').length;
    const errored = rows.filter((r) => r.status === 'error').length;
    const na = rows.filter((r) => r.status === 'not_applicable').length;
    byAlgo[id] = {
      label: rows[0]?.algorithm_label || id,
      family: rows[0]?.family || null,
      status: errored ? 'partial_error' : skipped === rows.length ? 'skipped_no_provider' : anyExecuted ? 'executed' : 'no_data',
      executed: rows.filter((r) => r.status === 'executed').length,
      skipped_no_provider: skipped,
      errors: errored,
      not_applicable: na,
      metrics: aggregate(scored, { algorithms: id }),
    };
  }
  return {
    generated_at: new Date().toISOString(),
    algorithms: algoIds,
    cases: caseIds,
    by_algorithm: byAlgo,
  };
}

/** List persisted sweeps, newest first. */
export function listSweeps() {
  if (!exists(RUNS_DIR)) return [];
  return fs
    .readdirSync(RUNS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => {
      const id = d.name;
      const dir = runDir(id);
      // Tolerant reads: a listing must never throw because one sweep is
      // mid-write. A concurrent sweep rewrites results.json on every case.
      const meta = readJsonSafe(path.join(dir, 'sweep.json'), { run_id: id }) || { run_id: id };
      const hasSummary = exists(path.join(dir, 'summary.json'));
      const res = readJsonSafe(path.join(dir, 'results.json'), null);
      const partial = res ? res.partial !== false : true;
      const count = res?.results?.length || 0;
      return {
        run_id: id,
        started_at: meta.started_at || null,
        algorithms: meta.algorithms || [],
        cases: meta.cases || [],
        complete: hasSummary && !partial,
        result_count: count,
      };
    })
    .sort((a, b) => String(b.run_id).localeCompare(String(a.run_id)));
}

export function loadSweep(runId) {
  const dir = runDir(runId);
  if (!exists(dir)) throw new Error(`sweep not found: ${runId}`);
  const results = readJsonSafe(path.join(dir, 'results.json'), { results: [], partial: true });
  const summary = readJsonSafe(path.join(dir, 'summary.json'), null);
  const meta = readJsonSafe(path.join(dir, 'sweep.json'), { run_id: runId }) || { run_id: runId };
  return { meta, results: results.results || [], partial: results.partial !== false, summary };
}

export { RESULTS_DIR };
