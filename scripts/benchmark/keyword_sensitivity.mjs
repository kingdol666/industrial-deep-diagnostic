#!/usr/bin/env node
// keyword_sensitivity.mjs — re-scores the frozen benchmark corpus under the
// PRE-calibration keyword sets (git 221d061~1) using the grader's exact matching
// logic (zcode_direct_pipeline.mjs:366-390), and writes a provenance-labelled
// addendum artifact results/benchmark/keyword_sensitivity.json.
//
// READ-ONLY wrt canonical artifacts: the only file it writes is the addendum JSON.
// 用法: node scripts/benchmark/keyword_sensitivity.mjs
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const ROOT = path.resolve(import.meta.dirname, "..", "..");
process.chdir(ROOT);

const OLD_REV = "221d061~1"; // parent of the keyword-calibration commit = pre-revision sets
const cur = JSON.parse(fs.readFileSync("scripts/benchmark/cases/benchmark_cases.json", "utf8")).cases;
const oldRaw = execSync(`git show ${OLD_REV}:scripts/benchmark/cases/benchmark_cases.json`, {
  encoding: "utf8",
  maxBuffer: 1 << 24,
  shell: "bash", // tilde/caret revisions must not pass through cmd.exe escaping
});
const oldById = new Map(JSON.parse(oldRaw).cases.map((c) => [c.case_id, c]));

// text built exactly as the grader builds it (zcode_direct_pipeline.mjs:373-378)
const flat = (v) => Array.isArray(v) ? v.map(flat).join(" ")
  : (v && typeof v === "object") ? Object.values(v).map(flat).join(" ") : String(v ?? "");

const scenarios = [];
let oldTop1 = 0, newTop1 = 0, oldTopk = 0, newTopk = 0;
for (const c of cur) {
  if (c.control) continue;
  const g = JSON.parse(fs.readFileSync(path.join("results/benchmark/gradings", `${c.case_id}.json`), "utf8"));
  const runDir = path.isAbsolute(g.run_dir) ? g.run_dir : path.join(ROOT, g.run_dir);
  const D = JSON.parse(fs.readFileSync(path.join(runDir, "04_diagnostics/diagnosis.json"), "utf8"));
  const surviving = D.hypotheses?.surviving ?? [];
  const text = [String(D.primary_finding ?? ""),
    ...surviving.flatMap((h) => [h?.name, flat(h?.physical_logic_chain), flat(h?.supporting_evidence), flat(h?.ontology_data_physics_proof)]),
  ].filter(Boolean).join(" ").toLowerCase();
  const hit = (kw) => (kw || []).some((k) => text.includes(String(k).toLowerCase()));
  const oldKw = oldById.get(c.case_id)?.keywords ?? [];
  const newHit1 = D.diagnosis_type === "DETERMINED" && hit(c.keywords);
  const newHitK = hit(c.keywords);
  const oldHit1 = D.diagnosis_type === "DETERMINED" && hit(oldKw);
  const oldHitK = hit(oldKw);
  newTop1 += newHit1; oldTop1 += oldHit1; newTopk += newHitK; oldTopk += oldHitK;
  scenarios.push({
    case_id: c.case_id,
    diagnosis_type: D.diagnosis_type,
    pre_revision: { top1: oldHit1, topk: oldHitK, n_keywords: oldKw.length },
    calibrated: { top1: newHit1, topk: newHitK, n_keywords: (c.keywords ?? []).length },
    changed: oldHit1 !== newHit1 || oldHitK !== newHitK,
  });
}

const out = {
  artifact: "keyword-sensitivity addendum (post-hoc analysis, not part of the canonical grading)",
  generated_by: "scripts/benchmark/keyword_sensitivity.mjs",
  logic_reference: "scripts/benchmark/zcode_direct_pipeline.mjs:366-390 (grader matching, replicated verbatim)",
  pre_revision_keyword_source: `git show ${OLD_REV}:scripts/benchmark/cases/benchmark_cases.json`,
  calibrated_keyword_commit: "221d061",
  corpus: "results/benchmark/gradings/*.json (canonical, frozen)",
  summary: {
    faults: scenarios.length,
    top1: { pre_revision: `${oldTop1}/${scenarios.length}`, calibrated: `${newTop1}/${scenarios.length}` },
    topk: { pre_revision: `${oldTopk}/${scenarios.length}`, calibrated: `${newTopk}/${scenarios.length}` },
    changed_scenarios: scenarios.filter((s) => s.changed).map((s) => s.case_id),
  },
  scenarios,
};
fs.mkdirSync("results/benchmark", { recursive: true });
fs.writeFileSync(path.join("results/benchmark/keyword_sensitivity.json"), JSON.stringify(out, null, 2) + "\n");
console.log(JSON.stringify(out.summary, null, 2));
console.log("wrote results/benchmark/keyword_sensitivity.json");
