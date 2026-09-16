#!/usr/bin/env node
// check-bib.mjs — structural gate for refs.bib.
//
// Two defects bit this file during the integrity pass, both from slicing an entry
// from `indexOf('{key,') - 1` on the assumption that the text is `@{key,` when it
// is actually `@type{key,`:
//   1. orphaned entry-type fragments (`@articl`, `@mis`) left behind;
//   2. the closing brace of the PREVIOUS entry consumed or duplicated.
// Both are syntax errors that BibTeX reports only as "(Error may have been on
// previous line)", which points nowhere useful. This gate names them.
//
//   node scripts/check-bib.mjs [path/to/refs.bib]

import fs from 'node:fs';

const BIB = process.argv[2] || '../paper/refs.bib';
const raw = fs.readFileSync(BIB, 'utf8');
const lines = raw.split(/\r?\n/);
const problems = [];

// 1. every line starting with '@' must be a complete, well-formed header
lines.forEach((l, i) => {
  const t = l.trim();
  if (t.startsWith('@') && !/^@\w+\s*\{\s*[^,\s]+\s*,/.test(t)) {
    problems.push(`line ${i + 1}: malformed or truncated entry header: ${JSON.stringify(t)}`);
  }
});

// 2. brace balance per entry
const entries = raw.split(/(?=^@)/m).filter((s) => s.trim().startsWith('@'));
const seen = new Set();
for (const e of entries) {
  const key = (e.match(/^@\w+\s*\{\s*([^,\s]+)/) || [])[1];
  if (!key) continue;
  if (seen.has(key)) problems.push(`duplicate entry key: ${key}`);
  seen.add(key);
  const open = (e.match(/\{/g) || []).length;
  const close = (e.match(/\}/g) || []).length;
  if (open !== close) problems.push(`unbalanced braces in ${key}: ${open} '{' vs ${close} '}'`);
}

// 3. every entry needs year and title
for (const e of entries) {
  const key = (e.match(/^@\w+\s*\{\s*([^,\s]+)/) || [])[1];
  if (!key) continue;
  if (!/\byear\s*=/.test(e)) problems.push(`${key}: no year field`);
  if (!/\btitle\s*=/.test(e)) problems.push(`${key}: no title field`);
}

// 4. trailing comma followed by a blank line, or a comma on its own line —
//    the exact shape a bad splice produces
lines.forEach((l, i) => {
  if (/^\s*,\s*$/.test(l)) problems.push(`line ${i + 1}: a comma sits alone on its line (bad splice)`);
  if (/,\s*,/.test(l)) problems.push(`line ${i + 1}: doubled comma`);
});

console.log(`\n=== refs.bib structural check ===`);
console.log(`  entries: ${entries.length}   lines: ${lines.length}`);
if (!problems.length) {
  console.log('  OK — every entry header is well-formed, braces balance, keys are unique.\n');
  process.exit(0);
}
console.log(`\n  ${problems.length} PROBLEM(S):`);
for (const p of problems) console.log(`    !! ${p}`);
console.log('');
process.exit(1);
