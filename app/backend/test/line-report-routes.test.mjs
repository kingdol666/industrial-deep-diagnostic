// line-report routes e2e — spawns the real backend (auth off, isolated DB and
// CLOSEDLOOP_DATA_DIR) and drives POST /api/line-report/tasks to a finished
// report through the real skill CLIs.
import { describe, test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const backendDir = join(here, '..');
const repoRoot = join(backendDir, '..', '..');
const PORT = '3978';
const BASE = `http://localhost:${PORT}`;
const DATA_ROOT = join(repoRoot, 'workspace', `line-report-test-${process.pid}`);

let child;

async function waitHealthy(timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`${BASE}/api/health`);
      if (r.ok) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error('backend did not become healthy');
}

async function req(method, path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(120000),
  });
  let payload = null;
  try { payload = await r.json(); } catch { /* empty */ }
  return { status: r.status, body: payload };
}

async function pollUntil(fn, { timeoutMs = 180000, intervalMs = 1200, label } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    last = await fn();
    if (last.done) return last.value;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`poll timeout: ${label}`);
}

function writeStableCsv(path, n = 600) {
  const rows = ['t,temp,press,rate,yield_pct'];
  for (let i = 0; i < n; i++) {
    // bounded noise (±1.8 sigma uniform) keeps Nelson violations near zero
    const u = () => (Math.random() * 3.6 - 1.8);
    rows.push([
      new Date(Date.UTC(2026, 9, 1, 8, 0, 0) + i * 60000).toISOString(),
      (85 + u() * 0.03).toFixed(4),
      (0.6 + u() * 0.0008).toFixed(5),
      (120 + u() * 0.25).toFixed(3),
      (98.5 + u() * 0.15).toFixed(3),
    ].join(','));
  }
  writeFileSync(path, rows.join('\n'));
}

describe('line-report routes', { timeout: 240000 }, () => {
  let dataCsv;

  before(async () => {
    mkdirSync(DATA_ROOT, { recursive: true });
    dataCsv = join(DATA_ROOT, 'stable_line.csv');
    writeStableCsv(dataCsv);
    child = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
      cwd: backendDir,
      env: {
        ...process.env,
        PORT, SERVER_PORT: PORT,
        AUTH_ENABLED: '0',
        DATABASE_PATH: join(mkdtempSync(join(tmpdir(), 'lsr-db-')), 'e2e.db'),
        CLOSEDLOOP_DATA_DIR: DATA_ROOT,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    child.stderr.on('data', () => {});
    await waitHealthy();
  });

  after(() => {
    child?.kill();
    try { rmSync(DATA_ROOT, { recursive: true, force: true }); } catch { /* win lock */ }
  });

  test('submit → completed with A-grade report, gate-passed html reachable', async () => {
    const created = await req('POST', '/api/line-report/tasks', {
      data_path: dataCsv,
      line_id: 'L1-TEST',
      time_col: 't',
    });
    assert.equal(created.status, 200, JSON.stringify(created.body));
    assert.ok(created.body.data.task_id);

    const final = await pollUntil(async () => {
      const v = await req('GET', `/api/line-report/tasks/${created.body.data.task_id}`);
      const done = v.body?.data?.status === 'completed' || v.body?.data?.status === 'failed';
      return { done, value: v.body?.data };
    }, { label: 'line-report task' });

    assert.equal(final.status, 'completed', JSON.stringify(final).slice(0, 600));
    assert.ok([0, 1].includes(final.exit_code), `exit code ${final.exit_code}`);
    const summary = final.result.report_summary;
    assert.ok(summary.score >= 85, `score ${summary.score}`);
    assert.equal(summary.grade, 'A');
    assert.equal(final.result.report_summary.status, 'ok');
    assert.ok(final.result.html_url.includes('/workspace-files/'));

    const html = await fetch(`${BASE}${final.result.html_url}`);
    assert.equal(html.status, 200);
    const text = await html.text();
    assert.ok(text.includes('产线运行稳定性报告'));
    assert.ok(text.includes('L1-TEST'));
  });

  test('directory input adaptively selects a primary table and audits auxiliary files', { timeout: 180000 }, async () => {
    const dir = join(DATA_ROOT, 'adaptive-folder');
    mkdirSync(dir, { recursive: true });
    const dcs = join(dir, 'process_timeseries.csv');
    writeStableCsv(dcs, 240);
    writeFileSync(join(dir, 'qc_shift_8h.csv'), 'time,yield_pct\\n'
      + Array.from({ length: 63 }, (_, i) => `${new Date(Date.UTC(2026, 9, 1, i)).toISOString()},${98 + i / 100}`).join('\\n'));
    writeFileSync(join(dir, 'maintenance_log.csv'), 'event_time,event\\n2026-10-02T00:00:00Z,filter change\\n');
    writeFileSync(join(dir, 'README.md'), '# Mixed folder\\nAuxiliary files have different cadence.');
    writeFileSync(join(dir, 'ground_truth.md'), '# Must not be loaded by preprocessing');
    writeFileSync(join(dir, 'ontology.json'), JSON.stringify({
      scene: { name: 'FOLDER-TEST', process_type: 'batch' },
      signals: {},
    }));

    const created = await req('POST', '/api/line-report/tasks', {
      data_dir: dir, input_kind: 'directory', line_id: 'FOLDER-TEST', time_col: null,
    });
    assert.equal(created.status, 200, JSON.stringify(created.body));
    const final = await pollUntil(async () => {
      const v = await req('GET', `/api/line-report/tasks/${created.body.data.task_id}`);
      const done = v.body?.data?.status === 'completed' || v.body?.data?.status === 'failed';
      return { done, value: v.body?.data };
    }, { label: 'folder line-report task' });
    assert.equal(final.status, 'completed', JSON.stringify(final).slice(0, 700));
    const runDir = final.result.run_dir;
    const manifest = JSON.parse(await import('fs').then(({ readFileSync }) => readFileSync(join(runDir, '00_input', 'input_manifest.json'), 'utf8')));
    const report = JSON.parse(await import('fs').then(({ readFileSync }) => readFileSync(final.result.report_path, 'utf8')));
    assert.equal(manifest.input_kind, 'directory');
    assert.equal(manifest.selected_table.file, 'process_timeseries.csv');
    assert.equal(manifest.scoring_table.rows, 240);
    assert.equal(manifest.scoring_table.time_column, 't');
    assert.ok(manifest.scoring_table.sha256.startsWith('sha256:'));
    const dispositions = Object.fromEntries(manifest.source_dispositions.map((item) => [item.relative_path, item]));
    assert.equal(dispositions['qc_shift_8h.csv'].role, 'auxiliary');
    assert.equal(dispositions['qc_shift_8h.csv'].disposition, 'excluded_from_scoring');
    assert.equal(dispositions['maintenance_log.csv'].role, 'event');
    assert.equal(dispositions['maintenance_log.csv'].disposition, 'excluded_from_scoring');
    assert.equal(dispositions['README.md'].disposition, 'context_only');
    assert.equal(dispositions['ground_truth.md'].disposition, 'protected_excluded');
    assert.equal(dispositions['ground_truth.md'].sha256, null);
    assert.equal(dispositions['ground_truth.md'].size_bytes, null);
    assert.equal(dispositions['ontology.json'].disposition, 'context_only');
    assert.ok(final.result.report_summary.n_parameters_assessed > 0);
    assert.equal(report.data.n_rows_used, 240);
    assert.equal(report.data.preprocessing.mode, 'directory_adaptive');
    assert.equal(report.data.preprocessing.source_directory, dir);
    assert.ok(String(report.condition?.ontology?.path || '').includes('ontology.json'),
      `ontology auto-wired, got ${JSON.stringify(report.condition?.ontology)}`);
    assert.ok(report.data.preprocessing.manifest_path.endsWith('input_manifest.json'));
    assert.ok(report.data.preprocessing.source_files.some((item) => item.relative_path === 'process_timeseries.csv' && item.disposition === 'selected'));
    assert.ok(final.result.html_url.includes('/workspace-files/'));
    const detail = await req('GET', `/api/line-report/runs/${created.body.data.task_id}`);
    assert.equal(detail.status, 200);
    assert.equal(detail.body.data.report.report_id, report.report_id);
  });

  test('folder API rejects mismatched kind, path escape and non-directories', async () => {
    const wrongKind = await req('POST', '/api/line-report/tasks', {
      data_dir: DATA_ROOT, input_kind: 'file',
    });
    assert.equal(wrongKind.status, 400);
    const outside = await req('POST', '/api/line-report/tasks', {
      data_dir: 'C:/Windows', input_kind: 'directory',
    });
    assert.equal(outside.status, 400);
    const notDir = await req('POST', '/api/line-report/tasks', {
      data_dir: dataCsv, input_kind: 'directory',
    });
    assert.equal(notDir.status, 400);
  });

  test('missing data_path → 400', async () => {
    const r = await req('POST', '/api/line-report/tasks', { line_id: 'x' });
    assert.equal(r.status, 400);
    assert.match(r.body.error, /data_path/);
  });

  test('path outside project root → 400', async () => {
    const r = await req('POST', '/api/line-report/tasks', {
      data_path: 'C:/Windows/win.ini',
    });
    assert.equal(r.status, 400);
  });

  test('directory and unsupported extension are rejected before task creation', async () => {
    const folder = await req('POST', '/api/line-report/tasks', { data_path: DATA_ROOT });
    assert.equal(folder.status, 400);
    assert.match(folder.body.error, /expected a data file/);
    const unsupported = join(DATA_ROOT, 'notes.txt');
    writeFileSync(unsupported, 'not tabular data');
    const ext = await req('POST', '/api/line-report/tasks', { data_path: unsupported });
    assert.equal(ext.status, 400);
    assert.match(ext.body.error, /unsupported file type/);
  });

  test('tiny data → completed with honest not_assessable (code 2)', async () => {
    const tiny = join(DATA_ROOT, 'tiny.csv');
    writeFileSync(tiny, 't,temp\n'
      + Array.from({ length: 20 }, (_, i) =>
        `${new Date(Date.UTC(2026, 9, 1, 8, i)).toISOString()},${85 + i * 0.001}`).join('\n'));
    const created = await req('POST', '/api/line-report/tasks', {
      data_path: tiny, line_id: 'TINY', time_col: 't',
    });
    assert.equal(created.status, 200);
    const final = await pollUntil(async () => {
      const v = await req('GET', `/api/line-report/tasks/${created.body.data.task_id}`);
      const done = v.body?.data?.status === 'completed' || v.body?.data?.status === 'failed';
      return { done, value: v.body?.data };
    }, { label: 'tiny task' });
    assert.equal(final.status, 'completed');
    assert.equal(final.exit_code, 2);
    assert.equal(final.result.outcome, 'not_assessable');
    assert.equal(final.result.report_summary.score, null);
  });

  test('GET /runs lists the finished report; unknown task → 404', async () => {
    const runs = await req('GET', '/api/line-report/runs');
    assert.equal(runs.status, 200);
    assert.ok(Array.isArray(runs.body.data));
    const mine = runs.body.data.find((x) => x.line_id === 'L1-TEST');
    assert.ok(mine, 'report listed');
    assert.equal(mine.grade, 'A');

    const missing = await req('GET', '/api/line-report/tasks/NOPE');
    assert.equal(missing.status, 404);
  });
});
