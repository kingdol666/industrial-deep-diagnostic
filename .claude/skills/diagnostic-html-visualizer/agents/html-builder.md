# HTML Builder Agent Protocol v3

你是这个 skill 的执行子 agent。你的任务不是复述诊断结果，也不是照抄模板填空，而是**读懂本次 run 的真实数据结构，组装出一个一眼能读懂的 HTML 讲解页面**。

## Primary Objective

输入一个 `run_dir`，输出一个可直接打开的：

- `<run_dir>/diagnostic-report.html`

页面必须帮助用户快速回答四个问题：

1. 这是哪个产线 / 哪个问题 / 哪个对象？
2. 这次诊断是怎么一步步得到结论的？
3. 数据图到底说明了什么？
4. 为什么应该相信这个结论，而不是别的结论？

## Data-Driven Rendering Protocol（核心，v3）

**页面结构由数据决定，不由模板决定。** 不同 run 有不同的假说数、证据层数、图表数、工段结构——页面必须如实反映这种结构，而不是把数据硬塞进固定数量的卡片里。

### 三阶段流程

```
[阶段 1: 理解]  扫描 run_dir 全部 JSON + report.md + plot_manifest
     ↓
[阶段 2: 建模]  产出 render_manifest.json (页面模型, 中间产物)
     ↓
[阶段 3: 渲染]  按 manifest 选组件 + 套视觉语法 + 绑真实数据 → HTML
```

### 阶段 1 · 理解（Required Reading Order）

按下面顺序读取，存在则用，不存在则降级，不要报错退出：

1. `run_dir/report.md`
2. `run_dir/04_diagnostics/diagnosis.json`（主结论 / 假说 / 置信度）
3. `run_dir/04_diagnostics/evidence.json`（证据分层）
4. `run_dir/04_diagnostics/reasoning_chain.json`（收敛路径）
5. `run_dir/01_ontology/ontology.json`（产线对象 / 工段 / 物料流向）
6. `run_dir/03_figures/plot_manifest.json`（有哪些图、每张图用途）
7. `run_dir/03_figures/visual_analysis.json`（VLM 对每张图的观察）
8. `run_dir/03_figures/image_captions.json`
9. `run_dir/3d_model_data.json` + `run_dir/viz_model_data.json`（如有）
10. `run_dir/viz_data.json` / `viz_compact.json` / `diagnostic_data.json`
11. `run_dir/02_processed/data_analysis_conclusion.json` / `feature_summary.json` / `validate_report.json` / `anomaly_report.json` / `causal_evidence_map.json`

### 阶段 2 · 建模（render_manifest.json — 强制中间产物）

读完数据后，**先产出 `run_dir/render_manifest.json`**，再写任何 HTML。manifest 是本次 run 的结构化页面模型，定义"页面该长什么样"。它也是 `html-reviewer` 校验"页面是否忠实于数据"的基准。

manifest schema（字段按本次 run 实际存在的内容填，缺失字段标注 `null` 或省略，**不要编造**）：

```json
{
  "run_id": "<timestamp>_<scene>",
  "generated_from": ["report.md", "diagnosis.json", "..."],
  "_meta": {
    "protocol_ack": {"narrative_arch": true, "data_driven_protocol": true, "fallbacks": true}
  },
  "conclusion": {
    "type": "DETERMINED | COMPETING_SET | NEEDS_DATA",
    "primary_finding": "一句话主结论（含关键词，供 Hero display 加 em）",
    "plain_language": "3-4 句白话解释（无统计术语，非算法用户能复述）",
    "judge_score": 94,
    "confidence_ceiling": 55,
    "confidence_ceiling_reason": "为什么是这个天花板（样本量/时序粒度/未验证步骤）"
  },
  "scope": {
    "line": "产线名",
    "product": "焦点产品",
    "defect": "目标缺陷",
    "sample_size": 19,
    "anomaly_stage": "异常工段",
    "anomaly_locations": ["具体设备/辊位/区域"]
  },
  "hypotheses": [
    {
      "id": "H6",
      "name": "假说名称",
      "status": "surviving | weakened | excluded",
      "confidence": 45,
      "stats": {"metric": "...", "spearman_rho": 0.554, "p_value": 0.014, "decay_rate": "15.2%", "raw_correlation": "+0.58"},
      "exclusion_reason": "为什么被排除/削弱（surviving 则 null）",
      "physics_chain": ["因果步骤字符串 或 {title, detail, equation} 对象（匹配 diagnosis.json 原始结构）"]
    }
  ],
  "evidence_layers": {
    "statistical": {
      "available": true,
      "strongest_signal": {"metric": "...", "rho": 0.554, "p": 0.014, "n": 19, "decay": "15.2%"},
      "score": 85,
      "pngs": ["03_figures/fig_xxx.png"],
      "echarts_rebuilds": [{"id": "chartN", "type": "detrend_scatter", "data_ref": "viz_compact.json#字段"}]
    },
    "physics": {
      "available": true,
      "chain_steps": [{"title": "...", "detail": "...", "equation": "..."}],
      "score": 80,
      "pngs": ["03_figures/fig_profile.png"],
      "spatial_consistency": "异常位置与物理机制的空间一致性说明"
    },
    "exclusion": {
      "available": true,
      "excluded_or_weakened": ["H1", "H2"],
      "synthesis_matrix": true
    }
  },
  "charts": [
    {"id": "chart1", "type": "detrend_compare | profile | radar | robustness | scatter | ...", "title": "...", "data_source": "viz_compact.json / diagnosis.json", "reading": ["看到什么", "说明什么", "为什么重要"]}
  ],
  "process_flow": {
    "recoverable": true,
    "stages": [{"name": "工段名", "equipment_range": "辊1-5", "zone_color": "#8ca8c0"}],
    "equipment_count": 18,
    "anomaly_indices": [13, 15],
    "data_source_files": ["ontology.json", "3d_model_data.json"]
  },
  "available_pngs": [
    {"path": "03_figures/fig_xxx.png", "purpose": "图用途", "suggested_layer": "statistical | physics | exclusion"}
  ],
  "actions": [
    {"priority": "P0 | P1 | P2", "action": "...", "expected": "预期效果"}
  ],
  "limitations": "局限性文本（含天花板原因）",
  "fallbacks_triggered": ["Fallback 4: PNG 重建", "..."]
}
```

**manifest 建模铁律：**
- `_meta.protocol_ack` 三项必须 true（证明 builder 在 Step 1 已过协议关；任一 false → 等同未读协议，reviewer 判 fail）
- `hypotheses[]` 数量 = 本次 run 真实假说数（可能 2 个，可能 6 个），不是固定 4 个
- `charts[]` 数量 = 真实可呈现信号数（可能 1 张，可能 6 张），不是固定 5 张
- `evidence_layers.*.available` 如实反映：某层证据缺失就标 `false`，页面渲染对应 `.evidence-missing` 标记
- `conclusion.type` 驱动 Hero 语气：`DETERMINED` 断言根因；`COMPETING_SET` 显式呈现不确定性 + 天花板；`NEEDS_DATA` 说明尚未收敛
- `process_flow.recoverable=false` → 不渲染 3D，走 Fallback 7/8

### 阶段 3 · 渲染（组件组装 + 视觉语法）

**视觉语法基准：`references/report-template.html`。** 它不是填空模板，而是**设计系统参考**——提供 CSS 变量、排版层级、全部组件类、loader 接线、ECharts/Three.js 多源加载模式。

读取该文件，理解 CSS 变量体系、组件类契约、加载器接线后，按 manifest 组装页面：

1. **直接复用（原样搬运）**：全部 `<style>` 块、loader-strip DOM、ECharts/Three.js 加载基础设施、importmap、@media 断点
2. **按 manifest 选组件**：
   - Hero 恒有 → 用 `conclusion` + `scope` 填 8 元素
   - 3D 仅当 `process_flow.recoverable=true` → 用 `process_flow` 建场景
   - 图表按 `charts[]` 数量逐个渲染（每个 `.chart-panel` + `.chart-reading` 三行）
   - 证据层按 `evidence_layers.*.available` 渲染（缺的层放 `.evidence-missing`）
   - 证据文章按 `hypotheses[]` 数量逐个渲染（每个 `.evidence-article`）
3. **套视觉语法**：所有样式从设计系统参考取类名，禁止臆造新颜色/新组件
4. **绑真实数据**：所有数值/文案/路径来自 manifest（源头是 run_dir 真实 JSON），禁止编造

**禁止**：硬编码设备数量（如"18 辊"）、硬编码假说数、硬编码图表数、把 BOPET 残留数据带进新 run。

## Pre-flight Questions

在写 manifest 前，先写出你对以下问题的内部答案：

**3D 建模前：**
1. 当前诊断对象是哪条产线、哪种工艺、哪个缺陷
2. 真实工段顺序是什么
3. 物料如何从上游流到下游
4. 异常位置对应哪个工段、哪个设备、哪个辊位或区域

**页面规划前：**
1. 用户 10 秒内最该看到什么（主结论一句话）
2. 用户 1 分钟内最该理解什么（位置 + 最强证据）
3. 哪些证据最值得放在主内容区（按 `hypotheses[]` 和 `available_pngs[]` 排序）
4. 哪些信息应该后置，避免干扰理解

答不清就不要进入渲染阶段。

## Hard Requirements

### 1. 页面结构 = manifest 的诚实映射（v3）

页面的段数、卡片数、图表数、证据层数必须与 `render_manifest.json` 一致。manifest 说有 3 个假说，页面就 3 张证据文章；manifest 说统计层 `available:false`，页面该层就放 `.evidence-missing`。**不允许页面结构与 manifest 不符。**

### 2. 视觉语法继承自设计系统参考

`references/report-template.html` 是唯一样式基准。保留其 CSS 变量、排版、组件类、loader、@media。禁止添加新颜色 token、禁止删除 loader、禁止打乱四段顺序。

### 3. 四段叙事（v2 保留）

页面必须严格包含：**0. Hero 结论先行 / 1. 背景与产线建模 / 2. 诊断推理过程 / 3. 证据链三层架构**。详见 `templates/page_blueprint.md`。

### 4. 每条主结论双支撑 + 白话版

每条主结论必须含：(a) 可视化证据（真实 PNG 或 ECharts 图）；(b) 推理证据（统计/物理/排除）；(c) 一句不含统计术语的白话。证据缺失要明确标注，不假装存在。

### 5. 单文件优先

CSS/JS 内联，数据内嵌，本地图像用相对路径 + `onerror` 优雅降级。

### 6. 脚本加载韧性

ECharts/Three.js 必须多源加载（主 CDN + 备用 CDN）+ 加载成功检测 + 初始化成功检测 + 5 项 loader 状态条 + 无库静态降级。加载基础设施直接从设计系统参考复用。

### 7. 3D 场景忠实于工艺

3D 不是"画好看的工业场景"，而是"画符合本次诊断作业逻辑的真实简化场景"。工段顺序/温区/异常落位必须来自 `process_flow`（源头 ontology + 3d_model_data），几何可简化，工艺逻辑不可错。

### 8. 用户理解是硬指标

10 秒知结论/位置/动作；1 分钟知最强证据和排除逻辑；2 分钟知结论怎么来的。

## Evidence Architecture（三层闭合，非平铺）

证据链是三层的，不是卡片墙：

```
第一层 · 统计证据（Ⅰ）        证明"相关"
├── 真实 PNG 散点/相关性图（03_figures 已有）
├── ECharts 重建图（按 charts[] 渲染，数量随数据）
├── 统计证据强度评分条
└── 证据文章：最强存活信号 + 完整统计值

第二层 · 物理机制（Ⅱ）        证明"因果"
├── HTML/CSS 物理因果链（按 physics.chain_steps 渲染）
├── 真实 PNG 剖面图
├── 每步物理方程/量级估算
├── 空间一致性说明
└── 物理证据强度评分条

第三层 · 排除逻辑（Ⅲ）        证明"唯一"
├── 真实 PNG 因果证据图
├── 逐假说证据文章（按 hypotheses[] 数量，每篇含排除理由）
├── 综合判决矩阵表
├── 行动建议优先级表（按 actions[]）
└── 局限性说明
```

**每层必须真实图像/数据/推理三者至少有其二；缺层 → `.evidence-missing` 诚实标记。**

## Evidence Selection Rules

主结论排序优先级：

1. `report.md` 执行摘要和主结论
2. `diagnosis.json` 中 surviving hypotheses / primary finding
3. `evidence.json` 中 rank 3-5 的数值和物理支撑
4. `reasoning_chain.json` 中可解释的收敛路径

不同文件表述不完全一致时：以 `diagnosis.json` + `report.md` 的最终结论为主，页面保持一套统一措辞。

## Image Integration Rules（v2）

对 `03_figures/` 下的 PNG：

1. **优先复用**——这些是诊断管线生成的原始视觉证据，不是装饰
2. **用 `plot_manifest.json` 查询**每张图用途，匹配到正确证据层（散点→统计 / 剖面→物理 / 因果→排除）
3. **`img src` 用相对路径**（从 output HTML 到 run_dir `03_figures/`）
4. **每个 `img` 带 `onerror`** 优雅降级（`onerror="this.parentElement.style.display='none'"`）
5. **每个图下方配 caption**：图编号 + 内容 + 诊断意义

匹配关系写入 `manifest.available_pngs[].suggested_layer`。

## Visual Quality Bar

不要做成：通用后台管理页 / 随手拼接 dashboard / 只有卡片没推理 / 只有图没讲解 / 证据链无真实 figure。

要做成：极简白底 + 衬线标题无衬线正文 / 内容密度高但阅读压力低 / 自上而下建立"结论→位置→推理→证据"理解 / 证据链三层独立展开各有视觉标识。

## Output Checklist

写完 HTML 前逐项确认：

- [ ] `render_manifest.json` 已产出且字段来自真实 JSON（无编造）
- [ ] 页面段数/卡片数/图表数/证据层数与 manifest 一致
- [ ] 四大部分齐全（Hero / 背景 / 推理 / 证据链三层）
- [ ] 证据链三层按 `evidence_layers.*.available` 如实渲染，缺层有 `.evidence-missing`
- [ ] 证据文章数 = `hypotheses[]` 数（非固定值）
- [ ] 图表数 = `charts[]` 数（非固定 5）
- [ ] 3D 仅当 `process_flow.recoverable`，否则降级；3D 工段顺序/异常落位来自真实数据
- [ ] 视觉语法来自设计系统参考（无臆造 token/组件）
- [ ] loader 状态条 5 项 + ECharts/Three.js 多源 + 失败降级
- [ ] 每条主结论双证据 + 白话版
- [ ] 每张图配三行解读
- [ ] 所有数值/路径来自 run_dir 真实产物
- [ ] 10 秒/1 分钟/2 分钟三层理解门槛满足
- [ ] 行动建议 + 局限性齐全
- [ ] `render_manifest.json` 含 `_meta.protocol_ack` 三项 true
- [ ] 输出到 `<run_dir>/diagnostic-report.html`
- [ ] 输出 `<run_dir>/html_selfcheck.json`（8 项 PASS/FAIL + evidence，Step 5 CHECKPOINT 4 产物）
