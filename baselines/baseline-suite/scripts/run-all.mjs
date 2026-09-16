// run-all.mjs — fire the full baseline suite against all 12 scenarios (pipeline step 2).
// Usage: node scripts/run-all.mjs [--base http://localhost:5181] [--only case_a,case_b]
const base = (process.argv.indexOf('--base') >= 0 ? process.argv[process.argv.indexOf('--base') + 1] : 'http://localhost:5181').replace(/\/$/, '');
const onlyArg = process.argv.indexOf('--only') >= 0 ? process.argv[process.argv.indexOf('--only') + 1] : '';

const health = await fetch(`${base}/api/scenarios`).then((r) => r.json());
const cases = onlyArg ? health.filter((s) => onlyArg.split(',').includes(s.case_id)) : health;
console.log(`[suite] ${cases.length} scenario(s) via ${base}`);

let ok = 0, fail = 0;
for (const s of cases) {
  const jobs = [['pca', null]];
  if (s.dataset === 'tep') jobs.push(['fe', null]);
  jobs.push(['llm', 'no_candidates']);
  if (s.dataset === 'tep') jobs.push(['llm', 'with_candidates'], ['llm', 'fe_official']);
  for (const [arm, regime] of jobs) {
    const label = `${s.case_id} · ${arm}${regime ? '.' + regime : ''}`;
    try {
      const res = await fetch(`${base}/api/diagnose/${s.case_id}`, {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ arm, regime }),
      });
      if (!res.ok) throw new Error(`${res.status} ${(await res.text()).slice(0, 120)}`);
      const json = await res.json();
      const mode = json.mode ? ` (${json.mode})` : '';
      console.log(`  ✓ ${label}${mode}`);
      ok++;
    } catch (e) {
      console.log(`  ✗ ${label} — ${e.message}`);
      fail++;
    }
  }
}
console.log(`[suite] done: ${ok} run(s) saved to runs/, ${fail} failure(s)`);
process.exit(fail ? 1 : 0);
