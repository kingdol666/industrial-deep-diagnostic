#!/usr/bin/env node
// gen_input.mjs — deterministic bearing_overheat scenario input generator
// Causal structure (ground truth for the demo):
//   cooling_water_flow_lpm: 12.0 -> 8.0 step at row index 60 (scaling/fouling)
//   bearing_temp_c: +8.0 degC starting at row index 62 (lag = 2 samples after flow step), then holds
//   vibration_mm_s: +0.4 same-direction slight rise, same lag 2
//   motor_load_pct / ambient_temp_c: stationary noise only
import fs from 'fs';
import path from 'path';

const runDir = process.argv[2];
if (!runDir) { console.error('usage: node gen_input.mjs <run_dir>'); process.exit(2); }

// mulberry32 seeded PRNG — fixed seed for reproducibility
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(20261119);
// Approximate standard normal via Irwin-Hall (sum of 6 uniforms, centered)
function gauss() {
  return (rand() + rand() + rand() + rand() + rand() + rand() - 3) * Math.sqrt(2);
}

const N = 120;
const START = Date.parse('2026-11-18T08:00:00+08:00');
const STEP_MS = 2 * 60 * 1000;
const FLOW_STEP_AT = 60;   // row index where flow steps 12.0 -> 8.0
const LAG = 2;             // bearing_temp/vibration respond FLOW_STEP_AT + LAG
const rows = [];
for (let i = 0; i < N; i++) {
  const ts = new Date(START + i * STEP_MS);
  const iso = ts.toISOString().replace('Z', '+08:00').replace('T', 'T');
  // ISO with +08:00: build manually to avoid TZ drift
  const d = new Date(START + i * STEP_MS);
  const pad = (x) => String(x).padStart(2, '0');
  // Since START is expressed as +08:00, use fixed-offset arithmetic
  const t8 = new Date(START + i * STEP_MS);
  const y = t8.getUTCFullYear(), mo = t8.getUTCMonth() + 1, da = t8.getUTCDate();
  // Note: Date.parse('...+08:00') yields UTC millis of that local time; UTC fields
  // correspond to Beijing clock shifted by -8h. Compensate +8h:
  const t = new Date(START + i * STEP_MS + 8 * 3600 * 1000);
  const Y = t.getUTCFullYear(), M = pad(t.getUTCMonth() + 1), D = pad(t.getUTCDate());
  const H = pad(t.getUTCHours()), Mi = pad(t.getUTCMinutes()), S = pad(t.getUTCSeconds());
  const stamp = `${Y}-${M}-${D}T${H}:${Mi}:${S}+08:00`;

  const flow = (i < FLOW_STEP_AT ? 12.0 : 8.0) + gauss() * 0.15;
  const stepTemp = i >= FLOW_STEP_AT + LAG;
  const temp = (stepTemp ? 73.0 : 65.0) + gauss() * 0.25;
  const vib = (stepTemp ? 2.4 : 2.0) + gauss() * 0.05;
  const load = 75.0 + gauss() * 0.8;
  const ambient = 28.0 + gauss() * 0.5;
  rows.push([stamp, temp.toFixed(2), load.toFixed(2), flow.toFixed(2), ambient.toFixed(2), vib.toFixed(3)].join(','));
}
const csv = ['timestamp,bearing_temp_c,motor_load_pct,cooling_water_flow_lpm,ambient_temp_c,vibration_mm_s', ...rows].join('\n') + '\n';
const out = path.join(runDir, '00_input', 'bearing_data.csv');
fs.writeFileSync(out, csv, 'utf8');

const userContext = {
  user_complaint: '轴承温度偏高,请查根因',
  scene: 'bearing_overheat',
  reported_symptoms: [
    '轴承温度(bearing_temp_c)较正常水平明显偏高',
    '疑似伴随振动轻微上升'
  ],
  operating_context: '电机驱动产线关键风机轴承,冷却水回路为闭式循环,DCS 每 2 分钟采集一次',
  expectation: '给出根因结论与置信度,如需整改请附验证计划',
  language: 'zh'
};
fs.writeFileSync(path.join(runDir, '00_input', 'user_context.json'), JSON.stringify(userContext, null, 2), 'utf8');
console.log(JSON.stringify({ written: [out, 'user_context.json'], rows: N, first: rows[0], flow_step_row_index: FLOW_STEP_AT, temp_step_row_index: FLOW_STEP_AT + LAG }));
