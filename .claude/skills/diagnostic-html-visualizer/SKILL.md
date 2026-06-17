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

这个 skill 的重点不是”把 JSON 摆上去”，而是把诊断结果转译成符合人类理解顺序的前端讲解。页面设计哲学：

1. 先讲结论（Hero 首屏）：用户 10 秒内知道答案
2. 再讲位置（3D 产线模型）：用户 30 秒内知道问题在哪
3. 再讲过程（诊断推理）：用户 1 分钟内知道结论怎么来的
4. 最后讲证据（三层闭合链）：用户 2 分钟内建立信任——**统计证明相关性 + 物理证明因果性 + 排除逻辑证明唯一性**

如果目录中已有图像、图表、3D 数据、可视化摘要，就优先复用；如果没有，就根据真实诊断 JSON 重新组织出最关键的 ECharts 图，并在必要时用 Three.js 画简化 3D 产线模型。

**页面模板**: `references/report-template.html` 是 HTML 结构骨架和 CSS 样式基准。builder agent 必须以此模板为基础，替换占位数据为真实诊断数据。

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

### 铁律 4: 3D 与图表组件的加载成功是交付门槛（加强）

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

### 铁律 7: 证据链必须是三层闭合架构

证据链是用户信任建立的核心区块，不是平铺的卡片堆。必须严格按三层展开：

**第一层 · 统计证据（Ⅰ）** — 证明相关性
- 复用诊断管线生成的散点图、相关性图 PNG（来自 `03_figures/`）
- 至少 1 张 ECharts 重建的去趋势散点图（从 `viz_compact.json` 取真实数据）
- 关键统计值：Spearman ρ + p 值 + 去趋势衰减率
- 统计证据强度评分条

**第二层 · 物理机制（Ⅱ）** — 证明因果性
- HTML/CSS 物理因果链流程图（每节点有标题 + 物理细节 + 方程或量级估算）
- 复用温度分区剖面图 + 扭矩分区剖面图 PNG
- 解释异常位置与物理机制的空间一致性
- 物理证据强度评分条

**第三层 · 排除逻辑（Ⅲ）** — 证明唯一性
- 复用因果证据图 PNG
- 逐假说证据文章：原始证据 vs 去趋势后真相 + 排除理由
- 「为什么被排除」的视觉解释块（不需要用户自己推断）
- 综合判决矩阵表（全部假说 × 三层证据）
- 行动建议优先级表 + 局限性说明

三层缺一不可。缺少任一层，证据链不闭合，页面不合格。

### 铁律 8: 证据链的图像必须优先使用诊断管线的真实产出

页面中证据链部分的图像**优先使用 03_figures/ 目录下的真实 PNG**——这些是诊断管线生成的原始视觉证据，不是装饰图。使用规则：

1. 先用 `plot_manifest.json` 查有哪些图、每张图的用途
2. 再用 `visual_analysis.json` 查每张图的 VLM 推断观察
3. 把图匹配到正确的证据层：散点图→统计层、剖面图→物理层、因果图→排除层
4. `img src` 用相对路径（从 output HTML 位置指向 run_dir 的 `03_figures/`）
5. 每个 `img` 标签带 `onerror` 优雅降级
6. 每个图下方配 caption：图编号 + 内容描述 + 诊断意义
7. 没有对应 PNG 时才用 ECharts 重绘或标注「当前缺少该层证据」

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
| P1 | `03_figures/*.png` / `*.jpg` | 现成视觉证据——证据链区块优先复用 |
| P1 | `03_figures/visual_analysis.json` | VLM 推断的图表观察与诊断意义 |
| P1 | `03_figures/image_captions.json` | 图表标题回退 |
| P1 | `3d_model_data.json` | 3D 场景实体、温区、辊位、异常点 |
| P1 | `viz_model_data.json` | 优化版可视化模型数据（如有） |
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
5. ECharts 与 Three.js 必须通过多源 loader 尝试加载，并在页面内输出 5 项 loader 状态条
6. 若远程脚本加载失败，页面仍保留静态文本、摘要卡和本地图片证据
7. 除非用户明确允许，否则不得把「组件未加载成功」的页面视为完成品
8. 页面必须包含一个「结论先行」的首屏摘要，以及一个「我是如何得到这个结论的」简明路径
9. 页面必须控制信息密度，优先突出 3-5 个最关键证据，不得把所有图一股脑平铺为主内容
10. 页面生成后必须经过 `html-reviewer` 质检子 Agent 审核，不通过则返回修订（最多 3 次修订循环）
11. 证据链必须三层完整且各有真实图像/数据/物理推理支撑，缺任一层 → 页面不合格

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

🔴 **CHECKPOINT 1 · 协议确认**: builder agent 读完 html-builder.md 后，在内部确认三件事：(a) 我理解了四段式叙事架构；(b) 我理解了模板继承规则；(c) 我理解了 8 条 fallback 的分支逻辑。确认后再进入 Step 2。

### Step 2: Load the page template

再读 `references/report-template.html`。这是 HTML 结构骨架和 CSS 样式基准。理解其四段式叙事架构、CSS 变量体系、排版节奏后，替换占位数据。

🛑 **CHECKPOINT 2 · 模板可读**: 确认模板文件存在且可完整读取。如果模板不可用，执行 Fallback 1 的分支逻辑。不要跳过这步直接手写 HTML。

### Step 3: Build the artifact inventory

快速识别：

- 这次 run 的主题、产线、目标缺陷、焦点产品
- 哪些 JSON 可以直接抽取结论
- **`03_figures/` 下有哪些 PNG 可直接嵌入证据链**（查 `plot_manifest.json`）
- 哪些图必须用 ECharts 重绘
- 是否存在 `3d_model_data.json` / `viz_model_data.json` 可直接用于 3D 建模
- 当前真实工艺路径是什么，工段先后顺序是什么，异常点落在哪个设备/辊位/区域

🔴 **CHECKPOINT 3 · 产物清单**: 把以上识别结果整理成一个简短的 artifact checklist（5-8 项），内部确认「P0 文件存在 / 3D 数据可用 / PNG 可用 / ECharts 数据可用」。如果 P0 文件全部缺失，执行 Fallback 3 的分支逻辑，不要继续写页面。

### Step 4: Write the page

优先生成一个白底叙事页面，按四段组织：

1. **Hero 结论先行** — 10 秒回答「结论是什么」
2. **背景与产线建模** — 30 秒回答「发生在哪里」（含 3D 模型）
3. **诊断推理过程** — 1 分钟回答「怎么得出来的」（含统计表格 + ECharts 图 + 方法解释）
4. **证据链三层架构** — 2 分钟回答「为什么相信」和「为什么不是别的」
   - 第一层：统计证据（真实 PNG + ECharts 重建图 + 统计强度条）
   - 第二层：物理机制（因果链可视化 + 剖面图 + 物理方程）
   - 第三层：排除逻辑（逐假说排除文章 + 判决矩阵 + 行动建议 + 局限性）

### Step 5: Validate the page

至少检查：

- HTML 是否可打开
- ECharts / Three.js / OrbitControls 是否有主源 + 备用源 + 成功检测
- 至少一个图表是否真正初始化成功（`echarts.getInstanceByDom`）
- 至少一个 Three.js 场景是否真正渲染成功（canvas 元素存在）
- 本地图片路径是否相对输出文件可访问
- **证据链三层是否完整且各有真实图像/数据/推理支撑**
- 主结论、关键证据、排除逻辑、行动建议、局限性是否齐全
- 用户是否能不依赖统计术语理解「为什么得出这个结论」

🔴 **CHECKPOINT 4 · 自检验证**: 跑完上面 8 项检查，把结果写成简短 checklist（每项 PASS/FAIL）。任何 FAIL 项必须修复后再往下。修复超过 3 项 → 回到 Step 4 重新审视页面结构。

如果环境允许预览页面，必须实际打开页面验证加载状态；不要只靠静态阅读 HTML 源码判断成功。

### Step 6: Run html-reviewer

将生成的页面提交给 `html-reviewer` agent 进行独立审校。

🛑 **CHECKPOINT 5 · 审校通过**: 只有当 `html-reviewer` 输出 `verdict: pass` 时，页面才能交付。若 `warn`——修 warning 后重新提交审校。若 `fail`——把 blocker 列表反馈给 builder agent 修订，最多 3 次修订循环；3 次后仍 fail → 终止并向调用者报告 blocker 列表。

## Visual Standards

### 必备信息层

页面首屏必须直接给出：

- 主结论一句话
- 3-4 句白话解释（不用统计术语）
- 诊断类型 / Judge 评分 / 置信度天花板 / 焦点产品 / 样本量 / 异常工段
- 4 格关键发现（最强证据 + 已排除因素 + 推荐动作 + 证据缺口）
- 一段”这页怎么读”的超短引导

### 四段叙事结构

#### 0. Hero — 结论先行（强制 8 元素不允许省略）

以下 8 个元素必须在 Hero 区全部出现，缺一不可：

1. `.hero-bar` — 36px×3px 墨色细线
2. `.display` — 衬线体大标题，`<em>` 强调关键词
3. `.hero-lede` — 3-4 句白话解释，≤640px 宽
4. `.hero-meta` — 诊断类型 / Judge评分 / 置信度 / 焦点产品 / 样本量 / 异常工段（最少 5 项）
5. `.key-findings` — 4 格关键发现网格（1px split border）：最强证据 / 已排除 / 推荐动作 / 证据缺口
6. 每格包含 `.kl` (标签) + `.kv` (值) + 可选 `.kd` (补充说明)
7. 阅读指引 caption — 一句话说明页面自上而下的浏览顺序
8. 4 格内容的每一格必须有具体值，不允许出现空字符串或 Lorem 占位

#### 1. 背景与产线建模

- 场景描述 + 异常定位
- 3D 产线模型：工段平台 + 辊组（半径按真实数据缩放）+ 三区颜色 + 异常高亮 + 编号标签 + 流向
- 图例 + 数据来源标注

#### 2. 诊断推理过程

- 关键统计表格（去趋势前后对比：参数 / ρ / p / 衰减率 / 判决）
- 3-5 张 ECharts 图，每张配三行解读
- 真实 PNG 截图嵌入（时间对齐图、Simpson 悖论可视化等）
- 关键方法白话解释（去趋势、分层分析、竞争假说）

#### 3. 证据链 — 三层闭合架构

**这是页面的核心说服区块。必须包含真实的诊断产线图像、数据分析和物理逻辑推理。**

**第一层 · 统计证据（Ⅰ）:**
- 复用散点图、相关性图 PNG + ECharts 去趋势散点图
- 统计证据强度评分条
- 证据文章：最强存活信号的完整统计值

**第二层 · 物理机制（Ⅱ）:**
- HTML/CSS 物理因果链流程图
- 复用温度/扭矩分区剖面图 PNG
- 每步物理量级估算
- 物理证据强度评分条

**第三层 · 排除逻辑（Ⅲ）:**
- 复用因果证据图 PNG
- 逐假说证据文章（含排除理由视觉解释块）
- 综合判决矩阵表
- 行动建议 + 局限性

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

对每个库都使用”主源 → 备用源 → 失败上报”的顺序。

推荐顺序：

- ECharts
  - `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
  - `https://unpkg.com/echarts@5/dist/echarts.min.js`
- Three.js（通过 importmap ES module，不要用旧的 global script）
  - `importmap`: `”three”: “https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js”`
  - `importmap`: `”three/addons/”: “https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/”`
  - 备用 importmap 源: 替换 jsdelivr 为 unpkg
- OrbitControls（ES module import，不是示例目录全局脚本）
  - `import('three/addons/controls/OrbitControls.js')`
  - Three.js r152 之后 `examples/js/` 目录已删除，OrbitControls 必须通过 `examples/jsm/` 的 ES module 路径载入

页面中必须内置一个 loader 状态区，显示：

- `ECharts: loaded / fallback / failed`
- `Three.js: loaded / fallback / failed`
- `OrbitControls: loaded / optional-missing / failed`
- `Charts initialized: yes / no`
- `3D scene initialized: yes / no`

## Fallback Rules

以下覆盖 8 个常见失败场景的完整 fallback 链。每条规则格式：**触发条件 → 一线修复 → 仍失败兜底**。Builder agent 必须在遇到对应场景时执行对应分支，不得静默继续。

### Fallback 1: `references/report-template.html` 文件不存在

**触发条件**: builder agent 在 Step 2 无法读取模板文件
**一线修复**: 回退到 `templates/page_blueprint.md` 的四段叙事结构 + `templates/render_prompt_template.md` 的构建规范，从零手写 HTML（内联模板中关键 CSS 变量和排版规则）
**仍失败兜底**: 终止生成，向调用者报告「标准模板和回退蓝图均不可用，无法生成高质量报告。请检查 skill 安装是否完整。」

### Fallback 2: `run_dir` 路径无效或不存在

**触发条件**: `run_dir` 不是有效绝对路径，或路径下无任何诊断产物
**一线修复**: 检查路径字符串是否正确、是否缺少前导 `/`、是否用了相对路径。尝试在当前工作目录和 `workspace/diagnostic-runs/` 下查找
**仍失败兜底**: 终止生成，向调用者报告明确的路径错误，列出已尝试的替代路径列表

### Fallback 3: 关键 JSON (diagnosis.json) 为空或格式错误

**触发条件**: `04_diagnostics/diagnosis.json` 文件存在但 `JSON.parse` 失败，或 `primary_finding` 字段为空字符串
**一线修复**: 降级读取 `report.md` 的「执行摘要」章节，提取主结论文本；跳过假说评分、置信度细节
**仍失败兜底**: 页面 Hero 区标注「[诊断结论数据缺失，以下为从 report.md 提取的概要]」；证据链三层标注「[JSON 数据不可解析]」；不捏造统计值

### Fallback 4: `03_figures/` 目录为空或所有 PNG 返回 404

**触发条件**: `plot_manifest.json` 中列出的 PNG 全部不存在或无法加载
**一线修复**: 从 `viz_compact.json` / `diagnosis.json` / `evidence.json` 读取数组数据，用 ECharts 重建关键图表（去趋势散点、鲁棒性对比、温扭剖面）
**仍失败兜底**: 证据链三层中的「真实 PNG」全部替换为 ECharts 重建图（标记为「ECharts 重建 · 原始图像不可用」）；物理因果链流程图仍用 HTML/CSS 展示

### Fallback 5: ECharts 或 Three.js 主源+备用源均加载失败

**触发条件**: `document.getElementById('dotEcharts')` 和 `document.getElementById('dotThree')` 的状态均为 fail
**一线修复**: 保留摘要卡、文字讲解、所有本地 PNG（`<img>` 标签不受影响）、静态证据链模块；loader 状态条所有指标变红
**仍失败兜底**: 页面首屏显式提示「当前浏览环境无法加载交互式图表/3D 模块，页面处于静态降级模式」；保留 Hero + 背景 + 统计表格 + 证据文章文字 + 行动建议（关键信息不丢失）

### Fallback 6: ECharts `echarts.init()` 返回 null（DOM 未挂载）

**触发条件**: `echarts.getInstanceByDom(dom)` 验证返回 undefined
**一线修复**: 检查对应 `<div id="chartN">` 是否在 DOM 中存在、是否被 `display:none` 隐藏；若 DOM 正常但 init 返回 null，重试一次（setTimeout 200ms）
**仍失败兜底**: 该图的位置显示静态替代文字「[图表加载失败]」+ 图标题 + 三行解读的文字内容；loader 状态条「图表初始化」变红

### Fallback 7: Three.js `WebGLRenderer` 创建失败（WebGL 不可用）

**触发条件**: `new THREE.WebGLRenderer()` 抛出异常或返回 null
**一线修复**: 尝试 `THREE.WebGLRenderer({ failIfMajorPerformanceCaveat: true })` 检测；若失败则尝试 `THREE.CSS2DRenderer` 纯 DOM 渲染简化标注；若仍失败则降级为 2D SVG/Canvas 工段流程图
**仍失败兜底**: 3D 容器显示静态替代内容「[WebGL 3D 模块不可用 · 产线结构: 预加热段(辊1-5)→拉伸段(辊6-11)→急冷定型段(辊12-18)]」；保留工段文字描述 + 异常辊位文本说明

### Fallback 8: `3d_model_data.json` 和 `ontology.json` 均缺失

**触发条件**: 两个文件都不存在
**一线修复**: 从 `report.md` 和 `diagnosis.json` 中提取产线描述文本，用 HTML/CSS 画 2D 工段流程图（div + 箭头字符 + 颜色区分）
**仍失败兜底**: 3D 容器替换为「[产线结构数据缺失，以下为从诊断结论提取的工段文字描述]」+ 文字版工段顺序 + 异常位置文本；不影响 Hero / 诊断推理 / 证据链区块

### 通用降级原则

- **不静默失败**：任何 fallback 触发时，页面必须在对应位置显示降级状态标签
- **不丢信息**：降级后用户仍能获取 Hero 结论、关键统计值、排除逻辑、行动建议
- **不假装成功**：loader 状态条如实反映每个模块的加载状态

## Style Direction & Visual Grammar

> **Builder agent 必须先读本节再写页面。** 这里定义的不是”参考建议”，而是页面设计的强制视觉语法。Fallback 规则在下一节，出错时查阅。

### Default: Light Minimal Narrative（白底极简叙事）

页面传达的不是”技术系统感”，而是”清晰的诊断说服力”。

### 设计原则（v2）

1. **白底暖调** — `#fafaf8` + `#f4f3f0` 次级底
2. **单墨色贯穿** — `#1e3a54` 唯一强调色
3. **衬线标题 + 无衬线正文** — 排版层次替代装饰
4. **大留白 + hairline** — 1px分割线替代卡片阴影
5. **正文 ≤640px** — 控制阅读节奏

### 色彩系统（CSS 变量强制）

页面必须使用 CSS 自定义属性，不得硬编码颜色值。当前变量体系：

```css
:root {
  /* 背景层 — 暖白阶梯 */
  --bg: #fafaf8;
  --bg-alt: #f4f3f0;
  --bg-card: #ffffff;

  /* 边框 — hairline 体系 */
  --hairline: rgba(0,0,0,0.06);
  --rule: rgba(0,0,0,0.10);
  --em: rgba(0,0,0,0.16);

  /* 文字层级 — 高对比 */
  --t1: #111111;
  --t2: #4a4a4a;
  --t3: #888888;

  /* 功能色 — 低饱和度 */
  --ink: #1e3a54;       /* 蓝灰墨色 — 主强调/信息/统计 */
  --warm: #c2673a;      /* 暖橙 — 异常/警告/物理 */
  --green: #2d7d4f;     /* 深绿 — 成功/通过/证据强 */
  --red: #c4433b;       /* 暗红 — 排除/危险/统计死亡 */
  --gold: #8a6d3b;      /* 暗金 — 中等置信度/过渡 */

  /* 排版 */
  --serif: 'Source Serif 4', 'Noto Serif SC', 'Songti SC', Georgia, serif;
  --sans: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --mono: 'SF Mono', 'JetBrains Mono', 'Consolas', monospace;
}
```

### 排版系统

| 层级 | 字体 | 大小 | 用途 |
|------|------|------|------|
| `.display` | var(--serif) | 2.8rem / 600 / -0.025em | Hero 主结论 |
| `h1` | var(--serif) | 1.9rem / 600 / -0.015em | 主标题 |
| `h2` | var(--serif) | 1.45rem / 600 | Section 标题 |
| `h4` | var(--serif) | 1.08rem / 600 | 证据文章标题 |
| `.body-l` | var(--sans) | 1.08rem | 引导段落 |
| `.body` | var(--sans) | 0.9rem | 正文 |
| `.caption` | var(--sans) | 0.76rem | 图表说明、元数据 |
| `.mono` | var(--mono) | 0.78rem | 统计数值、代码 |

### Hero 区规范

- 顶部 36px × 3px 细线装饰（`--ink`）
- 衬线 display 大标题，`<em>` 标签强调关键词（`--warm` italic）
- 导语段 max-width: 640px
- 元数据行：flex-wrap + gap: 32px
- 4 格关键发现：`grid-template-columns: repeat(4, 1fr)`，1px split border frame
- 底部 caption 阅读指引

### 章节标题规范

- Section 编号用等宽字体 + `--t3` 色 + `letter-spacing: 0.1em`
- h2 标题用衬线体

### 证据链三层视觉标识

- 每层独立 `.evidence-layer` 容器
- 层标题带圆形数字图标（Ⅰ/Ⅱ/Ⅲ），颜色区分：统计=墨色 / 物理=暖橙 / 排除=暗红
- 层内证据文章用 hairline 底部分隔

### 证据强度评分条

```html
<!-- 统计证据强度: 85/100 -->
<div class=”evidence-score”>
  <div class=”es-bar fill” style=”width:85px”></div>
  <div class=”es-bar empty” style=”width:15px”></div>
  <span class=”es-label”>统计证据强度: 85/100</span>
</div>
```

### 物理因果链

```html
<div class=”physics-chain”>
  <div class=”pc-step”><div class=”pc-title”>① 辊面μ不均匀</div><div class=”pc-detail”>低聚物沉积<br>μ_s > μ_k</div></div>
  <div class=”pc-arrow”>→</div>
  <!-- ... 更多步骤 ... -->
</div>
```

### 统计强调标签

```html
<span class=”stat-callout”>ρ=+0.554, p=0.014</span>
<!-- 渲染为: 等宽字体 + 墨色 + 淡墨色背景 -->
```

### 3D 容器规范

- 高度: 500px (桌面) / 340px (平板) / 260px (手机)
- 背景: `#ecebe6`（暖灰，匹配白底）
- 悬停: `cursor: grab` / `cursor: grabbing`
- Overlay: 左上角等宽字体 + 半透明白底
- 图例: 右下角 + 5 色 swatch（预加热/拉伸/急冷/异常/流向）

### 图表容器规范

- ECharts 图表高度: 380px (桌面) / 280px (平板)
- 图表标题用 `.chart-panel-header` + 等宽编号
- 三行解读用 `.chart-reading` (grid: 90px + 1fr)
- 解读三行标签（”看到什么 / 说明什么 / 为什么重要”）用等宽字体 + 墨色
- 全局 ECharts 色板: `['#1e3a54', '#2d7d4f', '#c2673a', '#c4433b', '#8a6d3b']`

### 统计表格规范

```css
.stat-table { width:100%; border-collapse:collapse; }
.stat-table thead th { text-transform:uppercase; letter-spacing:0.08em; color:var(--t3); border-bottom:1px solid var(--rule); }
.stat-table tbody td { border-bottom:1px solid var(--hairline); }
.stat-table .num { font-family:var(--mono); text-align:right; }
.stat-table .hi { color:var(--ink); font-weight:600; }
.stat-table .lo { color:var(--t3); }
```

### 移动端适配（强制）

```css
@media (max-width: 768px) {
  .page { padding: 0 18px; }
  .hero .display { font-size: 1.7rem; }
  .key-findings { grid-template-columns: repeat(2, 1fr); }
  .threejs-stage { height: 340px; }
  .chart-canvas { height: 280px; }
  .chart-reading { grid-template-columns: 1fr; }
  .section { margin: 56px 0; }
  .reading-nav { display: none; }
  .physics-chain { flex-wrap: wrap; }
}
@media (max-width: 480px) {
  .key-findings { grid-template-columns: 1fr; }
  .threejs-stage { height: 260px; }
  .hero-meta { gap: 18px; }
}
```

### 不要做成的风格

| 禁止 | 原因 |
|------|------|
| 暗色工业风 (080d14 深底) | 与当前模板不兼容，除非用户明确指定 |
| 卡片阴影堆砌 | 白底用 hairline 分隔，不靠阴影建立层次 |
| 彩色顶部装饰线 | 用单一墨色，不凭空发明颜色 |
| 紫色渐变 / 霓虹 glow | AI slop，携带零品牌信息 |
| 满屏 KPI 数字跳动 | 用户不是来监控的，是来理解结论的 |
| 图片墙式平铺 | 每张图必须配三行解读，没有例外 |

## 🔴 红线黑名单（命中任一条 → html-reviewer 直接判 fail）

| # | 🚫 禁止 | 为什么 | 正确 |
|---|--------|--------|------|
| 1 | **证据链平铺卡片堆** | 用户分不清相关/因果 | 统计→物理→排除三层独立展开 |
| 2 | **证据链无真实 PNG** | 03_figures 是原始产出 | plot_manifest.json 查图→匹配证据层→嵌入 |
| 3 | **只有统计无物理** | ρ 只证明相关 | 因果链+每步方程 |
| 4 | **只说A不说为什么不是BCD** | 信任未闭环 | 逐假说列排除理由+原始vs去趋势 |
| 5 | **3D画通用工厂** | 装饰垃圾 | ontology恢复工段→真温区→异常落位 |
| 6 | **图旁无文字** | 看不懂 | 每图三行：看到什么/说明什么/为什么重要 |
| 7 | **首屏无结论** | 需滚动才知答案 | Hero区结论在最顶部 |
| 8 | **术语不翻译** | 非算法用户不懂 | ρ=0.73→"方向几乎一致" |
| 9 | **图片404** | 视觉证据丢失 | 相对路径+onerror |
| 10 | **工段数与场景矛盾** | 3D推翻结论 | ontology+3d_model_data恢复真值 |
| 11 | **捏造数据** | 造假 | 仅用run_dir真实JSON |
| 12 | **不跑reviewer** | 逻辑断层 | 3次修订循环上限 |
| 13 | **暗色工业风** | 与v2模板不兼容 | 白底极简；除非用户明确指定暗色 |

## Deliverable Closeout

完成后必须告诉调用者：

1. 读取了哪些关键文件
2. HTML 输出到了哪里
3. 哪些内容是直接复用已有图像，哪些是重新生成图表
4. 证据链三层各用了哪些数据源（哪些来自 03_figures PNG，哪些来自 JSON 重绘）
5. 如果还要继续优化，最值得增强的是哪一层证据或哪一种交互

在交付前还要确认：

- `html-reviewer` 是否通过
- 若未通过，是否已经把 blockers 反馈给 `html-visualizer` 修订

## References Directory

`references/` 目录包含以下文件：

| 文件 | 用途 |
|------|------|
| `report-template.html` | **HTML 结构骨架和 CSS 样式基准**。builder agent 以此为基础替换占位数据。包含四段式叙事架构、CSS 变量体系、排版节奏、移动端断点、ECharts/Three.js 多源 loader、三层证据链结构。 |
