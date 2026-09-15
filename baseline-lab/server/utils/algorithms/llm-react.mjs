// llm-react — ReAct-style tool-using single agent baseline.
//
// docs/publication-strategy-report.md §5.2 lists "ReAct + 工具调用" as a
// baseline arm. This is a RUNNABLE implementation: the model may call tools that
// compute real statistics over the actual case record, observes the results, and
// only then commits to a verdict.
//
// EVIDENCE INTEGRITY
// ------------------
// A ReAct agent that writes its own `OBSERVATION:` lines is not using tools, it
// is inventing data — and a real run did exactly that: it called two tools that
// do not exist (`column_trace`, `trend`) and fabricated their output, including
// a plausible-looking `{"slope":0.00093,"p_value":0.0001,"r2":0.83}`, then
// answered from that fabrication. Reporting such an answer as a diagnosis would
// be worse than reporting nothing.
//
// This module therefore:
//   1. detects self-authored OBSERVATION lines and counts them as violations;
//   2. STRIPS them from the transcript forwarded to the model, so a fabrication
//      cannot be carried forward as if it were evidence;
//   3. corrects the model and re-prompts rather than silently proceeding;
//   4. records `evidence_integrity` on the result, and refuses to present an
//      answer as grounded when it is not.
//
// Tools the model reaches for that turn out to be genuinely useful are
// implemented for real (see `trend`), so the intent is served by computation
// instead of by hallucination.

import { llmContext, notRun, callJson, normalizeAnswer, promptSource, archiveAnswer } from './_llm-shared.mjs';
import { buildReactPrompt } from '../llm/prompts.mjs';
import { mean, stdev, pearson, betai } from '../linalg.mjs';
import { chat, extractJson, modelLabel } from '../llm/provider.mjs';

export const meta = {
  id: 'llm-react',
  label: 'ReAct 工具调用代理',
  short: 'ReAct',
  family: 'llm',
  kind: 'llm',
  deterministic: false,
  requiresProvider: true,
  needsReference: false,
  regimes: ['react'],
  description:
    'Single tool-using agent (ReAct loop). The model may call column_stats / top_changed_columns / correlate / window_compare / trend up to 6 times; each observation is computed from the real record, then the agent commits to a ranked root-cause verdict. Self-authored observations are detected and stripped as protocol violations.',
  provenance: {
    basis: 'yao2023react',
    repo: null,
    note: 'ReAct arm of the comparison matrix, with real data tools; full trajectory archived including protocol violations.',
  },
};

const MAX_STEPS = 6;

function col(matrix, name) {
  const j = matrix.colNames.indexOf(name);
  if (j < 0) return null;
  return { j, values: matrix.X.map((r) => r[j]) };
}

/** Ordinary least squares slope with a t-test p-value, for the `trend` tool. */
function linearTrend(values) {
  const n = values.length;
  const xs = Array.from({ length: n }, (_, i) => i);
  const mx = mean(xs), my = mean(values);
  let sxx = 0, sxy = 0;
  for (let i = 0; i < n; i++) { sxx += (xs[i] - mx) ** 2; sxy += (xs[i] - mx) * (values[i] - my); }
  if (sxx === 0) return { slope: 0, intercept: my, r2: 0, p_value: 1, n };
  const slope = sxy / sxx;
  const intercept = my - slope * mx;
  let ssRes = 0, ssTot = 0;
  for (let i = 0; i < n; i++) {
    const pred = intercept + slope * xs[i];
    ssRes += (values[i] - pred) ** 2;
    ssTot += (values[i] - my) ** 2;
  }
  const r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;
  // Two-sided p-value from the t distribution. A PERFECT fit (ssRes = 0) is
  // infinitely significant, not insignificant: the earlier guard `se > 0` mapped
  // it to t = 0 and therefore p = 1, inverting the meaning of an exact trend.
  const df = Math.max(1, n - 2);
  let p;
  if (se2IsZero(ssRes)) {
    p = slope === 0 ? 1 : 0;
  } else if (sxx <= 0) {
    p = 1;
  } else {
    const se = Math.sqrt((ssRes / df) / sxx);
    const t = se > 0 ? Math.abs(slope / se) : Infinity;
    p = Number.isFinite(t) ? Math.max(1e-300, 2 * (1 - studentTCdf(t, df))) : 0;
  }
  const se = sxx > 0 ? Math.sqrt((ssRes / df) / sxx) : 0;
  return { slope, intercept, r2, p_value: p, se, df, n };
}

/** True when the residual sum of squares is numerically zero. */
function se2IsZero(ssRes) {
  return !(ssRes > 1e-300);
}

/** Student-t CDF via the regularized incomplete beta (same primitive as fe-official). */
function studentTCdf(t, df) {
  const x = df / (df + t * t);
  const ib = betai(df / 2, 0.5, x);
  return t >= 0 ? 1 - ib / 2 : ib / 2;
}

/** Tool implementations — every number comes from the actual record. */
export function makeToolbox(matrix) {
  const cols = matrix.colNames;
  const n = matrix.n;

  function series(name) {
    const c = col(matrix, name);
    if (!c) return null;
    return c.values;
  }
  const unknown = (name) => ({ error: `unknown column '${name}'. Available: ${cols.slice(0, 12).join(', ')}${cols.length > 12 ? ' …' : ''}` });

  function columnStats(name, fromRow, toRow) {
    const v = series(name);
    if (!v) return unknown(name);
    // An optional window is honoured rather than rejected: an earlier version
    // rejected it, and the model responded by inventing its own result.
    const f = Number.isFinite(Number(fromRow)) ? Math.max(0, Number(fromRow)) : 0;
    const t = Number.isFinite(Number(toRow)) ? Math.min(n, Number(toRow)) : n;
    if (!(t > f)) return { error: `invalid window ${fromRow}..${toRow} for a record of ${n} rows` };
    const win = v.slice(f, t);
    const half = Math.floor(win.length / 2);
    return {
      column: name,
      window: [f, t],
      rows: win.length,
      mean: Number(mean(win).toFixed(5)),
      std: Number(stdev(win).toFixed(5)),
      min: Number(Math.min(...win).toFixed(5)),
      max: Number(Math.max(...win).toFixed(5)),
      first_half_mean: Number(mean(win.slice(0, half)).toFixed(5)),
      second_half_mean: Number(mean(win.slice(half)).toFixed(5)),
      half_shift: Number((mean(win.slice(half)) - mean(win.slice(0, half))).toFixed(5)),
    };
  }

  function topChangedColumns(k = 5) {
    const half = Math.floor(n / 2);
    const scored = cols.map((name, j) => {
      const v = matrix.X.map((r) => r[j]);
      const sd = stdev(v) || 1e-12;
      return { column: name, half_shift: (mean(v.slice(half)) - mean(v.slice(0, half))) / sd };
    });
    scored.sort((x, y) => Math.abs(y.half_shift) - Math.abs(x.half_shift));
    const kk = Math.min(Math.max(1, Number(k) || 5), cols.length);
    return {
      k: kk,
      ranked: scored.slice(0, kk).map((s) => ({
        column: s.column,
        normalized_shift_sigma: Number(s.half_shift.toFixed(4)),
      })),
    };
  }

  function correlate(a, b) {
    const va = series(a), vb = series(b);
    if (!va || !vb) return { error: `unknown column(s): ${!va ? a : ''} ${!vb ? b : ''}`.trim() };
    return { a, b, pearson_r: Number(pearson(va, vb).toFixed(5)), n };
  }

  function windowCompare(name, fromRow, toRow) {
    const v = series(name);
    if (!v) return unknown(name);
    const f = Math.max(0, Number(fromRow) || 0);
    const t = Math.min(n, Number(toRow) || n);
    if (!(t > f)) return { error: `invalid range ${fromRow}..${toRow} for n=${n}` };
    const w = v.slice(f, t);
    return {
      column: name, from_row: f, to_row: t, rows: w.length,
      mean: Number(mean(w).toFixed(5)),
      std: Number(stdev(w).toFixed(5)),
      min: Number(Math.min(...w).toFixed(5)),
      max: Number(Math.max(...w).toFixed(5)),
    };
  }

  // Implemented for real because the model repeatedly asked for it. Serving the
  // intent with computation is strictly better than letting it fabricate.
  function trend(name, fromRow, toRow) {
    const v = series(name);
    if (!v) return unknown(name);
    const f = Math.max(0, Number(fromRow) || 0);
    const t = Math.min(n, Number(toRow) || n);
    if (!(t - f >= 3)) return { error: `need at least 3 rows for a trend; got ${t - f}` };
    const r = linearTrend(v.slice(f, t));
    return {
      column: name, window: [f, t], rows: r.n,
      slope_per_row: Number(r.slope.toExponential(4)),
      r2: Number(r.r2.toFixed(4)),
      p_value: Number(r.p_value.toExponential(3)),
      direction: r.slope > 0 ? 'increasing' : r.slope < 0 ? 'decreasing' : 'flat',
      // NOTE: not `significant_at_0.05` — a dot is illegal in an identifier, and
      // the module failed to parse because of it.
      significant_at_5pct: r.p_value < 0.05,
    };
  }

  return { column_stats: columnStats, top_changed_columns: topChangedColumns, correlate, window_compare: windowCompare, trend };
}

export const TOOL_NAMES = ['column_stats', 'top_changed_columns', 'correlate', 'window_compare', 'trend'];

/**
 * Parse one model turn.
 *
 * Also reports whether the model wrote its OWN `OBSERVATION:`. That is the
 * signature of a fabricated result and must never be treated as evidence.
 *
 * DETECTION RULE — the model writes the fabrication INLINE, not on its own line:
 *     ACTION: trend(XMEAS_34, 120, 200) OBSERVATION: {"slope":0.00093,...}
 * so an anchored `^OBSERVATION:` test misses the real cases (it did). But flagging
 * every occurrence of the word would false-positive on prose such as
 * "Thinking about the OBSERVATION: field semantics". The discriminator is that a
 * fabricated observation is attached to a tool call / final answer, or is
 * followed by machine-readable JSON — neither of which holds for prose.
 */
export function parseTurn(text) {
  const s = String(text);
  const hasObs = /OBSERVATION\s*:/i.test(s);
  const obsFollowedByData = /OBSERVATION\s*:\s*[{["\d-]/i.test(s);
  const hasActionOrFinal = /(^|\n|\s)(ACTION|FINAL)\s*:/i.test(s);
  const fabricated = hasObs && (hasActionOrFinal || obsFollowedByData);

  // Strip every fabricated observation, from the marker up to the next
  // ACTION/FINAL/THOUGHT marker or the end of the turn.
  const stripped = fabricated
    ? s.replace(/OBSERVATION\s*:[\s\S]*?(?=(?:^|\n|\s)(?:ACTION|FINAL|THOUGHT)\s*:|$)/gi, ' ')
    : s;

  const finalMatch = stripped.match(/FINAL:\s*([\s\S]*)$/);
  if (finalMatch) {
    const parsed = extractJson(finalMatch[1]);
    if (parsed) return { kind: 'final', answer: parsed, selfAuthoredObservation: fabricated, cleaned: stripped };
  }
  const action = stripped.match(/ACTION:\s*([a-z_]+)\s*\(([^)]*)\)/i);
  if (action) {
    return {
      kind: 'action',
      tool: action[1],
      args: action[2].split(',').map((x) => x.trim().replace(/^["']|["']$/g, '')).filter((x) => x !== ''),
      selfAuthoredObservation: fabricated,
      cleaned: stripped,
    };
  }
  return { kind: 'none', selfAuthoredObservation: fabricated, cleaned: stripped };
}

export async function run(ctx, { config = {}, onEvent = null } = {}) {
  const t0 = Date.now();
  const { caseDef, matrix } = ctx;

  const { provider, providerError } = llmContext(config);
  if (providerError) return { ...notRun('error', { error: providerError }), runtime_ms: Date.now() - t0 };
  if (!provider) return { ...notRun('skipped_no_provider'), runtime_ms: Date.now() - t0 };

  const toolbox = makeToolbox(matrix);
  const timeoutMs = config.llmTimeoutMs || 300000;
  const maxSteps = config.reactMaxSteps || MAX_STEPS;
  // A ReAct step is ONE turn, not a full answer: giving every step the whole
  // 5-minute budget let a 6-step run occupy half an hour. But a flat short cap
  // fails step 0, which carries the full brief plus the tool contract and is
  // legitimately the slowest turn. So: a longer first step, tighter later ones,
  // and a hard budget on the whole algorithm.
  const firstStepTimeoutMs = config.reactFirstStepTimeoutMs || Math.min(timeoutMs, 240000);
  const stepTimeoutMs = config.reactStepTimeoutMs || Math.min(timeoutMs, 150000);
  const totalBudgetMs = config.reactTotalBudgetMs || Math.min(timeoutMs * 2, 600000);
  const runDeadline = Date.now() + totalBudgetMs;

  const transcript = [];
  const invocations = [];
  const toolLog = [];
  const violations = [];
  let finalAnswer = null;
  let groundedInRealTool = false;

  let turnPrompt = buildReactPrompt(caseDef.case_id, matrix);
  let correction = '';

  for (let step = 0; step <= maxSteps; step++) {
    if (Date.now() > runDeadline) {
      transcript.push({ step, role: 'system', text: `aborted: exceeded this algorithm's ${Math.round(totalBudgetMs / 1000)}s budget` });
      break;
    }
    onEvent?.('llm_call_start', { tag: `react.step${step}`, algoId: meta.id, provider: provider.id, model: modelLabel(provider), prompt_chars: turnPrompt.length });
    const r = await chat(provider, { prompt: turnPrompt + correction, timeoutMs: step === 0 ? firstStepTimeoutMs : stepTimeoutMs });
    correction = '';

    const archivedStep = r.ok
      ? archiveAnswer(caseDef.case_id, `${meta.id}.step${step}`, {
          case_id: caseDef.case_id,
          algorithm: meta.id,
          tag: `react.step${step}`,
          prompt: turnPrompt + correction,
          provider: r.provider,
          model: r.model,
          ok: r.ok,
          seconds: Number((r.seconds || 0).toFixed(2)),
          raw_reply: String(r.text || ''),
          archived_at: new Date().toISOString(),
        })
      : null;
    invocations.push({
      tag: `react.step${step}`,
      provider: r.provider,
      model: r.model,
      ok: r.ok,
      seconds: Number((r.seconds || 0).toFixed(2)),
      error: r.error || null,
      archived: archivedStep,
      raw_head: String(r.text || '').slice(0, 1500),
    });
    onEvent?.('llm_call_done', {
      tag: `react.step${step}`, algoId: meta.id, ok: r.ok, model: r.model,
      seconds: Number((r.seconds || 0).toFixed(2)), error: r.error || null,
      archived: archivedStep, reply_head: String(r.text || '').slice(0, 600),
    });
    if (!r.ok) break;

    const turn = parseTurn(r.text);

    if (turn.selfAuthoredObservation) {
      violations.push({ step, tool: turn.tool || null, detail: 'model wrote its own OBSERVATION line (fabricated tool output)' });
      onEvent?.('protocol_violation', {
        algorithm: meta.id, step, kind: 'self_authored_observation',
        detail: 'the model wrote its own OBSERVATION — that text was stripped and NOT treated as evidence',
      });
    }

    // Record the CLEANED text only: a fabrication must not become transcript.
    transcript.push({ step, role: 'assistant', text: turn.cleaned, selfAuthoredObservation: turn.selfAuthoredObservation });

    if (turn.kind === 'final') {
      finalAnswer = turn.answer;
      // The answer is only grounded if the agent actually received at least one
      // real observation and did not fabricate any.
      groundedInRealTool = toolLog.some((t) => t.observation && !t.observation.error) && violations.length === 0;
      break;
    }

    if (turn.kind !== 'action') {
      const parsed = extractJson(turn.cleaned);
      if (parsed) {
        finalAnswer = parsed;
        groundedInRealTool = false;
        break;
      }
      correction = '\n\nYour reply contained neither "ACTION: ..." nor "FINAL: {...}". '
        + 'Remember: you must NOT write OBSERVATION lines — the system supplies them. '
        + `Available tools are exactly: ${TOOL_NAMES.join(', ')}. Emit one ACTION now, or FINAL with the required keys.`;
      continue;
    }

    const fn = toolbox[turn.tool];
    let observation;
    if (!fn) {
      observation = {
        error: `unknown tool '${turn.tool}'. Available tools are exactly: ${TOOL_NAMES.join(', ')}. `
          + 'Do not invent tools or their output.',
      };
      violations.push({ step, tool: turn.tool, detail: `called a tool that does not exist: ${turn.tool}` });
      onEvent?.('protocol_violation', {
        algorithm: meta.id, step, kind: 'unknown_tool', tool: turn.tool,
        detail: `'${turn.tool}' is not a real tool; the corrected list was sent back`,
      });
    } else {
      try {
        observation = fn(...turn.args);
      } catch (err) {
        observation = { error: `tool threw: ${String(err && err.message ? err.message : err)}` };
      }
    }
    toolLog.push({ step, tool: turn.tool, args: turn.args, observation, recognised: Boolean(fn) });
    transcript.push({ step, role: 'tool', tool: turn.tool, args: turn.args, observation });

    correction = '';
    turnPrompt = `${turn.cleaned}\nOBSERVATION: ${JSON.stringify(observation)}\n\n`
      + `Continue: emit another ACTION line using one of ${TOOL_NAMES.join(', ')}, or FINAL: {...} if you have enough evidence.`;
  }

  const cleanTranscript = transcript;

  // ---- evidence integrity -------------------------------------------------
  const unknownToolCalls = violations.filter((v) => v.kind === 'unknown_tool').length;
  const fabricatedObservations = violations.filter((v) => v.kind === 'self_authored_observation').length;
  const evidenceIntegrity = !violations.length && groundedInRealTool
    ? 'grounded'
    : violations.length ? 'contaminated' : 'unverified';

  const integrityNote = {
    grounded: `Answer grounded in ${toolLog.filter((t) => t.recognised).length} real tool observation(s); no protocol violations.`,
    unverified: 'The agent produced an answer without a usable real tool observation, so its evidence base is unverified.',
    contaminated:
      `CONTAMINATED: the agent committed ${violations.length} protocol violation(s) `
      + `(${fabricatedObservations} self-authored OBSERVATION line(s), ${unknownToolCalls} call(s) to non-existent tool(s)). `
      + 'Fabricated observations were stripped and are NOT evidence. Treat any number this answer cites that does not '
      + 'appear in the recorded tool_calls as unreliable.',
  }[evidenceIntegrity];

  const trajectory = archiveAnswer(caseDef.case_id, `${meta.id}.trajectory`, {
    case_id: caseDef.case_id,
    algorithm: meta.id,
    provider: provider.id,
    model: modelLabel(provider),
    steps: toolLog.length,
    transcript: cleanTranscript,
    tool_calls: toolLog,
    protocol_violations: violations,
    evidence_integrity: evidenceIntegrity,
    final_answer: finalAnswer,
    invocations: invocations.map((i) => ({ tag: i.tag, ok: i.ok, seconds: i.seconds, error: i.error })),
    archived_at: new Date().toISOString(),
  });

  if (!finalAnswer) {
    return {
      status: 'error',
      top3: [],
      verdict: null,
      reasoning: `The ReAct agent did not converge on a FINAL answer within ${maxSteps} tool steps. No answer is reported.`,
      invocations,
      tool_calls: toolLog,
      protocol_violations: violations,
      evidence_integrity: evidenceIntegrity,
      integrity_note: integrityNote,
      trajectory,
      runtime_ms: Date.now() - t0,
    };
  }

  const norm = normalizeAnswer(finalAnswer, { caseDef });
  if (violations.length) {
    // Surface the contamination in the answer itself, so a reader cannot mistake
    // it for a grounded diagnosis.
    norm.reasoning = `[${integrityNote}]\n\n${norm.reasoning}`;
  }
  return {
    status: 'executed',
    ...norm,
    invocations,
    tool_calls: toolLog,
    tools_used: [...new Set(toolLog.filter((t) => t.recognised).map((t) => t.tool))],
    protocol_violations: violations,
    evidence_integrity: evidenceIntegrity,
    integrity_note: integrityNote,
    trajectory,
    prompt_source: promptSource(caseDef.case_id),
    regime: 'react',
    runtime_ms: Date.now() - t0,
  };
}
