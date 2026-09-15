// GET /api/sweeps        — list persisted sweeps
// GET /api/sweeps/:id    — full results + summary for one sweep

import { defineEventHandler, getRouterParam } from 'h3';
import { listSweeps, loadSweep } from '../../utils/runner.mjs';

export default defineEventHandler((event) => {
  const id = getRouterParam(event, 'id');
  if (!id) return { sweeps: listSweeps() };
  const sweep = loadSweep(id);
  return {
    meta: sweep.meta,
    partial: sweep.partial,
    summary: sweep.summary,
    results: sweep.results.map((r) => ({
      case_id: r.case_id,
      dataset: r.dataset,
      algorithm: r.algorithm,
      algorithm_label: r.algorithm_label,
      family: r.family,
      status: r.status,
      error: r.error || null,
      scored: r.scored,
      output: r.output,
    })),
  };
});
