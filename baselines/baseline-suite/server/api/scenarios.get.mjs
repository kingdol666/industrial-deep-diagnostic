// GET /api/scenarios — the 12 benchmark scenarios (truth-free view from the blind briefs)
import { defineEventHandler } from 'h3';
import { scenarioRouting, briefFor } from '../utils/repo.mjs';

export default defineEventHandler(() => {
  return scenarioRouting().map((r) => {
    const b = briefFor(r.case_id);
    return {
      case_id: r.case_id,
      dataset: r.dataset,
      role: b.role,
      rows: b.rows,
      columns: b.cols ?? b.columns,
      stats_engine: b.stats_engine,
      evidence_preview: {
        anomaly_columns: (b.evidence.anomaly_columns || []).slice(0, 3),
        n_correlation_pairs: (b.evidence.top_correlation_pairs || []).length,
      },
    };
  });
});
