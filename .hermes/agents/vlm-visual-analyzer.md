# Agent: VLM Visual Analyzer (Phase 5.5, internal)

## Model Configuration
**此 Agent 使用专属模型配置，定义在 `agents.yaml`。**

```
model:
  provider: deepseek
  model: deepseek-v4-pro       # DeepSeek V4 Pro 支持视觉
  max_iterations: 40
  reasoning_effort: medium
```

**视觉模型回退方案** (如果 DeepSeek V4 视觉不可用):
- OpenRouter: `google/gemini-2.5-flash` — Gemini 2.5 Flash (原生视觉, 免费)
- OpenRouter: `anthropic/claude-sonnet-4` — Claude Sonnet 4 (原生视觉)
- OpenRouter: `openai/gpt-4o` — GPT-4o (原生视觉)

切换方式: 修改 `agents.yaml` 中 vlm-visual-analyzer 的 model 字段，或使用 `terminal_spawn` 模式启动独立进程:
```bash
hermes chat -m openrouter/google/gemini-2.5-flash -q "执行VLM视觉分析..."
```

## Role
工业诊断流程 Phase 5.5 — VLM 视觉图像分析。读取 data-processor 生成的 PNG 图表，结合本体模型和结构化知识，输出 visual_analysis.json 和 image_captions.json。

这是 data-processor 的子代理，由 data-processor 内部启动，不是独立管线步骤。

## Hermes 启动方式

### 方式A: delegate_task (继承主模型)
当主模型支持视觉时使用:

```
delegate_task(
    goal="执行工业诊断图表VLM视觉分析。以本体感知方式读取PNG图表：先读ontology.json理解参数物理含义，再带有知识地看PNG图，提取结构化视觉证据。输出visual_analysis.json（12个required字段）和image_captions.json（PNG不可用时的回退）。",
    toolsets=["terminal", "file", "vision"],
    context="SKILL_PATH={SKILL_PATH}\nRUN_DIR={RUN_DIR}\n\n执行 vlm-visual-analyzer 完整协议"
)
```

### 方式B: terminal_spawn (独立模型)
当需要为视觉任务使用专属模型时:

```bash
hermes chat -m deepseek-v4-pro --yolo -q "
加载 SKILL_PATH/agents/vlm-visual-analyzer.md 协议。
RUN_DIR={RUN_DIR}
SKILL_PATH={SKILL_PATH}

执行VLM视觉分析完整流程:
1. 读 ontology.json — 理解每个参数列的物理含义
2. 读 scenario_classification.json — 场景分类和预期物理行为
3. 读 plot_manifest.json — 图像清单和优先级顺序
4. 读 feature_summary.json — 关键统计相关性
5. 按优先级逐图读取PNG（用vision工具）
6. 输出 visual_analysis.json（按schema的12个required字段）
7. 输出 image_captions.json（回退方案）
8. 运行 validate.mjs 验证两个输出

Schema-First规则：写前必读 visual_analysis_schema.json 和 image_captions_schema.json
完整协议文档见: SKILL_PATH/agents/vlm-visual-analyzer.md
" --workdir /Volumes/laxer/codes/skills/industrial-deep-diagnostic
```

## Tools Needed
- terminal (bash, validate.mjs)
- file (read images, write JSON)
- vision (image analysis, read PNG charts) — **核心工具，需要模型支持视觉**

## Core Rules
- 先理解上下文，再读图 — 不知道本体模型的参数含义就去看图 = 盲人摸象
- 必须读 ontology.json — 这是理解图中参数物理含义的唯一方式
- 不是做统计计算 — 价值是"看见了什么"，不是"r=0.8"
- 时间对齐不适用时必须明确声明
- 产品分组存在时必须区分组内/组间
- 输出 visual_analysis.json 必须可供 diagnostician 直接引用
- 默认中文
