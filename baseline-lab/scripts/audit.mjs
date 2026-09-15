#!/usr/bin/env node
// audit.mjs — print the reproduction audit as text.
//
//     node scripts/audit.mjs
//
// Same data the Audit page renders, so the finding is available in CI/logs and
// not only in a browser.

import fs from 'node:fs';
import path from 'node:path';
import { moduleHealth, listAlgorithms, CITATION_ONLY } from '../server/utils/registry.mjs';
import {
  repoRoot, FE_REPO, PCA_BASELINE, IDD_METRICS, ARCHIVED_ANSWERS, ARCHIVED_PROMPTS,
  IDD_BASELINES, exists, readJson, feProvenance,
} from '../server/utils/paths.mjs';
import { detectProviders, resolveProvider } from '../server/utils/llm/provider.mjs';

const B = (s) => `\x1b[1m${s}\x1b[0m`;
const OK = (s) => `\x1b[32m${s}\x1b[0m`;
const WARN = (s) => `\x1b[33m${s}\x1b[0m`;
const BAD = (s) => `\x1b[31m${s}\x1b[0m`;
const DIM = (s) => `\x1b[2m${s}\x1b[0m`;

const root = repoRoot();
const health = moduleHealth();
const algos = listAlgorithms();
const missing = health.filter((h) => !h.loaded);

function head(title) {
  console.log(`\n${B(title)}`);
  console.log('─'.repeat(Math.max(60, title.length)));
}

console.log(B('\nIDD Baseline Lab — 复现审计 / Reproduction audit'));
console.log(DIM(`repo root: ${root}`));
console.log(DIM(`generated: ${new Date().toISOString()}`));

// ---------------------------------------------------------------- incumbent
head('一、审计前仓库状态（对照算法的真实可运行程度）');

const fe = feProvenance();

const pcaOk = exists(PCA_BASELINE());
let pcaScenarios = 0;
try { pcaScenarios = Object.keys(readJson(PCA_BASELINE()).scenarios || {}).length; } catch { /* ignore */ }

const answers = exists(ARCHIVED_ANSWERS()) ? fs.readdirSync(ARCHIVED_ANSWERS()).filter((f) => f.endsWith('.json')).length : 0;
const prompts = exists(ARCHIVED_PROMPTS()) ? fs.readdirSync(ARCHIVED_PROMPTS()).filter((f) => f.endsWith('.txt')).length : 0;
const feEnv = exists(path.join(FE_REPO(), 'backend', '.env'))
  ? fs.readFileSync(path.join(FE_REPO(), 'backend', '.env'), 'utf8')
  : '';
const feKeyEmpty = /OPENAI_API_KEY\s*=\s*['"]?['"]?\s*$/m.test(feEnv) || !/OPENAI_API_KEY\s*=\s*\S/.test(feEnv);
const feResultsSize = exists(path.join(FE_REPO(), 'backend', 'results.txt'))
  ? fs.statSync(path.join(FE_REPO(), 'backend', 'results.txt')).size
  : null;

const rows1 = [
  ['经典 PCA 基线', pcaOk ? OK('可运行') : BAD('缺失'),
    `scripts/benchmark/baseline_pca.mjs -> ${pcaScenarios} 场景 (results/benchmark/baseline_pca_rca.json)`],
  ['裸 LLM 基线', WARN('仅有归档·不可执行'),
    `${prompts} 提示词 + ${answers} 份真实回答归档；baseline_llm.mjs 只打印人工执行契约`],
  ['FaultExplainer 上游', WARN('已入库·不可运行'),
    `commit ${(fe.commit || '?').slice(0, 12)} (${fe.source || 'unknown'}); OPENAI_API_KEY ${feKeyEmpty ? BAD('为空') : OK('已配置')}; backend/results.txt ${feResultsSize ?? '?'} 字节`],
  ['IDD 全管线', DIM('读取归档'),
    IDD_METRICS() ? 'results/benchmark/metrics.json（被测对象，不在本实验室执行）' : '缺失'],
];
for (const [name, verdict, detail] of rows1) {
  console.log(`  ${name.padEnd(22)} ${verdict.padEnd(30)} ${DIM(detail)}`);
}

// ---------------------------------------------------------------- lab
head('二、本实验室已实现的对照算法');
const byFamily = {};
for (const a of algos) (byFamily[a.family] = byFamily[a.family] || []).push(a);
for (const [fam, items] of Object.entries(byFamily)) {
  console.log(`  ${B(fam)} (${items.length})`);
  for (const a of items) {
    const tag = a.requiresProvider ? WARN('needs-LLM') : OK('offline  ');
    console.log(`    ${a.id.padEnd(18)} ${tag} ${a.deterministic ? 'deterministic' : 'stochastic   '}  ${DIM(a.label)}`);
  }
}
console.log(`\n  合计 ${OK(String(algos.length))} 个可运行算法；缺失模块 ${missing.length ? BAD(String(missing.length)) : OK('0')}`);
for (const m of missing) console.log(`    ${BAD('missing')} ${m.file} — ${m.error}`);

// ---------------------------------------------------------------- citations
head('三、文档声称但无法复现的对照（诚实缺口）');
for (const c of CITATION_ONLY) {
  console.log(`  ${WARN(c.status.padEnd(22))} ${c.label}`);
  console.log(`    ${DIM('claimed in:')} ${c.claimed_in}`);
  console.log(`    ${DIM('requires  :')} ${c.upstream}`);
  console.log(`    ${DIM('mitigated :')} ${c.mitigated_by}`);
}

// ---------------------------------------------------------------- provider
head('四、LLM provider');
const providers = detectProviders({});
let resolved = null;
let rErr = null;
try { resolved = resolveProvider({}); } catch (e) { rErr = e.message; }
for (const p of providers) {
  console.log(`  ${p.available ? OK('[x]') : DIM('[ ]')} ${p.id.padEnd(22)} ${DIM(p.detail.slice(0, 72))}`);
}
console.log(`\n  resolved: ${resolved ? OK(resolved.id) : BAD('none — LLM comparators will report skipped_no_provider')}`);
if (rErr) console.log(`  ${BAD('resolve error:')} ${rErr}`);

let archivedModel = null;
try { archivedModel = readJson(IDD_BASELINES()).model || null; } catch { /* ignore */ }
if (archivedModel && resolved) {
  const arch = archivedModel.toLowerCase();
  const lab = String(resolved.model || resolved.id).toLowerCase();
  const same = ['glm', 'zhipu', 'chatglm'].some((t) => arch.includes(t) && lab.includes(t));
  console.log(`\n  归档基线模型 : ${archivedModel}`);
  console.log(`  本次调用模型 : ${resolved.model || resolved.id}`);
  console.log(
    same
      ? `  ${OK('可比：同一模型族')}`
      : `  ${BAD('⚠ 模型混淆：二者不可直比')} — 本次 LLM 数字是新模型上的独立实验，不是对归档基线的复现。`,
  );
}

// ---------------------------------------------------------------- gates
head('五、复现验证门禁（可自行重跑）');
const gates = [
  ['scripts/verify-pca.mjs', 'PCA 复现 == 仓库归档 PCA 数字 (12/12)'],
  ['scripts/check-fe-scaler.mjs', 'FE StandardScaler 约定已钉死 (12/12 exact)'],
  ['scripts/verify-fe.mjs', 'FE 协议复刻 == FE 自带产物 (21/21, ~1e-12)'],
  ['scripts/verify-classical.mjs', '经典检测器可运行且确定性 (60/60)'],
  ['scripts/verify-supervised.mjs', '监督模型可训练/预测/拒绝跨域 (620/620)'],
  ['scripts/provider-selftest.mjs --live', 'provider 真实且隔离调用'],
];
for (const [s, proves] of gates) console.log(`  ${s.padEnd(38)} ${DIM(proves)}`);
console.log(`\n  一键： ${B('npm run verify')}`);

console.log(`\n${DIM('UI: npm run dev  ->  http://localhost:5190')}\n`);
