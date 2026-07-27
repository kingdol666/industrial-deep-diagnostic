---
name: industrial-vlm-analyzer
description: "工业诊断管线 — VLM 视觉图像分析，读取图表 PNG 覆盖 visual_analysis.json skeleton。含自检、降级路径、防伪造验证。Trigger: VLM, 视觉分析, 图像分析, 图表解读, visual analysis, chart reading, image analysis, vlm visual analyzer. Do NOT use for general image captioning or OCR."
---

# Industrial VLM Analyzer

读取数据处理阶段生成的图表 PNG，用视觉语言模型（VLM）提取图表中的视觉证据，回写到 `visual_analysis.json`。含自检协议确保 VLM 输出可信，并支持降级到纯元数据推断。

## Inputs (expected in `RUN_DIR`)

| File | Description |
|------|-------------|
| `03_figures/visual_analysis.json` | data-processor 写入的 pre-VLM skeleton |
| `03_figures/plot_manifest.json` | 图表清单 + 元数据 |
| `03_figures/*.png` | 待分析的图表 |
| `01_ontology/ontology.json` | 领域本体（提供参数语义上下文） |

## Outputs

| File | Description |
|------|-------------|
| `03_figures/visual_analysis.json` | skeleton 被覆盖，`skeleton_overwritten=true` |

## Execution

启动 `vlm-visual-analyzer` 子Agent：

```javascript
Agent({
  subagent_type: "vlm-visual-analyzer",
  description: "VLM 图表视觉证据提取",
  permissionMode: "bypassPermissions",
  prompt: `RUN_DIR=<run-dir-path>
SKILL_PATH=<this-skill-directory>

Read "<this-skill-directory>/references/agent-protocol.md" and execute the complete protocol.

For each chart in plot_manifest.json:
1. Load the PNG image
2. Extract visual evidence (trends, anomalies, patterns, outliers)
3. Cross-reference with ontology for semantic interpretation
4. Run self-check protocol before writing

If VLM is unavailable or unreliable:
- Fall back to metadata-backed inference (using plot_manifest.json + image_captions.json)
- Mark degraded mode in visual_analysis.json`,
  run_in_background: true
})
```

### VLM Self-Check Protocol

每个 VLM 观察必须通过三项自检：
1. **一致性检查**: VLM 描述与 plot_manifest 元数据（轴标签、数据范围）是否一致？
2. **数值验证**: VLM 报告的数值是否在图表显示范围内？
3. **防伪造**: 是否存在 VLM "幻觉"（描述不存在的数据特征）？→ 标记 `[VLM_HALLUCINATION]`

### Degradation Paths

| 触发条件 | 降级策略 |
|----------|----------|
| VLM 不可用 | 从 `image_captions.json` + `plot_manifest.json` 推断 → L4 文本回退 |
| VLM 自检失败 >50% | 自动降级到 metadata-only 模式 |
| 单张图 VLM 失败 | 该图标记 `vlm_status: "failed"`，其余正常处理 |

## Verification

```bash
SKILL_PATH="<this-skill-directory>"

# Schema validation
node "$SKILL_PATH/scripts/validate.mjs" \
  "$SKILL_PATH/schemas/visual_analysis_schema.json" \
  "$RUN_DIR/03_figures/visual_analysis.json"

# VLM verification
node "$SKILL_PATH/scripts/vlm-verification-check.mjs" "$RUN_DIR"
```

## References

- `references/agent-protocol.md` — 完整的 VLM 分析执行协议
- `schemas/visual_analysis_schema.json` — visual_analysis.json Schema
- `scripts/visual_analysis.py` — VLM 视觉分析 Python 脚本
- `scripts/vlm-verification-check.mjs` — VLM 防伪造验证
