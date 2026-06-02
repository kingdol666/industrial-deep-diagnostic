# Ontology Output Templates — Universal Natural Language Templates

> 本文件定义了本体输出的模板结构。适用于任何知识领域。

---

## Template A: 通用领域（通用模板）

适用于任何没有被特殊模板覆盖的领域。

```yaml
template: universal
scene:
  name: "{领域名}"
  domain_type: "{specific_domain_snake_case}"
  domain_summary: "2-3 句中文描述"
  scope:
    included: ["本本体覆盖的范围"]
    excluded: ["不覆盖的范围"]
    boundary_conditions: ["模型失效条件"]

concepts:
  target_concept_template:
    name: "概念标准名"
    definition: "精确中文定义：是什么、不是什么、有效条件"
    definition_confidence: "KNOWN|INFERRED|UNKNOWN"
    concept_type: "measurement|outcome|..."
    unit: "SI 或领域单位"
    expected_value_range: "合理范围及说明"
    broader_concept: "父概念（IS-A）"
    part_of_whole: "所属整体（PART-OF）"
    terminology:
      canonical_name: "标准名"
      synonyms: []
      abbreviations: []
      cross_language: {}
      context_aliases: {}
    instantiation:
      normal: {value, context, inference}
      abnormal: {value, context, inference}

  related_concept_template:
    name: "概念名"
    definition: "..."
    concept_type: "predictor|input|control|mediator|..."
    # ...同上结构

  context_dimension_template:
    name: "维度名"
    definition: "分层什么"
    cardinality: "low|medium|high|continuous"
    typical_values: []

entity_template:
  id: "entity_id"
  name: "领域特定实体名"
  type: "agent|component|organization|system|..."
  definition: "2-3 句中文"
  part_of: "父实体"
  has_parts: []
  key_attributes: []
  role_in_domain: "位置描述"

relationship_template:
  id: "rel_NNN"
  from: "源概念"
  to: "目标概念"
  type: "causal|correlative|physical|control|..."
  mechanism: "2-3 句中文"
  direction: "from↑→to↑ | from↑→to↓ | ..."
  conditions: ["前提条件"]
  exceptions: ["例外情况"]
  expected_lag: "时滞"
  knowledge_confidence: 0.0-1.0

constraint_template:
  id: "constraint_NNN"
  statement: "自然语言约束陈述"
  type: "hard|soft|heuristic"
  applicable_concepts: []
  violation_consequence: "违反后果"
  boundary_conditions: "失效条件"

confounder_template:
  name: "混杂因素名"
  type: "batch|category|..."
  reasoning: "2-3 句中文"
  confounded_relationships: []
  expected_impact: "high|medium|low"
```

---

## Template B: 工业过程控制

适用于：制造、加工、化工、冶金等工业领域。

### 额外的概念类型扩展

```yaml
concept_type_extensions:
  - "process_parameter"  # 过程参数（可调节）
  - "quality_indicator"  # 质量指标（目标）
  - "equipment_state"    # 设备状态（监测）
  - "material_property"  # 材料属性（固有）
  - "environmental_factor" # 环境因素（不可控）

relationship_type_extensions:
  - "physical"    # 物理定律约束
  - "control"     # 控制回路

constraint_type_examples:
  hard:
    - "熔体温度 >300°C 会导致 PET 热降解（不可逆）"
    - "反应压力超过安全阀设定值时自动泄压"
  soft:
    - "建议 MDO 拉伸温度控制在 Tg+5~15°C 范围内"
    - "轴承温度 >70°C 建议安排维护"
  heuristic:
    - "温度每升高 10°C，粘度约降低 30-40%（Arrhenius 近似）"
    - "振动速度超过 4.5 mm/s 时表面粗糙度大概率超标"
```

### 工业领域特有字段

```yaml
industrial_extensions:
  process_stages:
    - id: "stage_id"
      name: "工序名"
      order: 1
      function: "该工序的作用"
      key_equipment: ["entity_id"]
      key_parameters: ["concept_name"]
      input_material: "上游来料"
      output_material: "下游产出"

  degradation_mechanisms:
    - name: "退化机制名"
      affected_entity: "entity_id"
      progression: "退化如何随时间/条件发展"
      early_warning_signals: ["concept_name"]
      intervention_options: ["可能的干预措施"]
```

---

## Template C: 临床医学

适用于：疾病诊断、风险评估、治疗方案等。

### 额外的概念类型扩展

```yaml
concept_type_extensions:
  - "biomarker"        # 生物标志物
  - "clinical_outcome" # 临床结局
  - "risk_factor"      # 危险因素
  - "protective_factor" # 保护因素
  - "medication"       # 药物
  - "comorbidity"      # 合并症

relationship_type_extensions:
  - "causal"      # 生物/病理因果
  - "statistical" # 统计模型预测

constraint_type_examples:
  hard:
    - "HbA1c ≥ 6.5% 可诊断为糖尿病（ADA 标准）"
    - "eGFR <30 mL/min 禁用二甲双胍"
  soft:
    - "BMI >25 建议进行糖耐量筛查"
  heuristic:
    - "年龄每增加 10 岁，2 型糖尿病风险约增加 1.5 倍"
```

### 医学领域特有字段

```yaml
clinical_extensions:
  diagnostic_criteria:
    - condition: "疾病名"
      required_biomarkers: ["biomarker_name"]
      thresholds: {"biomarker": "threshold_value"}
      reference: "指南来源"

  treatment_pathways:
    - condition: "疾病状态"
      first_line: ["治疗方案A"]
      second_line: ["治疗方案B"]
      contraindications: ["禁忌条件"]
```

---

## Template D: 法律/合规

适用于：合同审查、合规检查、法规分析等。

### 额外的概念类型扩展

```yaml
concept_type_extensions:
  - "legal_concept"     # 法律概念
  - "contract_clause"   # 合同条款
  - "obligation"        # 义务
  - "right"             # 权利
  - "liability"         # 责任
  - "compliance_requirement" # 合规要求

relationship_type_extensions:
  - "legal"        # 法律因果关系
  - "precedential" # 先例关系
  - "regulatory"   # 监管关系

constraint_type_examples:
  hard:
    - "非竞争条款在加利福尼亚州通常不可执行"
    - "ECOA 禁止使用种族、性别作为信贷决策因素"
  soft:
    - "赔偿条款上限建议不超过合同总价值的 200%"
```

---

## Template E: 金融/风险

适用于：信用评分、市场分析、风险评估等。

### 额外的概念类型扩展

```yaml
concept_type_extensions:
  - "financial_metric"   # 金融指标
  - "risk_score"         # 风险分数
  - "market_factor"      # 市场因素
  - "behavioral_signal"  # 行为信号

relationship_type_extensions:
  - "statistical"  # 统计模型关系
  - "correlative"  # 相关关系

constraint_type_examples:
  hard:
    - "模型不得使用受保护特征作为违约预测的直接输入（ECOA 合规）"
    - "LTV 比率 >80% 需要 PMI 保险"
  heuristic:
    - "债务收入比 >40% 时违约概率显著上升"
```

---

## How to Use Templates (LLM Instructions)

1. **不要死套模板。** 模板是起点，不是终点。根据领域特点增减字段。
2. **优先保证核心结构完整。** concepts、relationships、constraints 是必需的。扩展字段视领域需要。
3. **自然语言定义永远比结构化字段更重要。** 一个好的中文定义胜过 10 个空字段。
4. **每个模板的 constraint_type_examples 都是参考。** 你必须从实际知识块中提取约束，不是复制示例。
5. **如果领域跨模板（如医学+法律），合并多个模板的字段。**

**Anti-pattern:** 不要因为模板里有某个字段就强制填充。没有知识源支持的字段留空或标注 UNKNOWN。
