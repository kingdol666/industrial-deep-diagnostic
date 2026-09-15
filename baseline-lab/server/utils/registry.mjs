// Algorithm registry — the single place that declares what the lab can run.
//
// Every entry is an EXECUTABLE module (meta + run(ctx)). Nothing is listed as a
// baseline unless it can actually be invoked; comparators that exist only as
// citations are recorded separately in `CITATION_ONLY`, so the audit view can
// show the difference between "reproduced and runnable here" and "quoted from a
// paper".
//
// Modules are loaded dynamically: a module that fails to import is reported as
// `status: 'load_error'` rather than taking the whole registry down. That keeps
// the audit honest — a missing implementation shows up as a gap, not a crash.

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { LAB_ROOT } from './paths.mjs';

// Resolve the algorithm directory from LAB_ROOT (which is derived once in
// paths.mjs and is correct under both plain Node and Nitro's bundler) rather
// than recomputing it from this module's own import.meta.url — the latter is a
// build-output path inside Nitro and silently pointed at a non-existent dir.
const ALGO_DIR = path.join(LAB_ROOT, 'server', 'utils', 'algorithms');

/** Declared algorithm modules, in presentation order. */
export const MANIFEST = [
  // --- classical statistical process monitoring (deterministic, offline) ---
  { file: 'pca.mjs', family: 'classical' },
  { file: 'kpca.mjs', family: 'classical' },
  { file: 'ica.mjs', family: 'classical' },
  { file: 'spc.mjs', family: 'classical' },
  { file: 'knn.mjs', family: 'classical' },
  { file: 'iforest.mjs', family: 'classical' },
  // --- supervised / deep (deterministic, trained on labelled TEP) ---
  { file: 'xgb.mjs', family: 'supervised' },
  { file: 'rf.mjs', family: 'supervised' },
  { file: 'mlp.mjs', family: 'supervised' },
  { file: 'ae.mjs', family: 'supervised' },
  // --- LLM comparators (genuine calls; never fabricated) ---
  { file: 'llm-direct.mjs', family: 'llm' },
  { file: 'llm-cot.mjs', family: 'llm' },
  { file: 'llm-react.mjs', family: 'llm' },
  { file: 'llm-debate.mjs', family: 'llm' },
  // --- published-protocol replica ---
  { file: 'fe-official.mjs', family: 'official' },
];

const modules = new Map();
const loadErrors = new Map();

for (const entry of MANIFEST) {
  const abs = path.join(ALGO_DIR, entry.file);
  if (!fs.existsSync(abs)) {
    loadErrors.set(entry.file, 'module file missing');
    continue;
  }
  try {
    // Absolute file URL + @vite-ignore: works identically under plain Node (the
    // CLI scripts) and under Nitro's bundler (the web app), and keeps a module
    // that fails to load isolated to its own manifest entry.
    const mod = await import(/* @vite-ignore */ pathToFileURL(abs).href);
    if (!mod.meta || typeof mod.run !== 'function') {
      loadErrors.set(entry.file, 'module does not export { meta, run }');
      continue;
    }
    modules.set(mod.meta.id, { ...mod, _file: entry.file });
  } catch (err) {
    loadErrors.set(entry.file, String(err && err.message ? err.message : err));
  }
}

export const REGISTRY = modules;

export function listAlgorithms() {
  return [...modules.values()].map((m) => ({ ...m.meta }));
}

export function getAlgorithm(id) {
  const m = modules.get(id);
  if (!m) {
    const known = loadErrors.size ? ` (unavailable modules: ${[...loadErrors.keys()].join(', ')})` : '';
    throw new Error(`unknown or unavailable algorithm: ${id}${known}`);
  }
  return m;
}

/** Honest coverage report used by the audit view. */
export function moduleHealth() {
  return MANIFEST.map((e) => {
    const mod = [...modules.values()].find((m) => m._file === e.file);
    return {
      file: e.file,
      family: e.family,
      id: mod?.meta?.id || null,
      label: mod?.meta?.label || null,
      loaded: Boolean(mod),
      error: loadErrors.get(e.file) || null,
    };
  });
}

export const FAMILY_LABELS = {
  classical: '经典统计过程监测',
  supervised: '监督学习分类器',
  llm: 'LLM 诊断算法',
  official: '对标论文官方协议复刻',
  reference: '本仓库全管线（参照）',
};

/**
 * Comparators the repository's documentation claims but which have NO runnable
 * implementation anywhere (neither here nor upstream). Recorded so the audit
 * states coverage honestly instead of silently omitting them. Each entry names
 * what would be needed to close the gap.
 */
export const CITATION_ONLY = [
  {
    id: 'faultexplainer-python',
    label: 'FaultExplainer 官方 Python 管线（原样端到端运行）',
    claimed_in: 'docs/benchmark/design.md §4.2 (B14); docs/publication-strategy-report.md §5.2',
    status: 'vendored-not-runnable',
    reason:
      'baselines/FaultExplainer 已按 commit 2fcfee9 完整入库（vendored，见该目录 VENDOR.md），但原样运行需要 OPENAI_API_KEY（backend/.env 为空）与 scikit-learn/fastapi 运行环境；上游亦无端到端执行记录（backend/results.txt 为 0 字节）。',
    upstream: 'baselines/FaultExplainer (vendored @ 2fcfee9) + OPENAI_API_KEY',
    mitigated_by:
      'fe-official —— 已按 model.py/analysis.py/prompts.py 逐式复刻，并与 FE 自带产物逐行核对（21/21 通过，误差 ~1e-12）',
  },
  {
    id: 'gong-multiagent',
    label: 'Gong et al. 多代理 LLM 传感器失效推理 (JII 2026)',
    claimed_in: 'docs/publication-strategy-report.md §5.1 (B2), §5.2',
    status: 'no-code-released',
    reason:
      'FailureSensorIQ 为 MCQA 问答集，其代理编排代码未开源；论文数字（Llama3.1-8B 36.5%→54.6%）属跨任务引用值，与真实时序 RCA 不同口径。',
    upstream: 'FailureSensorIQ (HF) + 未开源的代理编排',
    mitigated_by: 'llm-debate —— 自实现的多代理辩论同构基线（3 专家 + 主席裁决）',
  },
  {
    id: 'autogen-multiagent',
    label: 'AutoGen / CrewAI 通用多代理讨论框架',
    claimed_in: 'docs/publication-strategy-report.md §5.2',
    status: 'framework-not-in-repo',
    reason: '通用编排框架未在本仓库安装，也无工业诊断场景适配实现。',
    upstream: 'autogen / crewai 运行时',
    mitigated_by: 'llm-debate —— 无框架依赖的同构多代理辩论实现',
  },
  {
    id: 'xgboost-lstm-published',
    label: '文献 XGBoost / LSTM / BeatGAN 数字 (B7/B8)',
    claimed_in: 'docs/benchmark/design.md §4.2; docs/publication-strategy-report.md §5.2',
    status: 'citation-only',
    reason:
      'Pozdnyakov et al. 的 MLP/GRU/TCN（0.8873/0.9067/0.8985）与 Hartung et al. 的 BeatGAN/TCN-S2S-AE（F1 0.9699/0.9632）为逐样本检测任务，与本基准的根因任务口径不同，仅作量级参照。',
    upstream: '论文表格（引用值，非本仓库复现）',
    mitigated_by: 'xgb / rf / mlp / ae —— 同族模型在本基准上的实测复现',
  },
  {
    id: 'idd-full-pipeline',
    label: 'IDD 全管线（被测对象本身）',
    claimed_in: 'results/benchmark/metrics.json',
    status: 'archived-results',
    reason:
      '全管线结果由 14-agent 编排产生，不在本实验室内执行；实验室读取其归档结果作为参照列，不重跑。',
    upstream: 'results/benchmark/{metrics.json,gradings/*}',
    mitigated_by: '读取归档（reference 列）',
  },
];
