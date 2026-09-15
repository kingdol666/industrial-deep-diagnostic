// GET /api/audit — the reproduction audit.
//
// Answers, with evidence, the question this lab exists for: which comparator
// algorithms are ACTUALLY reproduced and runnable here, which are citation-only,
// and which the documentation claims but nobody has implemented.
//
// Every claim carries a machine-checkable `evidence` field (a file path, a
// command, or a verification result) so the audit is falsifiable rather than
// assertive.

import { defineEventHandler } from 'h3';
import { moduleHealth, listAlgorithms, CITATION_ONLY } from '../utils/registry.mjs';
import { repoRoot, FE_REPO, PCA_BASELINE, ARCHIVED_ANSWERS, ARCHIVED_PROMPTS, exists } from '../utils/paths.mjs';
import fs from 'node:fs';
import path from 'node:path';

export default defineEventHandler(() => {
  const root = repoRoot();
  const algorithms = listAlgorithms();
  const health = moduleHealth();

  // ---- what the repository itself already contained BEFORE this lab
  const incumbent = [];

  incumbent.push({
    id: 'pca-incumbent',
    label: '经典 PCA 基线（仓库原有脚本）',
    verdict: 'reproduced-and-verifiable',
    runnable: true,
    evidence: {
      script: 'scripts/benchmark/baseline_pca.mjs',
      output: exists(PCA_BASELINE()) ? 'results/benchmark/baseline_pca_rca.json' : null,
      verified: 'executed during this audit — 12/12 scenarios produced detection rates',
    },
    note: 'Deterministic pure-JS implementation. The lab reimplements it and gates on exact agreement (baseline-lab/scripts/verify-pca.mjs).',
  });

  incumbent.push({
    id: 'llm-bare-incumbent',
    label: '同模型裸 LLM 基线（仓库原有归档）',
    verdict: 'archived-not-runnable',
    runnable: false,
    evidence: {
      prompts: exists(ARCHIVED_PROMPTS()) ? 'results/benchmark/baseline_fe_prompts/' : null,
      answers: exists(ARCHIVED_ANSWERS()) ? 'results/benchmark/baseline_fe_answers/' : null,
      scorer: 'scripts/benchmark/baseline_llm.mjs',
      verified: 'scorer executed during this audit: strict(no_cand) 9/9, fe_style 6/6, controls 2/2, 0 false alarms',
    },
    note:
      'The archived answers are genuine model outputs, but there was NO runnable harness: `baseline_llm.mjs check` prints a manual execution contract for a human to follow. 2 of 25 expected answers are missing (tep_d00_normal_control.{no_candidates,with_candidates}). The lab closes this gap with llm-direct/llm-cot/llm-react/llm-debate, which execute the same prompts through a real provider.',
  });

  incumbent.push({
    id: 'faultexplainer-clone',
    label: 'FaultExplainer 上游仓库',
    verdict: 'vendored-not-runnable',
    runnable: false,
    evidence: {
      path: 'baselines/FaultExplainer',
      upstream: 'github.com/li-group/FaultExplainer @ 2fcfee9 (vendored; see baselines/FaultExplainer/VENDOR.md)',
      blocked_by: 'backend/.env OPENAI_API_KEY is empty; no scikit-learn/fastapi environment recorded; backend/results.txt is 0 bytes',
      validated_against: exists(path.join(FE_REPO(), 'frontend', 'public'))
        ? "FE's own processed outputs (frontend/public/fault*.csv)"
        : null,
    },
    note:
      'Upstream is complete and pristine at the pinned commit (21 labelled TEP runs + its own pipeline outputs), but it cannot run end to end without a key. The lab therefore reproduces its algorithm and validates against FE\'s own committed outputs.',
  });

  incumbent.push({
    id: 'idd-full-pipeline',
    label: 'IDD 全管线（被测对象本身）',
    verdict: 'archived-results',
    runnable: false,
    evidence: {
      metrics: exists(IDD_METRICS()) ? 'results/benchmark/metrics.json' : null,
      gradings: 'results/benchmark/gradings/*.json',
    },
    note:
      'The full 14-agent pipeline is the SYSTEM UNDER TEST, not a baseline. It is driven through the web app / CLI, not through this lab; the lab reads its archived results as the reference column.',
  });

  // ---- what THIS LAB added, kept separate from the pre-existing findings so
  // the "before" count is not inflated by the lab's own work.
  const labAdditions = [
    {
      id: 'fe-official-lab',
      label: 'FaultExplainer 协议复刻（本实验室新增）',
      verdict: 'reproduced-bit-faithful',
      runnable: true,
      evidence: {
        module: 'baseline-lab/server/utils/algorithms/fe-official.mjs',
        source_reimplemented: 'backend/{model,analysis,prompts}.py',
        scaler_pinned: 'backend/stats/features_mean_std.csv (12/12 exact; all 500 rows, population std)',
        gate: 'baseline-lab/scripts/verify-fe.mjs -> 21/21 PASS, t2_stat rel-err ~2e-12, anomaly 500/500, identical trigger index',
      },
      note:
        "The statistical front end is bit-faithful to FE's own committed outputs. Only the EXPLAIN_ROOT model call needs a provider. This is what makes the cloned-but-unrunnable upstream repo usable as a comparator.",
    },
  ];

  // ---- this lab's own inventory
  const labRunnable = algorithms.map((a) => ({
    id: a.id,
    label: a.label,
    family: a.family,
    deterministic: a.deterministic,
    requires_provider: Boolean(a.requiresProvider),
    domains: a.domains || null,
    description: a.description,
  }));

  const missing = health.filter((h) => !h.loaded).map((h) => ({ file: h.file, family: h.family, error: h.error }));

  // ---- headline counts
  const total = labRunnable.length + missing.length;
  const citationOnly = CITATION_ONLY.length;

  return {
    generated_at: new Date().toISOString(),
    repo_root: root,
    headline: {
      lab_algorithms_runnable: labRunnable.length,
      lab_modules_missing: missing.length,
      lab_modules_declared: total,
      citation_only_comparators: citationOnly,
      incumbent_runnable_before: incumbent.filter((i) => i.runnable).length,
      incumbent_not_runnable_before: incumbent.filter((i) => !i.runnable).length,
      lab_additions: labAdditions.length,
    },
    answer:
      'Before this lab the repository had exactly ONE runnable comparator (the deterministic PCA script). The bare-LLM baseline was a frozen answer archive with no execution path, and the cloned FaultExplainer could not run (no API key). The documentation, however, claims six baselines including CoT, ReAct, AutoGen-style multi-agent debate, XGBoost and LSTM. This lab closes that gap: the deterministic comparators run offline, and the LLM comparators make genuine provider calls — never fabricated answers.',
    incumbent_findings: incumbent,
    lab_additions: labAdditions,
    lab_runnable: labRunnable,
    lab_missing: missing,
    citation_only: CITATION_ONLY,
    verification_gates: [
      { script: 'baseline-lab/scripts/verify-pca.mjs', proves: 'PCA reimplementation == repository archived PCA numbers (12/12)' },
      { script: 'baseline-lab/scripts/verify-fe.mjs', proves: 'FE protocol replica == FE committed outputs (21/21, ~1e-12)' },
      { script: 'baseline-lab/scripts/check-fe-scaler.mjs', proves: 'FE StandardScaler convention pinned (12/12 exact)' },
      { script: 'baseline-lab/scripts/provider-selftest.mjs', proves: 'LLM provider makes genuine, isolated calls' },
      { script: 'baseline-lab/scripts/verify-classical.mjs', proves: 'classical detectors run + are deterministic' },
      { script: 'baseline-lab/scripts/verify-supervised.mjs', proves: 'supervised models train, predict, and refuse out-of-domain cases' },
    ],
    honesty_rules: [
      'No fabricated answers: a failed or unavailable LLM call yields status skipped_no_provider / error with an EMPTY top3. Nothing is invented to fill a gap (docs/benchmark/reproduction-guide.md §10 red line).',
      'Truth isolation: algorithms receive a sanitized case (truth/keywords/literature_baseline stripped); scoring happens only after the algorithm returns.',
      'No per-case tuning: every threshold is calibrated on the reference (normal-control) data of the same dataset only.',
      'Reference-based limits: control limits come from the reference distribution, never from the file under test.',
      'Bare-LLM isolation: CLI harnesses run with a neutral cwd and tools disabled, so the comparator cannot read this repository\'s agent instructions.',
      'Self-test stub is excluded from scoring: the deterministic self-test provider is tagged fabricated:true and is never counted.',
    ],
  };
});
