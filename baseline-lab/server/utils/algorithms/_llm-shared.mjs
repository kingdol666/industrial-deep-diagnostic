// Shared scaffolding for LLM comparator algorithms.
//
// Guarantees enforced here:
//   * NO FABRICATION — a failed or unavailable call yields `status`
//     SKIPPED_NO_PROVIDER / ERROR with empty top3. Nothing is ever invented to
//     fill a gap. (docs/benchmark/reproduction-guide.md §10 red line.)
//   * PROVENANCE — every call records provider, model, latency and the RAW
//     reply, archived under results/answers/<case>/<algorithm>.<n>.json so any
//     number in the UI can be traced back to the exact bytes the model emitted.
//   * DETERMINISM DISCLOSURE — LLM calls are not deterministic; `meta` says so
//     and the UI repeats it next to every LLM row.

import fs from 'node:fs';
import path from 'node:path';
import { RESULTS_DIR, ensureDir, loadBrief } from '../paths.mjs';
import { resolveProvider, chat, extractJson } from '../llm/provider.mjs';
import { buildDirectPrompt, buildCotPrompt } from '../llm/prompts.mjs';

export const ANSWERS_DIR = path.join(RESULTS_DIR, 'answers');

/** Archive one raw model reply. Returns the relative path for provenance. */
export function archiveAnswer(caseId, algoId, payload) {
  const dir = path.join(ANSWERS_DIR, caseId);
  ensureDir(dir);
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const file = path.join(dir, `${algoId}.${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(payload, null, 2), 'utf8');
  return path.relative(RESULTS_DIR, file).replace(/\\/g, '/');
}

/** Provider plumbing shared by every LLM algorithm. */
export function llmContext(cfg = {}) {
  let provider = null;
  let providerError = null;
  try {
    provider = resolveProvider(cfg);
  } catch (err) {
    providerError = String(err && err.message ? err.message : err);
  }
  return { provider, providerError };
}

/** Standard "we could not run" result — never contains invented answers. */
export function notRun(reason, extra = {}) {
  return {
    status: reason, // 'skipped_no_provider' | 'error'
    top3: [],
    verdict: null,
    reasoning:
      reason === 'skipped_no_provider'
        ? 'No LLM provider is configured, so this comparator was NOT executed. No answer is reported — fabricating one would violate the benchmark truthfulness contract.'
        : `Execution failed (${extra.error || 'unknown error'}). No answer is reported.`,
    invocations: [],
    ...extra,
  };
}

const JSON_INSTRUCTION =
  'Reply with STRICT JSON only. No markdown fences, no commentary before or after the JSON object.';

/**
 * Run a single prompt through the provider and parse the strict JSON reply.
 * Returns { ok, answer, invocation }.
 */
export async function callJson(provider, prompt, { timeoutMs = 300000, caseId, algoId, tag } = {}) {
  const r = await chat(provider, { prompt: `${prompt}\n\n${JSON_INSTRUCTION}`, timeoutMs });
  const parsed = r.ok ? extractJson(r.text) : null;
  const invocation = {
    tag: tag || algoId,
    provider: r.provider,
    model: r.model,
    ok: r.ok,
    seconds: Number((r.seconds || 0).toFixed(2)),
    fabricated: Boolean(r.fabricated),
    error: r.error || null,
    parsed_ok: Boolean(parsed),
    raw_head: String(r.text || '').slice(0, 1200),
  };
  if (caseId && algoId) {
    invocation.archived = archiveAnswer(caseId, algoId, {
      case_id: caseId,
      algorithm: algoId,
      tag: invocation.tag,
      prompt,
      provider: r.provider,
      model: r.model,
      ok: r.ok,
      error: r.error || null,
      seconds: invocation.seconds,
      raw_reply: String(r.text || ''),
      parsed,
      archived_at: new Date().toISOString(),
    });
  }
  return { ok: r.ok, answer: parsed, invocation, raw: String(r.text || '') };
}

/** Normalise a parsed model answer into the lab's result shape. */
export function normalizeAnswer(answer, { caseDef } = {}) {
  const top3 = Array.isArray(answer?.top3) ? answer.top3.map(String).filter(Boolean) : [];
  let verdict = null;
  if (answer && typeof answer.verdict === 'string') {
    verdict = answer.verdict.toLowerCase() === 'normal' ? 'normal' : 'fault';
  } else if (top3.length) {
    verdict = caseDef?.control ? 'fault' : 'fault';
  }
  return { top3, verdict, reasoning: String(answer?.reasoning || '') };
}

/** Build the prompt for a named regime. */
export function promptForRegime(regime, caseId, matrix) {
  if (regime === 'cot') return buildCotPrompt(caseId, matrix);
  return buildDirectPrompt(caseId, matrix, regime === 'with_candidates' ? 'with_candidates' : 'no_candidates');
}

/** Convenience: does a blind brief exist (used for prompt-source disclosure)? */
export function promptSource(caseId) {
  return loadBrief(caseId) ? 'archived blind brief (results/benchmark/briefs)' : 'computed anomaly digest';
}
