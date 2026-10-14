// doe-analysis routes e2e — spawns the real backend (auth off, isolated data
// root) and drives POST /api/doe-analysis/tasks through the real
// industrial-doe-analyzer CLI, including the SSE live-log stream.
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
const PORT = '3976';
const BASE = `http://localhost:${PORT}`;
const DATA_ROOT = join(repoRoot, 'workspace', `doe-analysis-test-${process.pid}`);

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
    signal: AbortSignal.timeout(180000),
  });
  let payload = null;
  try { payload = await r.json(); } catch { /* empty */ }
  return { status: r.status, body: payload };
}

async function pollUntil(fn, { timeoutMs = 240000, intervalMs = 1500, label } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    last = await fn();
    if (last.done) return last.value;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`poll timeout: ${label}`);
}

// observational-style dataset: x drives y with lag 3, z is noise
function writeDataset(path, n = 500) {
  const rows = ['t,x_drive,y_resp,z_noise'];
  let yHist = [];
  for (let i = 0; i < n; i++) {
    const x = Math.sin(i / 25) + (Math.random() - 0.5) * 0.2;
    yHist.unshift(x);
    const y = (yHist[3] ?? 0) * 1.0 + (Math.random() - 0.5) * 0.1;
    const z = (Math.random() - 0.5) * 2;
    rows.push([
      new Date(Date.UTC(2026, 9, 1, 8, 0, 0) + i * 60000).toISOString(),
      x.toFixed(4), y.toFixed(4), z.toFixed(4),
    ].join(','));
  }
  writeFileSync(path, rows.join('\n'));
}

describe('doe-analysis routes', { timeout: 300000 }, () => {
  let dataCsv;

  before(async () => {
    mkdirSync(DATA_ROOT, { recursive: true });
    dataCsv = join(DATA_ROOT, 'process_data.csv');
    writeDataset(dataCsv);
    child = spawn(process.execPath, [join(backendDir, 'src', 'index.mjs')], {
      cwd: backendDir,
      env: {
        ...process.env,
        PORT, SERVER_PORT: PORT,
        AUTH_ENABLED: '0',
        DATABASE_PATH: join(mkdtempSync(join(tmpdir(), 'doe-db-')), 'e2e.db'),
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

  test('submit → completed with artifacts, report html reachable', async () => {
    const created = await req('POST', '/api/doe-analysis/tasks', {
      data_path: dataCsv,
      time_col: 't',
      scene: 'doe-hub-test',
    });
    assert.equal(created.status, 200, JSON.stringify(created.body));
    const taskId = created.body.data.task_id;

    const final = await pollUntil(async () => {
      const v = await req('GET', `/api/doe-analysis/tasks/${taskId}`);
      const done = v.body?.data?.status === 'completed' || v.body?.data?.status === 'failed';
      return { done, value: v.body?.data };
    }, { label: 'doe task' });

    assert.equal(final.status, 'completed', JSON.stringify(final).slice(0, 800));
    assert.ok(final.result.conclusions_summary, 'summary present');
    assert.ok(final.result.report_url?.includes('/workspace-files/'),
      `report_url=${final.result.report_url}`);
    assert.ok(final.result.artifacts.length >= 5, 'artifact manifest');

    const html = await fetch(`${BASE}${final.result.report_url}`);
    assert.equal(html.status, 200);
    const text = await html.text();
    assert.ok(text.length > 4096, 'report html non-trivial');

    // 全量产物端点
    const full = await req('GET', `/api/doe-analysis/runs/${taskId}`);
    assert.equal(full.status, 200);
    assert.ok(full.body.data.conclusions.doe_conclusion);

    const runs = await req('GET', '/api/doe-analysis/runs');
    assert.ok(runs.body.data.some((x) => x.task_id === taskId));
  });

  test('SSE stream replays logs and ends with done', async () => {
    const created = await req('POST', '/api/doe-analysis/tasks', {
      data_path: dataCsv, time_col: 't',
    });
    const taskId = created.body.data.task_id;
    await pollUntil(async () => {
      const v = await req('GET', `/api/doe-analysis/tasks/${taskId}`);
      const done = v.body?.data?.status === 'completed' || v.body?.data?.status === 'failed';
      return { done, value: v.body?.data };
    }, { label: 'doe stream task' });

    const r = await fetch(`${BASE}/api/doe-analysis/tasks/${taskId}/stream`,
      { signal: AbortSignal.timeout(15000) });
    assert.equal(r.headers.get('content-type'), 'text/event-stream');
    const text = await r.text();
    assert.match(text, /event: log/);
    assert.match(text, /event: done/);
    assert.match(text, /"status":\s*"completed"/);
  });

  test('directory and non-CSV files are rejected; unknown task → 404', async () => {
    const folder = await req('POST', '/api/doe-analysis/tasks', { data_path: DATA_ROOT });
    assert.equal(folder.status, 400);
    assert.match(folder.body.error, /expected a data file/);
    const excel = join(DATA_ROOT, 'input.xlsx');
    writeFileSync(excel, 'placeholder');
    const unsupported = await req('POST', '/api/doe-analysis/tasks', { data_path: excel });
    assert.equal(unsupported.status, 400);
    assert.match(unsupported.body.error, /unsupported file type/);
    const bad = await req('POST', '/api/doe-analysis/tasks', {});
    assert.equal(bad.status, 400);
    const missing = await req('GET', '/api/doe-analysis/tasks/NOPE');
    assert.equal(missing.status, 404);
  });

  test('directory input adaptively selects a primary table and audits auxiliary files', { timeout: 240000 }, async () => {
    const dir = join(DATA_ROOT, 'doe-folder');
    mkdirSync(dir, { recursive: true });
    const rows = ['t,x_drive,y_resp,z_noise'];
    for (let i = 0; i < 300; i++) {
      const x = Math.sin(i / 20) + (Math.random() - 0.5) * 0.2;
      rows.push([
        new Date(Date.UTC(2026, 9, 2, 8, 0, 0) + i * 60000).toISOString(),
        x.toFixed(4), (x * 0.8 + (Math.random() - 0.5) * 0.1).toFixed(4),
        (Math.random() - 0.5).toFixed(4),
      ].join(','));
    }
    writeFileSync(join(dir, 'process_timeseries.csv'), rows.join('\n'));
    writeFileSync(join(dir, 'qc_shift_8h.csv'), 'time,yield_pct\n'
      + Array.from({ length: 40 }, (_, i) => `${new Date(Date.UTC(2026, 9, 2, i)).toISOString()},${97 + i / 50}`).join('\n'));
    writeFileSync(join(dir, 'maintenance_log.csv'), 'event_time,event\n2026-10-02T12:00:00Z,filter swap\n');
    writeFileSync(join(dir, 'ontology.json'), JSON.stringify({
      scene: { name: 'doe-folder-test', process_type: 'continuous' },
      signals: {},
    }));

    const created = await req('POST', '/api/doe-analysis/tasks', {
      data_dir: dir,
      input_kind: 'directory',
      time_col: 't',
      scene: 'doe-folder-test',
    });
    assert.equal(created.status, 200, JSON.stringify(created.body));
    const final = await pollUntil(async () => {
      const v = await req('GET', `/api/doe-analysis/tasks/${created.body.data.task_id}`);
      const done = v.body?.data?.status === 'completed' || v.body?.data?.status === 'failed';
      return { done, value: v.body?.data };
    }, { label: 'doe folder task' });
    assert.equal(final.status, 'completed', JSON.stringify(final).slice(0, 800));

    const manifest = JSON.parse(await import('fs').then(({ readFileSync }) => readFileSync(final.result.input_manifest_path, 'utf8')));
    assert.equal(manifest.input_kind, 'directory');
    assert.equal(manifest.selected_table.file, 'process_timeseries.csv');
    const dispositions = Object.fromEntries(manifest.source_dispositions.map((item) => [item.relative_path, item]));
    assert.equal(dispositions['qc_shift_8h.csv'].disposition, 'excluded_from_scoring');
    assert.equal(dispositions['maintenance_log.csv'].disposition, 'excluded_from_scoring');
    assert.equal(dispositions['ontology.json'].disposition, 'context_only');

    const mismatch = await req('POST', '/api/doe-analysis/tasks', { data_dir: dir, input_kind: 'file' });
    assert.equal(mismatch.status, 400);
    const notDir = await req('POST', '/api/doe-analysis/tasks', { data_dir: dataCsv, input_kind: 'directory' });
    assert.equal(notDir.status, 400);
  });
});
