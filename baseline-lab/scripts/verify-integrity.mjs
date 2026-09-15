#!/usr/bin/env node
// verify-integrity.mjs — deterministic test of the ReAct evidence-integrity guard.
//
// A live run showed the model writing its OWN `OBSERVATION:` lines and calling
// tools that do not exist (`column_trace`, `trend`), then answering from that
// fabricated output. Live runs are slow and non-deterministic, so the guard is
// proven here against the exact transcripts that were observed.

import { parseTurn, makeToolbox, TOOL_NAMES } from '../server/utils/algorithms/llm-react.mjs';

let pass = 0, fail = 0;
const check = (name, ok, detail = '') => {
  if (ok) { pass++; console.log(`  PASS  ${name}${detail ? `  ${detail}` : ''}`); }
  else { fail++; console.log(`  FAIL  ${name}${detail ? `  ${detail}` : ''}`); }
};

console.log('\n=== 1. fabricated-observation detection (real transcript) ===\n');

// Verbatim shape from the live run that exposed the problem.
const fabricated = `ACTION: trend(XMEAS_34, 120, 200) OBSERVATION: {"column":"XMEAS_34","slope":0.00093,"p_value":0.0001,"r2":0.83,"direction":"increasing","significant":true}`;
let t = parseTurn(fabricated);
check('self-authored OBSERVATION is flagged', t.selfAuthoredObservation === true);
check('the fabricated text is STRIPPED from the cleaned turn', !/0\.00093/.test(t.cleaned), `cleaned=${JSON.stringify(t.cleaned.slice(0, 60))}`);
check('the ACTION is still parsed so the real tool runs', t.kind === 'action' && t.tool === 'trend', `tool=${t.tool}`);

const fabricatedFinal = `I checked the data.
OBSERVATION: {"slope": 0.00093, "p_value": 0.0001}
FINAL: {"top3": ["XMEAS_34 drifts upward"], "reasoning": "slope 0.00093, p=0.0001"}`;
t = parseTurn(fabricatedFinal);
check('fabrication before FINAL is flagged', t.selfAuthoredObservation === true);
check('FINAL is still recovered', t.kind === 'final' && t.answer?.top3?.length === 1);
check('the fabricated OBSERVATION block is removed', !/OBSERVATION\s*:/i.test(t.cleaned) && !/"p_value"/.test(t.cleaned),
  `cleaned=${JSON.stringify(t.cleaned.slice(0, 70))}`);
// The model may still REPEAT its invented number in its own FINAL. We do not
// silently rewrite the model's words — we keep the answer and label it
// contaminated, so the number is visibly untrustworthy rather than invisibly
// corrected. That is why this asserts the flag, not the absence of the digits.
check('an answer repeating a fabricated number stays flagged as contaminated', t.selfAuthoredObservation === true,
  'contamination is labelled, not silently edited');

console.log('\n=== 2. clean turns are not false-positived ===\n');
t = parseTurn('ACTION: column_stats(XMEAS_34)');
check('a plain ACTION is clean', t.kind === 'action' && !t.selfAuthoredObservation);
t = parseTurn('FINAL: {"top3": ["a"], "reasoning": "b"}');
check('a plain FINAL is clean', t.kind === 'final' && !t.selfAuthoredObservation);
t = parseTurn('Thinking about the OBSERVATION: field semantics in general.');
check('mentioning the word without a line is not flagged', !t.selfAuthoredObservation,
  'prose mention must not trip the guard');

console.log('\n=== 3. tool surface ===\n');
// The two tools the model invented must either exist for real or be rejected.
check('trend is now a REAL tool (the model kept asking for it)', TOOL_NAMES.includes('trend'));
check('column_trace is NOT a tool (must be rejected)', !TOOL_NAMES.includes('column_trace'));

console.log('\n=== 4. real tool output vs the fabricated numbers ===\n');
// Build a synthetic matrix with a known trend and compare.
const N = 300;
const X = Array.from({ length: N }, (_, i) => [i, 10 + 0.05 * i]); // slope exactly 0.05
const matrix = { colNames: ['idx', 'XMEAS_34'], X, n: N, m: 2, times: [], header: ['idx', 'XMEAS_34'] };
const tb = makeToolbox(matrix);

const real_ = tb.trend('XMEAS_34', 0, N);
check('trend returns a real slope from the data', Math.abs(real_.slope_per_row - 0.05) < 1e-6, `slope=${real_.slope_per_row}`);
check('trend reports the true window, not an invented one', real_.window?.[0] === 0 && real_.window?.[1] === N);
check('trend p-value is a real statistic', Number.isFinite(real_.p_value) && real_.p_value < 0.05, `p=${real_.p_value}`);

const unknownCol = tb.trend('NOT_A_COLUMN');
check('unknown column is an ERROR, not a plausible number', Boolean(unknownCol.error), unknownCol.error?.slice(0, 60));

const unknownWindow = tb.column_stats('XMEAS_34', 500, 100);
check('inverted window is an ERROR, not silently clamped', Boolean(unknownWindow.error));

const withWindow = tb.column_stats('XMEAS_34', 0, 50);
check('column_stats now honours an optional window (the model asked for it)', withWindow.window?.[0] === 0 && withWindow.rows === 50);

console.log('\n=== 5. every tool returns data-derived values ===\n');
for (const name of TOOL_NAMES) {
  let r;
  if (name === 'column_stats') r = tb.column_stats('XMEAS_34');
  else if (name === 'top_changed_columns') r = tb.top_changed_columns(2);
  else if (name === 'correlate') r = tb.correlate('idx', 'XMEAS_34');
  else if (name === 'window_compare') r = tb.window_compare('XMEAS_34', 0, 100);
  else if (name === 'trend') r = tb.trend('XMEAS_34', 0, 100);
  const hasError = Boolean(r?.error);
  const finite = JSON.stringify(r).match(/-?\d+(\.\d+)?([eE][-+]?\d+)?/g)?.every((s) => Number.isFinite(Number(s)));
  check(`${name} returns a real result`, !hasError && finite, hasError ? r.error : JSON.stringify(r).slice(0, 80));
}

console.log(`\n=== RESULT: PASS ${pass}  FAIL ${fail} ===\n`);
process.exit(fail === 0 ? 0 : 1);
