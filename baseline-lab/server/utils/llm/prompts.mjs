// Blind prompt construction for the LLM comparators.
//
// The `direct` prompt is built to be BYTE-COMPARABLE with the repository's
// archived baseline (scripts/benchmark/baseline_llm.mjs -> buildPrompt), so the
// lab's fresh executions can be checked against
// results/benchmark/baseline_fe_prompts/*.txt and the archived answers.
//
// LEAKAGE DISCIPLINE
// ------------------
// Prompts are built ONLY from (a) the sanitized case definition and (b) the
// blind brief digest (statistics). Truth fields, keywords and the grading
// rubric are never interpolated. `assertNoLeak()` re-checks this at runtime.

import { loadBrief, loadCauseTable, loadCaseForAlgorithm } from '../paths.mjs';
import { anomalyDigest } from '../dataset.mjs';

const FORBIDDEN = [
  /IDV\((\d+)\)\s*(?:：|:)?\s*(?=[A-Z])/g, // would-be truth strings, caught below instead
];

/** Sanity guard: the rendered prompt must not contain the case's truth text. */
export function assertNoLeak(text, truth) {
  if (!truth) return;
  const t = String(truth).trim();
  if (t.length > 12 && text.includes(t)) {
    throw new Error('LEAKAGE: rendered prompt contains the case truth string');
  }
}

/**
 * Blind statistical digest lines — identical construction to
 * baseline_llm.mjs::digestLines, with a computed fallback when a brief is
 * absent.
 */
export function digestLines(caseId, matrix) {
  const brief = loadBrief(caseId);
  if (brief?.evidence?.anomaly_columns) {
    const cols = brief.evidence.anomaly_columns
      .map((c) => `${c.col} max|z|=${c.max_abs_z} (${(c.pct_z3 * 100).toFixed(1)}% beyond 3σ)`)
      .join('; ');
    const pairs = (brief.evidence.top_correlation_pairs || []).join('; ');
    return {
      lines: [
        `- Per-column max |z|-score (top columns): ${cols}`,
        `- Strongest cross-domain correlations: ${pairs}`,
      ],
      rows: brief.rows,
      process_description: brief.process_description,
      source: 'results/benchmark/briefs (archived blind brief)',
    };
  }
  const digest = anomalyDigest(matrix, { topK: 8 });
  return {
    lines: [
      `- Per-column max |z|-score (top columns): ${digest
        .map((c) => `${c.col} max|z|=${c.max_abs_z} (${(c.pct_z3 * 100).toFixed(1)}% beyond 3σ)`)
        .join('; ')}`,
      '- Strongest cross-domain correlations: (not available — brief missing)',
    ],
    rows: matrix.n,
    process_description: '',
    source: 'computed anomaly digest (brief missing)',
  };
}

const TEP_JSON_TASK =
  'Task: identify the root cause of this abnormal episode. Output STRICT JSON only (no markdown, no extra text): ' +
  '{"top3": ["<root cause id/name>", ...], "reasoning": "<2-3 sentences>"} where top3 is your ranked list of up to 3 candidate root causes.';

const GENERIC_JSON_TASK =
  'Task: (1) state whether this episode shows a fault or normal operation; (2) if a fault, give the most likely root cause and up to 2 alternatives. ' +
  'Output STRICT JSON only (no markdown, no extra text): {"verdict": "fault" | "normal", "top3": [...], "reasoning": "<2-3 sentences>"}';

/**
 * The baseline `direct` prompt. Mirrors baseline_llm.mjs::buildPrompt exactly.
 * regime: 'no_candidates' | 'with_candidates'
 */
export function buildDirectPrompt(caseId, matrix, regime = 'no_candidates') {
  const c = loadCaseForAlgorithm(caseId);
  const d = digestLines(caseId, matrix);
  const isTep = c.dataset === 'tep';
  const lines = [];

  if (isTep) {
    lines.push(
      'You are an industrial process monitoring engineer. The Tennessee Eastman Process (TEP) shows an abnormal episode. Your task: identify the root cause.',
    );
    lines.push('');
    lines.push(
      'Dataset: Tennessee Eastman Process simulation. Columns: XMEAS_1..41 process measurements, XMV_1..11 manipulator variables (Downs-Vogel standard mapping). Sampling: 3 minutes. Fault onset: sample 161 of 960.',
    );
  } else {
    lines.push(
      'You are an industrial process monitoring engineer. A process shows the following recorded episode. Your task: assess whether a fault is present and, if so, identify the most likely root cause.',
    );
    lines.push('');
    lines.push(`Dataset: ${c.case_id} (${c.dataset}). Rows: ${d.rows}. Sampling as described below.`);
  }

  lines.push('Blind statistical monitoring results (computed from the data):');
  lines.push(...d.lines);
  lines.push('');
  lines.push(`Process description: ${d.process_description || c.process_description || '(none)'}`);
  lines.push('');

  if (regime === 'with_candidates') {
    const causes = loadCauseTable();
    lines.push('Documented root-cause list for the TEP (choose from these):');
    for (const [id, desc] of Object.entries(causes.faults)) lines.push(`- ${id}: ${desc}`);
  }

  lines.push(isTep ? TEP_JSON_TASK : GENERIC_JSON_TASK);
  const text = lines.join('\n') + '\n';
  assertNoLeak(text, c.truth);
  return text;
}

// ------------------------------------------------------------- CoT variant

export function buildCotPrompt(caseId, matrix) {
  const base = buildDirectPrompt(caseId, matrix, 'no_candidates');
  return (
    base.replace(
      /Task:.*$/s,
      '',
    ) +
    [
      'Reason step by step before answering. Work through, in order:',
      '  1. Which physical units the deviating columns belong to (reactor / separator / stripper / feed / utility loop).',
      '  2. The direction and magnitude of each deviation and what it implies physically.',
      '  3. Which manipulated variables moved, and whether that indicates the control loop compensating for a disturbance.',
      '  4. The candidate root cause that can explain ALL observed deviations simultaneously.',
      '  5. Explicitly rule out at least two competing candidates and say why.',
      '',
      'Then output your final answer as STRICT JSON on the LAST line, with the reasoning field carrying your conclusion:',
      '{"top3": ["<root cause id/name>", ...], "reasoning": "<your step-by-step conclusion, 4-6 sentences>"}',
    ].join('\n')
  );
}

// ------------------------------------------------------------ ReAct variant

export const REACT_TOOLS = `Available tools (call at most 6 times total):
- column_stats(column)                     -> mean, std, min, max, first-half vs second-half mean shift for one column
- top_changed_columns(k)                   -> the k columns with the largest mean shift between the first and second half of the record
- correlate(column_a, column_b)            -> Pearson r between two columns
- window_compare(column, from_row, to_row) -> mean and std of one column over an explicit row range

To call a tool, emit a line exactly of the form:
ACTION: <tool_name>(<arguments>)
You will then receive:
OBSERVATION: <result>
Repeat as needed, then finish with:
FINAL: {"top3": ["<root cause id/name>", ...], "reasoning": "<2-3 sentences>"}`;

export function buildReactPrompt(caseId, matrix) {
  const c = loadCaseForAlgorithm(caseId);
  const d = digestLines(caseId, matrix);
  const isTep = c.dataset === 'tep';
  const lines = [];
  lines.push(
    isTep
      ? 'You are an industrial process monitoring engineer diagnosing an abnormal Tennessee Eastman Process (TEP) episode.'
      : 'You are an industrial process monitoring engineer assessing a recorded process episode.',
  );
  lines.push('');
  lines.push(`Dataset: ${c.case_id} (${c.dataset}). Rows: ${d.rows}. Columns: ${matrix.colNames.join(', ')}.`);
  lines.push('');
  lines.push('Blind statistical monitoring results (computed from the data):');
  lines.push(...d.lines);
  lines.push('');
  lines.push(`Process description: ${d.process_description || c.process_description || '(none)'}`);
  lines.push('');
  lines.push(
    'You may investigate the raw record with the tools below before concluding. Do NOT guess numbers — call tools and use their actual output.',
  );
  lines.push('');
  lines.push(REACT_TOOLS);
  const text = lines.join('\n') + '\n';
  assertNoLeak(text, c.truth);
  return text;
}

// ----------------------------------------------------------- Debate variant

export function buildDebateRoles(caseId, matrix) {
  const c = loadCaseForAlgorithm(caseId);
  const d = digestLines(caseId, matrix);
  const context = [
    `Dataset: ${c.case_id} (${c.dataset}). Rows: ${d.rows}.`,
    'Blind statistical monitoring results (computed from the data):',
    ...d.lines,
    '',
    `Process description: ${d.process_description || c.process_description || '(none)'}`,
  ].join('\n');

  return {
    context,
    roles: [
      {
        id: 'process',
        persona:
          'You are a process-systems engineer. You argue from mass balance, reaction stoichiometry and control-loop behaviour. You favour causes on the feed and reaction side.',
      },
      {
        id: 'utilities',
        persona:
          'You are a utilities/rotating-equipment engineer. You argue from cooling-water loops, valve behaviour, fouling and actuator dynamics. You favour causes on the utility side.',
      },
      {
        id: 'instrumentation',
        persona:
          'You are an instrumentation and data-quality engineer. You are sceptical: you check whether apparent deviations could be sensor drift, sampling artefacts, offline-assay carry-forward, or start-up transients rather than a real process fault.',
      },
    ],
  };
}

export function buildDebateOpening(role, context) {
  return [
    role.persona,
    '',
    context,
    '',
    'Give your independent initial diagnosis. State your top candidate and up to two alternatives, and the specific evidence in the digest that supports you.',
    'Output STRICT JSON only: {"top3": ["<cause>", ...], "reasoning": "<2-3 sentences of your argument>"}',
  ].join('\n');
}

export function buildDebateRebuttal(role, context, others) {
  const rendered = others
    .map((o) => `- ${o.id}: ${JSON.stringify(o.answer)}`)
    .join('\n');
  return [
    role.persona,
    '',
    context,
    '',
    'The other panellists argued:',
    rendered,
    '',
    'Now critique their arguments. Where do they contradict the evidence? Which single cause best explains the largest number of observed deviations?',
    'You may change your answer or hold your position — but justify it against the evidence.',
    'Output STRICT JSON only: {"top3": ["<cause>", ...], "reasoning": "<2-3 sentences>"}',
  ].join('\n');
}

export function buildDebateJudge(context, opinions) {
  const rendered = opinions
    .map((o) => `### ${o.id} (round ${o.round})\n${JSON.stringify(o.answer, null, 1)}`)
    .join('\n\n');
  return [
    'You are the chair of an industrial root-cause review panel. Three specialists have argued the case below.',
    '',
    context,
    '',
    'Their opinions across the debate:',
    rendered,
    '',
    'Adjudicate. Weigh the arguments strictly against the evidence in the digest. Do not simply count votes — a single well-argued position supported by more of the evidence should win.',
    'Output STRICT JSON only: {"top3": ["<cause>", ...], "reasoning": "<2-4 sentences explaining which argument you accepted and why>"}',
  ].join('\n');
}
