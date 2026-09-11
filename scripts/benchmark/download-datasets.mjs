#!/usr/bin/env node
// download-datasets.mjs — verified public-dataset fetcher for the benchmark.
//
// Safety (enforced on every request, including each redirect hop):
//   · only http/https schemes
//   · hostname may not be localhost/*.local/*.internal
//   · hostname resolved addresses may not be loopback, private, link-local,
//     CGNAT, multicast or reserved ranges
// Files are written under data/benchmark/raw/<dataset>/ and recorded with
// sha256 in data/benchmark/downloads.lock.json (resumable + auditable).
//
// Usage:
//   node scripts/benchmark/download-datasets.mjs --list
//   node scripts/benchmark/download-datasets.mjs                    # default set
//   node scripts/benchmark/download-datasets.mjs --only secom,cmapss
//   node scripts/benchmark/download-datasets.mjs --include-large    # + FEMTO (~1.5 GB)
//   node scripts/benchmark/download-datasets.mjs --force

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import dns from 'node:dns/promises';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const RAW = path.join(ROOT, 'data', 'benchmark', 'raw');
const LOCK = path.join(ROOT, 'data', 'benchmark', 'downloads.lock.json');

// ── Dataset registry (URLs probed live; see docs/benchmark-design.md) ──
const DATASETS = [
  {
    id: 'secom',
    name: 'SECOM (UCI) — semiconductor process, 1567×591, imbalanced fault labels',
    license: 'UCI open (CC BY 4.0)',
    sizeMb: 2,
    extract: 'zip',
    files: [{ url: 'https://archive.ics.uci.edu/static/public/179/secom.zip', name: 'secom.zip' }],
  },
  {
    id: 'cmapss',
    name: 'NASA C-MAPSS — turbofan degradation (RUL benchmark family FD001-FD004)',
    license: 'NASA open data',
    sizeMb: 60,
    extract: 'zip',
    files: [{ url: 'https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip', name: 'cmapss.zip' }],
  },
  {
    id: 'paderborn',
    name: 'Paderborn KAt bearing data center — K001/K002 (real damage), KA04/KA15 (artificial)',
    license: 'Free for research (cite Paderborn KAt)',
    sizeMb: 120,
    extract: 'rar',
    files: [
      { url: 'https://groups.uni-paderborn.de/kat/BearingDataCenter/K001.rar', name: 'K001.rar' },
      { url: 'https://groups.uni-paderborn.de/kat/BearingDataCenter/K002.rar', name: 'K002.rar' },
      { url: 'https://groups.uni-paderborn.de/kat/BearingDataCenter/KA04.rar', name: 'KA04.rar' },
      { url: 'https://groups.uni-paderborn.de/kat/BearingDataCenter/KA15.rar', name: 'KA15.rar' },
    ],
  },
  {
    id: 'femto',
    name: 'FEMTO-ST / PRONOSTIA bearing run-to-failure (NASA PCoE mirror)',
    license: 'NASA PCoE mirror (cite FEMTO-ST/NASA)',
    sizeMb: 1600,
    large: true,
    extract: 'zip',
    files: [{ url: 'https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip', name: 'femto-bearings.zip' }],
  },
  {
    id: 'cwru',
    name: 'CWRU bearing fault dataset (form-gated at the canonical site)',
    license: 'Free for research — cite Case Western Reserve University',
    sizeMb: 300,
    // Canonical files are behind the site's download form; scripted fetch is not
    // possible. Kept in the registry so the plan/report can state the gap honestly.
    manual: {
      landing: 'https://engineering.case.edu/bearingdatacenter/download-data-file',
      note: 'Download the 12 kHz Drive-End .mat set manually (97/105/118/130/169/209/3001-3004 + Normal_0/1/2/3) into data/benchmark/raw/cwru/ then re-run make_dataset_manifest.mjs.',
      mirrorCandidates: [
        'https://raw.githubusercontent.com/liguge/CWRU-Bearing-Data/main/97.mat',
      ],
    },
    files: [],
  },
];

const args = process.argv.slice(2);
const flag = (n) => args.includes(n);
const opt = (n, d) => (args.indexOf(n) >= 0 && args[args.indexOf(n) + 1] ? args[args.indexOf(n) + 1] : d);

if (flag('--list')) {
  for (const d of DATASETS) {
    console.log(`${d.id.padEnd(10)} ${String(d.sizeMb).padStart(5)}MB  ${d.manual ? 'MANUAL ' : 'auto   '} ${d.name}`);
  }
  process.exit(0);
}

// ── URL / host safety (Mimosa constraint) ──
const BLOCKED_HOST_RE = /^(localhost|.*\.localhost|.*\.local|.*\.internal|.*\.home\.arpa)$/i;

function ipIsBlocked(ip) {
  const kind = ip.includes(':') ? 6 : 4;
  if (kind === 6) {
    const low = ip.toLowerCase();
    if (low === '::1' || low === '::') return true;
    if (/^f[cd][0-9a-f]{2}:/.test(low)) return true;   // fc00::/7 unique-local
    if (/^fe[89ab][0-9a-f]:/.test(low)) return true;   // fe80::/10 link-local
    const mapped = low.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
    if (mapped) return ipIsBlocked(mapped[1]);
    return false;
  }
  const [a, b] = ip.split('.').map(Number);
  if (a === 0 || a === 10 || a === 127) return true;          // this-net, private, loopback
  if (a === 169 && b === 254) return true;                    // link-local
  if (a === 172 && b >= 16 && b <= 31) return true;           // private
  if (a === 192 && b === 168) return true;                    // private
  if (a === 100 && b >= 64 && b <= 127) return true;          // CGNAT
  if (a === 192 && b === 0) return true;                      // IETF protocol assignments
  if (a === 198 && (b === 18 || b === 19)) return true;       // benchmarking
  if (a >= 224) return true;                                  // multicast + reserved
  return false;
}

async function assertSafeUrl(rawUrl) {
  let u;
  try {
    u = new URL(rawUrl);
  } catch {
    throw new Error(`invalid URL: ${rawUrl}`);
  }
  if (u.protocol !== 'https:' && u.protocol !== 'http:') {
    throw new Error(`blocked scheme "${u.protocol}" (only http/https): ${rawUrl}`);
  }
  if (BLOCKED_HOST_RE.test(u.hostname)) {
    throw new Error(`blocked host "${u.hostname}": ${rawUrl}`);
  }
  // IP literal → direct check; otherwise resolve every address
  const addrs = /^[\d.]+$/.test(u.hostname) || u.hostname.includes(':')
    ? [u.hostname]
    : (await dns.lookup(u.hostname, { all: true })).map((a) => a.address);
  for (const a of addrs) {
    if (ipIsBlocked(a)) throw new Error(`blocked resolved address ${a} for ${u.hostname}`);
  }
  return u;
}

async function safeFetch(url, { maxHops = 5, headerTimeoutMs = 30000 } = {}) {
  let current = url;
  for (let hop = 0; hop <= maxHops; hop++) {
    await assertSafeUrl(current);
    // Timeout applies to the HEADER phase only — large bodies must stream
    // without a wall-clock cap (a bound signal would abort the body midway).
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), headerTimeoutMs);
    let res;
    try {
      res = await fetch(current, {
        redirect: 'manual',
        signal: controller.signal,
        headers: { 'user-agent': 'idd-benchmark-fetcher/1.0 (research; node)' },
      });
    } finally {
      clearTimeout(timer);
    }
    if (res.status >= 300 && res.status < 400) {
      const loc = res.headers.get('location');
      if (!loc) throw new Error(`redirect without location from ${current}`);
      current = new URL(loc, current).toString();
      continue;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${current}`);
    return { res, finalUrl: current };
  }
  throw new Error(`too many redirects for ${url}`);
}

function sha256File(p) {
  const h = crypto.createHash('sha256');
  h.update(fs.readFileSync(p));
  return h.digest('hex');
}

function extractArchive(dir, archivePath, kind) {
  const extractDir = path.join(dir, 'extracted');
  fs.mkdirSync(extractDir, { recursive: true });
  try {
    if (kind === 'zip') {
      execFileSync('unzip', ['-o', '-q', archivePath, '-d', extractDir], { stdio: 'ignore' });
    } else if (kind === 'rar') {
      // bsdtar (libarchive) reads RAR; try PATH then the Anaconda-shipped copy
      const bsdtar = process.platform === 'win32' && fs.existsSync('D:\\anaconda3\\Library\\bin\\bsdtar.exe')
        ? 'D:\\anaconda3\\Library\\bin\\bsdtar.exe'
        : 'bsdtar';
      execFileSync(bsdtar, ['-xf', archivePath, '-C', extractDir], { stdio: 'ignore' });
    }
    return { ok: true, extractDir };
  } catch (e) {
    return { ok: false, error: e.message.split('\n')[0] };
  }
}

async function downloadFile(datasetId, file, dir, { force }) {
  const dest = path.join(dir, file.name);
  if (!force && fs.existsSync(dest) && fs.statSync(dest).size > 0) {
    const sha = sha256File(dest);
    return { name: file.name, url: file.url, path: path.relative(ROOT, dest).replace(/\\/g, '/'), bytes: fs.statSync(dest).size, sha256: sha, cached: true };
  }
  fs.mkdirSync(dir, { recursive: true });
  const tmp = `${dest}.part`;
  const { res } = await safeFetch(file.url);
  if (!res.body) throw new Error(`no body for ${file.url}`);
  await pipeline(Readable.fromWeb(res.body), fs.createWriteStream(tmp));
  fs.renameSync(tmp, dest);
  const bytes = fs.statSync(dest).size;
  return { name: file.name, url: file.url, path: path.relative(ROOT, dest).replace(/\\/g, '/'), bytes, sha256: sha256File(dest), cached: false };
}

async function main() {
  const only = opt('--only', '').split(',').map((s) => s.trim()).filter(Boolean);
  const includeLarge = flag('--include-large');
  const force = flag('--force');
  const maxMb = Number(opt('--max-mb', '2000'));

  const lock = fs.existsSync(LOCK) ? JSON.parse(fs.readFileSync(LOCK, 'utf8')) : { generated_at: null, datasets: {} };
  const summary = [];

  for (const ds of DATASETS) {
    if (only.length && !only.includes(ds.id)) continue;
    if (ds.manual) {
      console.log(`[${ds.id}] MANUAL — ${ds.manual.note}`);
      summary.push({ id: ds.id, status: 'manual', note: ds.manual.note, landing: ds.manual.landing });
      continue;
    }
    if (ds.large && !includeLarge) {
      console.log(`[${ds.id}] SKIPPED (large ~${ds.sizeMb}MB — pass --include-large)`);
      summary.push({ id: ds.id, status: 'skipped-large', sizeMb: ds.sizeMb });
      continue;
    }
    if (ds.sizeMb > maxMb) {
      console.log(`[${ds.id}] SKIPPED (size ${ds.sizeMb}MB > --max-mb ${maxMb})`);
      summary.push({ id: ds.id, status: 'skipped-size', sizeMb: ds.sizeMb });
      continue;
    }

    const dir = path.join(RAW, ds.id);
    const files = [];
    try {
      for (const f of ds.files) {
        const rec = await downloadFile(ds.id, f, dir, { force });
        files.push(rec);
        console.log(`[${ds.id}] ${rec.cached ? 'cached' : 'GET   '} ${rec.name}  ${(rec.bytes / 1048576).toFixed(1)}MB  sha256=${rec.sha256.slice(0, 12)}…`);
      }
      let extraction = null;
      if (ds.extract && files.length) {
        extraction = [];
        for (const f of files) {
          const r = extractArchive(dir, path.join(dir, f.name), ds.extract);
          extraction.push({ file: f.name, ...r, extractDir: r.extractDir ? path.relative(ROOT, r.extractDir).replace(/\\/g, '/') : null });
          console.log(`[${ds.id}] extract ${f.name} → ${r.ok ? 'OK' : `FAILED (${r.error})`}`);
        }
      }
      lock.datasets[ds.id] = { name: ds.name, license: ds.license, files, extraction, fetched_at: new Date().toISOString() };
      summary.push({ id: ds.id, status: 'ok', files: files.length, bytes: files.reduce((a, f) => a + f.bytes, 0) });
    } catch (e) {
      console.error(`[${ds.id}] FAILED: ${e.message}`);
      summary.push({ id: ds.id, status: 'failed', error: e.message });
    }
  }

  lock.generated_at = new Date().toISOString();
  fs.writeFileSync(LOCK, JSON.stringify(lock, null, 1) + '\n');

  const ok = summary.filter((s) => s.status === 'ok');
  const bad = summary.filter((s) => ['failed', 'manual'].includes(s.status));
  console.log(`\n${ok.length} dataset(s) fetched, ${bad.length} needing attention`);
  for (const b of bad) console.log(`  ${b.status}: ${b.id} — ${b.error || b.note || ''}`);
  console.log(`lock: ${path.relative(ROOT, LOCK)}`);
}

main().catch((e) => {
  console.error('fatal:', e.message);
  process.exit(1);
});
