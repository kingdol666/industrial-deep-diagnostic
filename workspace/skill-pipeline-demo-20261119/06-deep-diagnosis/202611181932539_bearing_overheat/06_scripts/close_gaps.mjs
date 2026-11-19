#!/usr/bin/env node
// close_gaps.mjs — close pipeline-finalize gaps found on first pass:
// 1) 01_ontology/schema.json (schema copy alongside the ontology, finalize contract)
// 2) 02_processed/analysis_parameter_selection.json (Phase 0.4, deterministic from ontology roles)
// 3) diagnosis.process_fluctuation_analysis: analysis_performed + key_process_findings (closure Rule 1)
// 4) diagnosis.integrated_dual_drive_analysis (closure Rule 2; data view IS process_plus_inspection)
// 5) anomaly_report.dual_drive_analysis.cross_domain_links (script-derived lag-CCF link, provenance noted)
// All added numbers come from 02_processed/validate_report.json / time_lag_analysis.json (no new statistics).
import fs from 'fs';
import path from 'path';

const runDir = process.argv[2];
if (!runDir) { console.error('usage: node close_gaps.mjs <run_dir>'); process.exit(2); }
const read = (p) => JSON.parse(fs.readFileSync(path.join(runDir, p), 'utf8'));
const write = (p, o) => fs.writeFileSync(path.join(runDir, p), JSON.stringify(o, null, 2) + '\n', 'utf8');

// 1) schema copy
fs.copyFileSync(
  'D:/codes/myskills/idd-doe-impl/.claude/skills/industrial-ontology-builder/schemas/ontology_schema.json',
  path.join(runDir, '01_ontology', 'schema.json')
);

// 2) Phase 0.4 analysis parameter selection (deterministic from ontology roles)
write('02_processed/analysis_parameter_selection.json', {
  source: 'Phase 0.4 ontology-guided analysis selection',
  ontology_file: '01_ontology/ontology.json',
  parameter_physical_groups: {
    cooling_capacity: ['cooling_water_flow_lpm'],
    heat_generation: ['motor_load_pct'],
    heat_sink_boundary: ['ambient_temp_c'],
    bearing_condition: ['bearing_temp_c', 'vibration_mm_s']
  },
  quality_targets: ['bearing_temp_c', 'vibration_mm_s'],
  analysis_tiers: {
    tier_1: [
      {
        target: 'bearing_temp_c',
        predictor: 'cooling_water_flow_lpm',
        justification: '同回路同阶段已知因果物理: Q=m_water·cp·ΔT, 流量下降→散热能力下降→温度上升(direction=−); 本体机制边 type=physical/strength=strong, 优先分析'
      }
    ],
    tier_2: [
      {
        target: 'bearing_temp_c',
        predictor: 'motor_load_pct',
        justification: '上游参数有可信传播路径: 负载↑→轴承机械发热↑→温度↑(方向+); 本体机制边 strength=moderate, 作为备择假设 H3 通道'
      }
    ],
    tier_3: [
      {
        target: 'bearing_temp_c',
        predictor: 'ambient_temp_c',
        justification: '间接/弱连接: 环境温度经散热终温缓变影响温度(日内尺度), 与2采样点级阶跃的形态匹配度低; 作为备择假设 H2/混杂对照'
      }
    ]
  },
  pruned: [
    { predictor: 'motor_load_pct', target: 'vibration_mm_s', reason: '无直接物理通道声明(振动经温度/润滑状态间接关联); 避免无机制支撑的伪相关检验' },
    { predictor: 'ambient_temp_c', target: 'vibration_mm_s', reason: '无直接物理通道声明; 环境温度与轴承振动的耦合弱且间接' },
    { predictor: 'cooling_water_flow_lpm', target: 'vibration_mm_s', reason: '流量对振动无直接机制边(须以温度为中介); 直接检验会稀释机制链' }
  ],
  predictor_cols: ['cooling_water_flow_lpm', 'motor_load_pct', 'ambient_temp_c'],
  exclude_cols: ['timestamp'],
  derived_features_to_compute: [],
  notes: '与 stats/run.py 实际调用一致(target=bearing_temp_c; predictors=flow/load/ambient; time-col=timestamp; max_lag=10); 无派生特征需求(单源等间隔时序)'
});

// 3+4) diagnosis closure fields
const d = read('04_diagnostics/diagnosis.json');
d.process_fluctuation_analysis = {
  ...d.process_fluctuation_analysis,
  analysis_performed: true,
  key_process_findings: [
    'cooling_water_flow_lpm: 唯一 abrupt 波动源 — 变化点 idx60, mean 12.004→8.0225 (−33.2%, significant), cv=0.2001 (anomaly_report.json)',
    'motor_load_pct: 全程平稳 (cv=0.0106, mean 75.09%), 无变化点, 与温度相关不显著 (r=0.0254, p=0.7834)',
    'ambient_temp_c: 全程平稳 (cv=0.0167, mean 28.00℃), 无变化点, 与温度相关不显著 (r=0.0162, p=0.8608)',
    '纯工艺驱动结论: 冷却水流量阶跃下降是唯一与目标阶跃形态(滞后2步+保持)匹配的工艺侧驱动'
  ],
  ontology_physics_reasoning: '本体机制边 cooling_water_flow_lpm→bearing_temp_c (type=physical, direction=−, delayed_response, governing_equation: Q_cool=m_water·cp·(T_out−T_in)): 流量−33.2%→单位时间带热量同比例下降→热平衡点上移+8.02℃; 数据方向(负相关)/时滞(2步)/形态(阶跃保持)三要素与机理一致; physics_check 能量代理 −19.18% 独立支持'
};
d.integrated_dual_drive_analysis = {
  analysis_performed: true,
  has_quality_or_inspection_targets: true,
  linked_groups: ['cooling_capacity→bearing_condition', 'heat_generation→bearing_condition', 'heat_sink_boundary→bearing_condition'],
  process_to_quality_links: [
    {
      group: 'cooling_capacity→bearing_condition',
      process_parameter: 'cooling_water_flow_lpm',
      quality_target: 'bearing_temp_c',
      link_type: 'process_precedes_quality',
      statistical_evidence: '滞后CCF峰值 lag=−2: r=−0.9959 (n=118, 一致率1.0); Pearson −0.9626 (p≈0); Granger F=259.151@lag2; 变化点先后 60→62 恰2步 (validate_report.json/time_lag_analysis.json)',
      anomaly_evidence: '唯一 abrupt 工艺波动源 (anomaly_report.json cv=0.2001); 温度侧对应 +8.02℃ 平台台阶 (变化点 idx62)',
      ontology_physics_reasoning: 'Q=m_water·cp·ΔT: 流量下降→散热能力下降→热平衡点上移 (direction=−, delayed_response)',
      diagnostic_weight: 'critical'
    },
    {
      group: 'bearing_condition(inspection)',
      process_parameter: 'bearing_temp_c',
      quality_target: 'vibration_mm_s',
      link_type: 'coincident',
      statistical_evidence: '波动统计: temp span 8.02℃ 与 vib span 0.524 mm/s 同步双平台 (anomaly_report.json); 无独立相关检验(振动非目标列), 证据级 L4',
      anomaly_evidence: '叠加图 10:04 振动与温度同步轻升 (fig_adaptive_overlay.png; fast mode 无 VLM, 会话智能体读图)',
      ontology_physics_reasoning: '温度↑→润滑粘度/游隙变化→振动烈度轻升(伴生症状, 本体 correlative 边, 非根因)',
      diagnostic_weight: 'weak'
    }
  ],
  integrated_conclusion: '双驱动联合分析: 工艺驱动(冷却水流量阶跃−33.2%)经滞后2步传导至检查信号(轴承温度+8.02℃平台, 振动+0.4 同步轻升); 负载/环境两条工艺通道全程平稳且相关不显著 — 联合证据锁定 H1 为唯一存活根因'
};
write('04_diagnostics/diagnosis.json', d);

// 5) anomaly_report cross_domain_links (script-derived)
const a = read('02_processed/anomaly_report.json');
a.dual_drive_analysis = {
  ...a.dual_drive_analysis,
  cross_domain_links: [
    {
      process_parameter: 'cooling_water_flow_lpm',
      inspection_target: 'bearing_temp_c',
      link: 'process_precedes_quality',
      r: -0.9959,
      lag_steps: -2,
      n: 118,
      source: '02_processed/validate_report.json correlation.target_analysis.lagged_ccf (lag-CCF 峰值) + change_point_detection (60→62); 由 06_scripts/close_gaps.mjs 回填, 未新增统计'
    },
    {
      process_parameter: 'cooling_water_flow_lpm',
      inspection_target: 'vibration_mm_s',
      link: 'same_window',
      r: null,
      lag_steps: null,
      n: null,
      source: '03_figures/fig_adaptive_overlay.png 目视共变(fast mode 无VLM) + anomaly_report 波动统计; 无独立相关检验, 证据级 L4'
    }
  ],
  linkage_note: 'cross_domain_links 由 06_scripts/close_gaps.mjs 依据 validate_report.json 滞后CCF/变化点结果回填(dual-drive 闭合计录); 统计数字全部出自脚本工件'
};
write('02_processed/anomaly_report.json', a);

console.log(JSON.stringify({
  schema_copied: fs.existsSync(path.join(runDir, '01_ontology', 'schema.json')),
  analysis_parameter_selection: 'written',
  diagnosis_closure_fields: ['process_fluctuation_analysis.analysis_performed', 'integrated_dual_drive_analysis'],
  anomaly_cross_domain_links: a.dual_drive_analysis.cross_domain_links.length
}));
