# Industrial-Deep-Diagnostic Skill 评估报告

**评估日期**: 2026-06-02
**评估者**: Skill Creator framework + 人工审计
**Skill 路径**: `.claude/skills/industrial-deep-diagnostic/`
**Skill 总文件数**: 65 (排除 venv site-packages)

---

## 1. 总体评分

| 维度 | 评分 | 说明 |
|------|:---:|------|
| **硬编码消除** | 7.5/10 | 脚本层已完成零硬编码，但 templates 和 agents 中仍有 BOPET/CNC 示例残留 |
| **场景适应性** | 7.0/10 | L1-L5 推理阶梯是核心适应机制，但 knowledge base 偏向已知工业类型 |
| **物理检查覆盖** | 6.5/10 | 7种物理检查覆盖常见场景，但缺失张力/湿度/电气/尺寸等通用物理检查 |
| **输出一致性** | 8.0/10 | Schema-First Writing Protocol 解决了主要的 schema 验证失败问题 |
| **RAG 集成** | 6.0/10 | RAG 是可选的加速，不是硬依赖。但 RAG 引擎的 ChromaDB 持久化 bug 未修复 |
| **综合评分** | **7.0/10** | 良好的工业诊断框架，适用性仍需改进 |

---

## 2. 硬编码审计（全文件扫描结果）

### 2.1 已完成零硬编码 ✅

| 文件类别 | 状态 |
|---------|:---:|
| `scripts/physics_check.py` | ✅ 0 CNC 术语，CLI 参数接收所有列名 |
| `scripts/stats_analysis.py` | ✅ 0 BOPET 关键词，--target-cols CLI 参数 |
| `scripts/inspect.mjs` | ✅ 0 领域专用词 |
| `scripts/convert.mjs` | ✅ 0 领域专用词 |
| `scripts/stats.mjs` | ✅ 0 领域专用词 |
| `schemas/*.json` (11文件) | ✅ 全领域通用 |
| `evals/evals.json` | ✅ 预期的测试用例内容 |

### 2.2 需要修复的硬编码 ⚠️

#### CRITICAL: `templates/diagnosis_template.json` (29 处 BOPET 硬编码)

| 硬编码 | 行号 | 应替换为 |
|--------|:---:|---------|
| `"BOPET 膜厚偏差由 TDO zone-3..."` | 5 | `"{{primary_finding_summary}}"` |
| `["PET_12um","PET_23um","PET_50um"]` | 9 | `["{{product_1}}","{{product_2}}","{{product_3}}"]` |
| `"TDO_zone3_temp"` (参数名) | 12,79 | `"{{parameter_name}}"` |
| `"PET_12um"/"PET_23um"/"PET_50um"` (产品名) | 15-17,26-28 | `"{{grade_name}}"` |
| `"extruder_pressure"` (参数名) | 23 | `"{{parameter_name}}"` |
| `"加热元件电阻随时间上升..."` (物理链) | 46-59 | 保留为示例说明 |
| `"TDO zone-3 加热器性能退化"` (假设名称) | 41 | 保留为示例说明 |

**影响**: Diagnosis 模板被用于引导诊断师产出格式。全部示例都是 BOPET 场景会导致模型偏差——对非膜类过程可能输出 BOPET 风格的诊断结构。

**建议**: 将模板改为抽象 {{parameter_name}}、{{product_name}} 等占位符，附加一个独立的 `templates/example_bopet.json` 作为纯示例。

#### MODERATE: `agents/diagnostician.md` (Phase 1.5 示例均为 CNC/振动)

| 硬编码 | 行 | 问题 |
|--------|:---:|------|
| `"spindle_vibration_mm_s"` | 316 | CNC 专用参数名 |
| `"ISO 10816-1 + forced oscillator"` | 320 | 振动专用标准 |
| `"roughness ∝ vibration amplitude"` | 321 | 加工专用公式 |
| `"Preston (CMP)"` | 179 | 半导体 CMP 专用 |
| `"0.028 μm per mm/s"` | 283 | CNC 专用量级 |

**影响**: 这些是 Level 2 物理定律选择表和 Phase 1.5 证明构造模板中的示例。虽然是说明性的，但全部偏向 CNC/振动场景。对于化学过程、制药、食品加工等场景，缺乏相应的示例。

**建议**: 在示例中增加至少 2-3 个不同场景的等价示例（如热交换器、反应器、涂层）。

#### MODERATE: `templates/diagnosis_template.json` 的 BOPET 物理链

第 38-107 行（H1: TDO zone-3 加热器退化）和第 109-171 行（H2: 树脂 MFI 批次波动）的物理链全部是 BOPET 专用。这些是模板示例数据，但过于具体。

#### MINOR: 其他文件中的示例术语

| 文件 | 术语 | 上下文 | 严重度 |
|------|------|--------|:---:|
| `diagnostician.md:278` | "spindle vibration" | 证明构造示例 | 🟡 |
| `data-processor.md:43` | "conversion, yield, selectivity" | 派生特征示例列表 | 🟢 (通用化学术语) |
| `data-processor.md:111` | "fouling_resistance" | 热交换器示例 | 🟢 (通用热力学术语) |
| `report_template.md:120` | "film_points vs MD_TH009" | 表格示例数据 | 🟡 (应使用通用示例) |
| `physics_inference_framework.md` | "ISO 10816", "Preston (CMP)" | Level 2 定律选择表 | 🟡 |

---

## 3. 场景适应性评估

### 3.1 已覆盖的物理检查 (physics_check.py)

| 检查函数 | 覆盖的物理现象 | 覆盖的行业 |
|---------|-------------|-----------|
| `check_thermal_expansion` | 热膨胀 → 尺寸变化 | 🏭 任何含热+尺寸的系统 |
| `check_arrhenius` | 温度 → 反应/降解速率 | 🏭 化学、材料降解 |
| `check_vibration_threshold` | 振动 → 质量 | 🔧 旋转设备 |
| `check_energy_balance` | 功率 → 温度 | 🏭 任何含加热的系统 |
| `check_flow_restriction` | 流量 → 压降 | 🏭 流体系统 |
| `check_heat_transfer` | 热交换器结垢 | 🏭 热交换器 |
| `check_corrosion_rate` | pH → 腐蚀 | 🏭 化工、水处理 |

### 3.2 缺失的物理检查 ❌

| 缺失的检查 | 为什么重要 | 可能覆盖的行业 |
|-----------|---------|--------------|
| **张力/力平衡** (通用) | 张力+厚度→滑移→划痕 | 卷材、纺织、印刷、线缆 |
| **湿度/水分效应** | 水分→静电/吸湿→质量缺陷 | 制药、食品、造纸、纺织 |
| **电气参数退化** | R↑→P↓→T↓ (加热带退化) | 任何带电加热的工业过程 |
| **尺寸/间隙直接关系** | gap→thickness (模口→铸片) | 挤出、压延、涂层、印刷 |
| **反应速率/产率** | 浓度×温度→产率 | 化工、制药、食品加工 |
| **过滤/堵塞趋势** | ΔP_filter ∝ t 锯齿波 | 过滤系统、水处理 |

### 3.3 Knowledge Base 覆盖的行业

| 行业 | 详细程度 | 定量公式数 |
|------|:---:|:---:|
| BOPET/BOPP 膜生产 | ⭐⭐⭐⭐⭐ 极详细 | ~15 条 |
| 挤出工艺 | ⭐⭐⭐⭐ 详细 | ~5 条 |
| 注塑成型 | ⭐⭐⭐⭐ 详细 | ~15 条 |
| 化学反应器 | ⭐⭐⭐⭐ 详细 | ~15 条 |
| 半导体 CMP | ⭐⭐⭐⭐ 详细 | ~18 条 |
| 锂电池 | ⭐⭐⭐⭐ 详细 | ~15 条 |
| 旋转设备 | ⭐⭐⭐ 中等 | ~5 条 |
| 涂层工艺 | ⭐⭐ 简要 | 0 条定量 |
| 燃烧过程 | ⭐⭐ 简要 | 0 条定量 |
| 制药/生物 | ⭐ 无 | 0 条 |
| 食品加工 | ⭐ 无 | 0 条 |
| 水处理 | ⭐ 无 | 0 条 |
| 印刷/包装 | ⭐ 无 | 0 条 |
| 纺织/纤维 | ⭐ 无 | 0 条 |
| 采矿/选矿 | ⭐ 无 | 0 条 |
| 水泥/建材 | ⭐ 无 | 0 条 |
| 冶金/铸造 | ⭐ 无 | 0 条 |
| 造纸 | ⭐ 无 | 0 条 |

### 3.4 跨场景适应机制分析

```
┌─────────────────────────────────────────────────┐
│         适应机制           │     有效范围       │
├─────────────────────────────────────────────────┤
│ L1-L5 物理推理阶梯         │ ⭐⭐⭐⭐⭐ 核心层  │
│   (第一原理物理推导)        │ 任何场景通用       │
│                             │                   │
│ 数据自描述                   │ ⭐⭐⭐⭐ 很强     │
│   (列名→物理量→定律)        │ 大部分场景         │
│                             │                   │
│ RAG 知识检索                 │ ⭐⭐⭐ 中等       │
│   (外部领域知识补充)         │ KB 覆盖的场景     │
│                             │                   │
│ physics_check 自动验证       │ ⭐⭐ 偏弱         │
│   (当前仅7种检查+1种已删)    │ 旋转设备/热/流/腐蚀│
│                             │                   │
│ process_knowledge_base 参考  │ ⭐⭐⭐ 偏详细     │
│   (显式覆盖9个行业)          │ 覆盖的9个行业     │
└─────────────────────────────────────────────────┘
```

### 3.5 跨行业诊断能力预测

| 过程类型 | 列名推断 | 物理推理 | 知识库支持 | 自动检查 | **综合评级** |
|---------|:-----:|:-----:|:-----:|:-----:|:------:|
| BOPET/BOPP 膜 | ✅ | ✅ 强 | ✅ 极强 | ⚠️ 部分 | **⭐⭐⭐⭐⭐** 最优 |
| CNC 加工 | ✅ | ✅ 强 | ⚠️ 隐含 | ⚠️ 振动/力已删 | **⭐⭐⭐⭐** 良好 |
| 注塑成型 | ✅ | ✅ 强 | ✅ 强 | ⚠️ 部分 | **⭐⭐⭐⭐** 良好 |
| 化工反应器 | ✅ | ✅ 强 | ✅ 强 | ⚠️ 阿伦尼乌斯 | **⭐⭐⭐⭐** 良好 |
| 换热器结垢 | ✅ | ✅ 强 | ⚠️ 隐含 | ✅ 传热/流 | **⭐⭐⭐⭐** 良好 |
| 半导体 CMP | ✅ | ⚠️ 需推导 | ✅ 强 | ❌ Preston已删 | **⭐⭐⭐** 可接受 |
| 锂电池涂层 | ⚠️ 部分 | ⚠️ 需推导 | ✅ 强 | ❌ 无 | **⭐⭐⭐** 可接受 |
| 纺织/纤维 | ⚠️ 部分 | ⚠️ 需推导 | ❌ 无 | ❌ 无 | **⭐⭐** 较弱 |
| 水处理/过滤 | ⚠️ 部分 | ✅ 强 | ❌ 无 | ⚠️ 腐蚀 | **⭐⭐** 较弱 |
| 食品加工 | ⚠️ 部分 | ⚠️ 需推导 | ❌ 无 | ❌ 无 | **⭐** 弱 |
| 制药 | ❌ 弱 | ❌ 需专家 | ❌ 无 | ❌ 无 | **⭐** 弱 |
| 采矿/选矿 | ❌ 弱 | ⚠️ 可尝试 | ❌ 无 | ❌ 无 | **⭐** 弱 |

---

## 4. 关键发现

### 发现 1: Template 是最大的硬编码源 🔴

`templates/diagnosis_template.json` 的 80% 内容是 BOPET 特定的。这不是示例——这是 **模板**。代理会直接按此模板构造诊断输出。所有行业都会看到 BOPET 样式的诊断结构。

**修复难度**: 低（1小时）。将 BOPET 数据替换为 `{{parameter_name}}` 类占位符。

### 发现 2: 物理检查覆盖不足 🟡

当前 physics_check.py 只有 7 种检查（CNC 力平衡函数刚被删除）。缺失通用检查使得大数据集（如 BOPET: 12×温度+5×间隙+挤出参数）执行 0 次检查。Diagnosis 师必须手动执行 L1-L5 推理——这在统计和物理上都是正确的，但速度慢且容易遗漏。

**修复难度**: 中（2-3小时）。添加 `check_electrical_degradation`（加热带 R(t)）、`check_gap_dimension_coupling`、`check_tension_thickness_coupling` 等通用检查。

### 发现 3: Process Knowledge Base 存在行业偏差 🟡

9 个行业有详细覆盖，其余只有 26 条"通用"物理原则（Arrhenius、Fourier、Bernoulli...）。LLM 必须从这些原则中推导特定行业的物理公式——有时候这是可行的，有时不行。

**修复难度**: 中高（但不需要一次完成）。可以像 `process_knowledge_base.md` 那样渐进添加更多行业。

### 发现 4: 示例严重偏向 CNC/振动 🟡

Phase 1.5（证明构造）中的所有定量示例都使用 `spindle_vibration_mm_s`。Level 2 物理定律表中的示例包括 `Preston (CMP)` 和 `ISO 10816`。虽然不是硬编码逻辑，但会对 LLM 产生明显的提示偏差。

**修复难度**: 低。在示例中混入不同场景。

### 发现 5: RAG 集成不可靠 🔴

ChromiumDB 持续存在一个已知的 bug—— `parameter_to_physics.json` 索引错误（`name 'json' is not defined`）且 `kb_ready: false`。RAG fallback（"building ontology from scratch"）始终触发。这实际上使 RAG 成为一个无操作。

**修复难度**: 中。修复 ChromaDB JSON 加载 bug + 验证持久化是否正常工作。

---

## 5. 修复优先级

| 优先级 | 问题 | 影响 | 修复工作量 |
|:---:|------|------|:---:|
| **P0** 🔴 | `diagnosis_template.json` BOPET 硬编码 | 所有行业的诊断输出都被 BOPET 模板结构污染 | 1小时 |
| **P1** 🟡 | `diagnostician.md` 示例偏差（CNC/振动） | 非机械/振动场景的诊断推理存在提示偏差 | 30分钟 |
| **P2** 🟡 | `physics_check.py` 缺失通用检查 | 0次自动检查 → diagnosis 师必须手动计算 | 3小时 |
| **P3** 🟡 | `report_template.md` 示例术语 | 报告模板引导的轻微偏差 | 15分钟 |
| **P4** 🟠 | RAG 集成不可靠 | RAG fallback 始终启用（非阻塞但浪费机会） | 2小时 |
| **P5** 🟠 | Knowledge base 行业覆盖 | 8/16 行业有详细覆盖，另外 8 个缺失 | 持续进行 |

---

## 6. 结论

`industrial-deep-diagnostic` skill 是一个**结构良好的工业诊断框架**，物理基础坚实（L1-L5 推理阶梯），统计验证严谨（Simpson's Paradox、去趋势、分层），证据体系完善（7 级证据层级）。脚本层已实现零硬编码。

**当前最关键的问题**是 `templates/diagnosis_template.json` 中残留的 BOPET 硬编码——这使得诊断模板对非 BOPET 场景会产生偏差。第二大问题是物理检查覆盖——丢失 1 个函数（CNC force_balance）、其余 7 个中有 5 个在 BOPET 场景执行 0 次。

**场景适应性评分**：在膜/挤出/加工/反应器/换热器场景下良好（7-9/10），在锂电池/半导体场景下可接受（5-6/10），在纺织/食品/制药/采矿场景下较弱（2-4/10）。能够诊断任何工业过程的说法在理论上成立（通过 L1-L5 推理），但在实践中 knowledge base 的覆盖偏差会拖慢较冷门行业的诊断质量。
