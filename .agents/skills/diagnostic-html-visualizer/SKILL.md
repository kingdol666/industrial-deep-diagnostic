---
name: diagnostic-html-visualizer
description: "Generate a human-friendly HTML explanation page from a diagnostic run folder. Use whenever the user asks to visualize diagnosis results, create an HTML report/page/dashboard/front-end explainer, render diagnostic conclusions with ECharts or Three.js, or turn a run directory into a page that operators, managers, and engineers can understand at a glance. Strongly prefer this skill after industrial-deep-diagnostic finishes, especially when a folder contains report.md, ontology.json, diagnosis.json, evidence.json, reasoning_chain.json, plot_manifest.json, or 3d_model_data.json. Triggers on: 诊断结果可视化, 生成HTML报告, 前端讲解页面, 可视化证据链, 诊断网页, dashboard, html explain page, render diagnosis to html, visualize run folder. Do NOT use for doing the diagnosis itself, generic marketing landing pages, or cases where no diagnostic artifacts are available."
commands:
  - diagnostic-html-visualizer
  - diagnostic-html-visualizer build
  - diagnostic-html-visualizer refresh
compatibility: |
  Works with plain HTML/CSS/JS and does not require a bundler.
  Prefer single-file HTML output with inline CSS/JS plus relative links to local PNG/JPG assets in the run directory.
  Remote CDN loading is allowed for ECharts and Three.js, but the page must implement multi-source loading, runtime readiness checks, and explicit fallback behavior if scripts fail to load.
  Can be called standalone by the user or as a post-diagnosis consumer skill from industrial-deep-diagnostic.
---

# Diagnostic HTML Visualizer

## Language Default

默认输出语言为中文。页面文案、图表说明、证据链解释、行动建议都使用中文。结构化字段名、代码变量名、JSON enum 保持英文。

## Core Mission

把一个**已经完成的诊断工作目录**转成一个**能让人一眼读懂的 HTML 可视化讲解页面**。

这个 skill 的重点不是“把 JSON 摆上去”，而是把诊断结果转译成符合人类理解顺序的前端讲解：

1. 先讲背景和产线对象
2. 再讲这次诊断是怎么收敛出结论的
3. 再讲关键数据图看到了什么
4. 最后讲证据链和为什么相信这个结论

如果目录中已有图像、图表、3D 数据、可视化摘要，就优先复用；如果没有，就根据真实诊断 JSON 和 CSV 重新组织出最关键的 ECharts 图，并在必要时用 Three.js 画简化 3D 产线模型。

## Truth Rules

### 铁律 1: 页面必须忠实于诊断产物

- 只使用 run directory 中真实存在的诊断结论、证据、图像、统计结果和本体信息
- 不允许凭空补造“更好看”的结论
- 如果某个证据缺失，要明确标出“当前缺少该层证据”，而不是假装存在

### 铁律 2: 每条主结论都要有双支撑

每条主结论都要同时给出：

1. **可视化证据**：图表、时间对齐图、剖面图、3D 异常定位、流程图中的至少一种
2. **推理证据**：统计结论、物理机制、排除逻辑、竞争假说比较中的至少一种

### 铁律 3: 页面是“讲解”，不是“堆料”

- 每个图必须回答三件事：图上看到什么、这说明什么、为什么重要
- 页面必须符合四步讲解结构，不能变成无组织的 dashboard
- 读者默认是工业用户，不假设其熟悉统计术语
- 页面必须优先降低理解门槛，而不是优先展示技术复杂度

### 铁律 4: 3D 与图表组件的加载成功是交付门槛

- 页面**不能**只写上 ECharts / Three.js 的 CDN script 标签就算完成
- 必须实现多源加载、加载成功检测、初始化成功检测、失败提示与静态降级
- 只有在以下条件满足时，页面才算交付完成：
  1. `window.echarts` 可用且至少一个核心图表成功 `setOption`
  2. `window.THREE` 可用且 3D 场景成功创建
  3. 若使用 OrbitControls，则对应控制器也成功加载
- 如果远程脚本全部失败，就必须保留本地图片、摘要卡、静态证据链和降级提示，且明确标注“当前浏览环境未成功加载交互式图表/3D模块”

### 铁律 5: 3D 建模必须服从真实诊断场景与产线逻辑

- 3D 不是装饰，而是“把诊断发生位置和工艺路径讲清楚”的证据界面
- 必须先从 `ontology.json`、`report.md`、`diagnosis.json`、`3d_model_data.json` 中恢复真实场景，再进行简化建模
- 工段顺序、设备角色、辊位编号、物料流向、冷热区分、异常位置，必须与当前诊断场景一致
- 不允许画与当前场景无关的通用工厂、抽象流水线、错误数量的辊子、错误顺序的工段
- 可以做“简化建模”，但不能做“脱离工艺逻辑的随意建模”

### 铁律 6: 页面必须让用户在有限时间内真的看懂

把“用户看懂”视为交付标准，而不是主观愿望。页面至少要满足：

1. 用户在 5-15 秒内能看懂：
   - 结论是什么
   - 问题大致发生在哪个工段
   - 下一步最该做什么
2. 用户在 1-2 分钟内能看懂：
   - 为什么不是另一个看起来也相关的原因
   - 这次结论最强的证据是什么
   - 结论是怎么一步步收敛出来的
3. 用户在需要时能继续下钻：
   - 查看详细图表
   - 查看假说比较
   - 查看证据链与局限性

如果页面让用户必须先读大量术语、先看很多图、先懂统计，才明白主结论，那么页面不合格。

## Input Contract

### Required

- `run_dir`: 指向某次诊断结果目录的绝对路径

### Optional

- `output_html`: 输出 HTML 路径，默认 `<run_dir>/diagnostic-report.html`
- `audience`: `operator` / `engineer` / `manager` / `mixed`，默认 `mixed`
- `visual_mode`: `executive` / `engineering` / `story`，默认 `story`
- `force_single_file`: `true` / `false`，默认 `true`

### Expected Artifacts

优先读取以下文件；存在就使用，不存在就降级：

| Priority | File | Purpose |
|----------|------|---------|
| P0 | `report.md` | 最终结论、行动建议、局限性 |
| P0 | `04_diagnostics/diagnosis.json` | 主结论、竞争假说、置信度、排除项 |
| P0 | `04_diagnostics/evidence.json` | 证据分层与支撑细节 |
| P0 | `04_diagnostics/reasoning_chain.json` | 结论是如何一步步收敛出来的 |
| P1 | `01_ontology/ontology.json` | 产线对象、本体关系、工段结构 |
| P1 | `02_processed/data_analysis_conclusion.json` | 数据分析结论与解释桥接 |
| P1 | `02_processed/causal_evidence_map.json` | 因果链结构化输入 |
| P1 | `03_figures/plot_manifest.json` | 已有图表清单与标题 |
| P1 | `03_figures/*.png` / `*.jpg` | 现成视觉证据 |
| P1 | `3d_model_data.json` | 3D 场景实体、温区、辊位、异常点 |
| P2 | `viz_data.json` / `viz_compact.json` / `diagnostic_data.json` | 页面可直接复用的数据摘要 |
| P2 | `02_processed/feature_summary.json` / `validate_report.json` / `anomaly_report.json` | 补充统计与鲁棒性信息 |
| P2 | `.pipeline_events.jsonl` | 可选的流程执行说明与时间线 |

## Output Contract

默认输出：

- `<run_dir>/diagnostic-report.html`

页面必须满足：

1. 单文件 HTML 可直接打开
2. 四大讲解部分齐全
3. 至少一个 ECharts 图表模块
4. 若能获得工段结构，则至少一个 Three.js 简化 3D 模块
5. ECharts 与 Three.js 必须通过多源 loader 尝试加载，并在页面内输出加载状态
6. 若远程脚本加载失败，页面仍保留静态文本、摘要卡和本地图片证据
7. 除非用户明确允许，否则不得把“组件未加载成功”的页面视为完成品
8. 页面必须包含一个“结论先行”的首屏摘要，以及一个“我是如何得到这个结论的”简明路径
9. 页面必须控制信息密度，优先突出 3-5 个最关键证据，不得把所有图一股脑平铺为主内容
10. 页面生成后必须经过 `html-reviewer` 质检子 Agent 审核，不通过则返回修订

## Invocation Protocol

### Standalone

当用户明确提供某个诊断目录并要求做前端可视化时，直接调用本 skill。

示例：

```text
/diagnostic-html-visualizer build run_dir="/abs/path/to/workspace/diagnostic-runs/202606151602359_bopet_scratch_lekai"
```

### Consumer-Call from industrial-deep-diagnostic

当主诊断 skill 已经完成，且用户要求“生成 HTML 可视化讲解页面 / 前端报告 / dashboard / 可视化证据链”时：

1. 主 agent 不要自己即兴拼页面
2. 直接调用本 skill
3. 由本 skill 启动自己的子 agent 生成页面

推荐调用形式：

```text
Skill({
  skill: "diagnostic-html-visualizer",
  args: "build run_dir='<current_run_dir>' output_html='<current_run_dir>/diagnostic-report.html' audience='mixed' visual_mode='story'"
})
```

## Execution Flow

### Step 1: Read the builder protocol

先读 `agents/html-builder.md`，把它当作执行协议。

### Step 2: Build the artifact inventory

快速识别：

- 这次 run 的主题、产线、目标缺陷、焦点产品
- 哪些 JSON 可以直接抽取结论
- 哪些本地图像可直接上屏
- 哪些图必须用 ECharts 重绘
- 是否存在 `3d_model_data.json` 可直接用于 3D 建模
- 当前真实工艺路径是什么，工段先后顺序是什么，异常点落在哪个设备/辊位/区域

### Step 3: Load the page blueprint

再读：

- `templates/page_blueprint.md`
- `templates/render_prompt_template.md`

前者约束页面结构，后者给出一套高质量通用提示模板，便于子 agent 快速进入状态。

### Step 4: Generate the HTML

优先生成一个故事化页面，按以下四段组织：

1. 背景与动态建模 / 本体模型可视化
2. 诊断流程简要说明
3. 数据图表与可视化解释
4. 证据链、因果溯源、结论支撑

同时强制加入两层阅读路径：

- **快速路径**：用户只看首屏和每段开头，就能知道结论、位置、原因、动作
- **深度路径**：用户继续往下看，能明白统计验证、物理机制、竞争假说和局限性

### Step 5: Validate the page

至少检查：

- HTML 是否可打开
- ECharts / Three.js / OrbitControls 是否有主源 + 备用源 + 成功检测
- 至少一个图表是否真正初始化成功，而不只是 script 已注入
- 至少一个 Three.js 场景是否真正渲染成功，而不只是 `window.THREE` 存在
- 本地图片路径是否相对输出文件可访问
- 主结论、关键证据、行动建议、局限性是否齐全
- 每个主结论是否都能被一句人话解释清楚
- 用户是否能不依赖统计术语理解“为什么得出这个结论”

如果环境允许预览页面，必须实际打开页面验证加载状态；不要只靠静态阅读 HTML 源码判断成功。

## Visual Standards

### 必备信息层

页面首屏必须直接给出：

- 主结论一句话
- 诊断类型
- 置信度或置信度上限
- Judge 评分
- 焦点产品 / 样本量 / 异常工段
- 1 组“最强证据 / 已排除因素 / 下一步动作”摘要卡
- 一段“这页怎么读”的超短引导

### 四段式结构不可省略

#### 1. 背景与动态建模

- 用 ontology 讲清设备、工段、参数、目标缺陷
- 用简化的 2D/3D 结构让用户知道“问题在产线哪里”
- 异常位置必须被显著标识
- 3D 模型必须体现当前诊断场景的真实工艺顺序和设备逻辑，而不是抽象装饰模型

#### 2. 诊断流程说明

- 讲清为什么不是直接看全局相关
- 讲清去趋势、分层分析、竞争假说、证据筛选的作用
- 用流程带、步骤卡、漏斗图或收敛图表达
- 每个术语都要紧跟一句白话解释，例如“去趋势：把随时间一起变化但未必有因果的假相关先扣掉”

#### 3. 数据图表解释

- 重点讲时序对齐、全局 vs 产品内、鲁棒性、温区/扭矩剖面
- 每张图都要附通俗解释
- 主内容区优先只保留最关键的 3-5 张图，其余图可折叠、次级展示或合并到附加证据区

#### 4. 证据链与因果溯源

- 把结论拆成“结论卡 + 可视化证据 + 推理证据”
- 排除项也要解释为什么被排除
- 必须明确展示“观测到什么 -> 怎么验证 -> 为什么排除别的解释 -> 为什么留下这个结论”

### 技术实现建议

- 图表优先用 ECharts
- 3D 产线优先用 Three.js + OrbitControls
- 页面优先单文件 HTML，数据尽量内嵌
- 脚本加载要有主 CDN + 备用 CDN + 运行时状态面板 + 降级文案

### 3D Scene Fidelity Rules

构建 3D 时，优先顺序如下：

1. 若存在 `3d_model_data.json`，优先把它视为场景骨架
2. 再用 `ontology.json` 校验工段名称、设备顺序、物料流向
3. 用 `report.md` / `diagnosis.json` / `evidence.json` 标记异常工段、异常辊位、重点证据位置

最低要求：

- 工段顺序正确
- 每个工段的物理角色正确
- 异常点落位正确
- 物料流向正确
- 温区或功能区差异有视觉区分

简化允许：

- 不追求 CAD 精度
- 用基础几何体替代真实设备外形

但以下情况不允许：

- 工段顺序颠倒
- 急冷段、拉伸段、预热段混画
- 异常点高亮在错误设备上
- 用完全通用的工厂装饰替代当前场景

### Explainability Design Rules

为了让用户简单明了看懂，请强制遵守：

1. **结论先行**
   - 第一屏先告诉用户“结论是什么”，再展开过程
2. **一屏一任务**
   - 每个主要区块只回答一个核心问题，避免一个区块同时解释太多内容
3. **术语落地**
   - 每个统计或方法术语后面都跟一条白话解释
4. **图文绑定**
   - 图旁边必须直接解释图，不允许“图在上、解释在很远的下方”
5. **证据分层**
   - 主证据在前，次证据和扩展证据后置
6. **排除逻辑显性化**
   - 不仅说“最可能是什么”，还要说“为什么不是另外几个候选”
7. **动作闭环**
   - 页面最后必须让用户知道下一步怎么验证、怎么处理、怎么继续收集证据

### Comprehension Acceptance Test

生成页面后，自检是否能让一个非算法背景用户回答下面 6 个问题：

1. 这次最终结论是什么？
2. 问题发生在产线的哪个位置？
3. 最强的证据是什么？
4. 为什么不是另一个看起来也相关的原因？
5. 这个结论是怎么一步步得出来的？
6. 下一步最应该做什么？

只要有 2 个以上问题在页面里不容易被快速回答，页面就不合格，需要重做信息结构。

### Recommended Library Loading Strategy

对每个库都使用“主源 → 备用源 → 失败上报”的顺序。

推荐顺序：

- ECharts
  - `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
  - `https://unpkg.com/echarts@5/dist/echarts.min.js`
- Three.js
  - `https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js`
  - `https://unpkg.com/three@0.160.0/build/three.min.js`
- OrbitControls
  - `https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js`
  - `https://unpkg.com/three@0.160.0/examples/js/controls/OrbitControls.js`

页面中必须内置一个 loader 状态区，显示：

- `ECharts: loaded / fallback / failed`
- `Three.js: loaded / fallback / failed`
- `OrbitControls: loaded / optional-missing / failed`
- `Charts initialized: yes / no`
- `3D scene initialized: yes / no`

## Fallback Rules

### If images exist but chart libs fail

保留：

- 摘要卡
- 文字讲解
- 本地 PNG/JPG 图像
- 静态证据链模块

### If 3D data is missing

根据 `ontology.json` 中的工段和设备信息，用简单几何体画概念 3D 模型：

- 工段用长方体或分区平台
- 辊位用圆柱体
- 异常点用红橙色发光材质或警示标记

### If figures are missing

优先根据这些文件重绘：

- `diagnosis.json`
- `evidence.json`
- `reasoning_chain.json`
- `feature_summary.json`
- `validate_report.json`
- `viz_data.json`
- `viz_compact.json`

## Style Direction

默认采用“工业科技叙事风格”：

- 综合色彩：蓝灰、冷白、橙红告警、冷暖渐变温区
- 版式：大结论先行，向下逐步解释
- 背景：轻网格、流程线、分区氛围，不喧宾夺主
- 气质：可信、稳重、清晰，不做炫技式大屏

## Deliverable Closeout

完成后必须告诉调用者：

1. 读取了哪些关键文件
2. HTML 输出到了哪里
3. 哪些内容是直接复用已有图像，哪些是重新生成图表
4. 如果还要继续优化，最值得增强的是哪一层证据或哪一种交互

在交付前还要确认：

- `html-reviewer` 是否通过
- 若未通过，是否已经把 blockers 反馈给 `html-visualizer` 修订
