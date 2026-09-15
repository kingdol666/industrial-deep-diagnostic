// llm-direct — bare single-call LLM baseline (paper §8.4 arm ii).
//
// One call per scenario, no ontology, no pipeline, no gates, no tools. The
// prompt is the same blind statistical digest the IDD pipeline receives, built
// byte-compatibly with the repository's archived baseline
// (scripts/benchmark/baseline_llm.mjs), so a fresh execution can be compared
// against results/benchmark/baseline_fe_answers/*.json.
//
// Two regimes, both runnable:
//   no_candidates   — blind digest only (all 12 scenarios)
//   with_candidates — blind digest + documented TEP cause list (TEP only; the
//                     FaultExplainer regime-1 protocol)

import { llmContext, notRun, callJson, normalizeAnswer, promptForRegime, promptSource } from './_llm-shared.mjs';

export const meta = {
  id: 'llm-direct',
  label: '裸 LLM 单次调用（无管线/无候选）',
  short: 'LLM-direct',
  family: 'llm',
  kind: 'llm',
  deterministic: false,
  requiresProvider: true,
  needsReference: false,
  regimes: ['no_candidates', 'with_candidates'],
  description:
    'One bare model call per scenario over the identical blinded statistical digest, with no ontology, no pipeline stages and no quality gates. The with_candidates regime additionally supplies the documented TEP cause list (FaultExplainer protocol).',
  provenance: {
    basis: ['khan2024faultexplainer'],
    repo: 'scripts/benchmark/baseline_llm.mjs (prompt parity), results/benchmark/baseline_fe_answers (archive)',
    note: 'Prompt is built byte-compatibly with the archived baseline; execution is a genuine model call.',
  },
};

export async function run(ctx, { regime = 'no_candidates', config = {} } = {}) {
  const t0 = Date.now();
  const { caseDef, matrix } = ctx;

  if (regime === 'with_candidates' && caseDef.dataset !== 'tep') {
    return {
      status: 'not_applicable',
      top3: [],
      verdict: null,
      reasoning: 'The with_candidates regime uses the documented TEP cause list and therefore applies only to TEP scenarios.',
      invocations: [],
      runtime_ms: Date.now() - t0,
    };
  }

  const { provider, providerError } = llmContext(config);
  if (providerError) return { ...notRun('error', { error: providerError }), runtime_ms: Date.now() - t0 };
  if (!provider) return { ...notRun('skipped_no_provider'), runtime_ms: Date.now() - t0 };

  const prompt = promptForRegime(regime, caseDef.case_id, matrix);
  const { ok, answer, invocation } = await callJson(provider, prompt, {
    timeoutMs: config.llmTimeoutMs || 300000,
    caseId: caseDef.case_id,
    algoId: `${meta.id}.${regime}`,
    tag: regime,
  });

  if (!ok || !answer) {
    return {
      status: 'error',
      top3: [],
      verdict: null,
      reasoning: `The model call did not produce a parseable strict-JSON answer (${invocation.error || 'unparseable reply'}). No answer is reported.`,
      invocations: [invocation],
      prompt_source: promptSource(caseDef.case_id),
      runtime_ms: Date.now() - t0,
    };
  }

  const norm = normalizeAnswer(answer, { caseDef });
  return {
    status: 'executed',
    ...norm,
    invocations: [invocation],
    prompt_source: promptSource(caseDef.case_id),
    regime,
    runtime_ms: Date.now() - t0,
  };
}
