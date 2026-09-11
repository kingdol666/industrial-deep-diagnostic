#!/usr/bin/env node
// make_dataset_manifest.mjs — 生成 results/benchmark/dataset_manifest.json（sha256 + 行列数）
// 用法: node make_dataset_manifest.mjs
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const ROOT = path.resolve(import.meta.dirname, "..", "..");
const OUT = path.join(ROOT, "results/benchmark/dataset_manifest.json");
const PREPARED = path.join(ROOT, "data/benchmark/prepared");
const LOCK = path.join(ROOT, "data/benchmark/downloads.lock.json");
const files = [];

// 1) prepared CSV inputs — auto-discover every dataset directory
const preparedDirs = fs.existsSync(PREPARED)
  ? fs.readdirSync(PREPARED, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name).sort()
  : [];
for (const ds of preparedDirs) {
  const dir = path.join(PREPARED, ds);
  for (const f of fs.readdirSync(dir).filter(x => x.endsWith(".csv")).sort()) {
    const p = path.join(dir, f);
    const raw = fs.readFileSync(p, "utf8");
    const lines = raw.trim().split(/\r?\n/);
    files.push({
      path: `data/benchmark/prepared/${ds}/${f}`,
      kind: "prepared",
      dataset: ds,
      sha256: crypto.createHash("sha256").update(raw).digest("hex"),
      rows: lines.length - 1, cols: lines[0].split(",").length,
    });
  }
}

// 2) raw downloads — reuse the sha256 already recorded by download-datasets.mjs
//    (avoids re-hashing multi-hundred-MB archives in this script)
if (fs.existsSync(LOCK)) {
  const lock = JSON.parse(fs.readFileSync(LOCK, "utf8"));
  for (const [id, entry] of Object.entries(lock.datasets || {})) {
    for (const f of entry.files || []) {
      if (!fs.existsSync(path.join(ROOT, f.path))) continue;
      files.push({
        path: f.path,
        kind: "archive",
        dataset: id,
        sha256: f.sha256,
        bytes: f.bytes,
        url: f.url,
      });
    }
  }
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ generated_at: new Date().toISOString(), count: files.length, files }, null, 1));
console.log(`manifest: ${files.length} entr(ies) -> ${path.relative(ROOT, OUT)}`);
