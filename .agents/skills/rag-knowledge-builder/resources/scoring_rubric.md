# Scoring Rubric — Detailed Examples & Edge Cases

> 本文件为 `agents/scoring-agent.md` 的示例和边界情况参考。在 Phase 2 的评分过程中遇到不确定的情况时读取本文件。

## D1: Semantic Relevance — 详细示例

| 场景 | 内容片段 | 得分 | 理由 |
|------|----------|:----:|------|
| CNC 诊断，查询"spindle vibration" | "Spindle bearing wear causes vibration increase... ISO 10816 Zone C >4.5mm/s" | **9.5** | 直接匹配查询意图 + 定量阈值 |
| CNC 诊断，同一查询 | "Rotating machinery vibration monitoring in power plants..." | **4.0** | 讨论旋转设备但不讨论 CNC 加工质量 |
| CNC 诊断，同一查询 | "Heart rate variability monitoring using wearable sensors" | **0.5** | 不相关 — 医学领域 |

## D2: Parameter Direct Match — 详细示例

**context params**: [spindle_vibration_mm_s, spindle_temp_C, surface_roughness_Ra_um]

| 内容中的参数 | 匹配 | 得分 |
|-------------|:---:|:----:|
| "spindle_vibration" (exact) + "surface roughness" (exact) | 2/3 完全匹配 | **6.7** |
| "vibration" (generic) → matches "spindle_vibration" via token overlap | 1/3 部分匹配 | **3.3** |
| "轴承温度" (Chinese) + "粗糙度" (Chinese) | 2/3 语义匹配 | **5.0** |
| "oil viscosity" and "belt tension" | 0/3 匹配 | **0.0** → **AUTO-REJECT** |

## D3: Scenario Consistency — 边界情况

| chunk 标记 | 当前场景 | 得分 | 理由 |
|-----------|----------|:----:|------|
| "CNC_machining" | "CNC machining" | **10** | 完全匹配 |
| "metal_forming" | "CNC machining" | **5** | 邻近场景 — 冷轧的轴承包络与 CNC 主轴共享物理原理 |
| "batch_chemical" | "CNC machining" | **0** | 跨域 — 化学反应器知识不适用于 CNC |
| 无标记 | "CNC machining" | **3** | 中性 — 无法判断其特定性 |

## D4: Source Credibility — 证据等级

| 来源 | 得分 | 何时用 |
|------|:----:|--------|
| `parameter_to_physics.json` | **10** | 预验证的因果链和定量公式 |
| `process_knowledge_base.md` | **10** | 精炼的领域知识 |
| 之前诊断运行(Judge≥90 + ENDORSED) | **8** | 一个数据点 — 需要更多验证才能提升到 10 |
| 用户提供的 SOP 手册 | **7** | 来自用户的权威来源 |
| Wikipedia / ISO 标准 / 制造商 datasheet | **6** | 公开可验证 |
| 技术博客 / StackOverflow | **3** | 未经验证 |
| 无法识别的来源 | **1** | 无信息 |

## D5: Cross-Reference Count — 何时确认的链接才是真链接

**有效交叉验证的要求：**
- 引用相同(参数→目标)对 → 1 次确认
- 引用与第一个来源**相同方向**的因果链(不是反向) → 1 次确认
- 引用**来自不同源文件/URL** → 计为独立
- **不是确认：** 相同文档中内容相似的另一个块 — 那是冗余，不是交叉验证

## Composite Score 参考示例

| D1 | D2 | D3 | D4 | D5 | Composite | Tier | 原因 |
|:--:|:--:|:--:|:--:|:--:|:---------:|------|------|
| 9.5 | 9.5 | 10 | 10 | 8 | **9.35** | CRITICAL | 理想的知识块 |
| 8.0 | 7.0 | 10 | 10 | 5 | **8.25** | ACCEPTED | 全部良好，但没有交叉验证 |
| 6.0 | 8.0 | 5 | 3 | 2 | **5.65** | REJECTED | D4 太低 — web_general 来源单例 |
| 9.0 | 9.0 | 0 | 10 | 8 | — | REJECTED | D3=0(AUTO-REJECT R3): CNC 知识用于化学场景 |
