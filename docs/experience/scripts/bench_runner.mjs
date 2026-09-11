#!/usr/bin/env node
// 批量诊断评测循环器（骨架）—— 对标 FDDBenchmark CDR 口径
// 用法: node bench_runner.mjs [--cases cases.json] [--base http://localhost:3210]
//
// 系统没有批量诊断 API：POST /api/diagnosis/start 一次一个 run，
// 本脚本负责 启动 → 等待完成 → 解析 diagnosis.json → 与真值匹配 → 汇总 CDR/Top-k。
// 等待方式：轮询 run 目录的产物文件（04_diagnostics/diagnosis.json 出现且 05_review 完成即视为结束）。
import { setTimeout as sleep } from "node:timers/promises";
import fs from "node:fs/promises";
import path from "node:path";

const BASE = process.argv.includes("--base")
  ? process.argv[process.argv.indexOf("--base") + 1] : "http://localhost:3210";
const WORKSPACE = "workspace/diagnostic-runs";

// 评测用例：truth=根因真值描述；keywords=机理关键词（命中其一即 Top-1 候选）；
// expect=期望结论类型；难检故障（如 TEP 3/9/15）expect 用 "COMPETING_SET|NEEDS_DATA" 表达校准正确。
const CASES = JSON.parse(await fs.readFile(
  process.argv.includes("--cases")
    ? process.argv[process.argv.indexOf("--cases") + 1]
    : new URL("./bench_cases.example.json", import.meta.url), "utf8"));

async function startDiagnosis(c) {
  const res = await fetch(`${BASE}/api/diagnosis/start`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataPath: c.csv,
      user_question: c.user_question ?? "诊断本次异常的根本原因",
      ...(c.process_description ? { process_description: c.process_description } : {}),
    }),
  });
  if (!res.ok) throw new Error(`start failed: ${res.status} ${await res.text()}`);
  return res.json();
}

async function findNewestRunDir(before) {
  const dirs = await fs.readdir(WORKSPACE).catch(() => []);
  for (const d of dirs.sort().reverse()) {
    const stat = await fs.stat(path.join(WORKSPACE, d)).catch(() => null);
    if (stat?.mtime > before) return path.join(WORKSPACE, d);
  }
  return null;
}

async function waitComplete(runDir, timeoutMs = 2 * 3600_000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const dx = path.join(runDir, "04_diagnostics", "diagnosis.json");
    try { return JSON.parse(await fs.readFile(dx, "utf8")); } catch { /* 未生成 */ }
    await sleep(30_000);
  }
  throw new Error(`timeout waiting diagnosis.json in ${runDir}`);
}

// 关键词匹配：结论/假设文本中命中任一关键词 → Top-1 命中
function matchTruth(dx, c) {
  const text = JSON.stringify({ c: dx.conclusion ?? dx.root_cause ?? "", h: dx.competing_hypotheses ?? [] });
  const hit = c.keywords.some(k => text.toLowerCase().includes(k.toLowerCase()));
  return { top1: hit && dx.conclusion_type === "DETERMINED", topk: hit };
}

const results = [];
for (const c of CASES) {
  const before = new Date();
  const { run_dir: hint } = await startDiagnosis(c).catch(e => ({ error: String(e) }));
  const runDir = hint ?? await findNewestRunDir(before);
  if (!runDir) { results.push({ csv: c.csv, error: "no run dir" }); continue; }
  const dx = await waitComplete(runDir);
  const m = matchTruth(dx, c);
  const expectedTypes = (c.expect ?? "DETERMINED").split("|");
  results.push({
    csv: c.csv, runDir, conclusion_type: dx.conclusion_type, confidence: dx.confidence,
    top1: m.top1, topk: m.topk,
    calibrated: expectedTypes.includes(dx.conclusion_type),   // 三态校准正确性
  });
  console.error(`done: ${c.csv} → ${dx.conclusion_type} (${dx.confidence}) top1=${m.top1}`);
}

const ok = results.filter(r => r.top1).length;
const cal = results.filter(r => r.calibrated).length;
console.log(JSON.stringify({
  summary: { total: results.length, top1: ok, cdr: (ok / results.length).toFixed(3), calibrated: cal },
  results,
}, null, 2));
