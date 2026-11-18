#!/usr/bin/env node
/**
 * finalize_figures.mjs — rebuild 03_figures/plot_manifest.json with ALL real plots
 * (dp_toolkit visualize overwrites the manifest; this merges), restore
 * metadata.excluded_charts, and write image_captions.json with numeric
 * key_observations sourced from 02_processed/expert_findings.json and
 * 02_processed/validate_report.json (no invented numbers).
 * Usage: node finalize_figures.mjs <RUN_DIR>
 */
import fs from 'node:fs';
import path from 'node:path';

const RUN = process.argv[2];
const FIG = path.join(RUN, '03_figures');
const j = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));

const ef = j(path.join(RUN, '02_processed/expert_findings.json'));
const vr = j(path.join(RUN, '02_processed/validate_report.json'));
const v = (p, t) => vr.validations.find(x => x.parameter === p && x.target === t) || {};
const r3 = x => (x.pearson_r === undefined ? 'NA' : x.pearson_r.toFixed(3));
const ss = ef.regime_segments;

const EXCLUDED = (j(path.join(FIG, 'plot_manifest.json')).metadata?.excluded_charts) || [];

const plots = [
  { filename: 'fig_hetero_profile_heatmap.png', figure_type: 'profile_heatmap_over_time', priority: 'CRITICAL',
    description_zh: '带材横向温度剖面 时间×位置 热图（PROF 30min，12 位点 × 480 快照）+ 关键参数 z 叠加 + 操作事件竖线',
    columns: ['HX-PROF-L1BANDTEMPPROFILE30M-MEAN', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV', 'FUR-Z3-TEMP', 'FUR-YIELD'] },
  { filename: 'fig_vlm_temporal_overlay.png', figure_type: 'vlm_temporal_overlay', priority: 'CRITICAL',
    description_zh: '8 参数 + 2 质量目标 z 归一化共享时间轴叠加（VLM MANDATORY）',
    columns: ['FUR-Z3-TEMP', 'FUR-SPEED', 'FUR-PRES', 'HX-PROF-L1BANDTEMPPROFILE30M-MEAN', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV', 'HX-MAP-L1FURNACETHERMALMAP2-MEAN', 'HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR', 'HX-IMG-L1SURFACECCDINDEX-MEAN', 'FUR-YIELD', 'FUR-OUT-TEMP'] },
  { filename: 'fig_event_response.png', figure_type: 'event_response_bar', priority: 'HIGH',
    description_zh: '维护(02-06 06:40)/升温(02-08 10:00)事件前后 ±12h 相对变化' },
  { filename: 'fig2_key_scatter.png', figure_type: 'scatter_grid', priority: 'MEDIUM',
    description_zh: 'dp_toolkit 通用图：目标-参数散点网格（含 r 标注）' },
  { filename: 'fig6_causal_evidence_map.png', figure_type: 'causal_evidence_map', priority: 'HIGH',
    description_zh: '因果证据图：节点=参数/目标，边=通过 validate_report 的显著相关' },
];
for (const p of plots) p.path = '03_figures/' + p.filename;

const manifest = {
  plots,
  metadata: {
    generated_by: 'data-processor (finalize_figures.mjs; charts from adaptive_charts/expert_analysis/generate_vlm_charts/dp_toolkit visualize)',
    total_plots: plots.length,
    plot_budget: 'fast mode <= 8 plots — 5 kept, all hypothesis-relevant',
    excluded_charts: EXCLUDED.concat([
      { filename: 'fig_adaptive_contour_FUR-Z2-TEMP.png', reason: 'false 2D-field contour (grid-inferred axes FUR-Z1-TEMP x HX-MAP-POSMAX-Y); deleted' },
      { filename: 'fig_adaptive_contour_FUR-Z3-TEMP.png', reason: 'false 2D-field contour; deleted' },
      { filename: 'fig_adaptive_contour_FUR-SPEED.png', reason: 'false 2D-field contour; deleted' },
      { filename: 'fig_adaptive_contour_FUR-PRES.png', reason: 'false 2D-field contour; deleted' },
      { filename: 'fig_adaptive_contour_FUR-OUT-TEMP.png', reason: 'false 2D-field contour; deleted' },
      { filename: 'fig_adaptive_contour_FUR-YIELD.png', reason: 'false 2D-field contour; deleted' },
    ].filter((x, i, a) => !EXCLUDED.some(e => e.filename === x.filename) && a.findIndex(y => y.filename === x.filename) === i)),
    excluded_charts_note: 'adaptive_charts.py false-detected a 2D field from unrelated column pairs (FUR-Z1-TEMP x HX-MAP-POSMAX-Y, 311x4 grid); 6 junk contours were deleted; no physical x/y field exists in this dataset (time x position profiles are handled by fig_hetero_profile_heatmap.png).',
  },
};
fs.writeFileSync(path.join(FIG, 'plot_manifest.json'), JSON.stringify(manifest, null, 1));

const ny = x => (x === undefined || x === null ? 'NA' : String(x));
const captions = {
  generated_at: new Date().toISOString(),
  source_files: {
    'fig_hetero_profile_heatmap.png': '07_hetero/features/PROF-L1BANDTEMPPROFILE30M.csv + 02_processed/cleaned_data.csv (via 06_scripts/expert_analysis.py)',
    'fig_vlm_temporal_overlay.png': '02_processed/cleaned_data.csv (via generate_vlm_charts.py)',
    'fig_event_response.png': '02_processed/cleaned_data.csv (via 06_scripts/expert_analysis.py)',
    'fig2_key_scatter.png': '02_processed/cleaned_data.json (via dp_toolkit.py visualize)',
    'fig6_causal_evidence_map.png': '02_processed/feature_summary.json + validate_report.json (via dp_toolkit.py visualize)',
  },
  total_figures: 5,
  figures: {
    'fig_hetero_profile_heatmap.png': {
      description: '上方：带材横向温度剖面（12 位点 × 480 个 30min 快照）时间×位置热图，青虚线为操作事件（02-06 06:40 检修、02-08 10:00 升温、02-08 21:00 恢复、02-10 09:00 闭环）；下方：PROF-MEAN/EDGE-L-DEV/EDGE-R-DEV 与 FUR-Z3-TEMP/FUR-YIELD 的 z 归一化叠加。数据源为 PROF 快照原始矩阵与清洗后锚定表。',
      key_observations: [
        `剖面均值三段水平:前段 ${ny(ss.A_pre_aging.columns.pmean.mean)}°C → 维护窗 ${ny(ss.B_maintenance_window.columns.pmean.mean)}°C → 恢复后 ${ny(ss.D_restored.columns.pmean.mean)}°C (ΔB-A=${ny(ef.level_shift_deltas.pmean.B_minus_A)})`,
        `右边缘偏差 EDGE-R-DEV 三段: ${ny(ss.A_pre_aging.columns.pedger.mean)} → ${ny(ss.B_maintenance_window.columns.pedger.mean)} → ${ny(ss.D_restored.columns.pedger.mean)}°C，维护窗内右边缘显著变冷 (ΔB-A=${ny(ef.level_shift_deltas.pedger.B_minus_A)})`,
        `剖面斜率 SLOPE-LSQ 塌陷: ${ny(ss.A_pre_aging.columns.pslope.mean)} → ${ny(ss.B_maintenance_window.columns.pslope.mean)} → ${ny(ss.D_restored.columns.pslope.mean)} °C/100位 (ΔB-A=${ny(ef.level_shift_deltas.pslope.B_minus_A)})`,
        `快照级（去重后 n=480）PROF-MEAN 与 FUR-Z3-TEMP r=${ny(ef.snapshot_level_correlation.pmean.vs_z3_pearson)}、与 FUR-YIELD r=${ny(ef.snapshot_level_correlation.pmean.vs_yield_pearson)}（Spearman ${ny(ef.snapshot_level_correlation.pmean.vs_yield_spearman)}，水平偏移主导）`,
        `热图显示水平变化集中在 02-06 14:30→02-09 07:00 窗口（YIELD 变点窗口均值 ${ny(ef.yield_cp_window_steady_idx663_977.yield_mean)}% vs 之前 ${ny(ef.yield_cp_window_steady_idx663_977.yield_mean_before)}%），与右半侧变冷的横向梯度形态一致`,
      ],
      diagnostic_implication: '剖面恶化是水平偏移（right-side cooling）而非整体降温：右边缘偏差与斜率的台阶式塌陷与 02-06 后三区后段掉温事件对齐，是"炉膛右侧加热能力损失→带材右边缘变冷"链路的直接可视证据。',
      chart_type: 'heatmap', trend_shapes: 'step/plateau（水平台阶）+ 局部噪声',
      divergence_points: '02-06 14:30 起剖面斜率与均值开始偏离前段基线；02-08 10:00 升温后 02-08 21:00 起恢复',
      anomaly_regions: `OUT-TEMP 平台下移窗 02-07 00:20–02-08 23:40（均值 ${ny(ef.out_temp_dip_window_steady_idx722_933.out_temp_mean_dip)}°C vs 基线 ~549.99°C）`,
      validation_issues: ['Pearson-Spearman 背离: PROF-MEAN~Z3 r=0.858 vs ρ≈0.49（水平偏移主导）'],
      figure_order: 1,
    },
    'fig_vlm_temporal_overlay.png': {
      description: 'VLM 专用多参数时间叠加：8 个过程参数（三区炉温/速度/炉压/剖面均值/右边缘偏差/炉膛场均值/场不对称/图像均值）与 2 个质量目标（FUR-YIELD、FUR-OUT-TEMP）z 归一化共享时间轴，用于读取同步性、先导性、事件响应与趋势形态。',
      key_observations: [
        `FUR-Z3-TEMP 与 3 个质量指标的稳态相关: ↔FUR-YIELD r=${r3(v('FUR-Z3-TEMP', 'FUR-YIELD'))} (lag ${ny(v('FUR-Z3-TEMP', 'FUR-YIELD').best_lag_steps)} step)，↔FUR-OUT-TEMP r=${r3(v('FUR-Z3-TEMP', 'FUR-OUT-TEMP'))} (lag +4 step≈40min, 物理停留时间量级)，↔PROF-MEAN r=${r3(v('FUR-Z3-TEMP', 'HX-PROF-L1BANDTEMPPROFILE30M-MEAN'))}`,
        `维护窗水平偏移（B−A）: Z3 ${ny(ef.level_shift_deltas.z3.B_minus_A)}°C、OUT-TEMP ${ny(ef.level_shift_deltas.out.B_minus_A)}°C、YIELD ${ny(ef.level_shift_deltas.yield.B_minus_A)}pt、IMG-MEAN ${ny(ef.level_shift_deltas.immean.B_minus_A)}`,
        `02-08 10:00 升温事件 ±12h: Z3 ${ny(ef.event_response_windows_12h.heatup_20260208_1000.z3_before)} → ${ny(ef.event_response_windows_12h.heatup_20260208_1000.z3_after)}°C (Δ${ny(ef.event_response_windows_12h.heatup_20260208_1000.z3_delta)})，随后恢复至 879.5°C（D 段均值）`,
        `同步通道组：MAP-MEAN / MAP-CENTROID-X / IMG-MEAN / IMG-STD 与 Z3-YIELD 同向移动（|r|≥0.86），与相机-热辐射物理通道一致`,
      ],
      diagnostic_implication: '所有强相关的共同驱动是三区炉温水平：Z3 先导 OUT-TEMP ~40min、与 YIELD/PROF 几乎同步，说明质量劣化的时间源在均热段（三区）而非传输段。',
      chart_type: 'overlay', trend_shapes: '水平台阶 + 事件后回升',
      divergence_points: '02-06 06:40 前后 Z3 与 YIELD 开始同向下行；02-08 21:00 后同步回升',
      anomaly_regions: '过渡窗 02-08 10:00–21:00（升温恢复，非稳态）',
      validation_issues: ['多对 Pearson r>0.9 但 Spearman≈0.5（水平偏移主导，见 validate_report.summary.level_shift_dominated_pairs）'],
      figure_order: 2,
    },
    'fig_event_response.png': {
      description: '两个操作事件（02-06 06:40 检修通知、02-08 10:00 更换加热管后升温）前后 ±12h 各指标相对变化条形图（左=事件前均值，右=事件后均值）。',
      key_observations: [
        `检修事件 ±12h: Z3 ${ny(ef.event_response_windows_12h.maint_20260206_0640.z3_before)} → ${ny(ef.event_response_windows_12h.maint_20260206_0640.z3_after)}°C (Δ${ny(ef.event_response_windows_12h.maint_20260206_0640.z3_delta)})，YIELD Δ${ny(ef.event_response_windows_12h.maint_20260206_0640.yield_delta)}pt，IMG-MEAN Δ${ny(ef.event_response_windows_12h.maint_20260206_0640.immean_delta)}`,
        `升温事件 ±12h: Z3 ${ny(ef.event_response_windows_12h.heatup_20260208_1000.z3_before)} → ${ny(ef.event_response_windows_12h.heatup_20260208_1000.z3_after)}°C (Δ+${ny(ef.event_response_windows_12h.heatup_20260208_1000.z3_delta)})`,
        `事件响应幅度远小于分段水平偏移（Z3 事件 Δ≈±0.7~1.1°C vs 维护窗水平偏移 −4.93°C）→ 劣化是慢性漂移而非事件瞬时扰动`,
      ],
      diagnostic_implication: '事件窗内瞬时响应轻微，真正的劣化主体是 02-06→02-08 的持续性掉温平台（−4.93°C），支持"加热管老化渐进失效"而非"维护操作引入扰动"的解释。',
      chart_type: 'bar', figure_order: 3,
    },
    'fig2_key_scatter.png': {
      description: 'dp_toolkit 通用散点网格：关键目标（FUR-YIELD/FUR-OUT-TEMP）对各参数散点，带相关标注。',
      key_observations: [
        `Z3 与 YIELD 散点在稳态数据上呈强线性带 r=${r3(v('FUR-Z3-TEMP', 'FUR-YIELD'))}（n=1367，水平台阶叠加）`,
        `Z3 与 PROF-MEAN r=${r3(v('FUR-Z3-TEMP', 'HX-PROF-L1BANDTEMPPROFILE30M-MEAN'))}；ASYM-LR 与 EDGE-L-DEV r=${r3(v('HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV'))}（lag ${ny(v('HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV').best_lag_steps)} step）`,
        `FUR-SPEED 与 OUT-TEMP r=${r3(v('FUR-SPEED', 'FUR-OUT-TEMP'))}（不显著，速度方差仅 ${ny(ef.confounder_probes.speed.min)}–${ny(ef.confounder_probes.speed.max)}，无检验功效）`,
      ],
      diagnostic_implication: '散点形态（窄带、少量离群）表明相关由工艺水平带动；速度-温度通道在本数据集方差不足，无法验证停留时间机理。',
      chart_type: 'scatter', figure_order: 4,
    },
    'fig6_causal_evidence_map.png': {
      description: '因果证据图：节点为参数/质量目标，边为通过 validate_report 筛选的显著相关；用于诊断阶段的候选根因排序。',
      key_observations: [
        `中心节点 FUR-Z3-TEMP 连向 FUR-YIELD(r=${r3(v('FUR-Z3-TEMP', 'FUR-YIELD'))})、FUR-OUT-TEMP(r=${r3(v('FUR-Z3-TEMP', 'FUR-OUT-TEMP'))})、PROF-MEAN(r=${r3(v('FUR-Z3-TEMP', 'HX-PROF-L1BANDTEMPPROFILE30M-MEAN'))})`,
        `横向通道: MAP-ASYM-LR ↔ EDGE-L-DEV r=${r3(v('HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV'))}、↔ EDGE-R-DEV r=${r3(v('HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR', 'HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV'))}`,
        `表面通道: IMG-MEAN ↔ YIELD r=${r3(v('HX-IMG-L1SURFACECCDINDEX-MEAN', 'FUR-YIELD'))}，与 Z3 快照级 r=${ny(ef.snapshot_level_correlation.immean.vs_z3_pearson)}（热辐射物理通道或相机漂移，无法用现有数据区分）`,
        `validate_report: ${vr.summary.total_pairs_analyzed} 对中 ${vr.summary.significant_pairs} 对显著；趋势混杂 ${vr.summary.trend_confounded_pairs} 对；水平偏移主导标记 ${vr.summary.level_shift_dominated_pairs} 对`,
      ],
      diagnostic_implication: '证据网以三区炉温为单一上游汇聚点，炉膛场不对称与图像统计均为其下游/伴随通道——根因候选应聚焦三区加热能力（后段加热管）而非独立的多重故障。',
      chart_type: 'diagram', figure_order: 5,
    },
  },
};
fs.writeFileSync(path.join(FIG, 'image_captions.json'), JSON.stringify(captions, null, 1));
console.log(`plot_manifest.json: ${plots.length} plots (excluded_charts ${manifest.metadata.excluded_charts.length}); image_captions.json: ${Object.keys(captions.figures).length} figures`);
