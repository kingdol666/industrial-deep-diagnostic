#!/usr/bin/env node
// fix_schema_shapes.mjs — schema-conformance normalizers for Step 3 artifacts.
// 1) plot_manifest.json: figure_type must use the schema enum (line→trend),
//    priority must be an integer (MANDATORY→1, SUPPLEMENTARY→3).
// 2) data_analysis_conclusion.json: analysis_boundary Phase 0.4 did not run in this
//    pipeline, so only the honest {missing} branch is kept (the synthesized artifact
//    carried empty tier-shape keys that made it match two oneOf branches).
import fs from 'fs';
import path from 'path';

const runDir = process.argv[2];

// --- plot_manifest ---
const pmPath = path.join(runDir, '03_figures', 'plot_manifest.json');
const pm = JSON.parse(fs.readFileSync(pmPath, 'utf8'));
const prioInt = (p) => (String(p).toUpperCase().includes('MANDATORY') ? 1 : 3);
const figType = (t) => {
  const map = { temporal_overlay: 'temporal_overlay', line: 'trend', scatter: 'scatter', heatmap: 'heatmap', boxplot: 'boxplot' };
  return map[t] || 'other';
};
pm.plots = (pm.plots || []).map((pl) => ({
  ...pl,
  figure_type: figType(pl.figure_type || pl.chart_type),
  priority: prioInt(pl.priority ?? pl.vlm_priority ?? 'SUPPLEMENTARY')
}));
pm.metadata = {
  ...pm.metadata,
  total_plots: pm.plots.length
};
fs.writeFileSync(pmPath, JSON.stringify(pm, null, 2) + '\n', 'utf8');

// --- data_analysis_conclusion ---
const cPath = path.join(runDir, '02_processed', 'data_analysis_conclusion.json');
const c = JSON.parse(fs.readFileSync(cPath, 'utf8'));
if (c.analysis_boundary && typeof c.analysis_boundary.missing === 'string') {
  c.analysis_boundary = { missing: c.analysis_boundary.missing };
}
fs.writeFileSync(cPath, JSON.stringify(c, null, 2) + '\n', 'utf8');

console.log(JSON.stringify({
  plot_manifest: { figure_types: pm.plots.map(x => x.figure_type), priorities: pm.plots.map(x => x.priority) },
  analysis_boundary_keys: Object.keys(c.analysis_boundary)
}));
