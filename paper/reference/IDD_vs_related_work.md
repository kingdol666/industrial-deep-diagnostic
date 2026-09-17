# IDD 与近期对标文献：架构方向对比与雷同风险判定

对照对象：`paper/main.tex`（IDD，*Trustworthy agentic diagnosis for industrial processes: evidence-graded
competing-hypothesis reasoning evaluated against per-fault literature baselines*，投稿 AEI）。
文献清单见同目录 `README.md`。判定日期 2026-09-16。

---

## 一、IDD 的架构方向（把论文压成一句话）

> **IDD = 一条"可审计的"工业过程根因诊断流水线：用确定性脚本做统计、用 LLM agent 做机理推理，
> 靠"证据定级 + 竞争假设 + 三态裁决 + 机检评测契约"把 LLM 的结论变成工程上可复核的产物。**

它由六个相互咬合的支柱构成，缺任何一条都不成立：

| # | 支柱 | 具体机制 | 论文位置 |
|:--|:--|:--|:--|
| 1 | **九阶段编排 + 机械检查点 + 有界修复** | 18 skill 包 / 14 agent；CP-1…CP-9 每步为纯机械谓词（文件存在 / schema 合法 / 数值下界）；repair best-of-3、全局 ≤5、抗振荡置信度上限 0.50 | §System Architecture |
| 2 | **竞争假设协议 + 三态裁决** | 每场景 ≥3 假设，各带机理类 / 证据集 / 矛盾集；消除量化（$\lvert X_i\rvert>\lvert E_i\rvert$）；输出 determined / competing_set / needs_data | §Diagnostic Methodology |
| 3 | **证据分级 L1–L7 与门传播** | 结论置信度被"链上最弱证据级别"封顶；质量门拒绝超界置信度——把"抑制幻觉"从提示词指令变成**可算的算术约束** | §Evidence Grading |
| 4 | **四条件反伪相关过滤器** | 时滞补偿 CCF（时序在先）+ 去趋势/分层/多重校正后仍显著 + 本体中已有物理机理 + 留一法无矛盾；且先做稳态/批次相过滤 | §Anti-Spurious-Correlation |
| 5 | **机检评测契约 C1–C5** | 真值隔离（双向泄漏哨兵）、SHA-256 数据指纹、阶段署名产物+溯源标签、**执行证明**（无事件日志即无结果）、门禁评分；12 场景（SKAB/TEP/IndPenSim） | §Evaluation Framework |
| 6 | **引擎可互换执行层 + 本体资产库** | 14 引擎同一 start/stream/close 契约（400/409 类型化预检错误）；本体按 schema 指纹发布复用（知识复利） | §Execution Layer |

**论文自己承认的"真卖点"**：模型受控消融显示裸模型调用在同一盲摘要上 9/9 全对（流水线 6/9 解决），
因此 IDD 的贡献被明确定位为 **可审计性、标定过的不确定性、门控过程保证**——而不是准确率。
**其中"标定三态结论"(iii) 与"机检评测契约"(iv)，论文声称在同域所有已发表/同期系统中均不存在。**

---

## 二、逐篇侧重点（按与 IDD 的接近程度排序）

### 第 1 层｜同一战场，方法可对话（必须正面引用/区分）

**① AgentRCA — Agentic Root Cause Analysis through Evidence-Grounded Reasoning（arXiv 2607.22385, 2026-07-24）**
- 侧重：**零样本 agentic RCA**。正常态数字孪生 + 工具增强 LLM；agent 迭代采集统计证据、评估竞争假设、
  指认最能解释观测的物理故障；数据集为多相流装置 + 大型化工厂（TEP 系）；输出**透明推理轨迹**。
- 与 IDD 的重叠：agentic 框架 + 证据接地 + 竞争假设 + 真实工业时序 + TEP。**这是全库最接近的一篇，且已在 IDD 的 refs.bib 中（wei2026agentrca）。**
- 与 IDD 的差异：无证据分级（L1–L7）；无置信度上限算术与三态 cap；输出是**排序假设表**而非带标定的单裁决；
  无质量门/有界修复；无"机检评测契约"（无真值隔离/指纹/执行证明）；Top-1 40.0%、Top-2 61.5%（且**排除 IDV3/9/15**，正是 IDD 处理的那类）。

**② AEI 2026 — A trustworthy agentic AI framework for auditable label-free machinery fault diagnosis（10.1016/j.aei.2026.105205）**
- 侧重：**"可信 + 可审计 + agentic"的机械（旋转设备）故障诊断**，label-free（免故障标签），安全关键工程系统。
  作者 Yuntong Chen 等（西北工业大学），与同组 OA 预印本 **DENet（arXiv 2607.22797）**同源——后者把输出扩展为
  **结构化证据记录**（分类 + 可对理论值核验的特征频率 + 瞬态冲激的时间定位），并给出"预测频率 vs 理论频率
  偏差"作为**免标签、推理时校验信号**（AUROC 0.970 / 0.87）。
- 与 IDD 的重叠：**标题层面最高**——"trustworthy agentic"+"auditable"+"fault diagnosis"三个词同时命中；
  同为"让诊断输出可被独立核验"的动机。
- 与 IDD 的差异：对象是**部件级机械振动**而非**过程机理**；label-free 指免故障标签（IDD 的问题是免任务训练但用统计+机理）；
  无多阶段编排/检查点/修复；无三态裁决与置信度等级体系；评测是部件数据集而非场景级基准。
- ⚠ **未获取全文**（闭源、无 OA 副本）。**标题重合度高，建议投稿前务必通过机构订阅取得原文逐段核对。**

### 第 2 层｜机制上高度呼应，可作为"思想同源/邻近"引用

**③ AgentCDM（arXiv 2508.11995）** — 直接用 **ACH（Analysis of Competing Hypotheses）**驱动多 agent 决策，
把决策从"被动选答案"改为"主动假设评估与构造"，并两阶段训练内化。**IDD 竞争假设协议的思想祖先同源**
（IDD 正文亦引 Heuer 的 ACH）。差异：AgentCDM 面向通用决策基准，不接触工业时序、无证据等级、无门控。

**④ EviDx（arXiv 2608.24570, SJTU）** — **证据感知的主动诊断**：证据环境 + 临床脚手架 + 观察者引导的运行时
harness，**用不确定性与证据覆盖度来调节"何时终止诊断"**，并做三层评估金字塔（执行鲁棒性/推理动态/诊断结局）。
与 IDD 的"数据不足以判别时输出 competing_set 而非硬下结论"是**同一个决定性动作**，但域在临床。

**⑤ CORESEC / The Abstention Protocol（arXiv 2608.21412, Microsoft）** — 用**弃权代数**替代加权融合：
遥测 agent 以控制标志组合，证据模糊时给出**确定性弃权**而非不稳定归因；超大规模生产部署。
与 IDD 的 needs_data/competing_set 是同一设计哲学（Chow 的 reject 选项），域在数据中心网络。

**⑥ HCAA — A Trustworthy Industrial Fault Diagnosis Architecture（arXiv 2510.03815）** — 贝叶斯网络初诊 +
LLM 认知仲裁（可读诊断图）+ **温度标定与 ECE 风险量化**。IDD 剩余未做的那件事（**真正的心理测量学标定研究**）
正是 HCAA 的强项；IDD 目前只报"上限合规"并自陈其循环性。

**⑦ TraceBench（arXiv 2608.27182, ETH）** — 面向**时序 RCA agent 的受控评测基准**（仿真物理系统 + 参数扰动归属），
发现 agent 更依赖数值控制台输出而非可视化。IDD 的 C1–C5 契约是"评测基础设施"，TraceBench 是"评测任务生成器"，
两者互补；TraceBench 不含执行证明/真值隔离/产物溯源。

**⑧ OpsHarness — From General Agents to RCA Experts（arXiv 2608.25661, ByteDance/CUHK）** — 主张**把力气放在
agent 之外的 harness**，并让它**自演化**、把历次诊断经验沉淀为可复用专长（数据面知识分层 + idea-card 工具库；
控制面 setup/diagnosis/evolution/verification）。与 IDD"本体资产库按指纹复用→知识复利"高度同构。

### 第 3 层｜相邻但不构成竞争

| 文献 | 侧重点 | 与 IDD 的关系 |
|:--|:--|:--|
| **OpsHarness 之外** | | |
| Onnes（2607.05805） | 物理接地数字孪生 + 零样本 LLM agent 面板 vs 监督分类器**头对头**；报告真实硬件误报率 6.4% | IDD"模型受控消融"的同类诚实性设计，域在低温制冷 |
| DMAIC-IAD（2606.04599） | DMAIC 质量框架启发，"先规划后判"：异构参考蒸馏为 SOP + 免执行判决器模型排序策略 | 对应 IDD 的"判官门"与"先描述后诊断" |
| S2S-FDD（2603.08048, 浙大） | 信号→语义算子（趋势/周期/偏差）+ 多轮树状诊断 + 动态追加信道查询 | 与 IDD 统计摘要→机理推理、以及"点名缺失测量"呼应 |
| LLM Agents + Digital Twins for Fault Handling in Process Plants（2505.02076） | 过程工厂故障处置**闭环控制**（孪生既作知识库又作验证平台） | IDD 只做诊断决策支持，不闭环控制 |
| AURA（2511.03075） | LLM + 数字孪生 + **人在回路**；人确认诊断回流为参考样本 | 与 IDD 的"决定支持、人类签核"部署治理同向 |
| Integrating LLMs for Explainable FD（2402.06695, Argonne） | 模型化诊断 PRO-AID（核工程物理模型）+ LLM 解释层 | IDD 自动物理核验的前身式做法 |
| Exploring LLM-based Frameworks for FD（2509.23113, Hitachi） | 单 LLM vs 多 LLM × 输入表示 × 上下文窗口的**系统消融** | 与 IDD 消融章节同一方法论 |
| AutoIAD（2508.05503） | 管理器驱动多 agent，端到端**自动开发**视觉异常检测模型 | 编排结构相似，但产出是模型不是诊断结论 |
| LLM-ADAM（2605.03328）/ In-situ AM（2604.09889） | 增材制造过程异常检测 agent | 制造监测，非根因机理 |
| Foundation-Model Agents in Industrial Automation（2605.02592） | 领域综述（用途/能力/开放挑战） | 可用作 related-work 的定位锚点 |
| RADIANT-LLM（RESS 10.1016/j.ress.2026.113057） | 检索增强 + agentic + 页面/图级可追溯 + 幻觉抑制，核安全文档问答 | 可追溯性与证据接地同向，任务是文档问答而非时序 RCA |
| Rec-PdM（JMS 10.1016/j.jmsy.2026.08.012） | **决策校准**的多 agent 处方维护；信念溯源；对决策遗憾/尾部风险标定 | "标定"与"溯源"与 IDD 同向，目标是最优干预而非根因 |
| Co-Integration Causal RCA（TASE 10.1109/tase.2026.3710929） | 协整增强因果推断，抑制非平稳对因果网络的扭曲，TEP+多相流定位根因 | 传统因果 RCA 的当代最强形态，是 IDD 反伪相关过滤器的对照面 |
| FaultExplainer（2412.14492） | PCA 检测 + LLM 故障解释（TEP）| **IDD 的主要对照基线**（per-fault baseline 来源）|
| Loom（2609.02649） | 把多条诊断线索在**嵌入空间加权重加权**收敛为自由文本共识 | 对应 IDD"多假设→单一裁决"，但无证据等级与上限算术 |
| PropLLM（2606.00582） | 传播感知的场景重建（网络故障诊断）| 传播路径建模，域在通信网 |
| RCAgent（2310.16340） | 工具增强 LLM agent 做云根因分析（含工具调用+环境反馈）| agentic RCA 早期范式 |
| LLMs for Telecom RCA（2609.02805） | 结构化推理 + 检索增强知识接地 + agentic 编排 + 可验证推理 | 跨域同构（电信），无工业时序/无证据等级 |

---

## 三、雷同 / 高度相似判定

**结论：未发现与 IDD"高度雷同或一致"的文章。** 没有任何一篇同时具备
"真实工业时序输入 + 机理级根因 + 证据分级 + 标定三态裁决 + 机检评测契约"这五要素的组合。

按风险分级：

### 🟡 需要处理（标题/动机重合，但实质不同）—— 2 篇

1. **AEI 10.1016/j.aei.2026.105205**
   *"A trustworthy agentic AI framework for auditable label-free machinery fault diagnosis in safety-critical engineering systems"*
   —— **标题词面重合度最高**，且**同刊同卷（AEI）**。审稿人极可能同时看到。
   **风险点**：仅凭标题，"trustworthy / agentic / auditable / fault diagnosis / safety-critical"几乎逐词对应。
   **实质差异**（据其同组 OA 预印本 DENet 推断）：对象为**机械部件振动**而非**过程机理**；产出为*结构化证据记录 +
   频率偏差校验信号*而非*竞争假设三态裁决 + 证据等级门*；无多阶段编排、检查点、修复循环、评测契约。
   → **行动建议**：投稿前获取全文，在 Introduction/Related Work 中显式、精确地区分"auditable"在两边各指什么
   （对方 = 输出可对物理理论值核验；IDD = 全流程产物经由门控与执行证明可复核）。必要时在 Cover Letter 主动说明。

2. **AEI 10.1016/j.aei.2026.105198**
   *"Semantic-guided label-free multimodal fault diagnosis bridging time-series and textual data with language models"*
   —— 同为 AEI、同为"时序+语言模型+免标签"。差异：多模态语义对齐的**分类式 FDD**，无竞争假设、无三态裁决、
   无证据分级、无评测契约。风险等级低于第 1 篇。

### 🟢 已充分区隔（引用即可）

- **AgentRCA（2607.22385）**：同一战场的最强近邻，但 IDD 论文已引用并逐条列出五点协议差异
  （i 真时序 vs 无；ii 机理级 vs 排序假设表；iii 标定三态——对方列为 future work；iv 机检契约——对方无；
  v 排除口径）。**建议保持现有关联工作段落，并核对对方是否已有更新版本**（该文 2026-07 上线，与之论文
  引用口径一致）。
- AgentCDM / EviDx / CORESEC / HCAA / TraceBench / OpsHarness：**机制同源、域不同**，属于"思想祖先/邻近"
  而非雷同。**建议至少各引一条**——尤其 HCAA（标定）与 TraceBench（基准），因为你论文自陈的
  "心理测量学标定研究留待将来"和"机检契约"正是这两篇的正面交锋点，主动引用能显著降低审稿人
  "你忽略了最近工作"的质疑。

### 📌 未覆盖的检索盲区（诚实声明）

- 上述判定中，**2 篇 AEI 闭源论文仅依据标题、作者、期刊卷期**（Crossref/OpenAlex/Unpaywall/Semantic Scholar
  均无摘要，ScienceDirect 反爬返回 403，RSS 仅含题录）。**这两篇的"实质差异"结论对第 1 篇部分依据其同组
  OA 预印本（DENet）推断，属间接证据。**
- IEEE-TII 上未检索到"工业过程 + LLM agent + 根因"组合的论文（该刊此方向以零样本分类、知识图谱构建、
  信号语义化为主）。
- 检索限于 arXiv / Crossref / OpenAlex / Semantic Scholar / Unpaywall / Elsevier RSS；未覆盖 **Scopus、
  Web of Science、Google Scholar**（本机网络对这些站点不可达或返回反爬页），因此可能存在少量未被索引的条目。

---

## 四、对写作的三条可执行建议

1. **补引邻域最强近作**：把 AgentCDM（ACH）、EviDx（证据充分性判据）、CORESEC（弃权代数）、TraceBench（基准）、
   OpsHarness（harness 自演化）纳入 Related Work，并在 Table 1 的"Calib./Repro. gate"两列上对其逐项标注
   ——这正是 IDD 声称的独占维度，主动列表比分点叙述更有说服力。
2. **主动拆解 "trustworthy/auditable" 的词义**：因 AEI 105205 已占位该词面，建议在 Introduction 第一段就
   给 IDD 的 auditability 下**可操作定义**（"结论可分解为假设/证据/排除/置信度，且执行证明使产物不可伪造"），
   与"输出可对理论值核验"式的 auditability 区分开。
3. **把"缺失测量即工单"提升为贡献句**：三篇（EviDx 的终止判据、CORESEC 的弃权、AgentRCA 的 future work）
   都只到"承认不确定"为止，只有 IDD 把它变成**点名信道的工作指令**——这是你相对全部近邻最锐利的差异点，
   值得在 Abstract 与 Conclusion 各出现一次。
