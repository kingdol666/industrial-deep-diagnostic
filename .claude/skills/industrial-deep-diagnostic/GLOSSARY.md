# 术语表

## A

**Agent Decoupling（Agent 解耦）**
子 Agent 间仅通过 workspace 文件通信，不通过主 Agent 上下文传递信息。

**Anti-Oscillation Rule（反振荡规则）**
修复循环中，若相邻两轮修复指令 issue-type 重叠 >70%，第三次同问题修复直接 halt。

**Anti-Speculation（反推测五条件）**
声称因果必须同时满足：时间先后、统计显著、滞后窗一致性、物理机制可行、无矛盾（含子组内）。

## C

**Checkpoint（CP）**
管线中的强制暂停验证点，共 CP-1 到 CP-9。

**Clarification Gate（澄清门）**
Step 2.5，处理未知参数语义。模式：auto / interactive / minimal。

**Competing Set（竞争集）**
多个假设均无法排除时的诊断输出状态，confidence ceiling ≤65。

**Confidence Ceiling（置信度上限）**
根据结论类型设定的最高置信度：`DETERMINED` 无上限，`COMPETING_SET` ≤65，`NEEDS_DATA` ≤50。

## D

**Data Discriminability（数据鉴别力）**
判断竞争假设是否预测不同可观测模式的能力。缺乏鉴别力时必须输出 `COMPETING_SET`。

**Data Truth Mandate（数据真实铁律）**
data-processor 的最高约束：每个写入 JSON 的数字必须可从数据重算。

**Detrended Correlation（去趋势相关）**
去除共享时间趋势后的相关性，用于检测趋势混淆。

**Dual-Drive Analysis（双驱动分析）**
结合工艺参数波动与检测/质量异常，判断工艺异常是否进入缺陷因果链。

## E

**Evidence Closure（证据闭环）**
必须同时覆盖：纯工艺波动分析、工艺+检测双驱动分析、本体/行业知识解释。

**Evidence Grade（证据等级 L1-L7）**
L1 直接测量值 → L7 无支持假设。结论受最低等级约束。

**Execution Proof（执行证明）**
`.pipeline_events.jsonl` 通过 `pipeline-log-check.mjs` 校验，才视为完整执行。

## H

**HTML Opt-Out**
用户前置声明不要 HTML。通过 `00_input/html_opt_out` 标记文件生效。

## I

**INDISTINGUISHABLE**
竞争假设预测完全相同的可观测模式，无法区分。必须输出 `COMPETING_SET`。

## M

**Method Stage（方法阶段 1-6）**
通用诊断方法论阶段：统计验证 → 观察 → 时序相关 → 假设生成 → 实验验证 → 结论。

## O

**Ontology（本体）**
`ontology.json` 中定义的工艺阶段、设备、参数物理含义、行为匹配和差异信号。

**ontology_first（本体优先）**
Step 2 本体构建完成后，Step 3 才能进行实质性统计分析。

## P

**Phase（Agent 阶段）**
Diagnostician 内部流程编号 Phase 0-7。

**Pipeline Step（管线步骤 0-9）**
编排层流程编号：Setup → Inspect → Context → Clarify → Data → Diagnose → Judge → Report → Audit → HTML → Finalize。

**Process-Fluctuation Diagnosis（纯工艺波动诊断）**
仅从工艺数据中识别物理意义上的异常漂移、不稳定、阈值行为或工况切换。

**Production Regime Detection（生产工况检测）**
自动识别开机、停机、稳态三类工况，统计仅使用稳态数据。

## R

**Reasoning Segment（推理段 R1-R8）**
`reasoning_chain.json` 中的结构化推理路径：数据证据 → 物理证据 → 视觉证据 → 假设生成 → 假设评估 → 假设排除 → 结论形成 → 可证伪条件。

**Red Light Action（红灯动作）**
任何 Agent 均禁止的行为，命中一条 Judge 可直接判 fail。

**Repair Loop（修复循环）**
Judge 或 Reviewer 发现问题后，重新启动 diagnostician 修正诊断。

## S

**Schema-First（Schema 优先）**
写任何结构化文件前先读对应 schema，一次写对并立即验证。

**Simpson's Paradox（辛普森悖论）**
全数据集相关方向与分组内相关方向相反的现象。必须检测并处理。

**Steady-State Filtering（稳态过滤）**
仅对稳态工况数据进行统计分析，排除开机/停机/过渡影响。

## T

**Time-Lag Compensation（时滞补偿）**
用 CCF 找到 process→quality 的最优滞后，修正零滞后相关系数的偏差。

**Trend Confounding（趋势混淆）**
两个变量因共享时间趋势而表现出的虚假相关。去趋势后相关性衰减 >50% 即为严重。

## V

**VLM Visual Evidence（VLM 视觉证据）**
通过视觉语言模型从图表中提取的结构化观察，如同步组、事件响应、趋势形态。
