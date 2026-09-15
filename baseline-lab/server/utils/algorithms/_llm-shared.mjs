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
import { resolveProvider, chat, extractJson, modelLabel } from '../llm/provider.mjs';
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
 *
 * `onEvent` (optional) receives lifecycle callbacks so a caller can stream the
 * diagnosis live. Without it a long model call is an opaque 40-80 second gap —
 * which is exactly what makes a real diagnosis look like a frozen script.
 */
export async function callJson(provider, prompt, { timeoutMs = 300000, caseId, algoId, tag, onEvent = null } = {}) {
  const emit = (type, data) => { try { onEvent?.(type, data); } catch { /* a listener must never break the run */ } };
  emit('llm_call_start', {
    tag: tag || algoId,
    algoId,
    provider: provider?.id,
    // Same honest label the completion returns — an unconfigured CLI harness must
    // not have its provider id presented as a model name.
    model: provider ? modelLabel(provider) : null,
    prompt_chars: prompt?.length || 0,
  });

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
  emit('llm_call_done', {
    tag: invocation.tag,
    algoId,
    ok: r.ok,
    model: r.model,
    seconds: invocation.seconds,
    error: invocation.error,
    archived: invocation.archived || null,
    // A clipped view of the model's OWN words, so the UI can show the reply
    // arriving rather than only a spinner.
    reply_head: String(r.text || '').slice(0, 600),
  });
  return { ok: r.ok, answer: parsed, invocation, raw: String(r.text || '') };
}

/**
 * Render one hypothesis entry as a readable string.
 *
 * Models sometimes return objects instead of strings
 * (`"top3": [{"cause": "...", "confidence": 0.8}]`). `String(obj)` yields
 * "[object Object]", which is what the UI then displays — a real run did exactly
 * that. Pull the descriptive field out instead.
 */
function hypothesisToString(v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'string') return v.trim();
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  if (typeof v === 'object') {
    const pick = firstString(v, [
      'cause', 'root_cause', 'name', 'description', 'label', 'hypothesis',
      'fault', 'idv', 'mechanism', 'finding', 'title', 'text', 'id',
    ]);
    if (pick) return pick;
    // Last resort: a compact single-line JSON, never "[object Object]".
    try { return JSON.stringify(v).slice(0, 300); } catch { return ''; }
  }
  return String(v);
}

/** First present value from `keys` that is a non-empty string. */
function firstString(obj, keys) {
  for (const k of keys) {
    const v = obj?.[k];
    if (typeof v === 'string' && v.trim()) return v.trim();
  }
  return '';
}

/** First present value from `keys` that is a non-empty array. */
function firstArray(obj, keys) {
  for (const k of keys) {
    const v = obj?.[k];
    if (Array.isArray(v) && v.length) return v.map(hypothesisToString).filter(Boolean);
  }
  return [];
}

/**
 * Normalise a parsed model answer into the lab's result shape.
 *
 * SCHEMA TOLERANCE IS DELIBERATE. Models do not always honour the requested
 * JSON keys: a real ReAct run returned
 *   {"finding": "...", "confidence": "medium", "recommended_action": "..."}
 * instead of {"top3": [...], "reasoning": "..."}. A strict reader reduced a
 * substantive, correct diagnosis to an empty answer — the analysis was thrown
 * away over key naming. We therefore accept the common synonyms, and record
 * `schema_conformance` so a deviation stays VISIBLE instead of being silently
 * smoothed over.
 */
export function normalizeAnswer(answer, { caseDef } = {}) {
  const a = answer && typeof answer === 'object' ? answer : {};

  let top3 = firstArray(a, ['top3', 'top_candidates', 'candidates', 'root_causes', 'root_cause_candidates', 'hypotheses', 'causes', 'ranked_causes']);
  let reasoning = firstString(a, ['reasoning', 'finding', 'analysis', 'explanation', 'rationale', 'conclusion', 'assessment', 'summary']);

  // Callers may wrap the payload (e.g. {"result": {...}} or {"answer": {...}}).
  for (const wrap of ['result', 'answer', 'output', 'response']) {
    if (a[wrap] && typeof a[wrap] === 'object') {
      const inner = a[wrap];
      if (!top3.length) top3 = firstArray(inner, ['top3', 'top_candidates', 'candidates', 'root_causes', 'hypotheses', 'causes']);
      if (!reasoning) reasoning = firstString(inner, ['reasoning', 'finding', 'analysis', 'explanation', 'rationale', 'conclusion', 'summary']);
    }
  }

  // Verdict: honour an explicit one; otherwise a substantive cause implies fault.
  let verdict = null;
  const rawVerdict = firstString(a, ['verdict', 'status', 'conclusion_type']).toLowerCase();
  if (rawVerdict) verdict = rawVerdict.includes('normal') || rawVerdict.includes('no_fault') ? 'normal' : 'fault';

  // A model that states a cause but does not wrap it in a list has still named a
  // cause — take its own wording as the single ranked hypothesis rather than
  // discarding it. `recommended_action` is explicitly NOT treated as a cause.
  if (!top3.length && reasoning && verdict !== 'normal') {
    const firstSentence = reasoning.split(/(?<=[.。!?！？])\s+/)[0].slice(0, 300);
    top3 = [firstSentence || reasoning.slice(0, 300)];
  }
  if (!verdict) verdict = top3.length ? 'fault' : (rawVerdict ? 'normal' : null);

  const recommendation = firstString(a, ['recommended_action', 'next_step', 'recommendation']);
  if (recommendation) {
    reasoning = reasoning ? `${reasoning}\n\nRecommended action: ${recommendation}` : `Recommended action: ${recommendation}`;
  }

  const canonical = Array.isArray(a.top3) && typeof a.reasoning === 'string';
  return {
    top3,
    verdict,
    reasoning,
    confidence: firstString(a, ['confidence']) || null,
    schema_conformance: canonical
      ? 'canonical'
      : (top3.length || reasoning ? 'coerced' : 'empty'),
    schema_keys_seen: Object.keys(a).slice(0, 12),
  };
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
