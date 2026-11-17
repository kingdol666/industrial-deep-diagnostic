// Line memory core — deterministic extraction / consolidation / retrieval / proposals.
// Acceptance map: AC1 (idempotent extraction), AC2 (grading), AC3 (retrieval), AC4 (tiered proposals).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  PROPOSAL_CONTRACT,
  registerLine, findLineByAlias, readFindings, appendFindings, readConsensus,
  resolveLineIdentity, extractFindingsForRun, ingestRun, consolidate, independentCount,
  buildMemoryBrief, retrieveForRun, mergeLines, overrideEntry,
  validateProposal, ingestProposals, decideProposal, readProposalLog, proposalTier,
} from '../../../.claude/shared/scripts/line_memory.mjs';

const HERE = fileURLToPath(new URL('.', import.meta.url));
const ROOT = resolve(HERE, '..', '..', '..');
let seq = 0;

function tmpDir(label) {
  const dir = join(ROOT, `.tmp-line-memory-${label}-${process.pid}-${++seq}`);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  return dir;
}

function writeJson(abs, obj) {
  mkdirSync(join(abs, '..'), { recursive: true });
  writeFileSync(abs, JSON.stringify(obj, null, 2));
}

function makeStabilityRun(runDir, { runId, lineId = 'lekai-FW3-MDO', start = '2026-05-04 15:00:00', end = '2026-05-13 15:00:00', extraFindings = [], driftParams = [] }) {
  mkdirSync(join(runDir, 'line_report'), { recursive: true });
  const report = {
    contract_version: 'line-report/1.0',
    report_id: 'LR-' + runId,
    generated_at: new Date().toISOString(),
    status: 'warning',
    line: { line_id: lineId, product: 'BOPET · FW3 · MD' },
    period: { start, end },
    data: { rows: 1000 },
    parameters: [
      { name: 'MD_TH001@PV', score: 88, drift: { significant: false, per_day_relative: 0.0001, mk_p: null } },
      ...driftParams.map((p) => ({ name: p.name, score: p.score ?? 40, drift: { significant: true, per_day_relative: p.perDay, mk_p: 0.001, slope_per_second: 1e-6 } })),
    ],
    findings: [
      { finding_id: 'F001', severity: 'high', category: 'spc', title: 'MD_TH001@PV 检出 SPC 违规', detail: '890 个判异剧集', affected: ['MD_TH001@PV'], confidence: 90, evidence: [{ metric: 'violation_episodes', value: 890 }] },
      ...extraFindings,
    ],
    conclusion: { score: 54.4, grade: 'C', label: '波动', statement: '总体运行波动(54.4 分,C 级)' },
  };
  writeJson(join(runDir, 'line_report', 'stability_report.json'), report);
}

function makeQuickScreenRun(runDir, { runId }) {
  mkdirSync(join(runDir, 'sentinel'), { recursive: true });
  writeJson(join(runDir, 'sentinel', 'alert.json'), {
    contract_version: 'sentinel-alert/1.0',
    status: 'alert',
    generated_at: new Date().toISOString(),
    source: { data_path: 'x.csv', sha256: 'a'.repeat(64), window_start: '2026-05-04 14:42:00', window_end: '2026-05-13 14:26:00' },
    checks_summary: { spc: { n_triggered: 320 }, multivariate: { n_outliers: 86 } },
    alerts: [
      { alert_id: 'A1', check_type: 'spc', rule_name: 'NELSON_R1', parameter: 'W1C80@PV1_mean', severity: 'high' },
      { alert_id: 'A2', check_type: 'spc', rule_name: 'NELSON_R5', parameter: 'W1C80@PV1_mean', severity: 'warn' },
      { alert_id: 'A3', check_type: 'multivariate', rule_name: 'MAHALANOBIS_OUTLIER', parameter: null, severity: 'high', evidence: { contributing_params: [{ name: 'W1C4B@PV1_mean' }] } },
    ],
  });
}

function makeDiagnosisRun(runDir, { runId }) {
  mkdirSync(join(runDir, '04_diagnostics'), { recursive: true });
  writeJson(join(runDir, '04_diagnostics', 'diagnosis.json'), {
    run_id: runId,
    diagnosis_type: 'combined_dual_driver',
    primary_finding: '缺陷抬升集中在 3 个孤立批次, 属批级瞬态冲击, 非连续漂移。',
    hypotheses: [{ id: 'H3', statement: '再启动过渡颗粒爆发', verdict: 'COMPETING' }],
    four_condition_verdicts: { H3: 'not_discriminable' },
  });
  writeJson(join(runDir, '04_diagnostics', 'confidence.json'), {
    run_id: runId,
    overall_confidence: 65,
    confidence_breakdown: { H3: { hypothesis_id: 'H3', confidence_score: 64, level: 'MEDIUM' } },
  });
}

function readFindingsOf(storeDir, lineKey) { return readFindings(storeDir, lineKey); }

// ── AC1: extraction idempotency + identity ───────────────────────────────

test('extract: stability report → per-param findings + drift direction + line_state; identity from line_id', () => {
  const runDir = tmpDir('run');
  const store = tmpDir('store');
  makeStabilityRun(runDir, { runId: 'runA0001', driftParams: [{ name: 'F_PS006@PV', perDay: 0.0234 }, { name: 'F_PS005@PV', perDay: -0.01 }] });

  const identity = resolveLineIdentity({ storeDir: store, runDir, sceneKey: 'lekai-fw3-mdo-stability' });
  assert.equal(identity.lineKey, 'lekai-fw3-mdo');
  assert.ok(identity.aliases.includes('lekai-FW3-MDO'));

  const extracted = extractFindingsForRun({ runDir, runId: 'runA0001', intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability' });
  assert.equal(extracted.lineKey, 'lekai-fw3-mdo');
  const claims = extracted.findings.map((f) => f.claim_type).sort();
  assert.ok(claims.includes('spc_violation'));
  assert.ok(claims.includes('drift'));
  assert.ok(claims.includes('line_state'));
  const drift = extracted.findings.find((f) => f.claim_type === 'drift' && f.subject === 'F_PS006@PV');
  assert.equal(drift.direction, 'up');
  const driftDown = extracted.findings.find((f) => f.claim_type === 'drift' && f.subject === 'F_PS005@PV');
  assert.equal(driftDown.direction, 'down');
  for (const f of extracted.findings) {
    assert.equal(f.contract_version, 'finding-record/1.0');
    assert.match(f.finding_id, /^F-[a-z0-9]+-[a-f0-9]{8}$/);
    assert.ok(f.sources.length >= 1);
    assert.match(f.sources[0].sha256, /^sha256:[a-f0-9]{64}$/);
  }
});

test('extract: idempotent ingest — same run twice adds once; quick-screen groups alerts by subject+claim', () => {
  const store = tmpDir('store');
  const runDir = tmpDir('run');
  makeStabilityRun(runDir, { runId: 'runB0001' });
  const first = ingestRun({ storeDir: store, runDir, runId: 'runB0001', intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability' });
  assert.ok(first.findings_added > 0);
  const second = ingestRun({ storeDir: store, runDir, runId: 'runB0001', intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability' });
  assert.equal(second.findings_added, 0);
  assert.ok(second.skipped > 0);
  assert.equal(readFindingsOf(store, first.lineKey).length, first.findings_added);

  const qsRun = tmpDir('run-qs');
  makeQuickScreenRun(qsRun, { runId: 'runB0002' });
  const qs = ingestRun({ storeDir: store, runDir: qsRun, runId: 'runB0002', intent: 'quick-screen', sceneKey: 'lekai-defect-quickscreen' });
  const qsFindings = readFindingsOf(store, qs.lineKey).filter((f) => f.run_id === 'runB0002');
  const w1c = qsFindings.filter((f) => f.subject === 'W1C80@PV1_mean' && f.claim_type === 'spc_violation');
  assert.equal(w1c.length, 1, '同主体同 check 类型应聚合为一条');
  assert.equal(w1c[0].payload.n_alerts, 2);
  assert.ok(qsFindings.some((f) => f.subject === 'W1C4B@PV1_mean' && f.claim_type === 'multivariate_outlier'));
});

// ── AC2: independence + grading ──────────────────────────────────────────

test('extract: deep-diagnosis → primary conclusion + hypothesis findings (confidence joined)', () => {
  const store = tmpDir('store');
  const runDir = tmpDir('run');
  makeDiagnosisRun(runDir, { runId: 'runK0001' });
  const r = ingestRun({ storeDir: store, runDir, runId: 'runK0001', intent: 'deep-diagnosis', sceneKey: 'lekai-mixed-defects-diag' });
  const fs2 = readFindings(store, r.lineKey);
  const concl = fs2.find((x) => x.claim_type === 'diagnosis_conclusion');
  assert.ok(concl, 'primary conclusion extracted');
  assert.equal(concl.confidence, 65);
  const hyp = fs2.find((x) => x.claim_type === 'hypothesis');
  assert.ok(hyp, 'hypothesis extracted');
  assert.equal(hyp.confidence, 64);
  assert.equal(hyp.subject, 'H3');
});

test('independence: overlapping data windows count as ONE incident; distinct windows count separately', () => {
  const overlapA = { data_window: { start: '2026-05-04 00:00:00', end: '2026-05-10 00:00:00' }, observed_at: '2026-11-01T00:00:00Z', run_id: 'r1' };
  const overlapB = { data_window: { start: '2026-05-05 00:00:00', end: '2026-05-11 00:00:00' }, observed_at: '2026-11-20T00:00:00Z', run_id: 'r2' };
  const distinctC = { data_window: { start: '2026-06-01 00:00:00', end: '2026-06-10 00:00:00' }, observed_at: '2026-12-01T00:00:00Z', run_id: 'r3' };
  assert.equal(independentCount([overlapA, overlapB]), 1, '窗口重叠 >50% 视为同一事件');
  assert.equal(independentCount([overlapA, overlapB, distinctC]), 2);
});

test('grading: 1→singleton, 2→candidate, 3 independent→consensus; same incident never inflates', () => {
  const store = tmpDir('store');
  const windows = ['2026-05-01', '2026-06-01', '2026-07-01'];
  for (let i = 0; i < 3; i++) {
    const runDir = tmpDir('run');
    makeStabilityRun(runDir, {
      runId: 'runC000' + i,
      start: `${windows[i]} 00:00:00`, end: `${windows[i]} 10:00:00`,
      extraFindings: [{ finding_id: 'FX' + i, severity: 'high', category: 'spc', title: 'W1C82@PV1 检出 SPC 违规', detail: 'episodes', affected: ['W1C82@PV1'], confidence: 90 }],
    });
    ingestRun({ storeDir: store, runDir, runId: 'runC000' + i, intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability', observedAt: `${windows[i]}T11:00:00Z` });
  }
  let consensus = readConsensus(store, 'lekai-fw3-mdo');
  const entry = consensus.entries.find((e) => e.subject === 'W1C82@PV1' && e.claim_type === 'spc_violation');
  assert.ok(entry, 'entry exists');
  assert.equal(entry.independent, 3);
  assert.equal(entry.grade, 'consensus');

  // same-window duplicate run must not push a singleton to candidate
  const store2 = tmpDir('store');
  const mk = (n, start, end, observedAt) => {
    const runDir = tmpDir('run');
    makeStabilityRun(runDir, {
      runId: 'runD000' + n, start: `${start} 00:00:00`, end: `${end} 00:00:00`,
      extraFindings: [{ finding_id: 'FZ', severity: 'high', category: 'spc', title: 'X 判异', detail: '', affected: ['X@PV'], confidence: 90 }],
    });
    ingestRun({ storeDir: store2, runDir, runId: 'runD000' + n, intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability', observedAt });
  };
  mk(1, '2026-05-04', '2026-05-13', '2026-11-01T00:00:00Z');
  mk(2, '2026-05-05', '2026-05-12', '2026-11-02T00:00:00Z'); // 同事件
  const c2 = readConsensus(store2, 'lekai-fw3-mdo');
  const e2 = c2.entries.find((e) => e.subject === 'X@PV');
  assert.equal(e2.independent, 1);
  assert.equal(e2.grade, 'singleton');
});

test('grading: opposite directions → competing (both kept, never consensus); strong repeated evidence refutes a weak single observation', () => {
  const store = tmpDir('store');
  const addRun = (n, direction, perDay, levelNote) => {
    const runDir = tmpDir('run');
    makeStabilityRun(runDir, {
      runId: 'runE000' + n, start: `2026-0${n}-01 00:00:00`, end: `2026-0${n}-05 00:00:00`,
      driftParams: [{ name: 'F_PS006@PV', perDay }],
    });
    // 篡改证据级以便测试反证规则（L2 vs L5）
    const p = join(runDir, 'line_report', 'stability_report.json');
    const j = JSON.parse(readFileSync(p, 'utf-8'));
    j.findings = [];
    writeFileSync(p, JSON.stringify(j));
    ingestRun({ storeDir: store, runDir, runId: 'runE000' + n, intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability', observedAt: `2026-0${n}-06T00:00:00Z` });
  };
  addRun(1, 'up', 0.02);
  addRun(2, 'up', 0.03);
  addRun(3, 'down', -0.02);
  let c = readConsensus(store, 'lekai-fw3-mdo');
  let e = c.entries.find((x) => x.subject === 'F_PS006@PV' && x.claim_type === 'drift');
  assert.equal(e.grade, 'competing', '方向矛盾必须 competing');
  assert.equal(e.directions.length, 2);
  assert.equal(e.directions.every((d) => d.status !== 'refuted'), true, '独立数 2 vs 1 且证据级相同 → 不反证,双保留');

  // 强证据(独立2,L2) vs 弱单次(L5) → 弱侧 refuted,活跃侧独立数 2 → candidate
  const store2 = tmpDir('store');
  // 直接构造 findings 测试分级规则(不依赖产物)
  appendFindings(store2, 'lekai-fw3-mdo', [
    { contract_version: 'finding-record/1.0', finding_id: 'F-r1-aaaaaaaa', line_key: 'lekai-fw3-mdo', scene_key: 's', intent: 'stability-report', run_id: 'r1', observed_at: '2026-11-01T00:00:00Z', data_window: { start: '2026-05-01', end: '2026-05-02' }, subject: 'F_PS007@PV', claim_type: 'drift', direction: 'up', severity: 'high', confidence: 90, evidence_level: 'L2', detail: '', payload: {}, sources: [] },
    { contract_version: 'finding-record/1.0', finding_id: 'F-r2-aaaaaaaa', line_key: 'lekai-fw3-mdo', scene_key: 's', intent: 'stability-report', run_id: 'r2', observed_at: '2026-11-02T00:00:00Z', data_window: { start: '2026-06-01', end: '2026-06-02' }, subject: 'F_PS007@PV', claim_type: 'drift', direction: 'up', severity: 'high', confidence: 90, evidence_level: 'L2', detail: '', payload: {}, sources: [] },
    { contract_version: 'finding-record/1.0', finding_id: 'F-r3-aaaaaaaa', line_key: 'lekai-fw3-mdo', scene_key: 's', intent: 'stability-report', run_id: 'r3', observed_at: '2026-11-03T00:00:00Z', data_window: { start: '2026-07-01', end: '2026-07-02' }, subject: 'F_PS007@PV', claim_type: 'drift', direction: 'down', severity: 'warn', confidence: 40, evidence_level: 'L5', detail: '', payload: {}, sources: [] },
  ]);
  const c3 = consolidate(store2, 'lekai-fw3-mdo', { now: '2026-12-01T00:00:00Z' });
  const e3 = c3.entries.find((x) => x.subject === 'F_PS007@PV');
  assert.equal(e3.grade, 'candidate', '弱侧被反证后活跃侧独立数 2 → candidate');
  const weak = e3.directions.find((d) => d.direction === 'down');
  assert.equal(weak.status, 'refuted', '弱单次证据应被强重复证据反证');
});

test('grading: 90-day staleness flags old observations without deleting them', () => {
  const store = tmpDir('store');
  const runDir = tmpDir('run');
  makeStabilityRun(runDir, { runId: 'runF0001' });
  ingestRun({ storeDir: store, runDir, runId: 'runF0001', intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability', observedAt: '2026-01-01T00:00:00Z' });
  const c = consolidate(store, 'lekai-fw3-mdo', { now: '2026-12-01T00:00:00Z' });
  assert.ok(c.entries.length > 0);
  assert.equal(c.entries.some((e) => e.stale), true);
  assert.ok(c.entries.every((e) => e.grade !== 'refuted'));
});

// ── AC3: retrieval brief ────────────────────────────────────────────────

test('retrieval: consensus first, budget cap, discipline text, empty when no store', () => {
  const store = tmpDir('store');
  const runDir = tmpDir('run');
  makeStabilityRun(runDir, { runId: 'runG0001', driftParams: [{ name: 'W1C82@PV', perDay: 0.05 }] });
  ingestRun({ storeDir: store, runDir, runId: 'runG0001', intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability' });
  const r = retrieveForRun({ storeDir: store, sceneKey: 'lekai-fw3-mdo-stability' });
  assert.equal(r.hit, true);
  assert.equal(r.lineKey, 'lekai-fw3-mdo');
  assert.ok(r.text.includes('## 产线记忆'));
  assert.ok(r.text.includes('必须用本次数据重新验证'));
  assert.ok(r.payload.entries.length > 0);

  const empty = retrieveForRun({ storeDir: tmpDir('empty'), sceneKey: 'nope-line' });
  assert.equal(empty.hit, false);
  assert.equal(empty.text, '');

  const longStore = tmpDir('store-long');
  for (let i = 0; i < 30; i++) {
    const f = { contract_version: 'finding-record/1.0', finding_id: `F-x${i}-aaaaaaaa`, line_key: 'big-line', scene_key: 's', intent: 'stability-report', run_id: 'r' + i, observed_at: '2026-11-01T00:00:00Z', data_window: { start: '2026-0' + ((i % 9) + 1) + '-01', end: '2026-0' + ((i % 9) + 1) + '-02' }, subject: 'P' + i + '@PV', claim_type: 'spc_violation', direction: null, severity: 'high', confidence: 90, evidence_level: 'L3', detail: 'x'.repeat(200), payload: {}, sources: [] };
    appendFindings(longStore, 'big-line', [f, { ...f, finding_id: `F-y${i}-aaaaaaaa`, run_id: 'r' + i + 'b', data_window: { start: '2026-1' + (i % 2) + '-01', end: '2026-1' + (i % 2) + '-02' } }, { ...f, finding_id: `F-z${i}-aaaaaaaa`, run_id: 'r' + i + 'c', data_window: { start: '2027-01-01', end: '2027-01-02' } }]);
  }
  registerLine(longStore, { lineKey: 'big-line', name: 'big' });
  consolidate(longStore, 'big-line', { now: '2026-11-05T00:00:00Z' });
  const big = buildMemoryBrief(readConsensus(longStore, 'big-line'), { maxTokens: 120 });
  assert.ok(big.text.length <= 400, '预算硬截断生效: ' + big.text.length);
  assert.ok(big.text.includes('截断'));
});

// ── AC4: ontology proposals (tiered) ────────────────────────────────────

test('proposals: validation rejects unknown target / oversized count; tiers map correctly', () => {
  assert.equal(proposalTier('add_missing_parameter'), 'additive');
  assert.equal(proposalTier('correct_unit'), 'correction');
  assert.equal(proposalTier('remove'), 'removal');
  assert.equal(proposalTier('whatever'), 'invalid');

  const bad = validateProposal({
    contract_version: PROPOSAL_CONTRACT, run_id: 'r1', scene_key: 'lekai-fw3-mdo',
    proposals: Array.from({ length: 11 }, (_, i) => ({ id: 'P' + i, op: 'add_note', target: 'X', rationale: 'r' })),
  }, { dataColumns: ['X'] });
  assert.equal(bad.ok, false);
  assert.ok(bad.errors.some((e) => e.includes('上限')));

  const unknown = validateProposal({
    contract_version: PROPOSAL_CONTRACT, run_id: 'r1', scene_key: 'lekai-fw3-mdo',
    proposals: [{ id: 'P1', op: 'correct_unit', target: 'NOT_A_COLUMN', to: 'bar', rationale: 'r' }],
  }, { dataColumns: ['X', 'Y'] });
  assert.equal(unknown.ok, false);
  assert.ok(unknown.errors.some((e) => e.includes('不在本次数据列中')));
});

test('proposals: additive auto-applies; correction waits for 2 independent runs; removal awaits approval', () => {
  const store = tmpDir('store');
  const calls = [];
  const applyFn = (record, change) => {
    calls.push({ id: record.proposal_id, op: record.op, status: record.status });
    return { ok: true, scene_key: record.scene_key, version: calls.length };
  };
  const makeRun = (runId, proposals) => {
    const runDir = tmpDir('run');
    mkdirSync(join(runDir, '05_review'), { recursive: true });
    writeJson(join(runDir, '05_review', 'ontology_proposals.json'), {
      contract_version: PROPOSAL_CONTRACT, run_id: runId, scene_key: 'lekai-fw3-mdo', proposals,
    });
    return runDir;
  };

  const run1 = makeRun('runH0001', [
    { id: 'P1', op: 'add_missing_parameter', target: 'NEW_SENSOR@PV', to: { unit: 'bar', role: 'parameter' }, rationale: '数据中存在但本体缺失' },
    { id: 'P2', op: 'correct_unit', target: 'F_PS005@PV', field: 'unit', to: 'bar', rationale: '单位应为 bar' },
    { id: 'P3', op: 'remove', target: 'OLD_COL@PV', rationale: '已废弃' },
  ]);
  const r1 = ingestProposals({ storeDir: store, runDir: run1, runId: 'runH0001', lineKey: 'lekai-fw3-mdo', dataColumns: ['NEW_SENSOR@PV', 'F_PS005@PV', 'OLD_COL@PV'], applyFn });
  const additive = r1.records.find((x) => x.op === 'add_missing_parameter');
  const correction = r1.records.find((x) => x.op === 'correct_unit');
  const removal = r1.records.find((x) => x.op === 'remove');
  assert.equal(additive.status, 'applied');
  assert.ok(additive.applied && additive.applied.version);
  assert.equal(correction.status, 'pending_corroboration');
  assert.equal(removal.status, 'pending_approval');

  // second independent run with same change → correction auto-applies
  const run2 = makeRun('runH0002', [{ id: 'P2', op: 'correct_unit', target: 'F_PS005@PV', field: 'unit', to: 'bar', rationale: '再次确认' }]);
  const r2 = ingestProposals({ storeDir: store, runDir: run2, runId: 'runH0002', lineKey: 'lekai-fw3-mdo', dataColumns: ['F_PS005@PV'], applyFn });
  assert.equal(r2.records[0].status, 'applied');
  assert.equal(r2.records[0].corroborating_runs.length, 2);

  // idempotent re-ingest of the same run
  const again = ingestProposals({ storeDir: store, runDir: run1, runId: 'runH0001', lineKey: 'lekai-fw3-mdo', dataColumns: ['NEW_SENSOR@PV', 'F_PS005@PV', 'OLD_COL@PV'], applyFn });
  assert.equal(again.records.length, 0);

  // approve removal
  const removalRec = readProposalLog(store).find((x) => x.op === 'remove');
  const decided = decideProposal({ storeDir: store, proposalId: removalRec.proposal_id, action: 'approve', applyFn });
  assert.equal(decided.status, 'applied');
});

// ── Merge + overrides ───────────────────────────────────────────────────

test('merge: findings move to target line, source becomes alias, consensus recomputed', () => {
  const store = tmpDir('store');
  const runA = tmpDir('run');
  makeStabilityRun(runA, { runId: 'runI0001' });
  ingestRun({ storeDir: store, runDir: runA, runId: 'runI0001', intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability' });

  const qsRun = tmpDir('run');
  makeQuickScreenRun(qsRun, { runId: 'runI0002' });
  const qs = ingestRun({ storeDir: store, runDir: qsRun, runId: 'runI0002', intent: 'quick-screen', sceneKey: 'lekai-defect-quickscreen' });
  assert.equal(qs.lineKey, 'lekai-defect-quickscreen');

  const merged = mergeLines({ storeDir: store, fromKey: 'lekai-defect-quickscreen', intoKey: 'lekai-fw3-mdo' });
  assert.ok(merged.added > 0);
  assert.ok(merged.consensus.entries.some((e) => e.subject === 'W1C80@PV1_mean'));
  const reg = JSON.parse(readFileSync(join(store, 'lines.json'), 'utf-8'));
  assert.equal(reg.lines['lekai-defect-quickscreen'], undefined);
  assert.ok(reg.lines['lekai-fw3-mdo'].aliases.includes('lekai-defect-quickscreen'));
  // 别名可反查
  assert.equal(findLineByAlias(store, 'lekai-defect-quickscreen').lineKey, 'lekai-fw3-mdo');
});

test('override: manual refute wins over computed grade; unrefute restores', () => {
  const store = tmpDir('store');
  const runDir = tmpDir('run');
  makeStabilityRun(runDir, { runId: 'runJ0001' });
  const r = ingestRun({ storeDir: store, runDir, runId: 'runJ0001', intent: 'stability-report', sceneKey: 'lekai-fw3-mdo-stability' });
  const entryKey = 'MD_TH001@PV||spc_violation';
  const after = overrideEntry({ storeDir: store, lineKey: r.lineKey, entryKey, status: 'refuted', reason: '人工复核:该判异源于传感器校验' });
  const entry = after.entries.find((e) => e.entry_key === entryKey);
  assert.equal(entry.grade, 'refuted');
  const restored = overrideEntry({ storeDir: store, lineKey: r.lineKey, entryKey, status: 'active' });
  assert.notEqual(restored.entries.find((e) => e.entry_key === entryKey).grade, 'refuted');
});
