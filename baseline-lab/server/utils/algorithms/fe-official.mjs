// fe-official — FaultExplainer official protocol, reproduced from source.
//
// Source of truth: the cloned repository baselines/FaultExplainer (li-group,
// commit 2fcfee9). This module reimplements its algorithm step for step in pure
// JS so the protocol is runnable here without scikit-learn, FastAPI or an
// OpenAI key:
//
//   backend/model.py
//     scaler      : sklearn StandardScaler fitted on fault0.csv (ALL 500 rows,
//                   population variance ddof=0)  <- pinned against FE's own
//                   backend/stats/features_mean_std.csv (scripts/check-fe-scaler.mjs, 12/12 exact)
//     pca         : PCA(n_components=0.9) on the standardized training data;
//                   explained_variance_ = singular_values^2 / (n-1); keep the
//                   smallest k with cumulative ratio >= 0.9
//     t2_stat     : z P diag(1/lamda) P^T z^T
//     t2_threshold: [a(n-1)(n+1) / (n(n-a))] * F.ppf(1-alpha, a, n-a), alpha=0.01
//     t2_contrib  : c_j = sum_k (t_k/lamda_k) P[j,k] z[j], clipped at 0
//   backend/analysis.py
//     trigger     : first run of `fault_trigger_consecutive_step` consecutive
//                   anomalous samples (config.json)
//     features    : top-6 by t2_contrib at the trigger index
//     changes     : recent-window mean (20) vs stored normal mean, as % change
//   backend/prompts.py
//     EXPLAIN_ROOT: the 15-cause TEP prompt, reproduced verbatim below
//
// FIDELITY EVIDENCE: scripts/verify-fe.mjs compares this replica's per-row
// t2_stat, anomaly flag and per-feature contributions against FE's own
// committed outputs (baselines/FaultExplainer/frontend/public/fault*.csv).
//
// The model call itself is a GENUINE call through the shared provider layer.

import fs from 'node:fs';
import path from 'node:path';
import { repoPath, exists } from '../paths.mjs';
import { readCsv, TEP_TAG_ORDER, loadCaseMatrix } from '../dataset.mjs';
import { jacobiEigen, fPpf, mean } from '../linalg.mjs';
import { llmContext, notRun, callJson, normalizeAnswer } from './_llm-shared.mjs';

export const meta = {
  id: 'fe-official',
  label: 'FaultExplainer 官方协议复刻 (PCA0.9+T²F分布+EXPLAIN_ROOT)',
  short: 'FE-official',
  family: 'official',
  kind: 'llm',
  deterministic: false, // the STATISTICAL front-end is deterministic; the LLM call is not
  statistical_frontend_deterministic: true,
  requiresProvider: true,
  needsReference: false,
  domains: ['tep'],
  description:
    "FaultExplainer's published pipeline reproduced from its source: StandardScaler on fault0.csv, PCA(n_components=0.9), T² with an F-distribution control limit (alpha=0.01), consecutive-anomaly trigger, top-6 T²-contribution features, then FE's EXPLAIN_ROOT prompt with the 15 documented TEP causes.",
  provenance: {
    basis: ['khan2024faultexplainer'],
    repo: 'github.com/li-group/FaultExplainer @ 2fcfee9 (cloned at baselines/FaultExplainer)',
    note: 'Pure-JS reimplementation of backend/{model,analysis,prompts}.py; validated against FE\'s own committed outputs.',
  },
};

export const FE_CONFIG = {
  model: 'gpt-4o',
  fault_trigger_consecutive_step: 6, // config.json
  topkfeatures: 6,
  alpha: 0.01,
  variance_ratio: 0.9,
  recent_window: 20,
};

/** FE's EXPLAIN_ROOT prompt, reproduced verbatim from backend/prompts.py. */
export const EXPLAIN_ROOT = `
You have been provided with the descriptions of the Tennessee Eastman process (TEP). 
A fault has just occurred, and you are tasked with diagnosing its root cause.

You will be given:
A fault has just occurred in the TEP. You will be given the top six contributing features to the fault. 
For each of these six features, you will be provided with their values when the fault occurred
and their mean values during normal operation.

**Instructions**:
1. **Analyze Feature Changes**:
   - Compare the mean and standard deviation of each feature during the fault to the values under normal operation.
   - Identify significant deviations and hypothesize what these changes indicate about the system's behavior.

2. **Select Root Causes and Explain Fault Propagation**:
   - From the list of 16 predefined root causes (provided below), identify the three most likely causes of the fault.
   - Use your reasoning based on the provided process description, your understanding of the TEP dynamics, and the observed feature changes.
   - For each root cause, explain how it could lead to the observed changes in the six features.
- Note that some of the features are measured variables that cannot be changed directly. Some of the
        features are manipulated that are actively changed by the control algorithm. The control algorithm will
        changed the manipulated variables such that the measured variables are close to the normal operating condition.
   - Describe the sequence of events in the process that connect the root cause to the feature deviations.
   - Note that there is only one fault in the system, you should find the root cause that can explain all the feature deviations.
   - The most likely fault would be the one that can explain the most number of feature deviations.
   - In your explanation, make sure to explain how the root cause propagates through the system to cause the observed feature deviations.
   - If you cannot find a way to connect a root cause to the observed feature deviations, also mention that you cannot explain the deviation with that root cause.
   - In your explaination, explain whether each of the top 6 features can be explained by this particular root cause or not.
   - Give the total number out of the six that can be explained.
   -Have you explanation in a coherent paragraph instead of using bullet points.

3. **Ensure Deterministic Responses**:
   - Provide consistent and deterministic explanations for your choices every time you are run.
   - Base your reasoning strictly on the provided feature data and process knowledge.

**Available Root Causes**:
1. IDV(1) A/C Feed Ratio, B Composition Constant (Stream 4) & Step
2. IDV(2) B Composition, A/C Ratio Constant (Stream 4) & Step
3. IDV(3) D Feed Temperature (Stream 2) & Step
4. IDV(4) Reactor Cooling Water Inlet Temperature & Step
5. IDV(5) Condenser Cooling Water Inlet Temperature & Step
6. IDV(6) A Feed Loss (Stream 1) & Step
7. IDV(7) C Header Pressure Loss - Reduced Availability (Stream 4) & Step
8. IDV(8) A, B, C Feed Composition (Stream 4) & Random Variation
9. IDV(9) D Feed Temperature (Stream 2) & Random Variation
10. IDV(10) C Feed Temperature (Stream 4) & Random Variation
11. IDV(11) Reactor Cooling Water Inlet Temperature & Random Variation
12. IDV(12) Condenser Cooling Water Inlet Temperature & Random Variation
13. IDV(13) Reaction Kinetics & Slow Drift
14. IDV(14) Reactor Cooling Water Valve & Sticking
15. IDV(15) Condenser Cooling Water Valve & Sticking
`;

// ------------------------------------------------- statistical front end

let cachedModel = null;

/**
 * Fit FE's scaler + PCA on FE's own normal run (fault0.csv), in FE's column
 * order (which is identical to XMEAS_1..41,XMV_1..11, verified by
 * scripts/check-fe-scaler.mjs).
 */
export function fitFeModel({ trainingFile = null } = {}) {
  if (cachedModel && !trainingFile) return cachedModel;
  const file = trainingFile || repoPath('baselines', 'FaultExplainer', 'backend', 'data', 'fault0.csv');
  if (!exists(file)) throw new Error(`FE training file missing: ${file}`);

  const { header, rows } = readCsv(file);
  const keep = TEP_TAG_ORDER.map((t) => header.indexOf(t));
  const missing = TEP_TAG_ORDER.filter((t, i) => keep[i] < 0);
  if (missing.length) throw new Error(`FE training file missing TEP tags: ${missing.join(', ')}`);

  const X = rows.map((r) => keep.map((j) => Number(r[j])));
  const n = X.length;
  const m = X[0].length;

  // ---- StandardScaler: mean + population std over ALL rows (ddof=0)
  const mu = new Array(m).fill(0);
  const sd = new Array(m).fill(0);
  for (const r of X) for (let j = 0; j < m; j++) mu[j] += r[j] / n;
  for (const r of X) for (let j = 0; j < m; j++) sd[j] += (r[j] - mu[j]) ** 2 / n;
  for (let j = 0; j < m; j++) sd[j] = Math.sqrt(sd[j]) || 1;

  const Z = X.map((r) => r.map((v, j) => (v - mu[j]) / sd[j]));

  // ---- PCA(n_components=0.9): covariance with ddof=1 == explained_variance_
  const C = Array.from({ length: m }, () => new Float64Array(m));
  for (const r of Z) {
    for (let a = 0; a < m; a++) for (let b = a; b < m; b++) C[a][b] += (r[a] * r[b]) / (n - 1);
  }
  for (let a = 0; a < m; a++) for (let b = 0; b < a; b++) C[a][b] = C[b][a];

  const { values, vectors } = jacobiEigen(C);
  const total = Array.from(values).reduce((s, v) => s + Math.max(v, 0), 0) || 1;
  let cum = 0, a = 0;
  for (let k = 0; k < values.length; k++) {
    cum += Math.max(values[k], 0) / total;
    a++;
    if (cum >= FE_CONFIG.variance_ratio) break;
  }

  const P = [];
  const lamda = [];
  for (let k = 0; k < a; k++) {
    P.push(Array.from({ length: m }, (_, i) => vectors[i][k]));
    lamda.push(Math.max(values[k], 1e-300));
  }

  // ---- T² threshold: [a(n-1)(n+1)/(n(n-a))] * F.ppf(1-alpha, a, n-a)
  const scaling = (a * (n - 1) * (n + 1)) / (n * (n - a));
  const t2Threshold = scaling * fPpf(1 - FE_CONFIG.alpha, a, n - a);

  const model = { mu, sd, P, lamda, a, m, n, t2Threshold, scaling, trainingFile: file, colNames: TEP_TAG_ORDER.slice() };
  if (!trainingFile) cachedModel = model;
  return model;
}

/** FE per-row statistics: t2_stat, anomaly flag, per-feature contributions. */
export function feStatistics(X, model) {
  const { mu, sd, P, lamda, m, t2Threshold } = model;
  const out = [];
  for (const r of X) {
    const z = new Array(m);
    for (let j = 0; j < m; j++) z[j] = (r[j] - mu[j]) / sd[j];

    const t = new Array(P.length);
    for (let k = 0; k < P.length; k++) {
      let s = 0;
      const Pk = P[k];
      for (let j = 0; j < m; j++) s += Pk[j] * z[j];
      t[k] = s;
    }
    let t2 = 0;
    for (let k = 0; k < t.length; k++) t2 += (t[k] * t[k]) / lamda[k];

    const contrib = new Array(m).fill(0);
    for (let j = 0; j < m; j++) {
      // FE clips EACH component's term at zero BEFORE summing (np.maximum(c_ji, 0)
      // is applied inside calculate_c, then .sum() over components). Clipping the
      // total instead changes the numbers materially, so the order matters.
      let c = 0;
      for (let k = 0; k < P.length; k++) {
        const term = (t[k] / lamda[k]) * P[k][j] * z[j];
        c += term > 0 ? term : 0;
      }
      contrib[j] = c;
    }
    out.push({ t2, anomaly: t2 > t2Threshold, contrib, z });
  }
  return out;
}

/** First index ending a run of `k` consecutive anomalies (FE's trigger). */
export function findTrigger(stats, k = FE_CONFIG.fault_trigger_consecutive_step) {
  let run = 0;
  for (let i = 0; i < stats.length; i++) {
    if (stats[i].anomaly) {
      run++;
      if (run >= k) return i;
    } else run = 0;
  }
  return null;
}

/** Align a benchmark case matrix to FE's column order. */
export function alignCaseToFe(matrix) {
  const idx = TEP_TAG_ORDER.map((tag) => {
    const canon = TEP_TAG_TO_CANON_LOCAL(tag);
    return matrix.colNames.indexOf(canon);
  });
  if (idx.some((i) => i < 0)) return null;
  return matrix.X.map((r) => idx.map((j) => r[j]));
}

function TEP_TAG_TO_CANON_LOCAL(tag) {
  const i = TEP_TAG_ORDER.indexOf(tag);
  return i < 41 ? `XMEAS_${i + 1}` : `XMV_${i - 40}`;
}

/** Build FE's diagnosis prompt from the top-6 contributing features. */
export function buildFePrompt(model, stats, triggerIdx, featureTable) {
  const lines = [];
  lines.push('You will be given the top six contributing features to the fault.');
  lines.push('');
  lines.push('Top 6 contributing features (by T² contribution at the trigger sample):');
  for (const f of featureTable) {
    lines.push(
      `- ${f.feature}: fault-occurrence value = ${f.fault_value}, mean during the recent ${FE_CONFIG.recent_window}-sample window = ${f.recent_mean}, ` +
        `normal-operating mean = ${f.normal_mean}, percentage change = ${f.pct_change}%`,
    );
  }
  lines.push('');
  lines.push(`Trigger sample index: ${triggerIdx} (1-based row ${triggerIdx + 1}).`);
  lines.push(`T² statistic at trigger: ${stats[triggerIdx].t2.toFixed(4)} (control limit ${model.t2Threshold.toFixed(4)}).`);
  lines.push('');
  lines.push('Output STRICT JSON only: {"top3": ["<root cause id/name>", ...], "reasoning": "<your coherent paragraph>"}');
  return `${EXPLAIN_ROOT}\n${lines.join('\n')}\n`;
}

// ---------------------------------------------------------------- algorithm

export async function run(ctx, { config = {} } = {}) {
  const t0 = Date.now();
  const { caseDef, matrix } = ctx;

  if (caseDef.dataset !== 'tep') {
    return {
      status: 'not_applicable',
      top3: [],
      verdict: null,
      reasoning:
        "FaultExplainer's official protocol is defined for the Tennessee Eastman process (TEP) only; its training scaler, PCA basis and EXPLAIN_ROOT cause list are TEP-specific, so it is not applied to this domain.",
      invocations: [],
      runtime_ms: Date.now() - t0,
    };
  }

  const model = fitFeModel();
  const aligned = alignCaseToFe(matrix);
  if (!aligned) {
    return {
      status: 'error',
      top3: [],
      verdict: null,
      reasoning: 'Could not align the case matrix to the 52 TEP variables required by the FE protocol.',
      invocations: [],
      runtime_ms: Date.now() - t0,
    };
  }

  const stats = feStatistics(aligned, model);
  const k = config.feConsecutive || FE_CONFIG.fault_trigger_consecutive_step;
  const triggerIdx = findTrigger(stats, k);
  const anomalyCount = stats.filter((s) => s.anomaly).length;

  const frontEnd = {
    training_file: model.trainingFile.replace(/\\/g, '/'),
    scaler_rows: model.n,
    components_retained: model.a,
    t2_threshold: Number(model.t2Threshold.toFixed(6)),
    scaling_factor: Number(model.scaling.toFixed(6)),
    trigger_consecutive_step: k,
    trigger_index: triggerIdx,
    anomaly_rows: anomalyCount,
    detection_rate: Number((anomalyCount / stats.length).toFixed(4)),
    noise: 'statistical front end is deterministic; only the LLM explanation is stochastic',
  };

  // Control case: FE's protocol is a detector too — with no trigger it reports normal.
  if (triggerIdx === null) {
    return {
      status: 'executed',
      top3: [],
      verdict: 'normal',
      reasoning: `The FE statistical front end produced no run of ${k} consecutive T² violations (${anomalyCount}/${stats.length} anomalous rows, limit ${model.t2Threshold.toFixed(2)}), so the protocol does not trigger a diagnosis and reports no root cause.`,
      fe_frontend: frontEnd,
      invocations: [],
      runtime_ms: Date.now() - t0,
    };
  }

  // ---- top-6 features by T² contribution at the trigger index
  const row = stats[triggerIdx];
  const ranked = model.colNames
    .map((feature, j) => ({ feature, contribution: row.contrib[j] }))
    .sort((a, b) => b.contribution - a.contribution);
  const topK = ranked.slice(0, FE_CONFIG.topkfeatures);

  const start = Math.max(triggerIdx - FE_CONFIG.recent_window + 1, 0);
  const featureTable = topK.map(({ feature, contribution }) => {
    const j = model.colNames.indexOf(feature);
    const recent = aligned.slice(start, triggerIdx + 1).map((r) => r[j]);
    const recentMean = mean(recent);
    const normalMean = model.mu[j];
    return {
      feature,
      t2_contribution: Number(contribution.toFixed(6)),
      fault_value: Number(aligned[triggerIdx][j].toFixed(6)),
      recent_mean: Number(recentMean.toFixed(6)),
      normal_mean: Number(Number(normalMean).toFixed(6)),
      pct_change: Number((((recentMean - normalMean) / normalMean) * 100).toFixed(2)),
    };
  });

  const prompt = buildFePrompt(model, stats, triggerIdx, featureTable);
  const { provider, providerError } = llmContext(config);
  if (providerError) {
    return { ...notRun('error', { error: providerError }), fe_frontend: frontEnd, feature_table: featureTable, runtime_ms: Date.now() - t0 };
  }
  if (!provider) {
    return { ...notRun('skipped_no_provider'), fe_frontend: frontEnd, feature_table: featureTable, runtime_ms: Date.now() - t0 };
  }

  const { ok, answer, invocation } = await callJson(provider, prompt, {
    timeoutMs: config.llmTimeoutMs || 300000,
    caseId: caseDef.case_id,
    algoId: meta.id,
    tag: 'fe_official',
  });

  if (!ok || !answer) {
    return {
      status: 'error',
      top3: [],
      verdict: null,
      reasoning: `The FE-protocol model call produced no parseable strict-JSON answer (${invocation.error || 'unparseable reply'}). No answer is reported.`,
      fe_frontend: frontEnd,
      feature_table: featureTable,
      invocations: [invocation],
      runtime_ms: Date.now() - t0,
    };
  }

  const norm = normalizeAnswer(answer, { caseDef });
  return {
    status: 'executed',
    ...norm,
    top3_source: 'EXPLAIN_ROOT (official FE prompt, reproduced verbatim)',
    fe_frontend: frontEnd,
    feature_table: featureTable,
    invocations: [invocation],
    runtime_ms: Date.now() - t0,
  };
}
