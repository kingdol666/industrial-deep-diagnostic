// GET /api/state — consolidated lab state for the UI shell.
//
// One round trip gives the UI everything it needs to render the header: the
// repository contract, algorithm inventory (loaded vs missing), case list, LLM
// provider availability, archived-sweep list, and the reproduction audit.

import { defineEventHandler } from 'h3';
import { listAlgorithms, moduleHealth, CITATION_ONLY, FAMILY_LABELS } from '../utils/registry.mjs';
import { loadCasesRaw, repoRoot, CASES_FILE, FE_REPO, ARCHIVED_ANSWERS, exists, archivedBaselineModel, feProvenance } from '../utils/paths.mjs';
import { detectProviders, resolveProvider } from '../utils/llm/provider.mjs';
import { listSweeps } from '../utils/runner.mjs';
import { iddReference } from '../utils/scoring.mjs';
import fs from 'node:fs';
import path from 'node:path';

export default defineEventHandler(() => {
  const root = repoRoot();
  const providers = detectProviders({});
  let resolved = null;
  try {
    resolved = resolveProvider({});
  } catch { /* unavailable */ }

  const fe = feProvenance();

  const answerCount = exists(ARCHIVED_ANSWERS())
    ? fs.readdirSync(ARCHIVED_ANSWERS()).filter((f) => f.endsWith('.json')).length
    : 0;

  const cases = loadCasesRaw().map((c) => ({
    case_id: c.case_id,
    dataset: c.dataset,
    control: Boolean(c.control),
    csv: c.csv,
  }));

  // ---- comparability guard -------------------------------------------------
  // The repository's archived LLM baseline was produced with one specific model.
  // A fresh run through a DIFFERENT model is a different experiment; the honest
  // thing is to say so loudly rather than let tables be read as like-for-like.
  const archived = archivedBaselineModel();
  const labModel = resolved?.model || resolved?.id || null;
  let comparability = {
    status: 'no_provider',
    archived,
    lab_model: null,
    note: 'No LLM provider resolved; LLM comparators will report skipped_no_provider.',
  };
  if (resolved) {
    const arch = (archived?.model || '').toLowerCase();
    const lab = String(resolved.model || resolved.id || '').toLowerCase();
    // The archived baseline names its family ("GLM family ..."); match on any
    // family token rather than an exact string.
    const sameFamily = Boolean(arch)
      && ['glm', 'zhipu', 'chatglm'].some((t) => arch.includes(t) && lab.includes(t));
    comparability = sameFamily
      ? {
          status: 'same_family',
          archived,
          lab_model: labModel,
          note: 'The resolved provider appears to be the same model family as the archived baseline; fresh LLM numbers are directly comparable.',
        }
      : {
          status: 'different_model',
          archived,
          lab_model: labModel,
          note:
            'CONFOUND: the archived LLM baseline was produced with a different model than the one this lab calls. '
            + 'Fresh LLM comparator numbers are therefore NOT comparable to results/benchmark/baselines.json — they are a new '
            + 'experiment under a different model. Report them as such, or point the lab at the original model via '
            + 'BASELINE_LLM_MODEL / BASELINE_LLM_PROVIDER.',
        };
  }

  return {
    repo: {
      root,
      cases_file: CASES_FILE(),
      cases_present: exists(CASES_FILE()),
      fault_explainer: {
        path: fe.path,
        cloned: fe.cloned,
        commit: fe.commit,
        provenance_source: fe.source, // 'git' (live checkout) | 'VENDOR.md' (vendored)
        vendored: fe.vendored,
        upstream: fe.upstream,
        processed_outputs: exists(path.join(FE_REPO(), 'frontend', 'public')),
        api_key_configured: false, // backend/.env ships empty; verified at audit time
      },
      archived_llm_answers: answerCount,
    },
    families: FAMILY_LABELS,
    algorithms: listAlgorithms(),
    modules: moduleHealth(),
    citation_only: CITATION_ONLY,
    cases,
    providers,
    resolved_provider: resolved ? { id: resolved.id, detail: resolved.detail, model: resolved.model || null } : null,
    comparability,
    sweeps: listSweeps(),
    idd_reference: iddReference(),
    env: {
      baseline_llm_provider: process.env.BASELINE_LLM_PROVIDER || 'auto',
      baseline_llm_model: process.env.BASELINE_LLM_MODEL || '',
      selftest: process.env.BASELINE_LLM_ALLOW_SELFTEST === '1',
    },
  };
});
