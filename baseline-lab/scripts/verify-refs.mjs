#!/usr/bin/env node
// verify-refs.mjs — resolve every DOI in refs.bib against the publisher-deposited
// Crossref record and confirm it points at the SAME work the bibliography claims.
//
// This is the assertion that matters: an earlier audit found seven DOIs that
// resolved to entirely different papers, so "the DOI exists" is not sufficient —
// the resolved title must MATCH the cited title.
//
//   node scripts/verify-refs.mjs [path/to/refs.bib]
//
// Network is required. Exits non-zero if any DOI fails to resolve or does not match.

import fs from 'node:fs';

const bibPath = process.argv[2] || '../paper/refs.bib';
const text = fs.readFileSync(bibPath, 'utf8');

// ---- parse entries ---------------------------------------------------------
const entries = [];
const re = /@(\w+)\s*\{\s*([^,]+),([\s\S]*?)\n\}/g;
let m;
while ((m = re.exec(text))) {
  const body = m[3];
  const field = (name) => {
    const f = new RegExp(`\\b${name}\\s*=\\s*[{"]([\\s\\S]*?)[}"],?\\s*(\\n|$)`, 'i').exec(body + '\n');
    return f ? f[1].replace(/\s+/g, ' ').trim() : '';
  };
  entries.push({ key: m[2].trim(), type: m[1], title: field('title'), doi: field('doi'), year: field('year') });
}

const norm = (s) => String(s)
  .replace(/\\[a-zA-Z]+\{?|\\?[{}]/g, ' ')     // strip LaTeX macros/braces
  .replace(/[^a-z0-9 ]/gi, ' ')
  .replace(/\s+/g, ' ')
  .trim()
  .toLowerCase();

function titleMatches(cited, resolved) {
  const a = norm(cited);
  const b = norm(resolved);
  if (!a || !b) return { ok: false, why: 'missing title' };
  if (a === b) return { ok: true, why: 'exact' };
  if (b.includes(a) || a.includes(b)) return { ok: true, why: 'containment' };
  // token overlap: >=70% of the cited title's significant tokens appear
  const toks = a.split(' ').filter((w) => w.length > 3);
  const hit = toks.filter((w) => b.includes(w)).length;
  const ratio = toks.length ? hit / toks.length : 0;
  if (ratio >= 0.7) return { ok: true, why: `token overlap ${(ratio * 100).toFixed(0)}%` };
  return { ok: false, why: `token overlap only ${(ratio * 100).toFixed(0)}%` };
}

console.log(`\n=== resolving ${entries.filter((e) => e.doi).length} DOI(s) from ${bibPath} ===\n`);

let pass = 0, fail = 0, skipped = 0;
const problems = [];

for (const e of entries) {
  if (!e.doi) {
    skipped++;
    console.log(`  SKIP  ${e.key.padEnd(28)} no DOI (verified separately)`);
    continue;
  }
  process.stdout.write(`  ...   ${e.key.padEnd(28)} ${e.doi}\r`);
  let js;
  let registry = 'crossref';
  try {
    const r = await fetch(`https://api.crossref.org/works/${encodeURIComponent(e.doi)}`, {
      headers: { accept: 'application/json' },
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    js = (await r.json()).message;
  } catch (err) {
    // Datasets (Harvard Dataverse, Kaggle, Zenodo, Mendeley) register with
    // DataCite, not Crossref, so a Crossref 404 is not evidence of a bad DOI.
    try {
      const r2 = await fetch(`https://api.datacite.org/dois/${encodeURIComponent(e.doi)}`, {
        headers: { accept: 'application/vnd.api+json' },
      });
      if (!r2.ok) throw new Error(`HTTP ${r2.status}`);
      const d = (await r2.json()).data.attributes;
      registry = 'datacite';
      js = {
        title: (d.titles || []).map((t) => t.title),
        'container-title': [d.publisher],
        publisher: d.publisher,
        _datacite_state: d.state,
      };
    } catch (err2) {
      fail++;
      problems.push(`${e.key}: DOI did not resolve in Crossref (${err.message}) or DataCite (${err2.message})`);
      console.log(`  FAIL  ${e.key.padEnd(28)} ${e.doi}  -> Crossref ${err.message}; DataCite ${err2.message}`);
      continue;
    }
  }
  const resolvedTitle = Array.isArray(js.title) ? js.title[0] : String(js.title || '');
  const match = titleMatches(e.title, resolvedTitle);
  if (match.ok) {
    pass++;
    const venue = js['container-title']?.[0] || js.publisher || '';
    console.log(`  PASS  ${e.key.padEnd(28)} [${registry.padEnd(8)}] ${String(venue).slice(0, 30).padEnd(32)} ${match.why}`);
  } else {
    fail++;
    problems.push(`${e.key}: DOI ${e.doi} resolves to a DIFFERENT work\n        cited   : ${e.title.slice(0, 100)}\n        resolved: ${resolvedTitle.slice(0, 100)}`);
    console.log(`  FAIL  ${e.key.padEnd(28)} -> resolves to: ${resolvedTitle.slice(0, 60)}`);
  }
  await new Promise((r) => setTimeout(r, 120)); // be polite to Crossref
}

console.log(`\n${'='.repeat(90)}`);
console.log(`DOI resolution: PASS ${pass}  FAIL ${fail}  SKIP(no DOI) ${skipped}  |  entries ${entries.length}`);
if (problems.length) {
  console.log('\nPROBLEMS:');
  for (const p of problems) console.log(`  !! ${p}`);
}
console.log('');
process.exit(fail === 0 ? 0 : 1);
