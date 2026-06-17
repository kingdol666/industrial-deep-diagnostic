# Universal Render Prompt Template v2

在需要把任务转交给另一个实现 agent 时，可以把下面这段作为基础提示词，再替换占位符：

```text
请读取诊断工作目录 `{RUN_DIR}` 下的诊断产物，并生成一个完整的 HTML 可视化讲解页面，输出到 `{OUTPUT_HTML}`。

目标是让非算法背景的工业用户也能一眼读懂诊断结论、异常位置、推理路径和证据链。

## 模板文件

你必须以 `references/report-template.html` 为 HTML 结构骨架和 CSS 样式基准。
读取该文件，理解其四段式叙事架构、CSS 变量体系、排版节奏和组件规范，然后按以下要求替换内容：

1. **保留 CSS 变量体系和排版框架**（字体、色彩、间距、留白、移动端断点）
2. **保留导航圆点、loader 状态条、footer 结构**
3. **替换所有占位数据为真实诊断数据**（结论文案、统计值、假说描述）
4. **根据真实数据调整 ECharts 图表**（数据系列、标注点、坐标范围）
5. **根据真实产线结构调整 Three.js 3D 场景**（工段数、辊数、异常位置、温区颜色）
6. **替换图片 src 指向真实 PNG 文件**（带 onerror 优雅降级）

## 必须包含四大部分

### 0. Hero 结论先行
- 主结论一句话（衬线体 display，em 强调关键词）
- 3-4 句白话解释段落
- 元数据标签行：诊断类型 / Judge 评分 / 置信度天花板 / 焦点产品 / 样本量 / 异常工段
- 四格关键发现网格：最强证据 / 已排除因素 / 推荐动作 / 证据缺口
- 阅读指引

### 1. 背景与产线建模
- 场景描述 + 异常定位
- Three.js 3D 产线模型（工段平台 + 辊组 + 异常高亮 + 物料流向 + 三区颜色 + 图例）
- 3D 场景必须从 ontology.json + 3d_model_data.json + viz_model_data.json 恢复真实结构
- 3D 容器下方标注数据来源

### 2. 诊断推理过程
- 关键统计表格（去趋势前后对比：参数 / Spearman ρ / p值 / 衰减率 / 判决）
- 3-5 张 ECharts 图表，每张配三行解读（看到什么 / 说明什么 / 为什么重要）
- 图表数据必须来自真实 JSON 文件（viz_compact.json、diagnosis.json 等）
- 关键方法白话解释

### 3. 证据链（三层架构）⚠️ 这是用户信任建立的核心区块

#### 第一层 · 统计证据（Ⅰ）
- 复用诊断生成的散点图、相关性图 PNG（from 03_figures/）
- 至少 1 张 ECharts 重建的分析图（去趋势散点、相关性鲁棒性对比等）
- 统计证据强度评分条
- 证据文章：明确指出最强存活信号，附完整 Spearman ρ + p 值 + 衰减率

#### 第二层 · 物理机制（Ⅱ）
- HTML/CSS 物理因果链流程图（每个步骤节点有标题 + 物理细节）
- 复用温度分区剖面图 + 扭矩分区剖面图 PNG
- 每步附物理量级估算或物理方程
- 解释异常位置与物理机制的空间一致性
- 物理证据强度评分条

#### 第三层 · 排除逻辑（Ⅲ）
- 复用因果证据图 PNG
- 对被排除和被削弱的假说逐一撰文：
  - 假说名称 + 排除/削弱置信度
  - 原始证据 vs 去趋势后真相
  - 物理矛盾或内部不一致
  - 「为什么被排除」的解释块
- 证据链综合判决矩阵表（全部假说 × 三层证据）
- 行动建议优先级表（P0/P1/P2）
- 局限性说明

## 优先读取这些文件（存在则使用）

- `report.md`
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `01_ontology/ontology.json`
- `02_processed/data_analysis_conclusion.json`
- `02_processed/causal_evidence_map.json`
- `02_processed/feature_summary.json`
- `02_processed/validate_report.json`
- `02_processed/anomaly_report.json`
- `03_figures/plot_manifest.json`（获取图表清单与用途描述）
- `03_figures/visual_analysis.json`（获取 VLM 推断的图表观察）
- `03_figures/image_captions.json`
- `03_figures/*.png` / `*.jpg`（本地图像证据——优先复用！）
- `3d_model_data.json`
- `viz_model_data.json`
- `viz_data.json` / `viz_compact.json`
- `diagnostic_data.json`

## 图表与图像使用优先顺序

1. **优先复用 03_figures/ 下的已有 PNG**——这些是诊断管线生成的原始视觉证据
2. **没有对应 PNG 时用 ECharts 重绘**——直接读取 viz_compact.json 或 diagnosis.json 中的数组数据
3. **缺失数据时标注诚实 placeholder**——写 "[当前缺少该层证据]" 而非编造

## 页面要求

- 中文讲解（统计术语后紧跟白话解释）
- 单文件 HTML（CSS/JS 内联）
- ECharts 主源 + 备用源 + 运行时检测 + 状态展示 + 失败降级
- Three.js importmap ES module + OrbitControls 动态 import + 备用源
- 重点结论必须有「可视化证据 + 推理证据」
- 异常工段或异常辊位必须在 3D 模块中高亮
- 3D 建模必须符合当前诊断场景的真实工艺流程
- 页面加载状态面板展示 5 项状态指标
- 移动端双断点适配（768px / 480px）

## 在开始 3D 建模前，先遵循这段增强提示

"我要创建的不是通用工业示意图，而是一个真正符合当前诊断流程作业逻辑的简化工业场景模型。先从 ontology、诊断结论、证据链、3d_model_data 和报告中恢复真实产线结构、工段顺序、物料流向、关键设备和异常位置；再用准确但简化的几何体表达这些实体。任何视觉简化都不能破坏真实工艺逻辑，任何异常标记都必须落在当前诊断真正指向的位置上。"

## 完成后说明

- 你读取了哪些关键文件
- 页面输出到了哪里
- 哪些图是复用 03_figures PNG，哪些是 ECharts 重绘
- 3D 场景依据了哪些文件恢复真实工艺顺序
- 异常位置是如何映射到具体设备/辊位/区域的
- 证据链三层各用了哪些数据源
```
