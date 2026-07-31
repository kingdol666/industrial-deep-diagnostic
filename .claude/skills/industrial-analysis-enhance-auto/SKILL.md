---
name: industrial-analysis-enhance-auto
description: >
  Industrial Analysis Enhancement Auto — 全自动增强诊断管线编排。
  Trigger: enhance auto, 增强自动, 增强编排, enhancement orchestration, E1-E8 pipeline,
  全自动增强, auto enhance, enhance pipeline.
  Orchestrates E0 readiness check through E8 finalization: launches E1-E4 deep analysis scripts,
  E5 physics bridge, E6 knowledge fusion, E7a markdown publishing, E7b HTML visualization, E7c HTML review.
  Reads existing diagnostic RUN_DIR; writes only to RUN_DIR/enhancement/.
  CLI entry point for the full enhancement pipeline.
---

# Industrial Analysis Enhancement Auto

工业诊断全自动增强管线。从现有诊断 `RUN_DIR` 出发，依次执行：

| 阶段 | 脚本 | 功能 |
|------|------|------|
| E0 | `enhance_orchestrator.mjs` | 基线就绪检查、sha256 校验、清单生成 |
| E1 | `coverage_builder.py` (deep-analysis) | 全列覆盖分析 → `analysis_coverage.json` |
| E2 | `derived_feature_builder.py` (deep-analysis) | 物理衍生特征构建 → `derived_features.json` |
| E3 | `conditional_analysis.py` (deep-analysis) | 条件关系分析 + 可操作性 → `deep_data_analysis.json` |
| E5 | `physics_bridge_builder.py` (physics-bridge) | 物理机理桥接 → `physics_bridge.json` |
| E6 | `knowledge_fusion.py` | 知识融合 → `enhanced_knowledge.json` |
| E7a | `markdown_publisher.py` | Markdown 发布 → `enhanced_analysis.md` |
| E7b | `html_builder.py` (enhanced-html-visualizer) | ECharts HTML 可视化 → `enhanced-analysis.html` |
| E7c | `html_reviewer.py` (enhanced-html-reviewer) | HTML 审校 → `enhancement_html_review.json` |
| E8 | `enhance_orchestrator.mjs` (finalize) | 状态写入、摘要输出 |

## Inputs (read-only)

所有输入从 `RUN_DIR` 读取，不修改：

- `01_ontology/ontology.json`
- `02_processed/cleaned_data.csv`
- `02_processed/feature_summary.json`
- `02_processed/analysis_parameter_selection.json`
- `02_processed/validate_report.json`
- `02_processed/data_analysis_conclusion.json`
- `02_processed/production_regime_filter.json` (可选)
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `03_figures/plot_manifest.json`
- `03_figures/visual_analysis.json`

## Outputs (write only)

所有输出写入 `RUN_DIR/enhancement/`：

| 文件 | 阶段 | 说明 |
|------|------|------|
| `enhancement_manifest.json` | E0 | 运行时清单 |
| `analysis_coverage.json` | E1 | 列覆盖分析 |
| `derived_features.json` | E2 | 衍生特征 |
| `deep_data_analysis.json` | E3 | 深层数据分析 |
| `physics_bridge.json` | E5 | 物理桥接 |
| `enhanced_knowledge.json` | E6 | 增强知识整合 |
| `enhanced_analysis.md` | E7a | Markdown 报告 |
| `enhanced-analysis.html` | E7b | ECharts 可视化页面 |
| `html_selfcheck.json` | E7b | 页面运行时自检 |
| `enhancement_html_review.json` | E7c | HTML 审校结果 |
| `enhancement_status.json` | E8 | 最终状态 |

## Usage

### 双入口（Two Entry Points）

| 入口 | 调用方式 | 行为 |
|------|---------|------|
| **A: 新数据全流程** | 向 `enhance-orchestrator` Agent 传 `DATA_PATH=<data>` | Agent 先按 `skill://industrial-analysis-auto` 完整执行 Step 0-9（setup→inspect→ontology→data-processor→diagnostician→judge→audit→reporter→HTML），再执行 E0-E8 增强 |
| **B: 已有 RUN_DIR 仅增强** | `--run-dir <RUN_DIR>` | 跳过基线，直接 E0-E8（E0 校验基线产物，缺失则 BLOCKED） |

**入口 A 的基线调度由 enhance-orchestrator Agent 负责**（CLI 是纯增强执行器，不内嵌 LLM 基线步骤）。Agent 收到 `DATA_PATH` 时：
1. 用 `industrial-analysis-auto` 的 `setup.mjs`/`inspect.mjs` 建 RUN_DIR
2. 按 auto SKILL 顺序派发 context-builder → data-processor → diagnostician → judge/pre-audit → reporter → final audit → html-visualizer → html-reviewer
3. 基线完成（optimizer.md 含 ENDORSED）后再执行本 Skill 的 E0-E8

### 入口 B: 增强管线（已有基线）

```bash
node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs \
  --run-dir workspace/diagnostic-runs/<RUN_DIR>
```

Prints status JSON to stdout. Exit code 0 on success, 1 if BLOCKED or FAILED.

### 入口 B 带数据路径提示（可选）

```bash
node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs \
  --run-dir workspace/diagnostic-runs/<RUN_DIR> --data-path data/<file>.csv
```

`--data-path` 仅用于在清单中记录数据源；基线缺失时输出指引而非静默继续。

## Enhancement Status Logic

| 条件 | 状态 |
|------|------|
| 所有关系均可操作，无>30%混杂 | `READY` |
| >30% 关系为 CONFOUNDED 或 NOT_IDENTIFIABLE | `READY_WITH_WARNINGS` |
| P0 基线文件缺失 | `BLOCKED` |
| 任何增强脚本返回非零退出码 | `FAILED` |

## Operability Enum Values

与 `deep_data_analysis_schema.json` 一致：

1. `LEVER_IDENTIFIED` — 已确认可操作杠杆
2. `LEVER_OBSERVATIONAL` — 观察性关联（暂非杠杆）
3. `ENDOGENOUS_RESPONSE` — 内生响应（方向与物理矛盾）
4. `CONFOUNDED` — 混杂（Simpson/群组逆转或时间混淆）
5. `NOT_IDENTIFIABLE` — 不可识别
6. `CONSTRAINT_UNCONTROLLABLE` — 不可控约束条件

## Markdown Contract

- 9 节 (`## 1.` 到 `## 9.`) 中文报告
- 每条核心关系结论嵌入 ```json 块（claim_id, status, source, mask, n, method, effect, causal_ceiling, not_for）
- 零硬编码数字 —— 全部从 `enhanced_knowledge.json` 模板替换
- 每个数值带单位
- JSON enum 英文，正文中文
- 不使用 `dY_dX_linear`、`partial_r` 等原始 JSON 字段名

## Verification

```bash
# Full pipeline on any RUN_DIR (example: CSTR catalyst run)
node .claude/skills/industrial-analysis-enhance-auto/scripts/enhance_orchestrator.mjs \
  --run-dir <RUN_DIR>

# Validate enhanced_knowledge.json
node .claude/shared/scripts/validate.mjs \
  .claude/shared/schemas/enhanced_knowledge_schema.json \
  <RUN_DIR>/enhancement/enhanced_knowledge.json

# Reproduce markdown standalone
python .claude/skills/industrial-analysis-enhance-auto/scripts/markdown_publisher.py \
  --knowledge <RUN_DIR>/enhancement/enhanced_knowledge.json \
  --template .claude/skills/industrial-analysis-enhance-auto/templates/enhanced_analysis.md.tmpl \
  --output <RUN_DIR>/enhancement/enhanced_analysis_v2.md

# Check for hardcoded numbers, raw field names, section count
python -c "
import json, re
# Section count
with open('<RUN_DIR>/enhancement/enhanced_analysis.md') as f:
    md = f.read()
sections = re.findall(r'^## \d+\.', md, re.MULTILINE)
print(f'## sections: {len(sections)}')
# Embedded JSON blocks
json_blocks = re.findall(r'\x60\x60\x60json\n(.*?)\n\x60\x60\x60', md, re.DOTALL)
print(f'JSON claim blocks: {len(json_blocks)}')
# No raw field names
bad = ['dY_dX_linear', 'partial_r', 'detrended_r']
for b in bad:
    if b in md:
        print(f'WARN: raw field name {b!r} found')
    else:
        print(f'OK: no {b!r}')
# No hardcoded numbers (check in non-code non-table context)
# Status check
print('Status:', 'READY_WITH_WARNINGS' in md)
"
```

## References

- `references/orchestration-protocol.md` — E0-E8 阶段协议详细说明
