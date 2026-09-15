// GET /api/diagnose/:jobId/stream — live Server-Sent Events for a diagnosis.
//
// This is what makes the diagnosis observably real rather than a progress bar
// followed by a blob: every model call is announced when it starts and when it
// returns, with the provider, model, latency and a clipped excerpt of the
// model's own reply.
//
// Reconnection is handled by replaying everything already emitted, so a client
// that attaches late (or reloads) still converges on the same event log.

import { defineEventHandler, getRouterParam, createError, setResponseHeaders } from 'h3';
import { getDiagnosisJob, subscribe } from '../../../utils/diagnosis.mjs';

export default defineEventHandler(async (event) => {
  const jobId = getRouterParam(event, 'jobId');
  const job = getDiagnosisJob(jobId);
  if (!job) throw createError({ statusCode: 404, statusMessage: `unknown diagnosis job: ${jobId}` });

  setResponseHeaders(event, {
    'content-type': 'text/event-stream; charset=utf-8',
    'cache-control': 'no-cache, no-transform',
    connection: 'keep-alive',
    'x-accel-buffering': 'no',
  });

  const res = event.node.res;
  res.flushHeaders?.();

  const send = (payload) => {
    res.write(`data: ${JSON.stringify(payload)}\n\n`);
  };

  // 1) replay history so a late subscriber is not missing context
  for (const e of job.events) send(e);

  // 2) if the job already finished, close immediately
  if (job.state !== 'running') {
    send({ seq: job.events.length, type: 'end', state: job.state });
    res.end();
    return;
  }

  // 3) otherwise stream live
  const unsubscribe = subscribe(job, (e) => {
    send(e);
    if (e.type === 'end') {
      unsubscribe();
      res.end();
    }
  });

  // Heartbeat: keeps proxies and browsers from dropping an idle stream while a
  // 80-second model call is in flight.
  const beat = setInterval(() => {
    try { res.write(': keep-alive\n\n'); } catch { /* client gone */ }
  }, 15000);

  event.node.req.on('close', () => {
    clearInterval(beat);
    unsubscribe();
  });
});
