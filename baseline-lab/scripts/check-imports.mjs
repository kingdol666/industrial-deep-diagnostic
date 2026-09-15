#!/usr/bin/env node
// check-imports.mjs — resolve every relative import under server/ and app/.
//
// WHY THIS EXISTS
// ---------------
// Nitro reports an unresolvable relative import as a RollupError at request
// time, and the dev server then hangs instead of serving anything. The symptom
// is "the whole app stopped responding", which points nowhere near the actual
// mistake. A route file one directory deeper needs one more `../`, and that is
// easy to get wrong when adding routes.
//
// This walks every source file, resolves each relative specifier against the
// real filesystem, and fails loudly with the exact file and specifier.

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const SCAN_DIRS = ['server', 'app', 'scripts'];
const EXTS = ['', '.mjs', '.js', '.ts', '.vue', '.json', '.tsx', '.jsx'];
const INDEXES = ['index.mjs', 'index.js', 'index.ts', 'index.vue'];

const files = [];
function walk(dir) {
  if (!fs.existsSync(dir)) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === '.nuxt' || e.name === '.output') continue;
      walk(p);
    } else if (/\.(mjs|js|ts|vue)$/.test(e.name)) {
      files.push(p);
    }
  }
}
for (const d of SCAN_DIRS) walk(path.join(ROOT, d));

function resolves(fromFile, spec) {
  const base = path.resolve(path.dirname(fromFile), spec);
  for (const ext of EXTS) {
    if (ext && fs.existsSync(base + ext) && fs.statSync(base + ext).isFile()) return true;
  }
  if (fs.existsSync(base) && fs.statSync(base).isFile()) return true;
  if (fs.existsSync(base) && fs.statSync(base).isDirectory()) {
    for (const idx of INDEXES) if (fs.existsSync(path.join(base, idx))) return true;
  }
  return false;
}

// import ... from '...'  |  export ... from '...'  |  import('...')
const SPEC = /(?:^|\s)(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)/g;

let checked = 0;
const broken = [];
const SELF = path.resolve(import.meta.filename || import.meta.url.replace('file:///', ''));
for (const f of files) {
  // Skip this checker: its own SPEC regex contains literal '...' examples.
  if (path.resolve(f) === SELF) continue;
  const text = fs.readFileSync(f, 'utf8');
  for (const m of text.matchAll(SPEC)) {
    const spec = m[1] || m[2];
    if (!spec || !spec.startsWith('.')) continue;
    checked++;
    if (!resolves(f, spec)) {
      const line = text.slice(0, m.index).split('\n').length;
      broken.push({ file: path.relative(ROOT, f).replace(/\\/g, '/'), line, spec });
    }
  }
}

console.log(`\nchecked ${checked} relative imports across ${files.length} files under ${SCAN_DIRS.join('/')}\n`);
if (!broken.length) {
  console.log('OK — every relative import resolves.\n');
  process.exit(0);
}
console.log(`BROKEN (${broken.length}):`);
for (const b of broken) console.log(`  ${b.file}:${b.line}  ->  ${b.spec}`);
console.log('\nAn unresolvable import makes Nitro hang instead of serving. Fix before running.\n');
process.exit(1);
