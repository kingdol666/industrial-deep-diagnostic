// POST /api/run — start a sweep in the background; returns a job id immediately.
//
// The UI polls GET /api/run/:jobId for progress. Sweeps run sequentially so the
// progress log is deterministic and comparable between runs.

import { randomUUID } from 'node:crypto';
import { runSweep } from '../utils/runner.mjs';
import { listCaseIds } from '../utils/paths.mjs';
import { getAlgorithm } from '../utils/registry.mjs';
import { jobs, pruneJobs } from '../utils/jobs.mjs';
import { defineEventHandler, readBody, createError } from 'h3';

export default defineEventHandler(async (event) => {
  pruneJobs();
  const body = await readBody(event);
  const algorithms = Array.isArray(body?.algorithms) ? body.algorithms.filter(Boolean) : [];
  const cases = Array.isArray(body?.cases) && body.cases.length ? body.cases : listCaseIds();
  const config = body?.config || {};

  if (!algorithms.length) {
    throw createError({ statusCode: 400, statusMessage: 'select at least one algorithm' });
  }
  for (const id of algorithms) {
    try {
      getAlgorithm(id);
    } catch (err) {
      throw createError({ statusCode: 400, statusMessage: String(err.message) });
    }
  }

  const jobId = randomUUID();
  const job = {
    job_id: jobId,
    state: 'running',
    algorithms,
    cases,
    total: algorithms.length * cases.length,
    done: 0,
    started_at: new Date().toISOString(),
    log: [],
    run_id: null,
    summary: null,
    error: null,
  };
  jobs.set(jobId, job);

  // Fire and forget: the HTTP response returns the job id immediately.
  (async () => {
    try {
      const res = await runSweep({
        algorithms,
        cases,
        config,
        options: body?.options || {},
        label: body?.label || 'ui',
        onProgress: (p) => {
          if (p.phase === 'start') {
            job.log.push({ t: Date.now(), kind: 'start', algorithm: p.algorithmId, case: p.caseId, done: p.done, total: p.total });
          } else {
            job.done = p.done;
            const s = p.result.scored;
            job.log.push({
              t: Date.now(),
              kind: 'done',
              algorithm: p.algorithmId,
              case: p.caseId,
              status: p.result.status,
              outcome: p.result.status !== 'executed'
                ? p.result.status
                : s.control
                  ? (s.control_pass ? 'control-pass' : 'FALSE-ALARM')
                  : s.strict_top1_hit
                    ? 'hit'
                    : s.top3.length ? 'miss' : 'abstain',
              top3: s.top3?.slice(0, 3) || [],
              exact_idv: s.exact_idv_top1_hit ?? null,
              runtime_ms: p.result.output?.runtime_ms ?? null,
            });
          }
        },
      });
      job.run_id = res.run_id;
      job.summary = res.summary;
      job.state = 'complete';
      job.finished_at = new Date().toISOString();
    } catch (err) {
      job.state = 'error';
      job.error = String(err && err.stack ? err.stack : err);
      job.finished_at = new Date().toISOString();
    }
  })();

  return { job_id: jobId, total: job.total };
});
