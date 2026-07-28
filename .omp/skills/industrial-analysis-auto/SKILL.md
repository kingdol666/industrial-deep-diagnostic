---
name: industrial-analysis-auto
description: "工业深度诊断全自动编排器。Trigger: 工业诊断, 根因分析, 故障诊断, 生产过程异常, 质量缺陷分析, 传感器数据分析, 工艺参数优化, SPC excursion, root cause analysis, manufacturing diagnostics, 上传CSV/XLSX/Parquet数据后全自动执行8步诊断管线。零人工干预模式 (auto), 半自动确认模式 (interactive), 最小模式 (minimal)。输出: report.md + diagnostic-report.html"
---

# Industrial Analysis Auto — Full Pipeline Orchestrator

8步全自动工业诊断管线。输入传感器/工艺数据 → 输出中文诊断报告 + HTML可视化页。

## Pipeline Flow

```
Step 0-1: Setup + Inspect (main agent)  ── 创建运行目录、检查数据
Step 2+2.5: [ontology-builder] → CP-2, CP-3  ── 构建领域本体
Step 3+3.3: [data-processor] → CP-4  ── 统计验证 + VLM视觉分析
Step 4: [diagnostician] → CP-5  ── 竞争假说根因诊断
Step 5a: [judge] + 5b: [physical-auditor](并行) → CP-6  ── 质量门+预审计
  ↻ best-of-3 repair cycle
Step 6: [reporter] → CP-7  ── 生成report.md
Step 7: [physical-auditor](终审) → CP-8 ENDORSED
Step 8: [html-visualizer] + 8.5: [html-reviewer] → CP-9  ── HTML可视化
Step 9: Finalize  ── evidence_closure_report.json
```

## Execution

主agent按顺序逐步骤执行，每步调用对应sub-skill：

```javascript
// Pattern: 读skill://protocol → 设置路径 → Agent({subagent_type, prompt, run_in_background: true})
// 子agent通过文件系统通信，不经过主agent context
```

| Step | Skill | Agent | 关键输入 | 关键输出 |
|:----:|-------|-------|---------|---------|
| 2 | `industrial-ontology-builder` | context-builder | input_manifest, user_context, data | `ontology.json`, `rag_deep_understanding.json` |
| 3 | `industrial-data-processor` | data-processor | ontology, data | `data_analysis_conclusion.json`, `03_figures/*` |
| 4 | `industrial-diagnostician` | diagnostician | data_analysis_conclusion, visual_analysis, ontology | 4× 诊断JSON |
| 5a | `industrial-judge` | judge | 4×诊断JSON + analysis artifacts | `judge_feedback.json` |
| 5b | `industrial-physical-auditor` | report-reviewer | 诊断JSON | `optimizer_preflight.md` |
| 6 | `industrial-reporter` | reporter | 诊断JSON + figures | `report.md`, `run_summary.json` |
| 7 | `industrial-physical-auditor` | report-reviewer | report.md | `optimizer.md` (ENDORSED) |
| 8 | `industrial-html-visualizer` | html-visualizer | optimizer + report | `diagnostic-report.html` |
| 8.5 | `industrial-html-reviewer` | html-reviewer | HTML + diagnosis | `html_review.json` |

详见各sub-skill的SKILL.md获取Agent dispatch协议。

## Checkpoint Gates

| CP | 位置 | 验证 | 失败→ |
|:--|------|------|-------|
| CP-1 | 1→2 | `input_manifest.json` + `user_context.json` | 重做Step 0 |
| CP-2 | 2→2.5 | `ontology.json` ≥1KB + schema-valid | 重跑ontology-builder |
| CP-3 | 2.5→3 | `clarification_status: AUTO_RESOLVED\|USER_CONFIRMED` | 解决 |
| CP-4 | 3→4 | `data_analysis_conclusion.json` + plots>0 | 重跑data-processor |
| CP-5 | 4→5 | 4 diagnosis JSON schema-valid + quality-check | repair (best-of-3) |
| CP-6 | 5→6 | `judge_repair_summary.json` + pre-audit no FATAL | repair |
| CP-7 | 6→7 | `report.md` + `run_summary.json` | 重跑reporter |
| CP-8 | 7→8 | `optimizer.md` 含 `ENDORSED` | repair loop |
| CP-9 | 8.5→9 | HTML≥5120B + review verdict=pass | 重跑html-visualizer |

## Repair Governance

- Judge best-of-3: 最多3轮修复, score≥90时提前终止
- Reviewer repair: 最多2轮完整D→J→R→R循环
- 全局重诊断上限: 5次 (tracked by `repair_spawn`)
- 防震荡: 第3次同issue震荡→`COMPETING_SET`, confidence≤50
- 永不halt: score不够仍继续生成report+HTML

## Setup & Finalize

```bash
# Step 0
SKILL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.claude/skills/industrial-analysis-auto" && pwd)"
SHARED_PATH="$(cd "$SKILL_PATH/../../.claude/shared" && pwd)"
node "$SKILL_PATH/scripts/setup.mjs" --name <scene> --base-dir "$PROJECT_ROOT/workspace/diagnostic-runs"
node "$SHARED_PATH/scripts/uv_env_setup.mjs"

# Step 1
node "$SKILL_PATH/scripts/inspect.mjs" <data_path>

# Step 9
node "$SKILL_PATH/scripts/pipeline-finalize.mjs" "$RUN_DIR"
```

每次step_start/step_complete必须 logging:
```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event step_start --agent <agent> --step <step>
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" --event step_complete --agent <agent> --step <step> --files <outputs>
# 子agent内部使用 log-agent-event.mjs 自动记录agent_start/agent_complete
```

## Failure Recovery

| 场景 | 恢复 |
|------|------|
| RAG引擎不可用 | 使用 `parameter_to_physics.json` + web search |
| uv创建venv失败 | 回退system Python + pip |
| Agent超时(>600s) | 检查部分产物→可用则继续；retry 1x"
| VLM不可用 | 降级为 metadata_backed_inference + L4_text_fallback; 不影响后续 |
| 图表生成失败 | 修复数据重画 → 仍失败则 `image_captions.json` L4文本回退 |
| HTML构建失败 | 重跑 → 2x失败则仅交付report.md + `HTML_DELIVERY_FAILED` |

## Red-Light Blacklist

| # | 禁止 | 替代 |
|---|------|------|
| 1 | 主agent直接写HTML | 通过html-visualizer子agent |
| 2 | 主agent读了协议自己执行 | 用 `Agent({subagent_type})` |
| 3 | 跳过数据分析直接诊断 | `ontology_first` 强制 |
| 4 | Judge未通过就启动Reporter | 只有repair是合法操作 |
| 5 | COMPETING_SET强选一个 | 诚实输出竞争假说表, confidence≤65 |
| 6 | 全局相关做因果证据 | per-product分层+去趋势+Simpson+留一法 |
| 7 | HTML只有CDN无降级 | 多源加载+运行时检测+降级内容 |
| 8 | 3D模型用通用工厂 | 从ontology恢复真实工段 |
| 9 | 结论无证据等级 | 每条 `[Evidence Rank L1-L7]` |
| 10 | 模糊用语搪塞 | 具体数字+置信度, 或明确说不充分 |

## VLM Auto-Degradation

| 条件 | 行为 |
|------|------|
| vision模型可用 | 运行 visual_analysis.py → VLM子agent读PNG → vlm-verification-check |
| vision模型不可用/超时 | metadata_backed_inference + L4_text_fallback, degradation_active=true |
| VLM_ENABLED=false | 从plot_manifest + image_captions生成metadata-only skeleton |
