// GET /api/uploads — list the user's uploaded datasets, newest first.

import { defineEventHandler } from 'h3';
import { listUploads } from '../../utils/uploads.mjs';

export default defineEventHandler(() => {
  const uploads = listUploads();
  return {
    uploads,
    count: uploads.length,
    // Which algorithms can meaningfully run on user data, and why the others
    // cannot. Stated here so the UI does not have to guess or over-promise.
    applicability: {
      runnable: [
        'pca-t2-spe', 'kpca-rbf', 'ica-fastica', 'spc-ewma-cusum', 'knn-fdd', 'iforest',
        'llm-direct', 'llm-cot', 'llm-react', 'llm-debate',
      ],
      not_applicable: {
        'fe-official': 'FaultExplainer\'s protocol is defined for the Tennessee Eastman process only (its scaler, PCA basis and EXPLAIN_ROOT cause list are TEP-specific).',
        'xgb-gbdt': 'Trained on labelled TEP runs; it cannot classify a different process.',
        'rf-forest': 'Trained on labelled TEP runs; it cannot classify a different process.',
        'mlp-classifier': 'Trained on labelled TEP runs; it cannot classify a different process.',
        'ae-reconstruction': 'Its reconstruction threshold was calibrated on the TEP normal run and does not transfer to another dataset\'s per-row scale.',
      },
      note:
        'Detectors report CONTRIBUTING VARIABLES for user data: the variable->cause table in tep-affinity.mjs is TEP-specific and is deliberately NOT applied. '
        + 'Mechanism hypotheses come from the LLM comparators, which reason over the statistical digest plus whatever process description you supply.',
    },
  };
});
