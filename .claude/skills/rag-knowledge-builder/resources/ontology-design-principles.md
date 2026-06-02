# Ontology Design Principles — Natural Language Ontology Quality Standard

> 本文件定义了一个好的本体模型在自然语言层面必须满足的设计原则。
> 这是 Phase 2 本体构建 agent 的核心参考标准。

---

## 1. 概念精确性 (Concept Precision)

### 原则
每个概念有且仅有一个精确的自然语言定义。定义必须：
- **唯一性**：在该本体范围内，没有其他概念有相同的含义
- **消歧义**：明确指出该概念"不是什么"，避免与相似概念混淆
- **可操作**：一个领域专家读完定义后能判断任何实例是否属于该概念

### 反模式
```
❌ "温度" — 太模糊：什么温度？在哪里？什么条件下？
❌ "反应温度，单位摄氏度" — 缺少物理含义，只是复述了名称
❌ "主轴温度" — 没说清是轴承温度、电机绕组温度还是主轴表面温度

✅ "主轴前轴承外圈温度 (°C) — 反映主轴轴承运行状态的关键指标。
   正常范围 20-70°C；>80°C 预示润滑失效或过载；
   >90°C 需立即停机。与电机绕组温度 (winding_temp_C) 不同，
   后者反映电机发热而非轴承状态。"
```

```
✅ "HbA1c (糖化血红蛋白百分比, %) — 反映过去 2-3 个月平均血糖水平的指标。
   与空腹血糖 (fasting_glucose_mg_dl) 不同：HbA1c 反映长期趋势而非瞬时值。
   正常 <5.7%；5.7-6.4% 为糖尿病前期；≥6.5% 为糖尿病诊断阈值。
   在贫血或血红蛋白病患者中可能不准确。"
```

### 检验方法
对于每个概念定义，问三个问题：
1. **领域专家能区分它和相似概念吗？** 如果不能 → 定义不够精确
2. **定义中有"等"、"大概"、"类似"吗？** 如果有 → 消歧义不充分
3. **读完定义后能判断一个实例是否属于该概念吗？** 如果不能 → 定义太模糊

---

## 2. 层次完整性 (Hierarchical Completeness)

### 原则
核心概念必须有 IS-A（分类层次）和 PART-OF（组成层次）关系。层次结构必须：
- **覆盖核心概念**：每个重要概念至少出现在一个层次链中
- **避免孤立节点**：没有概念完全游离于层次结构之外
- **区分 IS-A 与 PART-OF**：IS-A 是"是一种"，PART-OF 是"是...的一部分"
- **避免过深层次**：一般不超过 4 层（根→子→孙→叶），更深的层次应扁平化

### IS-A 层次 (Taxonomy)
```
IS-A 层次表达概念的分类关系：

工业领域示例:
  物理量
  ├── 温度量
  │   ├── 熔体温度 (melt_temp_C)
  │   ├── 轴承温度 (bearing_temp_C)
  │   └── 环境温度 (ambient_temp_C)
  ├── 振动量
  │   ├── 轴承振动速度 (bearing_vib_mm_s)
  │   └── 结构振动加速度 (structure_vib_g)
  └── 流量
      ├── 冷却水流量 (coolant_flow_L_min)
      └── 进料流量 (feed_rate_L_min)

医学领域示例:
  生物标志物
  ├── 血糖相关标志物
  │   ├── 空腹血糖 (fasting_glucose_mg_dl)
  │   ├── HbA1c (hba1c_pct)
  │   └── 餐后血糖 (postprandial_glucose_mg_dl)
  ├── 心血管标志物
  │   ├── 血压 (blood_pressure_mmhg)
  │   └── 心率 (heart_rate_bpm)
  └── 肾功能标志物
      ├── eGFR (egfr_ml_min)
      └── 肌酐 (creatinine_mg_dl)
```

### PART-OF 层次 (Mereology)
```
PART-OF 层次表达组成关系：

工业领域示例:
  CNC 加工系统
  ├── 主轴系统
  │   ├── 主轴轴承
  │   ├── 主轴电机
  │   └── 冷却系统
  ├── 进给系统
  │   ├── X 轴驱动
  │   ├── Y 轴驱动
  │   └── Z 轴驱动
  └── 刀具系统
      ├── 刀柄
      └── 刀片

医学领域示例:
  2 型糖尿病管理
  ├── 血糖监测
  │   ├── HbA1c 检测
  │   ├── 空腹血糖检测
  │   └── 持续血糖监测 (CGM)
  ├── 药物治疗
  │   ├── 二甲双胍
  │   ├── SGLT2 抑制剂
  │   └── 胰岛素
  └── 生活方式干预
      ├── 饮食管理
      └── 运动处方
```

### 反模式
```
❌ 所有概念平铺在一个列表里，没有任何层次关系
❌ IS-A 和 PART-OF 混淆（"主轴 IS-A CNC" 是错的，"主轴 PART-OF CNC系统" 是对的）
❌ 层次太深（5层以上）：工业过程 → 聚合物加工 → 薄膜拉伸 → 双向拉伸 → MDO拉伸 → MDO温度 → T1区温度
✅ 适当扁平化：工业过程 → 薄膜拉伸 → MDO温度 (含 T1-T12 各温区的说明)
```

---

## 3. 关系语义丰富性 (Relationship Semantic Richness)

### 原则
每个关系不仅有 `from → to` 方向，还必须有：
- **关系类型**：精确的语义类型（不只是 "related_to"）
- **机制描述**：用 2-3 句自然语言解释为什么存在这种关系
- **方向性**：明确因果方向、时序方向或逻辑方向
- **基数约束**：一对一、一对多、多对多
- **条件约束**：在什么条件下关系成立
- **时滞**：原因和效果之间的时间延迟
- **强度/置信度**：这个关系有多确定

### 关系类型分类

| 类型 | 语义 | 自然语言模式 | 示例 |
|------|------|-------------|------|
| `causal` | 直接物理/生物因果 | "X 导致 Y，因为..." | "轴承磨损导致振动增大，因为..." |
| `correlative` | 统计关联（无因果证据） | "X 与 Y 相关，相关方向为..." | "BMI 与 HbA1c 正相关" |
| `physical` | 物理定律约束 | "根据 [定律]，X 决定 Y" | "根据 Arrhenius 方程，温度决定反应速率" |
| `control` | 控制回路 | "X 是 Y 的控制变量" | "PID 控制器调节冷却水流量以维持温度设定值" |
| `temporal` | 时序/演化 | "X 先于 Y 发生" | "进料变化先于出口温度变化约 5 分钟" |
| `compositional` | 组成关系 | "X 是 Y 的组成部分" | "主轴轴承是主轴系统的组成部分" |
| `classificational` | 分类关系 | "X 是 Y 的一种" | "HbA1c 是血糖相关生物标志物的一种" |
| `conditional` | 条件依赖 | "在 Z 条件下，X 影响 Y" | "在高温条件下(>85°C)，拉伸比增加导致雾度上升" |
| `regulatory` | 监管/法规 | "法规/标准要求 X 限制 Y" | "ISO 10816 要求振动速度 <4.5mm/s" |
| `definitional` | 定义性 | "X 被定义为 Y" | "转化率被定义为(进料-出料)/进料 × 100%" |
| `statistical` | 统计模型 | "统计模型预测 X → Y" | "Logistic 回归模型预测债务收入比 → 违约概率" |
| `precedential` | 先例/参考 | "先例 X 指导 Y" | "Delaware 法院的先例指导赔偿条款的可执行性" |

### 反模式
```
❌ "温度 → 质量" — 没有机制，没有方向性，没有条件
❌ "spindle_vib → roughness (related)" — "related" 不是关系类型
❌ "HbA1c 影响血糖" — 因果方向反了（血糖影响 HbA1c）

✅ "melt_temp_C →(causal)→ melt_viscosity_Pa_s →(causal)→ draw_stability
     机制: PET 熔体粘度遵循 Arrhenius 型温度依赖性。
          温度升高 → 粘度降低 → 熔体强度下降 → 拉伸不稳定 → 厚度波动。
          该链在 270-290°C 范围内有效；低于 270°C 会出现未熔融粒子（不同机制）。
     时滞: 约 30-60s（熔体在挤出机中的停留时间）
     条件: 仅在正常 PET IV (0.60-0.80 dL/g) 范围内成立"
```

---

## 4. 术语映射 (Terminology Mapping)

### 原则
每个核心概念必须有术语映射表，包含：
- **标准名** (canonical name)：本体中使用的正式名称
- **同义词** (synonyms)：同一领域内可以互换使用的名称
- **缩写** (abbreviations)：常见的缩写形式
- **跨语言术语** (cross-language)：中英对照（或其他语言）
- **上下游别名** (context-specific aliases)：在不同阶段/上下文中可能使用的不同名称

### 示例

```json
{
  "canonical_name": "HbA1c",
  "synonyms": ["glycated hemoglobin", "hemoglobin A1c", "A1C test"],
  "abbreviations": ["HbA1c", "A1C", "HBA1C"],
  "cross_language": {
    "zh": "糖化血红蛋白",
    "en": "glycated hemoglobin",
    "ja": "糖化ヘモグロビン"
  },
  "context_aliases": {
    "clinical_lab": "HbA1c%",
    "icd10": "R73.0（异常糖化血红蛋白）",
    "data_column": "hba1c_pct"
  }
}
```

```json
{
  "canonical_name": "MDO 拉伸温度",
  "synonyms": ["纵向拉伸温度", "MD 拉伸温度", "机械方向拉伸温度"],
  "abbreviations": ["MDO_temp", "MDT"],
  "cross_language": {
    "zh": "MDO拉伸温度 / 纵拉温度",
    "en": "MDO stretching temperature / machine-direction orientation temperature"
  },
  "context_aliases": {
    "process_control": "MD_TH001~MD_TH012（各温区）",
    "quality_report": "纵向拉伸设定温度",
    "data_column": "mdo_temp_C"
  }
}
```

---

## 5. 公理与约束 (Axioms and Constraints)

### 原则
领域中的规则和约束必须用自然语言明确表达。公理包括：
- **物理约束**：物理定律施加的硬限制
- **操作约束**：工艺窗口、安全限值
- **逻辑约束**：概念之间的逻辑蕴含
- **互斥规则**：不能同时为真的条件
- **边界条件**：模型在什么条件下失效

### 自然语言公理格式

```
AXIOM <id>: <自然语言陈述>

约束类型: hard | soft | heuristic
适用范围: <概念列表>
违反后果: <如果违反会发生什么>
来源: <知识块引用>
```

### 示例

```
AXIOM temp_viscosity_01:
  "PET 熔体温度每升高 10°C，粘度约降低 30-40%（在 270-290°C 范围内）"
  约束类型: heuristic (Arrhenius 近似)
  适用范围: melt_temp_C, melt_viscosity_Pa_s
  违反后果: 如果温度低于 270°C，该规则失效（存在未熔融粒子）
  来源: kb_pet_physics_003

AXIOM diabetes_hba1c_01:
  "HbA1c ≥ 6.5% 可诊断为糖尿病；5.7-6.4% 为糖尿病前期；<5.7% 为正常"
  约束类型: hard (ADA 诊断标准)
  适用范围: hba1c_pct
  违反后果: 在血红蛋白病或贫血患者中，HbA1c 可能不准确
  来源: kb_clinical_guideline_001

AXIOM legal_noncompete_01:
  "非竞争条款在加利福尼亚州通常不可执行，而在特拉华州可执行（如果合理范围内）"
  约束类型: hard (州法律)
  适用范围: governing_law_state, non_compete_enforceability
  违反后果: 使用不可执行的非竞争条款可能导致整个合同条款无效
  来源: kb_legal_precedent_007

AXIOM credit_fairness_01:
  "模型不得使用受保护特征（种族、性别、年龄组）作为违约预测的直接输入（ECOA 合规）"
  约束类型: hard (联邦法规)
  适用范围: all related_concepts in credit scoring model
  违反后果: 监管处罚 + 诉讼风险
  来源: kb_regulatory_ecoa_001
```

---

## 6. 实例化说明 (Instantiation Examples)

### 原则
每个抽象概念必须有至少一个具体实例，说明：
- **典型值**：在正常运行/标准条件下的期望值
- **异常值示例**：什么样的值是异常的
- **实例上下文**：这个值出现在什么场景下
- **推断路径**：从该值如何推断出领域知识

### 示例

```
概念: HbA1c (hba1c_pct)
实例化:
  正常实例: { value: 5.2%, context: "45岁亚洲女性，无糖尿病史，常规体检" }
  异常实例: { value: 8.1%, context: "55岁非裔男性，2型糖尿病确诊3年，
             推断: 血糖控制不佳，可能需要调整药物方案" }
  边界实例: { value: 6.3%, context: "60岁白人女性，肥胖(BMI=32)，
             推断: 糖尿病前期，需生活方式干预" }
```

```
概念: 主轴振动速度 (spindle_vib_mm_s)
实例化:
  正常实例: { value: 1.2 mm/s RMS, context: "新轴承，8000RPM，铝合金加工" }
  异常实例: { value: 5.8 mm/s RMS, context: "运行2000小时后，
             推断: ISO 10816 Zone C（不满意），可能轴承磨损，
             预计表面粗糙度 Ra > 1.6μm" }
  临界实例: { value: 4.3 mm/s RMS, context: "Zone B 上限附近，
             推断: 需计划维护，尚未影响质量" }
```

---

## 7. 可追溯性 (Provenance)

### 原则
本体中的每个声明必须可追溯到来源知识，并标注置信度：
- **来源引用**：每个概念、关系、公理、实体都引用 source chunk_id
- **置信度**：KNOWN（有直接证据）/ INFERRED（有间接证据）/ UNKNOWN（无证据）
- **推理记录**：为什么从这个知识块推导出这个声明
- **冲突标记**：如果不同来源给出矛盾信息，明确标记

### 反模式
```
❌ 没有任何 knowledge_source 的概念定义
❌ 所有概念的置信度都是 KNOWN（不现实的）
❌ 没有记录推理过程（"HbA1c 正常值 <5.7%" — 从哪个指南来的？）
❌ 有冲突信息但未标记

✅ 每个声明都有 source chunk_id + confidence + 1-2句推理
✅ 冲突信息被标记，并说明选择理由
✅ UNKNOWN 的概念被列入 clarification_needed.json
```

---

## Quality Self-Assessment Checklist

在完成本体构建后，对以下每一项进行自检：

### A. 概念精确性
- [ ] 每个概念有唯一的、精确的自然语言定义
- [ ] 定义包含"不是什么"的消歧义说明
- [ ] 领域专家能从定义判断实例归属

### B. 层次完整性
- [ ] 核心概念出现在至少一个 IS-A 或 PART-OF 层次链中
- [ ] IS-A 和 PART-OF 没有混淆
- [ ] 没有超过 4 层的深层嵌套
- [ ] 没有完全孤立的节点

### C. 关系语义丰富性
- [ ] 每个关系有精确的类型（不是 "related_to"）
- [ ] 每个关系有 2-3 句机制描述
- [ ] 因果方向、时滞、条件约束都已标注
- [ ] 没有循环因果链

### D. 术语映射
- [ ] 核心概念有同义词列表
- [ ] 有缩写和跨语言术语
- [ ] 数据列名与本体概念名之间的映射已记录

### E. 公理与约束
- [ ] 至少有 3 条自然语言公理
- [ ] 公理标注了约束类型（hard/soft/heuristic）
- [ ] 公理标注了违反后果
- [ ] 边界条件已记录

### F. 实例化说明
- [ ] 核心概念有正常实例和异常实例
- [ ] 实例包含上下文和推断路径

### G. 可追溯性
- [ ] 每个声明有 source chunk_id
- [ ] 置信度（KNOWN/INFERRED/UNKNOWN）已标注
- [ ] 冲突信息已标记并说明选择理由
- [ ] UNKNOWN 概念已列入 clarification_needed

如果任何一项不通过，在提交前修复。
