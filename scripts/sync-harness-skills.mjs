#!/usr/bin/env node
// sync-harness-skills.mjs — 把 .claude/skills（唯一权威源）镜像到其他 Harness 的 skill 目录。
//
// 背景: .claude/skills 是所有执行引擎（claude/omp/codex/hermes/... 后端 14 引擎）
// 实际加载的唯一 skill 源。.agents/skills（ZCode 等通用 agent 发现）与
// .hermes/skills（Hermes CLI profile 的 external_dirs）是**生成副本**，禁止手改；
// 修改 skill 一律改 .claude/skills，然后运行本脚本同步。
//
// 用法:
//   node scripts/sync-harness-skills.mjs           # 执行镜像（多删少补）
//   node scripts/sync-harness-skills.mjs --check   # 只检查漂移，有差异则退出码 1
//
// 镜像语义:
//   - 目标目录的 skill 集合与文件内容必须与源逐字节一致
//   - 目标多出的文件/目录删除（例如已退役的 .hermes 合并大包 industrial-deep-diagnostic）
//   - __pycache__/ 与 .mimosa/ 在两侧都忽略（构建产物/钩子产物，不参与比较）
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, ".claude", "skills");
const TARGETS = [
  path.join(ROOT, ".agents", "skills"),
  path.join(ROOT, ".hermes", "skills"),
];
const IGNORE_DIRS = new Set(["__pycache__", ".mimosa"]);
const CHECK_ONLY = process.argv.includes("--check");

if (!fs.existsSync(path.join(SRC, "industrial-analysis-auto", "SKILL.md"))) {
  console.error(`FATAL: source skill missing: ${SRC}`);
  process.exit(2);
}

// rel path -> absolute path（跳过 IGNORE_DIRS）
function walk(base) {
  const out = new Map();
  if (!fs.existsSync(base)) return out;
  const visit = (dir, rel) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (IGNORE_DIRS.has(entry.name)) continue;
      const abs = path.join(dir, entry.name);
      const r = rel ? `${rel}/${entry.name}` : entry.name;
      if (entry.isDirectory()) visit(abs, r);
      else out.set(r.split(path.sep).join("/"), abs);
    }
  };
  visit(base, "");
  return out;
}

function pruneEmptyDirs(base) {
  if (!fs.existsSync(base)) return;
  for (const entry of fs.readdirSync(base, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const abs = path.join(base, entry.name);
    // 忽略目录（构建/钩子产物）在目标侧一律清除，避免残留空壳目录
    if (IGNORE_DIRS.has(entry.name)) { fs.rmSync(abs, { recursive: true, force: true }); continue; }
    pruneEmptyDirs(abs);
    if (fs.readdirSync(abs).length === 0) fs.rmdirSync(abs);
  }
}

const srcFiles = walk(SRC);
let totalDrift = 0;

for (const TARGET of TARGETS) {
  const rel = path.relative(ROOT, TARGET);
  if (!fs.existsSync(TARGET)) {
    if (CHECK_ONLY) { console.error(`DRIFT  ${rel}: missing directory`); totalDrift++; continue; }
    fs.mkdirSync(TARGET, { recursive: true });
  }
  const tgtFiles = walk(TARGET);

  const toDelete = [...tgtFiles.keys()].filter(k => !srcFiles.has(k));
  const toCopy = [];
  let unchanged = 0;
  for (const [k, srcAbs] of srcFiles) {
    const tgtAbs = tgtFiles.get(k);
    if (!tgtAbs) { toCopy.push([k, srcAbs]); continue; }
    if (fs.readFileSync(srcAbs).equals(fs.readFileSync(tgtAbs))) unchanged++;
    else toCopy.push([k, srcAbs]);
  }

  if (CHECK_ONLY) {
    if (toDelete.length || toCopy.length) {
      console.error(`DRIFT  ${rel}: ${toCopy.length} to update, ${toDelete.length} to delete (${unchanged} identical)`);
      totalDrift++;
    } else {
      console.log(`OK     ${rel}: ${unchanged} files identical`);
    }
    continue;
  }

  for (const k of toDelete) {
    fs.rmSync(path.join(TARGET, k), { force: true });
  }
  for (const [k, srcAbs] of toCopy) {
    const dst = path.join(TARGET, k);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(srcAbs, dst);
  }
  pruneEmptyDirs(TARGET);
  console.log(`${rel}: +${toCopy.length} updated/added, -${toDelete.length} deleted, ${unchanged} identical`);
}

if (CHECK_ONLY) {
  if (totalDrift > 0) {
    console.error(`\n${totalDrift} mirror(s) drifted from .claude/skills — run: node scripts/sync-harness-skills.mjs`);
    process.exit(1);
  }
  console.log("\nAll harness skill mirrors are in sync with .claude/skills.");
} else {
  console.log("\nDone. Mirrors regenerated from .claude/skills (single source of truth).");
}
