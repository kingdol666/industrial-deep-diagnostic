// llm.mjs — the same-model bare-LLM single-call arm (paper §8.4 arm iii) and the
// FE-prompt LLM execution (arm ii, second half).
//
// Two execution modes:
//   live     — when BASELINE_LLM_BASE_URL (+ BASELINE_LLM_API_KEY, BASELINE_LLM_MODEL)
//              is configured: one OpenAI-compatible /chat/completions call per
//              scenario/regime. Host validation BEFORE any request: http/https only;
//              localhost, loopback, private and reserved addresses are refused.
//   recorded — otherwise: replay the archived raw replies of the same-GLM deployment
//              (ZCode CLI harness, Sept 2026 snapshot) from
//              results/benchmark/baseline_fe_answers/<case>.<regime>.json.
//              Recorded mode is explicitly labeled in every response.
import fs from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import { REPO } from './repo.mjs';

const ANSWERS = path.join(REPO, 'results', 'benchmark', 'baseline_fe_answers');
const FE_PROMPTS = path.join(REPO, 'results', 'benchmark', 'fe_official_prompts');
const RECORDED_NOTE = 'archived raw replies of the same-GLM deployment as the IDD pipeline (ZCode CLI harness, Sept 2026 snapshot)';

// ---------- SSRF guard: validate the host BEFORE any request ----------
const BLOCKED_HOSTNAMES = new Set(['localhost', 'ip6-localhost', 'ip6-loopback']);

function isPrivateV4(ip) {
  const o = ip.split('.').map(Number);
  if (o.length !== 4 || o.some((x) => Number.isNaN(x))) return true;
  if (o[0] === 127 || o[0] === 10 || o[0] === 0) return true;              // loopback, private, this-network
  if (o[0] === 169 && o[1] === 254) return true;                          // link-local
  if (o[0] === 172 && o[1] >= 16 && o[1] <= 31) return true;              // private
  if (o[0] === 192 && o[1] === 168) return true;                          // private
  if (o[0] === 100 && o[1] >= 64 && o[1] <= 127) return true;             // CGNAT
  if (o[0] === 198 && (o[1] === 18 || o[1] === 19)) return true;          // benchmarking
  if (o[0] >= 224) return true;                                           // multicast + reserved
  return false;
}
function isBlockedIp(ip) {
  if (net.isIPv4(ip)) return isPrivateV4(ip);
  const v6 = ip.toLowerCase();
  if (v6 === '::1' || v6 === '::' || v6 === '::ffff:127.0.0.1') return true;   // loopback / unspecified
  if (v6.startsWith('fe80') || v6.startsWith('fc') || v6.startsWith('fd')) return true; // link-local / ULA
  if (v6.startsWith('ff')) return true;                                        // multicast
  return false;
}
export function validateEndpointBaseUrl(rawUrl) {
  let u;
  try { u = new URL(rawUrl); } catch { throw new Error(`BASELINE_LLM_BASE_URL is not a valid URL`); }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') throw new Error('BASELINE_LLM_BASE_URL must be http/https');
  const host = u.hostname.toLowerCase().replace(/\.$/, '');
  if (BLOCKED_HOSTNAMES.has(host) || host.endsWith('.localhost') || host.endsWith('.local') || host.endsWith('.internal')) {
    throw new Error(`refused LLM endpoint host: ${host}`);
  }
  const targets = net.isIP(host) ? [host] : [];
  if (net.isIP(host) && isBlockedIp(host)) throw new Error(`refused LLM endpoint address: ${host}`);
  if (!targets.length && (host === '0.0.0.0' || host === '[::]')) throw new Error('refused unspecified LLM endpoint host');
  return { url: u, host, resolved: targets };
}

// ---------- prompts ----------
export function buildBlindPrompt(brief, regime, causeTable) {
  const isTep = brief.dataset === 'tep';
  const cols = brief.evidence.anomaly_columns
    .map((c) => `${c.col} max|z|=${c.max_abs_z} (${(c.pct_z3 * 100).toFixed(1)}% beyond 3σ)`)
    .join('; ');
  const pairs = brief.evidence.top_correlation_pairs.join('; ');
  const lines = [];
  if (isTep) {
    lines.push('You are an industrial process monitoring engineer. The Tennessee Eastman Process (TEP) shows an abnormal episode. Your task: identify the root cause.');
    lines.push('');
    lines.push('Dataset: Tennessee Eastman Process simulation. Columns: XMEAS_1..41 process measurements, XMV_1..11 manipulator variables (Downs-Vogel standard mapping). Sampling: 3 minutes. Fault onset: sample 161 of 960.');
  } else {
    lines.push('You are an industrial process monitoring engineer. A process shows the following recorded episode. Your task: assess whether a fault is present and, if so, identify the most likely root cause.');
    lines.push('');
    lines.push(`Dataset: ${brief.case_id} (${brief.dataset}). Rows: ${brief.rows}. Sampling as described below.`);
  }
  lines.push('Blind statistical monitoring results (computed from the data):');
  lines.push(`- Per-column max |z|-score (top columns): ${cols}`);
  lines.push(`- Strongest cross-domain correlations: ${pairs}`);
  lines.push('');
  lines.push(`Process description: ${brief.process_description}`);
  lines.push('');
  if (regime === 'with_candidates') {
    lines.push('Documented root-cause list for the TEP (choose from these):');
    for (const [id, desc] of Object.entries(causeTable.faults)) lines.push(`- ${id}: ${desc}`);
  }
  if (isTep) {
    lines.push('Task: identify the root cause of this abnormal episode. Output STRICT JSON only (no markdown, no extra text): {"top3": ["<root cause id/name>", ...], "reasoning": "<2-3 sentences>"} where top3 is your ranked list of up to 3 candidate root causes.');
  } else {
    lines.push('Task: (1) state whether this episode shows a fault or normal operation; (2) if a fault, give the most likely root cause and up to 2 alternatives. Output STRICT JSON only (no markdown, no extra text): {"verdict": "fault" | "normal", "top3": [...], "reasoning": "<2-3 sentences>"}');
  }
  return lines.join('\n') + '\n';
}

function archivedAnswer(caseId, regime) {
  const p = path.join(ANSWERS, `${caseId}.${regime}.json`);
  if (!fs.existsSync(p)) return null;
  const raw = fs.readFileSync(p, 'utf8');
  return JSON.parse(raw.slice(raw.indexOf('{')));
}

// ---------- execution ----------
export async function runLlmArm({ caseId, brief, regime, causeTable, prompt }) {
  const baseUrl = process.env.BASELINE_LLM_BASE_URL;
  const apiKey = process.env.BASELINE_LLM_API_KEY;
  const model = process.env.BASELINE_LLM_MODEL || 'glm-4.6';

  if (regime === 'fe_official') {
    // FE's exact EXPLAIN_ROOT prompt is part of the vendored protocol inputs
    const p = path.join(FE_PROMPTS, `${caseId}.fe_official.txt`);
    if (fs.existsSync(p)) prompt = fs.readFileSync(p, 'utf8');
  }

  if (!baseUrl || !apiKey) {
    const rec = archivedAnswer(caseId, regime);
    if (!rec) return { arm: 'llm', regime, mode: 'unavailable', error: `no live endpoint configured and no archived answer for ${caseId}.${regime}` };
    return {
      arm: 'llm',
      regime,
      mode: 'recorded',
      recorded_source: RECORDED_NOTE,
      prompt,
      answer: { top3: rec.top3 ?? [], verdict: rec.verdict ?? null, reasoning: rec.reasoning ?? '' },
    };
  }

  const { url } = validateEndpointBaseUrl(baseUrl); // throws on blocked hosts — before any request
  const endpoint = new URL('/chat/completions', url);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      signal: controller.signal,
      headers: { 'content-type': 'application/json', authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!res.ok) throw new Error(`LLM endpoint ${res.status}: ${(await res.text()).slice(0, 200)}`);
    const data = await res.json();
    const content = data.choices?.[0]?.message?.content ?? '';
    const start = content.indexOf('{');
    let answer;
    try { answer = JSON.parse(content.slice(start)); } catch { answer = { top3: [], reasoning: content.slice(0, 500) }; }
    return { arm: 'llm', regime, mode: 'live', endpoint_host: url.host, model, prompt, answer };
  } finally {
    clearTimeout(timer);
  }
}
