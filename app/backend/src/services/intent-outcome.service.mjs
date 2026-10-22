// Intent outcome — run-level score/verdict derived from the run's OWN artifacts.
//
// Specialist runs (stability / quick-screen / DOE / experience / optimizer) do
// not go through the deep-diagnosis Judge step, so `report.md` carries no
// `Judge Score:` line. Their real outcome lives in the skill's JSON artifacts.
// This module is the single place that maps those artifacts to the run-level
// (score, verdict) pair shown in History and returned by the external API.
//
// Two call paths use it:
//   * write-time — the completion handler stores the derived pair;
//   * read-time  — terminal runs completed before this contract existed (or
//                  orphaned by a crash) are enriched on read, never overwritten.
import { existsSync, readFileSync } from 'fs';
import { isAbsolute, join, resolve } from 'path';

import { PROJECT_ROOT } from '../../../../config/loader.mjs';

const TERMINAL = new Set(['completed', 'failed', 'stopped', 'interrupted', 'expired']);

const EMPTY = Object.freeze({ score: null, verdict: null, source: null });

function readJson(absPath) {
  try {
    if (!absPath || !existsSync(absPath)) return null;
    return JSON.parse(readFileSync(absPath, 'utf-8'));
  } catch {
    return null;
  }
}

function asNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function parts(...values) {
  return values
    .map((v) => (v === null || v === undefined ? '' : String(v).trim()))
    .filter(Boolean)
    .join(' · ');
}

function countOf(list) {
  return Array.isArray(list) ? list.length : null;
}

/**
 * Extract the run-level outcome from a run directory for one intent.
 * Returns `{ score, verdict, source }`; missing/malformed artifacts yield nulls.
 * `source` names the artifact field used, for auditability.
 */
export function extractIntentOutcome(runDir, analysisIntent) {
  if (!runDir) return { ...EMPTY };
  const dir = isAbsolute(runDir) ? runDir : resolve(PROJECT_ROOT, runDir);
  const intent = String(analysisIntent || 'deep-diagnosis');

  if (intent === 'stability-report') {
    const rel = 'line_report/stability_report.json';
    const doc = readJson(join(dir, rel));
    const c = doc?.conclusion;
    if (!c || typeof c !== 'object') return { ...EMPTY };
    const score = asNumber(c.score);
    const verdict = c.grade ? parts(c.grade, c.label) : (c.label || null);
    if (score === null && !verdict) return { ...EMPTY };
    return { score, verdict, source: `${rel}#conclusion` };
  }

  if (intent === 'quick-screen') {
    const rel = 'sentinel/alert.json';
    const doc = readJson(join(dir, rel));
    if (!doc || typeof doc !== 'object') return { ...EMPTY };
    const status = typeof doc.status === 'string' ? doc.status : null;
    if (!status) return { ...EMPTY };
    const n = countOf(doc.alerts);
    return {
      score: null,
      verdict: parts(status, n === null ? null : `${n} alerts`),
      source: `${rel}#status`,
    };
  }

  if (intent === 'doe-analysis') {
    const rel = 'conclusions/doe_conclusion.json';
    const doc = readJson(join(dir, rel));
    if (!doc || typeof doc !== 'object') return { ...EMPTY };
    // DOE's artifact grades evidence, it does not score 0-100: inventing a
    // numeric score here would be dishonest, so only the verdict is derived.
    const verdict = parts(doc.evidence_grade, doc.design_type);
    if (!verdict) return { ...EMPTY };
    return { score: null, verdict, source: `${rel}#evidence_grade` };
  }

  if (intent === 'experience-mining') {
    const rel = 'conclusions/recommendation.json';
    const doc = readJson(join(dir, rel));
    if (!doc || typeof doc !== 'object') return { ...EMPTY };
    const status = typeof doc.recommendation_status === 'string' ? doc.recommendation_status : null;
    if (!status) return { ...EMPTY };
    const n = countOf(doc.playbooks);
    return {
      score: null,
      verdict: parts(status, n === null ? null : `${n} ${n === 1 ? 'playbook' : 'playbooks'}`),
      source: `${rel}#recommendation_status`,
    };
  }

  if (intent === 'optimizer-campaign') {
    const rel = '01_state/optimizer_state.json';
    const doc = readJson(join(dir, rel));
    if (!doc || typeof doc !== 'object') return { ...EMPTY };
    const phase = typeof doc.phase === 'string' ? doc.phase : null;
    if (!phase) return { ...EMPTY };
    const round = asNumber(doc.round_count);
    return {
      score: null,
      verdict: parts(phase, round === null ? null : `round ${round}`),
      source: `${rel}#phase`,
    };
  }

  // deep-diagnosis keeps its existing Judge Score extraction in the caller.
  return { ...EMPTY };
}

const outcomeCache = new Map();
const CACHE_MAX = 1000;

/**
 * Derive an outcome for a persisted run ONLY when the row has no stored
 * outcome. Existing values always win; live/non-terminal runs are skipped.
 */
export function deriveRunOutcome(run) {
  if (!run || !run.workspace_path) return { ...EMPTY };
  if (!TERMINAL.has(run.status)) return { ...EMPTY };
  if (run.score != null || run.judge_verdict != null) return { ...EMPTY };
  const intent = run.analysis_intent || 'deep-diagnosis';
  if (intent === 'deep-diagnosis') return { ...EMPTY };

  const cached = outcomeCache.get(run.run_id);
  if (cached) return cached;

  const outcome = extractIntentOutcome(run.workspace_path, intent);
  if (outcome.score !== null || outcome.verdict) {
    if (outcomeCache.size >= CACHE_MAX) outcomeCache.clear();
    outcomeCache.set(run.run_id, outcome);
  }
  return outcome;
}

/** Shallow copy with artifact-derived outcome filled in when the row is empty. */
export function enrichRunOutcome(run) {
  if (!run) return run;
  const derived = deriveRunOutcome(run);
  if (derived.score === null && !derived.verdict) return run;
  return {
    ...run,
    score: run.score == null ? derived.score : run.score,
    judge_verdict: run.judge_verdict == null ? derived.verdict : run.judge_verdict,
    outcome_source: derived.source,
  };
}
