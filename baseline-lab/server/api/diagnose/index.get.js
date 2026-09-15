// GET /api/diagnose — what a diagnosis can run on uploaded data, and why the
// rest cannot. The frontend renders this instead of guessing.

import { defineEventHandler } from 'h3';
import { diagnosableAlgorithms } from '../../utils/diagnosis.mjs';
import { detectProviders, resolveProvider } from '../../utils/llm/provider.mjs';

export default defineEventHandler(() => {
  const { runnable, refused } = diagnosableAlgorithms();
  let resolved = null;
  try { resolved = resolveProvider({}); } catch { /* none available */ }

  return {
    runnable: runnable.map((a) => ({
      id: a.id,
      label: a.label,
      short: a.short,
      family: a.family,
      deterministic: a.deterministic,
      requires_provider: Boolean(a.requiresProvider),
      kind: a.kind,
      description: a.description,
    })),
    refused: refused.map((a) => ({
      id: a.id,
      label: a.label,
      reason: a.why_not,
      family: a.family,
    })),
    provider: resolved ? { id: resolved.id, detail: resolved.detail, model: resolved.model || null } : null,
    truthfulness: 'Uploaded data has no ground truth, so a diagnosis reports real executions and real model '
      + 'answers but never a score. An algorithm that finds nothing says so; a model that concludes "normal" is '
      + 'reported as normal rather than pressed into naming a cause.',
  };
});
