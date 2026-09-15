// llm-debate — multi-agent debate baseline (AutoGen-style, framework-free).
//
// docs/publication-strategy-report.md §5.2 lists "AutoGen 多代理讨论" as a
// baseline arm and §5.1 (B2) names Gong et al.'s multi-agent LLM system as the
// nearest published competitor. No such system is runnable in this repository,
// so this module implements the same *shape* honestly and locally:
//
//   round 1  three role-separated specialists answer independently
//   round 2  each specialist sees the others and rebuts
//   judge    the chair adjudicates, weighing argument quality (not vote count)
//
// Each agent call uses the SAME blind digest as every other LLM comparator; the
// roles differ only in the reasoning stance they are instructed to take. Every
// individual reply is archived, so the debate trajectory is fully auditable.

import { llmContext, notRun, callJson, normalizeAnswer, promptSource, archiveAnswer } from './_llm-shared.mjs';
import { buildDebateRoles, buildDebateOpening, buildDebateRebuttal, buildDebateJudge } from '../llm/prompts.mjs';

export const meta = {
  id: 'llm-debate',
  label: '多代理辩论（3 专家 + 主席裁决）',
  short: 'Debate',
  family: 'llm',
  kind: 'llm',
  deterministic: false,
  requiresProvider: true,
  needsReference: false,
  regimes: ['debate'],
  description:
    'Framework-free multi-agent debate: three role-separated specialists (process / utilities / instrumentation) answer independently, then rebut each other, then a chair adjudicates the arguments against the evidence. Five model calls per scenario.',
  provenance: {
    basis: ['gong2026collective', 'du2023debate'],
    repo: null,
    note: 'Local, framework-free implementation of the multi-agent-debate arm; stands in for the unreleased Gong et al. system.',
  },
};

export async function run(ctx, { config = {}, onEvent = null } = {}) {
  const t0 = Date.now();
  const { caseDef, matrix } = ctx;

  const { provider, providerError } = llmContext(config);
  if (providerError) return { ...notRun('error', { error: providerError }), runtime_ms: Date.now() - t0 };
  if (!provider) return { ...notRun('skipped_no_provider'), runtime_ms: Date.now() - t0 };

  const timeoutMs = config.llmTimeoutMs || 300000;
  const { context, roles } = buildDebateRoles(caseDef.case_id, matrix);
  const invocations = [];

  // ---- round 1: independent openings -------------------------------------
  const openings = [];
  for (const role of roles) {
    const { ok, answer, invocation } = await callJson(provider, buildDebateOpening(role, context), {
      timeoutMs,
      caseId: caseDef.case_id,
      algoId: meta.id,
      tag: `debate.r1.${role.id}`,
      onEvent,
    });
    invocations.push(invocation);
    openings.push({ id: role.id, round: 1, ok, answer: answer || { top3: [], reasoning: '(no parseable reply)' } });
  }

  // ---- round 2: rebuttals -------------------------------------------------
  const rebuttals = [];
  for (const role of roles) {
    const others = openings.filter((o) => o.id !== role.id);
    const { ok, answer, invocation } = await callJson(
      provider,
      buildDebateRebuttal(role, context, others),
      { timeoutMs, caseId: caseDef.case_id, algoId: meta.id, tag: `debate.r2.${role.id}`, onEvent },
    );
    invocations.push(invocation);
    rebuttals.push({ id: role.id, round: 2, ok, answer: answer || { top3: [], reasoning: '(no parseable reply)' } });
  }

  // ---- adjudication -------------------------------------------------------
  const { ok: judgeOk, answer: judgeAnswer, invocation: judgeInv } = await callJson(
    provider,
    buildDebateJudge(context, [...openings, ...rebuttals]),
    { timeoutMs, caseId: caseDef.case_id, algoId: meta.id, tag: 'debate.judge', onEvent },
  );
  invocations.push(judgeInv);

  const trajectory = archiveAnswer(caseDef.case_id, `${meta.id}.trajectory`, {
    case_id: caseDef.case_id,
    algorithm: meta.id,
    provider: provider.id,
    model: provider.model || provider.id,
    openings,
    rebuttals,
    judge: judgeAnswer,
    invocations: invocations.map((i) => ({ tag: i.tag, ok: i.ok, seconds: i.seconds, error: i.error })),
    archived_at: new Date().toISOString(),
  });

  const succeeded = invocations.filter((i) => i.ok).length;
  if (!judgeOk || !judgeAnswer) {
    return {
      status: 'error',
      top3: [],
      verdict: null,
      reasoning: `The debate chair produced no parseable verdict (${succeeded}/${invocations.length} panel calls succeeded). No answer is reported.`,
      invocations,
      debate: { openings, rebuttals },
      trajectory,
      runtime_ms: Date.now() - t0,
    };
  }

  const norm = normalizeAnswer(judgeAnswer, { caseDef });
  return {
    status: 'executed',
    ...norm,
    invocations,
    debate: { openings, rebuttals, adjudication: judgeAnswer },
    panel_calls_ok: `${succeeded}/${invocations.length}`,
    trajectory,
    prompt_source: promptSource(caseDef.case_id),
    regime: 'debate',
    runtime_ms: Date.now() - t0,
  };
}
