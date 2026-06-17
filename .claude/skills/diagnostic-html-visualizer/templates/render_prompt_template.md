# Universal Render Prompt Template

在需要把任务转交给另一个实现 agent 时，可以把下面这段作为基础提示词，再替换占位符：

```text
请读取诊断工作目录 `{RUN_DIR}` 下的诊断产物，并生成一个完整的 HTML 可视化讲解页面，输出到 `{OUTPUT_HTML}`。

目标：让非算法背景的工业用户也能一眼读懂这次诊断结论、证据链、异常位置和下一步动作。

必须包含四大部分：
1. 背景与动态建模 / 数据本体模型可视化
2. 当前诊断流程简要概括说明
3. 可视化数据分析和图表解释
4. 证据链、因果溯源、结论支撑

优先读取这些文件（存在则使用）：
- `report.md`
- `01_ontology/ontology.json`
- `02_processed/data_analysis_conclusion.json`
- `02_processed/causal_evidence_map.json`
- `02_processed/feature_summary.json`
- `02_processed/validate_report.json`
- `02_processed/anomaly_report.json`
- `03_figures/plot_manifest.json`
- `03_figures/visual_analysis.json`
- `03_figures/image_captions.json`
- `04_diagnostics/diagnosis.json`
- `04_diagnostics/evidence.json`
- `04_diagnostics/confidence.json`
- `04_diagnostics/reasoning_chain.json`
- `3d_model_data.json`
- `viz_data.json`
- `viz_compact.json`
- `diagnostic_data.json`

页面要求：
- 中文讲解
- 单文件 HTML 优先
- 使用 ECharts 和 Three.js
- 脚本远程加载必须有主源、备用源、运行时检测、状态展示和失败降级
- Three.js 必须使用 importmap ES module 加载（不是旧式 global script），OrbitControls 通过 `import('three/addons/controls/OrbitControls.js')` 载入
- 重点结论必须有“可视化证据 + 推理证据”
- 若存在异常工段或异常辊位，必须在 3D 模块中高亮
- 若图片存在则复用；若关键图缺失则用真实 JSON 数据重绘
- 只有在图表和 3D 组件真实初始化成功后，才能将其标记为已启用
- 3D 建模必须符合当前诊断场景的真实工艺流程、工段顺序、设备角色、物料流向和异常位置，不允许画成通用抽象工业装饰图

在开始 3D 建模前，请先遵循这段增强提示：
“我要创建的不是通用工业示意图，而是一个真正符合当前诊断流程作业逻辑的简化工业场景模型。先从 ontology、诊断结论、证据链、3d_model_data 和报告中恢复真实产线结构、工段顺序、物料流向、关键设备和异常位置；再用准确但简化的几何体表达这些实体。任何视觉简化都不能破坏真实工艺逻辑，任何异常标记都必须落在当前诊断真正指向的位置上。”

请在页面中实现一个状态面板，明确展示：
- ECharts 是否加载成功
- Three.js 是否加载成功
- OrbitControls 是否加载成功
- 至少一个图表是否渲染成功
- 至少一个 3D 场景是否渲染成功

请在完成说明中额外交代：
- 3D 场景依据了哪些文件恢复真实工艺顺序
- 异常位置是如何映射到具体设备/辊位/区域的

完成后说明：
- 你读取了哪些关键文件
- 页面输出到了哪里
- 哪些图是复用，哪些是重绘
```
