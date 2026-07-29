#!/usr/bin/env node
// report-section-check.mjs — Verify report.md contains all 9 required sections.
//
// Usage:
//   node report-section-check.mjs <RUN_DIR>
//
// Exit code: 0 = PASS, 1 = FAIL

import fs from 'fs';
import { join } from 'path';

const runDir = process.argv[2];
if (!runDir) {
  console.error('Usage: node report-section-check.mjs <RUN_DIR>');
  process.exit(1);
}

const reportPath = join(runDir, 'report.md');
if (!fs.existsSync(reportPath)) {
  console.log(JSON.stringify({
    status: 'FAIL',
    error: 'report.md not found'
  }, null, 2));
  process.exit(1);
}

const content = fs.readFileSync(reportPath, 'utf8');
const lines = content.split('\n');

// Extract all ## and ### headers
const headers = lines
  .filter(l => /^#{2,3}\s/.test(l))
  .map(l => l.replace(/^#+\s*/, '').trim());

const REQUIRED_SECTIONS = [
  { keywords: ['执行摘要', 'Executive Summary'], label: '执行摘要/Executive Summary' },
  { keywords: ['核心证据', '对齐图'], label: '核心证据/对齐图' },
  { keywords: ['诊断结论', 'Diagnosis'], label: '诊断结论/Diagnosis' },
  { keywords: ['证据全景', 'Evidence Panorama'], label: '证据全景/Evidence Panorama' },
  { keywords: ['竞争假设', '排除逻辑', '排除的可能'], label: '竞争假设/排除逻辑' },
  { keywords: ['详细推导', 'Detailed Derivation', '推理过程', '得出结论'], label: '详细推导/推理过程' },
  { keywords: ['推理链', 'Reasoning Chain'], label: '推理链/Reasoning Chain' },
  { keywords: ['统计', '数据统计', 'Data', '数据与统计'], label: '统计验证/数据统计' },
  { keywords: ['行动方案', '局限', 'Action', '下一步'], label: '行动方案/局限性' },
];

const foundSections = [];
const missingSections = [];

for (const section of REQUIRED_SECTIONS) {
  const found = headers.some(h =>
    section.keywords.some(kw => h.includes(kw))
  );
  if (found) {
    const match = headers.find(h => section.keywords.some(kw => h.includes(kw)));
    foundSections.push(match);
  } else {
    missingSections.push(section.label);
  }
}

const result = {
  status: missingSections.length === 0 ? 'PASS' : 'FAIL',
  found_sections: foundSections,
  missing_sections: missingSections,
  total_sections: REQUIRED_SECTIONS.length,
  found_count: foundSections.length
};

console.log(JSON.stringify(result, null, 2));
process.exit(result.status === 'PASS' ? 0 : 1);
