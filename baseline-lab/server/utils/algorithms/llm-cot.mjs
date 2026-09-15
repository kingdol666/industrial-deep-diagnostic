// llm-cot — chain-of-thought single-agent LLM baseline.
//
// The comparison matrix in docs/publication-strategy-report.md §5.2 lists
// "GPT-4o + CoT" as a distinct baseline arm. This module makes it runnable:
// the same blind digest as llm-direct, but the model is instructed to work
// through unit attribution, deviation direction, control-loop compensation and
// explicit elimination of competing candidates BEFORE committing to an answer.

import { llmContext, notRun, callJson, normalizeAnswer, promptSource } from './_llm-shared.mjs';
import { buildCotPrompt } from '../llm/prompts.mjs';

export const meta = {
  id: 'llm-cot',
  label: 'LLM + 思维链 (CoT)',
  short: 'LLM-CoT',
  family: 'llm',
  kind: 'llm',
  deterministic: false,
  requiresProvider: true,
  needsReference: false,
  regimes: ['cot'],
  description:
    'Single model call with an explicit step-by-step reasoning scaffold: unit attribution, deviation direction, control-loop compensation, then elimination of named competing candidates before the final verdict.',
  provenance: {
    basis: ['wei2022chain'],
    repo: null,
    note: 'CoT arm of the comparison matrix, implemented as a runnable comparator.',
  },
};

export async function run(ctx, { config = {} } = {}) {
  const t0 = Date.now();
  const { caseDef, matrix } = ctx;

  const { provider, providerError } = llmContext(config);
  if (providerError) return { ...notRun('error', { error: providerError }), runtime_ms: Date.now() - t0 };
  if (!provider) return { ...notRun('skipped_no_provider'), runtime_ms: Date.now() - t0 };

  const prompt = buildCotPrompt(caseDef.case_id, matrix);
  const { ok, answer, invocation } = await callJson(provider, prompt, {
    timeoutMs: config.llmTimeoutMs || 300000,
    caseId: caseDef.case_id,
    algoId: meta.id,
    tag: 'cot',
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
    reasoning_scaffold: 'unit attribution -> deviation direction -> control compensation -> candidate elimination',
    prompt_source: promptSource(caseDef.case_id),
    regime: 'cot',
    runtime_ms: Date.now() - t0,
  };
}
