// llm-react — ReAct-style tool-using single agent baseline.
//
// docs/publication-strategy-report.md §5.2 lists "ReAct + 工具调用" as a
// baseline arm. This is a RUNNABLE implementation: the model may call four
// tools that compute real statistics over the actual case record, observes the
// results, and only then commits to a verdict. Tool results are computed from
// the data — the model cannot obtain numbers any other way, and its tool calls
// and observations are archived verbatim so the trajectory is auditable.

import { llmContext, notRun, callJson, normalizeAnswer, promptSource } from './_llm-shared.mjs';
import { buildReactPrompt } from '../llm/prompts.mjs';
import { mean, stdev, pearson } from '../linalg.mjs';
import { chat, extractJson } from '../llm/provider.mjs';

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
    'Single tool-using agent (ReAct loop). The model may call column_stats / top_changed_columns / correlate / window_compare up to 6 times; each observation is computed from the real record, then the agent commits to a ranked root-cause verdict.',
  provenance: {
    basis: ['yao2023react'],
    repo: null,
    note: 'ReAct arm of the comparison matrix, with real data tools; full trajectory archived.',
  },
};

const MAX_STEPS = 6;

function col(matrix, name) {
  const j = matrix.colNames.indexOf(name);
  if (j < 0) return null;
  return { j, values: matrix.X.map((r) => r[j]) };
}

/** Tool implementations — every number comes from the actual record. */
export function makeToolbox(matrix) {
  const cols = matrix.colNames;
  const n = matrix.n;

  function columnStats(name) {
    const c = col(matrix, name);
    if (!c) return { error: `unknown column '${name}'. Available: ${cols.slice(0, 12).join(', ')} ...` };
    const half = Math.floor(n / 2);
    const a = c.values.slice(0, half);
    const b = c.values.slice(half);
    return {
      column: name,
      mean: Number(mean(c.values).toFixed(5)),
      std: Number(stdev(c.values).toFixed(5)),
      min: Number(Math.min(...c.values).toFixed(5)),
      max: Number(Math.max(...c.values).toFixed(5)),
      first_half_mean: Number(mean(a).toFixed(5)),
      second_half_mean: Number(mean(b).toFixed(5)),
      half_shift: Number((mean(b) - mean(a)).toFixed(5)),
    };
  }

  function topChangedColumns(k = 5) {
    const half = Math.floor(n / 2);
    const scored = cols.map((name, j) => {
      const v = matrix.X.map((r) => r[j]);
      const a = v.slice(0, half), b = v.slice(half);
      const sd = stdev(v) || 1e-12;
      return { column: name, half_shift: (mean(b) - mean(a)) / sd };
    });
    scored.sort((x, y) => Math.abs(y.half_shift) - Math.abs(x.half_shift));
    return {
      k: Number(k) || 5,
      ranked: scored.slice(0, Number(k) || 5).map((s) => ({
        column: s.column,
        normalized_shift_sigma: Number(s.half_shift.toFixed(4)),
      })),
    };
  }

  function correlate(a, b) {
    const ca = col(matrix, a), cb = col(matrix, b);
    if (!ca || !cb) return { error: `unknown column(s): ${!ca ? a : ''} ${!cb ? b : ''}`.trim() };
    return { a, b, pearson_r: Number(pearson(ca.values, cb.values).toFixed(5)) };
  }

  function windowCompare(name, fromRow, toRow) {
    const c = col(matrix, name);
    if (!c) return { error: `unknown column '${name}'` };
    const f = Math.max(0, Number(fromRow) || 0);
    const t = Math.min(n, Number(toRow) || n);
    if (!(t > f)) return { error: `invalid range ${fromRow}..${toRow} for n=${n}` };
    const v = c.values.slice(f, t);
    return {
      column: name,
      from_row: f,
      to_row: t,
      rows: v.length,
      mean: Number(mean(v).toFixed(5)),
      std: Number(stdev(v).toFixed(5)),
      min: Number(Math.min(...v).toFixed(5)),
      max: Number(Math.max(...v).toFixed(5)),
    };
  }

  return { column_stats: columnStats, top_changed_columns: topChangedColumns, correlate, window_compare: windowCompare };
}

/** Parse `ACTION: name(args)` / `FINAL: {...}` from a model turn. */
export function parseTurn(text) {
  const finalMatch = String(text).match(/FINAL:\s*([\s\S]*)$/);
  if (finalMatch) {
    const parsed = extractJson(finalMatch[1]);
    if (parsed) return { kind: 'final', answer: parsed };
  }
  const action = String(text).match(/ACTION:\s*([a-z_]+)\s*\(([^)]*)\)/i);
  if (action) {
    return {
      kind: 'action',
      tool: action[1],
      args: action[2].split(',').map((s) => s.trim().replace(/^["']|["']$/g, '')).filter((s) => s !== ''),
    };
  }
  return { kind: 'none' };
}

export async function run(ctx, { config = {} } = {}) {
  const t0 = Date.now();
  const { caseDef, matrix } = ctx;

  const { provider, providerError } = llmContext(config);
  if (providerError) return { ...notRun('error', { error: providerError }), runtime_ms: Date.now() - t0 };
  if (!provider) return { ...notRun('skipped_no_provider'), runtime_ms: Date.now() - t0 };

  const toolbox = makeToolbox(matrix);
  const timeoutMs = config.llmTimeoutMs || 300000;
  const maxSteps = config.reactMaxSteps || MAX_STEPS;

  const transcript = [];
  const invocations = [];
  let finalAnswer = null;

  // Turn 0: the agent receives the brief plus the tool contract.
  let turnPrompt = buildReactPrompt(caseDef.case_id, matrix);
  const toolLog = [];

  for (let step = 0; step <= maxSteps; step++) {
    const r = await chat(provider, { prompt: turnPrompt, timeoutMs });
    invocations.push({
      tag: `react.step${step}`,
      provider: r.provider,
      model: r.model,
      ok: r.ok,
      seconds: Number((r.seconds || 0).toFixed(2)),
      error: r.error || null,
      raw_head: String(r.text || '').slice(0, 1500),
    });
    if (!r.ok) break;

    transcript.push({ step, role: 'assistant', text: r.text });
    const turn = parseTurn(r.text);

    if (turn.kind === 'final') {
      finalAnswer = turn.answer;
      break;
    }
    if (turn.kind !== 'action') {
      // Model produced neither an action nor a final answer; nudge once, then stop.
      const parsed = extractJson(r.text);
      if (parsed) {
        finalAnswer = parsed;
        break;
      }
      turnPrompt = `${r.text}\n\nYour reply contained neither "ACTION: ..." nor "FINAL: {...}". Emit FINAL now as STRICT JSON.`;
      continue;
    }

    const fn = toolbox[turn.tool];
    let observation;
    if (!fn) {
      observation = { error: `unknown tool '${turn.tool}'. Use one of: ${Object.keys(toolbox).join(', ')}` };
    } else {
      try {
        observation = fn(...turn.args);
      } catch (err) {
        observation = { error: `tool threw: ${String(err && err.message ? err.message : err)}` };
      }
    }
    toolLog.push({ step, tool: turn.tool, args: turn.args, observation });
    transcript.push({ step, role: 'tool', tool: turn.tool, args: turn.args, observation });
    turnPrompt = `${r.text}\nOBSERVATION: ${JSON.stringify(observation)}\n\nContinue: emit another ACTION line, or FINAL: {...} if you have enough evidence.`;
  }

  // Archive the full trajectory (auditable tool use).
  const { archiveAnswer } = await import('./_llm-shared.mjs');
  const archived = archiveAnswer(caseDef.case_id, meta.id, {
    case_id: caseDef.case_id,
    algorithm: meta.id,
    provider: provider.id,
    model: provider.model || provider.id,
    steps: toolLog.length,
    transcript,
    tool_calls: toolLog,
    final_answer: finalAnswer,
    invocations,
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
      trajectory: archived,
      runtime_ms: Date.now() - t0,
    };
  }

  const norm = normalizeAnswer(finalAnswer, { caseDef });
  return {
    status: 'executed',
    ...norm,
    invocations,
    tool_calls: toolLog,
    tools_used: [...new Set(toolLog.map((t) => t.tool))],
    trajectory: archived,
    prompt_source: promptSource(caseDef.case_id),
    regime: 'react',
    runtime_ms: Date.now() - t0,
  };
}
