// Results library — flat analysis-results management (plan 2026-10-25).
//
// Covers: deterministic per-intent summaries (fixtures shaped like the real
// artifacts), the completion-path UPSERT (AC-1/AC-11: update, never duplicate,
// user fields survive), list filters + brief mode (AC-3), detail shape + the
// read-time derive fallback (AC-4/AC-6), PATCH rules incl. SUMMARY_READONLY and
// ownership (AC-5), backfill idempotency (AC-2) and soft-delete visibility
// (AC-12). DB-touching cases create their own run rows and clean them up.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'fs';
import { join } from 'path';

const {
  summarizeRun, upsertResultFromRun, backfillResults,
  listResults, getResultDetail, updateResult, RESULT_INTENTS,
} = await import('../src/services/results-library.service.mjs');
import { stmts, db as dbHandle } from '../src/db/database.mjs';

function countResultRows(runId) {
  return dbHandle.prepare('SELECT COUNT(*) AS n FROM analysis_results WHERE run_id = ?').get(runId).n;
}

const ROOT = mkdtempSync(join(import.meta.dirname, '.tmp-reslib-'));
let seq = 0;
const createdRunIds = [];

function runDir(files = {}) {
  const dir = join(ROOT, `run-${seq += 1}`);
  mkdirSync(dir, { recursive: true });
  for (const [rel, body] of Object.entries(files)) {
    const abs = join(dir, rel);
    mkdirSync(join(abs, '..'), { recursive: true });
    writeFileSync(abs, typeof body === 'string' ? body : JSON.stringify(body), 'utf-8');
  }
  return dir;
}

function insertTestRun({ intent = 'stability-report', workspacePath = null, reportPath = null, userId = null } = {}) {
  seq += 1;
  const runId = `reslib_t${Date.now().toString(36)}_${seq}`;
  stmts.insertRun.run({
    runId,
    name: `${intent}_${runId}`,
    title: `${intent}_${runId}`,
    sceneName: 'reslib_scene',
    dataPath: 'data/x.csv',
    dataFolder: null,
    userQuestion: '',
    model: null,
    maxTurns: 5,
    reportLanguage: 'zh',
    harness: 'mock',
    ontologyHit: null,
    enhancementPolicy: 'off',
    enhancementTriggered: 0,
    analysisIntent: intent,
    userId,
  });
  createdRunIds.push(runId);
  stmts.completeRun.run({
    runId,
    workspacePath,
    reportPath,
    score: null,
    judgeVerdict: null,
  });
  return runId;
}

function cleanupRuns() {
  for (const runId of createdRunIds) {
    try { stmts.deleteResultByRunId.run(runId); } catch { /* absent */ }
    try { stmts.deleteLogsByRunId.run(runId); } catch { /* absent */ }
    try { stmts.deleteEventStreamByRunId.run(runId); } catch { /* absent */ }
    try { stmts.deleteRunRow.run(runId); } catch { /* absent */ }
  }
}
process.on('exit', () => {
  cleanupRuns();
  try { rmSync(ROOT, { recursive: true, force: true }); } catch { /* best effort */ }
});

// ── summarizeRun — per-intent deterministic extraction ─────────────────────

describe('summarizeRun — per-intent deterministic extraction', () => {
  test('stability-report: statement + key numbers + data profile', () => {
    const dir = runDir({
      'line_report/stability_report.json': {
        conclusion: {
          score: 65.8, grade: 'C', label: '波动',
          statement: '该产线在本时段总体运行波动（65.8 分，C 级）：评估 4 个参数，检出 343 个 SPC 违规剧集、2 项显著漂移；最需关注：yield_pct。',
          n_parameters_assessed: 4, n_findings: 10,
        },
        data: {
          n_rows_used: 864, parameter_cols: ['yield_pct', 'reactor_temp'],
          sampling_interval_median_seconds: 300, missing_rate: 0.0,
          sha256: 'sha256:5b71', sampled: false,
        },
        period: { start: '2026-10-07 08:00:00', end: '2026-10-10 07:55:00' },
      },
      'report.md': '# 报告',
    });
    const { summary, summary_json: sj } = summarizeRun(dir, { analysis_intent: 'stability-report' });
    assert.ok(summary.includes('65.8'));
    assert.ok(summary.includes('波动'));
    assert.ok(summary.includes('864 行'));
    assert.equal(sj.key_numbers.score, 65.8);
    assert.equal(sj.key_numbers.grade, 'C');
    assert.equal(sj.key_numbers.top_concern, 'yield_pct');
    assert.equal(sj.data_profile.rows, 864);
    assert.deepEqual(sj.data_profile.time_range, ['2026-10-07 08:00:00', '2026-10-10 07:55:00']);
    assert.equal(sj.sources.score, 'line_report/stability_report.json#conclusion.score');
  });

  test('quick-screen: status/alerts/checks summary', () => {
    const dir = runDir({
      'sentinel/alert.json': {
        status: 'alert',
        alerts: new Array(742).fill({}),
        source: { n_rows: 4786, window_start: '2025-12-25 00:00:10', window_end: '2025-12-31 18:34:30', sha256: 'f2b3' },
        checks_summary: {
          spc: { n_triggered: 660 },
          multivariate: { n_outliers: 612 },
          event_count: 201,
          events_by_parameter: {
            'spc|mill_feed_tph': { count: 6, alerts: 110 },
            'spc|baghouse_dp_kPa': { count: 9, alerts: 86 },
          },
        },
      },
    });
    const { summary, summary_json: sj } = summarizeRun(dir, { analysis_intent: 'quick-screen' });
    assert.ok(summary.includes('alert'));
    assert.ok(summary.includes('742 条告警'));
    assert.equal(sj.key_numbers.n_alerts, 742);
    assert.equal(sj.key_numbers.spc_n_triggered, 660);
    assert.equal(sj.key_numbers.top_parameter, 'mill_feed_tph');
    assert.equal(sj.data_profile.rows, 4786);
  });

  test('doe-analysis: evidence grade + design + top finding', () => {
    const dir = runDir({
      'conclusions/doe_conclusion.json': {
        evidence_grade: 'A', design_type: 'rsm_ccd', analysis_mode: 'designed',
        key_findings: [
          { id: 'KF-001', statement: 'TDO 第4区温度是厚度的第一主导因子', confidence: 'high', fdr_q: 1.4e-7 },
          { id: 'KF-002', statement: 'second', confidence: 'high' },
        ],
      },
    });
    const { summary, summary_json: sj } = summarizeRun(dir, { analysis_intent: 'doe-analysis' });
    assert.ok(summary.includes('A'));
    assert.ok(summary.includes('rsm_ccd'));
    assert.ok(summary.includes('TDO'));
    assert.equal(sj.key_numbers.evidence_grade, 'A');
    assert.equal(sj.key_numbers.n_key_findings, 2);
    assert.equal(sj.key_numbers.top_finding_id, 'KF-001');
  });

  test('experience-mining: status + playbooks + regime', () => {
    const dir = runDir({
      'conclusions/recommendation.json': {
        recommendation_status: 'playbook_hit', match_scope: 'machine',
        playbooks: [{ experience_id: 'e1' }],
        source: {
          fault_signature: {
            regime: { product: 'FP21', machine: 'MD18', regime_label: '低速|fault_onset' },
            degraded_metric: 'defect_rate_1000m',
            anomalous_params: [{ parameter: 'W1C01@PV1_mean', direction: 'low', severity: 99 }],
          },
        },
      },
    });
    const { summary, summary_json: sj } = summarizeRun(dir, { analysis_intent: 'experience-mining' });
    assert.ok(summary.includes('playbook_hit'));
    assert.ok(summary.includes('1 个 playbook'));
    assert.equal(sj.key_numbers.n_playbooks, 1);
    assert.equal(sj.key_numbers.product, 'FP21');
    assert.equal(sj.key_numbers.top_anomalous_param, 'W1C01@PV1_mean');
  });

  test('optimizer-campaign: phase/rounds/incumbent', () => {
    const dir = runDir({
      '01_state/optimizer_state.json': {
        campaign_id: 'OPT-1', phase: 'exploiting', round_count: 2, trial_count: 25,
        budget: { max_rounds: 5, max_trials: 40 },
        incumbent: { in_target: true, predicted_D: 0.843186 },
      },
    });
    const { summary, summary_json: sj } = summarizeRun(dir, { analysis_intent: 'optimizer-campaign' });
    assert.ok(summary.includes('exploiting'));
    assert.ok(summary.includes('2/5 轮'));
    assert.ok(summary.includes('已入目标窗'));
    assert.equal(sj.key_numbers.in_target, true);
    assert.equal(sj.key_numbers.predicted_D, 0.843186);
  });

  test('deep-diagnosis: report.md conclusion section', () => {
    const dir = runDir({
      'report.md': '# 诊断\n## 结论\n温度传感器漂移是良率下降的根本原因，证据等级 L3，置信度 92。\n## 建议\n更换传感器。',
    });
    const { summary, summary_json: sj } = summarizeRun(dir, {
      analysis_intent: 'deep-diagnosis', score: 96, judge_verdict: 'ENDORSED',
    });
    assert.ok(summary.includes('温度传感器漂移'));
    assert.ok(!summary.includes('更换传感器')); // only the conclusion section
    assert.equal(sj.key_numbers.score, 96); // the stored Judge score rides along
    assert.equal(sj.key_numbers.verdict, 'ENDORSED');
  });

  test('missing/malformed artifacts degrade to an empty summary, never throw', () => {
    const dir = runDir({ 'sentinel/alert.json': '{broken' });
    const out = summarizeRun(dir, { analysis_intent: 'quick-screen' });
    assert.equal(out.summary, '');
    assert.deepEqual(out.summary_json.key_numbers, {});
    const none = summarizeRun(null, { analysis_intent: 'stability-report' });
    assert.equal(none.summary, '');
  });

  test('intent artifact absent but report.md present → report fallback summary', () => {
    // Mock specialist runs never execute the skill scripts; their own
    // report.md conclusion is the honest summary.
    const dir = runDir({
      'report.md': '# 快筛\n## 结论\n本次快筛未发现需要立即处置的异常，产线整体平稳。\n## 建议\n保持观察。',
    });
    const { summary, summary_json: sj } = summarizeRun(dir, { analysis_intent: 'quick-screen' });
    assert.ok(summary.includes('产线整体平稳'));
    assert.ok(sj.sources.report_fallback, 'fallback source is marked');
    assert.equal(sj.sources.report_fallback, 'report.md#结论');
  });
});

// ── upsertResultFromRun — completion chokepoint behavior ───────────────────

describe('upsertResultFromRun — write path', () => {
  test('AC-1: completed run materializes a row with summary + metadata', () => {
    const dir = runDir({
      'line_report/stability_report.json': {
        conclusion: { score: 65.8, grade: 'C', label: '波动', statement: '总体波动。' },
        data: { n_rows_used: 864, parameter_cols: ['a', 'b'] },
      },
      'report.md': '# R',
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir });
    const row = upsertResultFromRun(runId);
    assert.ok(row, 'row returned');
    assert.equal(row.result_id, runId);
    assert.ok(row.summary.length >= 1);
    const sj = JSON.parse(row.summary_json);
    assert.equal(sj.key_numbers.score, 65.8);
    const md = JSON.parse(row.metadata);
    assert.ok(md.report_md.path.endsWith('report.md'));
    assert.ok(md.report_md.bytes > 0);
    assert.ok(Array.isArray(md.html));
  });

  test('AC-11: re-completion UPSERTs — no duplicate row, user fields survive', () => {
    const dir = runDir({
      'line_report/stability_report.json': {
        conclusion: { score: 70, grade: 'B', label: '平稳', statement: '第二次完成后的结论。' },
        data: { n_rows_used: 100 },
      },
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir });
    upsertResultFromRun(runId);
    updateResult(runId, { description: '用户批注', tags: ['关键', '产线A'] }, { id: '1', role: 'admin' });
    // simulate continue → re-complete: refresh the run row, then re-upsert
    stmts.completeRun.run({ runId, workspacePath: dir, reportPath: null, score: 70, judgeVerdict: 'B · 平稳' });
    upsertResultFromRun(runId);
    assert.equal(countResultRows(runId), 1, 'exactly one row per run');
    const row = stmts.getResultByRunId.get(runId);
    assert.equal(row.score, 70);
    assert.equal(row.verdict, 'B · 平稳');
    assert.equal(row.description, '用户批注', 'user description must survive re-upsert');
    assert.deepEqual(JSON.parse(row.tags), ['关键', '产线A'], 'user tags must survive re-upsert');
  });

  test('non-completed runs are refused (null, no row)', () => {
    seq += 1;
    const runId = `reslib_pend${seq}`;
    stmts.insertRun.run({
      runId, name: runId, title: runId, sceneName: 's', dataPath: 'data/x.csv', dataFolder: null,
      userQuestion: '', model: null, maxTurns: 5, reportLanguage: 'zh', harness: 'mock',
      ontologyHit: null, enhancementPolicy: 'off', enhancementTriggered: 0,
      analysisIntent: 'stability-report', userId: null,
    });
    createdRunIds.push(runId);
    assert.equal(upsertResultFromRun(runId), null);
    assert.equal(stmts.getResultByRunId.get(runId), undefined);
  });
});

// ── listResults — filters, brief, paging ───────────────────────────────────

describe('listResults — index query', () => {
  test('AC-3: q/intent/tag/min_score filters + brief mode + sort', () => {
    const dirA = runDir({
      'line_report/stability_report.json': {
        conclusion: { score: 65.8, grade: 'C', label: '波动', statement: '收率波动明显。' },
        data: { n_rows_used: 864 },
      },
    });
    const a = insertTestRun({ intent: 'stability-report', workspacePath: dirA });
    updateResult(a, { description: '演示产线 收率 问题', tags: ['收率'] }, { id: '1', role: 'admin' });

    const list = listResults({ id: '1', role: 'admin' }, { intent: 'stability-report', q: '收率' });
    assert.ok(list.results.some((r) => r.result_id === a));
    const byTag = listResults({ id: '1', role: 'admin' }, { tag: '收率' });
    assert.ok(byTag.results.some((r) => r.result_id === a));
    const wrongTag = listResults({ id: '1', role: 'admin' }, { tag: '不存在标签' });
    assert.ok(!wrongTag.results.some((r) => r.result_id === a));
    const minScore = listResults({ id: '1', role: 'admin' }, { intent: 'stability-report', min_score: 90 });
    assert.ok(!minScore.results.some((r) => r.result_id === a));

    const brief = listResults({ id: '1', role: 'admin' }, { intent: 'stability-report', brief: 'true', limit: 5 });
    const card = brief.results.find((r) => r.result_id === a);
    assert.ok(card);
    assert.ok(!('key_numbers' in card), 'brief mode drops key_numbers');
    assert.ok(card.display_text.length <= 161);
    assert.ok(typeof card.title === 'string' && card.title.length > 0);

    const paged = listResults({ id: '1', role: 'admin' }, { intent: 'stability-report', limit: 1, offset: 0 });
    assert.equal(paged.results.length, 1);
    assert.ok(paged.total >= 1);
  });

  test('invalid intent / sort / min_score → 400 RESULTS_QUERY_INVALID', () => {
    for (const bad of [
      { intent: 'nope' }, { sort: 'random' }, { min_score: 'abc' },
    ]) {
      assert.throws(() => listResults({ id: '1', role: 'admin' }, bad), (err) => err.code === 'RESULTS_QUERY_INVALID' && err.status === 400);
    }
  });

  test('display_text prefers description over summary', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 90, grade: 'A', statement: '自动摘要内容。' } },
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir });
    upsertResultFromRun(runId);
    const before = listResults({ id: '1', role: 'admin' }, { intent: 'stability-report' }).results.find((r) => r.result_id === runId);
    assert.ok(before, 'row-backed card exists');
    assert.equal(before.description, null);
    assert.ok(before.display_text.length > 0, 'falls back to the auto summary');
    updateResult(runId, { description: '用户描述优先' }, { id: '1', role: 'admin' });
    const after = listResults({ id: '1', role: 'admin' }, { intent: 'stability-report' }).results.find((r) => r.result_id === runId);
    assert.equal(after.display_text, '用户描述优先');
  });
});

// ── getResultDetail + derive fallback ──────────────────────────────────────

describe('getResultDetail — detail + derive fallback', () => {
  test('AC-4: full detail with summary_json/metadata/report_md/files', () => {
    const dir = runDir({
      'line_report/stability_report.json': {
        conclusion: { score: 65.8, grade: 'C', label: '波动', statement: 'st' },
        data: { n_rows_used: 864, sha256: 'sha256:aa' },
      },
      'report.md': '# 产线报告\n正文',
      'line_report/line_stability_report.html': '<html></html>',
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir });
    upsertResultFromRun(runId);
    const d = getResultDetail(runId, { user: { id: '1', role: 'admin' } });
    assert.equal(d.result_id, runId);
    assert.equal(d.score, 65.8);
    assert.equal(d.verdict, 'C · 波动');
    assert.ok(d.report_md.includes('# 产线报告'));
    assert.ok(d.files.html.some((h) => h.path === 'line_report/line_stability_report.html'));
    assert.ok(d.files.html[0].url.startsWith('/api/files/workspace/asset/'));
    assert.equal(d.derived, false);
    assert.ok(d.summary_json.sources.score);
    assert.ok(d.metadata.report_md.bytes > 0);

    const noMd = getResultDetail(runId, { user: { id: '1', role: 'admin' }, includeMd: false });
    assert.equal(noMd.report_md, null);
    assert.ok(noMd.report_md_url);
  });

  test('AC-6: missing row → read-time derived detail (derived:true)', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 88, grade: 'B', label: '平稳', statement: 'ok' } },
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir });
    stmts.deleteResultByRunId.run(runId);
    const d = getResultDetail(runId, { user: { id: '1', role: 'admin' } });
    assert.equal(d.derived, true);
    assert.equal(d.score, 88);
    assert.ok(d.summary.length > 0);
    assert.equal(d.description, null);
  });

  test('404 for unknown id / non-completed run / soft-deleted run', () => {
    assert.throws(() => getResultDetail('no_such_run'), (e) => e.code === 'RESULT_NOT_FOUND' && e.status === 404);
    const dir = runDir({ 'report.md': '# x' });
    seq += 1;
    const runId = `reslib_run${seq}`;
    stmts.insertRun.run({
      runId, name: runId, title: runId, sceneName: 's', dataPath: 'data/x.csv', dataFolder: null,
      userQuestion: '', model: null, maxTurns: 5, reportLanguage: 'zh', harness: 'mock',
      ontologyHit: null, enhancementPolicy: 'off', enhancementTriggered: 0,
      analysisIntent: 'deep-diagnosis', userId: null,
    });
    createdRunIds.push(runId);
    assert.throws(() => getResultDetail(runId), (e) => e.code === 'RESULT_NOT_FOUND');

    const doneId = insertTestRun({ intent: 'deep-diagnosis', workspacePath: dir });
    upsertResultFromRun(doneId);
    stmts.softDeleteRun.run({ runId: doneId });
    assert.throws(() => getResultDetail(doneId), (e) => e.code === 'RESULT_NOT_FOUND');
    const listed = listResults({ id: '1', role: 'admin' }, { intent: 'deep-diagnosis' });
    assert.ok(!listed.results.some((r) => r.result_id === doneId), 'AC-12: soft-deleted run invisible in index');
    stmts.restoreRun.run({ runId: doneId });
  });
});

// ── updateResult — PATCH rules ─────────────────────────────────────────────

describe('updateResult — PATCH rules', () => {
  test('AC-5: description/tags/category patch, reflected immediately', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 90, grade: 'A', statement: 's' } },
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir, userId: '42' });
    const user = { id: '42', role: 'user' };
    const d = updateResult(runId, { description: '新的描述', tags: ['t1', 't1', ' t2 '] }, user);
    assert.equal(d.description, '新的描述');
    assert.deepEqual(d.tags, ['t1', 't2']);
    const again = getResultDetail(runId, { user });
    assert.equal(again.description, '新的描述');
  });

  test('summary is read-only; validation codes; empty body 400', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 90, grade: 'A', statement: 's' } },
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir, userId: '42' });
    const user = { id: '42', role: 'user' };
    assert.throws(() => updateResult(runId, { summary: 'hack' }, user), (e) => e.code === 'SUMMARY_READONLY' && e.status === 400);
    assert.throws(() => updateResult(runId, { description: 'x'.repeat(2001) }, user), (e) => e.code === 'RESULT_PATCH_INVALID');
    assert.throws(() => updateResult(runId, { tags: new Array(17).fill('t') }, user), (e) => e.code === 'RESULT_PATCH_INVALID');
    assert.throws(() => updateResult(runId, { tags: ['x'.repeat(41)] }, user), (e) => e.code === 'RESULT_PATCH_INVALID');
    assert.throws(() => updateResult(runId, {}, user), (e) => e.code === 'RESULT_PATCH_INVALID');
    assert.throws(() => updateResult('missing_run_id', { description: 'x' }, user), (e) => e.code === 'RESULT_NOT_FOUND');
  });

  test('AC-5: ownership — non-owner 403, admin passes', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 90, grade: 'A', statement: 's' } },
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir, userId: '42' });
    assert.throws(
      () => updateResult(runId, { description: 'not mine' }, { id: '43', role: 'user' }),
      (e) => e.code === 'RESULT_FORBIDDEN' && e.status === 403,
    );
    const admin = updateResult(runId, { description: 'admin edit' }, { id: '9', role: 'admin' });
    assert.equal(admin.description, 'admin edit');
  });

  test('title/category_id delegate to the run row', () => {
    const dir = runDir({
      'line_report/stability_report.json': { conclusion: { score: 90, grade: 'A', statement: 's' } },
    });
    const runId = insertTestRun({ intent: 'stability-report', workspacePath: dir, userId: '42' });
    const user = { id: '42', role: 'user' };
    stmts.insertCategory.run({ id: 'CAT-RESLIB1', userId: '42', name: '结果库测试分类' });
    try {
      const d = updateResult(runId, { title: '重命名的结果', category_id: 'CAT-RESLIB1' }, user);
      assert.equal(d.title, '重命名的结果');
      assert.equal(d.category_id, 'CAT-RESLIB1');
      const run = stmts.getRunById.get(runId);
      assert.equal(run.title, '重命名的结果', 'run row is the single source of truth for title');
    } finally {
      stmts.deleteCategory.run('CAT-RESLIB1');
    }
  });
});

// ── backfill — idempotent, insert-only ─────────────────────────────────────

describe('backfillResults — idempotent', () => {
  test('AC-2: two passes → stable counts, zero duplicates', () => {
    const first = backfillResults();
    const second = backfillResults();
    assert.equal(second.inserted, 0, 'second pass inserts nothing');
    assert.equal(second.refreshed, 0, 'second pass refreshes nothing (first pass settled the empties)');
    const { n, distinct_runs: distinct } = dbHandle
      .prepare('SELECT COUNT(*) AS n, COUNT(DISTINCT run_id) AS distinct_runs FROM analysis_results')
      .get();
    assert.equal(n, distinct, 'no duplicate rows');
    assert.ok(n >= 1, 'legacy completed runs are materialized');
    const completed = dbHandle
      .prepare("SELECT COUNT(*) AS c FROM diagnostic_runs WHERE status='completed' AND deleted_at IS NULL")
      .get().c;
    assert.ok(n <= completed, 'backfill never exceeds completed non-deleted runs');
    assert.equal(first.inserted + first.refreshed + first.skipped + first.failed, completed);
  });
});
