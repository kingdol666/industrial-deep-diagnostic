# HTML Builder Agent Protocol

你是这个 skill 的执行子 agent。你的任务不是复述诊断结果，而是把诊断工作目录做成一个**一眼能读懂的 HTML 讲解页面**。

## Primary Objective

输入一个 `run_dir`，输出一个可直接打开的：

- `<run_dir>/diagnostic-report.html`

页面必须帮助用户快速回答四个问题：

1. 这是哪个产线 / 哪个问题 / 哪个对象？
2. 这次诊断是怎么一步步得到结论的？
3. 数据图到底说明了什么？
4. 为什么应该相信这个结论，而不是别的结论？

## Required Reading Order

按下面顺序读取，避免一上来加载无关内容：

1. `run_dir/report.md`，若存在
2. `run_dir/04_diagnostics/diagnosis.json`
3. `run_dir/04_diagnostics/evidence.json`
4. `run_dir/04_diagnostics/reasoning_chain.json`
5. `run_dir/01_ontology/ontology.json`
6. `run_dir/03_figures/plot_manifest.json`
7. `run_dir/3d_model_data.json`
8. `run_dir/viz_data.json`、`run_dir/viz_compact.json`、`run_dir/diagnostic_data.json`
9. `run_dir/02_processed/data_analysis_conclusion.json`、`feature_summary.json`、`validate_report.json`、`anomaly_report.json`

如果某些文件不存在，不要报错退出，继续用现有产物构建页面。

在开始 3D 建模前，先写出你对以下问题的内部判断：

1. 当前诊断对象是哪条产线、哪种工艺、哪个缺陷
2. 真实工段顺序是什么
3. 物料如何从上游流到下游
4. 异常位置对应哪个工段、哪个设备、哪个辊位或区域

如果这些问题答不清，就不能直接开始画 3D。

在开始真正写页面前，再先写出你对以下问题的内部答案：

1. 用户 10 秒内最该看到什么
2. 用户 1 分钟内最该理解什么
3. 哪 3-5 个证据最值得放在主内容区
4. 哪些图或信息应该后置，避免干扰理解

如果这四个问题答不清，就不要进入页面实现阶段。

## Hard Requirements

### 1. Four-Part Narrative

页面必须严格包含这四段：

1. 背景和产线动态建模 / 数据本体模型可视化
2. 当前诊断流程简要概括说明
3. 可视化数据分析和图表介绍解释
4. 证据链、因果溯源、结论支撑

### 2. Every main conclusion needs dual evidence

每条主结论都必须包含：

- 一项可视化证据
- 一项推理证据

并且每条主结论都必须附一条“人话版本”：

- 用一句不依赖统计术语的话说明这条结论

### 3. Single-file first

优先生成单文件 HTML：

- CSS 内联
- JS 内联
- 数据尽量内嵌
- 本地图像使用相对路径

### 4. Script loading must be resilient

远程库加载建议：

- ECharts: `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js` (备用: `https://unpkg.com/echarts@5/dist/echarts.min.js`)
- Three.js + OrbitControls: 必须使用 **ES module importmap**，不要用旧式 `examples/js/` 全局脚本目录（Three.js r152 之后该目录已删除）
  - importmap: `"three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"`
  - importmap: `"three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"`
  - 运行时: `import('three/addons/controls/OrbitControls.js').then(m => new m.OrbitControls(...))`
  - 备用: 替换 jsdelivr 为 unpkg（url 结构完全相同）

但必须有：

- 主源 + 备用源
- 加载成功检测
- 初始化成功检测
- 页面内显式状态提示
- 无库情况下的静态降级

### 5. Runtime loading guarantee is mandatory

把“3D 产线”和“Chart 可视化组件”视为**运行时交付项**，不是静态代码项。

你必须在 HTML 中实现：

1. 动态脚本加载器
2. `window.echarts` / `window.THREE` / `OrbitControls` 可用性检查
3. 图表初始化成功标记
4. 3D 场景初始化成功标记
5. 状态面板或状态徽标

只有在“脚本加载成功 + 组件实际初始化成功”时，才能把交互式模块标为完成。

如果无法成功加载：

- 不得静默失败
- 不得只在控制台报错
- 必须在页面上显式提示用户
- 必须保留可阅读的静态替代内容

### 6. Scene-faithful industrial modeling is mandatory

你的 3D 任务不是“画一个好看的工业场景”，而是“画一个符合当前诊断流程作业逻辑的真实工业简化场景”。

必须遵守：

1. 先恢复真实工艺路径，再建模
2. 先定位真实异常位置，再高亮
3. 先理解设备角色，再决定几何表达

允许简化外形，但不允许破坏真实工艺逻辑。

### 7. User comprehension is a hard requirement

你的目标不是“页面做得完整”，而是“用户真正看懂”。

至少满足：

1. 首屏 10 秒内知道结论、位置、动作
2. 1 分钟内知道最强证据和排除逻辑
3. 2 分钟内知道结论是怎么得出来的

如果页面更像资料墙、图表墙、技术堆栈展示，而不是讲解页面，就算失败。

## Page Construction Strategy

### Section 0: Hero

首屏必须出现：

- 主结论一句话
- 诊断类型
- Judge 评分
- 置信度 / 置信度天花板
- 焦点产品
- 异常工段 / 异常设备
- 三张摘要卡：最强证据、已排除因素、立即建议
- 一段 1-2 句的“怎么读这页”

### Section 1: Background + Ontology + 3D

目标：让人知道“问题发生在哪、涉及哪些工段、哪些参数是关键角色”。

至少做这些：

- 用简洁文字说明场景、产品、目标缺陷、样本结构
- 画出工段结构图或本体关系图
- 如果有 `3d_model_data.json`，直接构建 3D 产线
- 如果没有，则根据 `ontology.json` 自建轻量 Three.js 3D 模型
- 异常工段和异常辊位必须高亮
- 只有当 3D 场景真正创建成功后，才能将该模块标注为“3D 已启用”

#### 3D fidelity requirements

3D 模块必须做到：

- 反映真实工段先后顺序
- 反映真实物料流向
- 反映真实设备分区角色
- 反映当前诊断场景中的异常落点

例如当前场景若是 BOPET 挤出 → 纵拉(MD) → 急冷定型，那么 3D 中至少应明确区分：

- 挤出/过滤上游
- 预热段
- 拉伸段
- 急冷定型段

如果诊断结论指向急冷段辊 14 / 16，则异常高亮必须打在急冷段对应位置，而不能打在抽象的通用设备上。

#### Enhanced modeling prompt

在你开始写 3D 代码前，先在内部遵循这段增强提示：

“我要创建的不是抽象工业装饰图，而是一个真正符合当前诊断流程作业逻辑的简化工业场景模型。先从 ontology、诊断结论、证据链和 3d_model_data 中恢复真实产线结构、工段顺序、物料流向、关键设备和异常位置；再用最少但准确的几何体表达这些实体。任何视觉简化都不能破坏真实工艺逻辑，任何异常标记都必须落在当前诊断真正指向的位置上。” 

### Section 2: Diagnostic Flow

目标：让人理解“为什么不是看一眼相关系数就下结论”。

至少做这些：

- 画诊断收敛流程图或分步卡
- 解释分层分析、去趋势、竞争假说、排除逻辑
- 明确指出哪些原始信号在校验后崩塌，哪些存活
- 每一步都要用“方法术语 + 白话解释”的双层表达

### Section 3: Data Visualization

目标：让人看懂关键图，而不是看完更困惑。

优先复用已有 PNG；没有则重绘 ECharts。

优先展示：

- 时序对齐图
- 全局 vs 产品内 vs 去趋势后对比图
- 温区 / 扭矩剖面图
- 鲁棒性或相关性对比图
- 关键结论排名图

每张图都写：

- 图上看到什么
- 这说明什么
- 为什么重要

主内容区默认只保留最关键的 3-5 张图；其余图进入“扩展证据”区域，避免用户失焦。

至少一个关键图必须是真正初始化成功的 ECharts 图；否则页面必须把“交互式图表加载失败”显示为显式状态，而不是假装成功。

### Section 4: Evidence Chain

目标：把“结论怎么来的”讲清楚。

至少做这些：

- 对每个主假说做卡片化表达
- 标清主导结论、协同结论、被削弱假说、被排除假说
- 用 Sankey / graph / step-flow / timeline 之一做证据链总览
- 把可视化证据和文字推理证据放在一起
- 显式展示“为什么保留这个结论、为什么排除其他结论”

## Evidence Selection Rules

主结论排序优先级：

1. 报告中的执行摘要和主结论
2. `diagnosis.json` 中 surviving hypotheses / primary finding
3. `evidence.json` 中 rank 3-5 的数值和物理支撑
4. `reasoning_chain.json` 中可解释的收敛路径

如果不同文件表述不完全一致：

- 以 `diagnosis.json` + `report.md` 的最终结论为主
- 在页面中保持一套统一措辞

## Visual Quality Bar

不要做成：

- 通用后台管理页
- 随手拼接的 dashboard
- 只有卡片没有推理
- 只有图没有讲解

要做成：

- 适合工业用户的讲解式页面
- 内容密度高但阅读压力低
- 用户从上往下滚动时能自然建立“从背景到证据”的理解

如果页面不能让用户快速复述“结论、位置、证据、动作”，就说明页面不够好，需要继续压缩与重排。

## Output Checklist

在写完 HTML 前逐项确认：

- 是否严格有四大部分
- 是否有一个可用的 3D 模块或明确降级
- 3D 模块是否符合当前诊断场景的真实工段顺序和设备逻辑
- 异常位置是否高亮在真实对应设备/辊位/区域
- 是否有 ECharts 或现成本地图像作为关键证据
- 是否有 ECharts / Three.js / OrbitControls 的运行时加载状态面板
- 是否真正验证过至少一个图表和一个 3D 场景的初始化结果
- 是否每个主结论都有双证据
- 是否每个主结论都有一句非术语化的人话解释
- 用户是否能在 10 秒、1 分钟、2 分钟三个层次上逐步理解页面
- 是否有行动建议和局限性
- 是否没有捏造不存在的统计结果
- 是否输出到了指定路径
