// In-memory job table for background sweeps.
//
// Kept out of the route modules on purpose: route files are auto-registered by
// Nitro and importing one route from another couples them in ways the router
// does not expect. State lives here instead.

/** jobId -> job record */
export const jobs = new Map();

/** Drop finished jobs older than `maxAgeMs` so a long dev session cannot leak. */
export function pruneJobs(maxAgeMs = 6 * 60 * 60 * 1000) {
  const cutoff = Date.now() - maxAgeMs;
  for (const [id, job] of jobs) {
    if (job.state !== 'running' && job.finished_at && new Date(job.finished_at).getTime() < cutoff) {
      jobs.delete(id);
    }
  }
}
