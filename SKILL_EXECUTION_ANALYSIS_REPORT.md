# Industrial Deep Diagnostic Skill — 执行流程全量分析报告

**版本**: 4.0.0  
**分析日期**: 2026-05-21  
**核心原则**: Evidence first. Reasoning second. Conclusions last.

---

## 一、整体架构概览

### 1.1 主 Agent 的角色：纯粹编排器

主 Agent（Claude）**不持有任何领域上下文**。它只做三件事：

1. 运行固定脚本（Node.js inspect/setup）
2. 按顺序孵化（spawn）5 个子 Agent
3. 向用户展示最终结果

所有工业诊断的专业知识、数据分析、可视化决策、推理逻辑全部下放给子 Agent。主 Agent 的上下文始终保持干净。

### 1.2 子 Agent 之间的解耦机制

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ context-builder │     │ data-processor  │     │  diagnostician  │
│                 │     │                 │     │                 │
│ 写入:           │     │ 写入:           │     │ 读取:           │
│ 01_ontology/    │     │ 02_processed/   │     │ plot_manifest   │
│   ontology.json │     │ 03_figures/*.png │     │ (接口合约)      │
│   schema.json   │     │ plot_manifest   │     │ 所有图像        │
│                 │     │   .json (合约)   │     │ 所有JSON        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │     文件系统通信       │     文件系统通信       │
        └───────────────────────┴───────────────────────┘
```

关键设计：**Agent 之间不共享上下文**。它们仅通过 workspace 文件通信。context-builder 不知道 data-processor 的存在，diagnostician 不知道前面有多少个 Agent。它们只读取约定路径的文件。

### 1.3 Workspace 目录结构（每次诊断运行一个独立目录）

```
workspace/diagnostic-runs/<timestamp>_<name>/
├── 00_input/              ← 数据清单、用户上下文
├── 01_ontology/           ← 过程本体、规范化schema
├── 02_processed/          ← 清洗数据、特征汇总
├── 03_figures/            ← PNG图表 + plot_manifest.json (接口合约)
├── 04_diagnostics/        ← 诊断结论、证据链、置信度
├── 05_review/             ← 评审反馈
├── 06_scripts/            ← Agent 自主编写的 Python 脚本
├── report.md              ← 最终报告
└── run_summary.json       ← 运行元数据
```

---

## 二、完整执行流程（7 步）

### Step 0: Setup Workspace（主 Agent 执行）

主 Agent 调用 Node.js 脚本创建运行时目录：

```bash
node <skill_path>/scripts/setup.mjs --name <scene_name> --base-dir ./workspace/diagnostic-runs
```

`setup.mjs` 做的事：
- 生成 `YYYYMMDDHHmmss_<name>` 格式的 run_id
- 创建 7 个子目录（00_input ~ 06_scripts）
- 写入 `run_manifest.json`（记录每个 step 的状态）

**输出**: `run_manifest.json`（含 run_id 和 run_dir 绝对路径）

---

### Step 1: Inspect Data（主 Agent 执行）

```bash
node <skill_path>/scripts/inspect.mjs <data_path> [--rows N]
```

`inspect.mjs` 做的事（约 150 行，零依赖）：
1. 自动检测分隔符（逗号/制表符/分号）
2. 解析 CSV/JSON/TSV，提取表头和数据行
3. 对每列推断类型：`number` / `datetime` / `string`
4. 对数值列计算：count, missing%, mean, std, min, max, p25, p50, p75
5. 对字符串列计算：count, missing%, unique 数, top 5 值
6. 通过关键词匹配（time/timestamp/datetime/date/ts/时间/时刻）自动检测时间列

**输出 JSON**:
```json
{
  "file": "/absolute/path/to/data.csv",
  "format": "csv",
  "rows": 600,
  "columns": 46,
  "time_column": "timestamp",
  "column_details": [
    {"name": "col1", "index": 0, "type": "datetime", "stats": {...}},
    {"name": "col2", "index": 1, "type": "number", "stats": {"count": 600, "mean": 95.0, "std": 0.5, ...}},
    ...
  ],
  "preview": [{...}, ...]
}
```

然后主 Agent 向用户提问（最多 5 个），只问无法从数据中推断的问题：
- 过程描述
- 已知问题或异常症状
- 目标变量（质量信号）
- 参考文档路径

保存 `input_manifest.json` 和 `user_context.json` 到 `00_input/`。

---

### Step 2: Context Building（子 Agent）

**并行**: 可以和 Step 3 数据处理器 **并行运行**。

主 Agent 读取 `agents/context-builder.md` 并孵化一个子 Agent，传入以下参数：

| 参数 | 含义 |
|------|------|
| `DATA_PATH` | 数据文件路径 |
| `RUN_DIR` | 本次运行的 workspace 目录 |
| `REFERENCE_DIR` | 参考文档目录 |
| `PROCESS_DESCRIPTION` | 用户提供的过程描述 |
| `USER_OBJECTIVE` | 用户的诊断目标 |
| `SKILL_PATH` | skill 安装路径 |

子 Agent 执行 4 个子步骤：

**Step 2.1: 搜索参考目录**
- 递归搜索 REFERENCE_DIR
- 提取：设备名称、过程阶段、变量描述、设定值、已知故障模式、因果关系
- 保存到 `RUN_DIR/references/extracted_knowledge.json`

**Step 2.2: 可选 Web 研究**
- 仅当参考文档不足以理解过程时
- 最多 5 次搜索
- 所有 Web 发现标记为 `[EXTERNAL KNOWLEDGE]`
- 保存到 `RUN_DIR/research/web_findings.md`

**Step 2.3: 构建过程本体**（核心输出）
- 结合用户描述 + 参考文档 + Web 研究 + 数据列名
- 构建 `RUN_DIR/01_ontology/ontology.json`：
  - `scene`: 场景名称、过程类型、设备列表、阶段序列
  - `signals`: 四大类变量（inspection_signals / process_parameters / control_variables / events）
  - `relationships`: 因果/相关/控制/物理关系，每条标记强弱和推理与否
  - `metadata`: 单位、采样率、批次ID

**Step 2.4: 规范化 Schema**
- 原始列名 → 规范名
- 单位归一化
- 保存到 `RUN_DIR/01_ontology/schema.json`

---

### Step 3: Data Processing + Adaptive Visualization（子 Agent）

**并行**: 可以和 Step 2 上下文构建器 **并行运行**。

主 Agent 读取 `agents/data-processor.md` 并孵化一个子 Agent。

这是整个 pipeline 中**最复杂的一步**。子 Agent 需要具备 Python 和数据处理能力，它执行的流程如下：

#### Step 3.1: 数据探查
```bash
node SKILL_PATH/scripts/inspect.mjs DATA_PATH --rows 10 > RUN_DIR/00_input/data_inspection.json
```

#### Step 3.2: 统计分析
```bash
# 转换 CSV 为 JSON
node -e "..."  # 一行 Node 代码转换

# 运行 stats.mjs — 零依赖
node SKILL_PATH/scripts/stats.mjs data.json --time-col <col> --target-cols <cols> --max-lag 30
```

`stats.mjs`（约 145 行）输出：
- **Pearson 相关矩阵**: 所有数值列两两之间的相关系数
- **滞后相关**: 目标列 vs 每个过程参数的带滞后互相关（lag = -30 ~ +30），找到最佳滞后
- **Z-score 异常区间**: 基于前 20% 数据作为基线，|z| > 3 视为异常，合并连续异常点

#### Step 3.3: 数据维度分类（核心决策）

调用 `detect_data_pattern()` 自动分类数据维度：

| 模式 | 判别条件 | 适用场景 |
|------|----------|----------|
| `1d_scalar` | 所有数值列是时间的标量函数（默认） | 大多数传感器数据 |
| `multi_axis` | 列名共享词根带方向后缀 (vib_x/y/z) | 振动、加速度 |
| `2d_profile` | 存在空间/位置列 (zone, width, position) | 膜厚、温度分布 |
| `batch_event` | 存在分类批/阶段列 | 批次生产过程 |
| `spectral` | 存在频率/FFT 列 | 振动频谱分析 |
| `mixed` | 同时匹配多种模式 | 复杂过程（如膜厚+工艺参数） |

#### Step 3.4: 时间对齐策略

| 采样情况 | 处理方式 |
|----------|----------|
| 规则采样、单一频率 | 无需对齐 |
| 不规则采样 | `align_timeindex(df, time_col, method='linear')` |
| 多采样率 | 对齐到最快频率 |
| 缺失时间戳 | 线性插值或前向填充 |

对齐策略记录在 `plot_manifest.json.time_alignment` 中——后续诊断员必须知道数据是否经过重采样。

#### Step 3.5: 选择可视化基元（自适应，非固定模板）

根据分类的模式，从 `scripts/template_visualize.py`（约 1100 行）中选择组合：

**1D Scalar 模式**（最常见）:
- REQUIRED: `plot_multi_panel_timeseries` — 多面板时间序列概览
- REQUIRED: `plot_correlation_heatmap` — Pearson 相关热力图
- IF 3+ 信号: `plot_normalized_overlay` — 归一化叠加对比
- IF 有异常: `plot_anomaly_zoom` — 异常起始点附近放大
- IF 强相关: `plot_coupling_scatter` — 时间着色的散点图

**Multi-Axis 模式**: 以上全部 + `plot_orbit`（轨道图）+ `plot_axis_ratio`（轴比图）

**2D Profile 模式**: `plot_profile_evolution`（剖面演化）+ `plot_position_time_heatmap`（位置×时间热力图）+ `plot_deviation_from_target`（目标偏差图）

**Batch/Event 模式**: `plot_box_by_group`（分组箱线图）+ `plot_event_timeline`（事件时间线）

**Spectral 模式**: `plot_spectrogram`（频谱图）+ `plot_dominant_frequency`（主导频率趋势）

**Mixed 模式**: 组合各子模式的基元。

#### Step 3.6: 编写并执行自定义可视化脚本

子 Agent 将选定的基元组合成一个完整的 Python 脚本，写入 `06_scripts/visualize.py`，然后执行：

```bash
python3 RUN_DIR/06_scripts/visualize.py
```

每个基元函数返回 generation metadata（函数名、参数、归一化方法等），这些元数据最终进入 `plot_manifest.json`。

**错误恢复**: 如果脚本失败，子 Agent 按预定义的表进行恢复（安装缺失包、纠正列名、降采样等），最多重试 3 次。

#### Step 3.7: 写入 Plot Manifest（接口合约）

`write_plot_manifest()` 自动生成 `03_figures/plot_manifest.json`。这是 data-processor 和 diagnostician 之间的**接口合约**：

```json
{
  "data_dimensions": {"type": "mixed", "dimensions": 2, "numeric_count": 46, ...},
  "time_alignment": {"applied": false, "method": "none", ...},
  "anomaly": {"onset_time": "...", "onset_row": 360, ...},
  "plots": [
    {
      "filename": "01_process_timeseries.png",
      "plot_type": "multi_panel_timeseries",
      "description": "4-panel overview with anomaly region shaded",
      "generation_method": {
        "function": "plot_multi_panel_timeseries",
        "panel_count": 4,
        "signals": ["signal_a", "signal_b", ...],
        "anomaly_highlighting": true
      },
      "key_features": "what to look for in this plot",
      "anomaly_highlighted": true
    }
  ],
  "coupling_insights": {
    "primary_cause": "mdo_preheat_z2_temp_c",
    "affected_quality": ["thickness_std_um", "thickness_max_dev_um"],
    "coupling_type": "inverse — temperature drop → thickness increase"
  },
  "interpretation_hints": [
    "Read 01_process_timeseries.png first — overview",
    "Check 03_normalized_overlay.png — temporal coupling",
    ...
  ]
}
```

**为什么这是架构核心**：
- Diagnostician 必须先读 manifest 再看图
- `generation_method` 告诉它每个图是怎么生成的（用了什么对齐、什么归一化）
- `interpretation_hints` 告诉它按什么顺序读图
- 这实现了 Agent 之间的无状态通信——diagnostician 不需要知道 data-processor 的内部决策

#### Step 3.8: 数据预处理

编写并运行 `06_scripts/preprocess.py`，输出清洗后的数据和质量报告。

---

### Step 4: Diagnosis（子 Agent）

主 Agent 读取 `agents/diagnostician.md` 并孵化。

#### Step 4.0: 加载资源

先读取方法论文件：
- `resources/evidence_rules.md` — 7 级证据等级 + 反推测规则
- `resources/diagnosis_method.md` — 5 阶段诊断方法论
- `resources/process_knowledge_base.md` — 常见工业过程知识

再读取数据产物：
- `01_ontology/ontology.json` — 过程本体
- `02_processed/feature_summary.json` — 统计结果（含滞后相关）
- `00_input/data_inspection.json` — 数据探查

#### Step 4.1: 优先读取 Plot Manifest

**必须先读** `03_figures/plot_manifest.json`。这告诉 diagnostician：
- 数据维度分类（知道面对的是什么类型的数据）
- 时间对齐方法（知道图是原始还是重采样数据）
- 每个图的生成方法（用于校准解读置信度）
- 解读顺序提示

#### Step 4.2: VLM 解读每个图

对 manifest 中列出的每个 PNG 图，用 Read 工具查看图像，结合 `generation_method` 校准解读：
- 如果 `normalization: "min-max [0,1]"` → 叠图显示相对时序，非绝对值
- 如果 `time_alignment: "linear interpolation"` → 小间隙被填补，不过度解读插值区
- 如果 `function: "plot_orbit"` → 轨道形状揭示单一故障源 vs 多故障源
- 如果 `function: "plot_spectrogram"` → 频率内容随时间变化

每个图回答：
1. 趋势形状（线性漂移/阶跃/振荡/尖峰/S 曲线）
2. 哪个信号**最先**从基线偏离
3. 信号之间的相对时序
4. 信号是否耦合（归一化后形状相同 vs 独立）

#### Step 4.3-4.4: 观测与综合证据

从实际数据中提取精确数值，用 `[OBSERVATION]` 标记。

**关键：滞后相关优先分析**。从 `feature_summary.json.lagged_correlations` 开始：
1. 对每个目标变量，找到 |r| 最强的过程参数
2. 检查 `lag_periods` — 正滞后 = 过程先变（因果证据），负滞后 = 过程后变（排除因果）
3. Lag = 0 结合视觉证据判断更细粒度的时序
4. 建立"谁先动、谁后动"的完整时序链

#### Step 4.5: 假设形成

列出所有合理假设，每个包括：
- 物理机制（可解释的工程原理）
- 支持性证据（含 Rank + 来源）
- 矛盾性证据
- 可测试的预测

#### Step 4.6: 置信度评估

每个假设 0-100 分。高中低四个等级。

**输出文件（3 个 JSON）**:
- `04_diagnostics/diagnosis.json` — 完整诊断，含因果链和假设
- `04_diagnostics/evidence.json` — 结构化证据（visual/numerical/domain 三类）
- `04_diagnostics/confidence.json` — 每个假设的置信度细分

---

### Step 5: Judge Review（子 Agent + 自动修复循环）

主 Agent 读取 `agents/judge.md` 并孵化。

#### 评分体系（10 个维度，加权）

| # | 维度 | 权重 | 说明 |
|---|------|------|------|
| 1 | 数据质量 | 15% | 数据加载正确？缺失值处理？ |
| 2 | 变量分类 | 10% | 所有变量分类一致？ |
| 3 | 时间对齐 | 10% | 对齐方法恰当？无伪影？ |
| 4 | 可视化质量 | 10% | 标签/单位/图例完整？ |
| 5 | 证据驱动结论 | **25%** | 每个结论引用证据源？ |
| 6 | 相关 vs 因果 | 10% | 不混淆相关和因果？ |
| 7 | 不确定性披露 | 10% | 置信度和证据缺口明确？ |
| 8 | 报告质量 | 10% | 语言模板使用正确？ |
| 9 | 不过度断言 | **BLOCKING** | 无证据不声称根因，每违反扣 20 分 |
| 10 | 完整性 | 5% | 所有必需产物存在？ |

#### 判定

| 分数 | 判定 | 处理 |
|------|------|------|
| 90-100 | PASS | 进入 Step 6 报告生成 |
| 70-89 | NEEDS_REPAIR | 重新孵化 diagnostician，传入修复指令 |
| 50-69 | MAJOR_ISSUES | 报告严重问题给用户 |
| 0-49 | FAIL | 报告给用户，无法自动修复 |

#### 自动修复循环

```
Judge 写入 judge_feedback.json
       ↓
如果 NEEDS_REPAIR (70-89):
  → 读取 blocking_issues[].repair_instruction
  → 重新孵化 diagnostician，prompt 末尾附上修复指令
  → 重新评分
  → 最多 3 轮
  → 3 轮后若仍不通过，带警告进入 Step 6
```

`repair_instruction` 字段是自动化的关键——它包含精确的修复指示：
```json
{
  "description": "Evidence rank not cited for thickness-melt pressure correlation",
  "repair_instruction": "Re-analyze the melt pressure evidence in diagnosis.json step 3. Add explicit evidence rank (Rank 1) and source (melt_pressure_mpa time-series at rows 360-600).",
  "affected_steps": ["step_4"]
}
```

---

### Step 6: Report Generation（子 Agent）

主 Agent 读取 `agents/reporter.md` 并孵化。

Reporter 加载所有之前产生的人工制品，生成两样东西：

**`report.md`**（16 个章节的完整工程诊断报告）:
1. Executive Summary
2. Analysis Objective
3. User Context
4. Industrial Context
5. Reference Documents Used
6. External Research
7. Data Description（含完整表格）
8. Variable Classification
9. Preprocessing & Alignment
10. Visualization Interpretation
11. Diagnostic Findings（每个异常区间独立分析）
12. Root Cause Analysis
13. Confidence & Uncertainty
14. Recommended Actions（优先级排序表格）
15. Limitations
16. Appendix（运行配置、统计汇总等）

**`run_summary.json`** — 运行的元数据摘要

**写作标准**：
- 技术严谨，适合工程同行评审
- 每个结论引用证据源和等级
- `[OBSERVATION]` / `[INFERENCE]` / `[HYPOTHESIS]` / `[UNCERTAINTY]` 标记一致
- 精确数字 + 单位（"增加 8%" 而非 "上升很多"）

---

### Step 7: Present Results（主 Agent）

主 Agent 向用户展示：
- 执行摘要
- 关键发现
- 主要诊断
- 最佳建议
- Workspace 路径

---

## 三、核心设计决策

### 3.1 证据等级体系（7 级）

| Rank | 来源 | 置信度 |
|------|------|--------|
| 1 | 提供数据中的直接测量 | 最高 |
| 2 | 用户提供的文档（SOP、手册） | 高 |
| 3 | 数据统计分析 | 中高 |
| 4 | 图表的视觉证据 | 中 |
| 5 | 成熟的过程逻辑/领域知识 | 中 |
| 6 | 外部 Web 参考 | 低 |
| 7 | 假设（无支持） | 最低 |

每个非观察性陈述必须引用证据等级。从多等级得出的结论受限于最弱的等级。

### 3.2 反推测规则

**禁止**:
- 缺少时间优先 + 统计证据 + 物理机制 + 无矛盾的因果声明
- 对未测量的变量做假设
- 混淆相关和因果

**必须**:
- 披露每个结论的置信度
- 标记证据不充分的地方
- 分离数据推导和领域知识推理

### 3.3 因果断言的四标准

要声明 "X 导致 Y" 需要**全部**四项：
1. **时间优先**: X 在 Y 之前变化（有测量的滞后）
2. **统计显著**: 强相关（|r| > 0.7）且滞后正确
3. **物理机制**: 来自过程逻辑的可信解释
4. **无矛盾**: 没有证据抵触此因果声明

缺少任何一项 → 使用 `[HYPOTHESIS]` 语言。

### 3.4 语言标记体系

| 标记 | 含义 | 模板 |
|------|------|------|
| `[OBSERVATION]` | 直接测量事实 | "[Variable] 从 [T1] 到 [T2] [变化]了 [X%]" |
| `[INFERENCE]` | 基于证据的推理 | "这与 [event/measurement] 同时发生" |
| `[HYPOTHESIS]` | 推测性解释 | "这表明 [mechanism] 可能有贡献" |
| `[UNCERTAINTY]` | 不确定性声明 | "证据 [level] 不足以 [conclude X]" |

### 3.5 技术选型哲学

```
Node.js 脚本 (3 个)         Python 工具包 (2 个)
├── 固定操作                ├── 自适应、Agent 决策
├── 零依赖                  ├── matplotlib + pandas + numpy
├── 总是能运行              ├── Agent 根据数据维度选择基元
└── inspect/stats/setup     └── visualize/preprocess
```

### 3.6 Schema 体系（8 个 JSON Schema）

每个 Agent 产生的 JSON 都有对应的 JSON Schema draft-07 用于验证：

| Schema | 验证的对象 | 使用者 |
|--------|-----------|--------|
| `ontology_schema.json` | 过程本体 | context-builder |
| `signal_schema.json` | 信号分类和映射 | context-builder |
| `run_config_schema.json` | 运行配置 | setup |
| `analysis_schema.json` | 统计分析输出 | data-processor |
| `diagnosis_schema.json` | 诊断输出 | diagnostician |
| `evidence_schema.json` | 结构化证据 | diagnostician |
| `confidence_schema.json` | 置信度评分 | diagnostician, judge |
| `report_schema.json` | 报告结构 | reporter |

---

## 四、子 Agent 创建与执行机制

### 4.1 孵化方式

主 Agent 通过 Claude Code 的 Agent 工具孵化每个子 Agent：

```
主 Agent:
  1. Read agents/<agent-name>.md  →  读取 Agent 的 prompt 文件
  2. 替换模板参数 ({{DATA_PATH}}, {{RUN_DIR}}, ...) → 填充具体值
  3. Agent(subagent_type="general-purpose", prompt=agent_prompt_with_params)
     → 孵化子 Agent，子 Agent 拥有独立的上下文窗口
  4. 子 Agent 读取文件、执行命令、写入产物
  5. 子 Agent 返回执行结果给主 Agent
```

关键：子 Agent 之间**不共享上下文**。它们只通过 workspace 文件通信。这确保主 Agent 的上下文不会因累积大量诊断领域信息而膨胀。

### 4.2 并行与串行

```
Step 0: setup        ─┐
Step 1: inspect      ─┤ 主 Agent 直接执行（不孵化子 Agent）
                       │
Step 2: context-builder ─┐
                          ├─ 可并行
Step 3: data-processor ─┘
                       │
Step 4: diagnostician ─┤
Step 5: judge          ─┤ 串行（有依赖关系）
Step 6: reporter       ─┤
                       │
Step 7: present       ─┘ 主 Agent 直接执行
```

### 4.3 自动修复循环（Judge → Diagnostician 反馈）

```
┌──────────────┐     judge_feedback.json      ┌────────────────┐
│    Judge     │ ──────────────────────────►  │ Diagnostician  │
│  (评审员)    │   blocking_issues[n].         │  (重新孵化)     │
│              │   repair_instruction          │                │
└──────────────┘                               └────────────────┘
       ▲                                              │
       │         诊断员修复后重新提交                    │
       └──────────────────────────────────────────────┘
                   (最多 3 轮)
```

---

## 五、命令体系

| 斜杠命令 | 功能 | 执行路径 |
|----------|------|----------|
| `/industrial-deep-diagnostic` | 完整 pipeline | Step 0 → 1 → 2+3 → 4 → 5 → 6 → 7 |
| `/industrial-deep-diagnostic analyze` | 跳过用户交互 | 从 Step 2 开始 |
| `/industrial-deep-diagnostic review` | 重新评审 | 在已有结果上重新运行 Judge |
| `/industrial-deep-diagnostic report` | 重新生成报告 | 从已有产物重新生成 report.md |

---

## 六、评估结果

当前版本 (v4.0.0) 在 3 个 eval 上得分：

| 评估项 | 通过率 | 说明 |
|--------|--------|------|
| inspect.mjs 数据探查 | 100% (6/6) | 列类型推断和时间列检测完美 |
| stats.mjs 相关分析 | 100% (6/6) | Pearson 相关与真实值误差 < 0.015 |
| stats.mjs 异常检测 | 83.3% (5/6) | 1 个假阳性：低方差基线使 z-score 过于敏感 |
| **综合** | **94.4% (17/18)** | |

已知问题：z-score 异常检测在基线方差极低时会产生假阳性。建议添加最小偏差阈值（如基线均值的 5%）作为二次过滤器。

---

## 七、实战案例：PET Film MDO 诊断运行

以 `workspace/diagnostic-runs/202605211034380_pet_film_mdo/` 为例：

- **数据结构**: 600 行 × 46 列，10 秒采样。包含 13 个过程参数（挤出机温度、MDO 预热区温度、拉伸比等）+ 30 个厚度测量点（膜宽方向 0-290mm，每 10mm 一个测点）
- **数据维度分类**: `mixed` — 1D 标量过程参数 + 2D 膜宽剖面
- **生成图表**: 7 张 PNG（含 4 面板时间序列、相关热力图、归一化叠图、异常放大、剖面演化、位置×时间热力图、目标偏差图）
- **诊断**: MDO 预热区 2 加热器退化（置信度 95%）→ 膜厚标准差增加 141% → 次生熔体压力升高
- **关键证据**: mdo_preheat_z2_temp_c 与 thickness_mean_um 的 r=-0.9866，Lag=0（瞬时热-厚耦合）
