---
name: diagnostic-html-visualizer
description: "Generate a human-friendly HTML explanation page from a diagnostic run folder. Use whenever the user asks to visualize diagnosis results, create an HTML report/page/dashboard/front-end explainer, render diagnostic conclusions with ECharts or Three.js, or turn a run directory into a page that operators, managers, and engineers can understand at a glance. Strongly prefer this skill after industrial-deep-diagnostic finishes, especially when a folder contains report.md, ontology.json, diagnosis.json, evidence.json, reasoning_chain.json, plot_manifest.json, or 3d_model_data.json. Triggers on: 诊断结果可视化, 生成HTML报告, 前端讲解页面, 可视化证据链, 诊断网页, dashboard, html explain page, render diagnosis to html, visualize run folder. Do NOT use for doing the diagnosis itself, generic marketing landing pages, or cases where no diagnostic artifacts are available."
---

# Diagnostic HTML Visualizer

数据驱动的诊断结果 HTML 可视化引擎。将已完成的诊断工作目录转成人类可读的前端讲解页面，遵循「结论先行 → 位置 → 推理 → 证据」四段叙事。基于 `render_manifest.json` 数据建模 + 设计系统视觉语法参考组装页面。页面生成后经 `html-reviewer` 独立审校通过方可交付。

默认输出语言为中文。页面文案、图表说明、证据链解释、行动建议用中文；结构化字段名、代码变量名、JSON enum 保持英文。

## Inputs / Outputs

### Inputs (in `RUN_DIR`)

| Priority | File | Purpose |
|----------|------|---------|
| P0 | `report.md` | 最终结论、行动建议、局限性 |
| P0 | `04_diagnostics/diagnosis.json` | 主结论、竞争假说、置信度、排除项 |
| P0 | `04_diagnostics/evidence.json` | 证据分层与支撑细节 |
| P0 | `04_diagnostics/reasoning_chain.json` | 结论收敛路径 |
| P1 | `01_ontology/ontology.json` | 产线对象、本体关系、工段结构 |
| P1 | `02_processed/data_analysis_conclusion.json` | 数据分析结论与解释桥接 |
| P1 | `02_processed/causal_evidence_map.json` | 因果链结构化输入 |
| P1 | `03_figures/plot_manifest.json` | 已有图表清单与标题 |
| P1 | `03_figures/*.png` / `*.jpg` | 现成视觉证据 |
| P1 | `03_figures/visual_analysis.json` | VLM 推断的图表观察 |
| P1 | `03_figures/image_captions.json` | 图表标题回退 |
| P1 | `3d_model_data.json` | 3D 场景实体、温区、异常点 |
| P2 | `viz_data.json` / `viz_compact.json` / `diagnostic_data.json` | 页面可复用数据摘要 |
| P2 | `02_processed/feature_summary.json` / `validate_report.json` | 补充统计与鲁棒性信息 |
| P2 | `.pipeline_events.jsonl` | 流程执行说明与时间线 |

### Outputs

| File | Description |
|------|-------------|
| `<run_dir>/diagnostic-report.html` | 单文件 HTML 可视化页面 |
| `<run_dir>/render_manifest.json` | 数据驱动页面模型（含 `_meta.protocol_ack`） |
| `<run_dir>/html_selfcheck.json` | 8 项自检 PASS/FAIL + evidence |

## Dispatch

启动 `html-visualizer` 子Agent 进行页面生成与审校：

```javascript
// OMP dispatch via task tool:
task({
  agent: "html-visualizer",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.omp/skills/diagnostic-html-visualizer>
SHARED_PATH=<path-to-.omp/shared>

Read the builder protocol at <SKILL_PATH>/agents/html-builder.md and execute the full pipeline.
Read the design system reference at <SKILL_PATH>/references/report-template.html for visual grammar.

Key constraints:
- 先产出 render_manifest.json（数据驱动建模），再按 manifest 组装页面
- Hero 首屏 8 元素缺一不可
- ECharts + Three.js 多源加载 (jsdelivr → unpkg) + 5 项 loader 状态条
- 证据链三层完整且各有真实图像/数据/物理推理支撑
- 页面生成后必须经 html-reviewer 审校通过方可交付（最多 3 次修订循环）
- 输出中文，enum 保持英文
`,
  effort: "hi"
})
```

## Execution Flow

Full protocol in `agents/html-builder.md`. Design system reference in `references/report-template.html`. Fallback templates in `templates/page_blueprint.md` and `templates/render_prompt_template.md`.

| Step | Purpose | Checkpoint |
|------|---------|------------|
| 1 | 读取 `agents/html-builder.md` 协议，确认四段式叙事架构 + 数据驱动渲染协议 + 8 条 fallback 逻辑 | `_meta.protocol_ack` (三项 boolean，全 true) |
| 2 | 加载 `references/report-template.html` 设计系统参考（视觉语法基准，非填空模板） | 文件可读；不可用则 Fallback 1 |
| 3 | 扫描 run_dir 全部 JSON，产出 `render_manifest.json`（数据驱动建模：结论类型、假说列表、证据层状态、图表清单、工艺流程） | manifest 全部字段来自真实 JSON，无编造 |
| 4 | 按 manifest 选组件组装页面，套设计系统视觉语法 — Hero (恒有) + 3D (工艺可恢复时) + 图表 (真实信号数) + 证据层 (按可用性) + 证据文章 (真实假说数) | 检查清单 7 项逐项确认 |
| 5 | 自检 8 项验证，产出 `html_selfcheck.json` | 8 项全部 PASS；>3 FAIL → 回 Step 4 |
| 6 | 提交 `html-reviewer` 独立审校 | `verdict: pass` 方可交付；fail → 修订 (最多 3 次) |

## Verification

```bash
SKILL_PATH="<path-to-.omp/skills/diagnostic-html-visualizer>"
SHARED_PATH="<path-to-.omp/shared>"

# Validate html_selfcheck.json against schema
node "$SHARED_PATH/scripts/validate.mjs" \
  "$SHARED_PATH/schemas/html_review_schema.json" \
  "$RUN_DIR/html_selfcheck.json"

# Validate render_manifest.json completeness
node -e "
const m = require('$RUN_DIR/render_manifest.json');
const checks = [
  m._meta?.protocol_ack?.narrative_arch,
  m._meta?.protocol_ack?.data_driven_protocol,
  m._meta?.protocol_ack?.fallback_logic,
  m.conclusion?.type,
  m.hypotheses?.length > 0,
  Object.values(m.evidence_layers || {}).length === 3,
];
console.log(checks.every(Boolean) ? 'PASS' : 'FAIL');
"
```

### Selfcheck Items (Step 5)

1. HTML 可正常打开
2. ECharts / Three.js / OrbitControls 主源 + 备用源 + 成功检测
3. 至少一个 ECharts 图表初始化成功 (`echarts.getInstanceByDom`)
4. 至少一个 Three.js 场景渲染成功 (canvas 元素存在)
5. 本地图片路径相对输出文件可访问
6. 证据链三层完整且各有真实图像/数据/物理推理支撑
7. 主结论、关键证据、排除逻辑、行动建议、局限性齐全
8. 用户能不依赖统计术语理解「为什么得出这个结论」

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| 设计系统参考不可用 | Fallback 1: 回退到 `templates/page_blueprint.md` + `templates/render_prompt_template.md` 从零构建 |
| P0 文件全部缺失 | Fallback 3: 报告缺失 → 终止并说明所需的最小文件集合 |
| 单文件缺失 (P1/P2) | 诚实降级：该证据层标 `.evidence-missing`，不假装存在 |
| CDN 脚本加载失败 | 多源回退 → 静态替代内容；页面仍保留摘要卡和本地图片 |
| html-reviewer fail | 回 Step 4 修订，最多 3 次循环；3 次后仍 fail → 终止并报告 blocker 列表 |
| render_manifest 与页面不对齐 | 回 Step 3 重新建模 |

## Visual Standards (Reference)

### 6 条铁律

1. **忠实于诊断产物** — 只使用 run_dir 真实 JSON，禁止编造
2. **双支撑 + 白话版** — 每条结论：可视化证据 + 推理证据 + 非术语白话解释
3. **数据驱动组装 + 视觉语法继承** — 先 manifest 建模，再按 manifest 选组件，套设计系统 CSS/组件类/loader
4. **3D 建模 = 真实简化** — 几何可简（盒体/圆柱），工艺不可错（工段顺序/温区分色/异常落位），设备形态从 ontology 的 `role`/`type` 推断
5. **用户三层时间门槛** — 5-15s: 结论/位置/下一步 (Hero) | 1-2min: 为什么/最强证据 (Section 02) | 下钻: 图/假说/局限 (Section 03)
6. **运行时加载检测** — ECharts + Three.js 多源加载 + 5 项状态 + 失败降级，不因 CDN 不可用白屏

### Hero 8 元素

1. `.hero-bar` — 36px×3px 墨色细线
2. `.display` — 衬线体大标题，`<em>` 强调关键词
3. `.hero-lede` — 3-4 句白话解释，≤640px 宽
4. `.hero-meta` — 诊断类型 / Judge评分 / 置信度 / 焦点产品 / 样本量 / 异常工段（最少 5 项）
5. `.key-findings` — 4 格关键发现网格：最强证据 / 已排除 / 推荐动作 / 证据缺口
6. 每格包含 `.kl` (标签) + `.kv` (值) + 可选 `.kd` (补充说明)
7. 阅读指引 caption — 一句话说明浏览顺序
8. 4 格内容必须有具体值，不允许空字符串或占位符
