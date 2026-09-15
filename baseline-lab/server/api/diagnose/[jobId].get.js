// GET /api/diagnose/:jobId — current state of a diagnosis.
//
// Returns the accumulated findings. `?events=1` also returns the full event log
// (used when a client reconnects after the stream already finished, so it can
// rebuild exactly what it would have seen live).

import { defineEventHandler, getRouterParam, getQuery, createError } from 'h3';
import { getDiagnosisJob } from '../../utils/diagnosis.mjs';

export default defineEventHandler((event) => {
  const jobId = getRouterParam(event, 'jobId');
  const job = getDiagnosisJob(jobId);
  if (!job) throw createError({ statusCode: 404, statusMessage: `unknown diagnosis job: ${jobId}` });

  const withEvents = getQuery(event)?.events === '1';
  return {
    job_id: job.job_id,
    state: job.state,
    upload_id: job.upload_id,
    dataset_label: job.dataset_label,
    algorithms: job.algorithms,
    refused: job.refused,
    started_at: job.started_at,
    finished_at: job.finished_at,
    error: job.error,
    progress: {
      done: job.findings.length,
      total: job.algorithms.length,
    },
    findings: job.findings,
    report: job.report,
    ...(withEvents ? { events: job.events } : {}),
  };
});
