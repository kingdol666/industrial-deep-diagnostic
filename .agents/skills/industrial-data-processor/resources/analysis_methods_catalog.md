# Analysis Methods Catalog — 自适应方法选择目录

Phase 1.2（假设驱动方法选择）的唯一方法来源。**skill 只定义方向与选择规则；具体执行方式、参数与脚本由 agent 根据数据实况自行判断。**

## 选择规则（铁律）

1. **方法跟着假设走**：每个候选假设 H 必须映射到 ≥1 个能**判别**它的最小方法集；判别不了它的方法一律不跑。
2. **最小充分**：优先选择"能用最少计算判别最多假设"的方法组合；跑全量电池（`--mode full`）仅当方法计划明确选择了全部三项 stats 模式。
3. **跳过必须留痕**：传统"必跑"方法被跳过时，在 `analysis_method_plan.json` 的 `skipped` 中写明触发条件不满足的原因。
4. **目录不足即自建**：没有任何现有工具能判别某假设时 → 写聚焦的自定义脚本（M13），并在 plan 中登记。
5. **前置条件不满足 = 自动跳过**：每个方法的 Preconditions 是硬性门槛，运行前自检。

## 方法条目

### M1 · Correlation Screening — `stats/run.py --mode correlation`
- **判别**：哪些预测子与目标存在（伪）相关线索
- **前置**：≥2 个数值预测子 + ≥1 个数值目标；非数值列已在 Phase 0.4 分层
- **产出**：validate_report.json 的 correlation 段
- **不要用**：目标全为常量/分类时；纯分类目标改用 M8 分层比较

### M2 · Anti-Spurious Battery — `stats/run.py --mode spurious`
- **判别**：M1 的线索是真是假（Simpson / 去趋势衰减 / 变点 / 留一法杠杆）
- **前置**：存在分组列（Simpson/LOO）或时间列（去趋势/变点）——至少其一
- **不要用**：单产品且无时间列（无事可拆）；M1 未发现 |r|≥0.3 的候选时可降级为只跑变点

### M3 · Batch Integrity — `stats/run.py --mode batch`
- **判别**：批次标识完整性、跨批次污染（v6.6）
- **前置**：存在批次/_lot/_id 身份列
- **不要用**：无任何批次身份列

### M4 · Anomaly Detection — `dp_toolkit.py anomaly`
- **判别**：异常的分布、起始时间、与目标的共现
- **前置**：≥1 个数值列（几乎总是满足）→ **默认基线方法**
- **不要用**：无（缺失时说明理由即可）

### M5 · Production Regime Filter — `dp_toolkit.py regime-filter`
- **判别**：非稳态（启停/换产）是否污染了统计；确定 stats 输入源
- **前置**：时间列 + 工况类信号
- **不要用**：无时间列（fallback 全量 + WARNING，协议 Phase 1.5 已定义）

### M6 · Time-Lag CCF Compensation — `time_lag_compensator.mjs`
- **判别**：X 先于 Y 还是同步/反向（因果方向证据、v6.4）
- **前置**：时间列 + process_plus_inspection 双驱动数据
- **不要用**：无时间列；单侧数据（process_only 时因果时序证据缺失是天然证据缺口，写进 conclusion 而非硬跑）

### M7 · Physics Constraint Checks — `physics_check.py`
- **判别**：本体物理关系（方向/量级/函数形式）与数据方向是否一致
- **前置**：ontology relationships 中存在可数值校验的关系 + 对应列存在
- **不要用**：本体无可校验物理关系（0 checks 合法，需写明）

### M8 · Stratified / Per-Product Analysis — `stats/run.py --group-col <col>` + 模式 C
- **判别**：聚合相关是否为组间差异伪造（Simpson 的正向验证）；最差组定位
- **前置**：产品/组列且 ≥2 组、每组样本充足（≥30 行宜）
- **不要用**：无分组列或组数=1

### M9 · Paired-Sensor Differential & Efficiency — 模式 B（自定义脚本，T3）
- **判别**：级联链路中**哪一段**劣化（Δ=inlet−outlet、ε 效率指标的趋势/变点）
- **前置**：成对传感器（inlet/outlet、feed/die 等）或可派生的效率度量
- **不要用**：无成对结构

### M10 · Zone Drift Localization — 模式 A（自定义脚本，T3）
- **判别**：劣化是全局还是局部（分区斜率排名、相邻差分）
- **前置**：同名前缀 + 序号分区列（zone_1..zone_N）
- **不要用**：无分区结构

### M11 · Event-Response Alignment — 自定义脚本，T3
- **判别**：事件（换刀/清洗/维护）前后指标是否存在阶跃/趋势变化
- **前置**：事件标记列或已知事件时间点 + 时间列
- **不要用**：无事件信息

### M12 · Scenario-Pattern Deep Dives — `resources/scenario_patterns.md` A–H
- 按 Phase 1 检出的数据形状加载对应节；**只有被方法计划映射到某假设时才执行**
- 计划外的模式临时加入 → 必须在 Adaptive Decision Audit 里补记原因

### M13 · Custom Focused Script（逃生口）
- 判别：目录全部不适用时的针对性计算
- 要求：写入 `06_scripts/`、遵守 Data Truth Mandate、输出回写 conclusion 引用

## 假设 → 方法 速查（示例映射，非穷举）

| 假设类型 | 典型判别方法 |
|---------|-------------|
| "参数 X 漂移导致目标劣化" | M1 → M2（去趋势/变点）→ M6（时序先后）→ M7（物理方向） |
| "某产品/刀具特有问题" | M8 → M2（分层 Simpson）→ M4（最差组异常率） |
| "级联链路某段效率下降" | M9 → M7（效率物理式）→ M2（Δ 指标变点） |
| "批次污染/标识错误" | M3 → M8 |
| "非稳态工况混入统计" | M5 → M2（稳态前后对比） |
| "分区局部劣化" | M10 → M1（分区排名） |
