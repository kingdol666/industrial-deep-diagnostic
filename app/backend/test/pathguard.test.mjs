// PathGuard — user-supplied path fragments must provably stay inside their base
// directory. The retired `join(base, input).startsWith(base)` check admitted
// sibling prefixes (`../data-evil` against `.../data`) and encoded traversal;
// these tests pin its replacement (resolveInside / sanitizeFileName) plus the
// HTTP contract of the file routes that used the raw joins.
import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { join, resolve } from 'path';
import { mkdtempSync, mkdirSync, rmSync, existsSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';

const { PathViolationError, resolveInside, isInside, sanitizeFileName } = await import('../src/utils/pathGuard.mjs');
const { DATA_DIR } = await import('../src/services/files.service.mjs');

const WORK = mkdtempSync(join(tmpdir(), 'idd-pathguard-'));
const BASE = join(WORK, 'a', 'data'); // sibling dir with a matching prefix: <WORK>/a/data-evil
const SIBLING = join(WORK, 'a', 'data-evil');

mkdirSync(join(SIBLING), { recursive: true });
writeFileSync(join(SIBLING, 'leak.txt'), 'must not be reachable');

after(() => rmSync(WORK, { recursive: true, force: true }));

function assertViolation(fn, fragment) {
  assert.throws(fn, (err) => {
    assert.ok(err instanceof PathViolationError, `${fragment}: expected PathViolationError, got ${err?.name}: ${err?.message}`);
    assert.equal(err.status, 400, `${fragment}: status`);
    assert.equal(err.code, 'PATH_OUTSIDE_BASE', `${fragment}: code`);
    return true;
  }, `expected ${JSON.stringify(fragment)} to be rejected`);
}

describe('resolveInside — containment by path segments, not string prefix', () => {
  test('rejects parent traversal in forward, backslash and mixed form', () => {
    for (const attack of ['..', '../x', '..\\x', '../data-evil/x', 'a/../../x', 'sub/..\\..\\x']) {
      assertViolation(() => resolveInside(BASE, attack), attack);
    }
  });

  test('rejects the sibling-prefix attack the old startsWith() check allowed', () => {
    // Documents the bypass this test exists for: the string prefix still matches,
    // yet the target is a SIBLING of the base, not a child.
    assert.equal(join(BASE, '../data-evil/leak.txt').startsWith(BASE), true);
    assertViolation(() => resolveInside(BASE, '../data-evil/leak.txt'), '../data-evil/leak.txt');
  });

  test('rejects absolute and drive-relative input', () => {
    const attacks = ['/etc/passwd', 'C:\\Windows\\System32\\config', 'C:../escape'];
    if (process.platform === 'win32') attacks.push('\\\\attacker\\share\\payload');
    for (const attack of attacks) {
      assertViolation(() => resolveInside(BASE, attack), attack);
    }
  });

  test('rejects URL-encoded and double-encoded traversal', () => {
    for (const attack of ['%2e%2e%2fetc', '%2e%2e%5cx', '..%2fx', '%252e%252e%252fetc', '%252e%252e%255cx']) {
      assertViolation(() => resolveInside(BASE, attack), attack);
    }
  });

  test('rejects null bytes in raw and encoded form', () => {
    for (const attack of ['a\0b', '%00', 'sub%00/dir']) {
      assertViolation(() => resolveInside(BASE, attack), JSON.stringify(attack));
    }
  });

  test('rejects components Windows would mangle: trailing dot/space, ADS colon, device names', () => {
    // The verifier's passing-but-hostile vectors: every one of these survived
    // the lexical `..` check because Windows strips/manages the component
    // BEFORE opening it (`.. ` → `..`, `evil.` → `evil`, `NUL` → the device,
    // `file.txt:stream` → an alternate data stream).
    const attacks = [
      'a/.. /x',
      '.. .',
      'sub/.. ./.. ./SECRET',
      'file.txt:stream',
      'NUL',
      'evil. ',
      // same rules, further spellings
      'nul.txt',
      'CON',
      'com1',
      'LPT9.log',
      'report.csv.',
      'a/b ',
      'c%3Astream',       // encoded colon — caught via the decoded form
      'NUL/../ok',        // device component before an otherwise clean path
    ];
    for (const attack of attacks) {
      assertViolation(() => resolveInside(BASE, attack), attack);
    }
  });

  test('still accepts real names containing mid-name dots and spaces', () => {
    assert.equal(resolveInside(BASE, 'my report v2.csv'), resolve(BASE, 'my report v2.csv'));
    assert.equal(resolveInside(BASE, '03_figures/fig-1.2.png'), resolve(BASE, '03_figures/fig-1.2.png'));
    assert.equal(resolveInside(BASE, './sub/./f.csv'), resolve(BASE, 'sub/f.csv'));
    // `CONSOLE.log` / `NULLS.csv` are ordinary names — only exact device stems are refused.
    assert.equal(resolveInside(BASE, 'CONSOLE.log'), resolve(BASE, 'CONSOLE.log'));
    assert.equal(resolveInside(BASE, 'NULLS.csv'), resolve(BASE, 'NULLS.csv'));
  });

  test('rejects non-string and empty input', () => {
    for (const bad of [null, undefined, 42, {}, [], '', Buffer.from('x')]) {
      assertViolation(() => resolveInside(BASE, bad), String(bad));
    }
  });

  test('accepts nested paths and the base itself', () => {
    assert.equal(resolveInside(BASE, 'sub/dir/file.csv'), resolve(BASE, 'sub/dir/file.csv'));
    assert.equal(resolveInside(BASE, './sub'), resolve(BASE, 'sub'));
    assert.equal(resolveInside(BASE, '.'), resolve(BASE)); // the base itself
    assert.equal(resolveInside(BASE, 'v1.2/..data.csv'), resolve(BASE, 'v1.2/..data.csv')); // dots mid-name are not traversal
    assert.ok(isInside(BASE, resolveInside(BASE, 'sub/dir/file.csv')));
  });

  test('rejects ANY `..` segment, even one that would normalize away', () => {
    // Deliberately stricter than resolve()-then-relative(): a `..` segment is
    // refused outright so no downstream consumer can re-interpret the raw string.
    assertViolation(() => resolveInside(BASE, 'a/../b'), 'a/../b');
    assertViolation(() => resolveInside(BASE, 'sub/../file.csv'), 'sub/../file.csv');
  });

  test('isInside mirrors resolveInside: base itself in, sibling out', () => {
    assert.equal(isInside(BASE, BASE), true);
    assert.equal(isInside(BASE, join(BASE, 'sub', 'f.csv')), true);
    assert.equal(isInside(BASE, SIBLING), false);
    assert.equal(isInside(BASE, join(WORK, 'a')), false);
  });
});

describe('sanitizeFileName — attacker-supplied upload names become leaf names', () => {
  test('keeps ordinary names untouched', () => {
    assert.equal(sanitizeFileName('sensor.csv'), 'sensor.csv');
    assert.equal(sanitizeFileName('传感器数据-2026.csv'), '传感器数据-2026.csv');
  });

  test('strips directory components on both separators', () => {
    assert.equal(sanitizeFileName('../../etc/passwd'), 'passwd');
    assert.equal(sanitizeFileName('..\\..\\windows\\system32\\evil.dll'), 'evil.dll');
    assert.equal(sanitizeFileName('dir/sub/file.txt'), 'file.txt');
    assert.equal(sanitizeFileName('a/b/'), 'b');
    assert.equal(sanitizeFileName('C:\\tmp\\payload.exe'), 'payload.exe');
  });

  test('replaces forbidden and control characters', () => {
    assert.equal(sanitizeFileName('bad<name>.csv'), 'bad_name_.csv');
    assert.equal(sanitizeFileName('re\x00port\x1f.csv'), 're_port_.csv');
    // ':' may terminate a drive/stream prefix in win32 basename semantics, so
    // assert the invariant (no forbidden char survives) rather than one exact
    // platform-dependent spelling.
    const cleaned = sanitizeFileName('a:b|c?d*e"f.csv');
    assert.doesNotMatch(cleaned, /[<>:"|?*\x00-\x1f\\/]/);
    assert.match(cleaned, /\.csv$/);
  });

  test('trims, collapses whitespace, strips trailing dots/spaces and caps the length at 200', () => {
    assert.equal(sanitizeFileName('  my  report   v2.csv  '), 'my report v2.csv');
    assert.equal(sanitizeFileName('x'.repeat(300)).length, 200);
    // The length cap is ≤ 200; a cut that lands on a dot is re-stripped because
    // Windows would drop that dot anyway (D11) — 200 only when the cut is clean.
    assert.equal(sanitizeFileName(`${'y'.repeat(199)}x.csv`).length, 200);
    assert.equal(sanitizeFileName(`${'y'.repeat(199)}.csv`), 'y'.repeat(199), 'cap cut on a dot is re-stripped');
    // D11 — Windows silently drops trailing dots/spaces, landing the write on a
    // DIFFERENT name than the one returned to the user; strip them ourselves.
    assert.equal(sanitizeFileName('evil. '), 'evil');
    assert.equal(sanitizeFileName('report.csv.'), 'report.csv');
    assert.equal(sanitizeFileName('report.csv   '), 'report.csv');
    assert.equal(sanitizeFileName('trailing.' + ' ' + '.'), 'trailing');
    assert.equal(sanitizeFileName(`${'z'.repeat(198)}. .`), 'z'.repeat(198), 're-stripped after the length cap');
    assert.equal(sanitizeFileName('. . .'), '', 'nothing usable remains after the strip');
  });

  test('returns empty when nothing usable remains', () => {
    for (const bad of ['', '   ', '.', '..', '///', 'a/..', undefined, null, 42]) {
      assert.equal(sanitizeFileName(bad), '', `expected ${JSON.stringify(bad)} to sanitize to ''`);
    }
  });
});

describe('files routes — traversal params answer 400 PATH_OUTSIDE_BASE, legit paths still work', () => {
  let server;
  let baseUrl;
  let testFolder;
  // A PLAIN (non-dot) name on purpose: the preview endpoint refuses dot path
  // segments (dotfiles/dot-dirs are hidden system names, like the listing hides
  // them) — see files-read-guard.test.mjs. A dot-prefixed fixture would make the
  // "legitimate file still previews" assertion below contradict that rule.
  const TEST_FOLDER_NAME = `pathguard-test-${process.pid}`;

  // Hand-crafted multipart: undici's FormData strips directory components from
  // filenames client-side, which would mask the server-side guard under test.
  function multipart(fields) {
    const boundary = `----idd-pathguard-${process.pid}-${Math.random().toString(16).slice(2)}`;
    const chunks = [];
    for (const [name, value, filename] of fields) {
      const disposition = filename === undefined
        ? `Content-Disposition: form-data; name="${name}"`
        : `Content-Disposition: form-data; name="${name}"; filename="${filename}"\r\nContent-Type: application/octet-stream`;
      chunks.push(Buffer.from(`--${boundary}\r\n${disposition}\r\n\r\n${value}\r\n`));
    }
    chunks.push(Buffer.from(`--${boundary}--\r\n`));
    return { body: Buffer.concat(chunks), contentType: `multipart/form-data; boundary=${boundary}` };
  }

  async function upload(fields) {
    const { body, contentType } = multipart(fields);
    const res = await fetch(`${baseUrl}/api/files/data/upload`, {
      method: 'POST',
      headers: { 'content-type': contentType },
      body,
    });
    return { res, body: await res.json() };
  }

  before(async () => {
    const express = (await import('express')).default;
    const { default: filesRoutes } = await import('../src/routes/files.routes.mjs');
    const app = express();
    app.use(express.json());
    app.use('/api/files', filesRoutes);
    server = app.listen(0);
    await new Promise((r) => server.once('listening', r));
    baseUrl = `http://127.0.0.1:${server.address().port}`;

    testFolder = join(DATA_DIR, TEST_FOLDER_NAME);
    mkdirSync(join(testFolder, 'nested'), { recursive: true });
    writeFileSync(join(testFolder, 'nested', 'sample.csv'), 't,x\n1,2\n');
  });

  after(() => {
    if (server) server.close();
    rmSync(testFolder, { recursive: true, force: true });
  });

  test('GET /data/:folder with encoded traversal → 400 { code: PATH_OUTSIDE_BASE }', async () => {
    const res = await fetch(`${baseUrl}/api/files/data/${encodeURIComponent('../data-evil')}`);
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.equal(body.success, false);
    assert.equal(body.code, 'PATH_OUTSIDE_BASE');
    assert.match(body.error, /Invalid folder/);
  });

  test('GET /data/:folder with backslash traversal param → 400', async () => {
    const res = await fetch(`${baseUrl}/api/files/data/${encodeURIComponent('..\\..\\data')}`);
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.equal(body.success, false);
    assert.equal(body.code, 'PATH_OUTSIDE_BASE');
  });

  test('GET /data/:folder still lists a legitimate nested folder', async () => {
    const res = await fetch(`${baseUrl}/api/files/data/${encodeURIComponent(`${TEST_FOLDER_NAME}/nested`)}`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.success, true);
    assert.deepEqual(body.data.map((e) => e.name), ['sample.csv']);
  });

  test('GET /data/file/* still previews a legitimate data file', async () => {
    const res = await fetch(`${baseUrl}/api/files/data/file/${encodeURIComponent(`data/${TEST_FOLDER_NAME}/nested/sample.csv`)}`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.success, true);
    assert.match(body.data.content, /1,2/);
  });

  test('GET /data/file/* outside the readable roots → 403 Access denied (semantics preserved)', async () => {
    const res = await fetch(`${baseUrl}/api/files/data/file/${encodeURIComponent('../package.json')}`);
    assert.equal(res.status, 403);
    const body = await res.json();
    assert.equal(body.success, false);
    assert.equal(body.error, 'Access denied');
  });

  test('GET /data/file/* with a root-relative non-root path → 403', async () => {
    const res = await fetch(`${baseUrl}/api/files/data/file/package.json`);
    assert.equal(res.status, 403);
    const body = await res.json();
    assert.equal(body.success, false);
    assert.equal(body.error, 'Access denied');
  });

  test('POST /data/upload never lets a traversal filename escape the folder', async () => {
    const { res, body } = await upload([
      ['folder', TEST_FOLDER_NAME],
      ['files', 'a,b\n1,2\n', '../evil.csv'],
    ]);
    assert.equal(res.status, 200);
    assert.equal(body.success, true);
    assert.deepEqual(body.data.map((f) => f.name), ['evil.csv']);
    assert.equal(existsSync(join(testFolder, 'evil.csv')), true);
    assert.equal(existsSync(join(DATA_DIR, '..', 'evil.csv')), false);
    assert.equal(existsSync(join(DATA_DIR, 'evil.csv')), false);
  });

  test('POST /data/upload rejects a filename that sanitizes to nothing', async () => {
    // Busboy forwards a whitespace-only filename verbatim (only `..`-style parts
    // are dropped), so the route must reject it after sanitizing.
    const { res, body } = await upload([
      ['folder', TEST_FOLDER_NAME],
      ['files', 'x', '   '],
    ]);
    assert.equal(res.status, 400);
    assert.equal(body.success, false);
    assert.equal(body.error, 'Invalid file name');
  });

  test('POST /data/upload with a traversal folder → 400 { code: PATH_OUTSIDE_BASE }', async () => {
    const { res, body } = await upload([
      ['folder', '../data-evil'],
      ['files', 'x', 'ok.txt'],
    ]);
    assert.equal(res.status, 400);
    assert.equal(body.success, false);
    assert.equal(body.code, 'PATH_OUTSIDE_BASE');
  });

  test('POST /data/upload refuses a dot filename (e.g. the JWT secret)', async () => {
    // Uploading `.auth-jwt-secret` would overwrite the session-signing key the
    // read path already hides — the write path must refuse dot names too.
    const { res, body } = await upload([
      ['folder', TEST_FOLDER_NAME],
      ['files', 'forged', '.auth-jwt-secret'],
    ]);
    assert.equal(res.status, 400);
    assert.equal(body.success, false);
    assert.equal(body.error, 'Dot files cannot be uploaded');
    assert.equal(existsSync(join(testFolder, '.auth-jwt-secret')), false);
  });

  test('POST /data/upload refuses a dot folder target', async () => {
    const { res, body } = await upload([
      ['folder', '.uploads-evil'],
      ['files', 'x', 'ok.txt'],
    ]);
    assert.equal(res.status, 400);
    assert.equal(body.success, false);
    assert.equal(body.error, 'Dot folders are not valid upload targets');
    assert.equal(existsSync(join(DATA_DIR, '.uploads-evil')), false);
  });
});
