// GET /api/run/:jobId — poll a running sweep.

import { defineEventHandler, getRouterParam, createError } from 'h3';
import { jobs } from '../../utils/jobs.mjs';
import { wilson } from '../../utils/scoring.mjs';

export default defineEventHandler((event) => {
  const jobId = getRouterParam(event, 'jobId');
  const job = jobs.get(jobId);
  if (!job) throw createError({ statusCode: 404, statusMessage: `unknown job: ${jobId}` });

  // Compact per-algorithm rollup so the UI can show a live table.
  const live = {};
  for (const entry of job.log) {
    if (entry.kind !== 'done') continue;
    live[entry.algorithm] = live[entry.algorithm] || {
      algorithm: entry.algorithm, done: 0, hits: 0, faults: 0, exact: 0,
      controls: 0, controlPass: 0, falseAlarms: 0, abstain: 0, failed: 0, outcomes: [],
    };
    const l = live[entry.algorithm];
    l.done++;
    l.outcomes.push({ case: entry.case, outcome: entry.outcome, top3: entry.top3, exact_idv: entry.exact_idv });
    if (entry.outcome === 'hit') { l.hits++; l.faults++; }
    else if (entry.outcome === 'miss' || entry.outcome === 'abstain') l.faults++;
    if (entry.outcome === 'abstain') l.abstain++;
    if (entry.exact_idv === true) l.exact++;
    if (entry.outcome === 'control-pass') { l.controls++; l.controlPass++; }
    if (entry.outcome === 'FALSE-ALARM') { l.controls++; l.falseAlarms++; }
    if (['skipped_no_provider', 'error', 'not_applicable'].includes(entry.outcome)) l.failed++;
  }
  for (const l of Object.values(live)) {
    l.top1_rate = l.faults ? Number((l.hits / l.faults).toFixed(4)) : null;
    l.wilson = l.faults ? wilson(l.hits, l.faults) : null;
  }

  return {
    job_id: job.job_id,
    state: job.state,
    done: job.done,
    total: job.total,
    run_id: job.run_id,
    error: job.error,
    summary: job.summary,
    live,
    log: job.log.slice(-200),
    started_at: job.started_at,
    finished_at: job.finished_at || null,
  };
});
